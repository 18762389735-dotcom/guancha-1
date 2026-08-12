# Master Findings

Date: 2026-08-13  
Selected autonomous ceiling: exactly 3 P0 + 3 P1.

| ID | Severity | Problem | Resolution | Commit | Verification |
|---|---|---|---|---|---|
| P0-A | P0 | Need edit could pair a new premise with old Decision/questions/Delta | Server-first Need update, invalidate all derived client state, return to candidates | `9b95b77`, `cc3f6d6` | Frontend behavior tests PASS; DB invalidation test skipped without test DB |
| P0-B | P0 | Merchant sample negation and conflict boundaries were unsafe | Negation-first parse; conflict only for explicit, known, opposite product evidence | `9d91873`, `cc3f6d6` | Pure parser/helper tests PASS; DB persistence tests skipped |
| P0-C | P0 | Product, merchant, and inferred facts mixed in Answer Contract | Strict source/status separation | `9d91873` | Mapper tests PASS |
| P1-A | P1 | Result fit text disagreed with explicit sensory ordering; low-fire wording could reverse | Shared sensory display score and low-fire precedence | `a95a91d` | Backend + frontend tests PASS |
| P1-B | P1 | Budget range used first number as ceiling | Common range/以内 parser uses upper bound | `a95a91d` | Parametrized tests PASS |
| P1-C | P1 | Reload lost analysis/rejudge state | Snapshot job status + server-authoritative screen recovery | `9b95b77`, `cc3f6d6`, `ec63be4` | Pure/Stub/frontend tests PASS; DB/browser E2E blocked |

## Deduplicated remaining issues

| ID | Severity | Issue | Reason not fixed |
|---|---|---|---|
| REM-P1-01 | P1 | Skip onboarding can retain default O1/O2 preference references | Found by independent state audit after the six-item selection; outside ceiling |
| REM-P1-02 | P1 | Server reorder preserves index rather than active candidate identity | Found by independent state audit after the six-item selection; outside ceiling |
| REM-P1-03 | P1 | Merchant reply overlay/draft does not reopen automatically after reload | Explicitly deprioritized behind analysis and Delta recovery; no evidence corruption |
| REM-P2-01 | P2 | 390×568 Home primary CTA starts below initial viewport | Visual friction, no horizontal overflow or hard blocker |
| REM-P1-04 | P1 | Seed tea store/journal can look like real user data | Requires product-state clarification, outside selected fixes |
| REM-P1-05 | P1 | History conflates AI recommendation and final user choice | Data semantics change deferred |
| REM-P0-01 | P0 / NO-GO | Full merchant reply raw text is persisted in localStorage | Privacy blocker; must be first next iteration fix |
| REM-P1-06 | P1 | Aroma enum/concept levels are mixed | AI contract normalization remains |
| REM-P1-07 | P1 | Delta risk added/resolved semantics need real DB validation | PostgreSQL E2E unavailable |
| REM-P1-08 | P1 | Question ordering may privilege completeness over preference/value | Needs targeted eval fixtures |
| REM-P1-09 | P1 | Live Provider marketing-schema safety is unverified | No real Provider call ran |
| REM-P1-10 | P1 | Inferred evidence may still enter hard decision inputs | Requires explicit decision-policy review |
| REM-P2-02 | P2 | Vague merchant replies have limited recovery coverage | Expand fixtures later |
| REM-P2-03 | P2 | Fixed CTA overlap, sub-44px targets, decorative leaf over edit control | Browser/a11y debt |
| REM-P2-04 | P2 | Config/favicon 404s and oversized empty-state PNG | Reliability/performance debt |

## Final audit verdict

The selected code-level defects pass the final Red Team in the locally executable scope. Deployment remains blocked by the privacy finding and the absence of real PostgreSQL/browser core-chain verification.
