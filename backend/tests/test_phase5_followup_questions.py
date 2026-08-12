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
from guancha_api.domain.tieguanyin.questioning import simulate_decision_branch
from guancha_api.domain.tieguanyin.rules import load_approved_rules
from guancha_api.infrastructure.storage.memory import InMemoryTemporaryPrivateStorage
from guancha_api.main import create_app
from guancha_api.providers.fake import FakeProvider
from guancha_api.providers.reasoning import FakeReasoningProvider
from guancha_api.repositories.postgres import PostgresPhase2Repository


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
    buffer = BytesIO(); Image.new("RGB", (640, 480), "orange").save(buffer, "PNG"); return buffer.getvalue()


def _provider() -> FakeProvider:
    return FakeProvider(extraction_response={"product_name":"tea","tea_category":"oolong","tea_subtype":"tieguanyin","origin":None,"roast_or_style":None,"aroma_claims":[],"taste_claims":[],"season":None,"year_or_batch":None,"grade":None,"weight":None,"price":None,"brew_claims":[],"risk_flags":[],"evidence":[{"field_name":"tea_type","raw_text":"铁观音","normalized_value":"tieguanyin","model_confidence":1,"information_status":"explicit","source_type":"product-claim","verification_status":"unverified","source_location":"title","evidence_strength":"high"}]})


async def _decision(client: httpx.AsyncClient, headers: dict[str, str], runner: ManualTaskRunner) -> tuple[str, str]:
    session = await client.post("/api/v1/selection-sessions", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"need":{"taste_text":"清香"}})
    candidate = await client.post(f"/api/v1/selection-sessions/{session.json()['id']}/candidates", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"display_label":"B"})
    image = await client.post(f"/api/v1/candidates/{candidate.json()['id']}/images", headers={**headers, "Idempotency-Key": str(uuid4())}, files={"file":("tea.png", _image(), "image/png")})
    assert image.status_code == 201
    assert await runner.drain() == 1
    job = await client.post(f"/api/v1/selection-sessions/{session.json()['id']}/analyze", headers={**headers, "Idempotency-Key": str(uuid4())})
    assert job.status_code == 201
    assert await runner.drain() == 1
    decision = await client.get(f"/api/v1/selection-sessions/{session.json()['id']}/current-decision", headers=headers)
    return session.json()["id"], decision.json()["id"]


async def test_current_decision_generates_and_reads_deduplicated_questions(repository: PostgresPhase2Repository) -> None:
    runner = ManualTaskRunner(); app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=_provider(), reasoning_provider=FakeReasoningProvider())
    headers = {"X-Client-Id": str(uuid4())}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        _session_id, version_id = await _decision(client, headers, runner)
        created = await client.post(f"/api/v1/decision-versions/{version_id}/questions", headers={**headers, "Idempotency-Key": str(uuid4())})
        assert created.status_code == 201, created.text
        assert 1 <= len(created.json()) <= 3
        assert {row["field_key"] for row in created.json()} >= {"roast_level"}
        assert all("value_score" not in row for row in created.json())
        assert all(row["candidate_id"] for row in created.json())
        replay = await client.post(f"/api/v1/decision-versions/{version_id}/questions", headers={**headers, "Idempotency-Key": str(uuid4())})
        assert replay.json() == created.json()
        listed = await client.get(f"/api/v1/decision-versions/{version_id}/questions", headers=headers)
        assert listed.json() == created.json()
        assert await repository.get_question_generation_state(version_id=version_id) == "completed"


async def test_completed_empty_question_generation_is_visible_in_session_snapshot(repository: PostgresPhase2Repository) -> None:
    class EmptyReasoningProvider:
        async def generate_questions(self, candidates):
            return ()

    runner = ManualTaskRunner()
    app = create_app(
        repository=repository,
        task_runner=runner,
        temporary_storage=InMemoryTemporaryPrivateStorage(),
        provider=_provider(),
        reasoning_provider=EmptyReasoningProvider(),
    )
    headers = {"X-Client-Id": str(uuid4())}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session_id, version_id = await _decision(client, headers, runner)
        created = await client.post(
            f"/api/v1/decision-versions/{version_id}/questions",
            headers={**headers, "Idempotency-Key": str(uuid4())},
        )
        assert created.status_code == 201
        assert created.json() == []

        snapshot = await client.get(f"/api/v1/selection-sessions/{session_id}/snapshot", headers=headers)
        assert snapshot.status_code == 200
        assert snapshot.json()["questions"] == []
        assert snapshot.json()["question_decision_version_id"] == version_id
        assert snapshot.json()["question_generation_status"] == "completed"


async def test_stale_decision_and_foreign_client_cannot_use_questions(repository: PostgresPhase2Repository) -> None:
    runner = ManualTaskRunner(); app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=_provider())
    headers = {"X-Client-Id": str(uuid4())}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session_id, version_id = await _decision(client, headers, runner)
        assert (await client.get(f"/api/v1/decision-versions/{version_id}/questions", headers={"X-Client-Id":str(uuid4())})).status_code == 403
        await client.patch(f"/api/v1/selection-sessions/{session_id}", headers=headers, json={"need":{"taste_text":"浓香"}})
        stale = await client.post(f"/api/v1/decision-versions/{version_id}/questions", headers={**headers, "Idempotency-Key": str(uuid4())})
        assert stale.status_code == 409
        assert stale.json()["error"]["code"] == "decision_stale"


async def test_reasoning_provider_failure_preserves_decision_and_writes_no_question(repository: PostgresPhase2Repository) -> None:
    class FailingReasoningProvider:
        async def generate_questions(self, candidates):
            raise RuntimeError("provider failed")

    runner = ManualTaskRunner(); app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=_provider(), reasoning_provider=FailingReasoningProvider())
    headers = {"X-Client-Id": str(uuid4())}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        _session_id, version_id = await _decision(client, headers, runner)
        failed = await client.post(f"/api/v1/decision-versions/{version_id}/questions", headers={**headers, "Idempotency-Key": str(uuid4())})
        assert failed.status_code == 503
        assert failed.json()["error"]["code"] == "ai_provider_error"
        assert await repository.get_question_generation_state(version_id=version_id) == "failed"
        assert (await client.get(f"/api/v1/decision-versions/{version_id}", headers=headers)).status_code == 200
        async with repository._connection.cursor() as cursor:  # assert no partial question rows
            await cursor.execute("select count(*) as count from followup_questions where decision_version_id=%s", (version_id,))
            assert (await cursor.fetchone())["count"] == 0


async def test_reasoning_provider_can_only_select_precomputed_candidates(repository: PostgresPhase2Repository) -> None:
    class AlteringReasoningProvider:
        async def generate_questions(self, candidates):
            first = candidates[0]
            return (first.__class__(first.candidate_id, first.field_key, "invented fact", "invented reason", (), ("invented",), 0, 0, {}), first)

    runner = ManualTaskRunner(); app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=_provider(), reasoning_provider=AlteringReasoningProvider())
    headers = {"X-Client-Id": str(uuid4())}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        _session_id, version_id = await _decision(client, headers, runner)
        response = await client.post(f"/api/v1/decision-versions/{version_id}/questions", headers={**headers, "Idempotency-Key": str(uuid4())})
        assert response.status_code == 201
        assert len(response.json()) <= 3
        assert all("invented" not in row["question_text"] and "invented" not in row["reason"] for row in response.json())
        assert len({(row["candidate_id"], row["field_key"]) for row in response.json()}) == len(response.json())


def test_counterfactual_branch_is_side_effect_free_and_assigns_impact_levels() -> None:
    candidate_id = uuid4(); version_id = uuid4()
    inputs = [{"candidate_id": candidate_id, "extraction_version_id": version_id, "evidence":[{"field_name":"tea_type","normalized_value":"tieguanyin","information_status":"explicit"},{"field_name":"aroma_style","normalized_value":"qingxiang","information_status":"explicit"},{"field_name":"season","normalized_value":"spring","information_status":"explicit"}]}]
    original = [{"candidate_id": candidate_id, "action_bucket":"ask-before-buying", "overall_order":1, "risk_flags":["焙火未知"], "reasons":["焙火未说明"]}]
    before = repr(inputs)
    impact = simulate_decision_branch(need={"taste_text":"清香"}, inputs=inputs, original_decisions=original, target_candidate_id=candidate_id, field_key="roast_level", assumed_value="light", rules=load_approved_rules())
    assert repr(inputs) == before
    assert impact.impact_level in {0, 1, 2, 3, 4}
