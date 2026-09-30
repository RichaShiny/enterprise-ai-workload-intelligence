from dataclasses import asdict, dataclass
from typing import Any
import hashlib
import json
import re



STOP_WORDS = {
    "a", "an", "and", "are", "be", "can", "do", "for", "how", "i", "in",
    "is", "must", "of", "on", "our", "the", "to", "what", "when", "with", "you",
}
ABSTENTION_THRESHOLD = 0.20
MINIMUM_RANKING_MARGIN = 0.05
MAX_QUESTION_LENGTH = 500
ABSTENTION_REASON_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
ABSTENTION_REASON_AMBIGUOUS_RETRIEVAL = "ambiguous_retrieval"


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
    provenance_id: str
    excerpt: str
    relevance_score: float
    ranking_score: float
    ranking_method: str
    matched_query_terms: list[str]
    score_explanation: str


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
        question = question.strip()
        if not question or len(question) > MAX_QUESTION_LENGTH:
            return {
                "answer": (
                    "The policy question must contain text and be no longer than "
                    f"{MAX_QUESTION_LENGTH} characters."
                ),
                "grounded": False,
                "abstained": True,
                "reason": "Question failed policy-assistant input validation.",
                "retrieval": {
                    "confidence_status": "invalid_input",
                    "candidate_diagnostics": [],
                },
                "evidence": [],
            }
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
        retrieval = self._retrieval_metadata(evidence)
        if primary is None or primary.relevance_score < ABSTENTION_THRESHOLD:
            return {
                "answer": (
                    "I could not find sufficient approved policy evidence for that question. "
                    "Route it to the policy owner or add an approved source before acting."
                ),
                "grounded": False,
                "abstained": True,
                "abstention_reason_code": ABSTENTION_REASON_INSUFFICIENT_EVIDENCE,
                "reason": "No approved policy matched the question.",
                "retrieval": retrieval,
                "evidence": [],
            }

        if retrieval["confidence_status"] == "ambiguous":
            return {
                "answer": (
                    "I found multiple similarly ranked approved policies and cannot safely "
                    "choose one. Add a department or policy identifier, or route the question "
                    "to the policy owner."
                ),
                "grounded": False,
                "abstained": True,
                "abstention_reason_code": ABSTENTION_REASON_AMBIGUOUS_RETRIEVAL,
                "reason": "Top approved-policy candidates were too close to distinguish safely.",
                "retrieval": retrieval,
                "evidence": [],
            }

        relevant = [
            item for item in evidence
            if item.relevance_score >= ABSTENTION_THRESHOLD
            and item.relevance_score >= primary.relevance_score * 0.50
        ]
        return {
            "answer": f"According to {primary.title}, {primary.excerpt}",
            "grounded": True,
            "abstained": False,
            "abstention_reason_code": None,
            "reason": "Answer is an evidence extract from the highest-ranking approved policy.",
            "retrieval": retrieval,
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
        from src.retrieval.index import normalize_retrieval_text

        return {
            term for term in re.findall(r"[a-z0-9]+", normalize_retrieval_text(text))
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

    @staticmethod
    def _provenance_id(policy: PolicyDocument) -> str:
        """Return a stable identifier for the exact approved document revision."""
        canonical_document = json.dumps(
            asdict(policy), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(canonical_document).hexdigest()}"

    def _retrieval_metadata(self, evidence: list[PolicyEvidence]) -> dict:
        primary = evidence[0] if evidence else None
        runner_up = evidence[1] if len(evidence) > 1 else None
        ranking_margin = None
        confidence_status = "insufficient_evidence"
        if primary and primary.relevance_score >= ABSTENTION_THRESHOLD:
            confidence_status = "confident"
            if runner_up and runner_up.relevance_score >= ABSTENTION_THRESHOLD:
                ranking_margin = (
                    primary.ranking_score - runner_up.ranking_score
                ) / max(abs(primary.ranking_score), 1e-9)
                if ranking_margin < MINIMUM_RANKING_MARGIN:
                    confidence_status = "ambiguous"

        candidate_diagnostics = [
            {
                "rank": rank,
                "document_id": item.document_id,
                "department": item.department,
                "version": item.version,
                "relevance_score": item.relevance_score,
                "ranking_score": round(item.ranking_score, 3),
                "eligible": item.relevance_score >= ABSTENTION_THRESHOLD,
                "selected": rank == 1 and confidence_status == "confident",
            }
            for rank, item in enumerate(evidence, start=1)
        ]

        return {
            "ranking_method": "semantic" if self.semantic_reranker else "contextual_bm25",
            "contextualized": True,
            "context_fields": ["title", "department", "version", "document_id"],
            "candidate_limit": 3,
            "abstention_threshold": ABSTENTION_THRESHOLD,
            "minimum_ranking_margin": MINIMUM_RANKING_MARGIN,
            "ranking_margin": round(ranking_margin, 3) if ranking_margin is not None else None,
            "confidence_status": confidence_status,
            "candidate_diagnostics": candidate_diagnostics,
            "relevance_metric": "matched non-stopword query terms / query terms",
            "query_normalization": ["thousands_separators", "k_magnitude", "m_magnitude"],
        }

    def _evidence(
        self, question: str, policy: PolicyDocument, ranking_score: float = 0.0
    ) -> PolicyEvidence:
        query_terms = self._terms(question)
        policy_terms = self._terms(self._contextualized_text(policy))
        matched_terms = sorted(query_terms & policy_terms)
        score = len(matched_terms) / max(len(query_terms), 1)
        return PolicyEvidence(
            document_id=policy.document_id,
            title=policy.title,
            department=policy.department,
            version=policy.version,
            provenance_id=self._provenance_id(policy),
            excerpt=policy.text,
            relevance_score=round(score, 3),
            ranking_score=round(ranking_score, 3),
            ranking_method="contextual_bm25",
            matched_query_terms=matched_terms,
            score_explanation=(
                f"Matched {len(matched_terms)} of {len(query_terms)} normalized query terms; "
                "ranking used contextual BM25."
            ),
        )
