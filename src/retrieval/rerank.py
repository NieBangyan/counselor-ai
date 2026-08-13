from functools import lru_cache
from typing import Any

import torch
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
)

from src.config import (
    EMBEDDING_RANK_WEIGHT,
    RERANK_MAX_RESULTS,
    RERANK_MODEL_NAME,
    RERANK_RANK_WEIGHT,
)


@lru_cache(maxsize=1)
def get_reranker():
    """Load and cache the local BGE reranker."""

    tokenizer = AutoTokenizer.from_pretrained(
        RERANK_MODEL_NAME,
        local_files_only=True,
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        RERANK_MODEL_NAME,
        local_files_only=True,
    )

    model.eval()

    return tokenizer, model


def build_passage(
    result: dict[str, Any],
) -> str:
    """Combine metadata and content for reranking."""

    parts = [
        result.get("document_title") or "",
        result.get("chapter") or "",
        result.get("article") or "",
        result.get("content") or "",
    ]

    return "\n".join(
        part.strip()
        for part in parts
        if part and part.strip()
    )


def rerank_results(
    query: str,
    results: list[dict[str, Any]],
    max_results: int = RERANK_MAX_RESULTS,
) -> list[dict[str, Any]]:
    """
    Combine embedding rank and BGE reranker rank.

    Embedding retrieval remains the primary signal.
    The cross-encoder reranker acts as a secondary ranking signal.
    """

    if not results:
        return []

    tokenizer, model = get_reranker()

    # --------------------------------------------------
    # 1. 保存原始 Embedding 排名
    # --------------------------------------------------

    candidates: list[dict[str, Any]] = []

    for embedding_rank, result in enumerate(
        results,
        start=1,
    ):
        item = result.copy()

        item["embedding_score"] = float(
            result["score"]
        )

        item["embedding_rank"] = embedding_rank

        candidates.append(item)

    # --------------------------------------------------
    # 2. BGE Reranker 打分
    # --------------------------------------------------

    passages = [
        build_passage(item)
        for item in candidates
    ]

    pairs = [
        [query, passage]
        for passage in passages
    ]

    inputs = tokenizer(
        pairs,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )

    with torch.no_grad():
        scores = (
            model(**inputs)
            .logits
            .view(-1)
            .cpu()
            .tolist()
        )

    for item, score in zip(
        candidates,
        scores,
    ):
        item["rerank_score"] = float(score)

    # --------------------------------------------------
    # 3. 得到 Reranker 排名
    # --------------------------------------------------

    reranker_order = sorted(
        range(len(candidates)),
        key=lambda index: candidates[index][
            "rerank_score"
        ],
        reverse=True,
    )

    for rerank_rank, index in enumerate(
        reranker_order,
        start=1,
    ):
        candidates[index]["rerank_rank"] = (
            rerank_rank
        )

    # --------------------------------------------------
    # 4. Rank Fusion
    # --------------------------------------------------

    candidate_count = len(candidates)

    for item in candidates:
        embedding_component = (
            candidate_count
            - item["embedding_rank"]
            + 1
        ) / candidate_count

        rerank_component = (
            candidate_count
            - item["rerank_rank"]
            + 1
        ) / candidate_count

        final_score = (
            EMBEDDING_RANK_WEIGHT
            * embedding_component
            + RERANK_RANK_WEIGHT
            * rerank_component
        )

        item["final_score"] = final_score

    # --------------------------------------------------
    # 5. 最终排序
    # --------------------------------------------------

    candidates.sort(
        key=lambda item: item["final_score"],
        reverse=True,
    )

    return candidates[:max_results]