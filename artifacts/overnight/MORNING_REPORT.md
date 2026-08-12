# GUANCHA OVERNIGHT REPORT

## 1. Executive Summary

The six selected Beta-hardening defects were repaired and passed final local Red Team, but the release is **NO-GO**: the real PostgreSQL decision chain was unavailable and complete merchant reply text is persisted in localStorage.

## 2. Mission and baseline

- Mission: systematic Competition MVP Beta hardening, not feature expansion.
- Product north star retained: translate professional tea language into explainable, askable, correctable pre-purchase decisions for Chinese tea beginners.
- Starting commit: `163a635`.
- Formal competition baseline: `05b0292`.
- Working branch: `codex/overnight-beta-hardening`.
- `GUANCHA_CORE_EXPERIENCE_V3.md`: requested by the mission but absent from the repository; no substitute was invented.

## 3. Final code commit

`ec63be4` before this report-only commit.

## 4. What Was Audited

Product consistency, evidence/answer boundaries, sensory and Need scoring, budget parsing, question/reply/rejudge logic, active-state recovery, cold start, mobile/desktop geometry, performance smoke, privacy/secret exposure, and existing deterministic fixtures/tests.

## 5. Issues Found and Fixed

Exactly 3 P0 + 3 P1 were selected:

| ID | Before | After |
|---|---|---|
| P0-A | New Need could coexist with old Decision/questions/Delta | Existing session requires successful PATCH; all derived state invalidates and returns to candidates |
| P0-B | Sample negation and persisted conflict boundaries were unsafe | Negation wins; only explicit, known, opposite product claims conflict |
| P0-C | Inferred/merchant facts could appear as product-confirmed | Product explicit and merchant explicit are rendered in separate sections; inferred is excluded |
| P1-A | Ranking and fit text used different sensory signals; low-fire wording could reverse | Shared bounded signal and corrected low-fire precedence |
| P1-B | `150–300` used 150 as ceiling | Range and “以内” use the correct upper bound |
| P1-C | Reload lost Analysis/Rejudge context | Current server Job/Decision/Delta controls recovery |

## 6. Red Team Result

Final: **PASS in locally executable scope** at `ec63be4`.

Two repair cycles were consumed. The first found Need false success, persistence conflict drift, and incomplete Decision Job recovery. The second found a P0 SQL query placement/NameError regression. Both were reproduced with executable tests and fixed. Real PostgreSQL remains unverified.

## 7. AI Evaluation

- Total cases: 27
- PASS: 24
- FAIL: 1 — merchant textarea draft does not recover on reload (accepted P2 debt)
- NOT_AUTOMATED: 2 — database-backed empty-question and aggregate-rejudge closure
- Real Provider calls: 0

## 8. Browser E2E

Verdict: **FAIL / NO-GO**.

| Scenario | Result |
|---|---|
| New user complete / skip | PASS |
| Reload, cold start, new tab, back/forward | PASS |
| No-session Need save | PASS |
| Existing real-session Need PATCH | BLOCKED |
| 1/2/5 candidates; 390, 430, 390×568, desktop | PASS for static UI |
| Real analysis → Evidence → Question → Reply → Rejudge → Delta → tea store | BLOCKED |
| Static POST failure | 501; UI displayed `request_failed` |

Blocker: PostgreSQL listened locally, but no usable `GUANCHA_DATABASE_URL`, project virtualenv, or approved connection was available. No dependency installation or database mutation was attempted.

## 9. Regression Tests

- Frontend: 41/41 PASS.
- Backend: 205 PASS, 76 SKIPPED because `TEST_DATABASE_URL` was absent.
- Python `py_compile` for repository: PASS.
- Node `--check app.js`: PASS.
- `git diff --check`: PASS.

The Python tests used an existing sibling project environment; no dependency was installed. Database skips are not counted as PASS.

## 10. Performance / Reliability

- Browser console: 0 errors, 0 warnings.
- Network: 14 requests; 12×200, public config 404, favicon 404.
- Approximate transfer: 1,081,245 bytes.
- Empty-state PNG: 858,766 bytes, about 79% of observed bytes.
- Navigation timing / LCP: unavailable.
- Fixed CTA overlaps content by about 6 px.

## 11. Privacy / Security

- **FAIL / NO-GO:** complete `merchantReplies.raw_text` is persisted in localStorage.
- Full screenshot Blob is stored in IndexedDB; a 160×160 preview in localStorage is proportionate, but retention still needs an explicit policy.
- No API key, cookie, telemetry payload, or secret value leakage was observed.
- No telemetry was added.

## 12. Remaining Issues

Deployment blocker:

- Remove full merchant reply raw text from localStorage; persist identifiers/status only and fetch authorized detail.

P1:

- Skip onboarding retains default pseudo-preferences.
- Seed tea store/journal can look like user data.
- History conflates AI recommendation with user selection.
- Candidate identity can change after server reorder because numeric index is preserved.
- Reply/rejudge overlay does not fully restore.
- Aroma enum/concept levels are mixed.
- Delta risk semantics require real V1/V2 database validation.
- Question ordering may privilege completeness over preference/counterfactual value.
- Live Provider marketing-schema safety is unverified.
- Inferred evidence may still enter hard decision inputs.

P2:

- Merchant textarea draft is lost on reload.
- Vague merchant replies have limited recovery coverage.
- Short-screen CTA/6 px overlap, sub-44 px targets, decorative leaf over Need edit.
- Public config/favicon 404 and oversized empty-state PNG.

## 13. Files Changed

Product/test changes are limited to `app.js`, frontend adapters/tests, backend answer/decision/reply/repository modules and focused tests. Audit assets are under `artifacts/overnight/`; evaluation assets are `docs/AI_EVAL_MATRIX.md` and `docs/AI_FAILURE_TAXONOMY.md`.

User-owned documentation rename and untracked `__pycache__` were not staged or modified.

## 14. Git Commits

- `9d91873` fix: enforce merchant and answer evidence boundaries
- `a95a91d` fix: align sensory fit and budget ceilings
- `9b95b77` fix: invalidate stale decisions and recover active flows
- `b40f93f` docs: record overnight beta hardening audits
- `5b4affb` docs: record remaining state audit risks
- `cc3f6d6` fix: close red-team state and evidence gaps
- `ec63be4` fix: place decision recovery query in snapshot
- Final report-only commit: recorded after creation of this file

No push, merge, deployment, database migration, dependency installation, or Provider change occurred.

## 15. Risks

The highest uncertainty is not algorithmic polish; it is the unexecuted real PostgreSQL chain. Passing pure/stub tests cannot prove SQL behavior, transaction lineage, browser recovery, or aggregate rejudge persistence in the actual runtime.

## 16. Recommended Next Step

One smallest next iteration: first remove raw merchant reply text from localStorage, then provision an isolated `TEST_DATABASE_URL` and run the complete fake-provider browser chain through Decision V1 → questions → replies → aggregate V2/Delta. Do not add features before this passes.

## 17. Deployment Recommendation

`DO_NOT_DEPLOY`

## 18. Final Verdict

`COMPLETE_WITH_REMAINING_ISSUES`
