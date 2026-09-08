import json
from dataclasses import asdict
from pathlib import Path

from src.telemetry.schema import TelemetryEvent


class TelemetryStore:
    def __init__(self, path: str = "data/telemetry/events.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: TelemetryEvent) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event)) + "\n")

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []

        with self.path.open("r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]