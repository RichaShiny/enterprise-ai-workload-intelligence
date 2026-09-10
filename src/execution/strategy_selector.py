from dataclasses import dataclass, field

from src.telemetry.confidence import (
    calculate_evidence_confidence,
)
from src.telemetry.estimator import TelemetryEstimator
from src.telemetry.prior import (
    RoutingPrior,
    build_routing_prior,
)


STRATEGIES = [
    "direct_small",
    "direct_frontier",
    "verified_cascade",
]


@dataclass
class StrategyDecision:
    strategy: str
    source: str
    sample_count: int
    success_probability: float | None
    expected_latency_ms: float | None
    estimated_cost_usd: float | None
    match_level: str | None = None
    success_sample_count: int = 0
    conservative_success_probability: float | None = None
    candidates: list[dict] = field(default_factory=list)


class StrategySelector:
    def __init__(
        self,
        estimator: TelemetryEstimator,
        min_success_probability: float = 0.80,
        max_latency_ms: float = 6000,
    ):
        self.estimator = estimator
        self.min_success_probability = min_success_probability
        self.max_latency_ms = max_latency_ms

    def select(
        self,
        task_type: str,
        complexity: str,
        sensitivity: str,
    ) -> StrategyDecision:
        priors = {
            strategy: build_routing_prior(
                estimator=self.estimator,
                task_type=task_type,
                complexity=complexity,
                sensitivity=sensitivity,
                strategy=strategy,
            )
            for strategy in STRATEGIES
        }

        observed = [
            (strategy, prior)
            for strategy, prior in priors.items()
            if prior.source == "observed_telemetry"
        ]

        candidates = [
            self._assess_candidate(strategy, prior)
            for strategy, prior in priors.items()
        ]

        feasible = [
            (strategy, prior)
            for strategy, prior in observed
            if next(
                candidate["eligible"]
                for candidate in candidates
                if candidate["strategy"] == strategy
            )
        ]

        if feasible:
            strategy, prior = min(
                feasible,
                key=lambda item: (
                    self._sortable_cost(item[1]),
                    self._sortable_latency(item[1]),
                ),
            )

            return self._decision(
                strategy=strategy,
                prior=prior,
                candidates=candidates,
            )

        fallback_strategy = self._fallback_strategy(
            complexity=complexity,
            sensitivity=sensitivity,
        )

        fallback_prior = priors[fallback_strategy]

        return self._decision(
            strategy=fallback_strategy,
            prior=fallback_prior,
            source="fallback_policy",
            candidates=candidates,
        )

    def _assess_candidate(
        self,
        strategy: str,
        prior: RoutingPrior,
    ) -> dict:
        """Make exclusions visible to an enterprise reviewer."""
        confidence = calculate_evidence_confidence(prior)
        reasons = []

        if prior.source != "observed_telemetry":
            reasons.append("Insufficient matching observed telemetry.")
        elif confidence is None:
            reasons.append("No completed success outcomes are available.")
        elif confidence.lower_success_bound < self.min_success_probability:
            reasons.append(
                "Conservative success estimate is below the policy minimum."
            )

        if (
            prior.expected_latency_ms is not None
            and prior.expected_latency_ms > self.max_latency_ms
        ):
            reasons.append("Expected latency exceeds the policy limit.")

        return {
            "strategy": strategy,
            "eligible": not reasons,
            "reasons": reasons,
            "sample_count": prior.sample_count,
            "match_level": prior.match_level,
            "success_probability": prior.success_probability,
            "conservative_success_probability": (
                confidence.lower_success_bound if confidence else None
            ),
            "expected_latency_ms": prior.expected_latency_ms,
            "estimated_cost_usd": prior.estimated_cost_usd,
        }

    def _meets_constraints(
        self,
        prior: RoutingPrior,
    ) -> bool:
        confidence = calculate_evidence_confidence(
            prior
        )

        if confidence is None:
            return False

        if (
            confidence.lower_success_bound
            < self.min_success_probability
        ):
            return False

        if (
            prior.expected_latency_ms is not None
            and prior.expected_latency_ms
            > self.max_latency_ms
        ):
            return False

        return True

    @staticmethod
    def _fallback_strategy(
        complexity: str,
        sensitivity: str,
    ) -> str:
        if sensitivity == "high":
            return "verified_cascade"

        if complexity == "high":
            return "verified_cascade"

        return "direct_small"

    @staticmethod
    def _sortable_cost(
        prior: RoutingPrior,
    ) -> float:
        if prior.estimated_cost_usd is None:
            return float("inf")

        return prior.estimated_cost_usd

    @staticmethod
    def _sortable_latency(
        prior: RoutingPrior,
    ) -> float:
        if prior.expected_latency_ms is None:
            return float("inf")

        return prior.expected_latency_ms

    @staticmethod
    def _decision(
        strategy: str,
        prior: RoutingPrior,
        source: str | None = None,
        candidates: list[dict] | None = None,
    ) -> StrategyDecision:
        confidence = calculate_evidence_confidence(
            prior
        )

        conservative_success_probability = None

        if confidence is not None:
            conservative_success_probability = (
                confidence.lower_success_bound
            )

        return StrategyDecision(
            strategy=strategy,
            source=source or prior.source,
            sample_count=prior.sample_count,
            success_probability=prior.success_probability,
            expected_latency_ms=prior.expected_latency_ms,
            estimated_cost_usd=prior.estimated_cost_usd,
            match_level=prior.match_level,
            success_sample_count=prior.success_sample_count,
            conservative_success_probability=(
                conservative_success_probability
            ),
            candidates=candidates or [],
        )
