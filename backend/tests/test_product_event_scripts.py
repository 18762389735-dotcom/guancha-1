from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from export_product_events import export
from summarize_product_funnel import summarize


def test_export_skips_bad_lines_deduplicates_and_only_emits_allowlisted_columns(tmp_path) -> None:
    source, destination = tmp_path / "events.jsonl", tmp_path / "events.csv"
    events = [
        {"event_id": "b", "occurred_at": "2026-01-02", "event_name": "analysis_completed", "anonymous_session_id": "s1", "metadata": {"screen": "result", "raw_text": "secret"}, "private": "no"},
        {"event_id": "a", "occurred_at": "2026-01-01", "event_name": "start_selection", "anonymous_session_id": "s1", "metadata": {"candidate_count": 2}},
        {"event_id": "a", "occurred_at": "2026-01-03", "event_name": "start_selection", "anonymous_session_id": "s2"},
    ]
    source.write_text("\n".join([json.dumps(events[0]), "bad-json", json.dumps(events[1]), json.dumps(events[2])]), encoding="utf-8")
    assert export(source, destination) == 2
    rows = list(csv.DictReader(destination.open(encoding="utf-8-sig")))
    assert [row["event_id"] for row in rows] == ["a", "b"]
    assert "private" not in rows[0] and "raw_text" not in rows[0]


def test_funnel_summary_reports_raw_counts_without_percentages(tmp_path) -> None:
    source = tmp_path / "events.jsonl"
    source.write_text("\n".join(json.dumps(row) for row in [
        {"event_id": "1", "occurred_at": "1", "event_name": "start_selection", "anonymous_session_id": "s1"},
        {"event_id": "2", "occurred_at": "2", "event_name": "need_submitted", "anonymous_session_id": "s1"},
    ]), encoding="utf-8")
    output = summarize(source)
    assert "event_count=2" in output and "unique_session_count=1" in output
    assert "START=1" in output and "NEED SUBMITTED=1" in output and "%" not in output
