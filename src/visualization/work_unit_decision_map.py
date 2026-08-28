from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch


FAILURE_COSTS = [0.00, 0.01, 0.02, 0.05, 0.10, 0.20, 0.50, 1.00, 2.00]
ESCALATION_RATIOS = [0.00, 0.05, 0.10, 0.20, 0.30]

SMALL_SUCCESS = 0.72
FRONTIER_SUCCESS = 0.96

SMALL_COST = 0.004
FRONTIER_COST = 0.018


def direct_small_cost(failure_cost):
    failure_probability = 1 - SMALL_SUCCESS
    return SMALL_COST + failure_probability * failure_cost


def direct_frontier_cost(failure_cost):
    failure_probability = 1 - FRONTIER_SUCCESS
    return FRONTIER_COST + failure_probability * failure_cost


def cascade_cost(failure_cost, escalation_ratio):
    small_failure_probability = 1 - SMALL_SUCCESS
    frontier_failure_probability = 1 - FRONTIER_SUCCESS

    escalation_cost = failure_cost * escalation_ratio

    execution_cost = (
        SMALL_COST
        + small_failure_probability * FRONTIER_COST
        + small_failure_probability * escalation_cost
    )

    unresolved_failure_cost = (
        small_failure_probability
        * frontier_failure_probability
        * failure_cost
    )

    return execution_cost + unresolved_failure_cost


def choose_strategy(failure_cost, escalation_ratio):
    costs = {
        "Direct small": direct_small_cost(failure_cost),
        "Cascade": cascade_cost(failure_cost, escalation_ratio),
        "Direct frontier": direct_frontier_cost(failure_cost),
    }

    return min(costs, key=costs.get)


def main():
    strategy_to_value = {
        "Direct small": 0,
        "Cascade": 1,
        "Direct frontier": 2,
    }

    matrix = []

    for escalation_ratio in ESCALATION_RATIOS:
        row = []

        for failure_cost in FAILURE_COSTS:
            strategy = choose_strategy(
                failure_cost=failure_cost,
                escalation_ratio=escalation_ratio,
            )
            row.append(strategy_to_value[strategy])

        matrix.append(row)

    matrix = np.array(matrix)

    cmap = ListedColormap(
        [
            "#5DADE2",
            "#F4D03F",
            "#EC7063",
        ]
    )

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.imshow(
        matrix,
        cmap=cmap,
        aspect="auto",
        interpolation="nearest",
    )

    ax.set_xticks(np.arange(len(FAILURE_COSTS)))
    ax.set_xticklabels(
        [f"${value:.2f}" for value in FAILURE_COSTS]
    )

    ax.set_yticks(np.arange(len(ESCALATION_RATIOS)))
    ax.set_yticklabels(
        [f"{ratio:.0%}" for ratio in ESCALATION_RATIOS]
    )

    ax.set_xlabel("Failure cost")
    ax.set_ylabel("Escalation cost as % of failure cost")

    ax.set_title(
        "Optimal Routing Strategy by Work Unit Economics",
        fontsize=15,
        pad=18,
    )

    for row_index, escalation_ratio in enumerate(ESCALATION_RATIOS):
        for column_index, failure_cost in enumerate(FAILURE_COSTS):
            strategy = choose_strategy(
                failure_cost=failure_cost,
                escalation_ratio=escalation_ratio,
            )

            short_label = {
                "Direct small": "Small",
                "Cascade": "Cascade",
                "Direct frontier": "Frontier",
            }[strategy]

            ax.text(
                column_index,
                row_index,
                short_label,
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
            )

    legend = [
        Patch(facecolor="#5DADE2", label="Direct small"),
        Patch(facecolor="#F4D03F", label="Small → frontier cascade"),
        Patch(facecolor="#EC7063", label="Direct frontier"),
    ]

    ax.legend(
        handles=legend,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=3,
        frameon=False,
    )

    ax.set_title(
        "Optimal Routing Strategy by Work Unit Economics\n"
        "Failure and escalation costs create distinct routing regimes",
        fontsize=14,
        pad=18,
    )

    plt.tight_layout()

    output_dir = Path("results/figures")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "work_unit_decision_map.png"

    plt.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )

    print(f"Saved figure to {output_path}")


if __name__ == "__main__":
    main()