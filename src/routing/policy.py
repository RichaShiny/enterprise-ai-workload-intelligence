import pandas as pd


DATA_PATH = "data/processed/counterfactual_tool_outcomes.csv"


POLICY_CONFIGS = {
    "cost_optimized": {
        "base_quality": 0.75,
        "base_success": 0.75,
        "max_corrections": 3,
        "max_latency_ms": 6000,
        "priority_quality": 0.80,
        "priority_success": 0.82,
        "complex_quality": 0.80,
        "complex_success": 0.82,
        "sensitive_quality": 0.84,
        "sensitive_corrections": 2,
    },

    "balanced": {
        "base_quality": 0.80,
        "base_success": 0.80,
        "max_corrections": 2,
        "max_latency_ms": 6000,
        "priority_quality": 0.85,
        "priority_success": 0.88,
        "complex_quality": 0.85,
        "complex_success": 0.88,
        "sensitive_quality": 0.88,
        "sensitive_corrections": 1,
    },

    "reliability_first": {
        "base_quality": 0.85,
        "base_success": 0.88,
        "max_corrections": 1,
        "max_latency_ms": 6000,
        "priority_quality": 0.90,
        "priority_success": 0.92,
        "complex_quality": 0.90,
        "complex_success": 0.92,
        "sensitive_quality": 0.92,
        "sensitive_corrections": 1,
    },

    "strict": {
        "base_quality": 0.88,
        "base_success": 0.90,
        "max_corrections": 1,
        "max_latency_ms": 5000,
        "priority_quality": 0.92,
        "priority_success": 0.95,
        "complex_quality": 0.92,
        "complex_success": 0.95,
        "sensitive_quality": 0.95,
        "sensitive_corrections": 0,
    },
}


def load_counterfactuals():
    return pd.read_csv(DATA_PATH)


def get_constraints(row, policy="balanced"):
    if policy not in POLICY_CONFIGS:
        raise ValueError(
            f"Unknown policy: {policy}. "
            f"Choose from {list(POLICY_CONFIGS)}."
        )

    config = POLICY_CONFIGS[policy]

    min_quality = config["base_quality"]
    min_success_probability = config["base_success"]
    max_corrections = config["max_corrections"]
    max_latency_ms = config["max_latency_ms"]

    if row["business_priority"] >= 4:
        min_quality = max(
            min_quality,
            config["priority_quality"],
        )
        min_success_probability = max(
            min_success_probability,
            config["priority_success"],
        )

    if row["complexity"] == "high":
        min_quality = max(
            min_quality,
            config["complex_quality"],
        )
        min_success_probability = max(
            min_success_probability,
            config["complex_success"],
        )

    if row["sensitivity"] == "high":
        min_quality = max(
            min_quality,
            config["sensitive_quality"],
        )
        max_corrections = min(
            max_corrections,
            config["sensitive_corrections"],
        )

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
        in [
            "generation",
            "reasoning",
            "summarization",
            "coding",
        ]
    ):
        return False

    if (
        sensitivity == "high"
        and tool in ["chatgpt", "claude"]
    ):
        return False

    return True


def select_tool(group, policy="balanced"):
    group = group.copy()

    representative = group.iloc[0]

    constraints = get_constraints(
        representative,
        policy=policy,
    )

    group["allowed"] = group.apply(
        tool_allowed_for_task,
        axis=1,
    )

    feasible = group[
    (group["allowed"])
    & (
        group["expected_quality"]
        >= constraints["min_quality"]
    )
    & (
        group["success_probability"]
        >= constraints["min_success_probability"]
    )
    & (
        group["expected_corrections"]
        <= constraints["max_corrections"]
    )
    & (
        group["expected_latency_ms"]
        <= constraints["max_latency_ms"]
    )
]

    if not feasible.empty:
        selected = feasible.sort_values(
            by=[
                "estimated_cost_usd",
                "expected_latency_ms",
                "expected_quality",
            ],
            ascending=[
                True,
                True,
                False,
            ],
        ).iloc[0]

        decision_status = "constraints_satisfied"

    else:
        allowed = group[
            group["allowed"]
        ]

        if allowed.empty:
            allowed = group

        selected = allowed.sort_values(
            by=[
                "expected_quality",
                "success_probability",
                "expected_corrections",
                "estimated_cost_usd",
            ],
            ascending=[
                False,
                False,
                True,
                True,
            ],
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
        "expected_quality": selected[
            "expected_quality"
        ],
        "expected_corrections": selected[
            "expected_corrections"
        ],
        "expected_latency_ms": selected[
            "expected_latency_ms"
        ],
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
        "policy": policy,
    })


def build_routing_policy(
    policy="balanced",
    output_path=None,
):
    df = load_counterfactuals()

    decisions = []

    for event_id, group in df.groupby("event_id"):
        decision = select_tool(
            group,
            policy=policy,
        )

        decision["event_id"] = event_id

        decisions.append(decision)

    routed = pd.DataFrame(decisions)

    if output_path is None:
        output_path = (
            f"results/routing_decisions_{policy}.csv"
        )

    routed.to_csv(
        output_path,
        index=False,
    )

    print(
        f"Generated {len(routed)} "
        f"routing decisions for policy: {policy}"
    )

    print(
        f"Saved to: {output_path}"
    )

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
    build_routing_policy(
        policy="balanced",
        output_path="results/routing_decisions.csv",
    )