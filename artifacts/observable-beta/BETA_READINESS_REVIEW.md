# Observable Beta Readiness Review

## Final verdict

`NOT_READY_FOR_USER_VALIDATION`

## Readiness by area

| Area | Result | Evidence and boundary |
|---|---|---|
| Product core flow | BLOCKED | Localhost health passed, but no browser instance and no safe test database were available for the required Home → Need → candidate → analysis → question → reply → rejudge → selection regression. |
| AI evaluation | READY WITH LIMITATIONS | A 27-case repeatable harness reports 24 PASS, 0 FAIL, 3 BLOCKED. Fixed Extraction fixtures are not a live vision pipeline, and no real Provider call was made. |
| Analytics implementation | IMPLEMENTED, NOT VALIDATED | JSONL telemetry covers 26 event names (13 client + 13 server), but Phase 2 replay can duplicate raw records/enqueue and exporter metadata validation still coerces invalid types. |
| Failure taxonomy | READY FOR FIXED EVAL | Eval cases use the documented closed categories. This is failure classification coverage, not real-world model accuracy. |
| User test plan and toolkit | DOCUMENT READY | Task plan, observation template, interview guide, and five hypotheses exist. No participants were recruited and no study was run. |
| Metrics | DEFINED, NO OBSERVED VALUES | Six funnel metrics now state definition, event, denominator, interpretation, and limitation. No rate or North Star is claimed. |
| Privacy | FAIL / NO-GO | Nested allowed selection state can persist merchant raw text in localStorage. The independent re-review remains FAIL. |
| Browser regression | BLOCKED | The in-app browser exposed no usable browser instance. 390/430/1280 smoke, console/network/storage inspection, analytics-failure interaction, and full UI regression were not executed. |

## Blocking issues (maximum three)

1. **Privacy P0:** recursively nested merchant raw/text/summary values can survive in the selection bridge backing localStorage.
2. **Analytics integrity P1:** Phase 2 replay can duplicate raw JSONL transition records and extraction enqueue work because creation edges are not consistently preserved.
3. **Validation environment:** the required full browser flow remains unexecuted; no browser instance and no isolated `TEST_DATABASE_URL` were available.

The exporter metadata coercion finding remains recorded as P2 debt but is not promoted above the three release blockers.

## Decision rationale

The telemetry, eval harness, and research toolkit are useful implementation assets, but readiness requires more than their existence. A privacy P0 remains open and the real fake-provider/database/browser chain has not been demonstrated at this code commit. Recruiting participants now would expose private merchant text to local persistence and produce telemetry whose replay integrity is not yet reliable.

## Next review gate

Re-review only after the three blockers are handled in order: close the whole selection-bridge persistence boundary; preserve created/enqueued transition edges and prove raw-sink replay behavior; then run the complete fake-provider flow with an isolated database in a real browser at required viewports, including analytics endpoint failure.
