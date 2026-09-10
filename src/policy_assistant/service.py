from dataclasses import asdict, dataclass
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


APPROVED_POLICIES = (
    PolicyDocument(
        document_id="finance-expense-retention",
        title="Expense record retention",
        department="finance",
        version="2026.1",
        text=(
            "Approved expense reports, receipts, and reimbursement records must be retained "
            "for seven years after the end of the fiscal year. Finance owns the retention schedule."
        ),
    ),
    PolicyDocument(
        document_id="finance-spend-approval",
        title="Non-recurring spend approval",
        department="finance",
        version="2026.1",
        text=(
            "Non-recurring vendor spend above 5,000 dollars requires budget-owner approval "
            "before a purchase order is issued. Spend above 25,000 dollars also requires Finance approval."
        ),
    ),
    PolicyDocument(
        document_id="security-access-review",
        title="Privileged access review",
        department="security",
        version="2026.2",
        text=(
            "Privileged access is granted for a documented business purpose, reviewed every 90 days, "
            "and removed within one business day when the purpose ends or employment changes."
        ),
    ),
    PolicyDocument(
        document_id="security-incident-reporting",
        title="Security incident reporting",
        department="security",
        version="2026.2",
        text=(
            "Suspected security incidents must be reported immediately through the incident channel. "
            "Do not include credentials, regulated personal data, or customer secrets in the report."
        ),
    ),
    PolicyDocument(
        document_id="people-flexible-work",
        title="Flexible work eligibility",
        department="people",
        version="2026.1",
        text=(
            "Flexible work arrangements are agreed by the employee and manager and reviewed quarterly. "
            "The arrangement must preserve team coverage, data-security requirements, and core meeting obligations."
        ),
    ),
)


class ApprovedPolicyAssistant:
    """A compact, deterministic evidence retriever for the product demo.

    It intentionally returns policy evidence, not an invented generative answer.
    """

    def __init__(self, policies: tuple[PolicyDocument, ...] = APPROVED_POLICIES):
        self.policies = policies

    def answer(self, question: str, department: str | None = None) -> dict:
        candidates = [
            policy for policy in self.policies
            if not department or policy.department == department.lower()
        ]
        evidence = sorted(
            (self._evidence(question, policy) for policy in candidates),
            key=lambda item: item.relevance_score,
            reverse=True,
        )[:3]

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
            "evidence": [asdict(item) for item in relevant],
        }

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {
            term for term in re.findall(r"[a-z0-9]+", text.lower())
            if term not in STOP_WORDS and len(term) > 1
        }

    def _evidence(self, question: str, policy: PolicyDocument) -> PolicyEvidence:
        query_terms = self._terms(question)
        policy_terms = self._terms(f"{policy.title} {policy.text}")
        score = len(query_terms & policy_terms) / max(len(query_terms), 1)
        return PolicyEvidence(
            document_id=policy.document_id,
            title=policy.title,
            department=policy.department,
            version=policy.version,
            excerpt=policy.text,
            relevance_score=round(score, 3),
        )
