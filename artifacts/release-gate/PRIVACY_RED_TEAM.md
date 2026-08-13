# Phase 15 Privacy Red Team

## Verdict

**PASS** at `cabc959`. P0: 0; P1: 0; accepted P2: 1.

## Scope and adversarial checks

- Selection bridge v3 is rebuilt from field allowlists. Unknown trees, free text, extraction/presentation data, preview/data URI/File-like values, invalid IDs/statuses/timestamps, arrays and corrupt backing values are discarded; legacy storage is projected and cleared.
- Preference evidence, UI session and local post-purchase data use independent projections and rewrite sanitized backing values on load. Corrupt/scalar/array UI backing is removed.
- Warehouse risks accept only the closed semantic risk set. Arbitrary ASCII such as merchant/reply payloads and `light-roast` are rejected. Extraction no longer falls back to `raw_text`.
- Local post-purchase history retains only date plus safe recommended/selected IDs and A-E labels. Tea names, Need text and nested merchant/reply/answer content are not persisted.

Independent focused verification passed `26/26`, including malicious ASCII risk input, absence of the `raw_text` fallback, invalid UI backing removal, selection/legacy/preference/post-purchase regressions, `node --check app.js`, and `git diff --check 24b3d67..cabc959`.

## Accepted boundary

`guancha.pending-images.v1` remains a temporary IndexedDB image cache without a schema TTL/eviction policy. This is a declared P2 browser/session-policy boundary, not a P0/P1 privacy failure.

