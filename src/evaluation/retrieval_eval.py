from dataclasses import dataclass
from typing import Dict, List, Sequence


@dataclass
class RetrievalMetrics:
    recall_at_k: float
    precision_at_k: float
    reciprocal_rank: float
    hit_at_k: float


def evaluate_query(
    retrieved_ids: Sequence[str],
    relevant_ids: Sequence[str],
    k: int = 5,
) -> RetrievalMetrics:
    """
    Evaluate retrieval results for a single query.

    retrieved_ids:
        Document IDs ordered from most to least relevant.

    relevant_ids:
        Ground-truth document IDs considered relevant to the query.
    """

    if k <= 0:
        raise ValueError("k must be greater than 0.")

    relevant = set(relevant_ids)
    top_k = list(retrieved_ids[:k])

    if not relevant:
        return RetrievalMetrics(
            recall_at_k=0.0,
            precision_at_k=0.0,
            reciprocal_rank=0.0,
            hit_at_k=0.0,
        )

    relevant_retrieved = sum(
        document_id in relevant
        for document_id in top_k
    )

    recall_at_k = relevant_retrieved / len(relevant)

    precision_at_k = relevant_retrieved / k

    hit_at_k = float(relevant_retrieved > 0)

    reciprocal_rank = 0.0

    for rank, document_id in enumerate(retrieved_ids, start=1):
        if document_id in relevant:
            reciprocal_rank = 1.0 / rank
            break

    return RetrievalMetrics(
        recall_at_k=recall_at_k,
        precision_at_k=precision_at_k,
        reciprocal_rank=reciprocal_rank,
        hit_at_k=hit_at_k,
    )


def aggregate_metrics(
    metrics: List[RetrievalMetrics],
) -> Dict[str, float]:
    """
    Aggregate retrieval metrics across multiple queries.
    """

    if not metrics:
        return {
            "recall_at_k": 0.0,
            "precision_at_k": 0.0,
            "mrr": 0.0,
            "hit_rate_at_k": 0.0,
        }

    n = len(metrics)

    return {
        "recall_at_k": sum(
            metric.recall_at_k for metric in metrics
        ) / n,
        "precision_at_k": sum(
            metric.precision_at_k for metric in metrics
        ) / n,
        "mrr": sum(
            metric.reciprocal_rank for metric in metrics
        ) / n,
        "hit_rate_at_k": sum(
            metric.hit_at_k for metric in metrics
        ) / n,
    }