import os
from collections import Counter
from statistics import mean
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.telemetry.schema import TelemetryEvent
from src.telemetry.store import TelemetryStore

app = FastAPI(
    title="Enterprise AI Workload Intelligence",
    description="Production-style API for workload-aware AI routing.",
    version="1.0.0",
)


class RouteRequest(BaseModel):
    task_type: str
    sensitivity: str
    risk_level: str
    complexity: str = "medium"


class ShadowRouteRequest(RouteRequest):
    active_strategy: str = Field(
        description="The strategy the application used for this workload."
    )


class OutcomeRequest(BaseModel):
    workload_id: str
    task_type: str
    complexity: str = "medium"
    sensitivity: str
    strategy: str
    model: str = "unspecified"
    latency_ms: float = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    escalated: bool = False
    verification_passed: bool | None = None
    verification_confidence: float | None = Field(default=None, ge=0, le=1)
    estimated_cost_usd: float | None = Field(default=None, ge=0)
    success: bool | None = None
    decision_id: str | None = None
    recommended_strategy: str | None = None
    routing_source: str | None = None
    shadow_mode: bool = False


telemetry_store = TelemetryStore(
    os.getenv("TELEMETRY_PATH", "data/telemetry/events.jsonl")
)


def choose_strategy(request: RouteRequest) -> str:
    """A transparent starter policy until observed telemetry is sufficient."""
    task_type = request.task_type.lower()
    sensitivity = request.sensitivity.lower()
    risk_level = request.risk_level.lower()

    if sensitivity == "high" or risk_level == "high":
        return "direct_frontier"
    if task_type in {"technical_reasoning", "compliance", "retrieval"}:
        return "verified_cascade"
    return "direct_small"


def summarize_events(events: list[dict]) -> dict:
    """Return decision-ready, content-free operational intelligence."""
    completed = [event for event in events if event.get("success") is not None]
    latencies = [event["latency_ms"] for event in events if event.get("latency_ms") is not None]
    costs = [event["estimated_cost_usd"] for event in events if event.get("estimated_cost_usd") is not None]
    disagreements = [
        event
        for event in events
        if event.get("recommended_strategy")
        and event.get("recommended_strategy") != event.get("strategy")
    ]

    strategies = Counter(event["strategy"] for event in events)
    by_strategy = []
    for strategy, count in sorted(strategies.items()):
        strategy_events = [event for event in events if event["strategy"] == strategy]
        strategy_completed = [event for event in strategy_events if event.get("success") is not None]
        by_strategy.append({
            "strategy": strategy,
            "events": count,
            "success_rate": (
                sum(event["success"] for event in strategy_completed) / len(strategy_completed)
                if strategy_completed else None
            ),
            "average_latency_ms": (
                mean(event["latency_ms"] for event in strategy_events)
                if strategy_events else None
            ),
            "estimated_cost_usd": round(
                sum(event.get("estimated_cost_usd") or 0 for event in strategy_events), 6
            ),
        })

    return {
        "events_recorded": len(events),
        "completed_outcomes": len(completed),
        "outcomes_pending": len(events) - len(completed),
        "observed_success_rate": (
            sum(event["success"] for event in completed) / len(completed)
            if completed else None
        ),
        "average_latency_ms": round(mean(latencies), 2) if latencies else None,
        "estimated_cost_usd": round(sum(costs), 6),
        "shadow_recommendation_disagreements": len(disagreements),
        "by_strategy": by_strategy,
        "privacy": "Operational metadata only; this service does not store prompts or model outputs.",
    }

@app.get("/")
def root():
    return {
        "service": "Enterprise AI Workload Intelligence",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/route")
def route_workload(request: RouteRequest):
    strategy = choose_strategy(request)

    return {
        "task_type": request.task_type,
        "sensitivity": request.sensitivity,
        "risk_level": request.risk_level,
        "recommended_strategy": strategy,
        "note": "Starter policy. Its benchmark assumptions are simulation-based until observed telemetry is collected.",
    }


@app.post("/shadow-route")
def shadow_route(request: ShadowRouteRequest):
    """Recommend a strategy without changing the caller's active execution."""
    recommended_strategy = choose_strategy(request)
    return {
        "decision_id": str(uuid4()),
        "active_strategy": request.active_strategy,
        "recommended_strategy": recommended_strategy,
        "disagrees_with_active_strategy": recommended_strategy != request.active_strategy,
        "mode": "shadow",
        "next_step": "Execute your active strategy, then POST its content-free outcome to /telemetry/outcomes.",
        "note": "A shadow recommendation does not alter user traffic or prove a performance improvement.",
    }


@app.post("/telemetry/outcomes", status_code=201)
def record_outcome(request: OutcomeRequest):
    """Record the observed result of an execution for later policy evaluation."""
    event = TelemetryEvent(**request.model_dump())
    telemetry_store.log(event)
    return {
        "recorded": True,
        "workload_id": event.workload_id,
        "decision_id": event.decision_id,
        "timestamp": event.timestamp,
        "privacy": "No prompt or generated output was accepted or stored.",
    }


@app.get("/insights")
def insights():
    """Summarize observed decisions and outcomes for an enterprise reviewer."""
    return summarize_events(telemetry_store.load())
