import pandas as pd


COUNTERFACTUAL_PATH = (
    "data/processed/counterfactual_tool_outcomes.csv"
)

ROUTED_PATH = "results/routing_decisions.csv"


def load_data():
    outcomes = pd.read_csv(COUNTERFACTUAL_PATH)
    routed = pd.read_csv(ROUTED_PATH)

    return outcomes, routed


def build_baseline(outcomes):
    baseline = outcomes[
        outcomes["tool"]
        == outcomes["observed_tool"]
    ].copy()

    return baseline


def build_routed(outcomes, routing):
    selected = routing[
        ["event_id", "recommended_tool"]
    ].copy()

    routed = outcomes.merge(
        selected,
        on="event_id",
        how="inner"
    )

    routed = routed[
        routed["tool"]
        == routed["recommended_tool"]
    ].copy()

    return routed


def summarize(df):
    frontier_mask = df["tool"].isin(
        ["chatgpt", "claude"]
    )

    return {
        "events": len(df),
        "total_cost_usd": df["estimated_cost_usd"].sum(),
        "success_rate": df["task_success"].mean(),
        "avg_quality": df["quality_score"].mean(),
        "avg_latency_ms": df["latency_ms"].mean(),
        "avg_corrections": df["human_corrections"].mean(),
        "frontier_usage_rate": frontier_mask.mean(),
    }


def percent_change(new, old):
    if old == 0:
        return None

    return ((new - old) / old) * 100


def build_comparison():
    outcomes, routing = load_data()

    baseline = build_baseline(outcomes)
    routed = build_routed(outcomes, routing)

    if len(baseline) != len(routed):
        raise ValueError(
            "Baseline and routed populations differ."
        )

    baseline_summary = summarize(baseline)
    routed_summary = summarize(routed)

    rows = []

    for metric in baseline_summary:
        old = baseline_summary[metric]
        new = routed_summary[metric]

        rows.append({
            "metric": metric,
            "baseline": old,
            "routed": new,
            "absolute_change": new - old,
            "percent_change": percent_change(
                new,
                old
            ),
        })

    comparison = pd.DataFrame(rows)

    comparison.to_csv(
        "results/policy_comparison.csv",
        index=False
    )

    print("\nPolicy comparison")
    print(
        comparison
        .round(4)
        .to_string(index=False)
    )

    route_change_rate = (
        routing["observed_tool"]
        != routing["recommended_tool"]
    ).mean()

    constraint_rate = (
        routing["decision_status"]
        == "constraints_satisfied"
    ).mean()

    print("\nRouting behavior")
    print(
        f"Route changed: "
        f"{route_change_rate:.1%}"
    )
    print(
        f"Constraints satisfied: "
        f"{constraint_rate:.1%}"
    )

    print(
        "\nBoth policies were evaluated "
        "using the same simulated "
        "potential-outcome table."
    )

    return comparison


if __name__ == "__main__":
    build_comparison()