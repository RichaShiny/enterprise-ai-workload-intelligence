from src.evaluation.delegation_observability import (
    evaluate_delegation_cohort_balance,
    evaluate_delegation_evidence,
    summarize_delegation_events,
)


def test_delegation_summary_groups_observed_execution_paths_without_causal_claim():
    report = summarize_delegation_events([
        {
            "delegation_execution_path": "efficient_worker", "success": True,
            "latency_ms": 200, "estimated_cost_usd": 0.002, "total_tokens": 80,
        },
        {
            "delegation_execution_path": "primary_route", "success": False,
            "latency_ms": 800, "estimated_cost_usd": 0.02, "total_tokens": 600,
        },
    ])

    assert report["delegated"]["events"] == 1
    assert report["delegated"]["success_rate"] == 1.0
    assert report["retained_on_primary"]["estimated_cost_usd"] == 0.02
    assert "not causal" in report["scope"]


def test_evidence_gate_requires_completed_outcomes_on_both_paths():
    report = summarize_delegation_events([
        {"delegation_execution_path": "efficient_worker", "success": True, "latency_ms": 10},
        {"delegation_execution_path": "primary_route", "success": None, "latency_ms": 10},
    ])

    evidence = evaluate_delegation_evidence(report, minimum_completed_events=1)

    assert evidence["by_execution_path"]["efficient_worker"]["sufficient"] is True
    assert evidence["by_execution_path"]["primary_route"]["sufficient"] is False
    assert evidence["comparison_ready"] is False


def test_cohort_balance_flags_different_operation_mix():
    events = [
        {"delegation_execution_path": "efficient_worker", "delegation_operation": "bulk_context", "task_type": "coding", "sensitivity": "low"},
        {"delegation_execution_path": "primary_route", "delegation_operation": "debugging", "task_type": "coding", "sensitivity": "low"},
    ]

    balance = evaluate_delegation_cohort_balance(events, maximum_share_gap=0.20)

    assert balance["comparable"] is False
    assert balance["dimensions"]["delegation_operation"]["maximum_observed_gap"] == 1.0
    assert "do not attribute" in balance["reason"]
