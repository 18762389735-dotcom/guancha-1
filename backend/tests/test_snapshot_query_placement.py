import asyncio
from uuid import uuid4

from guancha_api.repositories.postgres import PostgresPhase2Repository


class _Cursor:
    def __init__(self, row=None):
        self.row = row
        self.executed = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def execute(self, sql, params=()):
        self.executed.append((sql, params))

    async def fetchone(self):
        return self.row


class _Connection:
    def __init__(self, cursors):
        self.cursors = list(cursors)

    def cursor(self):
        if not self.cursors:
            raise AssertionError("unexpected cursor use")
        return self.cursors.pop(0)


class _NoCurrentAnswerRepository(PostgresPhase2Repository):
    async def get_current_decision_for_session(self, **_kwargs):
        return None


class _SnapshotRepository(PostgresPhase2Repository):
    async def get_selection_session_for_client(self, **_kwargs):
        return {"need": {"taste_text": "fresh"}}

    async def list_candidates_for_session(self, **_kwargs):
        return []

    async def get_current_decision_for_session(self, **_kwargs):
        return None


def test_answer_contract_no_current_decision_does_not_execute_snapshot_job_sql() -> None:
    repository = _NoCurrentAnswerRepository(_Connection([]))
    result = asyncio.run(repository.answer_contract_inputs_for_session(session_id=uuid4(), client_id=uuid4()))
    assert result is None


def test_snapshot_executes_session_decision_job_query_in_its_own_scope() -> None:
    image_cursor = _Cursor()
    job = {"id": uuid4(), "status": "queued"}
    job_cursor = _Cursor(job)
    repository = _SnapshotRepository(_Connection([image_cursor, job_cursor]))
    result = asyncio.run(repository.selection_snapshot_for_client(session_id=uuid4(), client_id=uuid4()))
    assert result["session_decision_job"] == job
    assert len(job_cursor.executed) == 1
    assert "job_kind='session_decision'" in job_cursor.executed[0][0]
