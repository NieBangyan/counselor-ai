from src.wechat.dedup import (
    claim_wechat_message,
)


def test_wechat_message_dedup(
    redis_connection,
):
    msg_id = (
        "pytest-wechat-dedup-001"
    )

    key = (
        f"wechat:message:{msg_id}"
    )

    # 测试前确保不存在
    redis_connection.delete(
        key
    )

    try:
        # 第一次应该成功
        first = claim_wechat_message(
            msg_id
        )

        # 第二次相同 MsgId
        # 应该被识别为重复消息
        second = claim_wechat_message(
            msg_id
        )

        assert first is True
        assert second is False

        # 确认存在 TTL，
        # 防止 Redis 永久积累。
        ttl = redis_connection.ttl(
            key
        )

        assert ttl > 0
        assert ttl <= 86400

    finally:
        redis_connection.delete(
            key
        )