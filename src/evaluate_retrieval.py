import json
from pathlib import Path
from typing import Any

from src.retrieval.retriever import Retriever


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_CASES_PATH = PROJECT_ROOT / "tests" / "retrieval_cases.json"


def load_test_cases() -> list[dict[str, Any]]:
    if not TEST_CASES_PATH.exists():
        raise FileNotFoundError(
            f"找不到测试集：{TEST_CASES_PATH}"
        )

    with TEST_CASES_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        cases = json.load(file)

    if not isinstance(cases, list):
        raise ValueError("测试集最外层必须是列表。")

    return cases


def evaluate_case(
    retriever: Retriever,
    case: dict[str, Any],
) -> dict[str, Any]:
    query = case["query"]
    should_retrieve = case["should_retrieve"]

    results = retriever.retrieve(query)

    # ---------- 无关问题 ----------
    if not should_retrieve:
        passed = len(results) == 0

        return {
            "passed": passed,
            "results": results,
        }

    # ---------- 知识库内问题 ----------
    if not results:
        return {
            "passed": False,
            "results": [],
        }

    expected_document = case["expected_document"]
    expected_article = case["expected_article"]

    # 不要求必须 Top1 命中。
    # 只要最终保留下来的结果中存在正确条款即可。
    passed = any(
        item["document_title"] == expected_document
        and item["article"] == expected_article
        for item in results
    )

    return {
        "passed": passed,
        "results": results,
    }


def main() -> None:
    cases = load_test_cases()

    print("正在加载 Retriever...")
    retriever = Retriever()

    print()
    print("=" * 70)
    print("Retrieval Evaluation")
    print("=" * 70)

    passed_count = 0

    for number, case in enumerate(cases, start=1):
        evaluation = evaluate_case(
            retriever,
            case,
        )

        passed = evaluation["passed"]
        results = evaluation["results"]

        if passed:
            passed_count += 1

        status = "PASS" if passed else "FAIL"

        print()
        print(
            f"[{status}] "
            f"{number:02d}. {case['query']}"
        )

        if not results:
            print("       检索结果：无")
        else:
            top1 = results[0]

            print(
                f"       Top1: "
                f"{top1['document_title']} / "
                f"{top1['article']} / "
                f"{top1['score']:.4f}"
            )

        # 失败时输出更多信息，方便排查
        if not passed:
            if case["should_retrieve"]:
                print(
                    "       Expected: "
                    f"{case['expected_document']} / "
                    f"{case['expected_article']}"
                )

                if results:
                    print("       Retrieved:")

                    for item in results:
                        print(
                            "         - "
                            f"{item['document_title']} / "
                            f"{item['article']} / "
                            f"{item['score']:.4f}"
                        )
            else:
                print(
                    "       Expected: "
                    "应该拒绝检索"
                )

    total = len(cases)
    failed_count = total - passed_count
    accuracy = (
        passed_count / total * 100
        if total
        else 0.0
    )

    print()
    print("=" * 70)
    print(f"Passed:   {passed_count}/{total}")
    print(f"Failed:   {failed_count}/{total}")
    print(f"Accuracy: {accuracy:.1f}%")
    print("=" * 70)


if __name__ == "__main__":
    main()