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
