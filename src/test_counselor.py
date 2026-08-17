from src.counseling.counselor import Counselor


def main() -> None:
    counselor = Counselor()

    test_messages = [
        "最近学习压力有点大，总觉得事情做不完。",
        "最近和室友关系不太好，我不知道怎么处理。",
        "考试快到了，我一直很紧张。",
    ]

    for message in test_messages:
        print("=" * 70)
        print(f"学生：{message}")
        print()

        answer = counselor.answer(
            message
        )

        print(f"AI辅导员：{answer}")
        print()


if __name__ == "__main__":
    main()