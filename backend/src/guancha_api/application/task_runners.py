from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable


logger = logging.getLogger(__name__)


class TaskEnqueueError(RuntimeError):
    """A task could not be accepted after its queued Job was persisted."""


class InProcessTaskRunner:
    """Schedule background work without holding the request coroutine open."""

    def __init__(self) -> None:
        self._active_tasks: set[asyncio.Task[None]] = set()
        self._active_job_ids: set[object] = set()

    @property
    def active_count(self) -> int:
        return len(self._active_tasks)

    async def enqueue(self, *, job_id: object, task: Callable[[], Awaitable[None]]) -> bool:
        if job_id in self._active_job_ids:
            return False
        scheduled = asyncio.create_task(task(), name=f"guancha-job-{job_id}")
        self._active_job_ids.add(job_id)
        self._active_tasks.add(scheduled)
        scheduled.add_done_callback(lambda completed: self._on_done(job_id, completed))
        return True

    def _on_done(self, job_id: object, task: asyncio.Task[None]) -> None:
        self._active_tasks.discard(task)
        self._active_job_ids.discard(job_id)
        if task.cancelled():
            logger.info("background_task_cancelled", extra={"job_id": str(job_id)})
            return
        exception = task.exception()
        if exception is not None:
            logger.error(
                "background_task_failed",
                extra={"job_id": str(job_id), "exception_type": type(exception).__name__},
                exc_info=exception,
            )

    async def shutdown(self) -> None:
        """Cancel and await remaining work during application shutdown."""
        tasks = tuple(self._active_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._active_tasks.difference_update(tasks)
        self._active_job_ids.clear()


class ManualTaskRunner:
    def __init__(self) -> None:
        self.tasks: list[tuple[object, Callable[[], Awaitable[None]]]] = []
        self._job_ids: set[object] = set()

    @property
    def pending_count(self) -> int:
        return len(self.tasks)

    async def enqueue(self, *, job_id: object, task: Callable[[], Awaitable[None]]) -> bool:
        if job_id in self._job_ids:
            return False
        self._job_ids.add(job_id)
        self.tasks.append((job_id, task))
        return True

    async def run_next(self) -> bool:
        if not self.tasks:
            return False
        job_id, task = self.tasks.pop(0)
        try:
            await task()
        finally:
            self._job_ids.discard(job_id)
        return True

    async def drain(self) -> int:
        completed = 0
        while await self.run_next():
            completed += 1
        return completed

    async def shutdown(self) -> None:
        """Lifecycle-compatible no-op for deterministic tests."""
        return None
