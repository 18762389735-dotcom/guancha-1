"""ASGI contract tests backed by disposable PostgreSQL, never an in-memory repository."""

from __future__ import annotations

import os
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import psycopg
import pytest
import pytest_asyncio
from psycopg.rows import dict_row

from guancha_api.main import create_app
from guancha_api.repositories.postgres import PostgresPhase2Repository


DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def repository() -> PostgresPhase2Repository:
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL ASGI integration tests")
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


async def _client(repository: PostgresPhase2Repository) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(repository=repository)), base_url="http://test")


async def test_session_post_replay_get_and_header_errors(repository: PostgresPhase2Repository) -> None:
    client_id, key = uuid4(), uuid4()
    async with await _client(repository) as client:
        missing = await client.post("/api/v1/selection-sessions", json={"need": {}})
        assert missing.status_code == 422 and missing.json()["error"]["code"] == "missing_client_id"
        request = {"need": {"taste_text": "floral", "purpose_text": "gift", "budget_text": "300", "risk_attitude_text": "low"}}
        headers = {"X-Client-Id": str(client_id), "Idempotency-Key": str(key)}
        created = await client.post("/api/v1/selection-sessions", json=request, headers=headers)
        replay = await client.post("/api/v1/selection-sessions", json=request, headers=headers)
        assert created.status_code == replay.status_code == 201
        assert created.json() == replay.json()
        expires_at = datetime.fromisoformat(created.json()["expires_at"])
        assert datetime.now(timezone.utc) + timedelta(days=14, seconds=59) < expires_at < datetime.now(timezone.utc) + timedelta(days=15, seconds=1)
        restored = await client.get(f"/api/v1/selection-sessions/{created.json()['id']}", headers={"X-Client-Id": str(client_id)})
        assert restored.status_code == 200 and restored.json() == created.json()
        conflict = await client.post("/api/v1/selection-sessions", json={"need": {"taste_text": "roasted"}}, headers=headers)
        assert conflict.status_code == 409 and conflict.json()["error"]["code"] == "idempotency_conflict"
        other_client = await client.post(
            "/api/v1/selection-sessions",
            json=request,
            headers={"X-Client-Id": str(uuid4()), "Idempotency-Key": str(key)},
        )
        assert other_client.status_code == 201
        assert other_client.json()["id"] != created.json()["id"]
        denied = await client.get(
            f"/api/v1/selection-sessions/{created.json()['id']}",
            headers={"X-Client-Id": str(uuid4())},
        )
        assert denied.status_code == 403
        _assert_error(denied.json(), "resource_not_owned")
        missing_session = await client.get(
            f"/api/v1/selection-sessions/{uuid4()}",
            headers={"X-Client-Id": str(client_id)},
        )
        assert missing_session.status_code == 404
        _assert_error(missing_session.json(), "selection_session_not_found")

        invalid_client = await client.get(
            f"/api/v1/selection-sessions/{created.json()['id']}",
            headers={"X-Client-Id": "not-a-uuid"},
        )
        assert invalid_client.status_code == 422
        _assert_error(invalid_client.json(), "invalid_client_id")
        missing_key = await client.post(
            "/api/v1/selection-sessions",
            json=request,
            headers={"X-Client-Id": str(client_id)},
        )
        assert missing_key.status_code == 422
        _assert_error(missing_key.json(), "missing_idempotency_key")
        invalid_key = await client.post(
            "/api/v1/selection-sessions",
            json=request,
            headers={"X-Client-Id": str(client_id), "Idempotency-Key": "not-a-uuid"},
        )
        assert invalid_key.status_code == 422
        _assert_error(invalid_key.json(), "invalid_idempotency_key")


async def test_candidate_replay_limit_and_cross_client_ownership(repository: PostgresPhase2Repository) -> None:
    client_id = uuid4()
    async with await _client(repository) as client:
        missing_client = await client.post(
            "/api/v1/selection-sessions/00000000-0000-0000-0000-000000000001/candidates",
            json={"display_label": "A"},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert missing_client.status_code == 422
        _assert_error(missing_client.json(), "missing_client_id")
        invalid_client = await client.post(
            "/api/v1/selection-sessions/00000000-0000-0000-0000-000000000001/candidates",
            json={"display_label": "A"},
            headers={"X-Client-Id": "bad", "Idempotency-Key": str(uuid4())},
        )
        assert invalid_client.status_code == 422
        _assert_error(invalid_client.json(), "invalid_client_id")
        session = await client.post("/api/v1/selection-sessions", json={"need": {"taste_text": "fresh"}}, headers={"X-Client-Id": str(client_id), "Idempotency-Key": str(uuid4())})
        session_id = session.json()["id"]
        headers = {"X-Client-Id": str(client_id), "Idempotency-Key": str(uuid4())}
        request = {"display_label": "A", "display_name": "Tieguanyin"}
        missing_key = await client.post(
            f"/api/v1/selection-sessions/{session_id}/candidates",
            json=request,
            headers={"X-Client-Id": str(client_id)},
        )
        assert missing_key.status_code == 422
        _assert_error(missing_key.json(), "missing_idempotency_key")
        invalid_key = await client.post(
            f"/api/v1/selection-sessions/{session_id}/candidates",
            json=request,
            headers={"X-Client-Id": str(client_id), "Idempotency-Key": "bad"},
        )
        assert invalid_key.status_code == 422
        _assert_error(invalid_key.json(), "invalid_idempotency_key")
        created = await client.post(f"/api/v1/selection-sessions/{session_id}/candidates", json=request, headers=headers)
        replay = await client.post(f"/api/v1/selection-sessions/{session_id}/candidates", json=request, headers=headers)
        assert created.status_code == replay.status_code == 201 and created.json() == replay.json()
        listed = await client.get(f"/api/v1/selection-sessions/{session_id}/candidates", headers={"X-Client-Id": str(client_id)})
        assert listed.status_code == 200 and listed.json() == [created.json()]
        conflict = await client.post(
            f"/api/v1/selection-sessions/{session_id}/candidates",
            json={"display_label": "A", "display_name": "Different tea"},
            headers=headers,
        )
        assert conflict.status_code == 409
        _assert_error(conflict.json(), "idempotency_conflict")
        for label in ("B", "C", "D", "E"):
            created_candidate = await client.post(f"/api/v1/selection-sessions/{session_id}/candidates", json={"display_label": label}, headers={"X-Client-Id": str(client_id), "Idempotency-Key": str(uuid4())})
            assert created_candidate.status_code == 201
        sixth = await client.post(f"/api/v1/selection-sessions/{session_id}/candidates", json={"display_label": "F"}, headers={"X-Client-Id": str(client_id), "Idempotency-Key": str(uuid4())})
        assert sixth.status_code == 409 and sixth.json()["error"]["code"] == "candidate_limit_exceeded"
        denied = await client.get(f"/api/v1/selection-sessions/{session_id}/candidates", headers={"X-Client-Id": str(uuid4())})
        assert denied.status_code == 403 and denied.json()["error"]["code"] == "resource_not_owned"
        denied_create = await client.post(
            f"/api/v1/selection-sessions/{session_id}/candidates",
            json={"display_label": "B"},
            headers={"X-Client-Id": str(uuid4()), "Idempotency-Key": str(uuid4())},
        )
        assert denied_create.status_code == 403
        _assert_error(denied_create.json(), "resource_not_owned")


async def test_concurrent_candidate_replay_returns_one_persisted_candidate(repository: PostgresPhase2Repository) -> None:
    """Two HTTP apps use separate PostgreSQL connections to exercise the unique race."""
    client_id = uuid4()
    async with await _client(repository) as first_client:
        session = await first_client.post(
            "/api/v1/selection-sessions",
            json={"need": {"taste_text": "fresh"}},
            headers={"X-Client-Id": str(client_id), "Idempotency-Key": str(uuid4())},
        )
        session_id = session.json()["id"]
        second_connection = await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row)
        second_repository = PostgresPhase2Repository(second_connection)
        try:
            async with await _client(second_repository) as second_client:
                headers = {"X-Client-Id": str(client_id), "Idempotency-Key": str(uuid4())}
                request = {"display_label": "A", "display_name": "Tieguanyin"}
                one, two = await asyncio.gather(
                    first_client.post(f"/api/v1/selection-sessions/{session_id}/candidates", json=request, headers=headers),
                    second_client.post(f"/api/v1/selection-sessions/{session_id}/candidates", json=request, headers=headers),
                )
        finally:
            await second_connection.close()
    assert one.status_code == two.status_code == 201
    assert one.json()["id"] == two.json()["id"]
    async with repository._connection.cursor() as cursor:
        await cursor.execute(
            "select count(*) as count, min(display_label) as display_label, min(display_name) as display_name from candidates where selection_session_id=%s",
            (UUID(session_id),),
        )
        row = await cursor.fetchone()
    assert row == {"count": 1, "display_label": "A", "display_name": "Tieguanyin"}


async def test_concurrent_session_replay_returns_one_persisted_session(repository: PostgresPhase2Repository) -> None:
    """Two independent database connections replay one session creation request."""
    client_id, key = uuid4(), uuid4()
    headers = {"X-Client-Id": str(client_id), "Idempotency-Key": str(key)}
    request = {"need": {"taste_text": "fresh", "purpose_text": "gift"}}
    second_connection = await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row)
    second_repository = PostgresPhase2Repository(second_connection)
    try:
        async with await _client(repository) as first_client, await _client(second_repository) as second_client:
            one, two = await asyncio.gather(
                first_client.post("/api/v1/selection-sessions", json=request, headers=headers),
                second_client.post("/api/v1/selection-sessions", json=request, headers=headers),
            )
    finally:
        await second_connection.close()
    assert one.status_code == two.status_code == 201
    assert one.json()["id"] == two.json()["id"]
    async with repository._connection.cursor() as cursor:
        await cursor.execute(
            "select count(*) as count from selection_sessions where anonymous_client_id=%s and idempotency_key=%s",
            (client_id, key),
        )
        row = await cursor.fetchone()
    assert row == {"count": 1}


def _assert_error(payload: dict[str, object], code: str) -> None:
    error = payload["error"]
    assert isinstance(error, dict)
    assert error["code"] == code
    assert error["retryable"] is False
    assert error["resource_id"] is None
    assert error["request_id"]


async def test_database_not_configured_returns_service_unavailable_envelope() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app()),
        base_url="http://test",
    ) as client:
        response = await client.get(
            f"/api/v1/selection-sessions/{uuid4()}",
            headers={"X-Client-Id": str(uuid4())},
        )
    assert response.status_code == 503
    _assert_error(response.json(), "service_unavailable")
