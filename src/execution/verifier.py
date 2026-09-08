import json
from dataclasses import dataclass

from src.execution.executors import OpenAIExecutor


VERIFIER_MODEL = "gpt-5-mini"


@dataclass
class VerificationResult:
    passed: bool
    confidence: float
    reason: str


class OutputVerifier:
    def __init__(self):
        self.executor = OpenAIExecutor()

    def verify(self, prompt: str, candidate_output: str) -> VerificationResult:
        verification_prompt = f"""
You are evaluating whether an AI-generated answer adequately satisfies
the original user request.

Original request:
{prompt}

Candidate answer:
{candidate_output}

Evaluate the answer for:
- relevance
- completeness
- internal consistency
- obvious factual or reasoning problems

Return ONLY valid JSON in this exact format:
{{
  "passed": true,
  "confidence": 0.0,
  "reason": "brief explanation"
}}
"""

        result = self.executor.execute(
            prompt=verification_prompt,
            model=VERIFIER_MODEL,
        )

        try:
            parsed = json.loads(result.output_text)

            return VerificationResult(
                passed=bool(parsed["passed"]),
                confidence=float(parsed["confidence"]),
                reason=str(parsed["reason"]),
            )

        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return VerificationResult(
                passed=False,
                confidence=0.0,
                reason="Verifier returned an invalid response.",
            )