from typing import Any

from rq.job import Job

from src.conversation.store import (
    ConversationStore,
)
from src.services.assistant_service import (
    AssistantService,
)
from src.wechat.client import WeChatClient
from src.wechat.text_formatter import (
    format_wechat_text,
)


# ============================================================
# Worker-local Services
# ============================================================

_assistant_service: AssistantService | None = None
_wechat_client: WeChatClient | None = None
_conversation_store: ConversationStore | None = None


def get_assistant_service() -> AssistantService:
    """
    每个 RQ Worker 复用一个 AssistantService。
    """

    global _assistant_service

    if _assistant_service is None:
        print(
            "[WORKER] Loading "
            "AssistantService..."
        )

        _assistant_service = (
            AssistantService()
        )

        print(
            "[WORKER] "
            "AssistantService ready."
        )

    return _assistant_service


def get_wechat_client() -> WeChatClient:
    """
    每个 RQ Worker 复用一个 WeChatClient。
    """

    global _wechat_client

    if _wechat_client is None:
        _wechat_client = (
            WeChatClient()
        )

    return _wechat_client


def get_conversation_store() -> ConversationStore:
    """
    每个 RQ Worker 复用一个 ConversationStore。
    """

    global _conversation_store

    if _conversation_store is None:
        _conversation_store = (
            ConversationStore()
        )

    return _conversation_store


# ============================================================
# Final Failure Callback
# ============================================================


def handle_wechat_job_failure(
    job: Job,
    connection,
    exc_type,
    exc_value,
    traceback,
    *args,
    **kwargs,
) -> None:
    """
    RQ Job 失败回调。

    Retry 尚未耗尽：
        只记录日志，不通知用户。

    Retry 已耗尽：
        给用户发送一次最终失败提示。

    open_id 从原 Job args 中取得：
        process_wechat_message(open_id, content)
    """

    retries_left = getattr(
        job,
        "retries_left",
        None,
    )

    print(
        "[RQ FAILURE CALLBACK] "
        f"job={job.id} "
        f"retries_left={retries_left} "
        f"error={getattr(exc_type, '__name__', exc_type)}: "
        f"{exc_value}"
    )

    # --------------------------------------------------------
    # 如果还有重试机会，不通知用户
    # --------------------------------------------------------

    if (
        retries_left is not None
        and retries_left > 0
    ):
        print(
            "[RQ FAILURE CALLBACK] "
            f"job={job.id} "
            "retry pending, "
            "skip user notification."
        )

        return

    # --------------------------------------------------------
    # 获取 open_id
    # --------------------------------------------------------

    if not job.args:
        print(
            "[RQ FAILURE CALLBACK ERROR] "
            f"job={job.id} "
            "missing job args."
        )

        return

    open_id = str(
        job.args[0]
    )

    # --------------------------------------------------------
    # 防止极端情况下重复发送最终失败通知
    # --------------------------------------------------------

    notification_key = (
        f"wechat:failure_notified:{job.id}"
    )

    first_notification = (
        connection.set(
            notification_key,
            "1",
            nx=True,
            ex=86400,
        )
    )

    if not first_notification:
        print(
            "[RQ FAILURE CALLBACK] "
            f"job={job.id} "
            "failure notification "
            "already sent."
        )

        return

    # --------------------------------------------------------
    # 最终失败通知
    # --------------------------------------------------------

    try:
        client = get_wechat_client()

        client.send_text_message(
            open_id=open_id,
            content=(
                "AI 辅导员暂时无法处理"
                "这个问题，请稍后重新发送。"
            ),
        )

        print(
            "[RQ FINAL FAILURE SENT] "
            f"job={job.id} "
            f"user={open_id}"
        )

    except Exception as send_exc:
        print(
            "[RQ FINAL FAILURE SEND ERROR] "
            f"job={job.id} "
            f"user={open_id} "
            f"{type(send_exc).__name__}: "
            f"{send_exc}"
        )

        # 通知发送失败，删除幂等标记。
        # 以后如果有人工补偿机制，
        # 仍然可以再次尝试。
        try:
            connection.delete(
                notification_key
            )
        except Exception:
            pass


# ============================================================
# WeChat Job
# ============================================================


def process_wechat_message(
    open_id: str,
    content: str,
) -> dict[str, Any]:
    """
    处理一条微信消息。

    成功：
        AI
        -> 格式化
        -> 微信发送
        -> 保存会话历史
        -> Job FINISHED

    失败：
        AI 或微信发送失败时，
        直接抛异常给 RQ。

    注意：
        微信发送成功后，如果仅仅是
        ConversationStore 保存失败，
        不再抛异常。

        否则 RQ Retry 可能导致用户
        收到重复回答。

    Retry 和最终失败通知由 RQ 负责。
    """

    print(
        "[RQ START] "
        f"user={open_id} "
        f"question={content}"
    )

    service = get_assistant_service()

    client = get_wechat_client()

    # ========================================================
    # AI
    # ========================================================

    result = (
        service.handle_question(
            content,
            conversation_id=open_id,
        )
    )

    answer = (
        result.get(
            "answer",
            "",
        )
        .strip()
    )

    answer = format_wechat_text(
        answer
    )

    if not answer:
        raise RuntimeError(
            "AI returned an empty answer."
        )

    # ========================================================
    # WeChat length protection
    # ========================================================

    max_length = 1800

    if len(answer) > max_length:
        answer = (
            answer[:max_length]
            + "\n\n"
            "（回答较长，已截断。）"
        )

    # ========================================================
    # Send
    # ========================================================

    # 如果这里失败：
    # 直接抛异常给 RQ Retry。
    #
    # 因为此时还没有写入 conversation，
    # 所以不会污染会话历史。
    client.send_text_message(
        open_id=open_id,
        content=answer,
    )

    # ========================================================
    # Conversation History
    # ========================================================

    # 到这里说明微信发送已经成功。
    #
    # 因此即使 ConversationStore 写入失败，
    # 也不能再让整个 Job Retry，
    # 否则可能重复向用户发送相同回答。

    try:
        conversation_store = (
            get_conversation_store()
        )

        intent = result.get(
            "intent"
        )

        safety_level = result.get(
            "safety_level"
        )

        # ----------------------------------------------------
        # User
        # ----------------------------------------------------

        conversation_store.append(
            conversation_id=open_id,
            role="user",
            content=content,
            intent=(
                intent
                if isinstance(
                    intent,
                    str,
                )
                else None
            ),
            safety_level=(
                safety_level
                if isinstance(
                    safety_level,
                    str,
                )
                else None
            ),
        )

        # ----------------------------------------------------
        # Assistant
        # ----------------------------------------------------

        # 保存用户实际在微信里看到的回答：
        #
        # format_wechat_text()
        # + 长度保护之后的最终文本。
        conversation_store.append(
            conversation_id=open_id,
            role="assistant",
            content=answer,
            intent=(
                intent
                if isinstance(
                    intent,
                    str,
                )
                else None
            ),
            safety_level=(
                safety_level
                if isinstance(
                    safety_level,
                    str,
                )
                else None
            ),
        )

        print(
            "[CONVERSATION SAVED] "
            f"user={open_id} "
            f"intent={intent} "
            f"safety={safety_level}"
        )

    except Exception as exc:
        print(
            "[CONVERSATION SAVE ERROR] "
            f"user={open_id} "
            f"{type(exc).__name__}: "
            f"{exc}"
        )

    # ========================================================
    # Done
    # ========================================================

    print(
        "[RQ DONE] "
        f"user={open_id}"
    )

    return {
        "success": True,
        "open_id": open_id,
        "intent": result.get(
            "intent"
        ),
        "safety_level": result.get(
            "safety_level"
        ),
    }