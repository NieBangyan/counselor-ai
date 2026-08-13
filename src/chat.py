from src.llm.deepseek_client import DeepSeekClient
from src.retrieval.retriever import Retriever


def main() -> None:
    print("正在启动 AI 辅导员……")

    retriever = Retriever()
    client = DeepSeekClient()

    print("\nAI 辅导员已启动。")
    print("输入问题开始咨询，输入 exit 退出。")

    while True:
        question = input("\n你：").strip()

        if question.lower() in {"exit", "quit"}:
            print("\n再见！")
            break

        if not question:
            continue

        try:
            results = retriever.retrieve(question)

            llm_result = client.answer(
                question=question,
                retrieval_results=results,
            )

            answer = llm_result["answer"]
            cited_source_ids = set(
                llm_result["cited_source_ids"]
            )

            print(f"\nAI辅导员：\n{answer}")

            if cited_source_ids:
                print("\n参考依据：")

                for index, item in enumerate(
                    results,
                    start=1,
                ):
                    source_id = f"S{index}"

                    if source_id not in cited_source_ids:
                        continue

                    document_title = (
                        item.get("document_title")
                        or "未标注制度"
                    )
                    chapter = (
                        item.get("chapter")
                        or "未标注章节"
                    )
                    article = (
                        item.get("article")
                        or "未标注条款"
                    )
                    pages = item.get("pdf_pages") or []

                    page_text = (
                        "、".join(
                            str(page)
                            for page in pages
                        )
                        if pages
                        else "未标注"
                    )

                    print(
                        f"- [{source_id}] "
                        f"{document_title} / "
                        f"{chapter} / "
                        f"{article} / "
                        f"PDF第{page_text}页"
                    )

        except Exception as exc:
            print(f"\n发生错误：{exc}")


if __name__ == "__main__":
    main()