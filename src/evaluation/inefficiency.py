import pandas as pd


DATA_PATH = "data/raw/enterprise_workload_events.csv"


def load_events():
    return pd.read_csv(DATA_PATH)


def add_inefficiency_flags(df):
    df = df.copy()

    # Frontier model used for relatively simple work.
    df["simple_frontier_usage"] = (
        (df["model"] == "frontier_llm")
        & (df["complexity"] == "low")
    )

    # Specialized coding agent used outside coding.
    df["codex_mismatch"] = (
        (df["tool"] == "codex")
        & (df["task_type"] != "coding")
    )

    # Deterministic automation used for tasks that generally
    # require open-ended language generation or reasoning.
    df["automation_mismatch"] = (
        (df["tool"] == "deterministic_automation")
        & (
            df["task_type"].isin(
                ["generation", "reasoning", "summarization"]
            )
        )
    )

    # Expensive interaction that still failed.
    cost_threshold = df["estimated_cost_usd"].quantile(0.75)

    df["high_cost_failure"] = (
        (df["estimated_cost_usd"] >= cost_threshold)
        & (~df["task_success"])
    )

    # Successful output that still required substantial correction.
    df["high_correction_success"] = (
        (df["task_success"])
        & (df["human_corrections"] >= 3)
    )

    flag_columns = [
        "simple_frontier_usage",
        "codex_mismatch",
        "automation_mismatch",
        "high_cost_failure",
        "high_correction_success",
    ]

    df["inefficiency_flag_count"] = (
        df[flag_columns]
        .astype(int)
        .sum(axis=1)
    )

    df["flagged_for_review"] = (
        df["inefficiency_flag_count"] > 0
    )

    return df


def summarize_flags(df):
    flag_columns = [
        "simple_frontier_usage",
        "codex_mismatch",
        "automation_mismatch",
        "high_cost_failure",
        "high_correction_success",
    ]

    summary = []

    for flag in flag_columns:
        mask = df[flag]

        summary.append({
            "flag": flag,
            "events": int(mask.sum()),
            "event_rate": mask.mean(),
            "simulated_cost_usd": (
                df.loc[mask, "estimated_cost_usd"].sum()
            ),
            "avg_quality": (
                df.loc[mask, "quality_score"].mean()
                if mask.any()
                else 0
            ),
            "success_rate": (
                df.loc[mask, "task_success"].mean()
                if mask.any()
                else 0
            ),
        })

    return pd.DataFrame(summary)


def main():
    df = load_events()
    flagged_df = add_inefficiency_flags(df)

    summary = summarize_flags(flagged_df)

    print("\n POTENTIAL INEFFICIENCY SIGNALS ")
    print(summary.round(3).to_string(index=False))

    total_flagged = flagged_df["flagged_for_review"].sum()

    print("\n REVIEW SUMMARY ")
    print(f"Events flagged: {total_flagged}/{len(flagged_df)}")
    print(
        "Flagged event rate: "
        f"{flagged_df['flagged_for_review'].mean():.1%}"
    )

    flagged_df.to_csv(
        "results/workload_inefficiency_flags.csv",
        index=False,
    )

    summary.to_csv(
        "results/inefficiency_summary.csv",
        index=False,
    )

    print(
        "\nSaved event-level flags to "
        "results/workload_inefficiency_flags.csv"
    )
    print(
        "Saved summary to "
        "results/inefficiency_summary.csv"
    )


if __name__ == "__main__":
    main()