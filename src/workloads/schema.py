from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class WorkloadEvent:
    event_id: str
    department: str
    workflow: str
    task_type: str

    tool: str
    model: str
    agent_type: str

    complexity: str
    sensitivity: str
    business_priority: int

    tokens_in: int
    tokens_out: int
    latency_ms: float
    estimated_cost_usd: float

    human_time_minutes: float
    human_corrections: int

    task_success: bool
    quality_score: float

    notes: Optional[str] = None

    def to_dict(self):
        return asdict(self)