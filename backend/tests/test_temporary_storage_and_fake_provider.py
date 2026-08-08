from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from guancha_api.infrastructure.storage.memory import InMemoryTemporaryPrivateStorage
from guancha_api.infrastructure.temporary_images import temporary_private_image
from guancha_api.providers.execution import (
    ProviderNetworkExhaustedError,
    ProviderSchemaInvalidError,
    extract_validated_once,
)
from guancha_api.providers.fake import FakeProvider


_FIXTURES = Path(__file__).parent / "fixtures" / "fake_provider"


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


class FixtureSummary(BaseModel):
    title: str
    origin: str


def _validate_summary(raw: dict[str, object]) -> FixtureSummary:
    return FixtureSummary.model_validate(raw)


def test_temporary_private_image_is_deleted_after_success() -> None:
    async def scenario() -> None:
        storage = InMemoryTemporaryPrivateStorage()
        async with temporary_private_image(
            storage,
            object_key="temporary/example.png",
            content_type="image/png",
            data=b"image-bytes",
        ) as image:
            assert image.object_key in storage.objects
            assert image.content_type == "image/png"
        assert storage.objects == {}
        assert storage.deleted_keys == ["temporary/example.png"]

    asyncio.run(scenario())


def test_temporary_private_image_is_deleted_after_failure() -> None:
    async def scenario() -> None:
        storage = InMemoryTemporaryPrivateStorage()
        with pytest.raises(RuntimeError, match="provider failed"):
            async with temporary_private_image(
                storage,
                object_key="temporary/failure.jpg",
                content_type="image/jpeg",
                data=b"image-bytes",
            ):
                raise RuntimeError("provider failed")
        assert storage.objects == {}
        assert storage.deleted_keys == ["temporary/failure.jpg"]

    asyncio.run(scenario())


def test_temporary_private_image_is_deleted_on_task_cancellation() -> None:
    async def scenario() -> None:
        storage = InMemoryTemporaryPrivateStorage()
        with pytest.raises(asyncio.CancelledError):
            async with temporary_private_image(
                storage,
                object_key="temporary/cancelled.png",
                content_type="image/png",
                data=b"image-bytes",
            ):
                raise asyncio.CancelledError()
        assert storage.objects == {}
        assert storage.deleted_keys == ["temporary/cancelled.png"]

    asyncio.run(scenario())


def test_temporary_private_image_is_deleted_after_timeout() -> None:
    async def scenario() -> None:
        storage = InMemoryTemporaryPrivateStorage()

        async def work() -> None:
            async with temporary_private_image(
                storage,
                object_key="temporary/timed-out.png",
                content_type="image/png",
                data=b"image-bytes",
            ):
                await asyncio.sleep(1)

        with pytest.raises(TimeoutError):
            await asyncio.wait_for(work(), timeout=0.01)
        assert storage.objects == {}
        assert storage.deleted_keys == ["temporary/timed-out.png"]

    asyncio.run(scenario())


def test_fake_provider_retries_one_network_failure_then_validates() -> None:
    async def scenario() -> None:
        provider = FakeProvider(
            extraction_response=_load_fixture("valid-summary.json"),
            network_failures_before_success=1,
        )
        result = await extract_validated_once(
            provider,
            image_object_key="temporary/opaque-key",
            validate=_validate_summary,
        )
        assert result == FixtureSummary(title="铁观音", origin="安溪")
        assert provider.extraction_calls == 2
        assert provider.repair_calls == 0

    asyncio.run(scenario())


def test_fake_provider_does_not_retry_network_failure_more_than_once() -> None:
    async def scenario() -> None:
        provider = FakeProvider(
            extraction_response=_load_fixture("valid-summary.json"),
            network_failures_before_success=2,
        )
        with pytest.raises(ProviderNetworkExhaustedError):
            await extract_validated_once(
                provider,
                image_object_key="temporary/opaque-key",
                validate=_validate_summary,
            )
        assert provider.extraction_calls == 2
        assert provider.repair_calls == 0

    asyncio.run(scenario())


def test_schema_failure_uses_exactly_one_repair_and_never_returns_partial_data() -> None:
    async def scenario() -> None:
        provider = FakeProvider(
            extraction_response=_load_fixture("invalid-summary.json"),
            repair_response=_load_fixture("valid-summary.json"),
        )
        result = await extract_validated_once(
            provider,
            image_object_key="temporary/opaque-key",
            validate=_validate_summary,
        )
        assert result.origin == "安溪"
        assert provider.extraction_calls == 1
        assert provider.repair_calls == 1

    asyncio.run(scenario())


def test_unrepairable_schema_failure_raises_without_partial_result() -> None:
    async def scenario() -> None:
        provider = FakeProvider(
            extraction_response=_load_fixture("invalid-summary.json"),
            repair_response=_load_fixture("invalid-summary.json"),
        )
        with pytest.raises(ProviderSchemaInvalidError):
            await extract_validated_once(
                provider,
                image_object_key="temporary/opaque-key",
                validate=_validate_summary,
            )
        assert provider.extraction_calls == 1
        assert provider.repair_calls == 1

    asyncio.run(scenario())
