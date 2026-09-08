from dataclasses import dataclass
from math import sqrt

from src.telemetry.prior import RoutingPrior


@dataclass
class EvidenceConfidence:
    observed_success_probability: float
    lower_success_bound: float
    sample_count: int
    match_level: str | None


def wilson_lower_bound(
    success_probability: float,
    sample_count: int,
    z: float = 1.96,
) -> float:
    if sample_count <= 0:
        return 0.0

    p = success_probability
    n = sample_count

    denominator = 1 + (z**2 / n)

    center = p + (z**2 / (2 * n))

    adjustment = z * sqrt(
        (p * (1 - p) / n)
        + (z**2 / (4 * n**2))
    )

    lower_bound = (
        center - adjustment
    ) / denominator

    return max(
        0.0,
        min(1.0, lower_bound),
    )


def calculate_evidence_confidence(
    prior: RoutingPrior,
) -> EvidenceConfidence | None:
    if prior.success_probability is None:
        return None

    if prior.success_sample_count <= 0:
        return None

    lower_bound = wilson_lower_bound(
        success_probability=prior.success_probability,
        sample_count=prior.success_sample_count,
    )

    return EvidenceConfidence(
        observed_success_probability=prior.success_probability,
        lower_success_bound=lower_bound,
        sample_count=prior.success_sample_count,
        match_level=prior.match_level,
    )