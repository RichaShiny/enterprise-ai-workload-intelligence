from dataclasses import dataclass

from src.telemetry.estimator import TelemetryEstimator


@dataclass
class RoutingPrior:
    success_probability: float | None
    expected_latency_ms: float | None
    estimated_cost_usd: float | None
    source: str
    sample_count: int
    match_level: str | None = None
    success_sample_count: int = 0


def build_routing_prior(
    estimator: TelemetryEstimator,
    task_type: str,
    complexity: str,
    sensitivity: str,
    strategy: str,
) -> RoutingPrior:
    estimate = estimator.estimate(
        task_type=task_type,
        complexity=complexity,
        sensitivity=sensitivity,
        strategy=strategy,
    )

    if estimate is None:
        return RoutingPrior(
            success_probability=None,
            expected_latency_ms=None,
            estimated_cost_usd=None,
            source="fallback",
            sample_count=0,
            match_level=None,
            success_sample_count=0,
        )

    return RoutingPrior(
        success_probability=estimate.success_rate,
        expected_latency_ms=estimate.avg_latency_ms,
        estimated_cost_usd=estimate.avg_cost_usd,
        source="observed_telemetry",
        sample_count=estimate.sample_count,
        match_level=estimate.match_level,
        success_sample_count=estimate.success_sample_count,
    )