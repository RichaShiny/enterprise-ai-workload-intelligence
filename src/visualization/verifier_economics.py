from pathlib import Path

import matplotlib.pyplot as plt


VERIFIERS = [
    "Weak",
    "Moderate",
    "Strong",
]

RESULTS = {
    "Summarization": {
        "total_cost": [0.0095, 0.0088, 0.0083],
        "accepted_bad_rate": [3.0, 1.5, 0.5],
    },
    "Technical reasoning": {
        "total_cost": [0.0282, 0.0240, 0.0213],
        "accepted_bad_rate": [9.6, 4.8, 1.6],
    },
    "Compliance": {
        "total_cost": [0.2365, 0.1793, 0.1416],
        "accepted_bad_rate": [13.5, 6.8, 2.3],
    },
}


def main():
    fig, ax = plt.subplots(figsize=(11, 7))

    markers = {
        "Summarization": "o",
        "Technical reasoning": "s",
        "Compliance": "^",
    }

    for workload, values in RESULTS.items():
        ax.plot(
            VERIFIERS,
            values["total_cost"],
            marker=markers[workload],
            markersize=9,
            linewidth=2,
            label=workload,
        )

        for verifier, cost, bad_rate in zip(
            VERIFIERS,
            values["total_cost"],
            values["accepted_bad_rate"],
        ):
            ax.annotate(
                f"{bad_rate:.1f}% bad accepted",
                (verifier, cost),
                xytext=(8, 8),
                textcoords="offset points",
                fontsize=8,
            )

    ax.set_xlabel("Verifier quality")
    ax.set_ylabel("Expected total cost per Work Unit")

    ax.set_title(
        "Verification Quality Changes Work Unit Economics\n"
        "Stronger verification can justify additional escalation "
        "when unresolved failures are expensive",
        fontsize=14,
        pad=18,
    )

    ax.grid(
        alpha=0.25,
        linestyle="--",
    )

    ax.legend(
        frameon=False,
        loc="upper right",
    )

    plt.tight_layout()

    output_dir = Path("results/figures")
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / "verifier_economics.png"
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