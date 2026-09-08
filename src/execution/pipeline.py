from dataclasses import dataclass

from src.execution.executors import ExecutionResult, OpenAIExecutor
from src.execution.strategy_selector import (
    StrategyDecision,
    StrategySelector,
)
from src.execution.verifier import OutputVerifier
from src.telemetry.schema import TelemetryEvent
from src.telemetry.store import TelemetryStore


SMALL_MODEL = "gpt-5-mini"
FRONTIER_MODEL = "gpt-5.2"


@dataclass
class PipelineResult:
    strategy: str
    final_result: ExecutionResult
    escalated: bool
    verification_passed: bool | None = None
    verification_confidence: float | None = None
    verification_reason: str | None = None


class ExecutionPipeline:
    def __init__(
        self,
        strategy_selector: StrategySelector | None = None,
        telemetry_store: TelemetryStore | None = None,
    ):
        self.executor = None
        self.verifier = None
        self.strategy_selector = strategy_selector
        self.telemetry_store = telemetry_store

    def _get_executor(self) -> OpenAIExecutor:
        if self.executor is None:
            self.executor = OpenAIExecutor()

        return self.executor

    def _get_verifier(self) -> OutputVerifier:
        if self.verifier is None:
            self.verifier = OutputVerifier()

        return self.verifier

    def choose_strategy(
        self,
        task_type: str,
        complexity: str,
        sensitivity: str,
    ) -> StrategyDecision:
        if self.strategy_selector is None:
            raise ValueError(
                "No strategy selector configured."
            )

        return self.strategy_selector.select(
            task_type=task_type,
            complexity=complexity,
            sensitivity=sensitivity,
        )

    def execute_auto(
        self,
        prompt: str,
        workload_id: str,
        task_type: str,
        complexity: str,
        sensitivity: str,
    ) -> PipelineResult:
        decision = self.choose_strategy(
            task_type=task_type,
            complexity=complexity,
            sensitivity=sensitivity,
        )

        result = self.execute(
            prompt=prompt,
            strategy=decision.strategy,
        )

        self._log_telemetry(
            workload_id=workload_id,
            task_type=task_type,
            complexity=complexity,
            sensitivity=sensitivity,
            result=result,
        )

        return result

    def _log_telemetry(
        self,
        workload_id: str,
        task_type: str,
        complexity: str,
        sensitivity: str,
        result: PipelineResult,
    ) -> None:
        if self.telemetry_store is None:
            return

        success = None

        if result.verification_passed is not None:
            success = result.verification_passed

        event = TelemetryEvent(
            workload_id=workload_id,
            task_type=task_type,
            complexity=complexity,
            sensitivity=sensitivity,
            strategy=result.strategy,
            model=result.final_result.model,
            latency_ms=result.final_result.latency_ms,
            input_tokens=result.final_result.input_tokens,
            output_tokens=result.final_result.output_tokens,
            total_tokens=result.final_result.total_tokens,
            escalated=result.escalated,
            verification_passed=result.verification_passed,
            verification_confidence=result.verification_confidence,
            estimated_cost_usd=None,
            success=success,
        )

        self.telemetry_store.log(event)

    def execute(
        self,
        prompt: str,
        strategy: str,
    ) -> PipelineResult:
        if strategy == "direct_small":
            result = self._get_executor().execute(
                prompt=prompt,
                model=SMALL_MODEL,
            )

            return PipelineResult(
                strategy=strategy,
                final_result=result,
                escalated=False,
            )

        if strategy == "direct_frontier":
            result = self._get_executor().execute(
                prompt=prompt,
                model=FRONTIER_MODEL,
            )

            return PipelineResult(
                strategy=strategy,
                final_result=result,
                escalated=False,
            )

        if strategy == "verified_cascade":
            small_result = self._get_executor().execute(
                prompt=prompt,
                model=SMALL_MODEL,
            )

            verification = self._get_verifier().verify(
                prompt=prompt,
                candidate_output=small_result.output_text,
            )

            if verification.passed:
                return PipelineResult(
                    strategy=strategy,
                    final_result=small_result,
                    escalated=False,
                    verification_passed=True,
                    verification_confidence=verification.confidence,
                    verification_reason=verification.reason,
                )

            frontier_result = self._get_executor().execute(
                prompt=prompt,
                model=FRONTIER_MODEL,
            )

            return PipelineResult(
                strategy=strategy,
                final_result=frontier_result,
                escalated=True,
                verification_passed=False,
                verification_confidence=verification.confidence,
                verification_reason=verification.reason,
            )

        raise ValueError(
            f"Unknown routing strategy: {strategy}"
        )