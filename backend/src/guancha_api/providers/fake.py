from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from guancha_api.schemas.contracts import ProcessingMode


class ProviderNetworkError(RuntimeError):
    """A transient provider transport failure, never an HTTP response."""


class ProviderTimeoutError(ProviderNetworkError, TimeoutError):
    """A provider timeout, normalized without exposing upstream details."""


class ProviderRateLimitedError(ProviderNetworkError):
    """A provider rate-limit response, eligible for the normal one retry."""


class ProviderStructuredOutputError(ValueError):
    """A provider returned output that cannot enter the frozen payload contract."""


@dataclass(slots=True)
class FakeProvider:
    """Deterministic test provider. It never reads a key or uses the network."""

    extraction_response: dict[str, Any]
    repair_response: dict[str, Any] | None = None
    network_failures_before_success: int = 0
    extraction_calls: int = field(default=0, init=False)
    repair_calls: int = field(default=0, init=False)

    @property
    def processing_mode(self) -> ProcessingMode:
        return ProcessingMode.FAKE_PROVIDER

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_identifier(self) -> str:
        return "fixture-v1"

    async def extract(self, *, image_object_keys: tuple[str, ...] | None = None, image_object_key: str | None = None) -> dict[str, Any]:
        del image_object_keys, image_object_key
        self.extraction_calls += 1
        if self.extraction_calls <= self.network_failures_before_success:
            raise ProviderNetworkError("fake transient network failure")
        return deepcopy(self.extraction_response)

    async def repair_structure(self, *, invalid_response: dict[str, Any]) -> dict[str, Any]:
        del invalid_response
        self.repair_calls += 1
        if self.repair_response is None:
            return deepcopy(self.extraction_response)
        return deepcopy(self.repair_response)
