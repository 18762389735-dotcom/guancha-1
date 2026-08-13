from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from guancha_api.application.phase2_service import Phase2ExtractionService
from guancha_api.application.task_runners import ManualTaskRunner
from guancha_api.infrastructure.storage.memory import InMemoryTemporaryPrivateStorage
from guancha_api.providers.fake import FakeProvider
from guancha_api.schemas.contracts import CreateCandidateRequest, JobStage, JobState, ProcessingMode, SelectionNeedInput

pytestmark = pytest.mark.asyncio


async def test_session_and_candidate_services_preserve_created_edge_without_database() -> None:
    now = datetime.now(timezone.utc); session_id, client_id, candidate_id = uuid4(), uuid4(), uuid4()
    class Repository:
        session_calls = candidate_calls = 0
        async def create_selection_session(self, **kwargs):
            self.session_calls += 1
            return ({"id": session_id, "anonymous_client_id": client_id, "need": {}, "expires_at": now + timedelta(days=1), "created_at": now, "updated_at": now}, self.session_calls == 1)
        async def create_candidate(self, **kwargs):
            self.candidate_calls += 1
            return ({"id": candidate_id, "selection_session_id": session_id, "display_label": "A", "display_name": "Tea", "display_order": 1, "created_at": now}, self.candidate_calls == 1)
        async def stale_current_decision_for_session(self, **kwargs): return None

    service = Phase2ExtractionService(Repository())
    first_session, first_created = await service.create_session(client_id=client_id, idempotency_key=uuid4(), need=SelectionNeedInput())
    replay_session, replay_created = await service.create_session(client_id=client_id, idempotency_key=uuid4(), need=SelectionNeedInput())
    assert first_session.id == replay_session.id and first_created is True and replay_created is False
    request = CreateCandidateRequest(display_label="A", display_name="Tea")
    first_candidate, first_candidate_created = await service.create_candidate(client_id=client_id, session_id=session_id, idempotency_key=uuid4(), request=request)
    replay_candidate, replay_candidate_created = await service.create_candidate(client_id=client_id, session_id=session_id, idempotency_key=uuid4(), request=request)
    assert first_candidate.id == replay_candidate.id and first_candidate_created is True and replay_candidate_created is False


async def test_staged_analysis_returns_only_newly_accepted_jobs() -> None:
    job_id, candidate_id, image_id = uuid4(), uuid4(), uuid4(); now = datetime.now(timezone.utc)
    job = SimpleNamespace(id=job_id, candidate_id=candidate_id, candidate_image_id=image_id, status=JobState.QUEUED, stage=JobStage.QUEUED, attempt=1, error_code=None, extraction_version_id=None, decision_version_id=None, decision_delta_id=None, processing_mode=ProcessingMode.FAKE_PROVIDER, created_at=now, updated_at=now)
    class Repository:
        async def list_queued_extraction_jobs_for_session(self, **kwargs): return [job]
        async def fail_extraction_job(self, **kwargs): raise AssertionError("duplicate acceptance must not fail the job")
    service = Phase2ExtractionService(Repository())
    runner = ManualTaskRunner(); storage = InMemoryTemporaryPrivateStorage(); provider = FakeProvider(extraction_response={"evidence": []})
    kwargs = dict(session_id=uuid4(), client_id=uuid4(), storage=storage, task_runner=runner, provider=provider)
    assert len(await service.start_staged_extractions(**kwargs)) == 1
    assert await service.start_staged_extractions(**kwargs) == ()
    assert runner.pending_count == 1
