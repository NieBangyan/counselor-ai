from src.queue.connection import (
    redis_connection,
)


# 微信重复消息去重时间
# 24 小时足够覆盖微信服务器的重复投递场景。
WECHAT_MESSAGE_DEDUP_TTL = 86400


def claim_wechat_message(
    msg_id: str,
) -> bool:
    """
    尝试声明一条微信消息。

    返回：
        True
            第一次收到，可以继续处理。

        False
            已经处理/接收过，是重复消息。

    Redis:
        SET key value NX EX ttl

    SET + NX + EX 是一次原子操作，
    即使同时收到两个相同 MsgId，
    也只有一个请求能成功。
    """

    if not msg_id:
        # 没有 MsgId 时暂时不做去重，
        # 避免误杀正常消息。
        return True

    key = (
        f"wechat:message:{msg_id}"
    )

    claimed = redis_connection.set(
        key,
        "1",
        nx=True,
        ex=WECHAT_MESSAGE_DEDUP_TTL,
    )

    return bool(claimed)