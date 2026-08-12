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

## Responsive and browser limitation

Automated tests cover routing and state helpers, not rendered 390/430 px browser geometry. Browser acceptance must report its own result; this document does not claim a visual PASS.
