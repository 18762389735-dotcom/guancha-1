# Resume / Portfolio Evidence — Observable Beta

Status: implementation evidence, not a deployment or user-validation claim.

## Concise project statement

Built a privacy-minimized observability and repeatable AI-evaluation layer for Guancha, an explainable Chinese-tea comparison Beta, while preserving the existing product flow and deterministic decision architecture.

## Verifiable contributions

- Defined a versioned client/server event contract with strict metadata allowlists, anonymous session-scoped identity, deterministic server event IDs, and fail-open delivery.
- Added read-time migration and write-time filtering for the top-level MerchantReply persistence path; independent review found a remaining nested-complex-field bypass, so this is partial implementation evidence rather than a validated privacy claim.
- Added an append-only standard-library JSONL sink, strict `POST /api/v1/events`, privacy-safe CSV export, and raw funnel summary without a database migration or analytics SDK.
- Converted 27 documented AI cases into a machine-readable manifest and thin pytest runner covering Extraction fixtures, evidence boundaries, sensory translation, current Need, questions, merchant replies, rejudge/Delta, and Decision/Answer consistency.
- Added a user-validation toolkit for 5–10 tea beginners: five hypotheses, task plan, observation rubric, interview guide, and metric definitions.

## Current evidence

- AI fixed set: 27 total; 24 PASS; 0 FAIL; 3 BLOCKED without `TEST_DATABASE_URL`.
- Frontend and backend automated evidence is reproducible from repository commands; no live Provider call is required.
- Telemetry schemas reject unknown free-text fields and client-forged server outcome names.
- Export tools skip malformed lines, deduplicate first-seen event IDs, sort records, and output allowlisted columns only.

## Honest limits

- This does not demonstrate real-world model accuracy, production scale, statistical conversion, or completed user research.
- Three database integration evals remain BLOCKED until an isolated PostgreSQL test database is supplied.
- The fixed fixture pipeline begins after structured Extraction and does not validate live vision quality.
- Deployment/privacy/readiness verdict belongs to the independent review artifacts, not this evidence note.
- Independent final review verdict: Privacy FAIL / NO-GO and `NOT_READY_FOR_USER_VALIDATION`.
