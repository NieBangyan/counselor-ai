from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
)
from pydantic import (
    BaseModel,
    Field,
)

from src.alerts.alert_service import (
    AlertService,
)
from src.conversation.store import (
    ConversationStore,
)
from src.handoff.handoff_service import (
    HandoffService,
)
from src.wechat.client import (
    WeChatClient,
)
from src.wechat.text_formatter import (
    format_wechat_text,
)


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


# ============================================================
# Services
# ============================================================


alert_service = AlertService()
handoff_service = HandoffService()
conversation_store = ConversationStore()
wechat_client = WeChatClient()


# ============================================================
# Request Models
# ============================================================


class HumanMessageRequest(BaseModel):
    content: str = Field(
        ...,
        min_length=1,
        max_length=1800,
        description="辅导员发送给学生的消息",
    )


# ============================================================
# Helpers
# ============================================================


def build_alert_response(
    alert: dict[str, Any],
) -> dict[str, Any]:
    """
    给告警附加当前人工接管状态。

    注意：
        同一个 conversation 可能存在历史 Alert。

        因此除了 handoff_status，
        还返回当前 handoff_alert_id，
        方便判断当前 Handoff 到底属于哪条 Alert。
    """

    conversation_id = str(
        alert.get(
            "conversation_id",
            "",
        )
    )

    handoff_status = "AI"
    handoff_alert_id = None
    is_current_handoff = False

    if conversation_id:
        handoff = (
            handoff_service.get_handoff(
                conversation_id
            )
        )

        if handoff:
            handoff_status = str(
                handoff.get(
                    "status",
                    "AI",
                )
            )

            handoff_alert_id = (
                handoff.get(
                    "alert_id"
                )
            )

            is_current_handoff = (
                str(handoff_alert_id)
                == str(
                    alert.get(
                        "id",
                        "",
                    )
                )
            )

    return {
        **alert,
        "handoff_status": (
            handoff_status
        ),
        "handoff_alert_id": (
            handoff_alert_id
        ),
        "is_current_handoff": (
            is_current_handoff
        ),
    }


def get_alert_or_404(
    alert_id: str,
) -> dict[str, Any]:
    """
    根据 alert_id 获取告警。
    """

    alert = alert_service.get_alert(
        alert_id
    )

    if alert is None:
        raise HTTPException(
            status_code=404,
            detail="Alert not found.",
        )

    return alert


def get_matching_handoff(
    alert_id: str,
    conversation_id: str,
) -> dict[str, Any]:
    """
    获取与当前 Alert 对应的 Handoff。

    这是 Alert / Handoff 一致性保护。

    防止出现：

        Alert A
        +
        Handoff B

    被错误地一起 accept / resolve。
    """

    handoff = (
        handoff_service.get_handoff(
            conversation_id
        )
    )

    if handoff is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "This alert has no "
                "handoff record."
            ),
        )

    handoff_alert_id = str(
        handoff.get(
            "alert_id",
            "",
        )
    )

    if handoff_alert_id != alert_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "This alert is stale. "
                "The current handoff belongs "
                "to another alert. "
                f"Requested alert_id: "
                f"{alert_id}. "
                f"Current handoff alert_id: "
                f"{handoff_alert_id}."
            ),
        )

    return handoff


# ============================================================
# GET /admin/alerts
# ============================================================


@router.get(
    "/alerts",
)
def list_alerts() -> dict[str, Any]:
    """
    查看所有待处理高风险告警。
    """

    alerts = (
        alert_service
        .list_open_alerts()
    )

    return {
        "count": len(alerts),
        "alerts": [
            build_alert_response(
                alert
            )
            for alert in alerts
        ],
    }


# ============================================================
# GET /admin/alerts/{alert_id}
# ============================================================


@router.get(
    "/alerts/{alert_id}",
)
def get_alert(
    alert_id: str,
) -> dict[str, Any]:
    """
    查看单条告警详情。
    """

    alert = get_alert_or_404(
        alert_id
    )

    return build_alert_response(
        alert
    )


# ============================================================
# POST /admin/alerts/{alert_id}/accept
# ============================================================


@router.post(
    "/alerts/{alert_id}/accept",
)
def accept_alert(
    alert_id: str,
) -> dict[str, Any]:
    """
    辅导员接入高风险会话。

    Alert:
        pending -> accepted

    Handoff:
        HUMAN_PENDING -> HUMAN_ACTIVE

    必须保证：
        alert.id == handoff.alert_id
    """

    alert = get_alert_or_404(
        alert_id
    )

    conversation_id = str(
        alert.get(
            "conversation_id",
            "",
        )
    )

    if not conversation_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Alert has no "
                "conversation_id."
            ),
        )

    alert_status = str(
        alert.get(
            "status",
            "",
        )
    )

    if alert_status == "resolved":
        raise HTTPException(
            status_code=409,
            detail=(
                "Resolved alert cannot "
                "be accepted."
            ),
        )

    # ========================================================
    # Alert / Handoff consistency check
    # ========================================================

    current_handoff = (
        get_matching_handoff(
            alert_id=alert_id,
            conversation_id=(
                conversation_id
            ),
        )
    )

    current_status = str(
        current_handoff.get(
            "status",
            "",
        )
    )

    # --------------------------------------------------------
    # 已经接入：幂等返回
    # --------------------------------------------------------

    if (
        alert_status == "accepted"
        and current_status
        == "HUMAN_ACTIVE"
    ):
        return {
            "success": True,
            "already_accepted": True,
            "alert": alert,
            "handoff": (
                current_handoff
            ),
        }

    # --------------------------------------------------------
    # 只允许 HUMAN_PENDING -> HUMAN_ACTIVE
    # --------------------------------------------------------

    if current_status != "HUMAN_PENDING":
        raise HTTPException(
            status_code=409,
            detail=(
                "Handoff cannot be "
                "accepted from current "
                "status: "
                f"{current_status}"
            ),
        )

    try:
        updated_handoff = (
            handoff_service
            .accept_handoff(
                conversation_id
            )
        )

        updated_alert = (
            alert_service
            .accept_alert(
                alert_id
            )
        )

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return {
        "success": True,
        "already_accepted": False,
        "alert": updated_alert,
        "handoff": (
            updated_handoff
        ),
    }


# ============================================================
# POST /admin/alerts/{alert_id}/resolve
# ============================================================


@router.post(
    "/alerts/{alert_id}/resolve",
)
def resolve_alert(
    alert_id: str,
) -> dict[str, Any]:
    """
    辅导员完成风险事件处理。

    Alert:
        -> resolved

    Handoff:
        -> RESOLVED

    必须保证：
        alert.id == handoff.alert_id
    """

    alert = get_alert_or_404(
        alert_id
    )

    conversation_id = str(
        alert.get(
            "conversation_id",
            "",
        )
    )

    if not conversation_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Alert has no "
                "conversation_id."
            ),
        )

    # ========================================================
    # Alert / Handoff consistency check
    # ========================================================

    current_handoff = (
        get_matching_handoff(
            alert_id=alert_id,
            conversation_id=(
                conversation_id
            ),
        )
    )

    alert_status = str(
        alert.get(
            "status",
            "",
        )
    )

    handoff_status = str(
        current_handoff.get(
            "status",
            "",
        )
    )

    # --------------------------------------------------------
    # 已完成：幂等返回
    # --------------------------------------------------------

    if (
        alert_status == "resolved"
        and handoff_status
        == "RESOLVED"
    ):
        return {
            "success": True,
            "already_resolved": True,
            "alert": alert,
            "handoff": (
                current_handoff
            ),
        }

    # --------------------------------------------------------
    # 正常情况下要求辅导员已经接入
    # --------------------------------------------------------

    if handoff_status != "HUMAN_ACTIVE":
        raise HTTPException(
            status_code=409,
            detail=(
                "Handoff cannot be "
                "resolved from current "
                "status: "
                f"{handoff_status}"
            ),
        )

    try:
        updated_handoff = (
            handoff_service
            .resolve_handoff(
                conversation_id
            )
        )

        updated_alert = (
            alert_service
            .resolve_alert(
                alert_id
            )
        )

    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return {
        "success": True,
        "already_resolved": False,
        "alert": updated_alert,
        "handoff": (
            updated_handoff
        ),
    }


# ============================================================
# GET /admin/conversations/{conversation_id}
# ============================================================


@router.get(
    "/conversations/{conversation_id}",
)
def get_conversation(
    conversation_id: str,
) -> dict[str, Any]:
    """
    辅导员查看学生当前会话。

    conversation_id 在微信公众号场景下
    就是学生的 open_id。
    """

    conversation_id = (
        conversation_id.strip()
    )

    if not conversation_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Conversation ID "
                "cannot be empty."
            ),
        )

    history = (
        conversation_store.get_history(
            conversation_id
        )
    )

    handoff_status = (
        handoff_service.get_status(
            conversation_id
        )
    )

    handoff = (
        handoff_service.get_handoff(
            conversation_id
        )
    )

    return {
        "conversation_id": (
            conversation_id
        ),
        "handoff_status": (
            handoff_status
        ),
        "handoff": handoff,
        "message_count": len(
            history
        ),
        "messages": history,
    }


# ============================================================
# POST /admin/conversations/{conversation_id}/messages
# ============================================================


@router.post(
    "/conversations/{conversation_id}/messages",
)
def send_human_message(
    conversation_id: str,
    request: HumanMessageRequest,
) -> dict[str, Any]:
    """
    人工辅导员向学生发送消息。

    只有 HUMAN_ACTIVE 状态，
    辅导员才允许通过这个接口回复学生。

    流程：
        1. 检查人工接管状态
        2. 格式化文本
        3. 通过微信客服消息接口发送
        4. 保存人工回复到会话历史
    """

    conversation_id = (
        conversation_id.strip()
    )

    content = (
        request.content.strip()
    )

    if not conversation_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Conversation ID "
                "cannot be empty."
            ),
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail=(
                "Message cannot be empty."
            ),
        )

    # ========================================================
    # 1. Check Handoff
    # ========================================================

    handoff_status = (
        handoff_service.get_status(
            conversation_id
        )
    )

    if handoff_status != "HUMAN_ACTIVE":
        raise HTTPException(
            status_code=409,
            detail=(
                "Conversation is not "
                "currently controlled "
                "by a human counselor. "
                f"Current status: "
                f"{handoff_status}"
            ),
        )

    handoff = (
        handoff_service.get_handoff(
            conversation_id
        )
    )

    if handoff is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Human handoff record "
                "does not exist."
            ),
        )

    # ========================================================
    # 2. Format
    # ========================================================

    final_content = (
        format_wechat_text(
            content
        )
    )

    if not final_content:
        raise HTTPException(
            status_code=400,
            detail=(
                "Message cannot be empty."
            ),
        )

    # ========================================================
    # 3. Send to WeChat
    # ========================================================

    try:
        wechat_client.send_text_message(
            open_id=conversation_id,
            content=final_content,
        )

    except Exception as exc:
        print(
            "[HUMAN SEND ERROR] "
            f"user={conversation_id} "
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Failed to send "
                "message to WeChat."
            ),
        ) from exc

    # ========================================================
    # 4. Save Conversation
    # ========================================================

    try:
        conversation_store.append(
            conversation_id=(
                conversation_id
            ),
            role="assistant",
            content=final_content,
            intent="counseling",
            safety_level=None,
        )

        history_saved = True

        print(
            "[HUMAN MESSAGE SENT] "
            f"user={conversation_id} "
            f"alert={handoff.get('alert_id')}"
        )

    except Exception as exc:
        # 微信已经发送成功。
        # 此处不能让辅导员误以为发送失败，
        # 否则可能重复点击导致重复消息。

        history_saved = False

        print(
            "[HUMAN MESSAGE SAVE ERROR] "
            f"user={conversation_id} "
            f"{type(exc).__name__}: "
            f"{exc}"
        )

    # ========================================================
    # 5. Response
    # ========================================================

    return {
        "success": True,
        "conversation_id": (
            conversation_id
        ),
        "alert_id": (
            handoff.get(
                "alert_id"
            )
        ),
        "handoff_status": (
            handoff_status
        ),
        "content": final_content,
        "history_saved": (
            history_saved
        ),
    }
