import json
import logging

import faiss
import numpy as np

from src.config import (
    CHUNKS_PATH,
    FAISS_INDEX_PATH,
    TOP_K,
)
from src.embedding.model import get_embedding_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def load_chunks():
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def search(query: str, top_k: int = TOP_K):
    logger.info("Loading model...")
    model = get_embedding_model()

    logger.info("Loading FAISS index...")
    index = faiss.read_index(str(FAISS_INDEX_PATH))

    chunks = load_chunks()

    logger.info("Encoding query...")
    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
    ).astype("float32")

    scores, indices = index.search(query_embedding, top_k)

    results = []

    for score, idx in zip(scores[0], indices[0]):
        results.append(
            {
                "score": float(score),
                "chunk": chunks[idx],
            }
        )

    return results


if __name__ == "__main__":
    while True:
        question = input("\n请输入问题（输入 exit 退出）：")

        if question.lower() == "exit":
            break

        results = search(question)

        print("\n========================")

        for i, item in enumerate(results, start=1):
            chunk = item["chunk"]

            print(f"\nTop {i}")
            print(f"Score: {item['score']:.4f}")
            print(f"文档：{chunk['document_title']}")
            print(f"章节：{chunk['chapter']}")
            print(f"条款：{chunk['article']}")
            print(f"页码：{chunk['pdf_pages']}")
            print("-" * 60)
            print(chunk["content"])

        print("\n========================")