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

    def record_trace(self, trace: dict) -> None:
        """Persist one complete workload-to-outcome trace in a single transaction."""
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO workloads VALUES (?, ?, ?, ?, ?)",
                (trace["workload_id"], trace["task_type"], trace["complexity"], trace["sensitivity"], trace["workload_created_at"]),
            )
            connection.execute(
                "INSERT INTO route_decisions VALUES (?, ?, ?, ?, ?, ?)",
                (trace["decision_id"], trace["workload_id"], trace["policy_name"], trace["execution_path"], trace["routing_source"], trace["decided_at"]),
            )
            connection.execute(
                "INSERT INTO executions VALUES (?, ?, ?, ?, ?)",
                (trace["execution_id"], trace["decision_id"], trace.get("worker_profile"), trace["model_name"], trace["started_at"]),
            )
            connection.execute(
                "INSERT INTO outcomes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (trace["outcome_id"], trace["execution_id"], trace.get("success"), trace["latency_ms"], trace.get("estimated_cost_usd"), trace.get("total_tokens"), trace.get("verification_passed"), trace["recorded_at"]),
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

    def execution_path_summary(self) -> list[dict]:
        """Return a compact relational aggregate grouped by chosen execution path."""
        with self._connect() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("""
                SELECT d.execution_path,
                       COUNT(DISTINCT w.workload_id) AS workloads,
                       COUNT(o.outcome_id) AS outcomes_recorded,
                       AVG(o.success) AS success_rate,
                       AVG(o.latency_ms) AS average_latency_ms,
                       SUM(o.estimated_cost_usd) AS total_cost_usd,
                       AVG(o.total_tokens) AS average_total_tokens
                FROM route_decisions d
                JOIN workloads w ON w.workload_id = d.workload_id
                JOIN executions e ON e.decision_id = d.decision_id
                LEFT JOIN outcomes o ON o.execution_id = e.execution_id
                GROUP BY d.execution_path
                ORDER BY d.execution_path
            """).fetchall()
        return [dict(row) for row in rows]
