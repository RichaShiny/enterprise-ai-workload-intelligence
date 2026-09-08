from src.telemetry.confidence import (
    calculate_evidence_confidence,
    wilson_lower_bound,
)
from src.telemetry.prior import RoutingPrior


def test_wilson_bound_penalizes_small_samples():
    small_sample = wilson_lower_bound(
        success_probability=1.0,
        sample_count=5,
    )

    large_sample = wilson_lower_bound(
        success_probability=1.0,
        sample_count=100,
    )

    assert small_sample < large_sample
    assert small_sample < 0.80
    assert large_sample > 0.90


def test_wilson_bound_stays_between_zero_and_one():
    result = wilson_lower_bound(
        success_probability=0.90,
        sample_count=20,
    )

    assert 0.0 <= result <= 1.0
    assert result < 0.90


def test_confidence_preserves_match_level():
    prior = RoutingPrior(
        success_probability=0.95,
        expected_latency_ms=1000.0,
        estimated_cost_usd=0.01,
        source="observed_telemetry",
        sample_count=20,
        match_level="exact",
        success_sample_count=20,
    )

    confidence = calculate_evidence_confidence(
        prior
    )

    assert confidence is not None
    assert confidence.match_level == "exact"
    assert confidence.sample_count == 20
    assert confidence.lower_success_bound < 0.95


def test_confidence_returns_none_without_success_data():
    prior = RoutingPrior(
        success_probability=None,
        expected_latency_ms=None,
        estimated_cost_usd=None,
        source="fallback",
        sample_count=0,
        match_level=None,
    )

    confidence = calculate_evidence_confidence(
        prior
    )

    assert confidence is None