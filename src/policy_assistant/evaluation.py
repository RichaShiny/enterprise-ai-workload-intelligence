"""Small, inspectable evaluation set for the policy-retrieval demonstration."""

from dataclasses import dataclass

from src.policy_assistant.service import ApprovedPolicyAssistant


@dataclass(frozen=True)
class PolicyEvalCase:
    question: str
    expected_document_id: str | None
    department: str | None = None


POLICY_EVAL_CASES = (
    PolicyEvalCase(
        question="How long must finance expense reports and receipts be retained?",
        expected_document_id="finance-expense-retention",
        department="finance",
    ),
    PolicyEvalCase(
        question="Who approves non-recurring vendor spend above 25000 dollars?",
        expected_document_id="finance-spend-approval",
        department="finance",
    ),
    PolicyEvalCase(
        question="How often is privileged access reviewed?",
        expected_document_id="security-access-review",
        department="security",
    ),
    PolicyEvalCase(
        question="Where should a suspected security incident be reported?",
        expected_document_id="security-incident-reporting",
        department="security",
    ),
    PolicyEvalCase(
        question="Which office has the best parking?",
        expected_document_id=None,
    ),
)


def evaluate_policy_assistant(
    assistant: ApprovedPolicyAssistant | None = None,
    cases: tuple[PolicyEvalCase, ...] = POLICY_EVAL_CASES,
) -> dict:
    """Evaluate retrieval accuracy and safe abstention on the demo set."""
    assistant = assistant or ApprovedPolicyAssistant()
    outcomes = []

    for case in cases:
        result = assistant.answer(case.question, department=case.department)
        retrieved_id = result["evidence"][0]["document_id"] if result["evidence"] else None
        correct = retrieved_id == case.expected_document_id
        outcomes.append({
            "question": case.question,
            "expected_document_id": case.expected_document_id,
            "retrieved_document_id": retrieved_id,
            "grounded": result["grounded"],
            "abstained": result["abstained"],
            "correct": correct,
        })

    answerable = [item for item in outcomes if item["expected_document_id"]]
    unanswerable = [item for item in outcomes if not item["expected_document_id"]]
    correct_retrievals = sum(item["correct"] for item in answerable)
    correct_abstentions = sum(item["correct"] and item["abstained"] for item in unanswerable)

    return {
        "cases": len(outcomes),
        "retrieval_accuracy": correct_retrievals / len(answerable) if answerable else 0.0,
        "safe_abstention_rate": correct_abstentions / len(unanswerable) if unanswerable else 0.0,
        "overall_accuracy": sum(item["correct"] for item in outcomes) / len(outcomes) if outcomes else 0.0,
        "results": outcomes,
        "scope": "Demonstration-only benchmark using fictional approved-policy content.",
    }
