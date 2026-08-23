from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


RESULTS_PATH = Path("results/multi_seed_results.csv")
OUTPUT_DIR = Path("results/figures")


def load_results():
    return pd.read_csv(RESULTS_PATH)


def build_impact_summary(df):
    metrics = {
        "Cost reduction": "cost_reduction_pct",
        "Success improvement": "success_change_pp",
        "Latency reduction": "latency_reduction_pct",
        "Human correction reduction": "correction_reduction_pct",
        "Frontier usage reduction": "frontier_usage_change_pp",
    }

    rows = []

    for label, column in metrics.items():
        values = df[column].copy()

        if column == "frontier_usage_change_pp":
            values = -values

        mean = values.mean()
        std = values.std(ddof=1)
        ci_95 = 1.96 * std / (len(values) ** 0.5)

        rows.append({
            "metric": label,
            "mean": mean,
            "ci_95": ci_95,
        })  

    return pd.DataFrame(rows)


def plot_routing_impact():
    df = load_results()
    summary = build_impact_summary(df)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig, ax = plt.subplots(
        figsize=(10, 6),
    )

    bars = ax.barh(
        summary["metric"],
        summary["mean"],
        xerr=summary["ci_95"],
        capsize=4,
    )

    ax.set_xlabel(
        "Mean improvement across 10 simulation seeds"
    )

    ax.set_title(
        "Balanced Routing Policy: Mean Impact Across 10 Seeds"
    )

    ax.axvline(
        0,
        linewidth=1,
    )

    for bar, value in zip(
        bars,
        summary["mean"],
    ):
        ax.text(
            value + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f}",
            va="center",
        )

    fig.tight_layout()

    output_path = (
        OUTPUT_DIR
        / "routing_impact.png"
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
    plot_routing_impact()