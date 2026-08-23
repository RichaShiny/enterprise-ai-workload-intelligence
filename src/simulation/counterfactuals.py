import random
import pandas as pd


DATA_PATH = "data/raw/enterprise_workload_events.csv"


TOOLS = [
    "chatgpt",
    "claude",
    "codex",
    "small_local_model",
    "deterministic_automation",
]


BASE_SUCCESS = {
    "chatgpt": {
        "coding": 0.88,
        "generation": 0.93,
        "summarization": 0.94,
        "retrieval": 0.91,
        "reasoning": 0.94,
        "classification": 0.90,
        "extraction": 0.89,
    },
    "claude": {
        "coding": 0.87,
        "generation": 0.94,
        "summarization": 0.95,
        "retrieval": 0.92,
        "reasoning": 0.95,
        "classification": 0.89,
        "extraction": 0.90,
    },
    "codex": {
        "coding": 0.96,
        "generation": 0.68,
        "summarization": 0.66,
        "retrieval": 0.64,
        "reasoning": 0.74,
        "classification": 0.70,
        "extraction": 0.72,
    },
    "small_local_model": {
        "coding": 0.77,
        "generation": 0.83,
        "summarization": 0.86,
        "retrieval": 0.84,
        "reasoning": 0.73,
        "classification": 0.88,
        "extraction": 0.90,
    },
    "deterministic_automation": {
        "coding": 0.35,
        "generation": 0.30,
        "summarization": 0.40,
        "retrieval": 0.72,
        "reasoning": 0.25,
        "classification": 0.96,
        "extraction": 0.98,
    },
}


BASE_LATENCY_MS = {
    "chatgpt": 3500,
    "claude": 3800,
    "codex": 5000,
    "small_local_model": 1800,
    "deterministic_automation": 100,
}


def estimate_cost(tool, tokens_in, tokens_out):
    if tool in ["chatgpt", "claude"]:
        return round(
            (tokens_in * 0.00001) +
            (tokens_out * 0.00003),
            4
        )

    if tool == "codex":
        return round(
            (tokens_in * 0.000008) +
            (tokens_out * 0.00002),
            4
        )

    if tool == "small_local_model":
        return round(
            (tokens_in + tokens_out) * 0.000001,
            4
        )

    return 0.0


def complexity_adjustment(complexity):
    return {
        "low": 0.03,
        "medium": 0.00,
        "high": -0.08,
    }[complexity]


def sensitivity_adjustment(tool, sensitivity):
    if sensitivity != "high":
        return 0.0

    if tool in ["chatgpt", "claude"]:
        return -0.02

    if tool == "small_local_model":
        return 0.02

    return 0.0


def simulate_tool_outcome(row, tool, rng):
    task_type = row["task_type"]
    complexity = row["complexity"]
    sensitivity = row["sensitivity"]

    success_probability = BASE_SUCCESS[tool][task_type]

    success_probability += complexity_adjustment(complexity)
    success_probability += sensitivity_adjustment(
        tool,
        sensitivity
    )

    success_probability = max(
        0.05,
        min(0.99, success_probability)
    )
    

    expected_quality = (
        success_probability * 0.89
        + (1 - success_probability) * 0.46
    )

    expected_corrections = (
        success_probability * 0.95
        + (1 - success_probability) * 2.85
    )

    expected_latency_ms = BASE_LATENCY_MS[tool]

    task_success = rng.random() < success_probability

    if task_success:
        quality_score = rng.uniform(0.78, 1.0)
        human_corrections = rng.choices(
            [0, 1, 2, 3],
            weights=[0.45, 0.30, 0.18, 0.07],
            k=1,
        )[0]
    else:
        quality_score = rng.uniform(0.20, 0.72)
        human_corrections = rng.choices(
            [1, 2, 3, 4],
            weights=[0.10, 0.25, 0.35, 0.30],
            k=1,
        )[0]

    if tool == "deterministic_automation":
        tokens_in = 0
        tokens_out = 0
    else:
        tokens_in = int(row["tokens_in"])
        tokens_out = int(row["tokens_out"])

        if tokens_in == 0:
            tokens_in = rng.randint(200, 5000)

        if tokens_out == 0:
            tokens_out = rng.randint(50, 2000)

    latency_ms = max(
        20,
        rng.gauss(
            BASE_LATENCY_MS[tool],
            BASE_LATENCY_MS[tool] * 0.15
        )
    )

    estimated_cost_usd = estimate_cost(
        tool,
        tokens_in,
        tokens_out
    )

    human_time_minutes = max(
        0.5,
        rng.gauss(
            row["human_time_minutes"],
            2.5
        )
    )

    return {
        "tool": tool,
        "success_probability": success_probability,
        "expected_quality": round(
            expected_quality,
            3,
        ),
        "expected_corrections": round(
            expected_corrections,
            3,
        ),
        "expected_latency_ms": round(
            expected_latency_ms,
             2,
        ),
        "task_success": task_success,
        "quality_score": round(quality_score, 3),
        "human_corrections": human_corrections,
        "human_time_minutes": round(
            human_time_minutes,
            2
        ),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": round(latency_ms, 2),
        "estimated_cost_usd": estimated_cost_usd,
    }


def build_counterfactual_dataset(seed=42):
    df = pd.read_csv(DATA_PATH)

    rng = random.Random(seed)

    rows = []

    for _, workload in df.iterrows():
        for tool in TOOLS:
            outcome = simulate_tool_outcome(
                workload,
                tool,
                rng
            )

            rows.append({
                "event_id": workload["event_id"],
                "department": workload["department"],
                "workflow": workload["workflow"],
                "task_type": workload["task_type"],
                "complexity": workload["complexity"],
                "sensitivity": workload["sensitivity"],
                "business_priority": workload["business_priority"],
                "observed_tool": workload["tool"],
                **outcome,
            })

    result = pd.DataFrame(rows)

    output_path = (
        "data/processed/"
        "counterfactual_tool_outcomes.csv"
    )

    result.to_csv(
        output_path,
        index=False
    )

    print(
        f"Generated {len(result)} "
        "counterfactual tool outcomes."
    )
    print(f"Saved to: {output_path}")

    return result


if __name__ == "__main__":
    build_counterfactual_dataset()