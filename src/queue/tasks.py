from typing import Any

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


def get_assistant_service() -> AssistantService:
    """
    每个 RQ Worker 进程只初始化一次 AssistantService。

    后续该 Worker 处理其他任务时继续复用，
    避免每条微信消息都重新加载 Retriever、
    Embedding Model 等组件。
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
    每个 Worker 复用一个 WeChatClient，
    从而复用 access_token 缓存。
    """
    global _wechat_client

    if _wechat_client is None:
        _wechat_client = (
            WeChatClient()
        )

    return _wechat_client


# ============================================================
# WeChat Job
# ============================================================


def process_wechat_message(
    open_id: str,
    content: str,
) -> dict[str, Any]:
    """
    处理一条微信消息。

    Redis / RQ 负责：
        排队
        分配 Worker
        保存任务状态

    当前 Worker 负责：
        AI 处理
        微信主动回复
    """

    print(
        f"[RQ START] "
        f"user={open_id} "
        f"question={content}"
    )

    try:
        service = (
            get_assistant_service()
        )

        client = (
            get_wechat_client()
        )

        # ----------------------------------------------------
        # AI
        # ----------------------------------------------------

        result = (
            service.handle_question(
                content
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
            answer = (
                "暂时没有生成有效回答，"
                "请稍后再试。"
            )

        # ----------------------------------------------------
        # WeChat length protection
        # ----------------------------------------------------

        max_length = 1800

        if len(answer) > max_length:
            answer = (
                answer[:max_length]
                + "\n\n"
                "（回答较长，已截断。）"
            )

        # ----------------------------------------------------
        # Send
        # ----------------------------------------------------

        client.send_text_message(
            open_id=open_id,
            content=answer,
        )

        print(
            f"[RQ DONE] "
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

    except Exception as exc:
        print(
            f"[RQ ERROR] "
            f"user={open_id} "
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        # 尽量给用户发送失败提示
        try:
            client = (
                get_wechat_client()
            )

            client.send_text_message(
                open_id=open_id,
                content=(
                    "AI 辅导员暂时无法处理"
                    "这个问题，请稍后再试。"
                ),
            )

        except Exception as send_exc:
            print(
                f"[RQ SEND ERROR] "
                f"user={open_id} "
                f"{type(send_exc).__name__}: "
                f"{send_exc}"
            )

        
        raise