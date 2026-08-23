import json
import uuid
from datetime import datetime, timezone
from typing import Any

from src.queue.connection import (
    redis_connection,
)


class AlertService:
    """
    高风险告警服务。

    Redis 数据结构：

    单条告警：
        counselor:alert:{alert_id}

    待处理告警 ID 列表：
        counselor:alerts:pending
    """

    ALERT_PREFIX = "counselor:alert:"
    PENDING_KEY = "counselor:alerts:pending"

    def __init__(self) -> None:
        self.redis = redis_connection

    # ========================================================
    # Create
    # ========================================================

    def create_alert(
        self,
        user_id: str,
        message: str,
        risk_level: str,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        创建一条风险告警。
        """

        alert_id = str(
            uuid.uuid4()
        )

        now = datetime.now(
            timezone.utc
        ).isoformat()

        alert = {
            "id": alert_id,
            "user_id": user_id,
            "conversation_id": (
                conversation_id
                or user_id
            ),
            "risk_level": risk_level,
            "message": message,
            "status": "pending",
            "created_at": now,
            "accepted_at": None,
            "resolved_at": None,
        }

        # ----------------------------------------------------
        # 保存告警详情
        # ----------------------------------------------------

        self.redis.set(
            self.ALERT_PREFIX
            + alert_id,
            json.dumps(
                alert,
                ensure_ascii=False,
            ),
        )

        # ----------------------------------------------------
        # 加入待处理告警列表
        # ----------------------------------------------------

        self.redis.rpush(
            self.PENDING_KEY,
            alert_id,
        )

        print(
            "[ALERT CREATED] "
            f"id={alert_id} "
            f"user={user_id} "
            f"risk={risk_level}"
        )

        return alert

    # ========================================================
    # Get
    # ========================================================

    def get_alert(
        self,
        alert_id: str,
    ) -> dict[str, Any] | None:
        """
        根据 alert_id 获取单条告警。
        """

        raw = self.redis.get(
            self.ALERT_PREFIX
            + alert_id
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

    # ========================================================
    # List Pending
    # ========================================================

    def list_pending_alerts(
        self,
    ) -> list[dict[str, Any]]:
        """
        获取所有 pending 状态告警。

        新告警排在前面。
        """

        raw_ids = self.redis.lrange(
            self.PENDING_KEY,
            0,
            -1,
        )

        alerts: list[
            dict[str, Any]
        ] = []

        for raw_id in raw_ids:
            if isinstance(
                raw_id,
                bytes,
            ):
                alert_id = (
                    raw_id.decode(
                        "utf-8"
                    )
                )
            else:
                alert_id = str(
                    raw_id
                )

            alert = self.get_alert(
                alert_id
            )

            if alert is None:
                continue

            if (
                alert.get(
                    "status"
                )
                != "pending"
            ):
                continue

            alerts.append(
                alert
            )

        alerts.sort(
            key=lambda item: (
                item.get(
                    "created_at",
                    "",
                )
            ),
            reverse=True,
        )

        return alerts
    def list_open_alerts(
        self,
    ) -> list[dict[str, Any]]:
        """
        获取所有尚未完成处理的告警。

        包括：
            pending
            accepted

        不包括：
            resolved
        """

        raw_ids = self.redis.lrange(
            self.PENDING_KEY,
            0,
            -1,
        )

        alerts: list[
            dict[str, Any]
        ] = []

        for raw_id in raw_ids:
            if isinstance(
                raw_id,
                bytes,
            ):
                alert_id = (
                    raw_id.decode(
                        "utf-8"
                    )
                )
            else:
                alert_id = str(
                    raw_id
                )

            alert = self.get_alert(
                alert_id
            )

            if alert is None:
                continue

            status = alert.get(
                "status"
            )

            if status not in {
                "pending",
                "accepted",
            }:
                continue

            alerts.append(
                alert
            )

        alerts.sort(
            key=lambda item: (
                item.get(
                    "created_at",
                    "",
                )
            ),
            reverse=True,
        )

        return alerts
        
    # ========================================================
    # Update Status
    # ========================================================

    def update_status(
        self,
        alert_id: str,
        status: str,
    ) -> dict[str, Any]:
        """
        修改告警状态。

        支持：
            pending
            accepted
            resolved
        """

        allowed_statuses = {
            "pending",
            "accepted",
            "resolved",
        }

        if status not in allowed_statuses:
            raise ValueError(
                "不支持的告警状态："
                f"{status}"
            )

        alert = self.get_alert(
            alert_id
        )

        if alert is None:
            raise KeyError(
                "找不到告警："
                f"{alert_id}"
            )

        now = datetime.now(
            timezone.utc
        ).isoformat()

        alert["status"] = status

        if status == "accepted":
            alert["accepted_at"] = now

        elif status == "resolved":
            alert["resolved_at"] = now

        self.redis.set(
            self.ALERT_PREFIX
            + alert_id,
            json.dumps(
                alert,
                ensure_ascii=False,
            ),
        )

        print(
            "[ALERT STATUS] "
            f"id={alert_id} "
            f"status={status}"
        )

        return alert

    # ========================================================
    # Convenience Methods
    # ========================================================

    def accept_alert(
        self,
        alert_id: str,
    ) -> dict[str, Any]:
        """
        辅导员接入告警。
        """

        return self.update_status(
            alert_id=alert_id,
            status="accepted",
        )

    def resolve_alert(
        self,
        alert_id: str,
    ) -> dict[str, Any]:
        """
        辅导员完成处理。
        """

        return self.update_status(
            alert_id=alert_id,
            status="resolved",
        )