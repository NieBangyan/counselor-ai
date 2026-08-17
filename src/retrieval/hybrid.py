from typing import Any

from src.config import HYBRID_RRF_K


def reciprocal_rank_fusion(
    dense_results: list[dict[str, Any]],
    bm25_results: list[dict[str, Any]],
    rrf_k: int = HYBRID_RRF_K,
) -> list[dict[str, Any]]:
    fused: dict[int, dict[str, Any]] = {}

    for rank, item in enumerate(
        dense_results,
        start=1,
    ):
        chunk_id = item["id"]

        if chunk_id not in fused:
            fused[chunk_id] = item.copy()
            fused[chunk_id]["rrf_score"] = 0.0
            fused[chunk_id]["dense_rank"] = None
            fused[chunk_id]["bm25_rank"] = None

        fused[chunk_id]["dense_rank"] = rank
        fused[chunk_id]["rrf_score"] += (
            0.4 / (rrf_k + rank)
        )

    for rank, item in enumerate(
        bm25_results,
        start=1,
    ):
        chunk_id = item["id"]

        if chunk_id not in fused:
            fused[chunk_id] = item.copy()
            fused[chunk_id]["rrf_score"] = 0.0
            fused[chunk_id]["dense_rank"] = None
            fused[chunk_id]["bm25_rank"] = None

        fused[chunk_id]["bm25_rank"] = rank
        fused[chunk_id]["rrf_score"] += (
            0.6/ (rrf_k + rank)
        )

    results = list(
        fused.values()
    )

    results.sort(
        key=lambda item: item[
            "rrf_score"
        ],
        reverse=True,
    )

    return results