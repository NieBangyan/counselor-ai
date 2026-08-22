import os

from dotenv import load_dotenv
from openai import OpenAI

from src.counseling.prompt import (
    COUNSELING_SYSTEM_PROMPT,
)


load_dotenv()


class Counselor:
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

    def answer(
        self,
        message: str,
        history: (
            list[dict[str, str]]
            | None
        ) = None,
    ) -> str:
        """
        生成基础心理支持回答。

        history:
            当前会话最近几条历史消息。

        注意：
            SafetyClassifier 不在这里执行。
            安全判断仍由 AssistantService
            针对当前消息单独完成。
        """

        message = message.strip()

        if not message:
            return ""

        messages = [
            {
                "role": "system",
                "content": (
                    COUNSELING_SYSTEM_PROMPT
                ),
            }
        ]

        # ====================================================
        # Conversation History
        # ====================================================

        if history:
            for item in history:
                role = item.get(
                    "role"
                )

                content = (
                    item.get(
                        "content",
                        ""
                    )
                    .strip()
                )

                if (
                    role
                    in {
                        "user",
                        "assistant",
                    }
                    and content
                ):
                    messages.append(
                        {
                            "role": role,
                            "content": content,
                        }
                    )

        # ====================================================
        # Current User Message
        # ====================================================

        messages.append(
            {
                "role": "user",
                "content": message,
            }
        )

        # ====================================================
        # LLM
        # ====================================================

        response = (
            self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=600,
            )
        )

        answer = (
            response
            .choices[0]
            .message
            .content
        )

        if not answer:
            raise RuntimeError(
                "DeepSeek 返回了空内容。"
            )

        return answer.strip()