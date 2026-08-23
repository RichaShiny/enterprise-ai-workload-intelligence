import pandas as pd

from src.routing.policy import build_routing_policy
from src.simulation.compare_policies import (
    build_baseline,
    build_routed,
    summarize,
)

COUNTERFACTUAL_PATH = (
    "data/processed/counterfactual_tool_outcomes.csv"
)

POLICIES = [
    "cost_optimized",
    "balanced",
    "reliability_first",
    "strict",
]


def load_outcomes():
    return pd.read_csv(COUNTERFACTUAL_PATH)


def run_policy(policy, outcomes, baseline_summary):
    routing = build_routing_policy(
        policy=policy,
        output_path=(
            f"results/routing_decisions_{policy}.csv"
        ),
    )

    routed = build_routed(
        outcomes,
        routing,
    )

    routed_summary = summarize(routed)

    route_change_rate = (
        routing["observed_tool"]
        != routing["recommended_tool"]
    ).mean()

    constraint_satisfaction_rate = (
        routing["decision_status"]
        == "constraints_satisfied"
    ).mean()

    frontier_usage_change_pp = (
        routed_summary["frontier_usage_rate"]
        - baseline_summary["frontier_usage_rate"]
    ) * 100

    success_change_pp = (
        routed_summary["success_rate"]
        - baseline_summary["success_rate"]
    ) * 100

    cost_reduction_pct = (
        (
            baseline_summary["total_cost_usd"]
            - routed_summary["total_cost_usd"]
        )
        / baseline_summary["total_cost_usd"]
    ) * 100

    latency_reduction_pct = (
        (
            baseline_summary["avg_latency_ms"]
            - routed_summary["avg_latency_ms"]
        )
        / baseline_summary["avg_latency_ms"]
    ) * 100

    correction_reduction_pct = (
        (
            baseline_summary["avg_corrections"]
            - routed_summary["avg_corrections"]
        )
        / baseline_summary["avg_corrections"]
    ) * 100

    return {
        "policy": policy,
        "total_cost_usd": routed_summary[
            "total_cost_usd"
        ],
        "cost_reduction_pct": cost_reduction_pct,
        "success_rate": routed_summary[
            "success_rate"
        ],
        "success_change_pp": success_change_pp,
        "avg_quality": routed_summary[
            "avg_quality"
        ],
        "avg_latency_ms": routed_summary[
            "avg_latency_ms"
        ],
        "latency_reduction_pct": (
            latency_reduction_pct
        ),
        "avg_corrections": routed_summary[
            "avg_corrections"
        ],
        "correction_reduction_pct": (
            correction_reduction_pct
        ),
        "frontier_usage_rate": routed_summary[
            "frontier_usage_rate"
        ],
        "frontier_usage_change_pp": (
            frontier_usage_change_pp
        ),
        "constraint_satisfaction_rate": (
            constraint_satisfaction_rate
        ),
        "route_change_rate": route_change_rate,
    }


def main():
    outcomes = load_outcomes()

    baseline = build_baseline(outcomes)
    baseline_summary = summarize(baseline)

    rows = []

    for policy in POLICIES:
        print(f"\nRunning policy: {policy}")

        result = run_policy(
            policy,
            outcomes,
            baseline_summary,
        )

        rows.append(result)

    results = pd.DataFrame(rows)

    output_path = "results/policy_tradeoffs.csv"

    results.to_csv(
        output_path,
        index=False,
    )

    print("\nPolicy trade-offs")
    print(
        results[
            [
                "policy",
                "cost_reduction_pct",
                "success_rate",
                "success_change_pp",
                "avg_quality",
                "latency_reduction_pct",
                "correction_reduction_pct",
                "frontier_usage_rate",
                "constraint_satisfaction_rate",
            ]
        ]
        .round(3)
        .to_string(index=False)
    )

    print(
        f"\nSaved policy comparison to: "
        f"{output_path}"
    )


if __name__ == "__main__":
    main()