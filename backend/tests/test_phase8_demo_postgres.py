"""Phase 8 real PostgreSQL provider-failure checks; the provider never uses network."""
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
import pytest
import pytest_asyncio
from PIL import Image
from io import BytesIO
from psycopg.rows import dict_row

from guancha_api.application.task_runners import ManualTaskRunner
from guancha_api.infrastructure.storage.memory import InMemoryTemporaryPrivateStorage
from guancha_api.main import create_app
from guancha_api.providers.fake import ProviderNetworkError
from guancha_api.repositories.postgres import PostgresPhase2Repository
from guancha_api.schemas.contracts import ProcessingMode

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.asyncio


class FailingLiveProvider:
    provider_name = "openai"
    model_identifier = "test-live-model"
    processing_mode = ProcessingMode.OPENAI_VISION
    async def extract(self, **_: object) -> dict[str, object]:
        raise ProviderNetworkError("offline test provider")
    async def repair_structure(self, **_: object) -> dict[str, object]:
        raise ProviderNetworkError("offline test provider")


@pytest_asyncio.fixture
async def repository() -> PostgresPhase2Repository:
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is required for Phase 8 PostgreSQL integration tests")
    connection = await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row)
    migrations = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
    async with connection.cursor() as cursor:
        await cursor.execute("drop schema public cascade")
        await cursor.execute("create schema public")
        await cursor.execute("\n".join(item.read_text(encoding="utf-8") for item in sorted(migrations.glob("*.sql"))))
    await connection.commit(); await connection.set_autocommit(True)
    try:
        yield PostgresPhase2Repository(connection)
    finally:
        await connection.close()


async def _candidate(client: httpx.AsyncClient, client_id: str) -> str:
    session = await client.post("/api/v1/selection-sessions", json={"need": {}}, headers={"X-Client-Id": client_id, "Idempotency-Key": str(uuid4())})
    candidate = await client.post(f"/api/v1/selection-sessions/{session.json()['id']}/candidates", json={"display_label": "A"}, headers={"X-Client-Id": client_id, "Idempotency-Key": str(uuid4())})
    assert candidate.status_code == 201, candidate.text
    return candidate.json()["id"]


async def _upload(client: httpx.AsyncClient, client_id: str, candidate_id: str, filename: str) -> dict[str, object]:
    data = (Path(__file__).resolve().parents[2] / "test-fixtures" / "demo-images" / filename).read_bytes()
    response = await client.post(f"/api/v1/candidates/{candidate_id}/images", headers={"X-Client-Id": client_id, "Idempotency-Key": str(uuid4())}, files={"file": (filename, data, "image/png")})
    assert response.status_code == 201, response.text
    return response.json()


async def test_fixture_named_images_do_not_bypass_a_provider_failure(repository: PostgresPhase2Repository) -> None:
    runner = ManualTaskRunner()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=FailingLiveProvider())
    client_id = str(uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        candidate_id = await _candidate(client, client_id)
        first = await _upload(client, client_id, candidate_id, "candidate-a-qingxiang-1.png")
        upload = await _upload(client, client_id, candidate_id, "candidate-a-qingxiang-2.png")
        assert await runner.drain() == 2
        job = await client.get(f"/api/v1/jobs/{upload['extraction_job']['id']}", headers={"X-Client-Id": client_id})
        assert job.json()["status"] == "failed"
        assert job.json()["processing_mode"] == "openai-vision"
        assert job.json()["extraction_version_id"] is None


async def test_non_fixture_provider_failure_remains_failed(repository: PostgresPhase2Repository) -> None:
    runner = ManualTaskRunner()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=FailingLiveProvider())
    client_id = str(uuid4())
    raw = BytesIO(); Image.new("RGB", (640, 480), "purple").save(raw, "PNG")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        candidate_id = await _candidate(client, client_id)
        response = await client.post(f"/api/v1/candidates/{candidate_id}/images", headers={"X-Client-Id": client_id, "Idempotency-Key": str(uuid4())}, files={"file": ("unapproved.png", raw.getvalue(), "image/png")})
        assert response.status_code == 201, response.text
        assert await runner.drain() == 1
        job = await client.get(f"/api/v1/jobs/{response.json()['extraction_job']['id']}", headers={"X-Client-Id": client_id})
        assert job.json()["status"] == "failed"
        assert job.json()["processing_mode"] == "openai-vision"
        assert job.json()["error_code"] == "ai_provider_error"


async def test_admin_observability_is_token_protected(repository: PostgresPhase2Repository, monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "phase8-test-token")
    app = create_app(repository=repository, task_runner=ManualTaskRunner(), temporary_storage=InMemoryTemporaryPrivateStorage(), provider=FailingLiveProvider())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        denied = await client.get("/api/v1/admin/jobs")
        assert denied.status_code == 403
        assert "phase8-test-token" not in denied.text
        headers = {"Authorization": "Bearer phase8-test-token"}
        jobs = await client.get("/api/v1/admin/jobs", headers=headers)
        calls = await client.get("/api/v1/admin/ai-calls", headers=headers)
        assert jobs.status_code == calls.status_code == 200


async def test_failed_fixture_images_cannot_create_decision_inputs(repository: PostgresPhase2Repository) -> None:
    """Fixture-named input must not create a synthetic extraction or decision."""
    runner = ManualTaskRunner()
    storage = InMemoryTemporaryPrivateStorage()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=storage, provider=FailingLiveProvider())
    client_id = str(uuid4())
    files = (
        ("A", "candidate-a-qingxiang-1.png", "candidate-a-qingxiang-2.png"),
        ("B", "candidate-b-nongxiang-1.png", "candidate-b-nongxiang-2.png"),
        ("C", "candidate-c-marketing-heavy-1.png", "candidate-c-marketing-heavy-2.png"),
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session = await client.post("/api/v1/selection-sessions", json={"need": {"taste_text": "清香"}}, headers={"X-Client-Id": client_id, "Idempotency-Key": str(uuid4())})
        session_id = session.json()["id"]
        for label, first, second in files:
            candidate = await client.post(f"/api/v1/selection-sessions/{session_id}/candidates", json={"display_label": label}, headers={"X-Client-Id": client_id, "Idempotency-Key": str(uuid4())})
            assert candidate.status_code == 201
            candidate_id = candidate.json()["id"]
            await _upload(client, client_id, candidate_id, first)
            await _upload(client, client_id, candidate_id, second)
        assert await runner.drain() == 6
        assert len(storage.objects) == 6
        decision_job = await client.post(f"/api/v1/selection-sessions/{session_id}/analyze", headers={"X-Client-Id": client_id, "Idempotency-Key": str(uuid4())})
        assert decision_job.status_code == 409, decision_job.text
        assert decision_job.json()["error"]["code"] == "decision_inputs_incomplete"
