"""High-value competition flow: 3 candidates, A/B dual-image, aggregate rejudge."""
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


def image_bytes(color: str) -> bytes:
    stream = BytesIO(); Image.new("RGB", (640, 480), color).save(stream, "PNG"); return stream.getvalue()


def provider() -> FakeProvider:
    return FakeProvider(extraction_response={
        "product_name": "铁观音", "tea_category": "乌龙茶", "tea_subtype": "铁观音", "origin": None,
        "roast_or_style": "清香型", "aroma_claims": [], "taste_claims": [], "season": None,
        "year_or_batch": None, "grade": None, "weight": None, "price": None, "brew_claims": [], "risk_flags": [],
        "evidence": [{"field_name": "tea_type", "raw_text": "铁观音", "normalized_value": "tieguanyin", "model_confidence": 1,
                      "information_status": "explicit", "source_type": "product-claim", "verification_status": "unverified",
                      "source_location": "title", "evidence_strength": "high"}],
    })


async def test_three_candidate_competition_flow_preserves_image_and_decision_lineage(repository: PostgresPhase2Repository) -> None:
    runner = ManualTaskRunner()
    app = create_app(repository=repository, task_runner=runner, temporary_storage=InMemoryTemporaryPrivateStorage(), provider=provider())
    headers = {"X-Client-Id": str(uuid4())}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        session = await client.post("/api/v1/selection-sessions", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"need": {"taste_text": "清香", "budget_text": "100以内"}})
        session_id = session.json()["id"]
        candidate_ids: list[str] = []
        for label, image_count in (("A", 2), ("B", 2), ("C", 1)):
            candidate = await client.post(f"/api/v1/selection-sessions/{session_id}/candidates", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"display_label": label})
            candidate_id = candidate.json()["id"]; candidate_ids.append(candidate_id)
            for image_index in range(image_count):
                upload = await client.post(f"/api/v1/candidates/{candidate_id}/images", headers={**headers, "Idempotency-Key": str(uuid4())}, files={"file": (f"{label}-{image_index}.png", image_bytes(f"#{image_index + 1}{image_index + 2}{image_index + 3}"), "image/png")})
                assert upload.status_code == 201
        assert await runner.drain() == 5
        extractions = []
        for candidate_id, expected_count in zip(candidate_ids, (2, 2, 1), strict=True):
            extraction = await client.get(f"/api/v1/candidates/{candidate_id}/current-extraction", headers=headers)
            assert extraction.status_code == 200
            assert len(extraction.json()["source_image_ids"]) == expected_count
            extractions.append(extraction.json()["id"])
        assert len(set(extractions)) == 3
        decision_job = await client.post(f"/api/v1/selection-sessions/{session_id}/analyze", headers={**headers, "Idempotency-Key": str(uuid4())})
        assert decision_job.status_code == 201 and await runner.drain() == 1
        v1 = (await client.get(f"/api/v1/selection-sessions/{session_id}/current-decision", headers=headers)).json()["id"]
        questions = (await client.post(f"/api/v1/decision-versions/{v1}/questions", headers={**headers, "Idempotency-Key": str(uuid4())})).json()
        reply_ids = []
        for question in questions:
            reply = await client.post(f"/api/v1/selection-sessions/{session_id}/merchant-replies", headers={**headers, "Idempotency-Key": str(uuid4())}, json={"decision_version_id": v1, "followup_question_id": question["id"], "raw_text": "轻火，春茶，可试饮，价格¥88"})
            assert reply.status_code == 201
            reply_ids.append(reply.json()["id"])
        if reply_ids:
            rejudge = await client.post(f"/api/v1/selection-sessions/{session_id}/rejudge", headers={**headers, "Idempotency-Key": str(uuid4())}, json={})
            assert rejudge.status_code == 201 and await runner.drain() == 1
            job = (await client.get(f"/api/v1/jobs/{rejudge.json()['id']}", headers=headers)).json()
            assert job["status"] == "completed" and job["decision_version_id"] != v1
            delta = (await client.get(f"/api/v1/decision-deltas/{job['decision_delta_id']}", headers=headers)).json()
            assert set(delta["merchant_reply_ids"]) == set(reply_ids)
        snapshot = await client.get(f"/api/v1/selection-sessions/{session_id}/snapshot", headers=headers)
        assert snapshot.status_code == 200 and len(snapshot.json()["candidates"]) == 3
        recovered = snapshot.json()
        assert len(recovered["questions"]) == len(questions)
        assert set(reply["id"] for reply in recovered["merchant_replies"]) == set(reply_ids)
        if reply_ids:
            assert recovered["rejudge_job"]["status"] == "completed"
            assert set(recovered["decision_delta"]["merchant_reply_ids"]) == set(reply_ids)
            assert recovered["question_decision_version_id"] != recovered["current_decision_id"]
