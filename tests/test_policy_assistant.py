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
    assert result["retrieval"]["ranking_method"] == "contextual_bm25"
    assert result["retrieval"]["abstention_threshold"] == 0.20
    assert result["retrieval"]["candidate_limit"] == 3
    assert result["retrieval"]["confidence_status"] == "confident"
    assert result["retrieval"]["candidate_diagnostics"][0] == {
        "rank": 1,
        "document_id": "finance-expense-retention",
        "department": "finance",
        "version": "2026.1",
        "relevance_score": 0.8,
        "ranking_score": result["evidence"][0]["ranking_score"],
        "eligible": True,
        "selected": True,
    }
    assert result["evidence"][0]["matched_query_terms"] == [
        "expense", "finance", "records", "retained"
    ]
    assert "Matched 4 of 5" in result["evidence"][0]["score_explanation"]
    assert len(result["evidence"]) == 1
    assert "seven years" in result["answer"]


def test_policy_assistant_abstains_without_matching_evidence():
    result = ApprovedPolicyAssistant().answer(
        "Which office has the best parking?"
    )

    assert result["grounded"] is False
    assert result["abstained"] is True
    assert result["evidence"] == []
    assert result["retrieval"]["abstention_threshold"] == 0.20
    assert result["retrieval"]["confidence_status"] == "insufficient_evidence"


def test_policy_assistant_abstains_when_top_candidates_are_indistinguishable():
    policies = (
        PolicyDocument("retention-a", "Retention requirements", "finance", "1", "Records are retained."),
        PolicyDocument("retention-b", "Retention requirements", "finance", "1", "Records are retained."),
    )

    result = ApprovedPolicyAssistant(policies).answer("What are the retention requirements?")

    assert result["grounded"] is False
    assert result["abstained"] is True
    assert result["evidence"] == []
    assert result["retrieval"]["confidence_status"] == "ambiguous"
    assert result["retrieval"]["ranking_margin"] == 0.0
    assert len(result["retrieval"]["candidate_diagnostics"]) == 2
    assert not any(
        candidate["selected"]
        for candidate in result["retrieval"]["candidate_diagnostics"]
    )
    assert all(
        "excerpt" not in candidate
        for candidate in result["retrieval"]["candidate_diagnostics"]
    )
    assert "similarly ranked" in result["answer"]


def test_contextual_identity_disambiguates_policy_with_generic_body_text():
    policies = (
        PolicyDocument(
            "security-record-retention", "Retention requirements", "security", "1",
            "Records must be retained for the required period.",
        ),
        PolicyDocument(
            "finance-expense-retention", "Retention requirements", "finance", "1",
            "Records must be retained for the required period.",
        ),
    )

    result = ApprovedPolicyAssistant(policies).answer(
        "What is the finance expense retention requirement?"
    )

    assert result["evidence"][0]["document_id"] == "finance-expense-retention"
    assert result["retrieval"]["contextualized"] is True
    assert result["evidence"][0]["excerpt"] == policies[1].text


def test_policy_assistant_normalizes_numeric_shorthand_for_exact_retrieval():
    result = ApprovedPolicyAssistant().answer("Who approves vendor spend above 25k?")

    assert result["grounded"] is True
    assert result["evidence"][0]["document_id"] == "finance-spend-approval"
    assert "25000" in result["evidence"][0]["matched_query_terms"]
    assert "k_magnitude" in result["retrieval"]["query_normalization"]


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
