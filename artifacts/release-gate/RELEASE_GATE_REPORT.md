# GUANCHA RELEASE GATE CLOSURE

## Executive Summary

Phase 15 closes the runnable code gates for client persistence privacy, replay transition edges, state identity and analytics event validation. Final verdict:

**CODE_GATES_CLOSED_DB_BROWSER_VALIDATION_REQUIRED**

This is not a production-ready or fully validated release claim. PostgreSQL same-key replay/event behavior and the real browser flow remain BLOCKED in this environment.

## Starting Commit

`1d9d606` (`docs: finalize observable beta readiness report`).

## Final Implementation Commit

`cabc959` (`fix: close final client risk boundaries`). The evaluation/report commit follows this implementation boundary.

## P0 Closed

- Client persistence is projection-based and schema-bounded; selection bridge v3 never clones unknown client or server trees.
- Legacy `guancha-prototype-v2` migration is privacy-first, uses per-store serializers, prefers existing new stores, and always clears the legacy key.
- Need, answer/questions/delta and other server presentation state resume from server snapshot paths rather than long-lived unsafe client trees.

## P1 Closed

- Preference evidence, UI session, warehouse, journal and minimal selection history have independent allowlist serializers and load-time backing rewrites.
- Warehouse risk values use a semantic closed set; extraction cannot persist `raw_text` as a risk.
- Session/candidate/image transition events are emitted only at repository `created` edges; staged analysis emits only for newly accepted jobs.
- Task runners de-duplicate pending/active `job_id`s and release them on completion, failure and shutdown.
- Onboarding skip no longer creates pseudo-preferences; active candidate identity survives reorder/add/remove/slide/reload; recommended and selected history semantics are separate.
- Stored event export rejects coerced schema versions and non-object metadata before safe export.

## Privacy

Independent privacy red team verdict: **PASS**, P0 0 / P1 0. Evidence is in `artifacts/release-gate/PRIVACY_RED_TEAM.md`.

## Persistence Contract

`docs/CLIENT_PERSISTENCE_CONTRACT.md` is the normative client contract. Selection, UI, preference evidence and post-purchase stores are separate closed projections. IndexedDB images are explicitly temporary cache data.

Privacy-first migration has one deliberate semantic loss: old `history.winner` contained a free-form tea name and cannot be safely mapped to a candidate A-E label. It is dropped rather than guessed. Recommended identity is never inferred from legacy selected/winner data.

## Replay / Idempotency

Runnable unit/service tests verify repository `created` propagation, accepted-job gating and in-process job de-duplication. They do **not** prove database transaction exactly-once behavior.

`REPLAY-EDGE-01` is therefore named as created-edge propagation only. `REPLAY-DB-01` contains the real same-key session/candidate/image API cases and is **BLOCKED** without `TEST_DATABASE_URL`. GET/result/snapshot/current-decision/delta paths do not create transition events in the reviewed code.

## State Integrity

Server candidate IDs are preferred as stable anchors. Reorder preserves the active candidate; questions, replies, rejudge and tea-stock actions stay attached to that identity. Local history records AI-priority and user-selected labels separately, including Top A / Select B.

## AI Eval

Fixed set: **30 total; 26 PASS; 0 FAIL; 4 BLOCKED**. The four database integration cases are not counted as PASS. The runner makes no real Provider call and does not claim live vision accuracy. Exact cases are in `backend/evaluation/ai_eval_cases.json`; generated evidence is in `artifacts/observable-beta/AI_EVAL_RESULTS.md`.

## Automated Tests

- Frontend full suite: **61/61 PASS**.
- Backend full runnable suite: **228 PASS, 76 SKIPPED**; skips are database-gated.
- Privacy final focused suite: **26/26 PASS**.
- AI manifest: **1 PASS**; runner: **26 PASS, 0 FAIL, 4 BLOCKED**.
- Node syntax, Python compile and diff checks: PASS.
- Secret scan found no user secret; the only URL-like database credential was the known local test value in `.github/workflows/baseline.yml`.

## Database Status

**BLOCKED.** `TEST_DATABASE_URL` was absent. The 76 skipped backend tests and AI database cases include the PostgreSQL transaction and real same-key session/candidate/image replay boundary. No database was started or mutated.

## Browser Status

**BLOCKED.** The in-app browser runtime was present and selectable. A local host returned HTTP 200 outside the browser, but browser navigation to `127.0.0.1:8765` consistently returned `ERR_CONNECTION_REFUSED`/URL-policy error-page behavior. The tab was finalized, PID 31564 stopped, and the port was left without a listener. This is not a browser PASS.

## Remaining Blockers

- Run the database suite against an isolated PostgreSQL `TEST_DATABASE_URL`, including `REPLAY-DB-01`, and inspect event rows for exactly-once behavior.
- Run the acceptance path in a browser environment that can reach the local app host.

## Remaining P2

- Privacy: IndexedDB pending-image cache has no explicit TTL/eviction policy.
- State migration: legacy free-form tea-name history is intentionally lost under the new privacy contract.
- UI/product items explicitly outside Phase 15 remain open, including demo seeding, reply overlay, aroma-provider/policy presentation and broader question/UI refinement.

## Files Changed

Phase 15 changed the focused frontend persistence/adapters/app state path, Phase 2 routes/services/task runners/product-event validation, targeted frontend/backend tests, AI manifest/matrix/taxonomy/results, the persistence contract, and these release-gate artifacts. No dependency, migration, provider, database schema or deployment change was made.

## Commits

- `29549ae` privacy persistence boundary
- `78cbbac` replay transition edges
- `c09d135` candidate/preference identity
- `1e427e0` analytics metadata validation
- `dee97d8` release-gate regressions
- `932bcd0` remaining persistence projections
- `c704326` manual runner shutdown release
- `24b3d67` post-purchase text boundary
- `cabc959` final client risk boundaries

## Recommended Human Action

Keep the release gate closed for external beta until the isolated PostgreSQL replay suite and reachable-browser acceptance flow both pass. If both pass without new P0/P1 findings, update this verdict with those environment-specific evidence links; do not infer readiness from the runnable-only results here.

