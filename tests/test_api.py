from src.api.main import OutcomeRequest, RouteRequest, summarize_events


def test_high_risk_workloads_route_to_frontier():
    request = RouteRequest(
        task_type="summarization",
        sensitivity="medium",
        risk_level="high",
    )

    from src.api.main import choose_strategy

    assert choose_strategy(request) == "direct_frontier"


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
