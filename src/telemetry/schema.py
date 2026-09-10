from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class TelemetryEvent:
    workload_id: str
    task_type: str
    complexity: str
    sensitivity: str

    strategy: str
    model: str

    latency_ms: float
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None

    escalated: bool
    verification_passed: bool | None
    verification_confidence: float | None

    estimated_cost_usd: float | None = None
    success: bool | None = None

    # Decision metadata is deliberately limited to operational information.
    # Prompts, customer content, and model outputs do not belong in this ledger.
    decision_id: str | None = None
    recommended_strategy: str | None = None
    routing_source: str | None = None
    shadow_mode: bool = False

    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
