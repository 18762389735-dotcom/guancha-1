from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from export_product_events import _csv_safe, export
from summarize_product_funnel import summarize


def test_export_skips_bad_lines_deduplicates_and_only_emits_allowlisted_columns(tmp_path) -> None:
    source, destination = tmp_path / "events.jsonl", tmp_path / "events.csv"
    base = {"schema_version": 1, "received_at": "2026-01-01T00:00:01+00:00", "authority": "client", "metadata": {}}
    events = [
        {**base, "event_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "occurred_at": "2026-01-02T00:00:00+00:00", "event_name": "start_selection", "anonymous_session_id": "11111111-1111-4111-8111-111111111111", "metadata": {"screen": "result"}},
        {**base, "event_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "occurred_at": "2026-01-01T00:00:00+00:00", "event_name": "start_selection", "anonymous_session_id": "11111111-1111-4111-8111-111111111111", "metadata": {"candidate_count": 2}},
        {**base, "event_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "occurred_at": "2026-01-03T00:00:00+00:00", "event_name": "start_selection", "anonymous_session_id": "22222222-2222-4222-8222-222222222222"},
    ]
    source.write_text("\n".join([json.dumps(events[0]), "bad-json", json.dumps(events[1]), json.dumps(events[2])]), encoding="utf-8")
    assert export(source, destination) == 2
    rows = list(csv.DictReader(destination.open(encoding="utf-8-sig")))
    assert [row["event_id"] for row in rows] == ["aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"]
    assert "private" not in rows[0] and "raw_text" not in rows[0]


def test_funnel_summary_reports_raw_counts_without_percentages(tmp_path) -> None:
    source = tmp_path / "events.jsonl"
    source.write_text("\n".join(json.dumps(row) for row in [
        {"schema_version":1,"event_id":"11111111-1111-4111-8111-111111111111","occurred_at":"2026-01-01T00:00:00+00:00","received_at":"2026-01-01T00:00:01+00:00","event_name":"start_selection","anonymous_session_id":"33333333-3333-4333-8333-333333333333","authority":"client","metadata":{}},
        {"schema_version":1,"event_id":"22222222-2222-4222-8222-222222222222","occurred_at":"2026-01-01T00:00:02+00:00","received_at":"2026-01-01T00:00:03+00:00","event_name":"need_submitted","anonymous_session_id":"33333333-3333-4333-8333-333333333333","authority":"server","metadata":{}},
    ]), encoding="utf-8")
    output = summarize(source)
    assert "event_count=2" in output and "unique_session_count=1" in output
    assert "START=1" in output and "NEED SUBMITTED=1" in output and "%" not in output


def test_export_rejects_unknown_authority_event_pairs_and_sanitizes_csv_formulas(tmp_path) -> None:
    source, destination = tmp_path / "events.jsonl", tmp_path / "events.csv"
    valid = {"schema_version": 1, "event_id": "11111111-1111-4111-8111-111111111111", "event_name": "start_selection", "anonymous_session_id": "22222222-2222-4222-8222-222222222222", "occurred_at": "2026-08-13T00:00:00+00:00", "received_at": "2026-08-13T00:00:01+00:00", "authority": "client", "metadata": {"screen": "home"}}
    wrong_authority = {**valid, "event_id": "33333333-3333-4333-8333-333333333333", "authority": "server"}
    unknown_event = {**valid, "event_id": "44444444-4444-4444-8444-444444444444", "event_name": "made_up"}
    source.write_text("\n".join(json.dumps(row) for row in [wrong_authority, unknown_event, valid]), encoding="utf-8")
    assert export(source, destination) == 1
    assert _csv_safe("=2+2") == "'=2+2"
    assert _csv_safe("+cmd\r\nnext") == "'+cmd  next"


def test_export_rejects_noncanonical_ids_naive_timestamps_and_open_error_values(tmp_path) -> None:
    source, destination = tmp_path / "events.jsonl", tmp_path / "events.csv"
    valid = {"schema_version": 1, "event_id": "11111111-1111-4111-8111-111111111111", "event_name": "start_selection", "anonymous_session_id": "22222222-2222-4222-8222-222222222222", "occurred_at": "2026-08-13T00:00:00+00:00", "received_at": "2026-08-13T00:00:01+00:00", "authority": "client", "metadata": {}}
    rows = [
        {**valid, "event_id": "11111111111141118111111111111111"},
        {**valid, "event_id": "33333333-3333-4333-8333-333333333333", "occurred_at": "2026-08-13T00:00:00"},
        {**valid, "event_id": "44444444-4444-4444-8444-444444444444", "error_category": "private_need_text"},
        valid,
    ]
    source.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    assert export(source, destination) == 1
