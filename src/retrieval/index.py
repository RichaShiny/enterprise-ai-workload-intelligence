from dataclasses import dataclass
from typing import List, Dict, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class RetrievalResult:
    document_id: str
    text: str
    score: float
    metadata: Dict[str, Any]


class LexicalRetriever:
    def __init__(self):
        self.documents: List[Dict[str, Any]] = []
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
        )
        self.document_matrix = None

    def fit(self, documents: List[Dict[str, Any]]) -> None:
        self.documents = documents

        texts = [doc["text"] for doc in documents]

        self.document_matrix = self.vectorizer.fit_transform(texts)

    def search(
        self,
        query: str,
        top_k: int = 5,
        metadata_filters: Dict[str, Any] | None = None,
    ) -> List[RetrievalResult]:
        if self.document_matrix is None:
            raise RuntimeError("Retriever must be fit before calling search().")

        candidate_indices = list(range(len(self.documents)))

        if metadata_filters:
            candidate_indices = [
                idx
                for idx in candidate_indices
                if self._matches_metadata(
                    self.documents[idx].get("metadata", {}),
                    metadata_filters,
                )
            ]

        if not candidate_indices:
            return []

        query_vector = self.vectorizer.transform([query])

        candidate_matrix = self.document_matrix[candidate_indices]

        similarities = cosine_similarity(
            query_vector,
            candidate_matrix,
        ).flatten()

        ranked = sorted(
            zip(candidate_indices, similarities),
            key=lambda item: item[1],
            reverse=True,
        )[:top_k]

        return [
            RetrievalResult(
                document_id=self.documents[idx]["document_id"],
                text=self.documents[idx]["text"],
                score=float(score),
                metadata=self.documents[idx].get("metadata", {}),
            )
            for idx, score in ranked
        ]

    @staticmethod
    def _matches_metadata(
        metadata: Dict[str, Any],
        filters: Dict[str, Any],
    ) -> bool:
        for key, expected_value in filters.items():
            if metadata.get(key) != expected_value:
                return False

        return True