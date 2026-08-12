from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from guancha_api.product_events import validate_stored_event


COLUMNS = (
    "event_id", "occurred_at", "received_at", "anonymous_session_id", "event_name",
    "authority", "flow_id", "candidate_id", "decision_version_id", "stage",
    "duration_ms", "error_category", "candidate_count", "image_count", "has_budget",
    "has_sensory_need", "question_field", "question_count", "action_bucket",
    "processing_mode", "failure_category", "onboarding_status", "source", "screen",
)


def read_events(path: Path) -> list[dict[str, object]]:
    seen: set[str] = set(); records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            source = validate_stored_event(json.loads(line))
            if source is None:
                continue
            if source["event_id"] in seen:
                continue
            seen.add(source["event_id"])
            metadata = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
            records.append({key: source.get(key, metadata.get(key, "")) for key in COLUMNS})
        except (json.JSONDecodeError, TypeError):
            continue
    return sorted(records, key=lambda row: (str(row.get("occurred_at", "")), str(row["event_id"])))


def _csv_safe(value: object) -> object:
    if not isinstance(value, str):
        return value
    cleaned = value.replace("\r", " ").replace("\n", " ")
    return "'" + cleaned if cleaned.startswith(("=", "+", "-", "@")) else cleaned


def export(source: Path, destination: Path) -> int:
    rows = read_events(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader(); writer.writerows({key: _csv_safe(value) for key, value in row.items()} for row in rows)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export allowlisted Guancha product events to CSV.")
    parser.add_argument("source", type=Path); parser.add_argument("destination", type=Path)
    args = parser.parse_args(); count = export(args.source, args.destination)
    print(f"exported_events={count}"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
