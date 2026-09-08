from src.execution.strategy_selector import StrategySelector
from src.telemetry.estimator import TelemetryEstimator
from src.telemetry.schema import TelemetryEvent
from src.telemetry.store import TelemetryStore


def log_events(
    store: TelemetryStore,
    strategy: str,
    count: int,
    success_count: int,
    latency_ms: float,
    cost_usd: float,
) -> None:
    for i in range(count):
        store.log(
            TelemetryEvent(
                workload_id=f"{strategy}-{i}",
                task_type="reasoning",
                complexity="medium",
                sensitivity="medium",
                strategy=strategy,
                model="test-model",
                latency_ms=latency_ms,
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                escalated=False,
                verification_passed=None,
                verification_confidence=None,
                estimated_cost_usd=cost_usd,
                success=i < success_count,
            )
        )


def test_selector_chooses_cheapest_feasible_strategy(
    tmp_path,
):
    store = TelemetryStore(
        str(tmp_path / "events.jsonl")
    )

    log_events(
        store,
        strategy="direct_small",
        count=6,
        success_count=6,
        latency_ms=1000,
        cost_usd=0.005,
    )

    log_events(
        store,
        strategy="direct_frontier",
        count=6,
        success_count=6,
        latency_ms=2000,
        cost_usd=0.020,
    )

    log_events(
        store,
        strategy="verified_cascade",
        count=6,
        success_count=6,
        latency_ms=1500,
        cost_usd=0.010,
    )

    estimator = TelemetryEstimator(
        store=store,
        min_samples=5,
    )

    selector = StrategySelector(
        estimator=estimator,
    )

    decision = selector.select(
        task_type="reasoning",
        complexity="medium",
        sensitivity="medium",
    )

    assert decision.strategy == "direct_small"
    assert decision.source == "observed_telemetry"
    assert decision.sample_count == 6


def test_selector_rejects_unreliable_strategy(
    tmp_path,
):
    store = TelemetryStore(
        str(tmp_path / "events.jsonl")
    )

    log_events(
        store,
        strategy="direct_small",
        count=6,
        success_count=3,
        latency_ms=1000,
        cost_usd=0.005,
    )

    log_events(
        store,
        strategy="verified_cascade",
        count=6,
        success_count=6,
        latency_ms=1500,
        cost_usd=0.010,
    )

    estimator = TelemetryEstimator(
        store=store,
        min_samples=5,
    )

    selector = StrategySelector(
        estimator=estimator,
        min_success_probability=0.80,
    )

    decision = selector.select(
        task_type="reasoning",
        complexity="medium",
        sensitivity="medium",
    )

    assert decision.strategy == "verified_cascade"
    assert decision.source == "observed_telemetry"


def test_selector_falls_back_when_history_is_sparse(
    tmp_path,
):
    store = TelemetryStore(
        str(tmp_path / "events.jsonl")
    )

    estimator = TelemetryEstimator(
        store=store,
        min_samples=5,
    )

    selector = StrategySelector(
        estimator=estimator,
    )

    decision = selector.select(
        task_type="reasoning",
        complexity="high",
        sensitivity="medium",
    )

    assert decision.strategy == "verified_cascade"
    assert decision.source == "fallback_policy"

def test_selector_exposes_telemetry_match_level(
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

    selector = StrategySelector(
        estimator=estimator,
    )

    decision = selector.select(
        task_type="reasoning",
        complexity="high",
        sensitivity="medium",
    )

    assert decision.strategy == "direct_small"
    assert decision.source == "observed_telemetry"
    assert decision.match_level == "task_and_sensitivity"
    assert decision.sample_count == 6