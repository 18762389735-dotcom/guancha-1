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

## GC-P1-04

- Severity: P1
- Screen / Flow: Skip onboarding → Result explanation
- Observed behavior: skipped users still inherit default O1/O2 selections, so the page can describe preferences the user never supplied.
- Expected behavior: skip means no preference reference; only the current Need should guide the explanation.
- Why this matters: a fabricated personal reference weakens trust even when it is low confidence.
- Evidence: read-only state audit; `defaultState` contains populated O1/O2 values and preference presentation reads them.
- Recommended minimal fix: on skip, store empty O1/O2 or suppress preference references by onboarding status.
- Status: NOT FIXED — outside the selected ceiling.

## GC-P1-05

- Severity: P1
- Screen / Flow: Result carousel after server ordering
- Observed behavior: `applySessionDecision` reorders candidates but preserves the numeric active index, so the visible candidate identity can change silently.
- Expected behavior: preserve the active candidate id across server reorder.
- Why this matters: a user reviewing candidate B can be moved to a different card without an explicit action.
- Evidence: read-only state audit of the reorder path.
- Recommended minimal fix: capture active candidate id before reorder and resolve its new index afterward.
- Status: NOT FIXED — outside the selected ceiling.

## GC-P2-02

- Severity: P2
- Screen / Flow: Home at 390×568
- Observed behavior: the primary CTA is below the initial viewport while fixed navigation appears first.
- Expected behavior: the core start action should be visible or clearly discoverable on short mobile screens.
- Why this matters: adds first-use friction but does not block scrolling or corrupt the flow.
- Evidence: read-only browser geometry audit; no horizontal overflow at 390×844, 430×844, or 1280×900.
- Recommended minimal fix: evaluate only after Beta data; avoid an overnight layout rewrite.
- Status: NOT FIXED — visual P2.

## Remaining product findings (deduplicated)

### GC-P1-06 — Seed tea store and journal look like user data

- Severity: P1
- Screen / Flow: Tea store / journal on first use
- Observed behavior: the prototype ships populated tea and brew records before the user creates any.
- Expected behavior: demo content must be unmistakably labelled or isolated from real user history.
- Why this matters: users can mistake seed content for their own saved choices.
- Evidence: populated `defaultState.warehouse` and `defaultState.journalRecords`.
- Recommended minimal fix: use an explicit demo-data banner or empty first-user state.
- Status: NOT FIXED.

### GC-P1-07 — Historical recommendation and user selection can be conflated

- Severity: P1
- Screen / Flow: Selection history / tea store
- Observed behavior: local history emphasizes the selected winner without retaining a sufficiently explicit distinction between AI recommendation and user choice.
- Expected behavior: store both “system suggested” and “user selected” as separate concepts.
- Why this matters: later review can falsely imply that the system recommended what the user independently chose.
- Evidence: local `addSelectionHistory` winner-centric record.
- Recommended minimal fix: split recommendation snapshot from final user action.
- Status: NOT FIXED.

### GC-P0-03 — Full merchant reply persisted in localStorage

- Severity: P0 / deployment blocker
- Screen / Flow: Merchant reply → browser persistence
- Observed behavior: complete `merchantReplies.raw_text` is saved in the selection bridge in localStorage.
- Expected behavior: sensitive natural-language replies remain server-side or are locally minimized/redacted with a clear retention policy.
- Why this matters: localStorage is broadly readable by same-origin scripts and persists beyond the immediate screen.
- Evidence: Browser privacy audit of the current persistence payload.
- Recommended minimal fix: persist reply ids/status only; fetch authorized reply detail from the server when needed.
- Status: NOT FIXED; `DO_NOT_DEPLOY`.
