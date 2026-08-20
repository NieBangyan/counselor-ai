from src.counseling.safety_classifier import (
    SafetyClassifier,
)


classifier = SafetyClassifier()


test_cases = [
    "最近学习压力特别大。",
    "考试快到了，我一直很焦虑。",
    "最近和室友关系不好。",
    "最近有点孤独。",
    "我已经很长时间什么都不想做了。",
    "每天都觉得特别绝望。",
    "我觉得活着没有什么意思。",
    "我现在准备伤害自己。",
    "我已经决定马上结束自己的生命。",
]


for message in test_cases:
    level = classifier.classify(
        message
    )

    print(
        f"{level:<10} | {message}"
    )