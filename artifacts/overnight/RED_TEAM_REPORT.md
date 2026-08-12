# Independent Red Team Report

Date: 2026-08-13  
Final reviewed code HEAD: `ec63be4`

## Verdict

**PASS in the locally executable scope.** No open P0/P1 regression directly caused by the selected repairs remains. This is not a PostgreSQL or deployment PASS.

## Adversarial review history

### Cycle 0 — FAIL at `5b4affb`

- P0: an existing remote session with an unconfigured API could save the new Need locally and show success without PATCH.
- P0: repository persistence used a broader product conflict rule than the parser, so unknown/inferred/empty evidence could still become conflict.
- P1: recovery lacked a current server-side session Decision Job lineage.

Resolution: `cc3f6d6` introduced a server-gated Need transition, one explicit-product conflict helper used by both persistence paths, and server-authoritative session Decision Job recovery.

### Cycle 1 — FAIL at `cc3f6d6`

- P0 reproduction: the new session Decision Job SQL was mistakenly inserted in `answer_contract_inputs_for_session` and read an undefined `session`; `selection_snapshot_for_client` returned an undefined `session_decision_job`. Answer/Snapshot could return 500.

Resolution: `ec63be4` moved the query into Snapshot scope and added Stub-cursor method tests that fail without the correct placement.

### Cycle 2 — Final PASS at `ec63be4`

- Need transition: existing session requires configured API and successful PATCH; failure preserves old state. No-session first Need remains locally usable.
- Merchant conflict: pure helper covers unknown, inferred, empty, same, opposite, and non-product sources.
- Recovery: current server session Decision Job controls Analysis/Result/failed recovery; Answer no longer executes Snapshot SQL.
- Tests: frontend 41/41; backend 205 passed / 76 database-gated skips; Python compile, Node syntax, and diff checks passed.

## Unverified boundary

No isolated `TEST_DATABASE_URL` or project-local Python environment was available. PostgreSQL SQL execution, transaction persistence, and full API chain were not run. These are explicit limits, not PASS.
