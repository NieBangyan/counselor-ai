from typing import Any

import jieba
import numpy as np
from rank_bm25 import BM25Okapi


def tokenize(text: str) -> list[str]:
    """
    中文检索分词。
    """
    return [
        token.strip()
        for token in jieba.cut_for_search(text)
        if token.strip()
    ]


def build_search_text(
    chunk: dict[str, Any],
) -> str:
    """
    将结构化字段拼成 BM25 检索文本。
    """
    parts = [
        chunk.get("document_title") or "",
        chunk.get("chapter") or "",
        chunk.get("article") or "",
        chunk.get("content") or "",
    ]

    return " ".join(
        part
        for part in parts
        if part
    )


class BM25Retriever:
    def __init__(
        self,
        chunks: list[dict[str, Any]],
    ) -> None:
        self.chunks = chunks

        self.corpus_tokens = [
            tokenize(
                build_search_text(chunk)
            )
            for chunk in chunks
        ]

        self.bm25 = BM25Okapi(
            self.corpus_tokens
        )

    def search(
        self,
        query: str,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        query = query.strip()

        if not query:
            return []

        query_tokens = tokenize(query)

        scores = self.bm25.get_scores(
            query_tokens
        )

        indices = np.argsort(scores)[::-1][
            :top_k
        ]

        results: list[dict[str, Any]] = []

        for index in indices:
            score = float(scores[index])

            if score <= 0:
                continue

            chunk = self.chunks[int(index)]

            results.append(
                {
                    "id": chunk.get("id"),
                    "document_title": chunk.get(
                        "document_title"
                    ),
                    "chapter": chunk.get(
                        "chapter"
                    ),
                    "article": chunk.get(
                        "article"
                    ),
                    "content": chunk.get(
                        "content"
                    ),
                    "pdf_pages": chunk.get(
                        "pdf_pages",
                        [],
                    ),
                    "bm25_score": score,
                }
            )

        return results