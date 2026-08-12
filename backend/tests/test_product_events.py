from __future__ import annotations

import json
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from guancha_api.main import create_app
from guancha_api.product_events import ProductEventSink
from guancha_api.application.decision_service import SessionDecisionService
from guancha_api.application.merchant_reply_service import MerchantReplyService
from guancha_api.providers.merchant_reply import FakeMerchantReplyReasoningProvider


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


def test_event_endpoint_is_fail_open_even_when_sink_raises() -> None:
    class ThrowingSink:
        def emit_client(self, event):
            raise RuntimeError("telemetry unavailable")

        def emit_server(self, **kwargs):
            raise RuntimeError("telemetry unavailable")

    client = TestClient(create_app(product_event_sink=ThrowingSink()), raise_server_exceptions=False)
    assert client.post("/api/v1/events", json=payload("app_open")).status_code == 202


def test_allowed_metadata_fields_cannot_smuggle_sensitive_free_text(tmp_path) -> None:
    client = TestClient(create_app(product_event_sink=ProductEventSink(tmp_path / "events.jsonl")), raise_server_exceptions=False)
    for field, value in {
        "screen": "private Need text", "source": "C:/private/path", "question_field": "merchant reply",
        "action_bucket": "=HYPERLINK", "processing_mode": "data:image/png;base64,abc",
        "onboarding_status": "person@example.com",
    }.items():
        event = payload(); event["metadata"] = {field: value}
        assert client.post("/api/v1/events", json=event).status_code == 422


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
    assert sink.emit_server(event_name="analysis_failed", resource_id=uuid4(), anonymous_session_id=session_id, metadata={"raw_text": "private"}) is False
    assert sink.emit_server(event_name="analysis_failed", resource_id=uuid4(), anonymous_session_id=session_id, stage="private/path") is False
    assert sink.emit_server(event_name="analysis_failed", resource_id=uuid4(), anonymous_session_id=session_id, error_category="person@example.com") is False


def test_throwing_sink_cannot_turn_completed_decision_or_parsed_reply_into_failure() -> None:
    class ThrowingSink:
        def emit_server(self, **kwargs):
            raise RuntimeError("telemetry unavailable")

    class DecisionRepository:
        completed = False

        async def claim_job(self, *, job_id): return True
        async def complete_session_decision_job(self, **kwargs): self.completed = True
        async def fail_session_decision_job(self, **kwargs): raise AssertionError("completed decision was marked failed")

    decision_repository = DecisionRepository()
    asyncio.run(SessionDecisionService(decision_repository, ThrowingSink()).run(
        job_id=uuid4(), session_id=uuid4(), client_id=uuid4(), fingerprint="safe",
        need_snapshot={}, inputs_snapshot=[], analytics_session_id=uuid4(),
    ))
    assert decision_repository.completed is True

    reply_id, candidate_id, decision_id = uuid4(), uuid4(), uuid4()
    class ReplyRepository:
        persisted = False

        async def claim_merchant_reply_for_parse(self, **kwargs):
            return ({"field_key": "sample_available", "raw_text": "提供", "candidate_id": candidate_id, "decision_version_id": decision_id}, ())
        async def persist_merchant_reply_parse(self, **kwargs): self.persisted = True
        async def fail_merchant_reply_parse(self, **kwargs): raise AssertionError("persisted reply was marked failed")

    reply_repository = ReplyRepository()
    asyncio.run(MerchantReplyService(reply_repository, FakeMerchantReplyReasoningProvider(), ThrowingSink()).parse(
        reply_id=reply_id, client_id=uuid4(), analytics_session_id=uuid4(),
    ))
    assert reply_repository.persisted is True


def test_replayed_analysis_rejudge_and_reply_do_not_emit_started_or_submitted() -> None:
    class RecordingSink:
        events = []
        def emit_server(self, **kwargs): self.events.append(kwargs); return True

    sink = RecordingSink(); session_id, client_id, reply_id = uuid4(), uuid4(), uuid4()
    job = SimpleNamespace(id=uuid4(), processing_mode=None)
    class DecisionReplayRepository:
        async def decision_inputs_for_session(self, **kwargs): return ({"need": {}, "recent_preference_evidence": []}, [])
        async def create_session_decision_job(self, **kwargs): return job, False

    asyncio.run(SessionDecisionService(DecisionReplayRepository(), sink).analyze(
        session_id=session_id, client_id=client_id, idempotency_key=uuid4(), task_runner=SimpleNamespace(), analytics_session_id=uuid4(),
    ))

    now = datetime.now(timezone.utc)
    reply_row = {"id": reply_id, "selection_session_id": session_id, "decision_version_id": uuid4(), "followup_question_id": uuid4(), "candidate_id": uuid4(), "raw_text": "server business text", "status": "submitted", "processing_status": "queued", "parse_status": None, "created_at": now}
    class ReplyReplayRepository:
        async def create_or_replay_merchant_reply(self, **kwargs): return reply_row, False
        async def aggregate_rejudge_anchor(self, **kwargs): return reply_id
        async def create_merchant_rejudgement_job(self, **kwargs): return job, False

    service = MerchantReplyService(ReplyReplayRepository(), event_sink=sink)
    from guancha_api.schemas.contracts import CreateMerchantReplyRequest
    request = CreateMerchantReplyRequest(decision_version_id=reply_row["decision_version_id"], followup_question_id=reply_row["followup_question_id"], raw_text="server business text")
    asyncio.run(service.submit(session_id=session_id, client_id=client_id, idempotency_key=uuid4(), request=request, analytics_session_id=uuid4()))
    asyncio.run(service.rejudge(session_id=session_id, client_id=client_id, idempotency_key=uuid4(), task_runner=SimpleNamespace(), analytics_session_id=uuid4()))
    assert sink.events == []
