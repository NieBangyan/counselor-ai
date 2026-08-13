import json
from pathlib import Path
from typing import Any
from src.retrieval.rerank import rerank_results
import faiss

from src.config import (
    CHUNKS_PATH,
    FAISS_INDEX_PATH,
    TOP_K,
    MIN_RETRIEVAL_SCORE,
)
from src.embedding.model import get_embedding_model


class Retriever:
    def __init__(
        self,
        chunks_path: Path = CHUNKS_PATH,
        index_path: Path = FAISS_INDEX_PATH,
        top_k: int = TOP_K,
    ) -> None:
        self.top_k = top_k

        self.model = get_embedding_model()
        self.index = faiss.read_index(str(index_path))
        self.chunks = self._load_chunks(chunks_path)

        if self.index.ntotal != len(self.chunks):
            raise ValueError(
                "FAISS 向量数量与知识块数量不一致："
                f"{self.index.ntotal} != {len(self.chunks)}"
            )

    @staticmethod
    def _load_chunks(
        path: Path,
    ) -> list[dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(
                f"找不到知识块文件：{path}"
            )

        with path.open("r", encoding="utf-8") as file:
            chunks = json.load(file)

        if not isinstance(chunks, list):
            raise ValueError(
                "知识块文件格式错误：最外层必须是列表。"
            )

        return chunks

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        query = query.strip()

        if not query:
            return []

        k = top_k or self.top_k

        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype("float32")

        scores, indices = self.index.search(
            query_embedding,
            k,
        )

        results: list[dict[str, Any]] = []

        for score, index in zip(
            scores[0],
            indices[0],
        ):
            if index < 0:
                continue
            if score < MIN_RETRIEVAL_SCORE:
                continue

            chunk = self.chunks[index]

            results.append(
                {
                    "score": float(score),
                    "id": chunk.get("id"),
                    "document_title": chunk.get(
                        "document_title"
                    ),
                    "chapter": chunk.get("chapter"),
                    "article": chunk.get("article"),
                    "content": chunk.get("content"),
                    "pdf_pages": chunk.get(
                        "pdf_pages",
                        [],
                    ),
                }
            )

        return rerank_results(
        query=query,
        results=results,
)