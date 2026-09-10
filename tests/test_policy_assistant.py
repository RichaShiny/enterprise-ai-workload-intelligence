from src.policy_assistant.service import ApprovedPolicyAssistant


def test_policy_assistant_returns_cited_approved_evidence():
    result = ApprovedPolicyAssistant().answer(
        "How long must finance expense records be retained?"
    )

    assert result["grounded"] is True
    assert result["abstained"] is False
    assert result["evidence"][0]["document_id"] == "finance-expense-retention"
    assert len(result["evidence"]) == 1
    assert "seven years" in result["answer"]


def test_policy_assistant_abstains_without_matching_evidence():
    result = ApprovedPolicyAssistant().answer(
        "Which office has the best parking?"
    )

    assert result["grounded"] is False
    assert result["abstained"] is True
    assert result["evidence"] == []


def test_policy_evaluation_reports_retrieval_and_safe_abstention():
    from src.policy_assistant.evaluation import evaluate_policy_assistant

    report = evaluate_policy_assistant()

    assert report["cases"] == 5
    assert report["retrieval_accuracy"] == 1.0
    assert report["safe_abstention_rate"] == 1.0
    assert report["overall_accuracy"] == 1.0


def test_policy_change_gate_rejects_a_revision_that_breaks_expected_retrieval():
    from src.policy_assistant.change_gate import evaluate_policy_change
    from src.policy_assistant.service import APPROVED_POLICIES, PolicyDocument

    candidate = tuple(
        PolicyDocument(
            document_id="finance-expense-retention-v2" if policy.document_id == "finance-expense-retention" else policy.document_id,
            title=policy.title,
            department=policy.department,
            version="2026.2" if policy.document_id == "finance-expense-retention" else policy.version,
            text=policy.text,
        )
        for policy in APPROVED_POLICIES
    )

    report = evaluate_policy_change(candidate)

    assert report["passed"] is False
    assert "retrieval_accuracy" in report["regressions"]
