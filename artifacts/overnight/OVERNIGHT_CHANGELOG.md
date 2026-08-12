# Overnight Changelog

Date: 2026-08-13

## P0-A — Need / Decision invalidation

- Before: saving a Need only changed local display state.
- Observed problem: old Decision, questions, replies, Answer, and Delta could survive.
- Root cause: immutable backend snapshots and mutable local Need were not closed as one transition.
- Change: PATCH server Need first; then clear all derived decision state, preserve extraction, and return to candidates.
- After: a new Need can only reach Result through a fresh analysis.
- Evidence: `invalidateDecisionState` and `saveSelectionNeed`.
- Tests: frontend invalidation and server-first wiring tests PASS; PostgreSQL stale-decision test SKIPPED without `TEST_DATABASE_URL`.

## P0-B — Merchant sample semantics

- Before: positive substrings could override negation; unknown product evidence could conflict.
- Observed problem: false merchant evidence and unnecessary conflicts.
- Root cause: token ordering and an over-broad comparison.
- Change: negation-first closed vocabulary; explicit/known/opposite-only conflict.
- After: negative, positive, unknown, same, and opposite cases are deterministic.
- Evidence: fake merchant reasoning provider.
- Tests: parser matrix PASS.

## P0-C — Answer source separation

- Before: inferred and merchant evidence entered product `known_facts`.
- Observed problem: “商品页目前能确认” overstated its source.
- Root cause: status filtering happened before source separation.
- Change: product explicit only in `known_facts`; merchant explicit only in `merchant_facts`; inferred excluded.
- After: each visible fact retains its correct source class.
- Evidence: answer mapper.
- Tests: mixed-source contract test PASS.

## P1-A — Sensory fit consistency

- Before: ranking and labels read different score components; “低火味” could trigger broad “火味”.
- Observed problem: Decision and explanation could disagree.
- Root cause: duplicate presentation logic and token precedence.
- Change: shared summed sensory presentation signal; low-fire avoidance recognized first.
- After: fresh/low-fire and rich/heavy cases order and explain consistently.
- Evidence: decision evaluator and frontend adapter.
- Tests: decision regressions and adapter tests PASS.

## P1-B — Budget upper bound

- Before: `150–300` capped at 150.
- Observed problem: false over-budget classification.
- Root cause: first-number regex.
- Change: common budget text uses the maximum numeric amount as the ceiling.
- After: `150–300`, `150-300`, and `300以内` all cap at 300.
- Evidence: `_budget_fit`.
- Tests: parametrized 250/350 cases PASS.

## P1-C — Active-flow recovery

- Before: transient screens collapsed to candidates and did not recover by server state.
- Observed problem: analysis progress or rejudge Delta context disappeared after F5.
- Root cause: snapshot omitted current Job status and recovery routing was too broad.
- Change: snapshot includes current Job status; frontend derives Analysis/Result/Rejudge from authoritative state while preserving cold-start Home.
- After: active processing and completed Delta have distinct recovery paths.
- Evidence: repository snapshot, adapter recovery helper, frontend resume function.
- Tests: routing/recovery tests PASS; real browser and PostgreSQL E2E remain separate gates.

## Recorded but not changed

- Skip onboarding may still expose populated default O1/O2 as low-confidence preference references (P1).
- Server candidate reorder may change the visible candidate because the numeric index, not candidate id, is preserved (P1).
- Merchant reply overlay and unsubmitted textarea are not restored automatically (P1 audit finding; explicitly deprioritized in this repair).
- At 390×568 the Home primary CTA begins below the initial viewport (P2); no horizontal overflow was observed at the audited larger viewports.
