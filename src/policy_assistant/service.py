from dataclasses import asdict, dataclass
from typing import Any
import re



STOP_WORDS = {
    "a", "an", "and", "are", "can", "do", "for", "how", "i", "in",
    "is", "of", "on", "our", "the", "to", "what", "when", "with", "you",
}


@dataclass(frozen=True)
class PolicyDocument:
    document_id: str
    title: str
    department: str
    version: str
    text: str


@dataclass(frozen=True)
class PolicyEvidence:
    document_id: str
    title: str
    department: str
    version: str
    excerpt: str
    relevance_score: float
    ranking_score: float
    ranking_method: str


from src.policy_assistant.catalog import load_policy_catalog


APPROVED_POLICIES = tuple(
    PolicyDocument(**policy)
    for policy in load_policy_catalog()
)


class ApprovedPolicyAssistant:
    """A compact, deterministic evidence retriever for the product demo.

    It intentionally returns policy evidence, not an invented generative answer.
    """

    def __init__(
        self,
        policies: tuple[PolicyDocument, ...] = APPROVED_POLICIES,
        semantic_reranker: Any | None = None,
    ):
        self.policies = policies
        self.semantic_reranker = semantic_reranker
        from src.retrieval.index import BM25Retriever

        self.retriever = BM25Retriever()
        self.retriever.fit([
            {
                "document_id": policy.document_id,
                "text": self._contextualized_text(policy),
                "metadata": {"department": policy.department},
            }
            for policy in policies
        ])

    def answer(self, question: str, department: str | None = None) -> dict:
        policies_by_id = {policy.document_id: policy for policy in self.policies}
        matches = self.retriever.search(
            question,
            top_k=3,
            metadata_filters={"department": department.lower()} if department else None,
        )
        lexical = [
            self._evidence(question, policies_by_id[match.document_id], match.score)
            for match in matches
        ]
        evidence = self._rerank(question, lexical)

        primary = evidence[0] if evidence else None
        if primary is None or primary.relevance_score < 0.20:
            return {
                "answer": (
                    "I could not find sufficient approved policy evidence for that question. "
                    "Route it to the policy owner or add an approved source before acting."
                ),
                "grounded": False,
                "abstained": True,
                "reason": "No approved policy matched the question.",
                "retrieval": self._retrieval_metadata(),
                "evidence": [],
            }

        relevant = [
            item for item in evidence
            if item.relevance_score >= 0.20
            and item.relevance_score >= primary.relevance_score * 0.50
        ]
        return {
            "answer": f"According to {primary.title}, {primary.excerpt}",
            "grounded": True,
            "abstained": False,
            "reason": "Answer is an evidence extract from the highest-ranking approved policy.",
            "retrieval": self._retrieval_metadata(),
            "evidence": [asdict(item) for item in relevant],
        }

    def _rerank(self, question: str, evidence: list[PolicyEvidence]) -> list[PolicyEvidence]:
        """Apply semantic ordering only to lexical candidates with usable evidence."""
        if not self.semantic_reranker or not evidence:
            return evidence
        from src.retrieval.index import RetrievalResult

        policies_by_id = {policy.document_id: policy for policy in self.policies}
        results = [
            RetrievalResult(
                document_id=item.document_id,
                text=self._contextualized_text(policies_by_id[item.document_id]),
                score=item.relevance_score,
                metadata={
                    "title": item.title,
                    "department": item.department,
                    "version": item.version,
                },
            )
            for item in evidence
        ]
        semantic = self.semantic_reranker.rerank(question, results)
        score_by_id = {item.document_id: item.ranking_score for item in semantic}
        return sorted(
            [
                PolicyEvidence(
                    **{**asdict(item), "ranking_score": score_by_id[item.document_id], "ranking_method": "semantic"}
                )
                for item in evidence
            ],
            key=lambda item: item.ranking_score,
            reverse=True,
        )

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {
            term for term in re.findall(r"[a-z0-9]+", text.lower())
            if term not in STOP_WORDS and len(term) > 1
        }

    @staticmethod
    def _contextualized_text(policy: PolicyDocument) -> str:
        """Prepend stable document identity so retrieval retains policy context."""
        identity = (
            f"Approved policy: {policy.title}. Department: {policy.department}. "
            f"Version: {policy.version}. Document ID: {policy.document_id}."
        )
        return f"{identity}\n{policy.text}"

    def _retrieval_metadata(self) -> dict:
        return {
            "ranking_method": "semantic" if self.semantic_reranker else "contextual_bm25",
            "contextualized": True,
            "context_fields": ["title", "department", "version", "document_id"],
        }

    def _evidence(
        self, question: str, policy: PolicyDocument, ranking_score: float = 0.0
    ) -> PolicyEvidence:
        query_terms = self._terms(question)
        policy_terms = self._terms(self._contextualized_text(policy))
        score = len(query_terms & policy_terms) / max(len(query_terms), 1)
        return PolicyEvidence(
            document_id=policy.document_id,
            title=policy.title,
            department=policy.department,
            version=policy.version,
            excerpt=policy.text,
            relevance_score=round(score, 3),
            ranking_score=round(ranking_score, 3),
            ranking_method="contextual_bm25",
        )
