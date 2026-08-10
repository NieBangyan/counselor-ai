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

            answer = client.answer(
                question=question,
                retrieval_results=results,
            )

            print(f"\nAI辅导员：{answer}")

        except Exception as exc:
            print(f"\n发生错误：{exc}")


if __name__ == "__main__":
    main()