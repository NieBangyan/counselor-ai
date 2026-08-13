import json
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
        question: str,
        retrieval_results: list[dict],
    ) -> dict:
        if not retrieval_results:
            return {
                "answer": (
                    "根据当前检索到的《学生手册》内容，"
                    "暂时没有找到足够可靠的相关规定，"
                    "因此无法确认这个问题。"
                ),
                "cited_source_ids": [],
            }

        user_prompt = build_user_prompt(
            question=question,
            results=retrieval_results,
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
            max_tokens=1000,
        )

        content = response.choices[0].message.content

        if not content:
            raise RuntimeError(
                "DeepSeek 返回了空内容。"
            )

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "DeepSeek 返回的内容不是合法 JSON。"
            ) from exc

        answer = data.get("answer")
        cited_source_ids = data.get(
            "cited_source_ids",
            [],
        )

        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError(
                "DeepSeek 返回结果缺少有效 answer。"
            )

        if not isinstance(cited_source_ids, list):
            raise RuntimeError(
                "cited_source_ids 必须是列表。"
            )

        valid_ids = {
            f"S{index}"
            for index in range(
                1,
                len(retrieval_results) + 1,
            )
        }

        cited_source_ids = [
            source_id
            for source_id in cited_source_ids
            if source_id in valid_ids
        ]

        return {
            "answer": answer.strip(),
            "cited_source_ids": cited_source_ids,
        }