"""Aggregate observed results for policy-enforced worker delegation."""

from statistics import mean


def _summary(events: list[dict]) -> dict:
    completed = [event for event in events if event.get("success") is not None]
    latencies = [event["latency_ms"] for event in events if event.get("latency_ms") is not None]
    costs = [event["estimated_cost_usd"] for event in events if event.get("estimated_cost_usd") is not None]
    tokens = [event["total_tokens"] for event in events if event.get("total_tokens") is not None]
    return {
        "events": len(events),
        "completed_outcomes": len(completed),
        "success_rate": (sum(event["success"] for event in completed) / len(completed) if completed else None),
        "average_latency_ms": round(mean(latencies), 2) if latencies else None,
        "estimated_cost_usd": round(sum(costs), 6),
        "average_total_tokens": round(mean(tokens), 2) if tokens else None,
    }


def summarize_delegation_events(events: list[dict]) -> dict:
    """Compare observed outcomes by enforced execution path without causal claims."""
    delegated = [
        event for event in events
        if event.get("delegation_execution_path") == "efficient_worker"
    ]
    retained = [
        event for event in events
        if event.get("delegation_execution_path") == "primary_route"
    ]
    return {
        "delegated": _summary(delegated),
        "retained_on_primary": _summary(retained),
        "scope": (
            "Descriptive observed telemetry grouped by enforced execution path; "
            "differences are not causal estimates because workloads may differ."
        ),
        "privacy": "Aggregates use operational metadata only; prompts and model outputs are excluded.",
    }


def evaluate_delegation_evidence(
    report: dict,
    *,
    minimum_completed_events: int = 20,
) -> dict:
    """State whether each execution path has enough observed outcomes for review."""
    if minimum_completed_events < 1:
        raise ValueError("minimum_completed_events must be at least 1.")

    paths = {
        "efficient_worker": report["delegated"],
        "primary_route": report["retained_on_primary"],
    }
    evidence = {
        path: {
            "completed_outcomes": summary["completed_outcomes"],
            "minimum_completed_events": minimum_completed_events,
            "sufficient": summary["completed_outcomes"] >= minimum_completed_events,
        }
        for path, summary in paths.items()
    }
    return {
        "by_execution_path": evidence,
        "comparison_ready": all(item["sufficient"] for item in evidence.values()),
        "note": (
            "This is an evidence-volume gate, not a causal inference test. "
            "Use matched or randomized evaluation before attributing differences to delegation."
        ),
    }


def evaluate_delegation_cohort_balance(
    events: list[dict],
    *,
    maximum_share_gap: float = 0.20,
) -> dict:
    """Check whether primary and worker telemetry cover comparable workload cohorts."""
    if not 0 <= maximum_share_gap <= 1:
        raise ValueError("maximum_share_gap must be between 0 and 1.")

    delegated = [event for event in events if event.get("delegation_execution_path") == "efficient_worker"]
    retained = [event for event in events if event.get("delegation_execution_path") == "primary_route"]
    if not delegated or not retained:
        return {
            "comparable": False,
            "maximum_share_gap": maximum_share_gap,
            "reason": "Both execution paths need observed events before cohort balance can be assessed.",
            "dimensions": {},
        }

    dimensions = {}
    for field in ("delegation_operation", "task_type", "sensitivity"):
        delegated_counts = {}
        retained_counts = {}
        for event in delegated:
            value = event.get(field, "unspecified") or "unspecified"
            delegated_counts[value] = delegated_counts.get(value, 0) + 1
        for event in retained:
            value = event.get(field, "unspecified") or "unspecified"
            retained_counts[value] = retained_counts.get(value, 0) + 1
        categories = sorted(set(delegated_counts) | set(retained_counts))
        gaps = {
            category: round(
                abs(delegated_counts.get(category, 0) / len(delegated) - retained_counts.get(category, 0) / len(retained)),
                4,
            )
            for category in categories
        }
        dimensions[field] = {
            "maximum_observed_gap": max(gaps.values(), default=0.0),
            "category_share_gaps": gaps,
        }

    comparable = all(
        detail["maximum_observed_gap"] <= maximum_share_gap
        for detail in dimensions.values()
    )
    return {
        "comparable": comparable,
        "maximum_share_gap": maximum_share_gap,
        "dimensions": dimensions,
        "reason": (
            "Cohorts are balanced within the configured share-gap threshold."
            if comparable
            else "Cohort composition differs across execution paths; do not attribute outcome differences to delegation."
        ),
    }


def recommend_delegation_rollout(
    report: dict,
    evidence: dict,
    cohort_balance: dict,
    *,
    minimum_worker_success_rate: float = 0.80,
) -> dict:
    """Return a conservative, human-review recommendation for delegation rollout."""
    if not 0 <= minimum_worker_success_rate <= 1:
        raise ValueError("minimum_worker_success_rate must be between 0 and 1.")
    if not evidence["comparison_ready"]:
        return {
            "status": "hold_insufficient_evidence",
            "recommended_action": "Keep the current delegation policy unchanged and collect completed outcomes on both paths.",
            "reason": "The evidence-volume gate has not passed.",
        }
    if not cohort_balance["comparable"]:
        return {
            "status": "hold_unbalanced_cohorts",
            "recommended_action": "Do not compare or expand routes until workload cohorts are better matched.",
            "reason": cohort_balance["reason"],
        }
    worker_success_rate = report["delegated"]["success_rate"]
    if worker_success_rate is None or worker_success_rate < minimum_worker_success_rate:
        return {
            "status": "hold_success_below_floor",
            "recommended_action": "Keep the efficient-worker route scoped to its current allowlist and investigate failed outcomes.",
            "reason": "The worker path does not meet the configured observed-success floor.",
            "worker_success_rate": worker_success_rate,
            "minimum_worker_success_rate": minimum_worker_success_rate,
        }
    return {
        "status": "eligible_for_human_review",
        "recommended_action": "Review outcome quality and failure cases before expanding the delegation allowlist.",
        "reason": "Evidence volume, cohort balance, and the worker success floor passed; this is not automatic promotion.",
        "worker_success_rate": worker_success_rate,
        "minimum_worker_success_rate": minimum_worker_success_rate,
    }
