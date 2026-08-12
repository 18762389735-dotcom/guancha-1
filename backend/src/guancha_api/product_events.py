from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID, NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field


CLIENT_EVENT_NAMES = frozenset({
    "app_open", "start_selection", "onboarding_started", "onboarding_completed",
    "onboarding_skipped", "need_started", "candidate_result_viewed",
    "merchant_question_viewed", "merchant_question_copied", "merchant_reply_started",
    "candidate_selected", "tea_stock_added", "flow_abandoned",
})
SERVER_EVENT_NAMES = frozenset({
    "need_submitted", "candidate_created", "candidate_deleted", "candidate_image_added",
    "candidate_image_removed", "analysis_started", "analysis_completed", "analysis_failed",
    "merchant_reply_submitted", "merchant_reply_unusable", "rejudge_started",
    "rejudge_completed", "rejudge_failed",
})
FailureCategory = Literal[
    "EXTRACTION_MISS", "EXTRACTION_HALLUCINATION", "EVIDENCE_SOURCE_ERROR",
    "MARKETING_CLAIM_LEAK", "SENSORY_OVERCLAIM", "SENSORY_MISSING",
    "NEED_PRIORITY_ERROR", "BUDGET_PARSE_ERROR", "DECISION_ANSWER_MISMATCH",
    "QUESTION_DUPLICATE", "QUESTION_LOW_VALUE", "MERCHANT_REPLY_PARSE_ERROR",
    "MERCHANT_CONFLICT_FALSE_POSITIVE", "REJUDGE_INCONSISTENT",
    "DECISION_STATE_STALE", "STATE_RECOVERY_ERROR", "COLD_START_ERROR",
    "MOBILE_UI_BLOCKER", "PROVIDER_ERROR", "DATABASE_ERROR",
]


class EventMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_count: int | None = Field(default=None, ge=0, le=5)
    image_count: int | None = Field(default=None, ge=0, le=10)
    has_budget: bool | None = None
    has_sensory_need: bool | None = None
    question_field: str | None = Field(default=None, max_length=64)
    question_count: int | None = Field(default=None, ge=0, le=100)
    action_bucket: str | None = Field(default=None, max_length=32)
    processing_mode: str | None = Field(default=None, max_length=32)
    failure_category: FailureCategory | None = None
    onboarding_status: str | None = Field(default=None, max_length=32)
    source: str | None = Field(default=None, max_length=32)
    screen: str | None = Field(default=None, max_length=32)


class ClientProductEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_name: str = Field(min_length=1, max_length=64)
    anonymous_session_id: UUID
    occurred_at: datetime
    flow_id: UUID | None = None
    candidate_id: UUID | None = None
    decision_version_id: UUID | None = None
    stage: str | None = Field(default=None, max_length=32)
    duration_ms: int | None = Field(default=None, ge=0, le=86_400_000)
    error_category: str | None = Field(default=None, max_length=64)
    metadata: EventMetadata = Field(default_factory=EventMetadata)


class ProductEventSink:
    """Append-only, fail-open product telemetry with no business dependency."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self.logger = logging.getLogger("guancha.product_event")

    @classmethod
    def from_environment(cls) -> "ProductEventSink":
        return cls(os.getenv("GUANCHA_PRODUCT_EVENT_LOG_PATH"))

    def emit_client(self, event: ClientProductEvent) -> bool:
        if event.event_name not in CLIENT_EVENT_NAMES:
            return False
        return self._write({
            "schema_version": 1,
            **event.model_dump(mode="json", exclude_none=True),
            "authority": "client",
            "received_at": datetime.now(timezone.utc).isoformat(),
        })

    def emit_server(
        self, *, event_name: str, resource_id: UUID, anonymous_session_id: UUID | None,
        flow_id: UUID | None = None, candidate_id: UUID | None = None,
        decision_version_id: UUID | None = None, stage: str | None = None,
        error_category: str | None = None, metadata: dict[str, object] | None = None,
    ) -> bool:
        if event_name not in SERVER_EVENT_NAMES or anonymous_session_id is None:
            return False
        try:
            safe_metadata = EventMetadata.model_validate(metadata or {})
            event_id = uuid5(NAMESPACE_URL, f"guancha:event:v1:{event_name}:{resource_id}")
            return self._write({
                "schema_version": 1, "event_id": str(event_id), "event_name": event_name,
                "anonymous_session_id": str(anonymous_session_id),
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "flow_id": str(flow_id) if flow_id else None,
                "candidate_id": str(candidate_id) if candidate_id else None,
                "decision_version_id": str(decision_version_id) if decision_version_id else None,
                "stage": stage, "duration_ms": None, "error_category": error_category,
                "metadata": safe_metadata.model_dump(mode="json", exclude_none=True),
                "authority": "server", "received_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            return False

    def _write(self, record: dict[str, object]) -> bool:
        try:
            line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            if self.path:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
            else:
                self.logger.info(line)
            return True
        except Exception:
            self.logger.warning("product event emission failed", exc_info=False)
            return False


def parse_analytics_session(value: str | None) -> UUID | None:
    try:
        return UUID(value) if value else None
    except ValueError:
        return None
