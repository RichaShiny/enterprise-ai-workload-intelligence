import os
from collections import Counter
from statistics import mean
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.execution.strategy_selector import StrategySelector
from src.telemetry.estimator import TelemetryEstimator
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


def select_recommendation(
    request: RouteRequest,
    store: TelemetryStore | None = None,
) -> dict:
    """Apply hard risk guardrails, then use evidence when it is sufficient."""
    sensitivity = request.sensitivity.lower()
    risk_level = request.risk_level.lower()

    if sensitivity == "high" or risk_level == "high":
        return {
            "recommended_strategy": "direct_frontier",
            "routing_source": "risk_guardrail",
            "sample_count": 0,
            "match_level": None,
            "observed_success_probability": None,
            "conservative_success_probability": None,
            "expected_latency_ms": None,
            "estimated_cost_usd": None,
            "note": "High-risk or high-sensitivity workloads use the explicit frontier guardrail.",
        }

    selector = StrategySelector(
        estimator=TelemetryEstimator(store or telemetry_store),
    )
    decision = selector.select(
        task_type=request.task_type.lower(),
        complexity=request.complexity.lower(),
        sensitivity=sensitivity,
    )
    return {
        "recommended_strategy": decision.strategy,
        "routing_source": decision.source,
        "sample_count": decision.sample_count,
        "match_level": decision.match_level,
        "observed_success_probability": decision.success_probability,
        "conservative_success_probability": decision.conservative_success_probability,
        "expected_latency_ms": decision.expected_latency_ms,
        "estimated_cost_usd": decision.estimated_cost_usd,
        "note": (
            "Recommendation is based on observed telemetry with confidence-aware constraints."
            if decision.source == "observed_telemetry"
            else "Recommendation uses the cold-start fallback policy until sufficient telemetry exists."
        ),
    }


def choose_strategy(request: RouteRequest) -> str:
    """Compatibility helper for callers that only need the strategy name."""
    return select_recommendation(request)["recommended_strategy"]


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
    recommendation = select_recommendation(request)

    return {
        "task_type": request.task_type,
        "complexity": request.complexity,
        "sensitivity": request.sensitivity,
        "risk_level": request.risk_level,
        **recommendation,
    }


@app.post("/shadow-route")
def shadow_route(request: ShadowRouteRequest):
    """Recommend a strategy without changing the caller's active execution."""
    recommendation = select_recommendation(request)
    recommended_strategy = recommendation["recommended_strategy"]
    return {
        "decision_id": str(uuid4()),
        "active_strategy": request.active_strategy,
        "recommended_strategy": recommended_strategy,
        "disagrees_with_active_strategy": recommended_strategy != request.active_strategy,
        "mode": "shadow",
        "recommendation": recommendation,
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
