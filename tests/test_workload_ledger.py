import sqlite3

import pytest

from src.storage.workload_ledger import RelationalWorkloadLedger, schema_relationships


def test_relational_ledger_preserves_workload_to_outcome_trace(tmp_path):
    ledger = RelationalWorkloadLedger(str(tmp_path / "ledger.sqlite3"))
    ledger.record_workload("workload-1", "coding", "medium", "low", "2026-01-01T00:00:00Z")
    ledger.record_decision("decision-1", "workload-1", "delegation-guardrail-v1", "efficient_worker", "policy_guardrail", "2026-01-01T00:01:00Z")
    ledger.record_execution("execution-1", "decision-1", "bulk_context_worker", "efficient-model", "2026-01-01T00:02:00Z")
    ledger.record_outcome("outcome-1", "execution-1", True, 120.0, 0.002, 45, True, "2026-01-01T00:03:00Z")

    assert ledger.trace_rows() == [{
        "workload_id": "workload-1", "task_type": "coding", "decision_id": "decision-1",
        "execution_path": "efficient_worker", "execution_id": "execution-1",
        "worker_profile": "bulk_context_worker", "outcome_id": "outcome-1",
        "success": 1, "latency_ms": 120.0, "estimated_cost_usd": 0.002,
    }]


def test_relational_ledger_rejects_orphaned_decisions(tmp_path):
    ledger = RelationalWorkloadLedger(str(tmp_path / "ledger.sqlite3"))

    with pytest.raises(sqlite3.IntegrityError):
        ledger.record_decision("decision-1", "missing-workload", "policy", "primary_route", "guardrail", "2026-01-01T00:00:00Z")


def test_schema_relationships_describe_the_trace_graph():
    graph = schema_relationships()

    assert graph["tables"] == ["workloads", "route_decisions", "executions", "outcomes"]
    assert graph["relationships"][0]["from"] == "route_decisions.workload_id"
