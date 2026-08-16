import argparse
import json
from pathlib import Path
from typing import Any

from src.llm.deepseek_client import DeepSeekClient
from src.retrieval.retriever import Retriever


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_PATHS = {
    "regression": PROJECT_ROOT / "tests" / "rag_cases.json",
    "holdout": PROJECT_ROOT / "tests" / "rag_holdout_cases.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the Counselor AI RAG system."
    )

    parser.add_argument(
        "--dataset",
        choices=DATASET_PATHS.keys(),
        default="regression",
        help=(
            "选择评估数据集："
            "regression 或 holdout。"
        ),
    )

    return parser.parse_args()


def load_test_cases(
    dataset: str,
) -> list[dict[str, Any]]:
    test_cases_path = DATASET_PATHS[dataset]

    if not test_cases_path.exists():
        raise FileNotFoundError(
            f"找不到测试集：{test_cases_path}"
        )

    with test_cases_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        cases = json.load(file)

    if not isinstance(cases, list):
        raise ValueError(
            "测试集最外层必须是列表。"
        )

    return cases


def should_answer_case(
    case: dict[str, Any],
) -> bool:
    """
    兼容两种测试集字段：

    regression:
        should_answer

    holdout:
        should_retrieve
    """
    if "should_answer" in case:
        return bool(case["should_answer"])

    if "should_retrieve" in case:
        return bool(case["should_retrieve"])

    raise ValueError(
        f"测试用例缺少 should_answer / "
        f"should_retrieve：{case.get('query')}"
    )


def get_required_keywords(
    case: dict[str, Any],
) -> list[str]:
    """
    兼容两种关键词字段：

    regression:
        required_keywords

    holdout:
        expected_keywords
    """
    if "required_keywords" in case:
        return case["required_keywords"]

    return case.get(
        "expected_keywords",
        [],
    )


def check_keywords(
    answer: str,
    keywords: list[str],
) -> tuple[bool, list[str]]:
    """
    检查回答是否包含所有必要关键词。
    """
    missing = [
        keyword
        for keyword in keywords
        if keyword not in answer
    ]

    return len(missing) == 0, missing


def get_cited_results(
    results: list[dict[str, Any]],
    cited_source_ids: list[str],
) -> list[dict[str, Any]]:
    """
    将 S1 / S2 等引用 ID
    映射回 Retriever 结果。
    """
    cited_results: list[dict[str, Any]] = []

    for source_id in cited_source_ids:
        if not source_id.startswith("S"):
            continue

        try:
            index = int(source_id[1:]) - 1
        except ValueError:
            continue

        if 0 <= index < len(results):
            cited_results.append(
                results[index]
            )

    return cited_results


def check_citation(
    cited_results: list[dict[str, Any]],
    expected_document: str,
    expected_article: str,
) -> bool:
    """
    检查最终实际引用中
    是否包含预期条款。
    """
    return any(
        item.get("document_title")
        == expected_document
        and item.get("article")
        == expected_article
        for item in cited_results
    )


def main() -> None:
    args = parse_args()

    dataset = args.dataset
    cases = load_test_cases(dataset)

    print(
        f"正在加载 RAG 系统..."
    )

    retriever = Retriever()
    client = DeepSeekClient()

    print("RAG 系统加载完成。")
    print(
        f"当前数据集：{dataset}"
    )
    print(
        f"测试用例数：{len(cases)}"
    )

    answer_passed = 0
    citation_passed = 0
    rejection_passed = 0
    overall_passed = 0

    positive_count = 0
    negative_count = 0

    print()
    print("=" * 70)
    print(
        f"RAG Evaluation [{dataset}]"
    )
    print("=" * 70)

    for number, case in enumerate(
        cases,
        start=1,
    ):
        query = case["query"]

        should_answer = should_answer_case(
            case
        )

        results = retriever.retrieve(query)

        llm_result = client.answer(
            question=query,
            retrieval_results=results,
        )

        answer = llm_result["answer"]

        cited_source_ids = llm_result.get(
            "cited_source_ids",
            [],
        )

        cited_results = get_cited_results(
            results,
            cited_source_ids,
        )

        print()
        print(
            f"{number:02d}. {query}"
        )

        # ============================================================
        # 知识库外问题
        # ============================================================

        if not should_answer:
            negative_count += 1

            refusal_markers = [
                "无法确认",
                "无法根据",
                "没有找到足够可靠",
                "不能确认",
            ]

            answer_refused = any(
                marker in answer
                for marker in refusal_markers
            )

            citation_refused = (
                len(cited_source_ids) == 0
            )

            rejected = (
                answer_refused
                and citation_refused
            )

            if rejected:
                rejection_passed += 1
                overall_passed += 1
                status = "PASS"
            else:
                status = "FAIL"

            print(
                f"     Status:    {status}"
            )

            print(
                "     Rejection: "
                f"{'PASS' if rejected else 'FAIL'}"
            )

            if not rejected:
                print(
                    f"     Retrieved: "
                    f"{len(results)}"
                )

                print(
                    f"     Citations: "
                    f"{cited_source_ids}"
                )

                print()
                print("     Answer:")
                print(
                    f"     {answer}"
                )

            continue

        # ============================================================
        # 知识库内问题
        # ============================================================

        positive_count += 1

        required_keywords = (
            get_required_keywords(case)
        )

        keyword_ok, missing_keywords = (
            check_keywords(
                answer,
                required_keywords,
            )
        )

        citation_ok = check_citation(
            cited_results=cited_results,
            expected_document=case[
                "expected_document"
            ],
            expected_article=case[
                "expected_article"
            ],
        )

        if keyword_ok:
            answer_passed += 1

        if citation_ok:
            citation_passed += 1

        case_passed = (
            keyword_ok
            and citation_ok
        )

        if case_passed:
            overall_passed += 1
            status = "PASS"
        else:
            status = "FAIL"

        print(
            f"     Status:          {status}"
        )

        print(
            "     Answer Keywords: "
            f"{'PASS' if keyword_ok else 'FAIL'}"
        )

        print(
            "     Citation:        "
            f"{'PASS' if citation_ok else 'FAIL'}"
        )

        if not keyword_ok:
            print(
                "     Missing:         "
                + ", ".join(
                    missing_keywords
                )
            )

        if not citation_ok:
            print(
                "     Expected:        "
                f"{case['expected_document']} / "
                f"{case['expected_article']}"
            )

            if cited_results:
                print(
                    "     Actual Citations:"
                )

                for item in cited_results:
                    print(
                        "       - "
                        f"{item.get('document_title')} / "
                        f"{item.get('article')}"
                    )
            else:
                print(
                    "     Actual Citations: none"
                )

        if not case_passed:
            print()
            print("     Retrieved Candidates:")

            if results:
                for index, item in enumerate(
                    results,
                    start=1,
                ):
                    print(
                        f"       #{index} "
                        f"{item.get('document_title')} / "
                        f"{item.get('article')} / "
                        f"{item.get('score', 0):.4f}"
                    )
            else:
                print("       none")

            print()
            print("     Answer:")
            print(
                f"     {answer}"
            )

    # ================================================================
    # Summary
    # ================================================================

    total = len(cases)

    answer_accuracy = (
        answer_passed
        / positive_count
        * 100
        if positive_count
        else 0.0
    )

    citation_accuracy = (
        citation_passed
        / positive_count
        * 100
        if positive_count
        else 0.0
    )

    rejection_accuracy = (
        rejection_passed
        / negative_count
        * 100
        if negative_count
        else 0.0
    )

    overall_accuracy = (
        overall_passed
        / total
        * 100
        if total
        else 0.0
    )

    print()
    print("=" * 70)
    print(
        f"RAG Evaluation Summary "
        f"[{dataset}]"
    )
    print("=" * 70)

    print(
        f"Answer Accuracy:    "
        f"{answer_passed}/{positive_count} "
        f"({answer_accuracy:.1f}%)"
    )

    print(
        f"Citation Accuracy:  "
        f"{citation_passed}/{positive_count} "
        f"({citation_accuracy:.1f}%)"
    )

    print(
        f"Rejection Accuracy: "
        f"{rejection_passed}/{negative_count} "
        f"({rejection_accuracy:.1f}%)"
    )

    print(
        f"Overall:            "
        f"{overall_passed}/{total} "
        f"({overall_accuracy:.1f}%)"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()