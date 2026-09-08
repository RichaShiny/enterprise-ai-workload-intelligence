from dataclasses import dataclass

from src.telemetry.store import TelemetryStore


@dataclass
class PerformanceEstimate:
    task_type: str
    complexity: str
    sensitivity: str
    strategy: str

    sample_count: int
    success_rate: float | None
    avg_latency_ms: float | None
    avg_cost_usd: float | None
    verification_pass_rate: float | None


class TelemetryEstimator:
    def __init__(
        self,
        store: TelemetryStore,
        min_samples: int = 5,
    ):
        self.store = store
        self.min_samples = min_samples

    def estimate(
        self,
        task_type: str,
        complexity: str,
        sensitivity: str,
        strategy: str,
    ) -> PerformanceEstimate | None:
        events = self.store.load()

        matching = [
            event
            for event in events
            if event["task_type"] == task_type
            and event["complexity"] == complexity
            and event["sensitivity"] == sensitivity
            and event["strategy"] == strategy
        ]

        if len(matching) < self.min_samples:
            return None

        success_values = [
            event["success"]
            for event in matching
            if event.get("success") is not None
        ]

        latency_values = [
            event["latency_ms"]
            for event in matching
            if event.get("latency_ms") is not None
        ]

        cost_values = [
            event["estimated_cost_usd"]
            for event in matching
            if event.get("estimated_cost_usd") is not None
        ]

        verification_values = [
            event["verification_passed"]
            for event in matching
            if event.get("verification_passed") is not None
        ]

        return PerformanceEstimate(
            task_type=task_type,
            complexity=complexity,
            sensitivity=sensitivity,
            strategy=strategy,
            sample_count=len(matching),
            success_rate=self._mean(success_values),
            avg_latency_ms=self._mean(latency_values),
            avg_cost_usd=self._mean(cost_values),
            verification_pass_rate=self._mean(
                verification_values
            ),
        )

    @staticmethod
    def _mean(values):
        if not values:
            return None

        return sum(values) / len(values)