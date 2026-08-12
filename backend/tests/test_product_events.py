from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from guancha_api.main import create_app
from guancha_api.product_events import ProductEventSink


def payload(event_name: str = "start_selection") -> dict[str, object]:
    return {
        "event_id": str(uuid4()), "event_name": event_name,
        "anonymous_session_id": str(uuid4()), "occurred_at": datetime.now(timezone.utc).isoformat(),
        "flow_id": str(uuid4()), "metadata": {"candidate_count": 2, "screen": "home"},
    }


def test_client_event_endpoint_is_strict_and_rejects_server_outcomes(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    client = TestClient(create_app(product_event_sink=ProductEventSink(path)), raise_server_exceptions=False)
    accepted = client.post("/api/v1/events", json=payload())
    assert accepted.status_code == 202
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["authority"] == "client" and record["schema_version"] == 1
    assert record["metadata"] == {"candidate_count": 2, "screen": "home"}

    forged = client.post("/api/v1/events", json=payload("analysis_completed"))
    assert forged.status_code == 422
    private = payload()
    private["metadata"] = {"need_text": "private need", "raw_text": "merchant reply"}
    rejected = client.post("/api/v1/events", json=private)
    assert rejected.status_code == 422


def test_event_schema_rejects_free_text_top_level_and_oversized_metadata(tmp_path) -> None:
    client = TestClient(create_app(product_event_sink=ProductEventSink(tmp_path / "events.jsonl")), raise_server_exceptions=False)
    with_need = {**payload(), "need": "private"}
    assert client.post("/api/v1/events", json=with_need).status_code == 422
    oversized = payload(); oversized["metadata"] = {"screen": "x" * 65}
    assert client.post("/api/v1/events", json=oversized).status_code == 422
    unknown_failure = payload(); unknown_failure["metadata"] = {"failure_category": "MADE_UP"}
    assert client.post("/api/v1/events", json=unknown_failure).status_code == 422


def test_event_endpoint_accepts_valid_payload_even_when_sink_is_unavailable(tmp_path) -> None:
    directory_path = tmp_path / "directory-instead-of-log"; directory_path.mkdir()
    client = TestClient(create_app(product_event_sink=ProductEventSink(directory_path)), raise_server_exceptions=False)
    assert client.post("/api/v1/events", json=payload("app_open")).status_code == 202


def test_server_event_ids_are_deterministic_and_sink_is_fail_open(tmp_path) -> None:
    path = tmp_path / "events.jsonl"; sink = ProductEventSink(path)
    resource_id, session_id = uuid4(), uuid4()
    assert sink.emit_server(event_name="analysis_completed", resource_id=resource_id, anonymous_session_id=session_id)
    assert sink.emit_server(event_name="analysis_completed", resource_id=resource_id, anonymous_session_id=session_id)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert records[0]["event_id"] == records[1]["event_id"]
    assert all(record["authority"] == "server" for record in records)

    directory_path = tmp_path / "directory-instead-of-log"; directory_path.mkdir()
    failing_sink = ProductEventSink(directory_path)
    assert failing_sink.emit_server(event_name="analysis_failed", resource_id=uuid4(), anonymous_session_id=session_id) is False
