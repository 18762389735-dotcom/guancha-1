# Observable Beta Privacy Review

## Verdict

**FAIL / NO-GO**

The review covered events, logs, CSV export, the public analytics API, browser persistence, replay behavior, and fail-open behavior. The two-authorized-privacy-fix and three-authorized-analytics-fix budget is exhausted. The remaining findings are recorded for a later, explicitly authorized iteration; they were not repaired in this reporting pass.

## First review: five findings

The first independent review returned FAIL with these five required fixes:

1. **PRIV-1 / P0:** `selectionBridge` copied unknown top-level and unsafe MerchantReply fields, did not strictly validate IDs/status/timestamps, and did not remove corrupt backing JSON.
2. **PRIV-2 / P1:** client/server identifiers and metadata string fields were not consistently closed vocabularies; server-side final rejection was incomplete.
3. **AN-1 / P0:** analytics exceptions could cross business success/failure boundaries because emission was not uniformly fail-open.
4. **AN-2 / P1:** result views and server transitions could be double-counted; GET polling emitted `merchant_reply_unusable`; replay boundaries were incomplete.
5. **AN-3 / P1:** the exporter did not fully validate schema/authority/event pairing or protect CSV consumers from formulas and embedded newlines.

## Fix commit reviewed

Commit `26f9fe5` implemented the authorized fixes: top-level and MerchantReply allowlists, UUID and enum boundaries, `safe_emit_*`, business-terminal emission outside failure-catching regions, created-only Decision/Rejudge/MerchantReply transitions, result edge guarding, strict JSONL export validation, and CSV formula/CRLF protection.

## Re-review: remaining findings

### P0 Privacy — nested selection bridge raw text

`frontend/stores.js` still clones allowed complex fields such as `candidates`, `followupQuestions`, and `selectionAnswer`. A nested `merchantReplies.*.raw_text`, `text`, or `summary` inside those structures remains in backing localStorage. Top-level MerchantReply sanitation therefore does not establish a whole-bridge privacy boundary.

### P1 Analytics — Phase 2 replay and enqueue duplication

Several Phase 2 creation/start paths discard repository `created` information or return no equivalent edge flag. Idempotent replay can append duplicate raw JSONL records for need, candidate, image, or staged analysis events, and queued extraction can be enqueued again. Deterministic event IDs and export-time deduplication do not prevent duplicate raw records or duplicate enqueue side effects.

### P2 Analytics — metadata coercion in export validation

`validate_stored_event()` accepts falsey non-object metadata as `{}` and Pydantic coercion accepts values such as numeric strings or integer booleans. The exporter can therefore silently normalize invalid JSONL rather than reject it under a strict v1 schema.

### Additional counting limitation

The result-view edge guard is not reset after leaving result/rejudge. Re-entering the same candidate and decision may be under-counted. This is a measurement limitation, not the privacy NO-GO cause.

## Passed checks

- Invalid persisted analytics sessions rotate to a session-scoped UUID.
- Flow, candidate, and decision IDs enforce UUID boundaries.
- Top-level MerchantReply unknown/sensitive fields, invalid question keys, arrays, and corrupt JSON are removed; reset clears the backing key.
- Client metadata rejects nested objects and sensitive credential, PII, path, base64, and free-text shapes at the tested boundaries.
- Stage, error category, failure category, and metadata string values use closed vocabularies.
- Clients cannot submit server-authoritative outcome events.
- Throwing analytics sinks do not change successful HTTP, Decision, Rejudge, or MerchantReply parse state.
- `merchant_reply_unusable` was removed from GET polling and retained only after parse persistence.
- Decision, Rejudge, and MerchantReply service replay no longer emits their tested transition events.
- Export rejects malformed JSON, unknown events, incorrect authority/event pairs, noncanonical UUIDs, naive timestamps, and unknown top-level fields.
- CSV cells beginning with `=`, `+`, `-`, or `@` are quoted defensively; CR/LF is removed.
- Funnel summaries remain raw counts and do not invent rates.
- Secret scan found no real credential.

## Verification evidence

- Frontend: 48 passed.
- Backend full runnable suite: 223 passed, 76 skipped because `TEST_DATABASE_URL` was unavailable.
- AI evaluation: 24 PASS, 0 FAIL, 3 BLOCKED.
- Real Provider calls: 0.
- `git diff --check`: passed.

## Release decision

Because raw merchant text can still be persisted through nested allowed selection fields, Privacy remains **FAIL / NO-GO**. The exhausted fix budget prevents another code repair in this phase.
