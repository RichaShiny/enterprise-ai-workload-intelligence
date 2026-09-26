import pandas as pd
import pytest

from src.evaluation.routing_release import (
    build_policy_decisions,
    evaluate_routing_policy_change,
    assess_interval_directions,
    paired_bootstrap_intervals,
)


def outcomes():
    shared = {
        "department": "engineering",
        "workflow": "implementation",
        "task_type": "coding",
        "complexity": "medium",
        "sensitivity": "medium",
        "business_priority": 3,
    }
    return pd.DataFrame([
        {
            **shared, "event_id": "a", "tool": "small", "observed_tool": "small",
            "expected_quality": 0.82, "success_probability": 0.82,
            "expected_corrections": 2, "expected_latency_ms": 900,
            "estimated_cost_usd": 0.01, "task_success": 0.82,
            "quality_score": 0.82, "latency_ms": 900, "human_corrections": 2,
        },
        {
            **shared, "event_id": "a", "tool": "frontier", "observed_tool": "small",
            "expected_quality": 0.93, "success_probability": 0.94,
            "expected_corrections": 0, "expected_latency_ms": 1300,
            "estimated_cost_usd": 0.08, "task_success": 0.94,
            "quality_score": 0.93, "latency_ms": 1300, "human_corrections": 0,
        },
        {
            **shared, "event_id": "b", "tool": "small", "observed_tool": "small",
            "expected_quality": 0.82, "success_probability": 0.82,
            "expected_corrections": 2, "expected_latency_ms": 850,
            "estimated_cost_usd": 0.01, "task_success": 0.82,
            "quality_score": 0.82, "latency_ms": 850, "human_corrections": 2,
        },
        {
            **shared, "event_id": "b", "tool": "frontier", "observed_tool": "small",
            "expected_quality": 0.93, "success_probability": 0.94,
            "expected_corrections": 0, "expected_latency_ms": 1400,
            "estimated_cost_usd": 0.08, "task_success": 0.94,
            "quality_score": 0.93, "latency_ms": 1400, "human_corrections": 0,
        },
    ])


def test_release_report_compares_matched_events_and_flags_cost_regression():
    report = evaluate_routing_policy_change(
        outcomes(), "balanced", "reliability_first", default_tolerance=0.001
    )

    assert report.evaluated_events == 2
    assert report.candidate["success_rate"] > report.baseline["success_rate"]
    assert report.candidate["cost_per_event_usd"] > report.baseline["cost_per_event_usd"]
    assert "cost_per_event_usd" in report.regressions
    assert not report.release_ready
    assert "counterfactual" in report.evidence.lower()
    assert report.confidence_intervals["cost_per_event_usd"]["lower"] > 0
    assert report.uncertainty_assessment["cost_per_event_usd"] == "confident_regression"


def test_build_policy_decisions_is_deterministic_and_one_per_event():
    decisions = build_policy_decisions(outcomes(), "balanced")

    assert decisions["event_id"].tolist() == ["a", "b"]
    assert len(decisions) == 2


def test_release_report_rejects_incomplete_outcomes():
    with pytest.raises(ValueError, match="missing required columns"):
        evaluate_routing_policy_change(
            pd.DataFrame([{"event_id": "a", "tool": "small"}]),
            "balanced",
            "strict",
        )


def test_paired_bootstrap_intervals_reject_unaligned_event_ids():
    baseline = build_policy_decisions(outcomes(), "balanced")
    candidate = build_policy_decisions(outcomes(), "strict")
    candidate.loc[0, "event_id"] = "different"

    with pytest.raises(ValueError, match="aligned event IDs"):
        paired_bootstrap_intervals(baseline, candidate, samples=10)


def test_interval_assessment_marks_zero_crossing_as_inconclusive():
    assessment = assess_interval_directions(
        {"success_rate": {"lower": -0.01, "upper": 0.02}},
        {"success_rate": True},
    )

    assert assessment == {"success_rate": "inconclusive"}
