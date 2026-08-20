import hashlib
import hmac
import os
import xml.etree.ElementTree as ET

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import PlainTextResponse

from src.services.assistant_service import (
    AssistantService,
)
from src.wechat.client import WeChatClient


load_dotenv()


router = APIRouter()


# ============================================================
# Shared WeChat Client
# ============================================================


wechat_client = WeChatClient()


# ============================================================
# Token / Signature
# ============================================================


def get_wechat_token() -> str:
    token = os.getenv("WECHAT_TOKEN")

    if not token:
        raise RuntimeError(
            "没有找到 WECHAT_TOKEN，"
            "请检查项目根目录下的 .env 文件。"
        )

    return token


def verify_wechat_signature(
    signature: str,
    timestamp: str,
    nonce: str,
) -> bool:
    token = get_wechat_token()

    values = [
        token,
        timestamp,
        nonce,
    ]

    values.sort()

    raw_text = "".join(values)

    calculated_signature = hashlib.sha1(
        raw_text.encode("utf-8")
    ).hexdigest()

    return hmac.compare_digest(
        calculated_signature,
        signature,
    )


# ============================================================
# GET /wechat
# 微信服务器配置验证
# ============================================================


@router.get(
    "/wechat",
    response_class=PlainTextResponse,
)
def verify_wechat_server(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
):
    valid = verify_wechat_signature(
        signature=signature,
        timestamp=timestamp,
        nonce=nonce,
    )

    if not valid:
        raise HTTPException(
            status_code=403,
            detail="Invalid WeChat signature.",
        )

    return echostr


# ============================================================
# XML Parser
# ============================================================


def parse_wechat_xml(
    raw_xml: bytes,
) -> dict[str, str]:
    try:
        root = ET.fromstring(
            raw_xml.decode("utf-8")
        )
    except (
        ET.ParseError,
        UnicodeDecodeError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid WeChat XML.",
        ) from exc

    data: dict[str, str] = {}

    for child in root:
        data[child.tag] = (
            child.text or ""
        ).strip()

    return data


# ============================================================
# Background Worker
# ============================================================


def process_wechat_text_message(
    service: AssistantService,
    open_id: str,
    content: str,
) -> None:
    """
    后台处理微信文本消息。

    1. 调用 AI 辅导员
    2. 获取回答
    3. 使用客服消息接口主动发送给用户
    """
    try:
        print(
            f"[WECHAT PROCESS] "
            f"{open_id}: {content}"
        )

        result = service.handle_question(
            content
        )

        answer = result.get(
            "answer",
            "",
        ).strip()

        if not answer:
            answer = (
                "暂时没有生成有效回答，"
                "请稍后再试。"
            )

        # 微信文本消息长度保护
        max_length = 1800

        if len(answer) > max_length:
            answer = (
                answer[:max_length]
                + "\n\n（回答较长，已截断。）"
            )

        wechat_client.send_text_message(
            open_id=open_id,
            content=answer,
        )

    except Exception as exc:
        print(
            "[WECHAT ERROR] "
            f"{type(exc).__name__}: {exc}"
        )

        # 后台任务出错时尝试给用户一个兜底提示
        try:
            wechat_client.send_text_message(
                open_id=open_id,
                content=(
                    "AI 辅导员暂时无法处理这个问题，"
                    "请稍后再试。"
                ),
            )
        except Exception as send_exc:
            print(
                "[WECHAT SEND ERROR] "
                f"{type(send_exc).__name__}: "
                f"{send_exc}"
            )


# ============================================================
# POST /wechat
# 接收微信公众号消息
# ============================================================


@router.post(
    "/wechat",
    response_class=PlainTextResponse,
)
async def receive_wechat_message(
    request: Request,
    background_tasks: BackgroundTasks,
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
):
    # --------------------------------------------------------
    # 1. 验证微信签名
    # --------------------------------------------------------

    valid = verify_wechat_signature(
        signature=signature,
        timestamp=timestamp,
        nonce=nonce,
    )

    if not valid:
        raise HTTPException(
            status_code=403,
            detail="Invalid WeChat signature.",
        )

    # --------------------------------------------------------
    # 2. 读取并解析 XML
    # --------------------------------------------------------

    raw_xml = await request.body()

    message = parse_wechat_xml(
        raw_xml
    )

    msg_type = message.get(
        "MsgType",
        "",
    )

    from_user = message.get(
        "FromUserName",
        "",
    )

    # --------------------------------------------------------
    # 3. 非文本消息
    # --------------------------------------------------------

    if msg_type != "text":
        if from_user:
            background_tasks.add_task(
                wechat_client.send_text_message,
                from_user,
                (
                    "目前 AI 辅导员暂时只支持文字消息，"
                    "请直接发送文字问题。"
                ),
            )

        # 立即告诉微信服务器已成功接收
        return "success"

    # --------------------------------------------------------
    # 4. 文本消息
    # --------------------------------------------------------

    content = message.get(
        "Content",
        "",
    ).strip()

    if not content:
        return "success"

    print(
        f"[WECHAT RECEIVE] "
        f"{from_user}: {content}"
    )

    # --------------------------------------------------------
    # 5. 获取共享 AssistantService
    # --------------------------------------------------------

    service = getattr(
        request.app.state,
        "assistant_service",
        None,
    )

    if service is None:
        print(
            "[WECHAT ERROR] "
            "Assistant service is not ready."
        )

        return "success"

    if not isinstance(
        service,
        AssistantService,
    ):
        print(
            "[WECHAT ERROR] "
            "Invalid assistant service."
        )

        return "success"

    # --------------------------------------------------------
    # 6. 加入后台任务
    #
    # 关键：
    # 不在当前微信请求中等待 DeepSeek / RAG。
    # --------------------------------------------------------

    background_tasks.add_task(
        process_wechat_text_message,
        service,
        from_user,
        content,
    )

    # --------------------------------------------------------
    # 7. 立即返回 success
    # --------------------------------------------------------

    return "success"