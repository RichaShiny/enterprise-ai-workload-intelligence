"""A minimal relational ledger for traceable AI workload execution."""

import sqlite3
from pathlib import Path


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS workloads (
    workload_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    complexity TEXT NOT NULL,
    sensitivity TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS route_decisions (
    decision_id TEXT PRIMARY KEY,
    workload_id TEXT NOT NULL REFERENCES workloads(workload_id),
    policy_name TEXT NOT NULL,
    execution_path TEXT NOT NULL,
    routing_source TEXT NOT NULL,
    decided_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS executions (
    execution_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL REFERENCES route_decisions(decision_id),
    worker_profile TEXT,
    model_name TEXT NOT NULL,
    started_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outcomes (
    outcome_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL REFERENCES executions(execution_id),
    success INTEGER,
    latency_ms REAL NOT NULL,
    estimated_cost_usd REAL,
    total_tokens INTEGER,
    verification_passed INTEGER,
    recorded_at TEXT NOT NULL
);
"""


def schema_relationships() -> dict:
    """Expose the backend graph without exposing row-level workload data."""
    return {
        "tables": ["workloads", "route_decisions", "executions", "outcomes"],
        "relationships": [
            {"from": "route_decisions.workload_id", "to": "workloads.workload_id", "cardinality": "many-to-one"},
            {"from": "executions.decision_id", "to": "route_decisions.decision_id", "cardinality": "many-to-one"},
            {"from": "outcomes.execution_id", "to": "executions.execution_id", "cardinality": "many-to-one"},
        ],
    }


class RelationalWorkloadLedger:
    """SQLite-backed ledger with foreign-key enforcement and narrow write methods."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA_SQL)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def record_workload(self, workload_id: str, task_type: str, complexity: str, sensitivity: str, created_at: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO workloads VALUES (?, ?, ?, ?, ?)",
                (workload_id, task_type, complexity, sensitivity, created_at),
            )

    def record_decision(self, decision_id: str, workload_id: str, policy_name: str, execution_path: str, routing_source: str, decided_at: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO route_decisions VALUES (?, ?, ?, ?, ?, ?)",
                (decision_id, workload_id, policy_name, execution_path, routing_source, decided_at),
            )

    def record_execution(self, execution_id: str, decision_id: str, worker_profile: str | None, model_name: str, started_at: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO executions VALUES (?, ?, ?, ?, ?)",
                (execution_id, decision_id, worker_profile, model_name, started_at),
            )

    def record_outcome(self, outcome_id: str, execution_id: str, success: bool | None, latency_ms: float, estimated_cost_usd: float | None, total_tokens: int | None, verification_passed: bool | None, recorded_at: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO outcomes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (outcome_id, execution_id, success, latency_ms, estimated_cost_usd, total_tokens, verification_passed, recorded_at),
            )

    def trace_rows(self) -> list[dict]:
        """Return a joined, content-free execution trace for review or evaluation."""
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("""
                SELECT w.workload_id, w.task_type, d.decision_id, d.execution_path,
                       e.execution_id, e.worker_profile, o.outcome_id, o.success,
                       o.latency_ms, o.estimated_cost_usd
                FROM workloads w
                JOIN route_decisions d ON d.workload_id = w.workload_id
                JOIN executions e ON e.decision_id = d.decision_id
                LEFT JOIN outcomes o ON o.execution_id = e.execution_id
                ORDER BY d.decided_at, e.started_at
            """).fetchall()
        return [dict(row) for row in rows]
