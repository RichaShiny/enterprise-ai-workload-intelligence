from src.simulation.work_unit import (
    WorkUnit,
    ModelProfile,
    direct_route,
    cascade_route,
)


TASK_MODEL_PERFORMANCE = {
    "summarization": {
        "small_model": {
            "success_probability": 0.90,
            "quality": 0.84,
        },
        "frontier_model": {
            "success_probability": 0.97,
            "quality": 0.94,
        },
    },
    "technical_reasoning": {
        "small_model": {
            "success_probability": 0.68,
            "quality": 0.76,
        },
        "frontier_model": {
            "success_probability": 0.95,
            "quality": 0.93,
        },
    },
    "compliance": {
        "small_model": {
            "success_probability": 0.55,
            "quality": 0.72,
        },
        "frontier_model": {
            "success_probability": 0.96,
            "quality": 0.95,
        },
    },
}


def build_model_profiles(task_type):
    performance = TASK_MODEL_PERFORMANCE[task_type]

    small = ModelProfile(
        name="small_model",
        cost_per_attempt=0.004,
        success_probability=performance["small_model"]["success_probability"],
        latency_ms=700,
        quality=performance["small_model"]["quality"],
    )

    frontier = ModelProfile(
        name="frontier_model",
        cost_per_attempt=0.018,
        success_probability=performance["frontier_model"]["success_probability"],
        latency_ms=1400,
        quality=performance["frontier_model"]["quality"],
    )

    return small, frontier


def print_result(label, result):
    print(f"\n{label}")
    print(f"Strategy: {result.strategy}")
    print(
    f"Expected execution + escalation cost: "
    f"${result.expected_cost:.4f}"
    )
    print(f"Expected latency: {result.expected_latency_ms:.1f} ms")
    print(f"Success probability: {result.success_probability:.3f}")
    print(f"Expected failure cost: ${result.expected_failure_cost:.4f}")
    print(f"Expected total cost: ${result.expected_total_cost:.4f}")


def main():
    work_units = [
        WorkUnit(
            workload_id="WU-001",
            task_type="summarization",
            complexity=0.3,
            sensitivity="low",
            business_value=10,
            failure_cost=0.01,
            escalation_cost=0.002,
        ),
        WorkUnit(
            workload_id="WU-002",
            task_type="technical_reasoning",
            complexity=0.8,
            sensitivity="medium",
            business_value=50,
            failure_cost=0.10,
            escalation_cost=0.02,
        ),
        WorkUnit(
            workload_id="WU-003",
            task_type="compliance",
            complexity=0.7,
            sensitivity="high",
            business_value=100,
            failure_cost=1.00,
            escalation_cost=0.20,
        ),
    ]

    for work_unit in work_units:
        small_model, frontier_model = build_model_profiles(
            work_unit.task_type
        )

        print("\n" + "=" * 60)
        print(
            f"{work_unit.workload_id} | "
            f"{work_unit.task_type} | "
            f"failure_cost=${work_unit.failure_cost:.2f}"
        )

        print(
            f"Model success probabilities | "
            f"small={small_model.success_probability:.2f} | "
            f"frontier={frontier_model.success_probability:.2f}"
        )

        direct_small = direct_route(
            work_unit,
            small_model,
        )

        direct_frontier = direct_route(
            work_unit,
            frontier_model,
        )

        cascade = cascade_route(
            work_unit,
            small_model,
            frontier_model,
        )

        print_result("Direct small model", direct_small)
        print_result("Direct frontier model", direct_frontier)
        print_result("Small → frontier cascade", cascade)

        candidates = [
            direct_small,
            direct_frontier,
            cascade,
        ]

        best = min(
            candidates,
            key=lambda x: x.expected_total_cost,
        )

        print(
            f"\nBest strategy by expected total cost: "
            f"{best.strategy}"
        )


if __name__ == "__main__":
    main()