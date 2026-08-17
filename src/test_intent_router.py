from src.routing.intent_router import (
    IntentRouter,
)


def main() -> None:
    router = IntentRouter()

    test_cases = [
        "我不想上课了。",
        "最近什么都不想做。",
        "挂科了怎么办？",
        "我挂科之后特别难受。",
        "最近睡不好，总想着考试。",
        "我想休学一段时间。",
        "和老师闹矛盾了，不知道怎么办。",
        "我想知道休学需要什么手续。",
    ]

    for message in test_cases:
        intent = router.classify(message)

        print(
            f"{intent:12} | {message}"
        )


if __name__ == "__main__":
    main()