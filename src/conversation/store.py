import json

from src.queue.connection import (
    redis_connection,
)


CONVERSATION_TTL = 1800
MAX_MESSAGES = 6


class ConversationStore:
    """
    Redis 短期会话存储。

    每个 conversation_id 独立保存最近几条消息。
    """

    def _key(
        self,
        conversation_id: str,
    ) -> str:
        return (
            f"conversation:{conversation_id}"
        )

    def get_history(
        self,
        conversation_id: str,
    ) -> list[dict[str, str]]:
        if not conversation_id:
            return []

        key = self._key(
            conversation_id
        )

        raw_messages = (
            redis_connection.lrange(
                key,
                0,
                -1,
            )
        )

        history: list[
            dict[str, str]
        ] = []

        for raw in raw_messages:
            try:
                item = json.loads(
                    raw.decode("utf-8")
                )
            except (
                json.JSONDecodeError,
                UnicodeDecodeError,
            ):
                continue

            role = item.get("role")
            content = item.get("content")

            if (
                role
                not in {
                    "user",
                    "assistant",
                }
            ):
                continue

            if not isinstance(
                content,
                str,
            ):
                continue

            history.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        return history

    def append(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:
        if not conversation_id:
            return

        if role not in {
            "user",
            "assistant",
        }:
            raise ValueError(
                "Invalid conversation role."
            )

        content = content.strip()

        if not content:
            return

        key = self._key(
            conversation_id
        )

        value = json.dumps(
            {
                "role": role,
                "content": content,
            },
            ensure_ascii=False,
        )

        pipeline = (
            redis_connection.pipeline()
        )

        pipeline.rpush(
            key,
            value,
        )

        # 只保留最近 6 条
        pipeline.ltrim(
            key,
            -MAX_MESSAGES,
            -1,
        )

        # 每次对话刷新 30 分钟 TTL
        pipeline.expire(
            key,
            CONVERSATION_TTL,
        )

        pipeline.execute()

    def clear(
        self,
        conversation_id: str,
    ) -> None:
        if not conversation_id:
            return

        redis_connection.delete(
            self._key(
                conversation_id
            )
        )