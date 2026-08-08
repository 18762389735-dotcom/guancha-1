"""Phase 3 PRD integration tests: real PostgreSQL, generated images, FakeProvider only."""
from __future__ import annotations

import asyncio
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

from guancha_api.application.task_runners import InProcessTaskRunner, ManualTaskRunner
from guancha_api.infrastructure.storage.memory import InMemoryTemporaryPrivateStorage
from guancha_api.main import create_app
from guancha_api.providers.fake import FakeProvider
from guancha_api.providers.mimo import MiMoVisionProvider
from guancha_api.repositories.postgres import PostgresPhase2Repository


DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.asyncio


class RecordingFakeProvider(FakeProvider):
    def __init__(self, *, extraction_response: dict[str, object]) -> None:
        super().__init__(extraction_response=extraction_response)
        self.input_sets: list[tuple[str, ...]] = []

    async def extract(self, *, image_object_keys: tuple[str, ...] | None = None, image_object_key: str | None = None) -> dict[str, object]:
        keys = image_object_keys or ((image_object_key,) if image_object_key else ())
        self.input_sets.append(keys)
        return await super().extract(image_object_keys=keys)


class StagedVisionProvider(MiMoVisionProvider):
    """Offline double for an external vision provider's dispatch boundary."""

    def __init__(self, *, extraction_response: dict[str, object], storage: InMemoryTemporaryPrivateStorage) -> None:
        super().__init__(api_key="test-only", model="mimo-v2.5", storage=storage)
        self.extraction_response = extraction_response
        self.extraction_calls = 0
        self.input_sets: list[tuple[str, ...]] = []

    async def extract(self, *, image_object_keys: tuple[str, ...] | None = None, image_object_key: str | None = None) -> dict[str, object]:
        keys = image_object_keys or ((image_object_key,) if image_object_key else ())
        self.input_sets.append(keys)
        self.extraction_calls += 1
        return self.extraction_response


@pytest_asyncio.fixture
async def repository() -> PostgresPhase2Repository:
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is required for Phase 3 PostgreSQL integration tests")
    connection = await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row)
    migration_directory = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
    migration = "\n".join(path.read_text(encoding="utf-8") for path in sorted(migration_directory.glob("*.sql")))
    async with connection.cursor() as cursor:
        await cursor.execute("drop schema public cascade")
        await cursor.execute("create schema public")
        await cursor.execute(migration)
    await connection.commit()
    await connection.set_autocommit(True)
    try:
        yield PostgresPhase2Repository(connection)
    finally:
        await connection.close()


def _image(color: str) -> bytes:
    value = BytesIO()
    Image.new("RGB", (640, 480), color).save(value, "PNG")
    return value.getvalue()


def _payload(name: str, *, two_sources: bool = False) -> dict[str, object]:
    evidence: list[dict[str, object]] = [{
        "field_name": "product_name", "raw_text": name, "normalized_value": name,
        "model_confidence": 0.9, "information_status": "explicit",
        "source_type": "merchant-claim", "verification_status": "user-confirmed",
        "source_location": "title", "evidence_strength": "high", "source_image_index": 1,
    }]
    if two_sources:
        evidence.append({
            "field_name": "origin", "raw_text": "安溪", "normalized_value": "安溪",
            "model_confidence": 0.8, "information_status": "explicit",
            "source_type": "merchant-claim", "verification_status": "user-confirmed",
            "source_location": "details", "evidence_strength": "medium", "source_image_index": 2,
        })
    return {
        "product_name": name, "tea_category": "乌龙茶", "tea_subtype": "铁观音", "origin": "安溪",
        "roast_or_style": None, "aroma_claims": [], "taste_claims": [], "season": None, "year_or_batch": None,
        "grade": None, "weight": None, "price": None, "brew_claims": [], "risk_flags": [], "evidence": evidence,
    }


async def _session_and_candidates(client: httpx.AsyncClient, client_id: str, count: int) -> tuple[str, list[str]]:
    session = await client.post("/api/v1/selection-sessions", json={"need": {"taste_text": "清香"}}, headers={"X-Client-Id": client_id, "Idempotency-Key": str(uuid4())})
    assert session.status_code == 201
    result = []
    for index in range(count):
        response = await client.post(f"/api/v1/selection-sessions/{session.json()['id']}/candidates", json={"display_label": chr(65 + index)}, headers={"X-Client-Id": client_id, "Idempotency-Key": str(uuid4())})
        assert response.status_code == 201
        result.append(response.json()["id"])
    return session.json()["id"], result


async def _upload(client: httpx.AsyncClient, client_id: str, candidate_id: str, color: str) -> dict[str, object]:
    response = await client.post(f"/api/v1/candidates/{candidate_id}/images", headers={"X-Client-Id": client_id, "Idempotency-Key": str(uuid4())}, files={"file": ("fixture.png", _image(color), "image/png")})
    assert response.status_code == 201, response.text
    return response.json()


async def _poll_terminal_job(client: httpx.AsyncClient, client_id: str, job_id: str) -> dict[str, object]:
    for _ in range(80):
        response = await client.get(f"/api/v1/jobs/{job_id}", headers={"X-Client-Id": client_id})
        assert response.status_code == 200
        body = response.json()
        if body["status"] in {"completed", "failed", "stale"}:
            return body
        await asyncio.sleep(0.05)
    raise AssertionError("Extraction job did not reach a terminal state")


async def test_external_two_image_candidate_is_dispatched_once_after_selection_start(
    repository: PostgresPhase2Repository,
) -> None:
    """A live-style provider must not receive per-upload calls for a pair."""
    runner, storage = ManualTaskRunner(), InMemoryTemporaryPrivateStorage()
    provider = StagedVisionProvider(extraction_response=_payload("joint", two_sources=True), storage=storage)
    app = create_app(
        repository=repository, task_runner=runner, temporary_storage=storage, provider=provider
    )
    client_id = str(uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session_id, candidates = await _session_and_candidates(client, client_id, 1)
        first = await _upload(client, client_id, candidates[0], "red")
        second = await _upload(client, client_id, candidates[0], "blue")
        assert await runner.drain() == 0
        kickoff = await client.post(
            f"/api/v1/selection-sessions/{session_id}/analyze",
            headers={"X-Client-Id": client_id, "Idempotency-Key": str(uuid4())},
        )
        assert kickoff.status_code == 201
        assert kickoff.json()["id"] == second["extraction_job"]["id"]
        assert await runner.drain() == 1
        completed = await client.get(
            f"/api/v1/jobs/{second['extraction_job']['id']}",
            headers={"X-Client-Id": client_id},
        )
    assert completed.json()["status"] == "completed"
    assert provider.extraction_calls == 1
    assert len(provider.input_sets) == 1
    assert len(provider.input_sets[0]) == 2
    assert first["extraction_job"]["id"] != second["extraction_job"]["id"]


async def test_external_abc_input_sets_create_exactly_three_vision_calls(
    repository: PostgresPhase2Repository,
) -> None:
    """A=2, B=2, C=1 is the paid-call boundary used by final browser E2E."""
    runner, storage = ManualTaskRunner(), InMemoryTemporaryPrivateStorage()
    provider = StagedVisionProvider(extraction_response=_payload("abc"), storage=storage)
    app = create_app(repository=repository, task_runner=runner, temporary_storage=storage, provider=provider)
    client_id = str(uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session_id, candidates = await _session_and_candidates(client, client_id, 3)
        for candidate_id, count, colors in zip(
            candidates, (2, 2, 1), (("red", "blue"), ("green", "yellow"), ("purple",)), strict=True
        ):
            for color in colors[:count]:
                await _upload(client, client_id, candidate_id, color)
        assert await runner.drain() == 0
        kickoff = await client.post(
            f"/api/v1/selection-sessions/{session_id}/analyze",
            headers={"X-Client-Id": client_id, "Idempotency-Key": str(uuid4())},
        )
        assert kickoff.status_code == 201
        assert await runner.drain() == 3
    assert provider.extraction_calls == 3
    assert sorted(len(item) for item in provider.input_sets) == [1, 2, 2]


async def test_session_allows_five_candidates_and_candidate_deletion_is_isolated(repository: PostgresPhase2Repository) -> None:
    runner, storage = ManualTaskRunner(), InMemoryTemporaryPrivateStorage()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=storage, provider=FakeProvider(extraction_response=_payload("base")))
    client_id = str(uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session_id, candidates = await _session_and_candidates(client, client_id, 5)
        sixth = await client.post(f"/api/v1/selection-sessions/{session_id}/candidates", json={"display_label": "F"}, headers={"X-Client-Id": client_id, "Idempotency-Key": str(uuid4())})
        assert sixth.status_code == 409
        removed = await client.delete(f"/api/v1/candidates/{candidates[2]}", headers={"X-Client-Id": client_id})
        assert removed.status_code == 204
        replacement = await client.post(f"/api/v1/selection-sessions/{session_id}/candidates", json={"display_label": "F"}, headers={"X-Client-Id": client_id, "Idempotency-Key": str(uuid4())})
        assert replacement.status_code == 201
        assert replacement.json()["position"] == 3
        listed = await client.get(f"/api/v1/selection-sessions/{session_id}/candidates", headers={"X-Client-Id": client_id})
        assert [row["id"] for row in listed.json()] == candidates[:2] + [replacement.json()["id"]] + candidates[3:]


async def test_two_images_are_jointly_extracted_and_new_version_becomes_current(repository: PostgresPhase2Repository) -> None:
    runner, storage = ManualTaskRunner(), InMemoryTemporaryPrivateStorage()
    first_provider = RecordingFakeProvider(extraction_response=_payload("A-v1"))
    app = create_app(repository=repository, task_runner=runner, temporary_storage=storage, provider=first_provider)
    client_id = str(uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        _, candidate_ids = await _session_and_candidates(client, client_id, 1)
        candidate_id = candidate_ids[0]
        first = await _upload(client, client_id, candidate_id, "red")
        assert await runner.drain() == 1
        first_job = await client.get(f"/api/v1/jobs/{first['extraction_job']['id']}", headers={"X-Client-Id": client_id})
        v1 = first_job.json()["extraction_version_id"]
        second_provider = RecordingFakeProvider(extraction_response=_payload("A-v2", two_sources=True))
        app.state.provider = second_provider
        second = await _upload(client, client_id, candidate_id, "blue")
        assert second["image"]["candidate_id"] == candidate_id
        assert second["image"]["display_order"] == 2
        stale_before_joint_completion = await client.get(
            f"/api/v1/candidates/{candidate_id}/current-extraction",
            headers={"X-Client-Id": client_id},
        )
        assert stale_before_joint_completion.status_code == 404
        assert await runner.drain() == 1
        second_job = await client.get(f"/api/v1/jobs/{second['extraction_job']['id']}", headers={"X-Client-Id": client_id})
        v2 = second_job.json()["extraction_version_id"]
        current = await client.get(f"/api/v1/candidates/{candidate_id}/current-extraction", headers={"X-Client-Id": client_id})
        v1_response = await client.get(f"/api/v1/extraction-versions/{v1}", headers={"X-Client-Id": client_id})
    assert v1 != v2
    assert first_provider.input_sets == [(f"temporary/{first['image']['id']}",)]
    assert second_provider.input_sets == [(f"temporary/{first['image']['id']}", f"temporary/{second['image']['id']}")]
    assert current.json()["id"] == v2
    assert current.json()["source_image_ids"] == [first["image"]["id"], second["image"]["id"]]
    assert v1_response.status_code == 200
    assert {item["source_image_id"] for item in current.json()["evidence_items"]} == {first["image"]["id"], second["image"]["id"]}
    assert all(item["source_type"] == "product-claim" and item["verification_status"] == "unverified" for item in current.json()["evidence_items"])


async def test_inprocess_worker_uses_independent_database_connection_for_fast_second_image(repository: PostgresPhase2Repository) -> None:
    """A real HTTP request must not race its worker on the same Psycopg connection."""
    assert DATABASE_URL is not None
    runner, storage = InProcessTaskRunner(), InMemoryTemporaryPrivateStorage()
    # The first independently scheduled image is allowed to complete before
    # its sibling exists.  Keep this provider payload valid for both the
    # one-image and the later two-image invocation; this regression targets
    # connection isolation, not two-source evidence mapping.
    provider = RecordingFakeProvider(extraction_response=_payload("joint"))
    app = create_app(
        repository=repository,
        worker_repository_factory=lambda: PostgresPhase2Repository.connect(DATABASE_URL),
        task_runner=runner,
        temporary_storage=storage,
        provider=provider,
    )
    client_id = str(uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        _, candidates = await _session_and_candidates(client, client_id, 1)
        first = await _upload(client, client_id, candidates[0], "red")
        second = await _upload(client, client_id, candidates[0], "blue")
        first_job = await _poll_terminal_job(client, client_id, first["extraction_job"]["id"])
        second_job = await _poll_terminal_job(client, client_id, second["extraction_job"]["id"])
        current = await client.get(f"/api/v1/candidates/{candidates[0]}/current-extraction", headers={"X-Client-Id": client_id})
    await runner.shutdown()
    assert first_job["status"] == "completed"
    assert second_job["status"] == "completed"
    assert current.status_code == 200
    assert current.json()["source_image_ids"] == [first["image"]["id"], second["image"]["id"]]


async def test_deleted_image_stales_current_result_and_allows_a_replacement(repository: PostgresPhase2Repository) -> None:
    runner, storage = ManualTaskRunner(), InMemoryTemporaryPrivateStorage()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=storage, provider=RecordingFakeProvider(extraction_response=_payload("replacement")))
    client_id = str(uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        _, candidates = await _session_and_candidates(client, client_id, 1)
        candidate_id = candidates[0]
        uploaded = await _upload(client, client_id, candidate_id, "red")
        await runner.drain()
        second = await _upload(client, client_id, candidate_id, "blue")
        await runner.drain()
        removed = await client.delete(f"/api/v1/candidate-images/{uploaded['image']['id']}", headers={"X-Client-Id": client_id})
        assert removed.status_code == 204
        current = await client.get(f"/api/v1/candidates/{candidate_id}/current-extraction", headers={"X-Client-Id": client_id})
        survivor = await client.get(f"/api/v1/candidate-images/{second['image']['id']}", headers={"X-Client-Id": client_id})
        replacement = await _upload(client, client_id, candidate_id, "green")
    assert current.status_code == 404
    assert survivor.status_code == 200
    assert survivor.json()["display_order"] == 2
    assert replacement["image"]["display_order"] == 1


async def test_three_candidates_six_images_stay_isolated_and_late_old_job_is_not_current(repository: PostgresPhase2Repository) -> None:
    runner, storage = ManualTaskRunner(), InMemoryTemporaryPrivateStorage()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=storage, provider=FakeProvider(extraction_response=_payload("unused")))
    client_id = str(uuid4())
    providers: list[RecordingFakeProvider] = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        _, candidate_ids = await _session_and_candidates(client, client_id, 3)
        uploads: dict[str, list[dict[str, object]]] = {candidate_id: [] for candidate_id in candidate_ids}
        for index, candidate_id in enumerate(candidate_ids):
            first_provider = RecordingFakeProvider(extraction_response=_payload(f"candidate-{index}-v1"))
            app.state.provider = first_provider
            providers.append(first_provider)
            uploads[candidate_id].append(await _upload(client, client_id, candidate_id, ("red", "green", "blue")[index]))
        for index, candidate_id in enumerate(candidate_ids):
            second_provider = RecordingFakeProvider(extraction_response=_payload(f"candidate-{index}-v2", two_sources=True))
            app.state.provider = second_provider
            providers.append(second_provider)
            uploads[candidate_id].append(await _upload(client, client_id, candidate_id, ("yellow", "purple", "orange")[index]))
        assert await runner.drain() == 6
        for index, candidate_id in enumerate(candidate_ids):
            current = await client.get(f"/api/v1/candidates/{candidate_id}/current-extraction", headers={"X-Client-Id": client_id})
            assert current.status_code == 200
            assert current.json()["source_image_ids"] == [uploads[candidate_id][0]["image"]["id"], uploads[candidate_id][1]["image"]["id"]]
            names = {item["normalized_value"] for item in current.json()["evidence_items"] if item["field_name"] == "product_name"}
            assert names == {f"candidate-{index}-v2"}
    assert all(provider.extraction_calls == 1 for provider in providers)
