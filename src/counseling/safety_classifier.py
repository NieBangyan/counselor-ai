import os
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


SafetyLevel = Literal[
    "normal",
    "concern",
    "crisis",
]


SAFETY_SYSTEM_PROMPT = """
你是高校 AI 辅导员系统中的心理安全分类器。

你的任务不是提供心理咨询，而是判断学生当前表达中
是否存在需要升级处理的安全风险。

只允许输出以下三个标签之一：

normal
concern
crisis


分类标准：

1. normal

普通的学习压力、考试焦虑、人际关系困扰、
孤独、短暂低落、烦躁等。

没有明显的自伤、自杀或即时人身安全风险。

例如：

“最近学习压力特别大。”
“考试快到了，我很焦虑。”
“最近和室友关系不好。”
“最近有点孤独。”
“最近心情不太好。”


2. concern

学生表现出比较明显或持续的心理困扰，
例如强烈绝望、长期严重低落、明显无法正常生活，
或者出现值得关注但没有明确即时危险的信息。

例如：

“我已经很长时间什么都不想做了。”
“每天都觉得特别绝望。”
“最近完全撑不住了。”
“我觉得活着没有什么意思。”

这一等级需要鼓励学生尽快联系现实中的可信任的人、
学校心理支持资源或专业人员，但当前表达尚不足以判断
存在明确、即时的人身安全危险。


3. crisis

学生明确表达正在实施、即将实施，
或者存在非常明确的即时自伤、自杀或其他严重人身安全风险。

例如：

“我现在准备伤害自己。”
“我已经决定马上结束自己的生命。”
“我现在正在做可能伤害自己的事情。”

只有存在明确的即时危险信息时才分类为 crisis。


重要规则：

- 不要回答学生的问题。
- 不要提供心理建议。
- 不要解释判断理由。
- 不要输出 Markdown。
- 不要因为普通的“压力大”“焦虑”“难受”
  就判断为 crisis。
- 不确定是否存在即时危险时，不要武断升级为 crisis。
- 只能输出 normal、concern 或 crisis。
""".strip()


class SafetyClassifier:
    def __init__(self) -> None:
        api_key = os.getenv(
            "DEEPSEEK_API_KEY"
        )

        model = os.getenv(
            "DEEPSEEK_MODEL",
            "deepseek-v4-flash",
        )

        if not api_key:
            raise RuntimeError(
                "没有找到 DEEPSEEK_API_KEY，"
                "请检查项目根目录下的 .env 文件。"
            )

        self.model = model

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

    def classify(
        self,
        message: str,
    ) -> SafetyLevel:
        message = message.strip()

        if not message:
            return "normal"

        allowed_levels = (
            "normal",
            "concern",
            "crisis",
        )

        # 与 IntentRouter 一样，
        # 对偶发的空 content 做一次重试。
        for _ in range(2):
            response = (
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                SAFETY_SYSTEM_PROMPT
                            ),
                        },
                        {
                            "role": "user",
                            "content": message,
                        },
                    ],
                    max_tokens=200,
                    temperature=0,
                )
            )

            result = (
                response
                .choices[0]
                .message
                .content
            )

            if not result:
                continue

            level = result.strip().lower()

            if level in allowed_levels:
                return level

            for allowed_level in allowed_levels:
                if allowed_level in level:
                    return allowed_level

        # 分类服务异常时不要凭空判断用户处于危机状态。
        return "normal"