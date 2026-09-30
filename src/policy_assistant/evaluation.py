"""Small, inspectable evaluation set for the policy-retrieval demonstration."""

from dataclasses import dataclass

from src.policy_assistant.service import ApprovedPolicyAssistant


@dataclass(frozen=True)
class PolicyEvalCase:
    question: str
    expected_document_id: str | None
    department: str | None = None
    variants: tuple[str, ...] = ()


POLICY_EVAL_CASES = (
    PolicyEvalCase(
        question="How long must finance expense reports and receipts be retained?",
        expected_document_id="finance-expense-retention",
        department="finance",
        variants=(
            "What is the retention period for finance receipts and expense reports?",
            "Finance expense receipts: how many years do we keep them?",
        ),
    ),
    PolicyEvalCase(
        question="Who approves non-recurring vendor spend above 25000 dollars?",
        expected_document_id="finance-spend-approval",
        department="finance",
        variants=("Who must approve vendor purchases over $25k?",),
    ),
    PolicyEvalCase(
        question="How often is privileged access reviewed?",
        expected_document_id="security-access-review",
        department="security",
        variants=("What is the review cadence for privileged access?",),
    ),
    PolicyEvalCase(
        question="Where should a suspected security incident be reported?",
        expected_document_id="security-incident-reporting",
        department="security",
        variants=("Where do employees report a possible security incident?",),
    ),
    PolicyEvalCase(
        question="Which office has the best parking?",
        expected_document_id=None,
        variants=("Is the moon made of cheese?",),
    ),
)


def evaluate_policy_assistant(
    assistant: ApprovedPolicyAssistant | None = None,
    cases: tuple[PolicyEvalCase, ...] = POLICY_EVAL_CASES,
) -> dict:
    """Evaluate retrieval accuracy and safe abstention on the demo set."""
    assistant = assistant or ApprovedPolicyAssistant()
    outcomes = []
    variant_outcomes = []

    for case in cases:
        result = assistant.answer(case.question, department=case.department)
        retrieved_id = result["evidence"][0]["document_id"] if result["evidence"] else None
        correct = retrieved_id == case.expected_document_id
        outcomes.append({
            "question": case.question,
            "department": case.department,
            "answerability": "answerable" if case.expected_document_id else "unanswerable",
            "expected_document_id": case.expected_document_id,
            "retrieved_document_id": retrieved_id,
            "grounded": result["grounded"],
            "abstained": result["abstained"],
            "correct": correct,
        })
        family_retrievals = [retrieved_id]
        for variant in case.variants:
            variant_result = assistant.answer(variant, department=case.department)
            variant_id = (
                variant_result["evidence"][0]["document_id"]
                if variant_result["evidence"] else None
            )
            family_retrievals.append(variant_id)
            variant_outcomes.append({
                "canonical_question": case.question,
                "question": variant,
                "expected_document_id": case.expected_document_id,
                "retrieved_document_id": variant_id,
                "correct": variant_id == case.expected_document_id,
            })
        outcomes[-1]["variant_consistent"] = (
            len(set(family_retrievals)) == 1
            and family_retrievals[0] == case.expected_document_id
        )

    answerable = [item for item in outcomes if item["expected_document_id"]]
    unanswerable = [item for item in outcomes if not item["expected_document_id"]]
    correct_retrievals = sum(item["correct"] for item in answerable)
    correct_abstentions = sum(item["correct"] and item["abstained"] for item in unanswerable)

    departments = sorted({item["department"] for item in outcomes if item["department"]})
    by_department = {}
    for department in departments:
        department_outcomes = [item for item in outcomes if item["department"] == department]
        by_department[department] = {
            "cases": len(department_outcomes),
            "accuracy": sum(item["correct"] for item in department_outcomes) / len(department_outcomes),
        }

    by_answerability = {
        "answerable": {
            "cases": len(answerable),
            "accuracy": correct_retrievals / len(answerable) if answerable else None,
        },
        "unanswerable": {
            "cases": len(unanswerable),
            "accuracy": correct_abstentions / len(unanswerable) if unanswerable else None,
        },
    }

    return {
        "cases": len(outcomes),
        "retrieval_accuracy": correct_retrievals / len(answerable) if answerable else 0.0,
        "safe_abstention_rate": correct_abstentions / len(unanswerable) if unanswerable else 0.0,
        "overall_accuracy": sum(item["correct"] for item in outcomes) / len(outcomes) if outcomes else 0.0,
        "breakdowns": {
            "by_department": by_department,
            "by_answerability": by_answerability,
        },
        "retrieval_consistency": (
            sum(item["variant_consistent"] for item in outcomes) / len(outcomes)
            if outcomes else 0.0
        ),
        "variants": len(variant_outcomes),
        "variant_results": variant_outcomes,
        "results": outcomes,
        "scope": "Demonstration-only benchmark using fictional approved-policy content.",
    }
