from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypeVar

from pydantic import ValidationError

from .fake import ProviderNetworkError, ProviderStructuredOutputError
from guancha_api.schemas.contracts import ProcessingMode


class StructuredVisionProvider(Protocol):
    @property
    def processing_mode(self) -> ProcessingMode: ...

    @property
    def provider_name(self) -> str: ...

    @property
    def model_identifier(self) -> str: ...

    async def extract(self, *, image_object_keys: tuple[str, ...]) -> dict[str, Any]: ...

    async def repair_structure(self, *, invalid_response: dict[str, Any]) -> dict[str, Any]: ...


class ProviderNetworkExhaustedError(RuntimeError):
    """Raised after exactly one retry of a transient provider failure."""


class ProviderSchemaInvalidError(RuntimeError):
    """Raised after exactly one failed structured-output repair attempt."""


T = TypeVar("T")


async def extract_validated_once(
    provider: StructuredVisionProvider,
    *,
    image_object_key: str | None = None,
    image_object_keys: tuple[str, ...] | None = None,
    validate: Callable[[dict[str, Any]], T | Awaitable[T]],
) -> T:
    """Run a provider safely without producing a partial fallback result.

    There are at most two extraction attempts for a network failure. A response that
    fails schema validation receives exactly one repair call. If either policy is
    exhausted, the caller receives a typed error and must mark its Job failed.
    """

    keys = image_object_keys or ((image_object_key,) if image_object_key is not None else ())
    if not keys:
        raise ValueError("at least one image object key is required")
    raw: dict[str, Any] | None = None
    for attempt in range(2):
        try:
            try:
                raw = await provider.extract(image_object_keys=keys)
            except TypeError:
                # Compatibility for deterministic legacy single-image test doubles.
                if len(keys) != 1:
                    raise
                raw = await provider.extract(image_object_key=keys[0])  # type: ignore[call-arg]
            break
        except ProviderStructuredOutputError as error:
            raise ProviderSchemaInvalidError("provider returned malformed structured output") from error
        except ProviderNetworkError as error:
            if attempt == 1:
                raise ProviderNetworkExhaustedError(
                    "provider network retry exhausted"
                ) from error

    assert raw is not None
    try:
        return await _validate(validate, raw)
    except (ValidationError, ValueError, TypeError) as first_error:
        repaired = await provider.repair_structure(invalid_response=raw)
        try:
            return await _validate(validate, repaired)
        except (ValidationError, ValueError, TypeError) as repair_error:
            raise ProviderSchemaInvalidError(
                "provider schema repair failed"
            ) from repair_error


async def _validate(
    validate: Callable[[dict[str, Any]], T | Awaitable[T]], raw: dict[str, Any]
) -> T:
    result = validate(raw)
    if hasattr(result, "__await__"):
        return await result  # type: ignore[misc]
    return result  # type: ignore[return-value]
