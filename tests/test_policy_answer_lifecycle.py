from src.policy_assistant.lifecycle import decide_policy_response


ROUTING = {"recommended_strategy": "direct_small", "routing_source": "observed_telemetry"}
GROUNDED = {"abstained": False}


def test_accepts_a_provider_answer_only_after_citation_validation():
    decision = decide_policy_response(GROUNDED, {
        "status": "generated",
        "citations": [{"document_id": "finance-expense-retention", "version": "2026.1"}],
    }, ROUTING)

    assert decision["status"] == "accepted"
    assert decision["response_source"] == "provider_summary"
    assert decision["verification"]["status"] == "passed"


def test_uses_deterministic_evidence_when_provider_is_unavailable():
    decision = decide_policy_response(GROUNDED, {"status": "fallback"}, ROUTING)

    assert decision["status"] == "accepted_with_fallback"
    assert decision["response_source"] == "deterministic_evidence"


def test_escalates_when_retrieval_abstains():
    decision = decide_policy_response({"abstained": True}, {"status": "not_requested"}, ROUTING)

    assert decision["status"] == "escalated"
    assert decision["next_action"] == "Send to policy owner"
