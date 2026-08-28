from src.simulation.work_unit import (
    WorkUnit,
    ModelProfile,
    direct_route,
    cascade_route,
)


def best_strategy(work_unit, cheap_model, strong_model):
    candidates = [
        direct_route(work_unit, cheap_model),
        direct_route(work_unit, strong_model),
        cascade_route(work_unit, cheap_model, strong_model),
    ]

    return min(
        candidates,
        key=lambda x: x.expected_total_cost,
    )


def main():
    cheap_model = ModelProfile(
        name="small_model",
        cost_per_attempt=0.004,
        success_probability=0.72,
        latency_ms=700,
        quality=0.78,
    )

    strong_model = ModelProfile(
        name="frontier_model",
        cost_per_attempt=0.018,
        success_probability=0.96,
        latency_ms=1400,
        quality=0.93,
    )

    failure_costs = [
        0.00,
        0.01,
        0.02,
        0.05,
        0.10,
        0.20,
        0.50,
        1.00,
        2.00,
    ]

    escalation_ratios = [
        0.00,
        0.05,
        0.10,
        0.20,
        0.30,
    ]

    print("Work Unit Routing Threshold Sweep\n")

    for escalation_ratio in escalation_ratios:
        print(
            f"\nEscalation cost = "
            f"{escalation_ratio:.0%} of failure cost"
        )

        previous_strategy = None

        for failure_cost in failure_costs:
            escalation_cost = (
                failure_cost * escalation_ratio
            )

            work_unit = WorkUnit(
                workload_id="threshold_test",
                task_type="generic",
                complexity=0.5,
                sensitivity="medium",
                business_value=50,
                failure_cost=failure_cost,
                escalation_cost=escalation_cost,
            )

            best = best_strategy(
                work_unit,
                cheap_model,
                strong_model,
            )

            marker = ""

            if (
                previous_strategy is not None
                and best.strategy != previous_strategy
            ):
                marker = "  <-- POLICY SWITCH"

            print(
                f"failure_cost=${failure_cost:>4.2f} | "
                f"escalation_cost=${escalation_cost:>5.3f} | "
                f"{best.strategy:<38} | "
                f"total=${best.expected_total_cost:.4f}"
                f"{marker}"
            )

            previous_strategy = best.strategy


if __name__ == "__main__":
    main()