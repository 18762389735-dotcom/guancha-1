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
from guancha_api.repositories.postgres import PostgresPhase2Repository
from guancha_api.domain.tieguanyin.decision import evaluate_candidate
from guancha_api.domain.tieguanyin.rules import load_approved_rules
from guancha_api.schemas.contracts import ActionBucket


DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def repository() -> PostgresPhase2Repository:
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is required")
    connection = await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row)
    migration_directory = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
    async with connection.cursor() as cursor:
        await cursor.execute("drop schema public cascade")
        await cursor.execute("create schema public")
        await cursor.execute("\n".join(path.read_text(encoding="utf-8") for path in sorted(migration_directory.glob("*.sql"))))
    await connection.commit()
    try:
        yield PostgresPhase2Repository(connection)
    finally:
        await connection.close()


def _image() -> bytes:
    output = BytesIO(); Image.new("RGB", (640, 480), "green").save(output, "PNG"); return output.getvalue()


def _provider() -> FakeProvider:
    return FakeProvider(extraction_response={"product_name":"A","tea_category":"oolong","tea_subtype":"tieguanyin","origin":None,"roast_or_style":None,"aroma_claims":[],"taste_claims":[],"season":None,"year_or_batch":None,"grade":None,"weight":None,"price":None,"brew_claims":[],"risk_flags":[],"evidence":[{"field_name":"tea_type","raw_text":"铁观音","normalized_value":"tieguanyin","model_confidence":0.9,"information_status":"explicit","source_type":"merchant-claim","verification_status":"system-consistent","source_location":"title","evidence_strength":"high"}]})


async def _prepared_session(client, headers, runner, count: int) -> str:
    session = await client.post("/api/v1/selection-sessions", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"need": {"taste_text": "清香"}})
    assert session.status_code == 201
    for index in range(count):
        candidate = await client.post(f"/api/v1/selection-sessions/{session.json()['id']}/candidates", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"display_label": chr(65 + index)})
        image = await client.post(f"/api/v1/candidates/{candidate.json()['id']}/images", headers={**headers, "Idempotency-Key": str(uuid4())}, files={"file": (f"tea-{index}.png", _image(), "image/png")})
        assert candidate.status_code == image.status_code == 201
    assert await runner.drain() == count
    return session.json()["id"]


async def test_session_decision_job_creates_immutable_current_snapshot(repository: PostgresPhase2Repository) -> None:
    runner = ManualTaskRunner()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=_provider())
    client_id = str(uuid4())
    headers = {"X-Client-Id": client_id}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session = await client.post("/api/v1/selection-sessions", headers={**headers,"Idempotency-Key":str(uuid4())}, json={"need":{"taste_text":"清香"}})
        candidate = await client.post(f"/api/v1/selection-sessions/{session.json()['id']}/candidates", headers={**headers,"Idempotency-Key":str(uuid4())}, json={"display_label":"A"})
        uploaded = await client.post(f"/api/v1/candidates/{candidate.json()['id']}/images", headers={**headers,"Idempotency-Key":str(uuid4())}, files={"file":("tea.png",_image(),"image/png")})
        assert uploaded.status_code == 201
        assert await runner.drain() == 1
        decision_job = await client.post(f"/api/v1/selection-sessions/{session.json()['id']}/analyze", headers={**headers,"Idempotency-Key":str(uuid4())})
        assert decision_job.status_code == 201, decision_job.text
        assert await runner.drain() == 1
        current = await client.get(f"/api/v1/selection-sessions/{session.json()['id']}/current-decision", headers=headers)
        assert current.status_code == 200, current.text
        assert current.json()["candidate_decisions"][0]["action_bucket"] == "insufficient-information"
        version = await client.get(f"/api/v1/decision-versions/{current.json()['id']}", headers=headers)
        assert version.status_code == 200
        foreign = await client.get(f"/api/v1/decision-versions/{current.json()['id']}", headers={"X-Client-Id": str(uuid4())})
        assert foreign.status_code == 403
        changed = await client.post(f"/api/v1/selection-sessions/{session.json()['id']}/candidates", headers={**headers,"Idempotency-Key":str(uuid4())}, json={"display_label":"B"})
        assert changed.status_code == 201
        stale = await client.get(f"/api/v1/selection-sessions/{session.json()['id']}/current-decision", headers=headers)
        assert stale.status_code == 404


async def test_snapshot_exposes_only_the_current_session_decision_job_lineage(repository: PostgresPhase2Repository) -> None:
    runner = ManualTaskRunner()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=_provider())
    headers = {"X-Client-Id": str(uuid4())}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session_id = await _prepared_session(client, headers, runner, 1)
        queued = await client.post(
            f"/api/v1/selection-sessions/{session_id}/analyze",
            headers={**headers, "Idempotency-Key": str(uuid4())},
        )
        snapshot = await client.get(f"/api/v1/selection-sessions/{session_id}/snapshot", headers=headers)
        assert snapshot.json()["session_decision_job"]["id"] == queued.json()["id"]
        assert snapshot.json()["session_decision_job"]["status"] == "queued"
        assert await runner.drain() == 1
        completed = await client.get(f"/api/v1/selection-sessions/{session_id}/snapshot", headers=headers)
        assert completed.json()["session_decision_job"]["status"] == "completed"
        assert completed.json()["session_decision_job"]["decision_version_id"] == completed.json()["current_decision_id"]


async def test_selection_answer_hides_evidence_enums_and_keeps_candidate_scope(repository: PostgresPhase2Repository) -> None:
    runner = ManualTaskRunner()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=_provider())
    headers = {"X-Client-Id": str(uuid4())}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session_id = await _prepared_session(client, headers, runner, 3)
        job = await client.post(f"/api/v1/selection-sessions/{session_id}/analyze", headers={**headers, "Idempotency-Key": str(uuid4())})
        assert job.status_code == 201
        assert await runner.drain() == 1
        answer = await client.get(f"/api/v1/selection-sessions/{session_id}/answer", headers=headers)
        assert answer.status_code == 200
        body = answer.json()
        assert body["answer_version"] == "v2"
        assert len(body["candidates"]) == 3
        assert "merchant-claim" not in str(body)
        assert "system-consistent" not in str(body)
        assert "fixture" not in str(body).lower()
        assert all("source_type" not in item for item in body["candidates"])
        snapshot = await client.get(f"/api/v1/selection-sessions/{session_id}/snapshot", headers=headers)
        assert snapshot.status_code == 200
        assert len(snapshot.json()["candidates"]) == 3
        assert snapshot.json()["current_decision_id"] == body["decision_version_id"]


async def test_need_change_stales_current_decision_and_new_analysis_uses_a_fresh_snapshot(
    repository: PostgresPhase2Repository,
) -> None:
    runner = ManualTaskRunner()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=_provider())
    headers = {"X-Client-Id": str(uuid4())}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session = await client.post(
            "/api/v1/selection-sessions", headers={**headers, "Idempotency-Key": str(uuid4())},
            json={"need": {"taste_text": "fresh"}},
        )
        candidate = await client.post(
            f"/api/v1/selection-sessions/{session.json()['id']}/candidates",
            headers={**headers, "Idempotency-Key": str(uuid4())}, json={"display_label": "A"},
        )
        uploaded = await client.post(
            f"/api/v1/candidates/{candidate.json()['id']}/images",
            headers={**headers, "Idempotency-Key": str(uuid4())}, files={"file": ("tea.png", _image(), "image/png")},
        )
        assert uploaded.status_code == 201
        assert await runner.drain() == 1

        queued = await client.post(
            f"/api/v1/selection-sessions/{session.json()['id']}/analyze",
            headers={**headers, "Idempotency-Key": str(uuid4())},
        )
        assert queued.status_code == 201
        changed = await client.patch(
            f"/api/v1/selection-sessions/{session.json()['id']}", headers=headers,
            json={"need": {"taste_text": "strong", "risk_attitude_text": "explore"}},
        )
        assert changed.status_code == 200
        assert changed.json()["need"]["taste_text"] == "strong"
        assert await runner.drain() == 1
        assert (await client.get(
            f"/api/v1/selection-sessions/{session.json()['id']}/current-decision", headers=headers,
        )).status_code == 404

        fresh = await client.post(
            f"/api/v1/selection-sessions/{session.json()['id']}/analyze",
            headers={**headers, "Idempotency-Key": str(uuid4())},
        )
        assert fresh.status_code == 201
        assert await runner.drain() == 1
        current = await client.get(
            f"/api/v1/selection-sessions/{session.json()['id']}/current-decision", headers=headers,
        )
        assert current.status_code == 200
        assert current.json()["version"] == 2


@pytest.mark.parametrize("count", [3, 5])
async def test_decision_supports_three_and_five_current_candidates(repository: PostgresPhase2Repository, count: int) -> None:
    runner = ManualTaskRunner()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=_provider())
    headers = {"X-Client-Id": str(uuid4())}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session_id = await _prepared_session(client, headers, runner, count)
        key = str(uuid4())
        first = await client.post(f"/api/v1/selection-sessions/{session_id}/analyze", headers={**headers, "Idempotency-Key": key})
        replay = await client.post(f"/api/v1/selection-sessions/{session_id}/analyze", headers={**headers, "Idempotency-Key": key})
        assert first.status_code == replay.status_code == 201
        assert first.json()["id"] == replay.json()["id"]
        assert await runner.drain() == 1
        current = await client.get(f"/api/v1/selection-sessions/{session_id}/current-decision", headers=headers)
        assert current.status_code == 200
        assert len(current.json()["candidate_decisions"]) == count
        assert [item["overall_order"] for item in current.json()["candidate_decisions"]] == list(range(1, count + 1))


@pytest.mark.parametrize(("need", "evidence", "expected"), [
    ({}, [{"field_name":"tea_type","normalized_value":None,"information_status":"unknown"}], ActionBucket.INSUFFICIENT_INFORMATION),
    ({"taste_text":"浓香"}, [{"field_name":"tea_type","normalized_value":"tieguanyin","information_status":"explicit"},{"field_name":"aroma_style","normalized_value":"qingxiang","information_status":"explicit"},{"field_name":"roast_level","normalized_value":"light","information_status":"explicit"},{"field_name":"season","normalized_value":"spring","information_status":"explicit"}], ActionBucket.NOT_RECOMMENDED_NOW),
    ({"taste_text":"清香"}, [{"field_name":"tea_type","normalized_value":"tieguanyin","information_status":"explicit"},{"field_name":"aroma_style","normalized_value":"qingxiang","information_status":"explicit"},{"field_name":"season","normalized_value":"spring","information_status":"explicit"}], ActionBucket.ASK_BEFORE_BUYING),
    ({"risk_attitude_text":"愿意探索"}, [{"field_name":"tea_type","normalized_value":"tieguanyin","information_status":"explicit"},{"field_name":"aroma_style","normalized_value":"qingxiang","information_status":"explicit"},{"field_name":"roast_level","normalized_value":"light","information_status":"explicit"},{"field_name":"season","normalized_value":"spring","information_status":"explicit"},{"field_name":"sample_available","normalized_value":"true","information_status":"explicit"}], ActionBucket.SAMPLE_FIRST),
    ({}, [{"field_name":"tea_type","normalized_value":"tieguanyin","information_status":"explicit"},{"field_name":"aroma_style","normalized_value":"qingxiang","information_status":"explicit"},{"field_name":"roast_level","normalized_value":"light","information_status":"explicit"},{"field_name":"season","normalized_value":"spring","information_status":"explicit"}], ActionBucket.CURRENTLY_SELECTABLE),
])
def test_rule_engine_uses_only_five_frozen_action_buckets(need, evidence, expected) -> None:
    draft = evaluate_candidate(candidate_id=uuid4(), extraction_version_id=uuid4(), need=need, evidence=evidence, rules=load_approved_rules())
    assert draft.action_bucket is expected
