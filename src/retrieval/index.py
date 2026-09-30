from dataclasses import dataclass
from collections import Counter
import math
import re
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


def normalize_retrieval_text(text: str) -> str:
    """Canonicalize common numeric forms without rewriting query meaning."""
    normalized = text.lower()
    normalized = re.sub(r"(?<=\d),(?=\d{3}\b)", "", normalized)

    def expand_suffix(match: re.Match[str]) -> str:
        value = float(match.group(1))
        multiplier = 1_000 if match.group(2) == "k" else 1_000_000
        expanded = value * multiplier
        return str(int(expanded)) if expanded.is_integer() else str(expanded)

    return re.sub(r"\b(\d+(?:\.\d+)?)([km])\b", expand_suffix, normalized)


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


class BM25Retriever:
    """Deterministic Okapi BM25 retrieval with optional metadata filtering."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: List[Dict[str, Any]] = []
        self.term_frequencies: List[Counter[str]] = []
        self.document_frequencies: Counter[str] = Counter()
        self.document_lengths: List[int] = []
        self.average_document_length = 0.0
        self._fitted = False

    @staticmethod
    def _tokens(text: str) -> List[str]:
        return re.findall(r"[a-z0-9]+", normalize_retrieval_text(text))

    def fit(self, documents: List[Dict[str, Any]]) -> None:
        self.documents = documents
        tokenized = [self._tokens(document["text"]) for document in documents]
        self.term_frequencies = [Counter(tokens) for tokens in tokenized]
        self.document_lengths = [len(tokens) for tokens in tokenized]
        self.document_frequencies = Counter(
            term for frequencies in self.term_frequencies for term in frequencies
        )
        self.average_document_length = (
            sum(self.document_lengths) / len(self.document_lengths)
            if self.document_lengths else 0.0
        )
        self._fitted = True

    def search(
        self,
        query: str,
        top_k: int = 5,
        metadata_filters: Dict[str, Any] | None = None,
    ) -> List[RetrievalResult]:
        if not self._fitted:
            raise RuntimeError("Retriever must be fit before calling search().")

        query_terms = self._tokens(query)
        candidates = [
            index for index, document in enumerate(self.documents)
            if not metadata_filters or LexicalRetriever._matches_metadata(
                document.get("metadata", {}), metadata_filters
            )
        ]
        document_count = len(self.documents)
        scored = []
        for index in candidates:
            score = 0.0
            frequencies = self.term_frequencies[index]
            length = self.document_lengths[index]
            for term in query_terms:
                frequency = frequencies[term]
                if not frequency:
                    continue
                document_frequency = self.document_frequencies[term]
                inverse_frequency = math.log(
                    1 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                normalization = frequency + self.k1 * (
                    1 - self.b + self.b * length / max(self.average_document_length, 1)
                )
                score += inverse_frequency * frequency * (self.k1 + 1) / normalization
            scored.append((index, score))

        ranked = sorted(
            scored,
            key=lambda item: (-item[1], self.documents[item[0]]["document_id"]),
        )[:top_k]
        return [
            RetrievalResult(
                document_id=self.documents[index]["document_id"],
                text=self.documents[index]["text"],
                score=float(score),
                metadata=self.documents[index].get("metadata", {}),
            )
            for index, score in ranked
        ]
