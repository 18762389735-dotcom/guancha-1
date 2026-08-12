# GUANCHA OBSERVABLE BETA REPORT

## Executive Summary

Phase 14 produced a minimal anonymous JSONL analytics layer, a repeatable 27-case AI evaluation harness, CSV/funnel tools, and a user-validation toolkit. Automated runnable tests pass, but independent Privacy re-review remains FAIL and required browser/database regression is blocked. This branch is not ready for participant recruitment or user validation.

## Starting Commit

`81566de`

## Final Commit

Final product/test code commit: `26f9fe5`. The final report-only documentation commit is created after this report is written.

## Previous Overnight Status

- Previous final verdict: `COMPLETE_WITH_REMAINING_ISSUES`.
- Previous deployment recommendation: `DO_NOT_DEPLOY`.
- Previous Browser result: FAIL / NO-GO because the real PostgreSQL decision chain was unavailable.

## Analytics Architecture

- Browser interaction events use a per-tab `sessionStorage` UUID and temporary flow UUID.
- `POST /api/v1/events` accepts only the client event allowlist.
- Server-authoritative outcomes are emitted at backend boundaries.
- The standard-library sink writes structured JSONL to logging/stdout or optional `GUANCHA_PRODUCT_EVENT_LOG_PATH`.
- Analytics is fail-open and is not awaited by the product flow.
- No database migration, third-party analytics SDK, Dashboard, or direct Provider integration was added.

This architecture is implemented but not validated for Beta use because Privacy and replay findings remain open.

## Events Implemented

26 event names:

- 13 client interaction events: `app_open`, `start_selection`, `onboarding_started`, `onboarding_completed`, `onboarding_skipped`, `need_started`, `candidate_result_viewed`, `merchant_question_viewed`, `merchant_question_copied`, `merchant_reply_started`, `candidate_selected`, `tea_stock_added`, `flow_abandoned`.
- 13 server-authoritative events: `need_submitted`, `candidate_created`, `candidate_deleted`, `candidate_image_added`, `candidate_image_removed`, `analysis_started`, `analysis_completed`, `analysis_failed`, `merchant_reply_submitted`, `merchant_reply_unusable`, `rejudge_started`, `rejudge_completed`, `rejudge_failed`.

## AI Eval Coverage

- 27 machine-readable cases across Extraction Safety, Evidence Safety, Sensory Translation, Current Need, Question, Merchant Reply, Rejudge/Delta, Decision/Answer, and State Safety.
- Deterministic tests and fixed structured Extraction fixtures are orchestrated through existing pytest node IDs.
- Database-dependent cases are explicitly BLOCKED rather than counted as PASS.
- Fixture pipeline coverage does not establish live vision Provider quality.

## AI Eval Result

- Total: 27.
- PASS: 24.
- FAIL: 0.
- BLOCKED: 3 without `TEST_DATABASE_URL`.
- Real Provider calls: 0.

This is the current fixed-evaluation-set result, not real-world AI accuracy.

## Failure Categories

The harness uses the documented closed failure taxonomy, including Extraction, evidence source, marketing claim, sensory, Need/budget, question, merchant reply, rejudge, Decision/Answer, state, Provider, and database categories. A PASS means the assigned regression test passed; it does not mean a failure occurred.

## Privacy Result

**FAIL / NO-GO.**

The first review found five issues. Commit `26f9fe5` repaired the authorized top-level persistence, closed vocabulary, fail-open, transition, and exporter boundaries. Re-review still found:

1. P0 nested selection fields can persist merchant raw/text/summary in localStorage.
2. P1 Phase 2 replay can duplicate raw events and enqueue work.
3. P2 exporter metadata validation coerces invalid types.

The phase fix budget is exhausted. No further code change was made during reporting.

## User Test Toolkit

Delivered document assets:

- Beta task plan for 5–10 Chinese tea beginners.
- Anonymous observation template.
- 10–15 minute interview guide.
- Exactly five product hypotheses.
- Metrics dictionary with explicit definitions and limitations.

These are preparation assets only. Participants: 0; completed user sessions: 0.

## Automated Tests

- Node syntax check: PASS.
- Frontend full suite: 48 passed, 0 failed.
- Backend runnable suite: 223 passed, 76 skipped because `TEST_DATABASE_URL` was absent.
- AI eval: 24 PASS, 0 FAIL, 3 BLOCKED.
- Focused privacy/analytics tests: included in the totals above.
- `git diff --check`: PASS.
- Secret scan: PASS; no real credential detected.

Skipped/BLOCKED cases are not counted as PASS.

## Browser Regression

`BLOCKED`

- The in-app browser had no available browser instance.
- Localhost fake-provider health check passed.
- No safe database connection was available for the real main chain.
- Full Home → Need → candidate → analysis → question → merchant reply → rejudge → selection UI regression was not executed.
- 390/430/1280 viewport smoke, console/network/localStorage inspection, analytics-success/failure interaction, duplicate-render observation, and performance evidence remain BLOCKED.
- No screenshot or browser measurement was fabricated.
- The previous overnight Browser verdict was FAIL / NO-GO.

## Files Changed

The branch adds or updates:

- Frontend analytics, persistence sanitation, API headers, event hooks, and focused tests.
- Backend event schema/sink/API hooks, service transition hooks, evaluation manifest/runner, and focused tests.
- JSONL-to-CSV and raw funnel scripts.
- Analytics, eval, taxonomy, metrics, user study, hypotheses, evidence, privacy, readiness, and report documentation.

The user-owned documentation deletion/rename and untracked `__pycache__` were not staged or modified.

## Commits

- `b712d3a` — `feat: add privacy-safe product telemetry`
- `27bca8f` — `test: make AI evaluation repeatable`
- `68fc929` — `docs: add observable beta validation toolkit`
- `26f9fe5` — `fix: close telemetry privacy boundaries`
- Final report-only commit — `docs: finalize observable beta readiness report`

No push, merge, deployment, dependency installation, database migration, or real Provider call occurred.

## Known Limitations

- Privacy P0: nested selection bridge values can retain merchant raw text.
- Analytics P1: several Phase 2 replay paths can append duplicate raw JSONL and re-enqueue extraction.
- Analytics P2: exporter metadata validation is not fully strict and can coerce invalid values.
- Result-view edge state can under-count re-entry to the same candidate/decision.
- Three database eval cases and the complete browser/database chain remain unexecuted.
- Fixed Extraction fixtures do not validate live vision extraction.
- There are no real user observations, conversion rates, performance measurements, or production-scale claims.

## Beta Readiness

`NOT_READY_FOR_USER_VALIDATION`

## Recommended Next Human Action

Handle only these blockers, in this order:

1. Close persistence across the entire selection bridge, including nested complex fields, and re-run the privacy red team.
2. Preserve repository creation/enqueue edges through Phase 2 routes and prove idempotent replay produces no duplicate raw events or work.
3. Provision an isolated `TEST_DATABASE_URL` and a usable browser, then run the full fake-provider chain at required viewports with analytics available and deliberately unavailable.

Do not recruit users or add product features before those gates pass.
