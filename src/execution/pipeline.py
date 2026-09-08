from dataclasses import dataclass

from src.execution.executors import ExecutionResult, OpenAIExecutor
from src.execution.verifier import OutputVerifier


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
    def __init__(self):
        self.executor = OpenAIExecutor()
        self.verifier = OutputVerifier()

    def execute(
        self,
        prompt: str,
        strategy: str,
    ) -> PipelineResult:

        if strategy == "direct_small":
            result = self.executor.execute(
                prompt=prompt,
                model=SMALL_MODEL,
            )

            return PipelineResult(
                strategy=strategy,
                final_result=result,
                escalated=False,
            )

        if strategy == "direct_frontier":
            result = self.executor.execute(
                prompt=prompt,
                model=FRONTIER_MODEL,
            )

            return PipelineResult(
                strategy=strategy,
                final_result=result,
                escalated=False,
            )

        if strategy == "verified_cascade":
            small_result = self.executor.execute(
                prompt=prompt,
                model=SMALL_MODEL,
            )

            verification = self.verifier.verify(
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

            frontier_result = self.executor.execute(
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

        raise ValueError(f"Unknown routing strategy: {strategy}")