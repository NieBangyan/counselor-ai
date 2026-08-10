import os

from dotenv import load_dotenv
from openai import OpenAI

from src.llm.prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
)


load_dotenv()


class DeepSeekClient:
    def __init__(self) -> None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

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
        question: str,
        retrieval_results: list[dict],
    ) -> str:
        user_prompt = build_user_prompt(
            question=question,
            results=retrieval_results,
        )
        if not retrieval_results:
            return (
                "根据当前检索到的《学生手册》内容，"
                "暂时没有找到足够可靠的相关规定，"
                "因此无法确认这个问题。"
           )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            max_tokens=800,
        )

        answer = response.choices[0].message.content

        if not answer:
            raise RuntimeError("DeepSeek 返回了空内容。")

        return answer.strip()