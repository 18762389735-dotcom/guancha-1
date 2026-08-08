from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol
from uuid import UUID


class TaskRunner(Protocol):
    async def enqueue(self, *, job_id: UUID, task: Callable[[], Awaitable[None]]) -> None:
        """Task boundary only; execution strategy is intentionally deferred."""
        ...
