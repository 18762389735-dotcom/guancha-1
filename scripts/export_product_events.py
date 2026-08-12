from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


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
            source = json.loads(line)
            if not isinstance(source, dict) or not isinstance(source.get("event_id"), str):
                continue
            if source["event_id"] in seen:
                continue
            seen.add(source["event_id"])
            metadata = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
            records.append({key: source.get(key, metadata.get(key, "")) for key in COLUMNS})
        except (json.JSONDecodeError, TypeError):
            continue
    return sorted(records, key=lambda row: (str(row.get("occurred_at", "")), str(row["event_id"])))


def export(source: Path, destination: Path) -> int:
    rows = read_events(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export allowlisted Guancha product events to CSV.")
    parser.add_argument("source", type=Path); parser.add_argument("destination", type=Path)
    args = parser.parse_args(); count = export(args.source, args.destination)
    print(f"exported_events={count}"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
