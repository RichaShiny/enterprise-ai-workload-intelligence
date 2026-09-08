from dataclasses import dataclass

from src.telemetry.store import TelemetryStore


@dataclass
class PerformanceEstimate:
    task_type: str
    complexity: str
    sensitivity: str
    strategy: str

    sample_count: int
    success_sample_count: int
    success_rate: float | None
    avg_latency_ms: float | None
    avg_cost_usd: float | None
    verification_pass_rate: float | None

    match_level: str


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

        match_levels = self._build_match_levels(
            task_type=task_type,
            complexity=complexity,
            sensitivity=sensitivity,
            strategy=strategy,
        )

        for match_level, matcher in match_levels:
            matching = [
                event
                for event in events
                if matcher(event)
            ]

            if len(matching) >= self.min_samples:
                return self._build_estimate(
                    matching=matching,
                    task_type=task_type,
                    complexity=complexity,
                    sensitivity=sensitivity,
                    strategy=strategy,
                    match_level=match_level,
                )

        return None

    def _build_match_levels(
        self,
        task_type: str,
        complexity: str,
        sensitivity: str,
        strategy: str,
    ):
        levels = [
            (
                "exact",
                lambda event: (
                    event["task_type"] == task_type
                    and event["complexity"] == complexity
                    and event["sensitivity"] == sensitivity
                    and event["strategy"] == strategy
                ),
            ),
            (
                "task_and_sensitivity",
                lambda event: (
                    event["task_type"] == task_type
                    and event["sensitivity"] == sensitivity
                    and event["strategy"] == strategy
                ),
            ),
        ]

        if sensitivity != "high":
            levels.extend(
                [
                    (
                        "task_and_complexity",
                        lambda event: (
                            event["task_type"] == task_type
                            and event["complexity"] == complexity
                            and event["strategy"] == strategy
                        ),
                    ),
                    (
                        "task",
                        lambda event: (
                            event["task_type"] == task_type
                            and event["strategy"] == strategy
                        ),
                    ),
                    (
                        "strategy",
                        lambda event: (
                            event["strategy"] == strategy
                        ),
                    ),
                ]
            )

        return levels

    def _build_estimate(
        self,
        matching: list[dict],
        task_type: str,
        complexity: str,
        sensitivity: str,
        strategy: str,
        match_level: str,
    ) -> PerformanceEstimate:
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
            success_sample_count=len(success_values),
            success_rate=self._mean(success_values),
            avg_latency_ms=self._mean(latency_values),
            avg_cost_usd=self._mean(cost_values),
            verification_pass_rate=self._mean(
            verification_values
            ),
            match_level=match_level,
        )

    @staticmethod
    def _mean(values):
        if not values:
            return None

        return sum(values) / len(values)