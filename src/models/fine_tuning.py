from dataclasses import dataclass
from typing import Dict, List


@dataclass
class FineTuningCandidate:
    name: str
    strategy: str
    training_examples: int
    expected_quality: float
    expected_faithfulness: float
    expected_latency_ms: float
    expected_cost_usd: float


class FineTuningPlanner:
    """
    Lightweight planning layer for comparing model adaptation strategies.

    This does not perform live fine-tuning. It defines and evaluates
    candidate strategies consistently inside the workload intelligence
    framework.
    """

    def __init__(self):
        self.candidates = self._build_candidates()

    def _build_candidates(self) -> List[FineTuningCandidate]:
        return [
            FineTuningCandidate(
                name="base_model",
                strategy="prompt_only",
                training_examples=0,
                expected_quality=0.81,
                expected_faithfulness=0.88,
                expected_latency_ms=1450.0,
                expected_cost_usd=0.018,
            ),
            FineTuningCandidate(
                name="rag_model",
                strategy="retrieval_augmented",
                training_examples=0,
                expected_quality=0.87,
                expected_faithfulness=0.93,
                expected_latency_ms=1780.0,
                expected_cost_usd=0.025,
            ),
            FineTuningCandidate(
                name="fine_tuned_model",
                strategy="supervised_fine_tuning",
                training_examples=250,
                expected_quality=0.90,
                expected_faithfulness=0.89,
                expected_latency_ms=1180.0,
                expected_cost_usd=0.012,
            ),
        ]

    def compare(
        self,
        quality_weight: float = 0.40,
        faithfulness_weight: float = 0.30,
        latency_weight: float = 0.15,
        cost_weight: float = 0.15,
    ) -> List[Dict[str, float]]:
        results = []

        max_latency = max(
            candidate.expected_latency_ms
            for candidate in self.candidates
        )

        max_cost = max(
            candidate.expected_cost_usd
            for candidate in self.candidates
        )

        for candidate in self.candidates:
            latency_score = (
                1.0
                - candidate.expected_latency_ms / max_latency
            )

            cost_score = (
                1.0
                - candidate.expected_cost_usd / max_cost
            )

            utility = (
                quality_weight * candidate.expected_quality
                + faithfulness_weight * candidate.expected_faithfulness
                + latency_weight * latency_score
                + cost_weight * cost_score
            )

            results.append(
                {
                    "name": candidate.name,
                    "strategy": candidate.strategy,
                    "training_examples": candidate.training_examples,
                    "quality": candidate.expected_quality,
                    "faithfulness": candidate.expected_faithfulness,
                    "latency_ms": candidate.expected_latency_ms,
                    "cost_usd": candidate.expected_cost_usd,
                    "utility": utility,
                }
            )

        return sorted(
            results,
            key=lambda item: item["utility"],
            reverse=True,
        )