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
ClientEventName = Literal[
    "app_open", "start_selection", "onboarding_started", "onboarding_completed",
    "onboarding_skipped", "need_started", "candidate_result_viewed",
    "merchant_question_viewed", "merchant_question_copied", "merchant_reply_started",
    "candidate_selected", "tea_stock_added", "flow_abandoned",
]
ServerEventName = Literal[
    "need_submitted", "candidate_created", "candidate_deleted", "candidate_image_added",
    "candidate_image_removed", "analysis_started", "analysis_completed", "analysis_failed",
    "merchant_reply_submitted", "merchant_reply_unusable", "rejudge_started",
    "rejudge_completed", "rejudge_failed",
]
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
QuestionField = Literal[
    "roast_level", "aroma_style", "season", "sample_available", "return_policy",
    "origin_text", "tea_subtype", "price", "weight_grams", "year_or_batch",
    "process_text", "unknown",
]
ActionBucketValue = Literal[
    "currently-selectable", "ask-before-buying", "sample-first",
    "not-recommended-now", "insufficient-information",
]
ProcessingModeValue = Literal["fake-provider", "openai-vision", "test-fixture", "live-ai", "cache-fallback"]
OnboardingStatus = Literal["not_started", "completed", "skipped"]
EventSource = Literal["selection", "settings", "manual", "copy_all"]
EventScreen = Literal[
    "home", "candidates", "o1", "o2", "analysis", "result", "rejudge", "ownership",
    "warehouse", "warehouse-detail", "warehouse-add", "journal", "journal-day",
    "choose-tea", "prepare", "timer", "infusion-done", "feedback", "advanced",
    "brew-result", "record-detail", "settings", "stub",
]
EventStage = Literal[
    "home", "candidates", "o1", "o2", "analysis", "result", "rejudge", "ownership",
    "warehouse", "warehouse-detail", "warehouse-add", "journal", "journal-day",
    "choose-tea", "prepare", "timer", "infusion-done", "feedback", "advanced",
    "brew-result", "record-detail", "settings", "stub", "queued", "claimed", "provider",
    "persisting", "cleaning", "completed", "failed",
]
ErrorCategory = Literal[
    "validation_error", "not_found", "method_not_allowed", "missing_client_id",
    "invalid_client_id", "missing_idempotency_key", "invalid_idempotency_key",
    "resource_not_owned", "selection_session_not_found", "candidate_not_found",
    "candidate_image_not_found", "candidate_limit_exceeded", "candidate_image_limit_exceeded",
    "invalid_image_type", "image_too_large", "unsafe_or_corrupt_image",
    "image_too_low_resolution", "image_pixel_limit_exceeded", "idempotency_conflict",
    "candidate_extraction_in_progress", "candidate_extraction_not_retryable", "ai_timeout",
    "ai_provider_error", "ai_schema_invalid", "worker_interrupted",
    "temporary_image_cleanup_failed", "current_decision_not_available", "decision_stale",
    "questions_not_available", "merchant_reply_not_found", "question_not_available",
    "decision_delta_not_found", "brew_feedback_invalid", "brew_session_not_found",
    "tea_record_not_found", "insufficient_feedback", "feedback_analysis_failed",
    "feedback_duplicate", "contract_not_implemented", "internal_error",
]


class EventMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_count: int | None = Field(default=None, ge=0, le=5)
    image_count: int | None = Field(default=None, ge=0, le=10)
    has_budget: bool | None = None
    has_sensory_need: bool | None = None
    question_field: QuestionField | None = None
    question_count: int | None = Field(default=None, ge=0, le=100)
    action_bucket: ActionBucketValue | None = None
    processing_mode: ProcessingModeValue | None = None
    failure_category: FailureCategory | None = None
    onboarding_status: OnboardingStatus | None = None
    source: EventSource | None = None
    screen: EventScreen | None = None


class ClientProductEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_name: ClientEventName
    anonymous_session_id: UUID
    occurred_at: datetime
    flow_id: UUID | None = None
    candidate_id: UUID | None = None
    decision_version_id: UUID | None = None
    stage: EventStage | None = None
    duration_ms: int | None = Field(default=None, ge=0, le=86_400_000)
    error_category: ErrorCategory | None = None
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
            if not isinstance(resource_id, UUID) or not isinstance(anonymous_session_id, UUID):
                return False
            if flow_id is not None and not isinstance(flow_id, UUID):
                return False
            if candidate_id is not None and not isinstance(candidate_id, UUID):
                return False
            if decision_version_id is not None and not isinstance(decision_version_id, UUID):
                return False
            if stage is not None and stage not in EventStage.__args__:
                return False
            if error_category is not None and error_category not in ErrorCategory.__args__:
                return False
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


def safe_emit_client(sink: object, event: ClientProductEvent) -> bool:
    try:
        return bool(sink.emit_client(event))
    except Exception:
        return False


def safe_emit_server(sink: object, **fields: object) -> bool:
    try:
        return bool(sink.emit_server(**fields))
    except Exception:
        return False


_STORED_FIELDS = frozenset({
    "schema_version", "event_id", "event_name", "anonymous_session_id", "occurred_at",
    "flow_id", "candidate_id", "decision_version_id", "stage", "duration_ms",
    "error_category", "metadata", "authority", "received_at",
})
_STORED_REQUIRED_FIELDS = frozenset({
    "schema_version", "event_id", "event_name", "anonymous_session_id", "occurred_at",
    "metadata", "authority", "received_at",
})


def _is_canonical_uuid(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False


def _is_aware_iso_timestamp(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except ValueError:
        return False


def validate_stored_event(record: object) -> dict[str, object] | None:
    """Validate a JSONL record before export; reject rather than repair it."""
    if (
        not isinstance(record, dict)
        or set(record) - _STORED_FIELDS
        or not _STORED_REQUIRED_FIELDS.issubset(record)
    ):
        return None
    authority, name = record.get("authority"), record.get("event_name")
    if authority == "client" and name not in CLIENT_EVENT_NAMES:
        return None
    if authority == "server" and name not in SERVER_EVENT_NAMES:
        return None
    if authority not in {"client", "server"} or record.get("schema_version") != 1:
        return None
    try:
        if not _is_canonical_uuid(record["event_id"]) or not _is_canonical_uuid(record["anonymous_session_id"]):
            return None
        for field in ("flow_id", "candidate_id", "decision_version_id"):
            if record.get(field) is not None and not _is_canonical_uuid(record[field]):
                return None
        if not _is_aware_iso_timestamp(record["occurred_at"]) or not _is_aware_iso_timestamp(record["received_at"]):
            return None
        EventMetadata.model_validate(record.get("metadata") or {})
        if record.get("stage") is not None and record["stage"] not in EventStage.__args__:
            return None
        if record.get("error_category") is not None and record["error_category"] not in ErrorCategory.__args__:
            return None
        duration = record.get("duration_ms")
        if duration is not None and (not isinstance(duration, int) or isinstance(duration, bool) or not 0 <= duration <= 86_400_000):
            return None
    except (KeyError, TypeError, ValueError):
        return None
    return record
