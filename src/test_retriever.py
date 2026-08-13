from src.retrieval.retriever import Retriever


retriever = Retriever()

results = retriever.retrieve(
"明天天气怎么样？")

for i, result in enumerate(results, start=1):
    print("=" * 70)
    print(f"Top {i}")
    print(f"Score: {result['score']:.4f}")
    print(f"文档：{result['document_title']}")
    print(
        f"章节："
        f"{result['chapter'] or '未标注章节'}"
    )
    print(f"条款：{result['article']}")
    print(f"页码：{result['pdf_pages']}")
    print(result["content"])