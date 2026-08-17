from src.retrieval.retriever import Retriever


TEST_QUERIES = [
    "新生因为有事不能按时报到，会直接取消入学资格吗？",
    "必修和限选课不合格累计多少学分可能被退学？",
]


def main() -> None:
    retriever = Retriever()

    for query in TEST_QUERIES:
        print()
        print("=" * 80)
        print(f"问题：{query}")
        print("=" * 80)

        results = retriever.retrieve(query)

        if not results:
            print("检索结果：无")
            continue

        for i, result in enumerate(
            results,
            start=1,
        ):
            print()
            print(f"Top {i}")

            print(
                f"文档："
                f"{result.get('document_title')}"
            )
            print(
                f"条款："
                f"{result.get('article')}"
            )

            print(
                f"Dense Score: "
                f"{result.get('dense_score')}"
            )
            print(
                f"Dense Rank: "
                f"{result.get('dense_rank')}"
            )
            print(
                f"BM25 Rank: "
                f"{result.get('bm25_rank')}"
            )
            print(
                f"RRF Score: "
                f"{result.get('rrf_score')}"
            )

            print(
                f"页码："
                f"{result.get('pdf_pages')}"
            )

            print(
                f"内容："
                f"{result.get('content')}"
            )


if __name__ == "__main__":
    main()