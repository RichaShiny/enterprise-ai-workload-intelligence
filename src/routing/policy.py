import pandas as pd


DATA_PATH = "data/processed/counterfactual_tool_outcomes.csv"


def load_counterfactuals():
    return pd.read_csv(DATA_PATH)


def get_constraints(row):
    priority = row["business_priority"]
    sensitivity = row["sensitivity"]
    complexity = row["complexity"]

    min_quality = 0.80
    min_success_probability = 0.80
    max_corrections = 2
    max_latency_ms = 6000

    if priority >= 4:
        min_quality = 0.85
        min_success_probability = 0.88

    if complexity == "high":
        min_quality = max(min_quality, 0.85)
        min_success_probability = max(
            min_success_probability,
            0.88
        )

    if sensitivity == "high":
        min_quality = max(min_quality, 0.88)
        max_corrections = 1

    return {
        "min_quality": min_quality,
        "min_success_probability": min_success_probability,
        "max_corrections": max_corrections,
        "max_latency_ms": max_latency_ms,
    }


def tool_allowed_for_task(row):
    tool = row["tool"]
    task_type = row["task_type"]
    sensitivity = row["sensitivity"]

    if tool == "codex" and task_type != "coding":
        return False

    if (
        tool == "deterministic_automation"
        and task_type
        in ["generation", "reasoning", "summarization", "coding"]
    ):
        return False

    if (
        sensitivity == "high"
        and tool in ["chatgpt", "claude"]
    ):
        return False

    return True


def select_tool(group):
    group = group.copy()

    representative = group.iloc[0]
    constraints = get_constraints(representative)

    group["allowed"] = group.apply(
        tool_allowed_for_task,
        axis=1
    )

    feasible = group[
        (group["allowed"])
        & (
            group["quality_score"]
            >= constraints["min_quality"]
        )
        & (
            group["success_probability"]
            >= constraints["min_success_probability"]
        )
        & (
            group["human_corrections"]
            <= constraints["max_corrections"]
        )
        & (
            group["latency_ms"]
            <= constraints["max_latency_ms"]
        )
    ]

    if not feasible.empty:
        selected = feasible.sort_values(
            by=[
                "estimated_cost_usd",
                "latency_ms",
                "quality_score",
            ],
            ascending=[True, True, False],
        ).iloc[0]

        decision_status = "constraints_satisfied"

    else:
        allowed = group[group["allowed"]]

        if allowed.empty:
            allowed = group

        selected = allowed.sort_values(
            by=[
                "quality_score",
                "success_probability",
            ],
            ascending=[False, False],
        ).iloc[0]

        decision_status = "fallback_best_available"

    return pd.Series({
        "department": selected["department"],
        "workflow": selected["workflow"],
        "task_type": selected["task_type"],
        "complexity": selected["complexity"],
        "sensitivity": selected["sensitivity"],
        "business_priority": selected["business_priority"],
        "observed_tool": selected["observed_tool"],
        "recommended_tool": selected["tool"],
        "quality_score": selected["quality_score"],
        "success_probability": selected[
            "success_probability"
        ],
        "task_success": selected["task_success"],
        "estimated_cost_usd": selected[
            "estimated_cost_usd"
        ],
        "latency_ms": selected["latency_ms"],
        "human_corrections": selected[
            "human_corrections"
        ],
        "decision_status": decision_status,
        "min_quality_required": constraints[
            "min_quality"
        ],
        "min_success_required": constraints[
            "min_success_probability"
        ],
    })


def build_routing_policy():
    df = load_counterfactuals()

    decisions = []

    for event_id, group in df.groupby("event_id"):
        decision = select_tool(group)

        decision["event_id"] = event_id

        decisions.append(decision)

    routed = pd.DataFrame(decisions)

    output_path = "results/routing_decisions.csv"

    routed.to_csv(
        output_path,
        index=False
    )

    print(
        f"Generated {len(routed)} routing decisions."
    )
    print(f"Saved to: {output_path}")

    print("\nRecommended tool distribution")
    print(
        routed["recommended_tool"]
        .value_counts()
    )

    print("\nDecision status")
    print(
        routed["decision_status"]
        .value_counts()
    )

    return routed


if __name__ == "__main__":
    build_routing_policy()