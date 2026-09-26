"""Counterfactual release checks for workload-routing policies.

This module evaluates two routing policies against the same potential-outcome
table.  It is intentionally a pre-release simulation tool: its estimates are
not evidence of live vendor or production performance.
"""

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
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
    confidence_intervals: dict[str, dict[str, float]]
    uncertainty_assessment: dict[str, str]
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


def paired_bootstrap_intervals(
    baseline_decisions: pd.DataFrame,
    candidate_decisions: pd.DataFrame,
    *,
    samples: int = 1_000,
    random_seed: int = 0,
    confidence_level: float = 0.95,
) -> dict[str, dict[str, float]]:
    """Estimate uncertainty of paired policy deltas by resampling event IDs."""
    if samples < 1:
        raise ValueError("samples must be at least 1.")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between 0 and 1.")
    baseline = baseline_decisions.sort_values("event_id").reset_index(drop=True)
    candidate = candidate_decisions.sort_values("event_id").reset_index(drop=True)
    if baseline["event_id"].tolist() != candidate["event_id"].tolist():
        raise ValueError("Bootstrap intervals require aligned event IDs.")

    series = {
        "cost_per_event_usd": (baseline["estimated_cost_usd"].to_numpy(), candidate["estimated_cost_usd"].to_numpy()),
        "success_rate": (baseline["task_success"].to_numpy(), candidate["task_success"].to_numpy()),
        "quality_score": (baseline["quality_score"].to_numpy(), candidate["quality_score"].to_numpy()),
        "latency_ms": (baseline["latency_ms"].to_numpy(), candidate["latency_ms"].to_numpy()),
        "corrections_per_event": (baseline["human_corrections"].to_numpy(), candidate["human_corrections"].to_numpy()),
        "constraints_satisfied_rate": ((baseline["decision_status"] == "constraints_satisfied").to_numpy(dtype=float), (candidate["decision_status"] == "constraints_satisfied").to_numpy(dtype=float)),
        "fallback_rate": ((baseline["decision_status"] == "fallback_best_available").to_numpy(dtype=float), (candidate["decision_status"] == "fallback_best_available").to_numpy(dtype=float)),
    }
    indices = np.random.default_rng(random_seed).integers(0, len(baseline), size=(samples, len(baseline)))
    alpha = (1 - confidence_level) / 2
    return {
        metric: {
            "lower": float(np.quantile(candidate_values[indices].mean(axis=1) - baseline_values[indices].mean(axis=1), alpha)),
            "upper": float(np.quantile(candidate_values[indices].mean(axis=1) - baseline_values[indices].mean(axis=1), 1 - alpha)),
        }
        for metric, (baseline_values, candidate_values) in series.items()
    }


def assess_interval_directions(
    confidence_intervals: dict[str, dict[str, float]],
    higher_is_better: dict[str, bool],
) -> dict[str, str]:
    """Classify whether a bootstrap interval supports a beneficial or harmful direction."""
    assessment = {}
    for metric, interval in confidence_intervals.items():
        lower, upper = interval["lower"], interval["upper"]
        if lower <= 0 <= upper:
            assessment[metric] = "inconclusive"
            continue
        candidate_increased = lower > 0
        beneficial = candidate_increased == higher_is_better.get(metric, True)
        assessment[metric] = "confident_improvement" if beneficial else "confident_regression"
    return assessment


def evaluate_routing_policy_change(
    outcomes: pd.DataFrame,
    baseline_policy: str,
    candidate_policy: str,
    *,
    default_tolerance: float = 0.02,
    metric_tolerances: dict[str, float] | None = None,
    bootstrap_samples: int = 1_000,
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
    confidence_intervals = paired_bootstrap_intervals(
        baseline_decisions,
        candidate_decisions,
        samples=bootstrap_samples,
    )
    uncertainty_assessment = assess_interval_directions(
        confidence_intervals,
        higher_is_better,
    )
    return RoutingReleaseReport(
        baseline_policy=baseline_policy,
        candidate_policy=candidate_policy,
        evaluated_events=len(baseline_decisions),
        baseline=baseline,
        candidate=candidate,
        deltas={metric: candidate[metric] - baseline[metric] for metric in baseline},
        confidence_intervals=confidence_intervals,
        uncertainty_assessment=uncertainty_assessment,
        regressions=comparison.regressions,
        improvements=comparison.improvements,
        unchanged=comparison.unchanged,
        release_ready=comparison.passed,
        evidence=(
            "Matched counterfactual simulation on the same workload events; "
            "not a claim about live provider or production performance."
        ),
    )
