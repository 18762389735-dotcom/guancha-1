from __future__ import annotations

from typing import Protocol
from uuid import UUID


class ProviderDisabledError(RuntimeError):
    """Raised if a Phase 1 caller attempts real provider execution."""


class ExtractionProvider(Protocol):
    async def extract_candidate(self, *, candidate_id: UUID, image_ids: tuple[UUID, ...]) -> UUID:
        """Interface only. No real AI/provider implementation belongs in Phase 1."""
        ...
