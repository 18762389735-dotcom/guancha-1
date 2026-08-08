# Legacy Fixture Provenance

The fixture catalog is project-owned test data derived from audited legacy **text, field structure, and expected outcomes**. It does not read the old project at runtime and contains no old images, URLs, database IDs, user records, provider configuration, request logs, or credentials.

## Converted cases

| Current fixture(s) | Legacy evidence | Conversion |
|---|---|---|
| `candidate-a-complete-qingxiang`, `boundary-complete-fields` | `backend/scripts/p0_trust_loop_tests.py`, `backend/scripts/real_text_regression.py` | Generic product wording; mapped price/weight/unit price and screenshot evidence to frozen PRD fields. |
| `candidate-b-nongxiang-unknown-roast`, `boundary-unknown-roast` | `backend/scripts/text_extraction_tests.py:T2` | Preserved `roast_level=unknown`; no inference from `nongxiang`. |
| `candidate-c-marketing-heavy`, `merchant-evasive` | `backend/scripts/stage3c_eval.py:TC-UGC-10` | Retained only generic marketing phrases; they remain product claims with low strength, never verified facts. |
| `boundary-missing-price`, `boundary-missing-weight` | `data/multimodal_extraction_schema_v1.json` | Rewrote the old unit-price guard as current null behavior. |
| `boundary-conflicting-fields`, `merchant-conflicting` | `backend/scripts/seller_reply_parse_tests.py` | Rewrote season disagreement as two append-only Evidence records. |
| `merchant-answered`, `merchant-partially-answered` | `backend/scripts/stage3c_eval.py:TC-UGC-01/02` | Converted explicit text to unverified `merchant-claim` evidence; unanswered fields remain unresolved. |

## Deliberately discarded legacy fields and behaviors

- Fact fields not in PRD: `price_confidence`, `trust_evidence`, `certification_verifiability`, `info_transparency_score`, `marketing_to_info_ratio`, `verifiable_credentials`.
- Any old `verified` meaning, direct candidate-field overwrite on merchant reply, old tier labels/scores, legacy database schema/IDs, provider configuration, source paths and images.
- The five YAML items are **candidate metadata only**; no production Decision Engine imports or executes them in this change.

## PRD constraints retained

All screenshot evidence is `product-claim` + `unverified`; all merchant evidence is `merchant-claim` + `unverified`. Unknown values are represented explicitly and conflicts preserve both sources instead of replacing the earlier evidence.
