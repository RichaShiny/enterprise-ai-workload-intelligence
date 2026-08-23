import random
import uuid
import pandas as pd

from src.workloads.schema import WorkloadEvent


DEPARTMENTS = {
    "engineering": [
        ("api_implementation", "coding"),
        ("bug_fix", "coding"),
        ("code_review", "coding"),
    ],
    "marketing": [
        ("campaign_brief", "generation"),
        ("social_copy", "generation"),
        ("campaign_analysis", "reasoning"),
    ],
    "recruiting": [
        ("interview_summary", "summarization"),
        ("job_description", "generation"),
        ("candidate_notes", "summarization"),
    ],
    "finance": [
        ("invoice_extraction", "extraction"),
        ("expense_classification", "classification"),
        ("financial_summary", "summarization"),
    ],
    "compliance": [
        ("policy_lookup", "retrieval"),
        ("policy_reasoning", "reasoning"),
        ("risk_review", "reasoning"),
    ],
    "sales": [
        ("outbound_email", "generation"),
        ("lead_research", "retrieval"),
        ("crm_note_summary", "summarization"),
    ],
    "support": [
        ("faq_response", "retrieval"),
        ("ticket_classification", "classification"),
        ("customer_response", "generation"),
    ],
}


TOOLS = [
    {
        "tool": "chatgpt",
        "model": "frontier_llm",
        "agent_type": "general_purpose",
    },
    {
        "tool": "claude",
        "model": "frontier_llm",
        "agent_type": "general_purpose",
    },
    {
        "tool": "codex",
        "model": "coding_agent",
        "agent_type": "specialized_agent",
    },
    {
        "tool": "small_local_model",
        "model": "small_llm",
        "agent_type": "specialized_model",
    },
    {
        "tool": "deterministic_automation",
        "model": "none",
        "agent_type": "automation",
    },
]


def estimate_cost(tool, tokens_in, tokens_out):
    # Synthetic cost assumptions for benchmarking only.
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


def generate_event():
    department = random.choice(list(DEPARTMENTS.keys()))
    workflow, task_type = random.choice(DEPARTMENTS[department])

    tool_info = random.choice(TOOLS)

    complexity = random.choice(["low", "medium", "high"])
    sensitivity = random.choice(["low", "medium", "high"])
    business_priority = random.randint(1, 5)

    if tool_info["tool"] == "deterministic_automation":
        tokens_in = 0
        tokens_out = 0
    else:
        tokens_in = random.randint(200, 5000)
        tokens_out = random.randint(50, 2000)

    base_latency = {
        "chatgpt": 3500,
        "claude": 3800,
        "codex": 5000,
        "small_local_model": 1800,
        "deterministic_automation": 100,
    }[tool_info["tool"]]

    latency_ms = max(
        20,
        random.gauss(base_latency, base_latency * 0.2)
    )

    estimated_cost = estimate_cost(
        tool_info["tool"],
        tokens_in,
        tokens_out,
    )

    human_time_minutes = round(
        random.uniform(1, 25),
        2
    )

    human_corrections = random.randint(0, 4)

    task_success_probability = {
        "chatgpt": 0.92,
        "claude": 0.93,
        "codex": 0.95 if task_type == "coding" else 0.70,
        "small_local_model": 0.85,
        "deterministic_automation": (
            0.97
            if task_type in ["classification", "extraction"]
            else 0.55
        ),
    }[tool_info["tool"]]

    task_success = random.random() < task_success_probability

    quality_score = round(
        random.uniform(0.75, 1.0)
        if task_success
        else random.uniform(0.2, 0.7),
        3
    )

    return WorkloadEvent(
        event_id=str(uuid.uuid4()),
        department=department,
        workflow=workflow,
        task_type=task_type,
        tool=tool_info["tool"],
        model=tool_info["model"],
        agent_type=tool_info["agent_type"],
        complexity=complexity,
        sensitivity=sensitivity,
        business_priority=business_priority,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=round(latency_ms, 2),
        estimated_cost_usd=estimated_cost,
        human_time_minutes=human_time_minutes,
        human_corrections=human_corrections,
        task_success=task_success,
        quality_score=quality_score,
    )


def generate_dataset(n_events=250):
    events = [
        generate_event().to_dict()
        for _ in range(n_events)
    ]

    df = pd.DataFrame(events)

    output_path = "data/raw/enterprise_workload_events.csv"
    df.to_csv(output_path, index=False)

    print(f"Generated {len(df)} synthetic enterprise workload events.")
    print(f"Saved to: {output_path}")
    print()
    print(df.head())


if __name__ == "__main__":
    random.seed(42)
    generate_dataset()