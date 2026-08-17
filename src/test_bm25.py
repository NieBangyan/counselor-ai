import json

from src.config import CHUNKS_PATH
from src.retrieval.bm25 import BM25Retriever


TEST_CASES = [
    {
        "query": (
            "新生因为有事不能按时报到，"
            "会直接取消入学资格吗？"
        ),
        "expected_document": (
            "清华大学本科生学籍管理规定"
        ),
        "expected_article": "第三条",
    },
    {
        "query": (
            "必修和限选课不合格累计"
            "多少学分可能被退学？"
        ),
        "expected_document": (
            "清华大学本科生学籍管理规定"
        ),
        "expected_article": "第三十九条",
    },
]


def main() -> None:
    with CHUNKS_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        chunks = json.load(file)

    retriever = BM25Retriever(chunks)

    for case in TEST_CASES:
        print()
        print("=" * 70)
        print(case["query"])
        print("=" * 70)

        results = retriever.search(
            case["query"],
            top_k=20,
        )

        expected_rank = None

        for rank, result in enumerate(
            results,
            start=1,
        ):
            chunk = chunks[
                result["index"]
            ]

            marker = ""

            if (
                chunk.get("document_title")
                == case["expected_document"]
                and chunk.get("article")
                == case["expected_article"]
            ):
                marker = " <=== EXPECTED"
                expected_rank = rank

            print(
                f"#{rank:02d} "
                f"score={result['score']:.4f} | "
                f"{chunk.get('document_title')} / "
                f"{chunk.get('article')}"
                f"{marker}"
            )

        print()

        if expected_rank:
            print(
                f"正确条款 BM25 排名："
                f"#{expected_rank}"
            )
        else:
            print(
                "正确条款没有进入 BM25 Top20"
            )


if __name__ == "__main__":
    main()