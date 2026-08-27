import numpy as np

from src.evaluation.ab_experiment import (
    analyze_binary_experiment,
)


SEED = 42
N_USERS = 2000


def summarize_metric(
    name,
    control,
    treatment,
    unit="",
):
    control_mean = np.mean(control)
    treatment_mean = np.mean(treatment)

    change = treatment_mean - control_mean

    print(f"\n{name}")
    print(
        f"Control: {control_mean:.3f}{unit}"
    )
    print(
        f"Treatment: {treatment_mean:.3f}{unit}"
    )
    print(
        f"Change: {change:+.3f}{unit}"
    )


def simulate_experiment():
    rng = np.random.default_rng(SEED)

    assignments = rng.integers(
        0,
        2,
        size=N_USERS,
    )

    success = np.zeros(N_USERS)
    cost = np.zeros(N_USERS)
    latency = np.zeros(N_USERS)
    faithfulness = np.zeros(N_USERS)
    human_correction = np.zeros(N_USERS)

    for i, assignment in enumerate(assignments):
        if assignment == 0:
            success[i] = rng.binomial(
                1,
                0.82,
            )

            cost[i] = rng.normal(
                0.024,
                0.004,
            )

            latency[i] = rng.normal(
                1450,
                180,
            )

            faithfulness[i] = np.clip(
                rng.normal(
                    0.91,
                    0.05,
                ),
                0,
                1,
            )

            human_correction[i] = rng.binomial(
                1,
                0.18,
            )

        else:
            success[i] = rng.binomial(
                1,
                0.87,
            )

            cost[i] = rng.normal(
                0.019,
                0.004,
            )

            latency[i] = rng.normal(
                1320,
                170,
            )

            faithfulness[i] = np.clip(
                rng.normal(
                    0.92,
                    0.04,
                ),
                0,
                1,
            )

            human_correction[i] = rng.binomial(
                1,
                0.13,
            )

    control_mask = assignments == 0
    treatment_mask = assignments == 1

    result = analyze_binary_experiment(
        success[control_mask],
        success[treatment_mask],
    )

    print("Routing A/B experiment")

    print(
        f"Control users: "
        f"{control_mask.sum()}"
    )

    print(
        f"Treatment users: "
        f"{treatment_mask.sum()}"
    )

    print("\nPrimary metric: task success")

    print(
        f"Control success rate: "
        f"{result.control_mean:.3f}"
    )

    print(
        f"Treatment success rate: "
        f"{result.treatment_mean:.3f}"
    )

    print(
        f"Absolute lift: "
        f"{result.absolute_lift:.3f}"
    )

    print(
        f"Relative lift: "
        f"{result.relative_lift:.3%}"
    )

    print(
        "95% CI: "
        f"[{result.ci_lower:.3f}, "
        f"{result.ci_upper:.3f}]"
    )

    print("\nGuardrail metrics")

    summarize_metric(
        "Cost per request",
        cost[control_mask],
        cost[treatment_mask],
        unit=" USD",
    )

    summarize_metric(
        "Latency",
        latency[control_mask],
        latency[treatment_mask],
        unit=" ms",
    )

    summarize_metric(
        "Faithfulness",
        faithfulness[control_mask],
        faithfulness[treatment_mask],
    )

    summarize_metric(
        "Human correction rate",
        human_correction[control_mask],
        human_correction[treatment_mask],
    )


if __name__ == "__main__":
    simulate_experiment()