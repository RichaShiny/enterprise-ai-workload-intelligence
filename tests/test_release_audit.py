from src.evaluation.release_audit import RoutingReleaseStore


def test_routing_release_store_records_aggregate_report_without_outcome_rows(tmp_path):
    store = RoutingReleaseStore(str(tmp_path / "routing-releases.jsonl"))
    record = store.record({
        "baseline_policy": "balanced",
        "candidate_policy": "strict",
        "evaluated_events": 3,
        "release_ready": False,
        "regressions": ["cost_per_event_usd"],
        "improvements": ["quality_score"],
        "unchanged": [],
        "baseline": {"quality_score": 0.8},
        "candidate": {"quality_score": 0.9},
        "deltas": {"quality_score": 0.1},
        "evidence": "Matched counterfactual simulation.",
    }, note="release review")

    assert record["note"] == "release review"
    assert "outcomes" not in record
    assert store.recent() == [record]
