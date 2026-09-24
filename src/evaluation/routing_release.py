"""Counterfactual release checks for workload-routing policies.

This module evaluates two routing policies against the same potential-outcome
table.  It is intentionally a pre-release simulation tool: its estimates are
not evidence of live vendor or production performance.
"""

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from src.evaluation.regression import RegressionEvaluator
from src.routing.policy import POLICY_CONFIGS, select_tool


REQUIRED_COLUMNS = {
    "event_id",
    "tool",
    "estimated_cost_usd",
    "task_success",
    "quality_score",
    "latency_ms",
    "human_corrections",
}


@dataclass
class RoutingReleaseReport:
    """A serializable release decision based on matched simulated workloads."""

    baseline_policy: str
    candidate_policy: str
    evaluated_events: int
    baseline: dict[str, float]
    candidate: dict[str, float]
    deltas: dict[str, float]
    regressions: list[str]
    improvements: list[str]
    unchanged: list[str]
    release_ready: bool
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate_outcomes(outcomes: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(outcomes.columns)
    if missing:
        raise ValueError(
            "Counterfactual outcomes are missing required columns: "
            + ", ".join(sorted(missing))
        )
    if outcomes.empty:
        raise ValueError("Counterfactual outcomes cannot be empty.")
    if outcomes["event_id"].isna().any():
        raise ValueError("Counterfactual outcomes contain an empty event_id.")


def build_policy_decisions(outcomes: pd.DataFrame, policy: str) -> pd.DataFrame:
    """Select exactly one potential outcome per event using an existing policy."""
    if policy not in POLICY_CONFIGS:
        raise ValueError(
            f"Unknown policy: {policy}. Choose from {list(POLICY_CONFIGS)}."
        )

    _validate_outcomes(outcomes)
    decisions = []
    for event_id, group in outcomes.groupby("event_id", sort=True):
        decision = select_tool(group, policy=policy)
        decision["event_id"] = event_id
        decisions.append(decision)
    return pd.DataFrame(decisions)


def summarize_policy_decisions(decisions: pd.DataFrame) -> dict[str, float]:
    """Summarize a matched policy run in units that are comparable per event."""
    if decisions.empty:
        raise ValueError("Policy decisions cannot be empty.")
    return {
        "cost_per_event_usd": float(decisions["estimated_cost_usd"].mean()),
        "success_rate": float(decisions["task_success"].mean()),
        "quality_score": float(decisions["quality_score"].mean()),
        "latency_ms": float(decisions["latency_ms"].mean()),
        "corrections_per_event": float(decisions["human_corrections"].mean()),
        "constraints_satisfied_rate": float(
            (decisions["decision_status"] == "constraints_satisfied").mean()
        ),
        "fallback_rate": float(
            (decisions["decision_status"] == "fallback_best_available").mean()
        ),
    }


def evaluate_routing_policy_change(
    outcomes: pd.DataFrame,
    baseline_policy: str,
    candidate_policy: str,
    *,
    default_tolerance: float = 0.02,
    metric_tolerances: dict[str, float] | None = None,
) -> RoutingReleaseReport:
    """Compare a candidate policy with a baseline on identical event IDs.

    Tolerances are absolute differences in the returned metric units.  For
    example, a success-rate tolerance of ``0.02`` permits a two percentage
    point decrease before the release is flagged.
    """
    if default_tolerance < 0:
        raise ValueError("default_tolerance must be non-negative.")

    baseline_decisions = build_policy_decisions(outcomes, baseline_policy)
    candidate_decisions = build_policy_decisions(outcomes, candidate_policy)
    if set(baseline_decisions["event_id"]) != set(candidate_decisions["event_id"]):
        raise ValueError("Policies must be evaluated on the same event population.")

    baseline = summarize_policy_decisions(baseline_decisions)
    candidate = summarize_policy_decisions(candidate_decisions)
    higher_is_better = {
        "cost_per_event_usd": False,
        "success_rate": True,
        "quality_score": True,
        "latency_ms": False,
        "corrections_per_event": False,
        "constraints_satisfied_rate": True,
        "fallback_rate": False,
    }
    comparison = RegressionEvaluator(
        default_tolerance=default_tolerance,
        metric_tolerances=metric_tolerances,
    ).compare(baseline, candidate, higher_is_better)
    return RoutingReleaseReport(
        baseline_policy=baseline_policy,
        candidate_policy=candidate_policy,
        evaluated_events=len(baseline_decisions),
        baseline=baseline,
        candidate=candidate,
        deltas={metric: candidate[metric] - baseline[metric] for metric in baseline},
        regressions=comparison.regressions,
        improvements=comparison.improvements,
        unchanged=comparison.unchanged,
        release_ready=comparison.passed,
        evidence=(
            "Matched counterfactual simulation on the same workload events; "
            "not a claim about live provider or production performance."
        ),
    )
