# Product Analytics Spec v1

## Purpose and boundary

This telemetry exists to support a small Beta study of the frozen competition flow. It does not score users, feed Decision logic, retain screenshots or conversation text, or claim conversion before real sessions exist. Event delivery is always fail-open.

Storage is append-only JSONL. By default the backend writes structured records through `guancha.product_event`; setting `GUANCHA_PRODUCT_EVENT_LOG_PATH` writes one JSON object per line to that local path. No database migration or third-party SDK is involved.

## Main funnel

`start_selection` → `need_submitted` → `candidate_image_added` → `analysis_completed` → `merchant_question_viewed|merchant_question_copied` → `merchant_reply_submitted` → `rejudge_completed` → `candidate_selected`

Question viewed, question copied, and merchant reply submitted are separate intentions and must not be collapsed.

## Schema v1

| Field | Required | Meaning |
|---|---:|---|
| `event_id` | yes | UUID; server events deterministically derive it from event name + resource. |
| `event_name` | yes | Closed event vocabulary below. |
| `anonymous_session_id` | yes | Per-tab/sessionStorage UUID; not the long-lived business client id. |
| `occurred_at` | yes | Client or server occurrence time. |
| `received_at` | server record | Server receipt time; server-owned. |
| `authority` | server record | `client` or `server`; server-owned. |
| `flow_id` | no | Temporary selection-flow UUID. |
| `candidate_id` | no | Server UUID only; never candidate name. |
| `decision_version_id` | no | Server UUID only. |
| `stage` | no | Bounded machine stage. |
| `duration_ms` | no | 0–86,400,000. |
| `error_category` | no | Bounded machine error code, never message/stack. |
| `metadata` | yes | Strict allowlist below. |

Allowed metadata only: `candidate_count`, `image_count`, `has_budget`, `has_sensory_need`, `question_field`, `question_count`, `action_bucket`, `processing_mode`, `failure_category`, `onboarding_status`, `source`, `screen`. Unknown, nested, or oversized metadata is rejected/dropped.

## Authority and events

Client interaction events: `app_open`, `start_selection`, `onboarding_started`, `onboarding_completed`, `onboarding_skipped`, `need_started`, `candidate_result_viewed`, `merchant_question_viewed`, `merchant_question_copied`, `merchant_reply_started`, `candidate_selected`, `tea_stock_added`, `flow_abandoned`.

Server outcome events: `need_submitted`, `candidate_created`, `candidate_deleted`, `candidate_image_added`, `candidate_image_removed`, `analysis_started`, `analysis_completed`, `analysis_failed`, `merchant_reply_submitted`, `merchant_reply_unusable`, `rejudge_started`, `rejudge_completed`, `rejudge_failed`.

The public `POST /api/v1/events` accepts client interaction names only. A client attempt to send a server outcome is rejected. Server terminal events are emitted only after the corresponding repository success/failure boundary. Deterministic server IDs make polling/replay export-safe.

Current implementation covers the main funnel and resource mutations. `flow_abandoned` is currently observed only through the explicit return-home path; browser/tab disappearance is intentionally not inferred. `merchant_reply_unusable` is emitted during rejudge parsing, not from client opinion.

## Privacy denylist

Never record Need text, merchant raw text or summaries, screenshot/blob/base64 data, file path or hash, candidate/product names, phone/WeChat/name, arbitrary identifiers, IP/user-agent/URL, cookies, authorization headers, tokens/keys, database URLs, exception messages, or stack traces. Analytics data is distinct from business MerchantReply storage.

The top-level MerchantReply bridge path persists only reply IDs/status/timestamps and legacy reads rewrite that path. Independent re-review found that allowed complex selection fields can still carry nested MerchantReply raw/text/summary values; therefore the whole-bridge privacy boundary is implemented only partially and is not validated for Beta use.

## Operations

```powershell
python scripts/export_product_events.py events.jsonl events.csv
python scripts/summarize_product_funnel.py events.jsonl
```

The exporter skips malformed lines, keeps the first occurrence of each `event_id`, sorts by occurrence time, and emits allowlisted columns only. The summary reports event counts, unique session counts, and raw sequential stage counts. It does not output percentages or statistical claims.

Current validation status: implemented, not Beta-validated. Phase 2 replay can still duplicate raw JSONL/enqueue work, and export metadata validation can coerce invalid falsey/non-strict values. See `artifacts/observable-beta/PRIVACY_REVIEW.md`.
