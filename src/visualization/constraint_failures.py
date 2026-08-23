from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


RESULTS_PATH = Path(
    "results/constraint_failure_analysis.csv"
)
OUTPUT_DIR = Path("results/figures")


def plot_constraint_failures():
    df = pd.read_csv(RESULTS_PATH)

    complexity = df[
        df["dimension"] == "complexity"
    ].copy()

    sensitivity = df[
        df["dimension"] == "sensitivity"
    ].copy()

    order = ["low", "medium", "high"]

    complexity["value"] = pd.Categorical(
        complexity["value"],
        categories=order,
        ordered=True,
    )

    sensitivity["value"] = pd.Categorical(
        sensitivity["value"],
        categories=order,
        ordered=True,
    )

    complexity = complexity.sort_values("value")
    sensitivity = sensitivity.sort_values("value")

    plot_df = pd.DataFrame({
        "level": order,
        "complexity": (
            complexity["fallback_rate"].to_numpy()
            * 100
        ),
        "sensitivity": (
            sensitivity["fallback_rate"].to_numpy()
            * 100
        ),
    })

    x = range(len(plot_df))
    width = 0.35

    fig, ax = plt.subplots(
        figsize=(9, 6),
    )

    ax.bar(
        [i - width / 2 for i in x],
        plot_df["complexity"],
        width,
        label="Complexity",
    )

    ax.bar(
        [i + width / 2 for i in x],
        plot_df["sensitivity"],
        width,
        label="Sensitivity",
    )

    ax.set_xticks(
        list(x),
        ["Low", "Medium", "High"],
    )

    ax.set_ylabel(
        "Fallback rate (%)"
    )

    ax.set_xlabel(
        "Workload level"
    )

    ax.set_title(
        "Routing Fallbacks Rise for Harder Workloads"
    )

    ax.legend()

    ax.grid(
        axis="y",
        alpha=0.25,
    )

    fig.tight_layout()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIR
        / "constraint_failures.png"
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
    plot_constraint_failures()