import os
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


Intent = Literal[
    "policy",
    "counseling",
    "other",
]


ROUTER_SYSTEM_PROMPT = """
你是高校 AI 辅导员系统的意图分类器。

你的任务是判断学生的问题应该交给哪个模块处理。

只允许输出以下三个标签之一：

policy
counseling
other

分类规则：

1. policy
与学校规章制度、学生手册、办事规定相关的问题。
例如：
- 请假
- 学籍
- 退学
- 转专业
- 选课、退课、重修
- 成绩、GPA
- 奖学金
- 辅修
- 毕业、学位
- 勤工助学
- 休学、复学
- 其他学校正式制度问题

2. counseling
学生正在表达情绪、压力、焦虑、孤独、
人际关系困扰、学习压力等，并希望获得
基础心理支持或倾听。

例如：
“最近学习压力特别大。”
“考试快到了，我很焦虑。”
“我和室友关系很差，不知道怎么办。”
“最近总觉得很孤独。”
“我挂科之后特别难受。”
“我不想上课了。”

3. other
既不是学校政策问题，也不是基础心理支持问题。

例如：
“明天天气怎么样？”
“帮我写一段 Python 代码。”
“哪里有好吃的火锅？”
“怎么做川菜？”

分类时注意区分：

“挂科了怎么办？”
更偏向询问学校制度和后续处理，属于 policy。

“我挂科之后特别难受。”
重点是学生的情绪困扰，属于 counseling。

“我想休学一段时间。”
涉及学校学籍制度，属于 policy。

“我想知道休学需要什么手续。”
明确询问学校规定，属于 policy。

注意：
- 不要回答学生的问题。
- 不要解释分类理由。
- 不要输出 Markdown。
- 只能输出 policy、counseling 或 other。
""".strip()


class IntentRouter:
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
    ) -> Intent:
        message = message.strip()

        if not message:
            return "other"

        allowed_intents = (
            "policy",
            "counseling",
            "other",
        )

        # DeepSeek 偶尔可能返回空 content，
        # 因此最多尝试两次。
        for _ in range(2):
            response = (
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                ROUTER_SYSTEM_PROMPT
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

            intent = result.strip().lower()

            # 最理想的情况：
            # 模型只返回一个标签。
            if intent in allowed_intents:
                return intent

            # 容忍模型偶尔返回：
            # “分类结果：policy”
            # “intent: counseling”
            for allowed_intent in allowed_intents:
                if allowed_intent in intent:
                    return allowed_intent

        # 两次调用都没有得到合法结果时，
        # 使用 other 作为安全兜底。
        return "other"