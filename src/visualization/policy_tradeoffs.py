from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


RESULTS_PATH = Path("results/policy_tradeoffs.csv")
OUTPUT_DIR = Path("results/figures")


def plot_policy_tradeoffs():
    df = pd.read_csv(RESULTS_PATH)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    policy_labels = {
        "cost_optimized": "Cost optimized",
        "balanced": "Balanced",
        "reliability_first": "Reliability first",
        "strict": "Strict",
    }

    df["policy_label"] = df["policy"].map(
        policy_labels
    )

    fig, ax = plt.subplots(
        figsize=(9, 6),
    )

    scatter = ax.scatter(
        df["cost_reduction_pct"],
        df["constraint_satisfaction_rate"] * 100,
        s=120,
    )

    for _, row in df.iterrows():
        ax.annotate(
            row["policy_label"],
            (
                row["cost_reduction_pct"],
                row["constraint_satisfaction_rate"] * 100,
            ),
            xytext=(8, 7),
            textcoords="offset points",
        )

    ax.set_xlabel(
        "Cost reduction vs. baseline (%)"
    )

    ax.set_ylabel(
        "Workloads satisfying all constraints (%)"
    )

    ax.set_title(
        "Routing Policy Trade-off: Cost vs. Constraint Coverage"
    )

    ax.grid(
        alpha=0.25,
    )

    fig.tight_layout()

    output_path = (
        OUTPUT_DIR
        / "policy_tradeoffs.png"
    )

    fig.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        f"Saved figure to: {output_path}"
    )


if __name__ == "__main__":
    plot_policy_tradeoffs()