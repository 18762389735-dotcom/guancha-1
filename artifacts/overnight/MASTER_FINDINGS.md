# Master Findings

Date: 2026-08-13  
Selected autonomous ceiling: exactly 3 P0 + 3 P1.

| ID | Severity | Problem | Resolution | Commit | Verification |
|---|---|---|---|---|---|
| P0-A | P0 | Need edit could pair a new premise with old Decision/questions/Delta | Server-first Need update, invalidate all derived client state, return to candidates | `9b95b77` | Frontend behavior tests PASS; DB invalidation test skipped without test DB |
| P0-B | P0 | Merchant sample negation and conflict boundaries were unsafe | Negation-first parse; conflict only for explicit, known, opposite product evidence | `9d91873` | Pure parser tests PASS |
| P0-C | P0 | Product, merchant, and inferred facts mixed in Answer Contract | Strict source/status separation | `9d91873` | Mapper tests PASS |
| P1-A | P1 | Result fit text disagreed with explicit sensory ordering; low-fire wording could reverse | Shared sensory display score and low-fire precedence | `a95a91d` | Backend + frontend tests PASS |
| P1-B | P1 | Budget range used first number as ceiling | Common range/以内 parser uses upper bound | `a95a91d` | Parametrized tests PASS |
| P1-C | P1 | Reload lost analysis/rejudge state | Snapshot job status + server-authoritative screen recovery | `9b95b77` | Pure/frontend tests PASS; DB/browser E2E not automated |

## Deduplicated remaining issue

| ID | Severity | Issue | Reason not fixed |
|---|---|---|---|
| P2-01 | P2 | Unsubmitted merchant textarea is lost on reload | Does not corrupt evidence or block the flow; outside selected ceiling |

## Audit verdict before independent review

The selected code-level defects are fixed and the non-DB suites pass. This is not a deployment claim: PostgreSQL integration and browser acceptance remain separate evidence gates.
