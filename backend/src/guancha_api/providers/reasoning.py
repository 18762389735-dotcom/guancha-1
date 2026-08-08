from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ReasoningCandidate:
    candidate_id: object
    field_key: str
    question_text: str
    reason: str
    affected_decision: tuple[str, ...]
    answer_branches: tuple[str, ...]
    priority: int
    value_score: int
    value_components: dict[str, int]


class ReasoningProvider(Protocol):
    """Expression-only boundary: no database access and no new factual fields."""

    async def generate_questions(self, candidates: tuple[ReasoningCandidate, ...]) -> tuple[ReasoningCandidate, ...]: ...


class FakeReasoningProvider:
    async def generate_questions(self, candidates: tuple[ReasoningCandidate, ...]) -> tuple[ReasoningCandidate, ...]:
        return candidates[:3]
