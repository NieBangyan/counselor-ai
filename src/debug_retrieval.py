from src.config import (
    CHUNKS_PATH,
    FAISS_INDEX_PATH,
)
from src.embedding.model import get_embedding_model

import faiss
import json


TEST_CASES = [
    {
        "query": "请两天假找谁批？",
        "expected_document": "清华大学本科生学籍管理规定",
        "expected_article": "第十一条",
    },
    {
        "query": "请病假必须交什么证明？",
        "expected_document": "清华大学本科生学籍管理规定",
        "expected_article": "第十一条",
    },
    {
        "query": "奖学金通常一年评几次？",
        "expected_document": "清华大学学生奖学金管理规定",
        "expected_article": "第十三条",
    },
]


def load_chunks():
    with CHUNKS_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def main() -> None:
    print("正在加载模型和索引...")

    model = get_embedding_model()
    index = faiss.read_index(
        str(FAISS_INDEX_PATH)
    )
    chunks = load_chunks()

    for case in TEST_CASES:
        query = case["query"]

        print()
        print("=" * 80)
        print(f"问题：{query}")
        print(
            "Expected: "
            f"{case['expected_document']} / "
            f"{case['expected_article']}"
        )
        print("=" * 80)

        query_embedding = model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype("float32")

        scores, indices = index.search(
            query_embedding,
            20,
        )

        expected_rank = None
        expected_score = None

        for rank, (score, index_id) in enumerate(
            zip(scores[0], indices[0]),
            start=1,
        ):
            if index_id < 0:
                continue

            chunk = chunks[index_id]

            document_title = chunk.get(
                "document_title"
            )
            article = chunk.get("article")

            marker = ""

            if (
                document_title
                == case["expected_document"]
                and article
                == case["expected_article"]
            ):
                marker = "  <=== EXPECTED"
                expected_rank = rank
                expected_score = float(score)

            print(
                f"#{rank:02d} "
                f"score={float(score):.4f} | "
                f"{document_title} / "
                f"{article}"
                f"{marker}"
            )

        print()
        print("-" * 80)

        if expected_rank is None:
            print(
                "正确条款没有进入 FAISS Top20。"
            )
        else:
            print(
                f"正确条款原始排名：#{expected_rank}"
            )
            print(
                f"正确条款原始分数："
                f"{expected_score:.4f}"
            )


if __name__ == "__main__":
    main()