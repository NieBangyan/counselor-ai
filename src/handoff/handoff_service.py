import json
from datetime import datetime, timezone
from typing import Any

from src.queue.connection import (
    redis_connection,
)


class HandoffService:
    """
    人工接管状态管理。

    每个 conversation_id 对应一个接管状态：

        AI
        HUMAN_PENDING
        HUMAN_ACTIVE
        RESOLVED
    """

    HANDOFF_PREFIX = "counselor:handoff:"

    AI = "AI"
    HUMAN_PENDING = "HUMAN_PENDING"
    HUMAN_ACTIVE = "HUMAN_ACTIVE"
    RESOLVED = "RESOLVED"

    def __init__(self) -> None:
        self.redis = redis_connection

    def _get_key(
        self,
        conversation_id: str,
    ) -> str:
        return (
            self.HANDOFF_PREFIX
            + conversation_id
        )

    def _now(self) -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    # ========================================================
    # Get
    # ========================================================

    def get_handoff(
        self,
        conversation_id: str,
    ) -> dict[str, Any] | None:
        raw = self.redis.get(
            self._get_key(
                conversation_id
            )
        )

        if not raw:
            return None

        if isinstance(
            raw,
            bytes,
        ):
            raw = raw.decode(
                "utf-8"
            )

        return json.loads(
            raw
        )

    def get_status(
        self,
        conversation_id: str,
    ) -> str:
        handoff = self.get_handoff(
            conversation_id
        )

        if handoff is None:
            return self.AI

        return str(
            handoff.get(
                "status",
                self.AI,
            )
        )

    # ========================================================
    # Save
    # ========================================================

    def _save(
        self,
        handoff: dict[str, Any],
    ) -> None:
        conversation_id = str(
            handoff["conversation_id"]
        )

        self.redis.set(
            self._get_key(
                conversation_id
            ),
            json.dumps(
                handoff,
                ensure_ascii=False,
            ),
        )

    # ========================================================
    # Crisis -> Human Pending
    # ========================================================

    def request_handoff(
        self,
        conversation_id: str,
        alert_id: str,
        reason: str = "crisis",
    ) -> dict[str, Any]:
        """
        高风险事件发生后，
        将会话标记为等待人工接入。
        """

        now = self._now()

        handoff = {
            "conversation_id": (
                conversation_id
            ),
            "alert_id": alert_id,
            "reason": reason,
            "status": (
                self.HUMAN_PENDING
            ),
            "created_at": now,
            "accepted_at": None,
            "resolved_at": None,
        }

        self._save(
            handoff
        )

        print(
            "[HANDOFF REQUESTED] "
            f"conversation={conversation_id} "
            f"alert={alert_id} "
            f"status={self.HUMAN_PENDING}"
        )

        return handoff

    # ========================================================
    # Counselor Accept
    # ========================================================

    def accept_handoff(
        self,
        conversation_id: str,
    ) -> dict[str, Any]:
        handoff = self.get_handoff(
            conversation_id
        )

        if handoff is None:
            raise KeyError(
                "找不到人工接管记录："
                f"{conversation_id}"
            )

        handoff["status"] = (
            self.HUMAN_ACTIVE
        )

        handoff["accepted_at"] = (
            self._now()
        )

        self._save(
            handoff
        )

        print(
            "[HANDOFF ACCEPTED] "
            f"conversation={conversation_id}"
        )

        return handoff

    # ========================================================
    # Resolve
    # ========================================================

    def resolve_handoff(
        self,
        conversation_id: str,
    ) -> dict[str, Any]:
        handoff = self.get_handoff(
            conversation_id
        )

        if handoff is None:
            raise KeyError(
                "找不到人工接管记录："
                f"{conversation_id}"
            )

        handoff["status"] = (
            self.RESOLVED
        )

        handoff["resolved_at"] = (
            self._now()
        )

        self._save(
            handoff
        )

        print(
            "[HANDOFF RESOLVED] "
            f"conversation={conversation_id}"
        )

        return handoff

    # ========================================================
    # Helpers
    # ========================================================

    def is_human_pending(
        self,
        conversation_id: str,
    ) -> bool:
        return (
            self.get_status(
                conversation_id
            )
            == self.HUMAN_PENDING
        )

    def is_human_active(
        self,
        conversation_id: str,
    ) -> bool:
        return (
            self.get_status(
                conversation_id
            )
            == self.HUMAN_ACTIVE
        )

    def requires_human(
        self,
        conversation_id: str,
    ) -> bool:
        status = self.get_status(
            conversation_id
        )

        return status in {
            self.HUMAN_PENDING,
            self.HUMAN_ACTIVE,
        }