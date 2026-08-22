from src.conversation.store import (
    ConversationStore,
)


def test_conversation_store(
    redis_connection,
):
    store = ConversationStore()

    conversation_id = (
        "pytest-conversation-001"
    )

    key = (
        f"conversation:"
        f"{conversation_id}"
    )

    redis_connection.delete(
        key
    )

    try:
        store.append(
            conversation_id,
            "user",
            "最近学习压力很大",
        )

        store.append(
            conversation_id,
            "assistant",
            "最近主要是哪方面压力比较大？",
        )

        history = (
            store.get_history(
                conversation_id
            )
        )

        assert len(history) == 2

        assert history[0] == {
            "role": "user",
            "content": "最近学习压力很大",
        }

        assert history[1] == {
            "role": "assistant",
            "content": (
                "最近主要是哪方面压力比较大？"
            ),
        }

        ttl = redis_connection.ttl(
            key
        )

        assert ttl > 0
        assert ttl <= 1800

    finally:
        redis_connection.delete(
            key
        )
def test_conversation_store_trims_old_messages(
    redis_connection,
):
    store = ConversationStore()

    conversation_id = (
        "pytest-conversation-trim-001"
    )

    key = (
        f"conversation:{conversation_id}"
    )

    redis_connection.delete(key)

    try:
        # 写入 8 条消息
        for index in range(8):
            role = (
                "user"
                if index % 2 == 0
                else "assistant"
            )

            store.append(
                conversation_id,
                role,
                f"message-{index}",
            )

        history = store.get_history(
            conversation_id
        )

        # 最多只能留下 6 条
        assert len(history) == 6

        # message-0 / message-1
        # 应该已经被裁掉
        assert history[0]["content"] == (
            "message-2"
        )

        assert history[-1]["content"] == (
            "message-7"
        )

    finally:
        redis_connection.delete(key)