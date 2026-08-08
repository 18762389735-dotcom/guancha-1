from __future__ import annotations

import pytest

from guancha_api.infrastructure.storage.memory import InMemoryTemporaryPrivateStorage
from guancha_api.main import _provider_from_environment, create_app
from guancha_api.providers.fake import FakeProvider, ProviderNetworkError
from guancha_api.providers.unavailable import UnconfiguredVisionProvider


@pytest.mark.asyncio
async def test_unconfigured_runtime_never_fabricates_a_fake_extraction(monkeypatch) -> None:
    monkeypatch.delenv("GUANCHA_PROVIDER", raising=False)
    provider = _provider_from_environment(InMemoryTemporaryPrivateStorage())

    assert isinstance(provider, UnconfiguredVisionProvider)
    try:
        await provider.extract(image_object_keys=("temporary/example",))
    except ProviderNetworkError:
        pass
    else:  # pragma: no cover - protects the Fake-as-live invariant
        raise AssertionError("an unconfigured runtime must not return a fixture")


def test_fake_remains_explicit_test_or_internal_mode(monkeypatch) -> None:
    monkeypatch.setenv("GUANCHA_PROVIDER", "fake")
    app = create_app()
    assert isinstance(app.state.provider, FakeProvider)
