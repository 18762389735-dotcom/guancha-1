# Final real MiMo E2E — 2026-08-08

## Scope and fixed runtime

- Frozen application commit under test: `556f05fd4854cb0215c3970e247b18b94c0cf4a0`
- Provider: `mimo`
- Model: `mimo-v2.5`
- Processing mode: `live-ai`
- Browser test surface: an isolated localhost origin and a fresh browser state.
- No FakeProvider, fixture prediction, cache fallback, prompt adjustment, or model-output retry was used.

The controlled inputs were real user-provided product screenshots mapped in the
Golden Set: Candidate A used `IMG-001` and `IMG-002`; Candidate B used
`IMG-003` and `IMG-004`; Candidate C used `IMG-006`.

## Result: extraction gate

The intended call budget was three candidate-level calls:

| Candidate | Intended images | Intended calls | Actual new live calls | Result |
| --- | ---: | ---: | ---: | --- |
| A | 2 | 1 joint call | 2 | FAIL |
| B | 2 | 1 joint call | 2 | FAIL |
| C | 1 | 1 single call | 1 | PASS in isolation |

The database recorded five new completed extraction jobs and five matching AI
call logs. All five have `provider=mimo`, `model_identifier=mimo-v2.5`, and
`processing_mode=live-ai`; none is marked as Fake or fallback.

Recorded job IDs:

- `68827b65-c754-5641-ac8f-05b2720cb0f2` — completed, live-ai
- `a03c0dfa-6784-5d72-9ba5-030eb8f3a060` — completed, live-ai
- `f8653194-c928-52ae-b229-3c892c6b8638` — completed, live-ai
- `9f63be57-c930-5c69-a009-dae2955ea7fa` — completed, live-ai
- `7d880c57-01e4-5480-93c5-d6f7e3714e81` — completed, live-ai

The local validation server was stopped immediately after this observation, so
no additional real calls were made and no retry was used.

## P0 — candidate-level multi-image contract is not met

**Observed behaviour:** each image upload creates and enqueues a separate
extraction job. Consequently, five uploaded images produce five real Vision
calls, even when two images belong to the same candidate.

**Code evidence:**

- `backend/src/guancha_api/application/phase2_service.py` creates an image plus
  an initial job in `upload_image()` and immediately schedules `_run_extraction_job()`.
- `backend/src/guancha_api/repositories/postgres.py` creates an
  `analysis_jobs` row for every call to `create_image_and_initial_job()`.
- The browser integration uploads the candidate's images in a loop and starts
  polling each returned image job. It therefore has no candidate-level
  aggregation boundary before the provider is called.

This contradicts the fixed final-E2E contract: A1/A2 must be passed in **one**
candidate-level Vision request, B1/B2 in another, and C1 in one single-image
request. It also makes `ExtractionVersion.source_image_ids` insufficient proof
of actual joint model input: the persistence shape can contain an image set,
while the provider calls were already made per image.

## Steps intentionally not executed

The following were not run after the P0 gate failed, because continuing would
misrepresent the requested end-to-end acceptance and could make more real
model calls:

- Evidence source-image joint-input verification for A and B
- Decision V1 and Answer V2 acceptance
- Question collection and merchant replies
- Aggregate rejudge, Decision V2, and DecisionDelta
- Tea Stock state confirmation and hard-refresh recovery

They are **not PASS** and are not inferred from prior FakeProvider coverage.

## Required remediation before another real E2E

Keep image upload as a storage/metadata operation, then create and enqueue
exactly one extraction job per candidate only when the candidate's input set is
finalized for analysis. That job must persist the complete ordered
`input_image_ids` set and pass that full set once to the provider. The session
analysis flow must then wait for those candidate jobs before requesting the
decision job. This needs a dedicated P0 fix and automated regression coverage
for A=2, B=2, C=1 -> exactly three provider invocations, before another paid
browser run.

## Final classification

- P0: 1
- P1: 0 assessed after the extraction gate (downstream acceptance not run)
- P2: not assessed

**FINAL VERDICT: `NOT_READY_FOR_DEPLOYMENT_HARDENING`**

---

## Final rerun after the candidate-batching repair

The failure above is retained as an audit record. It was remediated by
`2269145aff898fba1b53b91d2a1aa9fcfea4c4a9` (`fix: batch external candidate
image extraction`), then re-run through the browser with the same fixed input
shape and the real `mimo-v2.5` provider.

### Real Vision call gate: PASS

The final browser run created these candidate input sets:

| Candidate | Uploaded screenshots | Completed live extraction jobs | Result |
| --- | ---: | ---: | --- |
| A | 2 | 1 | PASS: one joint candidate input set |
| B | 2 | 1 | PASS: one joint candidate input set |
| C | 1 | 1 | PASS: one single-image candidate input set |

The database check after the run reported exactly one completed extraction job
per candidate for the current A/B/C session. Two earlier per-image jobs are
retained as `stale` audit history and were not dispatched during this re-run.
The active three jobs used `provider=mimo`, `model_identifier=mimo-v2.5`, and
`processing_mode=live-ai`. No FakeProvider, fixture, cache fallback, prompt
change, schema change, or retry was used in the real Vision portion.

### Browser acceptance: PASS

- Decision V1 and Answer V2 rendered three real candidate answers without
  exposing provider internals or fixture text.
- One merchant reply was saved for each candidate. No reply triggered an
  individual rejudge.
- After all three replies had been saved, the existing merchant sheet exposed
  **"提交并更新判断"** and performed one aggregate rejudge. The result page
  rendered the Decision V2 change section.
- The selected candidate was added to the existing local tea stock. A hard
  browser refresh kept the tea-stock record and its user-facing facts.

### Follow-up P1 repaired during the rerun

The first post-batching browser attempt exposed two frontend recovery defects:

1. reopening the merchant sheet reset its aggregate-rejudge readiness to
   `completed`, hiding the existing submit button;
2. a refresh that restored completed candidate extractions did not attach the
   returned session-decision job to the normal polling flow.

Both were repaired in `app.js` without changing page layout, API paths,
Evidence/Decision semantics, question generation, or merchant-reply fields.
The frontend suite and syntax check passed after the repair; the same browser
flow above verified the user-visible behavior.

## Current final classification

- Real MiMo candidate-level extraction: PASS
- Answer V2 / question / aggregate rejudge flow: PASS
- Tea-stock persistence after hard refresh: PASS
- Remaining items: P2 maintenance only; no final-E2E P0 or P1 remains.

**FINAL VERDICT: `READY_FOR_DEPLOYMENT_HARDENING`**
