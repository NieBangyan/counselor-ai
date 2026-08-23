from src.alerts.alert_service import (
    AlertService,
)


def main() -> None:
    service = AlertService()

    print("=" * 70)
    print("1. 创建告警")

    alert = service.create_alert(
        user_id="test_student_001",
        message="我现在准备伤害自己。",
        risk_level="crisis",
        conversation_id="test_conversation_001",
    )

    alert_id = alert["id"]

    print(
        "alert_id:",
        alert_id,
    )

    print(
        "status:",
        alert["status"],
    )

    print()

    print("=" * 70)
    print("2. 读取告警")

    loaded = service.get_alert(
        alert_id
    )

    print(
        loaded
    )

    print()

    print("=" * 70)
    print("3. 查询待处理告警")

    pending = (
        service.list_pending_alerts()
    )

    print(
        "pending count:",
        len(pending),
    )

    for item in pending:
        print(
            item["id"],
            item["risk_level"],
            item["status"],
            item["message"],
        )

    print()

    print("=" * 70)
    print("4. 辅导员接入")

    accepted = (
        service.accept_alert(
            alert_id
        )
    )

    print(
        "status:",
        accepted["status"],
    )

    print(
        "accepted_at:",
        accepted["accepted_at"],
    )

    print()

    print("=" * 70)
    print("5. 标记已处理")

    resolved = (
        service.resolve_alert(
            alert_id
        )
    )

    print(
        "status:",
        resolved["status"],
    )

    print(
        "resolved_at:",
        resolved["resolved_at"],
    )

    print()

    print("=" * 70)
    print("6. 再查询 pending")

    pending_after = (
        service.list_pending_alerts()
    )

    exists = any(
        item["id"] == alert_id
        for item in pending_after
    )

    print(
        "测试告警仍在 pending:",
        exists,
    )


if __name__ == "__main__":
    main()