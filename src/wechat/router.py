import hashlib
import hmac
import os
import xml.etree.ElementTree as ET

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import PlainTextResponse

from src.queue.connection import wechat_queue
from src.queue.tasks import process_wechat_message


load_dotenv()


router = APIRouter()


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
# POST /wechat
# ============================================================


@router.post(
    "/wechat",
    response_class=PlainTextResponse,
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

    # --------------------------------------------------------
    # 3. 只处理文本消息
    # --------------------------------------------------------

    if msg_type != "text":
        print(
            f"[WECHAT IGNORE] "
            f"user={from_user} "
            f"type={msg_type}"
        )

        return "success"

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
    # 4. 加入 Redis / RQ
    # --------------------------------------------------------

    try:
        job = wechat_queue.enqueue(
            process_wechat_message,
            from_user,
            content,
            job_timeout=180,
            result_ttl=500,
            failure_ttl=86400,
        )

        print(
            f"[WECHAT ENQUEUE] "
            f"user={from_user} "
            f"job={job.id}"
        )

    except Exception as exc:
        print(
            f"[WECHAT QUEUE ERROR] "
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        # 即使 Redis 临时出错，
        # 也先正常响应微信服务器，
        # 防止微信不断重试同一请求。
        return "success"

    # --------------------------------------------------------
    # 5. 立即回复微信服务器
    # --------------------------------------------------------

    return "success"