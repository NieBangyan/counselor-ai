from typing import Any

from src.config import (
    RERANK_MAX_RESULTS,
    RERANK_MAX_SCORE_GAP,
)


def rerank_results(
    results: list[dict[str, Any]],
    max_score_gap: float = RERANK_MAX_SCORE_GAP,
    max_results: int = RERANK_MAX_RESULTS,
) -> list[dict[str, Any]]:
    """
    根据与 Top1 的相似度差距过滤弱相关结果。

    这不是独立的神经网络 reranker，而是一层轻量的
    relative-score filtering。
    """
    if not results:
        return []

    sorted_results = sorted(
        results,
        key=lambda item: item["score"],
        reverse=True,
    )

    best_score = sorted_results[0]["score"]

    filtered_results = [
        item
        for item in sorted_results
        if best_score - item["score"] <= max_score_gap
    ]

    return filtered_results[:max_results]