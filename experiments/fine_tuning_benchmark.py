from src.models.fine_tuning import FineTuningPlanner


def run_benchmark():
    planner = FineTuningPlanner()

    results = planner.compare()

    print("Fine-tuning strategy comparison")

    for result in results:
        print(f"\nStrategy: {result['strategy']}")
        print(f"Model: {result['name']}")
        print(
            f"Training examples: "
            f"{result['training_examples']}"
        )
        print(
            f"Quality: "
            f"{result['quality']:.3f}"
        )
        print(
            f"Faithfulness: "
            f"{result['faithfulness']:.3f}"
        )
        print(
            f"Latency (ms): "
            f"{result['latency_ms']:.1f}"
        )
        print(
            f"Cost (USD): "
            f"{result['cost_usd']:.4f}"
        )
        print(
            f"Utility: "
            f"{result['utility']:.3f}"
        )


if __name__ == "__main__":
    run_benchmark()