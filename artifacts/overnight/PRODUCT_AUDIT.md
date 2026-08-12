# Product Consistency Audit

Date: 2026-08-13  
Scope: Competition MVP code, current-state documentation, fixtures, and automated tests. This audit did not treat visual polish as P0.

## GC-P0-01

- Severity: P0
- Screen / Flow: Result / Rejudge → edit current Need
- Observed behavior: the edited Need could be displayed beside the previous Decision, questions, replies, and Delta.
- Expected behavior: changing the comparison premise invalidates every derived decision artifact and returns the user to candidates for a fresh analysis.
- Why this matters: a new Need paired with an old result is a false decision, not a cosmetic stale-state issue.
- Evidence: the former `save-needs` handler only changed local `state.need`; backend decisions are immutable snapshots.
- Recommended minimal fix: update the server Need first, clear local decision derivatives, preserve extraction, and return to candidates.
- Status: FIXED in `9b95b77`.

## GC-P0-02

- Severity: P0
- Screen / Flow: Result evidence sections
- Observed behavior: inferred and merchant evidence could enter `known_facts`, which is rendered under “商品页目前能确认”.
- Expected behavior: only explicit product claims appear there; merchant statements have their own qualified section.
- Why this matters: source mixing upgrades an inference or seller statement into a page-confirmed fact.
- Evidence: prior mapper accepted `{explicit, inferred}` before separating sources.
- Recommended minimal fix: filter by both information status and source.
- Status: FIXED in `9d91873`.

## GC-P1-01

- Severity: P1
- Screen / Flow: Result fit label and caveat
- Observed behavior: server ranking used `explicit_sensory_need_match`, while the label/caveat inspected only `need_match`.
- Expected behavior: ranking explanation and visible fit qualification use the same bounded sensory signal.
- Why this matters: the page could deny a real current-Need match that had already affected ordering.
- Evidence: `fitLabel` and `fitCaveat` previously ignored the explicit component.
- Recommended minimal fix: one shared presentation helper summing the two bounded components.
- Status: FIXED in `a95a91d`.

## GC-P1-02

- Severity: P1
- Screen / Flow: Need budget → Decision
- Observed behavior: `150–300` was read as a ceiling of 150.
- Expected behavior: common ranges and “以内” forms use the actual upper bound.
- Why this matters: a tea priced at 250 could be incorrectly marked over budget.
- Evidence: the former parser used only the first numeric match.
- Recommended minimal fix: extract numeric amounts and use the maximum as the ceiling.
- Status: FIXED in `a95a91d`.

## GC-P1-03

- Severity: P1
- Screen / Flow: Active reload
- Observed behavior: all transient screens were normalized to candidates; server snapshot recovery did not distinguish processing analysis from completed rejudge.
- Expected behavior: a reload resumes a server-confirmed active analysis or rejudge Delta, while an ordinary reopen stays Home.
- Why this matters: users lose the meaning and progress of the active flow after F5.
- Evidence: snapshot did not expose current job status and the frontend promoted candidates/analysis to result too broadly.
- Recommended minimal fix: expose job status in the snapshot and choose the screen from server state.
- Status: FIXED in `9b95b77`.

## GC-P2-01

- Severity: P2
- Screen / Flow: Merchant reply sheet reload
- Observed behavior: unsubmitted textarea content is not persisted.
- Expected behavior: optionally recover draft text during an active reply flow.
- Why this matters: a reload can lose typing, but does not corrupt a saved decision or block the core flow.
- Evidence: overlays are intentionally saved as `null` and the reply draft is not part of the selection bridge.
- Recommended minimal fix: defer; if implemented later, persist only a bounded local draft keyed by question id.
- Status: NOT FIXED — outside the selected 3 P0 + 3 P1 scope.
