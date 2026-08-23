import random
import pandas as pd

from scipy import stats
from src.simulation.counterfactuals import build_counterfactual_dataset
from src.routing.policy import build_routing_policy
from src.simulation.compare_policies import (
    build_baseline,
    build_routed,
    summarize,
)


SEEDS = [11, 21, 31, 41, 51, 61, 71, 81, 91, 101]


def run_seed(seed):
    random.seed(seed)

    outcomes = build_counterfactual_dataset(seed=seed)
    routing = build_routing_policy()

    baseline = build_baseline(outcomes)
    routed = build_routed(outcomes, routing)

    baseline_summary = summarize(baseline)
    routed_summary = summarize(routed)

    return {
        "seed": seed,
        "baseline_cost": baseline_summary["total_cost_usd"],
        "routed_cost": routed_summary["total_cost_usd"],
        "cost_reduction_pct": (
            (
                baseline_summary["total_cost_usd"]
                - routed_summary["total_cost_usd"]
            )
            / baseline_summary["total_cost_usd"]
        )
        * 100,
        "baseline_success": baseline_summary["success_rate"],
        "routed_success": routed_summary["success_rate"],
        "success_change_pp": (
            routed_summary["success_rate"]
            - baseline_summary["success_rate"]
        )
        * 100,
        "baseline_quality": baseline_summary["avg_quality"],
        "routed_quality": routed_summary["avg_quality"],
        "quality_change": (
            routed_summary["avg_quality"]
            - baseline_summary["avg_quality"]
        ),
        "baseline_latency_ms": baseline_summary["avg_latency_ms"],
        "routed_latency_ms": routed_summary["avg_latency_ms"],
        "latency_reduction_pct": (
            (
                baseline_summary["avg_latency_ms"]
                - routed_summary["avg_latency_ms"]
            )
            / baseline_summary["avg_latency_ms"]
        )
        * 100,
        "baseline_corrections": baseline_summary["avg_corrections"],
        "routed_corrections": routed_summary["avg_corrections"],
        "correction_reduction_pct": (
            (
                baseline_summary["avg_corrections"]
                - routed_summary["avg_corrections"]
            )
            / baseline_summary["avg_corrections"]
        )
        * 100,
        "baseline_frontier_usage": baseline_summary[
            "frontier_usage_rate"
        ],
        "routed_frontier_usage": routed_summary[
            "frontier_usage_rate"
        ],
        "frontier_usage_change_pp": (
            routed_summary["frontier_usage_rate"]
            - baseline_summary["frontier_usage_rate"]
        )
        * 100,
        "constraint_satisfaction_rate": (
            routing["decision_status"]
            == "constraints_satisfied"
        ).mean(),
    }


def summarize_results(df):
    metrics = [
        "cost_reduction_pct",
        "success_change_pp",
        "quality_change",
        "latency_reduction_pct",
        "correction_reduction_pct",
        "frontier_usage_change_pp",
        "constraint_satisfaction_rate",
    ]

    summary_rows = []

    for metric in metrics:
        series = df[metric]

        mean = series.mean()
        std = series.std(ddof=1)
        n = len(series)

        sem = stats.sem(series)

        ci_low, ci_high = stats.t.interval(
            confidence=0.95,
            df=n - 1,
            loc=mean,
            scale=sem,
        )

        summary_rows.append({
            "metric": metric,
            "mean": mean,
            "std": std,
            "ci_95_low": ci_low,
            "ci_95_high": ci_high,
            "min": series.min(),
            "max": series.max(),
        })

    return pd.DataFrame(summary_rows)

def main():
    rows = []

    for seed in SEEDS:
        print(f"\nRunning seed {seed}")
        result = run_seed(seed)
        rows.append(result)

    results_df = pd.DataFrame(rows)

    summary_df = summarize_results(results_df)

    results_df.to_csv(
        "results/multi_seed_results.csv",
        index=False
    )

    summary_df.to_csv(
        "results/multi_seed_summary.csv",
        index=False
    )

    print("\nMulti-seed results")
    print(
        results_df[
            [
                "seed",
                "cost_reduction_pct",
                "success_change_pp",
                "quality_change",
                "latency_reduction_pct",
                "correction_reduction_pct",
                "frontier_usage_change_pp",
                "constraint_satisfaction_rate",
            ]
        ]
        .round(3)
        .to_string(index=False)
    )

    print("\nSummary across seeds")
    print(
        summary_df
        .round(3)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()