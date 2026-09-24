"""Content-light audit storage for routing policy release evaluations."""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class RoutingReleaseRecord:
    release_id: str
    created_at: str
    baseline_policy: str
    candidate_policy: str
    evaluated_events: int
    release_ready: bool
    regressions: list[str]
    improvements: list[str]
    unchanged: list[str]
    baseline: dict[str, float]
    candidate: dict[str, float]
    deltas: dict[str, float]
    note: str | None
    evidence: str


class RoutingReleaseStore:
    """Append-only local audit store that avoids retaining outcome-level rows."""

    def __init__(self, path: str = "data/routing_release_reports/decisions.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, report: dict, note: str | None = None) -> dict:
        record = RoutingReleaseRecord(
            release_id=str(uuid4()),
            created_at=datetime.now(UTC).isoformat(),
            baseline_policy=report["baseline_policy"],
            candidate_policy=report["candidate_policy"],
            evaluated_events=report["evaluated_events"],
            release_ready=report["release_ready"],
            regressions=report["regressions"],
            improvements=report["improvements"],
            unchanged=report["unchanged"],
            baseline=report["baseline"],
            candidate=report["candidate"],
            deltas=report["deltas"],
            note=note,
            evidence=report["evidence"],
        )
        serialized = asdict(record)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(serialized) + "\n")
        return serialized

    def recent(self, limit: int = 20) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as file:
            records = [json.loads(line) for line in file if line.strip()]
        return list(reversed(records[-limit:]))
