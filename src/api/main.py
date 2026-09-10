import os
from collections import Counter
from pathlib import Path
from statistics import mean
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.execution.strategy_selector import StrategySelector
from src.policy_assistant.audit import PolicyChangeStore
from src.policy_assistant.change_gate import evaluate_policy_change
from src.policy_assistant.catalog import catalog_metadata
from src.policy_assistant.evaluation import evaluate_policy_assistant
from src.policy_assistant.provider import PolicySummaryProvider
from src.policy_assistant.lifecycle import decide_policy_response
from src.policy_assistant.service import APPROVED_POLICIES, ApprovedPolicyAssistant, PolicyDocument
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
    min_success_probability: float = Field(default=0.80, gt=0, le=1)
    max_latency_ms: float = Field(default=6000, gt=0)


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


class PolicyAssistantRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    department: str | None = None
    complexity: str = "medium"
    sensitivity: str = "medium"
    risk_level: str = "medium"


class PolicyDocumentInput(BaseModel):
    document_id: str = Field(min_length=3, max_length=100)
    title: str = Field(min_length=3, max_length=200)
    department: str = Field(min_length=2, max_length=100)
    version: str = Field(min_length=1, max_length=50)
    text: str = Field(min_length=20, max_length=10_000)


class PolicyChangeRequest(BaseModel):
    candidate_policies: list[PolicyDocumentInput] = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=500)


telemetry_store = TelemetryStore(
    os.getenv("TELEMETRY_PATH", "data/telemetry/events.jsonl")
)
semantic_reranking_enabled = os.getenv("POLICY_SEMANTIC_RERANKING_ENABLED", "false").lower() == "true"


def build_policy_assistant() -> ApprovedPolicyAssistant:
    """Avoid loading the embedding runtime unless semantic reranking is enabled."""
    if not semantic_reranking_enabled:
        return ApprovedPolicyAssistant()
    from src.retrieval.ranker import SemanticReranker
    return ApprovedPolicyAssistant(semantic_reranker=SemanticReranker())


policy_assistant = build_policy_assistant()
policy_summary_provider = PolicySummaryProvider()
policy_change_store = PolicyChangeStore(
    os.getenv("POLICY_CHANGE_PATH", "data/policy_changes/decisions.jsonl")
)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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
        min_success_probability=request.min_success_probability,
        max_latency_ms=request.max_latency_ms,
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
        "policy": {
            "min_success_probability": request.min_success_probability,
            "max_latency_ms": request.max_latency_ms,
        },
        "candidates": decision.candidates,
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
    """Serve the public operator console; machine clients can use the documented API routes."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/console", include_in_schema=False)
def console():
    """Serve the operator interface separately from the machine API root."""
    return FileResponse(STATIC_DIR / "index.html")

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


@app.get("/policy-assistant/evaluation")
def policy_assistant_evaluation():
    """Run the fixed, fictional policy benchmark for the operator console."""
    return evaluate_policy_assistant(policy_assistant)


@app.get("/policy-assistant/catalog")
def policy_assistant_catalog():
    """Return safe metadata for the reviewed policy release currently in use."""
    return {
        **catalog_metadata(),
        "reranking": "semantic" if semantic_reranking_enabled else "lexical",
        "privacy": "Catalog metadata excludes policy text. Production sources must be access-controlled.",
    }


@app.get("/policy-assistant/provider-status")
def policy_assistant_provider_status():
    """Expose safe configuration readiness without disclosing any secret."""
    return {
        **policy_summary_provider.status(),
        "privacy": (
            "A provider receives a submitted question and selected approved-policy excerpts "
            "only after summaries are explicitly enabled. This service stores neither."
        ),
    }


@app.post("/policy-assistant/change-gate")
def policy_assistant_change_gate(request: PolicyChangeRequest):
    """Compare a proposed policy revision and retain a content-light decision record."""
    candidate_policies = tuple(PolicyDocument(**item.model_dump()) for item in request.candidate_policies)
    evaluation = evaluate_policy_change(candidate_policies, baseline_policies=APPROVED_POLICIES)
    audit_record = policy_change_store.record(evaluation, note=request.note)
    return {
        **evaluation,
        "audit": {
            "change_id": audit_record["change_id"],
            "created_at": audit_record["created_at"],
            "note": audit_record["note"],
        },
    }


@app.get("/policy-assistant/change-history")
def policy_assistant_change_history(limit: int = 20):
    """Return recent policy release-gate outcomes without policy body text."""
    safe_limit = min(max(limit, 1), 100)
    return {
        "records": policy_change_store.recent(limit=safe_limit),
        "privacy": "Records contain metrics and policy metadata, not policy document text or user questions.",
        "scope": "Demonstration audit trail. Production requires authenticated authors and protected, durable storage.",
    }


@app.post("/policy-assistant")
def answer_policy_question(request: PolicyAssistantRequest):
    """Retrieve approved evidence and pair it with a reviewable route decision."""
    policy_result = policy_assistant.answer(
        question=request.question,
        department=request.department,
    )
    model_summary = (
        policy_summary_provider.summarize(request.question, policy_result["evidence"])
        if policy_result["grounded"]
        else {
            "status": "not_requested",
            "reason": "No provider summary is requested when approved-policy retrieval abstains.",
        }
    )
    routing = select_recommendation(RouteRequest(
        task_type="retrieval",
        complexity=request.complexity,
        sensitivity=request.sensitivity,
        risk_level=request.risk_level,
    ))
    execution = decide_policy_response(policy_result, model_summary, routing)
    return {
        "question": request.question,
        "routing": routing,
        "policy_result": policy_result,
        "model_summary": model_summary,
        "execution": execution,
        "privacy": (
            "This service stores no question history. When provider summaries are disabled, only "
            "deterministic approved-policy evidence is returned. When enabled, the submitted question "
            "and selected approved-policy excerpts are sent to the configured provider for a non-stored summary."
        ),
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
