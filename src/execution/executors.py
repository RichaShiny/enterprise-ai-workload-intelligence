import os
import time
from dataclasses import dataclass

from openai import OpenAI


@dataclass
class ExecutionResult:
    model: str
    output_text: str
    latency_ms: float
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


class OpenAIExecutor:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def execute(
        self,
        prompt: str,
        model: str,
        instructions: str | None = None,
    ) -> ExecutionResult:
        start = time.perf_counter()

        response = self.client.responses.create(
            model=model,
            input=prompt,
            instructions=instructions,
        )

        latency_ms = (time.perf_counter() - start) * 1000

        usage = response.usage

        return ExecutionResult(
            model=model,
            output_text=response.output_text,
            latency_ms=round(latency_ms, 2),
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        )