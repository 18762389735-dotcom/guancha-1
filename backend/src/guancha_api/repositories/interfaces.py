from __future__ import annotations

from typing import Protocol
from uuid import UUID

from guancha_api.schemas.contracts import Candidate, JobStatus, SelectionSession


class SelectionSessionRepository(Protocol):
    async def get(self, session_id: UUID) -> SelectionSession | None: ...

    async def create(self, session: SelectionSession, *, idempotency_key: UUID) -> SelectionSession: ...


class CandidateRepository(Protocol):
    async def get(self, candidate_id: UUID) -> Candidate | None: ...

    async def list_for_session(self, session_id: UUID) -> tuple[Candidate, ...]: ...


class JobRepository(Protocol):
    async def get(self, job_id: UUID) -> JobStatus | None: ...
