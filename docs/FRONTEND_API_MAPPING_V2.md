# Frontend API mapping v2

> 2026-08-08 当前映射。此前 Phase 10 的“前端限制为单候选/单图”已废弃：产品与公共配置均允许最多 5 个候选、每个候选最多 2 张截图。UI 结构、视觉资源、按钮文案和跳转路径仍是不可变基线；本文件只约束 `frontend/` 的数据与动作接入。

Authority: generated OpenAPI from the current backend, not inferred routes.
The browser sends `X-Client-Id` on anonymous requests and `Idempotency-Key` on
all creation requests through `frontend/api-client.js`.

| User-flow step | OpenAPI route | Frontend consumer | Contract gap |
| --- | --- | --- | --- |
| Anonymous session | `POST /api/v1/selection-sessions`, `GET/PATCH /api/v1/selection-sessions/{session_id}` | need form and restored bridge | None |
| Candidate create/list | `POST/GET /api/v1/selection-sessions/{session_id}/candidates`, `DELETE /api/v1/candidates/{candidate_id}` | existing candidate card | Respect public limit: at most 5 candidates |
| Screenshot upload | `POST /api/v1/candidates/{candidate_id}/images`, `GET/DELETE /api/v1/candidate-images/{candidate_image_id}` | upload card and the existing supplementary-image control | Respect public limit: at most 2 images per candidate; persist only metadata, never bytes/base64 |
| Extraction job | `GET /api/v1/jobs/{job_id}`, `POST /api/v1/candidates/{candidate_id}/extraction-jobs` | `GuanchaJobPoller` | None; status mapping needs strict terminal handling |
| Extraction/Evidence | `GET /api/v1/candidates/{candidate_id}/current-extraction`, `GET /api/v1/extraction-versions/{id}` | result adapter | None |
| Decision | `POST /api/v1/selection-sessions/{session_id}/analyze`, `GET /api/v1/selection-sessions/{session_id}/current-decision`, `GET /api/v1/decision-versions/{id}` | result screen | Local Decision fallback must be disabled for real sessions |
| Next best questions | `GET/POST /api/v1/decision-versions/{id}/questions` | question sheet | None; preserve backend order and empty state |
| Merchant reply | `POST /api/v1/selection-sessions/{session_id}/merchant-replies`, `GET /api/v1/merchant-replies/{id}` | existing reply form | None |
| Rejudgement | `POST /api/v1/selection-sessions/{session_id}/rejudge`, `GET /api/v1/decision-deltas/{id}` | rejudge page | None; consume returned delta only |
| Owned/saved | no account endpoint in P0 | local post-purchase store | Intentional local-only bridge |
| Brew bridge | `POST /api/v1/brew-feedback/analyze` | tea journal | Intentional local ownership plus server analysis bridge |

## Known CONTRACT_GAP records

1. Candidate `GET list` is the reconciliation source after refresh. The bridge
   resumes server-backed active jobs and re-reads current Extraction/Decision
   state; it never invents a server result for a local candidate.
2. The candidate card may show a local preview of an uploaded screenshot in
   the active browser session. That preview is visual feedback only; it must
   not be promoted to a completed extraction or decision.

No alternate or guessed endpoint is permitted.
