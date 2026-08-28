import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


OUTPUT_PATH = Path(
    "results/figures/generative_specialization_comparison.png"
)

models = [
    "Base Qwen",
    "Base + RAG",
    "LoRA",
]

exact_match = [0.00, 0.00, 0.65]
task_type = [0.00, 0.25, 0.80]
sensitivity = [0.05, 0.60, 0.80]
risk_level = [0.05, 0.35, 0.80]
strategy = [0.00, 0.25, 0.80]

metrics = {
    "Exact match": exact_match,
    "Task type": task_type,
    "Sensitivity": sensitivity,
    "Risk level": risk_level,
    "Routing strategy": strategy,
}

x = np.arange(len(models))
width = 0.15

fig, ax = plt.subplots(figsize=(11, 6))

offsets = np.linspace(
    -2 * width,
    2 * width,
    len(metrics),
)

for offset, (label, values) in zip(
    offsets,
    metrics.items(),
):
    bars = ax.bar(
        x + offset,
        values,
        width,
        label=label,
    )

    for bar, value in zip(bars, values):
        if value > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.025,
                f"{value:.0%}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

ax.set_ylabel("Accuracy")
ax.set_ylim(0, 1.08)
ax.set_xticks(x)
ax.set_xticklabels(models)

ax.set_title(
    "Generative Model Specialization: "
    "Prompting vs Retrieval vs LoRA"
)

ax.legend(
    loc="upper left",
    ncol=2,
)

ax.grid(
    axis="y",
    alpha=0.2,
)

fig.text(
    0.5,
    0.01,
    "Held-out synthetic benchmark: 20 workloads. "
    "All three approaches achieved 100% valid JSON.",
    ha="center",
    fontsize=9,
)

plt.tight_layout(rect=[0, 0.04, 1, 1])

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

plt.savefig(
    OUTPUT_PATH,
    dpi=200,
    bbox_inches="tight",
)

print(f"Saved figure to {OUTPUT_PATH}")