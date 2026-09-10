from src.api.main import (
    OutcomeRequest,
    RouteRequest,
    select_recommendation,
    summarize_events,
)
from src.telemetry.schema import TelemetryEvent
from src.telemetry.store import TelemetryStore


def test_high_risk_workloads_use_explicit_frontier_guardrail():
    request = RouteRequest(
        task_type="summarization",
        sensitivity="medium",
        risk_level="high",
    )

    decision = select_recommendation(request)

    assert decision["recommended_strategy"] == "direct_frontier"
    assert decision["routing_source"] == "risk_guardrail"


def test_sufficient_observed_telemetry_informs_recommendation(tmp_path):
    store = TelemetryStore(str(tmp_path / "events.jsonl"))

    for index in range(30):
        store.log(TelemetryEvent(
            workload_id=f"telemetry-{index}",
            task_type="retrieval",
            complexity="medium",
            sensitivity="low",
            strategy="direct_small",
            model="small-model",
            latency_ms=250.0,
            input_tokens=50,
            output_tokens=25,
            total_tokens=75,
            escalated=False,
            verification_passed=True,
            verification_confidence=0.95,
            estimated_cost_usd=0.002,
            success=True,
        ))

    decision = select_recommendation(
        RouteRequest(
            task_type="retrieval",
            complexity="medium",
            sensitivity="low",
            risk_level="low",
        ),
        store=store,
    )

    assert decision["recommended_strategy"] == "direct_small"
    assert decision["routing_source"] == "observed_telemetry"
    assert decision["sample_count"] == 30
    assert decision["estimated_cost_usd"] == 0.002
    assert decision["policy"]["min_success_probability"] == 0.80
    assert decision["candidates"][0]["strategy"] == "direct_small"


def test_outcome_schema_excludes_customer_content():
    fields = OutcomeRequest.model_fields

    assert "prompt" not in fields
    assert "output" not in fields
    assert "model_output" not in fields


def test_insights_distinguish_observed_and_pending_outcomes():
    report = summarize_events([
        {
            "strategy": "direct_small",
            "latency_ms": 200.0,
            "estimated_cost_usd": 0.002,
            "success": True,
            "recommended_strategy": "verified_cascade",
        },
        {
            "strategy": "verified_cascade",
            "latency_ms": 800.0,
            "estimated_cost_usd": 0.02,
            "success": None,
            "recommended_strategy": "verified_cascade",
        },
    ])

    assert report["events_recorded"] == 2
    assert report["completed_outcomes"] == 1
    assert report["outcomes_pending"] == 1
    assert report["observed_success_rate"] == 1.0
    assert report["shadow_recommendation_disagreements"] == 1


def test_console_is_served_as_an_operator_interface():
    from fastapi.testclient import TestClient
    from src.api.main import app

    response = TestClient(app).get("/console")

    assert response.status_code == 200
    assert "Evaluate a workload" in response.text
    assert "Recent policy-change decisions" in response.text
    assert "OPTIONAL MODEL SUMMARY" in response.text


def test_policy_assistant_api_returns_grounded_evidence():
    from fastapi.testclient import TestClient
    from src.api.main import app

    response = TestClient(app).post(
        "/policy-assistant",
        json={"question": "What approval is required for vendor spend above 25000?"},
    )

    assert response.status_code == 200
    assert response.json()["policy_result"]["grounded"] is True
    assert response.json()["policy_result"]["evidence"][0]["department"] == "finance"
    assert response.json()["model_summary"]["status"] == "disabled"


def test_policy_assistant_provider_status_does_not_expose_configuration_secrets():
    from fastapi.testclient import TestClient
    from src.api.main import app

    response = TestClient(app).get("/policy-assistant/provider-status")

    assert response.status_code == 200
    assert response.json()["provider"] == "openai"
    assert "api_key" not in response.text.lower()


def test_policy_assistant_evaluation_endpoint_exposes_demo_quality_metrics():
    from fastapi.testclient import TestClient
    from src.api.main import app

    response = TestClient(app).get("/policy-assistant/evaluation")

    assert response.status_code == 200
    assert response.json()["retrieval_accuracy"] == 1.0
    assert response.json()["safe_abstention_rate"] == 1.0


def test_policy_change_gate_api_reports_a_release_decision(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from src.api.main import app
    from src.policy_assistant.audit import PolicyChangeStore
    from src.policy_assistant.service import APPROVED_POLICIES
    import src.api.main as api_main

    monkeypatch.setattr(api_main, "policy_change_store", PolicyChangeStore(str(tmp_path / "changes.jsonl")))

    response = TestClient(app).post(
        "/policy-assistant/change-gate",
        json={"candidate_policies": [
            {
                "document_id": policy.document_id,
                "title": policy.title,
                "department": policy.department,
                "version": policy.version,
                "text": policy.text,
            }
            for policy in APPROVED_POLICIES
        ]},
    )

    assert response.status_code == 200
    assert response.json()["passed"] is True
    assert response.json()["candidate_fingerprint"].startswith("sha256:")


def test_policy_change_history_reports_content_light_audit_records(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from src.api.main import app
    from src.policy_assistant.audit import PolicyChangeStore
    import src.api.main as api_main

    monkeypatch.setattr(api_main, "policy_change_store", PolicyChangeStore(str(tmp_path / "changes.jsonl")))
    client = TestClient(app)
    candidate_policies = [{
        "document_id": policy.document_id,
        "title": policy.title,
        "department": policy.department,
        "version": policy.version,
        "text": policy.text,
    } for policy in __import__("src.policy_assistant.service", fromlist=["APPROVED_POLICIES"]).APPROVED_POLICIES]

    response = client.post(
        "/policy-assistant/change-gate",
        json={"candidate_policies": candidate_policies, "note": "Quarterly review"},
    )
    history = client.get("/policy-assistant/change-history")

    assert response.status_code == 200
    assert response.json()["audit"]["note"] == "Quarterly review"
    assert history.status_code == 200
    assert history.json()["records"][0]["note"] == "Quarterly review"
    assert "text" not in str(history.json()["records"][0]["candidate_snapshot"])
    assert history.json()["records"][0]["candidate_fingerprint"].startswith("sha256:")
