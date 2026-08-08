from __future__ import annotations

from typing import Any

from guancha_api.providers.fake import ProviderNetworkError
from guancha_api.schemas.contracts import ProcessingMode


class UnconfiguredVisionProvider:
    """A safe production default which can never fabricate an extraction.

    Tests inject ``FakeProvider`` directly.  A normal application process with
    no configured external provider remains startable for health checks, but an
    extraction job deterministically fails through the existing provider-error
    path instead of returning a fixture as if it were a real product reading.
    """

    @property
    def processing_mode(self) -> ProcessingMode:
        return ProcessingMode.LIVE_AI

    @property
    def provider_name(self) -> str:
        return "unconfigured"

    @property
    def model_identifier(self) -> str:
        return "not-configured"

    async def extract(self, *, image_object_keys: tuple[str, ...]) -> dict[str, Any]:
        del image_object_keys
        raise ProviderNetworkError("Vision provider is not configured")

    async def repair_structure(self, *, invalid_response: dict[str, Any]) -> dict[str, Any]:
        del invalid_response
        raise ProviderNetworkError("Vision provider is not configured")
