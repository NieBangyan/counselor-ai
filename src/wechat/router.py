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

from src.queue.user_queue import (
    enqueue_user_message,
)
from src.wechat.dedup import (
    claim_wechat_message,
)


load_dotenv()


router = APIRouter()


# ============================================================
# Token / Signature
# ============================================================


def get_wechat_token() -> str:
    token = os.getenv(
        "WECHAT_TOKEN"
    )

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
    """
    验证微信公众号服务器签名。
    """

    token = get_wechat_token()

    values = [
        token,
        timestamp,
        nonce,
    ]

    values.sort()

    raw_text = "".join(
        values
    )

    calculated_signature = (
        hashlib.sha1(
            raw_text.encode(
                "utf-8"
            )
        )
        .hexdigest()
    )

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
    """
    微信公众平台配置服务器 URL 时，
    微信服务器会调用这个接口。

    验签成功后必须原样返回 echostr。
    """

    valid = verify_wechat_signature(
        signature=signature,
        timestamp=timestamp,
        nonce=nonce,
    )

    if not valid:
        raise HTTPException(
            status_code=403,
            detail=(
                "Invalid WeChat signature."
            ),
        )

    return echostr


# ============================================================
# XML Parser
# ============================================================


def parse_wechat_xml(
    raw_xml: bytes,
) -> dict[str, str]:
    """
    将微信发送的 XML 转换成 dict。
    """

    try:
        root = ET.fromstring(
            raw_xml.decode(
                "utf-8"
            )
        )

    except (
        ET.ParseError,
        UnicodeDecodeError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid WeChat XML."
            ),
        ) from exc

    data: dict[str, str] = {}

    for child in root:
        data[child.tag] = (
            child.text or ""
        ).strip()

    return data


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
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
):
    # ========================================================
    # 1. 验证微信签名
    # ========================================================

    valid = verify_wechat_signature(
        signature=signature,
        timestamp=timestamp,
        nonce=nonce,
    )

    if not valid:
        raise HTTPException(
            status_code=403,
            detail=(
                "Invalid WeChat signature."
            ),
        )

    # ========================================================
    # 2. 读取并解析 XML
    # ========================================================

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

    # ========================================================
    # 3. 目前只处理文本消息
    # ========================================================

    if msg_type != "text":
        print(
            "[WECHAT IGNORE] "
            f"user={from_user} "
            f"type={msg_type}"
        )

        return "success"

    # ========================================================
    # 4. 提取文本内容
    # ========================================================

    content = (
        message.get(
            "Content",
            "",
        )
        .strip()
    )

    if not content:
        return "success"

    # ========================================================
    # 5. MsgId 去重
    # ========================================================

    msg_id = (
        message.get(
            "MsgId",
            "",
        )
        .strip()
    )

    if msg_id:
        claimed = claim_wechat_message(
            msg_id
        )

        if not claimed:
            print(
                "[WECHAT DUPLICATE] "
                f"user={from_user} "
                f"msg_id={msg_id}"
            )

            # 告诉微信服务器消息已经收到，
            # 防止继续重复投递。
            return "success"

    # ========================================================
    # 6. 记录接收到的消息
    # ========================================================

    print(
        "[WECHAT RECEIVE] "
        f"user={from_user} "
        f"msg_id={msg_id} "
        f"content={content}"
    )

    # ========================================================
    # 7. 加入 Redis / RQ 队列
    # ========================================================

    try:
        job = enqueue_user_message(
            open_id=from_user,
            content=content,
        )

        print(
            "[WECHAT ENQUEUE] "
            f"user={from_user} "
            f"msg_id={msg_id} "
            f"job={job.id}"
        )

    except Exception as exc:
        print(
            "[WECHAT QUEUE ERROR] "
            f"user={from_user} "
            f"msg_id={msg_id} "
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        # 即使 Redis / RQ 暂时异常，
        # 也返回 success。
        #
        # 否则微信服务器可能重复 POST，
        # 造成重复消息风暴。
        return "success"

    # ========================================================
    # 8. 立即回复微信服务器
    # ========================================================

    return "success"