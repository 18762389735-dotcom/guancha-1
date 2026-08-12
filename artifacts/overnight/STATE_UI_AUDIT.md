# State and UI Audit

Date: 2026-08-13

## State authority map

| State | Authority | Reload behavior after hardening |
|---|---|---|
| Cold start / normal reopen | Navigation timing + local active-flow flag | Home |
| Candidate uploads and jobs | Server snapshot | Candidates or Analysis |
| Current Decision | Server current Decision | Result |
| Rejudge in progress | Server rejudge Job | Rejudge |
| Completed rejudge | Server Decision Delta | Rejudge with Delta |
| Unsubmitted merchant textarea | Browser transient UI | Not recovered (P2) |

## Findings

### UI-P0-01 — New Need with old result

- Initial state: Result or Rejudge with Decision V1/V2 and possibly questions/Delta.
- Action: edit and save Need.
- Former error state: new Need plus old derived artifacts.
- Fixed path: server PATCH succeeds → decision artifacts clear → candidates → fresh analysis.
- Error path: PATCH failure keeps the existing state and shows a retry message; it does not present a false successful update.
- Acceptance: pure invalidation test and frontend wiring test pass.

### UI-P1-01 — Processing analysis reload

- Initial state: active selection, at least one current Job queued/processing.
- Fixed path: reload → conservative local candidates → server snapshot → Analysis → polling resumes.
- Acceptance: pure recovery test and frontend integration-source test pass.

### UI-P1-02 — Delta reload

- Initial state: current V2 plus Decision Delta.
- Fixed path: reload → server snapshot → Rejudge → Delta remains visible.
- Acceptance: pure recovery test passes.

### UI-P2-01 — Merchant draft reload

- Initial state: user typed but did not submit a merchant reply.
- Current behavior: overlay and draft are not persisted.
- Impact: recoverable typing loss, no stored evidence or decision corruption.
- Status: NOT FIXED by explicit scope choice.

### UI-P1-03 — Skip retains default preference references

- Initial state: user chooses “暂时跳过”.
- Current behavior: populated default O1/O2 values remain available to personal-fit presentation.
- Risk: the system can describe a preference the user never stated.
- Status: NOT FIXED; independent audit finding outside the selected six repairs.

### UI-P1-04 — Active candidate identity after reorder

- Initial state: user is viewing a candidate by numeric carousel index.
- Current behavior: server Decision order replaces the array while preserving the old index.
- Risk: the visible candidate can change silently.
- Status: NOT FIXED; independent audit finding outside the selected six repairs.

### UI-P2-02 — Short mobile Home CTA

- Viewport: 390×568.
- Current behavior: primary start CTA begins below the initial viewport; fixed navigation is visible first.
- Status: NOT FIXED; scroll remains possible and no horizontal overflow was observed.

## Responsive and browser limitation

Automated tests cover routing and state helpers, not rendered geometry. The read-only audit found no horizontal overflow at 390×844, 430×844, or 1280×900, but found the short-viewport CTA issue above. This is not a complete end-to-end browser PASS.
