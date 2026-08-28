import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


def main():
    labels = [
        "Known\nATE",
        "Naive",
        "IPW",
        "Doubly\nRobust",
        "Double\nML",
    ]

    estimates = [
        0.1471,
        0.0956,
        0.1476,
        0.1410,
        0.1296,
    ]

    true_ate = 0.1471

    x = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(9, 5.5))

    bars = ax.bar(x, estimates)

    ax.axhline(
        true_ate,
        linestyle="--",
        linewidth=1.5,
        label=f"Known simulated ATE = {true_ate:.3f}",
    )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)

    ax.set_ylabel("Estimated treatment effect")
    ax.set_title(
        "Causal Estimation Under Confounded Routing\n"
        "Adjustment recovers much of the treatment effect hidden by naive comparison"
    )

    ax.set_ylim(0, 0.18)

    for bar, value in zip(bars, estimates):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.003,
            f"{value:.3f}",
            ha="center",
            va="bottom",
        )

    ax.legend()

    fig.tight_layout()

    output_dir = Path("results/figures")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "causal_estimation_comparison.png"

    fig.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )

    print(f"Saved figure to {output_path}")


if __name__ == "__main__":
    main()