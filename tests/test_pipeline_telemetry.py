from src.execution.executors import ExecutionResult
from src.execution.pipeline import ExecutionPipeline
from src.execution.strategy_selector import StrategyDecision
from src.telemetry.store import TelemetryStore


class FakeStrategySelector:
    def select(
        self,
        task_type: str,
        complexity: str,
        sensitivity: str,
    ) -> StrategyDecision:
        return StrategyDecision(
            strategy="direct_small",
            source="fallback_policy",
            sample_count=0,
            success_probability=None,
            expected_latency_ms=None,
            estimated_cost_usd=None,
        )


class FakeExecutor:
    def execute(
        self,
        prompt: str,
        model: str,
        instructions: str | None = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            model=model,
            output_text="Fake model response",
            latency_ms=250.0,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )


def test_execute_auto_logs_telemetry(tmp_path):
    store = TelemetryStore(
        str(tmp_path / "events.jsonl")
    )

    pipeline = ExecutionPipeline(
        strategy_selector=FakeStrategySelector(),
        telemetry_store=store,
    )

    pipeline.executor = FakeExecutor()

    result = pipeline.execute_auto(
        prompt="Analyze this problem",
        workload_id="workload-001",
        task_type="reasoning",
        complexity="medium",
        sensitivity="low",
    )

    events = store.load()

    assert result.strategy == "direct_small"
    assert result.final_result.output_text == "Fake model response"

    assert len(events) == 1

    event = events[0]

    assert event["workload_id"] == "workload-001"
    assert event["task_type"] == "reasoning"
    assert event["complexity"] == "medium"
    assert event["sensitivity"] == "low"

    assert event["strategy"] == "direct_small"
    assert event["model"] == "gpt-5-mini"

    assert event["latency_ms"] == 250.0
    assert event["input_tokens"] == 100
    assert event["output_tokens"] == 50
    assert event["total_tokens"] == 150

    assert event["escalated"] is False
    assert event["success"] is None