# Frontend integration score-gaming audit

Scope: production frontend files used by the competition mobile experience:
`app.js`, `index.html`, and `frontend/*.js`.  Test and evaluation workbenches
are outside this product bundle and are not imported by it.

## Prohibited artifact scan

The following strings were checked in production frontend sources:

- `EVAL-`, `HOLDOUT-`, `PERSONA-`, `META-`, `golden`
- `corrected_value`, `expected_bucket`, `expected_rank`
- `blind-holdout`, `decision-eval`

Result: no test artifact leakage and no answer lookup were found.  The
automated frontend test enforces the same scan.

## Decision and provider boundaries

- The browser calls only the Guancha backend API client. It does not include a
  provider API key, provider endpoint, or direct MiMo/OpenAI request.
- Action bucket labels are presentation-only mappings of the backend enum;
  the browser does not score, rank, or derive a decision.
- A local preview, demo warehouse record, or fixture is not rendered as an
  Extraction or `live-ai` result. Real result rendering requires a server
  ExtractionVersion and current server Decision.

## Verdict

- test artifact leakage: 0
- hardcoded evaluation answer: 0
- fake result presented as live-ai: 0
