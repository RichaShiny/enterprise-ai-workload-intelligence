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

def test_estimator_backs_off_to_task_and_sensitivity(
    tmp_path,
):
    store = TelemetryStore(
        str(tmp_path / "events.jsonl")
    )

    complexities = [
        "low",
        "low",
        "medium",
        "medium",
        "high",
        "high",
    ]

    for i, complexity in enumerate(complexities):
        store.log(
            TelemetryEvent(
                workload_id=f"backoff-{i}",
                task_type="reasoning",
                complexity=complexity,
                sensitivity="medium",
                strategy="direct_small",
                model="test-model",
                latency_ms=1000.0,
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                escalated=False,
                verification_passed=None,
                verification_confidence=None,
                estimated_cost_usd=0.005,
                success=True,
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
        strategy="direct_small",
    )

    assert estimate is not None
    assert estimate.sample_count == 6
    assert estimate.match_level == "task_and_sensitivity"


def test_estimator_prefers_exact_match(
    tmp_path,
):
    store = TelemetryStore(
        str(tmp_path / "events.jsonl")
    )

    for i in range(5):
        store.log(
            TelemetryEvent(
                workload_id=f"exact-{i}",
                task_type="reasoning",
                complexity="high",
                sensitivity="medium",
                strategy="direct_small",
                model="test-model",
                latency_ms=900.0,
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                escalated=False,
                verification_passed=None,
                verification_confidence=None,
                estimated_cost_usd=0.004,
                success=True,
            )
        )

    for i in range(5):
        store.log(
            TelemetryEvent(
                workload_id=f"broader-{i}",
                task_type="reasoning",
                complexity="low",
                sensitivity="medium",
                strategy="direct_small",
                model="test-model",
                latency_ms=3000.0,
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                escalated=False,
                verification_passed=None,
                verification_confidence=None,
                estimated_cost_usd=0.020,
                success=False,
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
        strategy="direct_small",
    )

    assert estimate is not None
    assert estimate.match_level == "exact"
    assert estimate.sample_count == 5
    assert estimate.success_rate == 1.0
    assert estimate.avg_latency_ms == 900.0


def test_high_sensitivity_does_not_use_lower_sensitivity_history(
    tmp_path,
):
    store = TelemetryStore(
        str(tmp_path / "events.jsonl")
    )

    for i in range(10):
        store.log(
            TelemetryEvent(
                workload_id=f"low-sensitivity-{i}",
                task_type="reasoning",
                complexity="high",
                sensitivity="low",
                strategy="direct_small",
                model="test-model",
                latency_ms=700.0,
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                escalated=False,
                verification_passed=None,
                verification_confidence=None,
                estimated_cost_usd=0.003,
                success=True,
            )
        )

    estimator = TelemetryEstimator(
        store=store,
        min_samples=5,
    )

    estimate = estimator.estimate(
        task_type="reasoning",
        complexity="high",
        sensitivity="high",
        strategy="direct_small",
    )

    assert estimate is None
    
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