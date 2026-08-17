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
        if (
            best_score - item["score"]
            <= max_score_gap
        )
    ]

    return filtered_results[:max_results]