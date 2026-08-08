from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
import pytest
import pytest_asyncio
from PIL import Image
from psycopg.rows import dict_row

from guancha_api.application.task_runners import ManualTaskRunner
from guancha_api.infrastructure.storage.memory import InMemoryTemporaryPrivateStorage
from guancha_api.main import create_app
from guancha_api.providers.fake import FakeProvider
from guancha_api.providers.merchant_reply import MerchantReplyParse
from guancha_api.repositories.postgres import PostgresPhase2Repository


DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def repository() -> PostgresPhase2Repository:
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is required")
    connection = await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row)
    migrations = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
    async with connection.cursor() as cursor:
        await cursor.execute("drop schema public cascade")
        await cursor.execute("create schema public")
        await cursor.execute("\n".join(path.read_text(encoding="utf-8") for path in sorted(migrations.glob("*.sql"))))
    await connection.commit()
    try:
        yield PostgresPhase2Repository(connection)
    finally:
        await connection.close()


class AnsweringReplyProvider:
    async def parse_merchant_reply(self, *, field_key, raw_text, product_evidence):
        return MerchantReplyParse(
            reply_status="answered", answered_fields=(field_key,),
            claims=({"field_key": field_key, "raw_text": raw_text, "normalized_value": "light"},),
            unresolved_fields=(), conflicts=(), coverage=1, ambiguity=0, should_rejudge=True,
        )


def _image() -> bytes:
    output = BytesIO()
    Image.new("RGB", (640, 480), "orange").save(output, "PNG")
    return output.getvalue()


def _vision() -> FakeProvider:
    return FakeProvider(extraction_response={
        "product_name": "tea", "tea_category": "oolong", "tea_subtype": "tieguanyin", "origin": None,
        "roast_or_style": None, "aroma_claims": [], "taste_claims": [], "season": None, "year_or_batch": None,
        "grade": None, "weight": None, "price": None, "brew_claims": [], "risk_flags": [],
        "evidence": [{"field_name": "tea_type", "raw_text": "tieguanyin", "normalized_value": "tieguanyin",
                      "model_confidence": 1, "information_status": "explicit", "source_type": "product-claim",
                      "verification_status": "unverified", "source_location": "title", "evidence_strength": "high"}],
    })


async def _current_decision(client: httpx.AsyncClient, headers: dict[str, str], runner: ManualTaskRunner) -> tuple[str, str]:
    session = await client.post("/api/v1/selection-sessions", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"need": {"taste_text": "light"}})
    candidate = await client.post(f"/api/v1/selection-sessions/{session.json()['id']}/candidates", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"display_label": "A"})
    upload = await client.post(f"/api/v1/candidates/{candidate.json()['id']}/images", headers={**headers, "Idempotency-Key": str(uuid4())}, files={"file": ("tea.png", _image(), "image/png")})
    assert upload.status_code == 201
    assert await runner.drain() == 1
    decision_job = await client.post(f"/api/v1/selection-sessions/{session.json()['id']}/analyze", headers={**headers, "Idempotency-Key": str(uuid4())})
    assert decision_job.status_code == 201
    assert await runner.drain() == 1
    current = await client.get(f"/api/v1/selection-sessions/{session.json()['id']}/current-decision", headers=headers)
    return session.json()["id"], current.json()["id"]


async def test_merchant_reply_rejudgement_creates_append_only_decision_v2(repository: PostgresPhase2Repository) -> None:
    runner = ManualTaskRunner()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=_vision(), merchant_reply_provider=AnsweringReplyProvider())
    headers = {"X-Client-Id": str(uuid4())}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session_id, v1 = await _current_decision(client, headers, runner)
        questions = await client.post(f"/api/v1/decision-versions/{v1}/questions", headers={**headers, "Idempotency-Key": str(uuid4())})
        assert questions.status_code == 201
        question = questions.json()[0]
        reply_key = str(uuid4())
        reply = await client.post(f"/api/v1/selection-sessions/{session_id}/merchant-replies", headers={**headers, "Idempotency-Key": reply_key}, json={"decision_version_id": v1, "followup_question_id": question["id"], "raw_text": "light roast"})
        assert reply.status_code == 201, reply.text
        replay = await client.post(f"/api/v1/selection-sessions/{session_id}/merchant-replies", headers={**headers, "Idempotency-Key": reply_key}, json={"decision_version_id": v1, "followup_question_id": question["id"], "raw_text": "light roast"})
        assert replay.json()["id"] == reply.json()["id"]
        for extra_question in questions.json()[1:]:
            extra = await client.post(f"/api/v1/selection-sessions/{session_id}/merchant-replies", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"decision_version_id": v1, "followup_question_id": extra_question["id"], "raw_text": "light roast"})
            assert extra.status_code == 201
        job = await client.post(f"/api/v1/selection-sessions/{session_id}/rejudge", headers={**headers, "Idempotency-Key": str(uuid4())}, json={})
        assert job.status_code == 201, job.text
        assert await runner.drain() == 1
        completed = await client.get(f"/api/v1/jobs/{job.json()['id']}", headers=headers)
        assert completed.json()["status"] == "completed"
        v2 = completed.json()["decision_version_id"]
        assert v2 and v2 != v1
        assert completed.json()["decision_delta_id"]
        current = await client.get(f"/api/v1/selection-sessions/{session_id}/current-decision", headers=headers)
        assert current.json()["id"] == v2
        async with repository._connection.cursor() as cursor:
            await cursor.execute("select source_type,verification_status from merchant_claims where merchant_reply_id=%s", (reply.json()["id"],))
            assert await cursor.fetchone() == {"source_type": "merchant-claim", "verification_status": "unverified"}
            await cursor.execute("select count(*) as count from decision_deltas where merchant_reply_id=%s", (reply.json()["id"],))
            assert (await cursor.fetchone())["count"] == 1
            await cursor.execute("select id from decision_deltas where merchant_reply_id=%s", (reply.json()["id"],))
            delta_id = (await cursor.fetchone())["id"]
        assert completed.json()["decision_delta_id"] == str(delta_id)
        delta = await client.get(f"/api/v1/decision-deltas/{delta_id}", headers=headers)
        assert delta.status_code == 200
        assert delta.json()["old_decision_version_id"] == v1
        assert delta.json()["new_decision_version_id"] == v2


async def test_rejudge_aggregates_all_saved_replies_into_one_delta(repository: PostgresPhase2Repository) -> None:
    class MultiFieldProvider:
        async def parse_merchant_reply(self, *, field_key, raw_text, **_kwargs):
            return MerchantReplyParse(
                reply_status="answered", answered_fields=(field_key,),
                claims=({"field_key": field_key, "raw_text": raw_text, "normalized_value": raw_text},),
                unresolved_fields=(), conflicts=(), coverage=1, ambiguity=0, should_rejudge=True,
            )

    runner = ManualTaskRunner()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=_vision(), merchant_reply_provider=MultiFieldProvider())
    headers = {"X-Client-Id": str(uuid4())}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session_id, v1 = await _current_decision(client, headers, runner)
        questions = (await client.post(f"/api/v1/decision-versions/{v1}/questions", headers={**headers, "Idempotency-Key": str(uuid4())})).json()
        assert len(questions) >= 2
        reply_ids = []
        for question in questions:
            response = await client.post(
                f"/api/v1/selection-sessions/{session_id}/merchant-replies",
                headers={**headers, "Idempotency-Key": str(uuid4())},
                json={"decision_version_id": v1, "followup_question_id": question["id"], "raw_text": f"answer {question['field_key']}"},
            )
            assert response.status_code == 201
            reply_ids.append(response.json()["id"])
        job = await client.post(
            f"/api/v1/selection-sessions/{session_id}/rejudge",
            headers={**headers, "Idempotency-Key": str(uuid4())}, json={},
        )
        assert job.status_code == 201
        assert await runner.drain() == 1
        completed = (await client.get(f"/api/v1/jobs/{job.json()['id']}", headers=headers)).json()
        assert completed["status"] == "completed"
        delta = (await client.get(f"/api/v1/decision-deltas/{completed['decision_delta_id']}", headers=headers)).json()
        assert set(delta["merchant_reply_ids"]) == set(reply_ids)
        assert delta["merchant_reply_id"] in reply_ids


async def test_foreign_client_cannot_read_reply_or_rejudge(repository: PostgresPhase2Repository) -> None:
    runner = ManualTaskRunner()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=_vision(), merchant_reply_provider=AnsweringReplyProvider())
    headers = {"X-Client-Id": str(uuid4())}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session_id, v1 = await _current_decision(client, headers, runner)
        questions = await client.post(f"/api/v1/decision-versions/{v1}/questions", headers={**headers, "Idempotency-Key": str(uuid4())})
        reply = await client.post(f"/api/v1/selection-sessions/{session_id}/merchant-replies", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"decision_version_id": v1, "followup_question_id": questions.json()[0]["id"], "raw_text": "light roast"})
        for extra_question in questions.json()[1:]:
            extra = await client.post(f"/api/v1/selection-sessions/{session_id}/merchant-replies", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"decision_version_id": v1, "followup_question_id": extra_question["id"], "raw_text": "light roast"})
            assert extra.status_code == 201
        foreign = {"X-Client-Id": str(uuid4()), "Idempotency-Key": str(uuid4())}
        assert (await client.get(f"/api/v1/merchant-replies/{reply.json()['id']}", headers=foreign)).status_code == 403
        assert (await client.post(f"/api/v1/selection-sessions/{session_id}/rejudge", headers=foreign, json={})).status_code == 403


async def test_failed_parser_preserves_the_current_decision_without_partial_rows(repository: PostgresPhase2Repository) -> None:
    class FailingReplyProvider:
        async def parse_merchant_reply(self, **_kwargs):
            raise RuntimeError("synthetic parser failure")

    runner = ManualTaskRunner()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=_vision(), merchant_reply_provider=FailingReplyProvider())
    headers = {"X-Client-Id": str(uuid4())}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session_id, v1 = await _current_decision(client, headers, runner)
        questions = await client.post(f"/api/v1/decision-versions/{v1}/questions", headers={**headers, "Idempotency-Key": str(uuid4())})
        reply = await client.post(f"/api/v1/selection-sessions/{session_id}/merchant-replies", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"decision_version_id": v1, "followup_question_id": questions.json()[0]["id"], "raw_text": "light roast"})
        for extra_question in questions.json()[1:]:
            extra = await client.post(f"/api/v1/selection-sessions/{session_id}/merchant-replies", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"decision_version_id": v1, "followup_question_id": extra_question["id"], "raw_text": "light roast"})
            assert extra.status_code == 201
        job = await client.post(f"/api/v1/selection-sessions/{session_id}/rejudge", headers={**headers, "Idempotency-Key": str(uuid4())}, json={})
        with pytest.raises(RuntimeError):
            await runner.drain()
        terminal = await client.get(f"/api/v1/jobs/{job.json()['id']}", headers=headers)
        assert terminal.json()["status"] == "failed"
        current = await client.get(f"/api/v1/selection-sessions/{session_id}/current-decision", headers=headers)
        assert current.json()["id"] == v1
        async with repository._connection.cursor() as cursor:
            await cursor.execute("select count(*) as count from merchant_claims where merchant_reply_id=%s", (reply.json()["id"],))
            assert (await cursor.fetchone())["count"] == 0
            await cursor.execute("select count(*) as count from decision_deltas where merchant_reply_id=%s", (reply.json()["id"],))
            assert (await cursor.fetchone())["count"] == 0


async def test_evasive_reply_still_produces_a_comparative_decision(repository: PostgresPhase2Repository) -> None:
    class EvasiveReplyProvider:
        async def parse_merchant_reply(self, *, field_key, **_kwargs):
            return MerchantReplyParse("evasive", (), (), (field_key,), (), 0, 1, False)

    runner = ManualTaskRunner()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=_vision(), merchant_reply_provider=EvasiveReplyProvider())
    headers = {"X-Client-Id": str(uuid4())}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session_id, v1 = await _current_decision(client, headers, runner)
        questions = await client.post(f"/api/v1/decision-versions/{v1}/questions", headers={**headers, "Idempotency-Key": str(uuid4())})
        reply = await client.post(f"/api/v1/selection-sessions/{session_id}/merchant-replies", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"decision_version_id": v1, "followup_question_id": questions.json()[0]["id"], "raw_text": "not sure"})
        for extra_question in questions.json()[1:]:
            extra = await client.post(f"/api/v1/selection-sessions/{session_id}/merchant-replies", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"decision_version_id": v1, "followup_question_id": extra_question["id"], "raw_text": "not sure"})
            assert extra.status_code == 201
        job = await client.post(f"/api/v1/selection-sessions/{session_id}/rejudge", headers={**headers, "Idempotency-Key": str(uuid4())}, json={})
        assert await runner.drain() == 1
        completed = await client.get(f"/api/v1/jobs/{job.json()['id']}", headers=headers)
        assert completed.json()["status"] == "completed"
        assert completed.json()["decision_version_id"] != v1
