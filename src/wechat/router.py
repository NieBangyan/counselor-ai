import hashlib
import hmac
import os
import time
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import PlainTextResponse, Response

from src.services.assistant_service import (
    AssistantService,
)


load_dotenv()


router = APIRouter()


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
# XML Helpers
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


def build_text_reply(
    to_user: str,
    from_user: str,
    content: str,
) -> str:
    """
    构造微信公众号被动文本回复 XML。

    收到消息时：
        FromUserName = 用户
        ToUserName = 公众号

    回复时必须反过来：
        ToUserName = 用户
        FromUserName = 公众号
    """
    safe_to_user = escape(to_user)
    safe_from_user = escape(from_user)
    safe_content = escape(content)

    return (
        "<xml>"
        f"<ToUserName><![CDATA[{safe_to_user}]]>"
        "</ToUserName>"
        f"<FromUserName><![CDATA[{safe_from_user}]]>"
        "</FromUserName>"
        f"<CreateTime>{int(time.time())}</CreateTime>"
        "<MsgType><![CDATA[text]]></MsgType>"
        f"<Content><![CDATA[{safe_content}]]>"
        "</Content>"
        "</xml>"
    )


# ============================================================
# POST /wechat
# 接收微信公众号消息
# ============================================================


@router.post(
    "/wechat",
)
async def receive_wechat_message(
    request: Request,
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
    # 2. 读取 XML
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

    to_user = message.get(
        "ToUserName",
        "",
    )

    # --------------------------------------------------------
    # 3. 目前只处理文本消息
    # --------------------------------------------------------

    if msg_type != "text":
        reply_text = (
            "目前 AI 辅导员暂时只支持文字消息。"
            "请直接发送文字问题。"
        )

        reply_xml = build_text_reply(
            to_user=from_user,
            from_user=to_user,
            content=reply_text,
        )

        return Response(
            content=reply_xml,
            media_type="application/xml",
        )

    content = message.get(
        "Content",
        "",
    ).strip()

    if not content:
        return PlainTextResponse(
            "success"
        )

    print(
        f"[WECHAT] {from_user}: "
        f"{content}"
    )

    # --------------------------------------------------------
    # 4. 调用现有 AI 辅导员
    # --------------------------------------------------------

    service = getattr(
        request.app.state,
        "assistant_service",
        None,
    )

    if service is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Assistant service "
                "is not ready."
            ),
        )

    if not isinstance(
        service,
        AssistantService,
    ):
        raise HTTPException(
            status_code=500,
            detail=(
                "Invalid assistant service."
            ),
        )

    result = service.handle_question(
        content
    )

    answer = result["answer"]

    # 微信单条回复不适合特别长，
    # 暂时做一个保护性截断。
    max_length = 1800

    if len(answer) > max_length:
        answer = (
            answer[:max_length]
            + "\n\n（回答较长，已截断。）"
        )

    # --------------------------------------------------------
    # 5. 返回微信要求的 XML
    # --------------------------------------------------------

    reply_xml = build_text_reply(
        to_user=from_user,
        from_user=to_user,
        content=answer,
    )

    return Response(
        content=reply_xml,
        media_type="application/xml",
    )