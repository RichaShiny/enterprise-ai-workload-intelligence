from src.evaluation.regression import RegressionEvaluator


BASELINE = {
    "task_success": 0.82,
    "quality": 0.84,
    "faithfulness": 0.91,
    "latency_ms": 1450.0,
    "cost_per_request": 0.024,
}


CANDIDATES = {
    "candidate_a": {
        "task_success": 0.86,
        "quality": 0.89,
        "faithfulness": 0.84,
        "latency_ms": 1380.0,
        "cost_per_request": 0.021,
    },
    "candidate_b": {
        "task_success": 0.85,
        "quality": 0.87,
        "faithfulness": 0.92,
        "latency_ms": 1320.0,
        "cost_per_request": 0.020,
    },
}


HIGHER_IS_BETTER = {
    "task_success": True,
    "quality": True,
    "faithfulness": True,
    "latency_ms": False,
    "cost_per_request": False,
}


def run_regression_suite():
    evaluator = RegressionEvaluator(
    default_tolerance=0.02,
    metric_tolerances={
        "task_success": 0.02,
        "quality": 0.02,
        "faithfulness": 0.01,
        "latency_ms": 100.0,
        "cost_per_request": 0.002,
    },
)

    print("Baseline")
    for metric, value in BASELINE.items():
        print(f"{metric}: {value}")

    for candidate_name, candidate_metrics in CANDIDATES.items():
        result = evaluator.compare(
            baseline=BASELINE,
            candidate=candidate_metrics,
            higher_is_better=HIGHER_IS_BETTER,
        )

        print(f"\nCandidate: {candidate_name}")
        print(f"Passed regression gate: {result.passed}")

        print("Improvements:")
        for metric in result.improvements:
            print(f"- {metric}")

        print("Regressions:")
        for metric in result.regressions:
            print(f"- {metric}")

        print("Within tolerance:")
        for metric in result.unchanged:
            print(f"- {metric}")


if __name__ == "__main__":
    run_regression_suite()