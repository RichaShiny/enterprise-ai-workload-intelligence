import pandas as pd


DATA_PATH = "data/raw/enterprise_workload_events.csv"


def load_events():
    return pd.read_csv(DATA_PATH)


def organization_summary(df):
    return {
        "total_events": len(df),
        "total_cost_usd": df["estimated_cost_usd"].sum(),
        "avg_quality": df["quality_score"].mean(),
        "success_rate": df["task_success"].mean(),
        "avg_latency_ms": df["latency_ms"].mean(),
        "avg_human_time_minutes": df["human_time_minutes"].mean(),
        "total_human_corrections": df["human_corrections"].sum(),
    }


def tool_summary(df):
    return (
        df.groupby("tool")
        .agg(
            events=("event_id", "count"),
            total_cost_usd=("estimated_cost_usd", "sum"),
            avg_cost_usd=("estimated_cost_usd", "mean"),
            success_rate=("task_success", "mean"),
            avg_quality=("quality_score", "mean"),
            avg_latency_ms=("latency_ms", "mean"),
            avg_human_time=("human_time_minutes", "mean"),
            avg_corrections=("human_corrections", "mean"),
        )
        .sort_values("total_cost_usd", ascending=False)
    )


def task_tool_summary(df):
    return (
        df.groupby(["task_type", "tool"])
        .agg(
            events=("event_id", "count"),
            success_rate=("task_success", "mean"),
            avg_quality=("quality_score", "mean"),
            avg_cost_usd=("estimated_cost_usd", "mean"),
            avg_latency_ms=("latency_ms", "mean"),
            avg_corrections=("human_corrections", "mean"),
        )
        .reset_index()
    )


def frontier_usage(df):
    frontier = df["model"] == "frontier_llm"

    return {
        "frontier_events": int(frontier.sum()),
        "frontier_usage_rate": frontier.mean(),
        "frontier_cost_usd": df.loc[
            frontier, "estimated_cost_usd"
        ].sum(),
    }


def main():
    df = load_events()

    print("\n ORGANIZATION SUMMARY ")
    for key, value in organization_summary(df).items():
        print(f"{key}: {value:.3f}")

    print("\n TOOL SUMMARY ")
    print(tool_summary(df).round(3))

    print("\n FRONTIER MODEL USAGE ")
    for key, value in frontier_usage(df).items():
        print(f"{key}: {value:.3f}")

    task_summary = task_tool_summary(df)
    task_summary.to_csv(
        "results/task_tool_observability.csv",
        index=False,
    )

    print(
        "\nSaved detailed task/tool analysis to "
        "results/task_tool_observability.csv"
    )


if __name__ == "__main__":
    main()