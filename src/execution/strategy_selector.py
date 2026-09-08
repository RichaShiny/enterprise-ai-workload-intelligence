from dataclasses import dataclass

from src.telemetry.estimator import TelemetryEstimator
from src.telemetry.prior import RoutingPrior, build_routing_prior


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

        feasible = [
            (strategy, prior)
            for strategy, prior in observed
            if self._meets_constraints(prior)
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
            )

        fallback_strategy = self._fallback_strategy(
            complexity=complexity,
            sensitivity=sensitivity,
        )

        fallback_prior = priors[fallback_strategy]

        return StrategyDecision(
            strategy=fallback_strategy,
            source="fallback_policy",
            sample_count=fallback_prior.sample_count,
            success_probability=fallback_prior.success_probability,
            expected_latency_ms=fallback_prior.expected_latency_ms,
            estimated_cost_usd=fallback_prior.estimated_cost_usd,
            match_level=fallback_prior.match_level,
        )

    def _meets_constraints(
        self,
        prior: RoutingPrior,
    ) -> bool:
        if prior.success_probability is None:
            return False

        if (
            prior.success_probability
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
    ) -> StrategyDecision:
        return StrategyDecision(
            strategy=strategy,
            source=prior.source,
            sample_count=prior.sample_count,
            success_probability=prior.success_probability,
            expected_latency_ms=prior.expected_latency_ms,
            estimated_cost_usd=prior.estimated_cost_usd,
            match_level=prior.match_level,
        )