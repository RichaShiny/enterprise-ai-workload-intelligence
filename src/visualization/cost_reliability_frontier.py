from pathlib import Path

import matplotlib.pyplot as plt


DATA = [
    {
        "workload": "Summarization",
        "strategy": "Direct small",
        "cost": 0.0050,
        "success": 0.900,
    },
    {
        "workload": "Summarization",
        "strategy": "Verified cascade",
        "cost": 0.0083,
        "success": 0.992,
    },
    {
        "workload": "Summarization",
        "strategy": "Direct frontier",
        "cost": 0.0183,
        "success": 0.970,
    },
    {
        "workload": "Technical reasoning",
        "strategy": "Direct small",
        "cost": 0.0360,
        "success": 0.680,
    },
    {
        "workload": "Technical reasoning",
        "strategy": "Verified cascade",
        "cost": 0.0213,
        "success": 0.968,
    },
    {
        "workload": "Technical reasoning",
        "strategy": "Direct frontier",
        "cost": 0.0230,
        "success": 0.950,
    },
    {
        "workload": "Compliance",
        "strategy": "Direct small",
        "cost": 0.4540,
        "success": 0.550,
    },
    {
        "workload": "Compliance",
        "strategy": "Verified cascade",
        "cost": 0.1416,
        "success": 0.960,
    },
    {
        "workload": "Compliance",
        "strategy": "Direct frontier",
        "cost": 0.0580,
        "success": 0.960,
    },
]


def main():
    fig, ax = plt.subplots(figsize=(12, 7))

    strategy_styles = {
        "Direct small": {
            "marker": "o",
            "label": "Direct small",
        },
        "Verified cascade": {
            "marker": "s",
            "label": "Verified cascade",
        },
        "Direct frontier": {
            "marker": "^",
            "label": "Direct frontier",
        },
    }

    for strategy, style in strategy_styles.items():
        points = [
            row
            for row in DATA
            if row["strategy"] == strategy
        ]

        ax.scatter(
            [row["cost"] for row in points],
            [row["success"] * 100 for row in points],
            marker=style["marker"],
            s=150,
            label=style["label"],
        )

    offsets = {
        ("Summarization", "Direct small"): (8, -18),
        ("Summarization", "Verified cascade"): (8, 10),
        ("Summarization", "Direct frontier"): (8, -18),

        ("Technical reasoning", "Direct small"): (8, -18),
        ("Technical reasoning", "Verified cascade"): (8, 10),
        ("Technical reasoning", "Direct frontier"): (8, -18),

        ("Compliance", "Direct small"): (-85, 10),
        ("Compliance", "Verified cascade"): (8, 10),
        ("Compliance", "Direct frontier"): (8, 10),
    }

    for row in DATA:
        offset = offsets[
            (row["workload"], row["strategy"])
        ]

        ax.annotate(
            row["workload"],
            (
                row["cost"],
                row["success"] * 100,
            ),
            xytext=offset,
            textcoords="offset points",
            fontsize=9,
        )

    ax.set_xscale("log")

    ax.set_xlabel(
        "Expected total cost per Work Unit (log scale)"
    )

    ax.set_ylabel(
        "Final success probability (%)"
    )

    ax.set_title(
        "Cost vs Reliability Across Routing Strategies\n"
        "The cheapest model call is not always "
        "the best completed-work strategy",
        fontsize=14,
        pad=18,
    )

    ax.grid(
        alpha=0.25,
        linestyle="--",
    )

    ax.legend(
        frameon=False,
        loc="lower left",
    )

    ax.set_ylim(50, 102)

    plt.tight_layout()

    output_dir = Path("results/figures")
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / "cost_reliability_frontier.png"
    )

    plt.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )

    print(
        f"Saved figure to {output_path}"
    )


if __name__ == "__main__":
    main()