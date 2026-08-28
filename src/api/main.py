from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Enterprise AI Workload Intelligence",
    description="Production-style API for workload-aware AI routing.",
    version="1.0.0",
)


class RouteRequest(BaseModel):
    task_type: str
    sensitivity: str
    risk_level: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/route")
def route_workload(request: RouteRequest):
    task_type = request.task_type.lower()
    sensitivity = request.sensitivity.lower()
    risk_level = request.risk_level.lower()

    if sensitivity == "high" or risk_level == "high":
        strategy = "direct_frontier"
    elif task_type in {"technical_reasoning", "compliance", "retrieval"}:
        strategy = "verified_cascade"
    else:
        strategy = "direct_small"

    return {
        "task_type": request.task_type,
        "sensitivity": request.sensitivity,
        "risk_level": request.risk_level,
        "recommended_strategy": strategy,
        "note": "Routing policy exposed through a production-style API. Core benchmark outcomes remain simulation-based.",
    }