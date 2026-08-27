from dataclasses import dataclass
from typing import List

from sentence_transformers import SentenceTransformer, util

from src.retrieval.index import RetrievalResult


@dataclass
class RankedResult:
    document_id: str
    text: str
    retrieval_score: float
    ranking_score: float
    metadata: dict


class SemanticReranker:
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        retrieval_weight: float = 0.35,
        semantic_weight: float = 0.65,
    ):
        self.model = SentenceTransformer(model_name)

        self.retrieval_weight = retrieval_weight
        self.semantic_weight = semantic_weight

    def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
    ) -> List[RankedResult]:

        if not results:
            return []

        query_embedding = self.model.encode(
            query,
            convert_to_tensor=True,
        )

        document_embeddings = self.model.encode(
            [result.text for result in results],
            convert_to_tensor=True,
        )

        semantic_scores = util.cos_sim(
            query_embedding,
            document_embeddings,
        )[0]

        reranked = []

        for result, semantic_score in zip(
            results,
            semantic_scores,
        ):
            semantic_score = float(semantic_score)

            ranking_score = (
                self.retrieval_weight * result.score
                + self.semantic_weight * semantic_score
            )

            reranked.append(
                RankedResult(
                    document_id=result.document_id,
                    text=result.text,
                    retrieval_score=result.score,
                    ranking_score=ranking_score,
                    metadata=result.metadata,
                )
            )

        return sorted(
            reranked,
            key=lambda item: item.ranking_score,
            reverse=True,
        )