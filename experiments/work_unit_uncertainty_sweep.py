from itertools import product

from src.simulation.work_unit import (
    WorkUnit,
    ModelProfile,
    direct_route,
    cascade_route,
)


def choose_best(work_unit, small_success, frontier_success):
    small = ModelProfile(
        name="small_model",
        cost_per_attempt=0.004,
        success_probability=small_success,
        latency_ms=700,
        quality=0.78,
    )

    frontier = ModelProfile(
        name="frontier_model",
        cost_per_attempt=0.018,
        success_probability=frontier_success,
        latency_ms=1400,
        quality=0.93,
    )

    candidates = [
        direct_route(work_unit, small),
        direct_route(work_unit, frontier),
        cascade_route(work_unit, small, frontier),
    ]

    return min(
        candidates,
        key=lambda x: x.expected_total_cost,
    )


def main():
    scenarios = [
        {
            "name": "summarization",
            "failure_cost": 0.01,
            "escalation_cost": 0.002,
            "small_base": 0.90,
            "frontier_base": 0.97,
        },
        {
            "name": "technical_reasoning",
            "failure_cost": 0.10,
            "escalation_cost": 0.02,
            "small_base": 0.68,
            "frontier_base": 0.95,
        },
        {
            "name": "compliance",
            "failure_cost": 1.00,
            "escalation_cost": 0.20,
            "small_base": 0.55,
            "frontier_base": 0.96,
        },
    ]

    perturbations = [-0.10, -0.05, 0.00, 0.05, 0.10]

    for scenario in scenarios:
        work_unit = WorkUnit(
            workload_id=f"uncertainty_{scenario['name']}",
            task_type=scenario["name"],
            complexity=0.5,
            sensitivity="medium",
            business_value=50,
            failure_cost=scenario["failure_cost"],
            escalation_cost=scenario["escalation_cost"],
        )

        strategy_counts = {}

        print("\n" + "=" * 70)
        print(f"Workload: {scenario['name']}")

        for small_delta, frontier_delta in product(
            perturbations,
            perturbations,
        ):
            small_success = min(
                0.999,
                max(0.01, scenario["small_base"] + small_delta),
            )

            frontier_success = min(
                0.999,
                max(0.01, scenario["frontier_base"] + frontier_delta),
            )

            best = choose_best(
                work_unit,
                small_success,
                frontier_success,
            )

            strategy_counts[best.strategy] = (
                strategy_counts.get(best.strategy, 0) + 1
            )

        total = sum(strategy_counts.values())

        print(f"Scenarios tested: {total}")

        for strategy, count in sorted(
            strategy_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            print(
                f"{strategy:<38} "
                f"{count:>2}/{total} "
                f"({count / total:.1%})"
            )

        dominant_strategy, dominant_count = max(
            strategy_counts.items(),
            key=lambda item: item[1],
        )

        print(
            f"Policy stability: "
            f"{dominant_strategy} remains optimal in "
            f"{dominant_count / total:.1%} of perturbations"
        )


if __name__ == "__main__":
    main()