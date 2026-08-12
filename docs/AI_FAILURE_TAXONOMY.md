# AI Failure Taxonomy

Status: current evaluation vocabulary, 2026-08-13. Categories come from observed project failure modes; they are not product features or database enums.

| Failure type | Definition | Example / detection boundary | Default severity |
|---|---|---|---|
| EXTRACTION_MISS | A visible decision-relevant field remains unknown. | Price or roast is visible but absent from Evidence. | P1 |
| EXTRACTION_HALLUCINATION | Evidence contains a value unsupported by the screenshot. | Missing sample availability becomes true. | P0 |
| EVIDENCE_SOURCE_ERROR | A fact is attributed to the wrong source. | Merchant statement appears as product-page fact. | P0 |
| MARKETING_CLAIM_LEAK | Marketing language is upgraded into a verified sensory or quality fact. | “大师制作” becomes “品质更高”. | P0 |
| SENSORY_OVERCLAIM | A bounded interpretation becomes a certain product experience. | “通常更偏熟香” becomes “一定有熟香”. | P0 |
| SENSORY_MISSING | Explicit decision-relevant evidence has no usable sensory translation. | Light roast is shown without explaining lower fire-presence direction. | P1 |
| NEED_PRIORITY_ERROR | Historical preference or token matching overrides the current Need. | “低火味” ranks heavy roast first. | P0/P1 |
| BUDGET_PARSE_ERROR | Budget text is normalized to the wrong ceiling. | `150–300` interpreted as 150. | P1 |
| DECISION_ANSWER_MISMATCH | Visible answer contradicts order/bucket/components. | Decision ranks B first while label says A fits better. | P0 |
| QUESTION_DUPLICATE | A question repeats known or synonymous information. | Asking aroma after an equivalent explicit field is already resolved. | P1 |
| QUESTION_LOW_VALUE | Different answers cannot change order, risk, or action. | Asking a completeness-only field. | P1 |
| MERCHANT_REPLY_PARSE_ERROR | Merchant text maps to the wrong normalized fact. | “没有小样” becomes true. | P0 |
| MERCHANT_CONFLICT_FALSE_POSITIVE | Unknown/empty product evidence is treated as opposite. | Product sample unknown conflicts with merchant “可以”. | P0 |
| REJUDGE_INCONSISTENT | V2 changes without decision-relevant new evidence or loses V1 inputs. | Unrelated reply changes ranking by dropping preference evidence. | P0 |
| DECISION_STATE_STALE | A changed premise is paired with old derived artifacts. | New Need shown with old Decision/Delta. | P0 |
| STATE_RECOVERY_ERROR | Active server state resumes to the wrong screen. | Processing analysis reloads to candidates. | P1 |
| COLD_START_ERROR | A normal reopen resumes an old active result without reload intent. | New tab jumps to yesterday’s result. | P1 |
| MOBILE_UI_BLOCKER | Mobile geometry prevents the core action. | CTA or reply field is unreachable. | P0/P1 |
| PROVIDER_ERROR | Provider failure is hidden or promoted to a successful result. | Failed parse creates partial facts. | P0 |
| DATABASE_ERROR | Persistence cannot preserve ownership, immutability, or recovery. | Current Decision/Delta cannot be reconstructed. | P0 |

## Usage

- One case may expose multiple symptoms, but record the earliest causal failure type.
- `PASS` means the stated expected behavior was executed and observed in an automated run.
- `NOT_AUTOMATED` means no executable evidence ran in the current environment; it must not be counted as PASS.
