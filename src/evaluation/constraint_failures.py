import pandas as pd


ROUTING_PATH = "results/routing_decisions.csv"


def load_routing_decisions():
    return pd.read_csv(ROUTING_PATH)


def failure_rate_by(df, column):
    summary = (
        df.groupby(column)
        .agg(
            workloads=("event_id", "count"),
            fallback_rate=(
                "decision_status",
                lambda x: (
                    x == "fallback_best_available"
                ).mean()
            ),
        )
        .reset_index()
    )

    return summary.sort_values(
        "fallback_rate",
        ascending=False,
    )


def analyze_constraint_failures():
    df = load_routing_decisions()

    fallback = df[
        df["decision_status"]
        == "fallback_best_available"
    ].copy()

    print("\nConstraint failure analysis")

    print(
        f"\nFallback workloads: "
        f"{len(fallback)}/{len(df)} "
        f"({len(fallback) / len(df):.1%})"
    )

    dimensions = [
        "task_type",
        "complexity",
        "sensitivity",
        "business_priority",
        "department",
    ]

    outputs = []

    for dimension in dimensions:
        summary = failure_rate_by(
            df,
            dimension,
        )

        summary.insert(
            0,
            "dimension",
            dimension,
        )

        summary = summary.rename(
            columns={
                dimension: "value"
            }
        )

        outputs.append(summary)

        print(f"\nFallback rate by {dimension}")
        print(
            summary[
                [
                    "value",
                    "workloads",
                    "fallback_rate",
                ]
            ]
            .round(3)
            .to_string(index=False)
        )

    combined = pd.concat(
        outputs,
        ignore_index=True,
    )

    combined.to_csv(
        "results/constraint_failure_analysis.csv",
        index=False,
    )

    print(
        "\nSaved analysis to: "
        "results/constraint_failure_analysis.csv"
    )


if __name__ == "__main__":
    analyze_constraint_failures()