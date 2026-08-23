from typing import Any

from rq.job import Job

from src.conversation.store import (
    ConversationStore,
)
from src.handoff.handoff_service import (
    HandoffService,
)
from src.services.assistant_service import (
    AssistantService,
)
from src.wechat.client import WeChatClient
from src.wechat.text_formatter import (
    format_wechat_text,
)


# ============================================================
# WeChat Text Protection
# ============================================================


def truncate_wechat_reply(
    text: str,
    max_length: int = 1800,
) -> str:
    """
    微信文本长度保护。

    如果文本没有超过限制：
        原样返回。

    如果文本超过限制：
        优先在靠近末尾的完整句子或换行处截断，
        尽量避免把一句话直接切成两半。
    """

    text = text.strip()

    if len(text) <= max_length:
        return text

    candidate = text[:max_length]

    cut_positions = [
        candidate.rfind("\n"),
        candidate.rfind("。"),
        candidate.rfind("！"),
        candidate.rfind("？"),
    ]

    cut_position = max(
        cut_positions
    )

    if cut_position >= int(
        max_length * 0.7
    ):
        candidate = candidate[
            :cut_position + 1
        ]

    return (
        candidate.rstrip()
        + "\n\n"
        "（回答内容较长，以上为主要内容。）"
    )


# ============================================================
# Worker-local Services
# ============================================================


_assistant_service: AssistantService | None = None
_wechat_client: WeChatClient | None = None
_conversation_store: ConversationStore | None = None
_handoff_service: HandoffService | None = None


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


def get_handoff_service() -> HandoffService:
    """
    每个 RQ Worker 复用一个 HandoffService。
    """

    global _handoff_service

    if _handoff_service is None:
        _handoff_service = (
            HandoffService()
        )

    return _handoff_service


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
    # 防止重复发送最终失败通知
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

        try:
            connection.delete(
                notification_key
            )
        except Exception:
            pass


# ============================================================
# Human Handoff Processing
# ============================================================


def process_human_handoff_message(
    open_id: str,
    content: str,
    handoff_status: str,
) -> dict[str, Any]:
    """
    HUMAN_PENDING / HUMAN_ACTIVE 状态下处理学生消息。

    规则：
    - 不调用 AI；
    - 保存学生后续消息；
    - 给学生发送受控提示；
    - 返回 Job 成功。
    """

    print(
        "[AI BYPASS] "
        f"user={open_id} "
        f"status={handoff_status}"
    )

    # ========================================================
    # Save User Message
    # ========================================================

    try:
        conversation_store = (
            get_conversation_store()
        )

        conversation_store.append(
            conversation_id=open_id,
            role="user",
            content=content,
            intent="counseling",
            safety_level=None,
        )

        print(
            "[HUMAN MESSAGE SAVED] "
            f"user={open_id} "
            f"status={handoff_status}"
        )

    except Exception as exc:
        print(
            "[CONVERSATION SAVE ERROR] "
            f"user={open_id} "
            f"{type(exc).__name__}: "
            f"{exc}"
        )

    # ========================================================
    # Controlled Reply
    # ========================================================

    if (
        handoff_status
        == HandoffService.HUMAN_PENDING
    ):
        answer = (
            "你的情况已经进入人工辅导员"
            "跟进流程。"
            "\n\n"
            "你可以继续在这里发送消息，"
            "后续内容会保留给辅导员查看。"
            "\n\n"
            "如果你现在有立即伤害自己的危险，"
            "请不要独自待着，尽快联系身边"
            "可信任的人，并寻求现实中的"
            "紧急帮助。"
        )

    else:
        answer = (
            "当前会话已经转由人工辅导员"
            "跟进。"
            "\n\n"
            "你可以继续在这里发送消息，"
            "后续内容会保留给辅导员查看。"
        )

    answer = format_wechat_text(
        answer
    )

    answer = truncate_wechat_reply(
        answer
    )

    client = get_wechat_client()

    client.send_text_message(
        open_id=open_id,
        content=answer,
    )

    print(
        "[HUMAN HANDOFF REPLY] "
        f"user={open_id} "
        f"status={handoff_status}"
    )

    print(
        "[RQ DONE] "
        f"user={open_id}"
    )

    return {
        "success": True,
        "open_id": open_id,
        "intent": "counseling",
        "safety_level": None,
        "handoff_status": handoff_status,
        "ai_bypassed": True,
    }


# ============================================================
# WeChat Job
# ============================================================


def process_wechat_message(
    open_id: str,
    content: str,
) -> dict[str, Any]:
    """
    处理一条微信消息。

    普通状态：
        AI
        -> 格式化
        -> 长度保护
        -> 微信发送
        -> 保存会话历史
        -> Job FINISHED

    HUMAN_PENDING / HUMAN_ACTIVE：
        不调用 AI
        -> 保存学生新消息
        -> 发送人工跟进提示
        -> Job FINISHED

    微信发送成功后，如果仅仅是
    ConversationStore 保存失败，
    不让整个 Job Retry。

    否则可能造成重复回复。
    """

    print(
        "[RQ START] "
        f"user={open_id} "
        f"question={content}"
    )

    # ========================================================
    # 1. Human Handoff Check
    # ========================================================

    handoff_service = (
        get_handoff_service()
    )

    handoff_status = (
        handoff_service.get_status(
            open_id
        )
    )

    print(
        "[HANDOFF CHECK] "
        f"user={open_id} "
        f"status={handoff_status}"
    )

    # ========================================================
    # 2. Human-controlled Conversation
    # ========================================================

    if handoff_status in {
        HandoffService.HUMAN_PENDING,
        HandoffService.HUMAN_ACTIVE,
    }:
        return (
            process_human_handoff_message(
                open_id=open_id,
                content=content,
                handoff_status=(
                    handoff_status
                ),
            )
        )

    # ========================================================
    # 3. Normal AI Processing
    # ========================================================

    service = get_assistant_service()

    client = get_wechat_client()

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

    # ========================================================
    # 4. WeChat Text Formatting
    # ========================================================

    answer = format_wechat_text(
        answer
    )

    if not answer:
        raise RuntimeError(
            "AI returned an empty answer."
        )

    # ========================================================
    # 5. WeChat Length Protection
    # ========================================================

    answer = truncate_wechat_reply(
        answer
    )

    # ========================================================
    # 6. Send
    # ========================================================

    client.send_text_message(
        open_id=open_id,
        content=answer,
    )

    # ========================================================
    # 7. Conversation History
    # ========================================================

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
    # 8. Done
    # ========================================================

    final_handoff_status = (
        handoff_service.get_status(
            open_id
        )
    )

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
        "handoff_status": (
            final_handoff_status
        ),
        "ai_bypassed": False,
    }