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


def is_expected_result(
    result: dict[str, Any],
    case: dict[str, Any],
) -> bool:
    """判断某条检索结果是否命中预期制度和条款。"""
    return (
        result["document_title"] == case["expected_document"]
        and result["article"] == case["expected_article"]
    )


def main() -> None:
    cases = load_test_cases()

    print("正在加载 Retriever...")
    retriever = Retriever()

    print()
    print("=" * 70)
    print("Retrieval Evaluation")
    print("=" * 70)

    recall_passed = 0
    top1_passed = 0
    positive_count = 0

    rejection_passed = 0
    negative_count = 0

    top1_failures: list[dict[str, Any]] = []

    for number, case in enumerate(cases, start=1):
        query = case["query"]
        should_retrieve = case["should_retrieve"]

        results = retriever.retrieve(query)

        print()

        # 
        # 知识库外问题
        # 
        if not should_retrieve:
            negative_count += 1

            rejected = len(results) == 0

            if rejected:
                rejection_passed += 1
                status = "PASS"
            else:
                status = "FAIL"

            print(
                f"[{status}] "
                f"{number:02d}. {query}"
            )

            if rejected:
                print("       检索结果：无（正确拒绝）")
            else:
                top1 = results[0]

                print(
                    f"       Top1: "
                    f"{top1['document_title']} / "
                    f"{top1['article']} / "
                    f"{top1['score']:.4f}"
                )
                print("       Expected: 应该拒绝检索")

            continue

        
        # 知识库内问题
        
        positive_count += 1

        recall_hit = any(
            is_expected_result(item, case)
            for item in results
        )

        top1_hit = (
            bool(results)
            and is_expected_result(results[0], case)
        )

        if recall_hit:
            recall_passed += 1

        if top1_hit:
            top1_passed += 1

        # 这里用 Recall@K 判断整体 PASS/FAIL
        status = "PASS" if recall_hit else "FAIL"

        print(
            f"[{status}] "
            f"{number:02d}. {query}"
        )

        if not results:
            print("       检索结果：无")
            print(
                "       Expected: "
                f"{case['expected_document']} / "
                f"{case['expected_article']}"
            )
            continue

        top1 = results[0]

        print(
            f"       Top1: "
            f"{top1['document_title']} / "
            f"{top1['article']} / "
            f"{top1['score']:.4f}"
        )

        if top1_hit:
            print("       Top1 Match: YES")
        else:
            print("       Top1 Match: NO")
            print(
                "       Expected: "
                f"{case['expected_document']} / "
                f"{case['expected_article']}"
            )

            top1_failures.append(
                {
                    "query": query,
                    "expected_document": case[
                        "expected_document"
                    ],
                    "expected_article": case[
                        "expected_article"
                    ],
                    "actual_document": top1[
                        "document_title"
                    ],
                    "actual_article": top1["article"],
                    "actual_score": top1["score"],
                }
            )

        if not recall_hit:
            print("       Retrieved:")

            for item in results:
                print(
                    "         - "
                    f"{item['document_title']} / "
                    f"{item['article']} / "
                    f"{item['score']:.4f}"
                )

    
    # 统计
    # 

    recall_accuracy = (
        recall_passed / positive_count * 100
        if positive_count
        else 0.0
    )

    top1_accuracy = (
        top1_passed / positive_count * 100
        if positive_count
        else 0.0
    )

    rejection_accuracy = (
        rejection_passed / negative_count * 100
        if negative_count
        else 0.0
    )

    print()
    print("=" * 70)
    print("Evaluation Summary")
    print("=" * 70)

    print(
        f"Recall@K:           "
        f"{recall_passed}/{positive_count} "
        f"({recall_accuracy:.1f}%)"
    )

    print(
        f"Top1 Accuracy:      "
        f"{top1_passed}/{positive_count} "
        f"({top1_accuracy:.1f}%)"
    )

    print(
        f"Rejection Accuracy: "
        f"{rejection_passed}/{negative_count} "
        f"({rejection_accuracy:.1f}%)"
    )

    # 
    # 输出 Top1 排序失败案例
    # 

    if top1_failures:
        print()
        print("=" * 70)
        print("Top1 Ranking Failures")
        print("=" * 70)

        for failure in top1_failures:
            print()
            print(f"问题：{failure['query']}")
            print(
                "Expected: "
                f"{failure['expected_document']} / "
                f"{failure['expected_article']}"
            )
            print(
                "Actual:   "
                f"{failure['actual_document']} / "
                f"{failure['actual_article']} / "
                f"{failure['actual_score']:.4f}"
            )

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()