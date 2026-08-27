from src.evaluation.faithfulness import FaithfulnessEvaluator


CASES = [
    {
        "name": "fully_supported",
        "contexts": [
            (
                "Frontier models generally provide stronger reasoning "
                "ability but introduce higher inference cost and latency."
            )
        ],
        "claims": [
            "Frontier models can provide stronger reasoning performance.",
            "Frontier models can have higher inference costs.",
        ],
    },
    {
        "name": "partially_supported",
        "contexts": [
            (
                "Smaller local models may handle low-complexity "
                "summarization when quality requirements are moderate."
            )
        ],
        "claims": [
            "Small local models can handle simple summarization.",
            "Small local models always outperform frontier models.",
        ],
    },
    {
        "name": "unsupported",
        "contexts": [
            (
                "Deterministic automation is appropriate for repetitive "
                "workflows with clear rules."
            )
        ],
        "claims": [
            "Deterministic automation produces better creative writing.",
        ],
    },
    {
    "name": "contradiction",
    "contexts": [
        (
            "Frontier models generally provide stronger reasoning "
            "ability but introduce higher inference cost and latency."
        )
    ],
    "claims": [
        "Frontier models always have lower latency than local models.",
    ],
},
{
    "name": "unsupported_detail",
    "contexts": [
        (
            "Small local models may handle low-complexity summarization "
            "when quality requirements are moderate."
        )
    ],
    "claims": [
        "Small local models reduce inference cost by exactly 60 percent.",
    ],
},
]


def run_benchmark():
    evaluator = FaithfulnessEvaluator()

    scores = []

    for case in CASES:
        result = evaluator.evaluate(
            claims=case["claims"],
            retrieved_contexts=case["contexts"],
        )

        scores.append(result.score)

        print(f"\nCase: {case['name']}")
        print(
            f"Faithfulness score: "
            f"{result.score:.3f}"
        )
        print(
            f"Supported claims: "
            f"{result.supported_claims}/"
            f"{result.total_claims}"
        )

        if result.unsupported_claims:
            print("Unsupported claims:")
            for claim in result.unsupported_claims:
                print(f"- {claim}")

        if result.contradiction_claims:
            print("Contradiction claims:")
            for claim in result.contradiction_claims:
                print(f"- {claim}")

    average_score = sum(scores) / len(scores)

    print(
        f"\nAverage faithfulness score: "
        f"{average_score:.3f}"
    )


if __name__ == "__main__":
    run_benchmark()