"""Content-light audit trail for policy-change release decisions."""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class PolicyChangeRecord:
    change_id: str
    created_at: str
    passed: bool
    note: str | None
    regressions: list[str]
    improvements: list[str]
    unchanged: list[str]
    baseline: dict[str, float]
    candidate: dict[str, float]
    baseline_snapshot: list[dict]
    candidate_snapshot: list[dict]


class PolicyChangeStore:
    """Append-only local audit store; production should use protected persistence."""

    def __init__(self, path: str = "data/policy_changes/decisions.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, evaluation: dict, note: str | None = None) -> dict:
        record = PolicyChangeRecord(
            change_id=str(uuid4()),
            created_at=datetime.now(UTC).isoformat(),
            passed=evaluation["passed"],
            note=note,
            regressions=evaluation["regressions"],
            improvements=evaluation["improvements"],
            unchanged=evaluation["unchanged"],
            baseline=evaluation["baseline"],
            candidate=evaluation["candidate"],
            baseline_snapshot=evaluation["baseline_snapshot"],
            candidate_snapshot=evaluation["candidate_snapshot"],
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
