from src.policy_assistant.change_gate import policy_release_fingerprint
from src.policy_assistant.service import APPROVED_POLICIES, ApprovedPolicyAssistant, PolicyDocument


def test_policy_release_fingerprint_is_stable_and_changes_with_policy_content():
    original = policy_release_fingerprint(APPROVED_POLICIES)
    reordered = policy_release_fingerprint(tuple(reversed(APPROVED_POLICIES)))
    changed = policy_release_fingerprint((
        PolicyDocument(
            document_id=APPROVED_POLICIES[0].document_id,
            title=APPROVED_POLICIES[0].title,
            department=APPROVED_POLICIES[0].department,
            version=APPROVED_POLICIES[0].version,
            text="A changed policy body.",
        ),
        *APPROVED_POLICIES[1:],
    ))

    assert original.startswith("sha256:")
    assert reordered == original
    assert changed != original


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


def test_policy_change_store_keeps_content_light_records(tmp_path):
    from src.policy_assistant.audit import PolicyChangeStore

    store = PolicyChangeStore(str(tmp_path / "decisions.jsonl"))
    record = store.record({
        "passed": True,
        "regressions": [],
        "improvements": ["retrieval_accuracy"],
        "unchanged": ["safe_abstention_rate"],
        "baseline": {"retrieval_accuracy": 0.8, "safe_abstention_rate": 1.0},
        "candidate": {"retrieval_accuracy": 1.0, "safe_abstention_rate": 1.0},
        "baseline_snapshot": [{"document_id": "finance-v1", "department": "finance", "version": "1"}],
        "candidate_snapshot": [{"document_id": "finance-v2", "department": "finance", "version": "2"}],
        "baseline_fingerprint": "sha256:baseline",
        "candidate_fingerprint": "sha256:candidate",
    }, note="Quarterly policy update")

    recent = store.recent()

    assert recent[0]["change_id"] == record["change_id"]
    assert recent[0]["note"] == "Quarterly policy update"
    assert "text" not in str(recent[0]["candidate_snapshot"])
    assert recent[0]["candidate_fingerprint"] == "sha256:candidate"
