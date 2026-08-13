# AI Failure Taxonomy

Status: current evaluation and privacy-safe analytics vocabulary, 2026-08-13. These are diagnostic categories, not product features or database enums.

| Failure type | Detection boundary | Default severity |
|---|---|---|
| EXTRACTION_MISS | Visible decision-relevant evidence remains unknown. | P1 |
| EXTRACTION_HALLUCINATION | Evidence contains a value unsupported by the screenshot. | P0 |
| EVIDENCE_SOURCE_ERROR | Product, merchant, user, or inferred evidence is attributed to the wrong source. | P0 |
| MARKETING_CLAIM_LEAK | Marketing language becomes verified taste, quality, or authenticity. | P0 |
| SENSORY_OVERCLAIM | A bounded interpretation becomes a certain drinking experience. | P0 |
| SENSORY_MISSING | Explicit evidence has no usable bounded sensory translation. | P1 |
| NEED_PRIORITY_ERROR | History or broad tokens override the current Need. | P0/P1 |
| BUDGET_PARSE_ERROR | Budget text is normalized to the wrong ceiling. | P1 |
| DECISION_ANSWER_MISMATCH | Visible explanation contradicts order, bucket, or components. | P0 |
| QUESTION_DUPLICATE | A question repeats known or synonymous information. | P1 |
| QUESTION_LOW_VALUE | Answers cannot change order, risk, action, or useful explanation. | P1 |
| MERCHANT_REPLY_PARSE_ERROR | Merchant text maps to the wrong normalized fact/status. | P0 |
| MERCHANT_CONFLICT_FALSE_POSITIVE | Unknown/empty product evidence is treated as an opposite fact. | P0 |
| REJUDGE_INCONSISTENT | V2 changes without relevant evidence or loses V1 inputs. | P0 |
| DECISION_STATE_STALE | A changed premise is paired with old derived artifacts. | P0 |
| STATE_RECOVERY_ERROR | Active server state resumes to the wrong screen. | P1 |
| COLD_START_ERROR | A normal reopen resumes an old active result. | P1 |
| MOBILE_UI_BLOCKER | Mobile geometry prevents a core action. | P0/P1 |
| PROVIDER_ERROR | Provider failure is hidden or promoted to success. | P0 |
| DATABASE_ERROR | Persistence breaks ownership, immutability, or recovery. | P0 |

## Engineering contract

- `backend/evaluation/ai_eval_cases.json` may only use values in this table.
- `backend/src/guancha_api/product_events.py` exposes the same closed `failure_category` vocabulary. Unknown values are rejected; free text is never substituted.
- An eval case records the earliest causal category. The category describes what a failure would mean; a PASS result does not claim that a failure occurred.
- Analytics may contain only the category token. It must not contain Need text, merchant text, screenshot data, candidate names, identifiers outside the schema, exception messages, stack traces, URLs, user-agent/IP values, or credentials.
- `BLOCKED` and pytest skips are never counted as PASS.

Phase 15 clarification: `STATE_RECOVERY_ERROR` also covers a replay or restore
path that repeats a server-authoritative transition or accepts the same queued
Job identity twice. This extends detection coverage; it does not create a new
failure category.
