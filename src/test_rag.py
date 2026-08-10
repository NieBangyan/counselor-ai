from src.llm.deepseek_client import DeepSeekClient
from src.retrieval.retriever import Retriever


def main() -> None:
    question = "我想请假四天，需要谁批准？"

    retriever = Retriever()
    results = retriever.retrieve(question)

    client = DeepSeekClient()
    answer = client.answer(
        question=question,
        retrieval_results=results,
    )

    print("\n问题：")
    print(question)

    print("\n回答：")
    print(answer)


if __name__ == "__main__":
    main()