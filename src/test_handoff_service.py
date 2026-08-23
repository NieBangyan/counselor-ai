from src.handoff.handoff_service import (
    HandoffService,
)



def main() -> None:
    service = HandoffService()

    conversation_id = (
        "test_student_handoff_001"
    )

    print("=" * 70)
    print("1. 默认状态")

    print(
        service.get_status(
            conversation_id
        )
    )

    print("=" * 70)
    print("2. 请求人工接管")

    handoff = service.request_handoff(
        conversation_id=conversation_id,
        alert_id="test_alert_001",
        reason="crisis",
    )

    print(
        handoff
    )

    print("=" * 70)
    print("3. 当前状态")

    print(
        service.get_status(
            conversation_id
        )
    )

    print(
        "requires_human:",
        service.requires_human(
            conversation_id
        ),
    )

    print("=" * 70)
    print("4. 辅导员接入")

    handoff = service.accept_handoff(
        conversation_id
    )

    print(
        handoff
    )

    print("=" * 70)
    print("5. 处理完成")

    handoff = service.resolve_handoff(
        conversation_id
    )

    print(
        handoff
    )

    print("=" * 70)
    print("6. 最终状态")

    print(
        service.get_status(
            conversation_id
        )
    )

    print(
        "requires_human:",
        service.requires_human(
            conversation_id
        ),
    )


if __name__ == "__main__":
    main()