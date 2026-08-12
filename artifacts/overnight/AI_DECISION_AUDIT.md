# AI Decision Audit

Date: 2026-08-13  
Method: deterministic fixtures and pure/service tests; no real Provider calls.

## Pipeline conclusion

The current pipeline still follows Extraction → Evidence → Sensory Interpretation → Personal Fit → Decision → Question → Merchant Reply → Rejudge → Decision Delta. The six selected repairs tighten source boundaries and consistency without changing the Provider, action buckets, or scoring architecture.

## Findings

### AI-P0-01 — Merchant sample negation inversion

- Boundary: MerchantReply
- Finding: “没有小样” could match “有小样”, and “不提供” could be normalized through broad positive tokens.
- Required behavior: negation wins; `不提供/没有/不可以=false`, `可以/提供/有=true`.
- Conflict rule: unknown/empty product evidence is not a conflict; only explicit opposite values conflict.
- Status: FIXED; deterministic positive, negative, unknown, same, and opposite tests pass.

### AI-P0-02 — Answer evidence source leak

- Boundary: Evidence → Answer
- Finding: inferred product evidence and merchant claims could enter `known_facts`.
- Required behavior: product explicit → `known_facts`; merchant explicit → `merchant_facts`; inferred → neither confirmed-fact section.
- Status: FIXED; mixed-source mapper test passes.

### AI-P1-01 — Low-fire need reversed by broad token

- Boundary: Current Need → Decision
- Finding: “低火味” contained the broad “火味” token and could add a positive heavy-roast signal in the legacy component.
- Required behavior: low-fire wording consistently prefers light roast within the same action bucket.
- Status: FIXED; light > heavy regression passes.

### AI-P1-02 — Budget range ceiling

- Boundary: Current Need → Decision
- Finding: the first number of a range was treated as its ceiling.
- Required behavior: `150–300`, `150-300`, and `300以内` all cap at 300.
- Status: FIXED; 250 fits and 350 does not for every form.

### AI-P1-03 — Rejudge preference stability

- Boundary: Rejudge
- Finding checked from the previous iteration: an unrelated merchant reply must not drop bounded low-confidence preference evidence or force ranking change.
- Status: EXISTING FIX RETAINED; `test_unrelated_reply_preserves_v1_bounded_preference_component_and_ranking` passes in the full suite.

## Safety checks

- Marketing-only evidence does not improve evidence sufficiency.
- Unknown evidence does not become known merely because it carries a value.
- Sensory output remains qualified and avoids quality judgments.
- Bucket priority remains above sensory tie-break signals.
- Aggregate rejudge DB closure remains NOT_AUTOMATED tonight because the dedicated test database is unavailable; the DB tests were skipped rather than reported as passed.

## Remaining AI findings

| ID | Severity | Finding | Risk / minimal next check |
|---|---|---|---|
| AI-REM-01 | P1 | Aroma values mix enum and concept levels (`qingxiang`, `floral`, orchid-like concepts). | Comparisons may look exact while categories are not equivalent; define one bounded aroma vocabulary and mapping tests. |
| AI-REM-02 | P1 | Delta risk lists can misstate whether a risk was added or resolved when evidence status changes across versions. | Verify old/new risk set semantics against real PostgreSQL V1/V2/Delta fixtures. |
| AI-REM-03 | P1 | Question ordering can overvalue generic completeness versus current preference and counterfactual decision value. | Add preference-aware value ordering fixtures without allowing history to override current Need. |
| AI-REM-04 | P1 | Live Provider marketing schema remains a blind spot despite fake-fixture safety. | Run a bounded real-provider holdout only after environment approval; do not infer PASS from deterministic fixtures. |
| AI-REM-05 | P1 | Inferred evidence may still participate in hard decision inputs outside the user-facing known-fact mapper. | Audit `_evidence_values` and rule conditions; explicit-only hard-decision policy needs a product decision. |
| AI-REM-06 | P2 | Vague replies beyond the closed fake vocabulary may remain partially answered without precise recovery guidance. | Expand adversarial reply fixtures before changing production parsing. |

No real MiMo call ran tonight. These are remaining risks, not claims that a live Provider failed.
