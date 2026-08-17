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
    ) -> str:
        message = message.strip()

        if not message:
            return ""

        response = (
            self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            COUNSELING_SYSTEM_PROMPT
                        ),
                    },
                    {
                        "role": "user",
                        "content": message,
                    },
                ],
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