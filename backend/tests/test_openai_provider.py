"""Offline unit tests for the opt-in Responses adapter; no SDK or network needed."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from guancha_api.infrastructure.storage.memory import InMemoryTemporaryPrivateStorage
from guancha_api.providers.fake import ProviderNetworkError, ProviderStructuredOutputError
from guancha_api.providers.execution import ProviderSchemaInvalidError, extract_validated_once
from guancha_api.providers.openai import OpenAIResponsesProvider
from guancha_api.schemas.contracts import ProcessingMode


def _payload(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "product_name": "铁观音", "tea_category": "乌龙茶", "tea_subtype": None,
        "origin": None, "roast_or_style": None, "aroma_claims": [], "taste_claims": [],
        "season": None, "year_or_batch": None, "grade": None, "weight": None, "price": None,
        "brew_claims": [], "risk_flags": [],
        "evidence": [{"field_name": "product_name", "raw_text": "铁观音", "normalized_value": "铁观音", "model_confidence": 0.9, "information_status": "explicit", "source_type": "merchant-claim", "verification_status": "system-consistent", "source_location": "title", "evidence_strength": "high"}],
    }
    value.update(overrides)
    return value


class _Responses:
    def __init__(self, output: object | Exception) -> None:
        self.output = output
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if isinstance(self.output, Exception):
            raise self.output
        return SimpleNamespace(output_text=self.output)


class _Client:
    def __init__(self, output: object | Exception) -> None:
        self.responses = _Responses(output)


async def _provider(output: object | Exception) -> tuple[OpenAIResponsesProvider, _Client]:
    storage = InMemoryTemporaryPrivateStorage()
    await storage.put_private(object_key="image", content_type="image/png", data=b"\x89PNG\r\n\x1a\nfixture")
    client = _Client(output)
    return OpenAIResponsesProvider(api_key="test-key", model="test-model", storage=storage, client_factory=lambda _: client), client


@pytest.mark.asyncio
async def test_openai_adapter_constructs_one_image_schema_request_and_parses_nulls() -> None:
    provider, client = await _provider(json.dumps(_payload()))
    assert provider.processing_mode is ProcessingMode.OPENAI_VISION
    assert provider.provider_name == "openai"
    assert provider.model_identifier == "test-model"
    result = await provider.extract(image_object_key="image")
    assert result["product_name"] == "铁观音" and result["origin"] is None
    assert len(client.responses.calls) == 1
    request = client.responses.calls[0]
    assert request["model"] == "test-model"
    assert request["text"]["format"]["type"] == "json_schema"
    assert request["input"][0]["content"][0]["image_url"].startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_openai_adapter_builds_one_request_with_two_same_candidate_images() -> None:
    provider, client = await _provider(json.dumps(_payload()))
    await provider._storage.put_private(object_key="image-2", content_type="image/jpeg", data=b"\xff\xd8fixture")

    await provider.extract(image_object_keys=("image", "image-2"))

    assert len(client.responses.calls) == 1
    content = client.responses.calls[0]["input"][0]["content"]
    assert len(content) == 2
    assert content[0]["image_url"].startswith("data:image/png;base64,")
    assert content[1]["image_url"].startswith("data:image/jpeg;base64,")


@pytest.mark.asyncio
async def test_openai_adapter_rejects_invalid_structured_output_without_fallback() -> None:
    provider, _ = await _provider("not-json")
    with pytest.raises(ProviderStructuredOutputError, match="invalid structured output"):
        await provider.extract(image_object_key="image")
    with pytest.raises(ProviderSchemaInvalidError):
        await extract_validated_once(provider, image_object_key="image", validate=lambda value: value)


@pytest.mark.asyncio
async def test_openai_adapter_converts_provider_failure_to_transient_error() -> None:
    provider, _ = await _provider(OSError("rate limited"))
    with pytest.raises(ProviderNetworkError):
        await provider.extract(image_object_key="image")


def test_fake_mode_app_starts_without_openai_key_and_serves_static_page(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from guancha_api.main import create_app
    from guancha_api.providers.fake import FakeProvider

    monkeypatch.setenv("GUANCHA_PROVIDER", "fake")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GUANCHA_OPENAI_MODEL", raising=False)
    app = create_app()
    assert isinstance(app.state.provider, FakeProvider)
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/").status_code == 200
    assert "/api/v1/extraction-versions/{extraction_version_id}" in app.openapi()["paths"]
