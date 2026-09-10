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
