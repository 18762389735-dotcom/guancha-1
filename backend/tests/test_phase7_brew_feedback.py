import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
import pytest
import pytest_asyncio
from pydantic import ValidationError
from psycopg.rows import dict_row

from guancha_api.application.brew_feedback_service import analyze_feedback
from guancha_api.main import create_app
from guancha_api.providers.feedback import FeedbackReasoningProvider
from guancha_api.repositories.postgres import PostgresPhase2Repository
from guancha_api.schemas.contracts import BrewAdjustment, BrewFeedbackAnalysisRequest, BrewFeedbackAnalysisResponse, BrewParameters, PreferenceEvidence, StructuredBrewFeedback


DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest_asyncio.fixture
async def repository() -> PostgresPhase2Repository:
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is required")
    connection = await psycopg.AsyncConnection.connect(DATABASE_URL, row_factory=dict_row)
    migration_directory = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
    async with connection.cursor() as cursor:
        await cursor.execute("drop schema public cascade")
        await cursor.execute("create schema public")
        await cursor.execute(
            "\n".join(path.read_text(encoding="utf-8") for path in sorted(migration_directory.glob("*.sql")))
        )
    await connection.commit()
    try:
        yield PostgresPhase2Repository(connection)
    finally:
        await connection.close()


def request(*, temperature=90, steep_time=10, rating=None, bitterness=None, note=None):
    return BrewFeedbackAnalysisRequest(
        brew_session_id="brew-1", tea_record_id="tea-1", client_feedback_id=uuid4(),
        system_recommended_parameters=BrewParameters(water_temperature=90, steep_time=10),
        actual_brew_parameters=BrewParameters(water_temperature=temperature, steep_time=steep_time),
        structured_feedback=StructuredBrewFeedback(overall_rating=rating, bitterness=bitterness, free_text_note=note),
    )


def test_brewing_feedback_returns_one_safe_parameter_adjustment():
    result = analyze_feedback(request(temperature=98, steep_time=25, bitterness="bitter"))
    assert result.attribution == "brewing"
    assert result.next_brew_adjustment.parameter == "water_temperature"
    assert len(result.preference_evidence) == 0


def test_positive_reasonable_brew_creates_only_low_tea_evidence():
    data = request(rating=5, note="顺滑回甘")
    data.actual_brew_parameters.infusion_number = 2
    result = analyze_feedback(data)
    assert result.attribution == "tea"
    assert len(result.preference_evidence) == 1
    assert result.preference_evidence[0].confidence == "low"
    assert result.preference_evidence[0].issue_source == "tea"


def test_repeated_reasonable_heavy_roast_feedback_creates_low_negative_tea_evidence():
    data = request(note="heavy roast is not pleasant")
    data.actual_brew_parameters.infusion_number = 2
    result = analyze_feedback(data)
    assert result.attribution == "tea"
    assert result.preference_evidence[0].target_type == "roast"
    assert result.preference_evidence[0].polarity == "negative"
    assert result.preference_evidence[0].confidence == "low"


def test_insufficient_feedback_stays_uncertain_without_evidence():
    result = analyze_feedback(request())
    assert result.attribution == "uncertain"
    assert result.preference_evidence == ()


@pytest.mark.asyncio
async def test_feedback_provider_failure_has_sanitized_retryable_error():
    class FailingProvider(FeedbackReasoningProvider):
        async def explain_brew_feedback(self, request):
            raise RuntimeError("provider secret must not escape")

    app = create_app(feedback_provider=FailingProvider())
    from httpx import ASGITransport, AsyncClient
    payload = request().model_dump(mode="json")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/brew-feedback/analyze",
            json=payload,
            headers={"X-Client-Id": str(uuid4()), "Idempotency-Key": str(uuid4())},
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "feedback_analysis_failed"
    assert "secret" not in response.text


@pytest.mark.asyncio
async def test_feedback_api_requires_idempotency_header_and_returns_structured_analysis():
    from httpx import ASGITransport, AsyncClient

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        missing = await client.post(
            "/api/v1/brew-feedback/analyze",
            json=request(temperature=98, steep_time=25, bitterness="bitter").model_dump(mode="json"),
            headers={"X-Client-Id": str(uuid4())},
        )
        response = await client.post(
            "/api/v1/brew-feedback/analyze",
            json=request(temperature=98, steep_time=25, bitterness="bitter").model_dump(mode="json"),
            headers={"X-Client-Id": str(uuid4()), "Idempotency-Key": str(uuid4())},
        )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "missing_idempotency_key"
    assert response.status_code == 200
    assert response.json()["attribution"] == "brewing"
    assert response.json()["next_brew_adjustment"]["parameter"] == "water_temperature"


@pytest.mark.asyncio
async def test_feedback_replay_is_persisted_without_a_second_provider_call(repository):
    class CountingProvider(FeedbackReasoningProvider):
        def __init__(self):
            self.calls = 0

        async def explain_brew_feedback(self, payload):
            self.calls += 1
            return analyze_feedback(payload)

    provider = CountingProvider()
    app = create_app(repository=repository, feedback_provider=provider)
    client_id, idempotency_key = uuid4(), uuid4()
    payload = request(temperature=98, steep_time=25, bitterness="bitter").model_dump(mode="json")
    headers = {"X-Client-Id": str(client_id), "Idempotency-Key": str(idempotency_key)}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post("/api/v1/brew-feedback/analyze", json=payload, headers=headers)
        replay = await client.post("/api/v1/brew-feedback/analyze", json=payload, headers=headers)

    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    assert provider.calls == 1


def test_feedback_contract_rejects_partial_adjustments_and_excess_evidence():
    with pytest.raises(ValidationError):
        BrewAdjustment(parameter="steep_time", reason="incomplete", confidence="low")

    evidence = PreferenceEvidence(
        id=uuid4(), target_type="roast", target_value="heavy-roast", polarity="negative",
        confidence="low", issue_source="tea", source_brew_session_id="brew-1",
        created_at=datetime.now(timezone.utc),
    )
    with pytest.raises(ValidationError):
        BrewFeedbackAnalysisResponse(
            attribution="tea", attribution_reasons=("fixture",),
            next_brew_adjustment=BrewAdjustment(reason="observe", confidence="low"),
            preference_evidence=(evidence, evidence, evidence, evidence),
            impact_explanation="fixture",
        )
