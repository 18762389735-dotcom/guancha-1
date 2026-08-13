# AI Evaluation Matrix

Status: executable fixed-set contract, 2026-08-13.

The machine-readable source is `backend/evaluation/ai_eval_cases.json`. Run it from any working directory with:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\run_ai_eval.py
```

The runner invokes existing pytest nodes, never calls a real Provider, never reads API keys, and writes `artifacts/observable-beta/AI_EVAL_RESULTS.md`. `PASS` means the stated fixed test executed successfully. `BLOCKED` is not PASS. `fixture_pipeline` begins with fixed structured Extraction fixtures and is not a live vision-pipeline claim.

Phase 15 adds two runnable replay-edge regressions and one explicit database replay gate. The fixed set is now 30. `REPLAY-EDGE-01` proves only that the service propagates the repository `created` flag; it does not prove route/event exactly-once behavior. `REPLAY-DB-01` is the real same-key session/candidate/image replay gate and remains BLOCKED without `TEST_DATABASE_URL`.

| Case | Level | Category | Failure category if broken | Current |
|---|---|---|---|---|
| EXT-01 | fixture_pipeline | Extraction Safety | EXTRACTION_MISS | PASS |
| EXT-02 | fixture_pipeline | Extraction Safety | EXTRACTION_HALLUCINATION | PASS |
| EXT-03 | fixture_pipeline | Extraction Safety | EXTRACTION_MISS | PASS |
| EXT-04 | fixture_pipeline | Extraction Safety | EVIDENCE_SOURCE_ERROR | PASS |
| EVD-01 | deterministic_unit | Evidence Safety | EVIDENCE_SOURCE_ERROR | PASS |
| EVD-02 | deterministic_unit | Evidence Safety | EVIDENCE_SOURCE_ERROR | PASS |
| EVD-03 | deterministic_unit | Evidence Safety | MARKETING_CLAIM_LEAK | PASS |
| EVD-04 | fixture_pipeline | Evidence Safety | EXTRACTION_HALLUCINATION | PASS |
| SEN-01 | deterministic_unit | Sensory Translation | SENSORY_OVERCLAIM | PASS |
| SEN-02 | deterministic_unit | Sensory Translation | SENSORY_OVERCLAIM | PASS |
| SEN-03 | deterministic_unit | Sensory Translation | SENSORY_MISSING | PASS |
| NEED-01 | deterministic_unit | Current Need | NEED_PRIORITY_ERROR | PASS |
| NEED-02 | deterministic_unit | Current Need | NEED_PRIORITY_ERROR | PASS |
| NEED-03 | deterministic_unit | Current Need | NEED_PRIORITY_ERROR | PASS |
| NEED-04 | deterministic_unit | Current Need | BUDGET_PARSE_ERROR | PASS |
| QST-01 | deterministic_unit | Question | QUESTION_LOW_VALUE | PASS |
| QST-02 | deterministic_unit | Question | QUESTION_DUPLICATE | PASS |
| QST-03 | deterministic_unit | Question | QUESTION_LOW_VALUE | PASS |
| MRP-01 | deterministic_unit | Merchant Reply | MERCHANT_REPLY_PARSE_ERROR | PASS |
| MRP-02 | deterministic_unit | Merchant Reply | MERCHANT_REPLY_PARSE_ERROR | PASS |
| MRP-03 | deterministic_unit | Merchant Reply | MERCHANT_CONFLICT_FALSE_POSITIVE | PASS |
| MRP-04 | fixture_pipeline | Merchant Reply | MERCHANT_REPLY_PARSE_ERROR | PASS |
| REJ-01 | deterministic_unit | Rejudge and Delta | REJUDGE_INCONSISTENT | PASS |
| REJ-02 | database_integration | Rejudge and Delta | REJUDGE_INCONSISTENT | BLOCKED |
| REJ-03 | database_integration | Rejudge and Delta | REJUDGE_INCONSISTENT | BLOCKED |
| ANS-01 | deterministic_unit | Decision Answer | DECISION_ANSWER_MISMATCH | PASS |
| STATE-01 | database_integration | State Safety | DECISION_STATE_STALE | BLOCKED |
| REPLAY-EDGE-01 | deterministic_unit | Replay Created Edge | STATE_RECOVERY_ERROR | PASS |
| STATE-03 | deterministic_unit | State Safety | STATE_RECOVERY_ERROR | PASS |
| REPLAY-DB-01 | database_integration | Replay Exactly Once | DATABASE_ERROR | BLOCKED |

Coverage details remain in the manifest through exact `pytest_nodeids`. Marketing safety executes all five required terms individually. Merchant reply vocabulary executes 轻、重、浅、深、淡、浓、提供、不提供、有、没有、不知道、没问这个 across the roast and sample contracts. Question coverage verifies a high-value unknown roast question, no repeat of known price, and unique candidate/field pairs.
