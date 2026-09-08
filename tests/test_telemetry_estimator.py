from src.telemetry.estimator import TelemetryEstimator
from src.telemetry.schema import TelemetryEvent
from src.telemetry.store import TelemetryStore


def make_event(
    workload_id: str,
    success: bool = True,
) -> TelemetryEvent:
    return TelemetryEvent(
        workload_id=workload_id,
        task_type="reasoning",
        complexity="high",
        sensitivity="medium",
        strategy="verified_cascade",
        model="gpt-5-mini",
        latency_ms=1000.0,
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        escalated=False,
        verification_passed=True,
        verification_confidence=0.9,
        estimated_cost_usd=0.01,
        success=success,
    )


def test_estimator_uses_sufficient_history(tmp_path):
    store = TelemetryStore(
        str(tmp_path / "events.jsonl")
    )

    for i in range(6):
        store.log(
            make_event(
                workload_id=f"test-{i}",
                success=i < 5,
            )
        )

    estimator = TelemetryEstimator(
        store=store,
        min_samples=5,
    )

    estimate = estimator.estimate(
        task_type="reasoning",
        complexity="high",
        sensitivity="medium",
        strategy="verified_cascade",
    )

    assert estimate is not None
    assert estimate.sample_count == 6
    assert estimate.success_rate == 5 / 6
    assert estimate.avg_latency_ms == 1000.0
    assert estimate.avg_cost_usd == 0.01


def test_estimator_rejects_sparse_history(tmp_path):
    store = TelemetryStore(
        str(tmp_path / "events.jsonl")
    )

    for i in range(3):
        store.log(
            make_event(
                workload_id=f"sparse-{i}"
            )
        )

    estimator = TelemetryEstimator(
        store=store,
        min_samples=5,
    )

    estimate = estimator.estimate(
        task_type="reasoning",
        complexity="high",
        sensitivity="medium",
        strategy="verified_cascade",
    )

    assert estimate is None