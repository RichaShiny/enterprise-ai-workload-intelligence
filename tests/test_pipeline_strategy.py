from src.execution.pipeline import ExecutionPipeline
from src.execution.strategy_selector import StrategySelector
from src.telemetry.estimator import TelemetryEstimator
from src.telemetry.schema import TelemetryEvent
from src.telemetry.store import TelemetryStore


def test_pipeline_uses_telemetry_strategy_selector(
    tmp_path,
):
    store = TelemetryStore(
        str(tmp_path / "events.jsonl")
    )

    for i in range(6):
        store.log(
            TelemetryEvent(
                workload_id=f"test-{i}",
                task_type="reasoning",
                complexity="medium",
                sensitivity="medium",
                strategy="direct_small",
                model="test-model",
                latency_ms=1000,
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

    pipeline = ExecutionPipeline(
        strategy_selector=selector,
    )

    decision = pipeline.choose_strategy(
        task_type="reasoning",
        complexity="medium",
        sensitivity="medium",
    )

    assert decision.strategy == "direct_small"
    assert decision.source == "observed_telemetry"