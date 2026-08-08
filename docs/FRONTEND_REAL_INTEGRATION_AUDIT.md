# Frontend real-backend integration audit

> Historical Phase 10 audit, superseded for current limits by
> [CURRENT_STATE.md](CURRENT_STATE.md) and [FRONTEND_API_MAPPING_V2.md](FRONTEND_API_MAPPING_V2.md).
> Its one-candidate/one-image scope is not current product behavior.

Scope: existing competition mobile UI (`app.js`, `frontend/*.js`) against the
current FastAPI OpenAPI document.  This audit distinguishes visual scaffolding
from data that can accidentally be presented as a live backend result.

| Page/module | Current data source | Real API exists | Required Phase 10 work | P0 path |
| --- | --- | --- | --- | --- |
| Home / need selection | local UI state | `POST/PATCH /selection-sessions` | Persist the selected need before candidate work; reuse the stored anonymous session when valid | Yes |
| Candidate page | local candidate objects and runtime object URLs | candidate create/list/delete | Keep one candidate and one image in this phase; attach server IDs to the existing cards | Yes |
| Image upload | runtime `File` plus local preview | image upload/get/delete, job get | Use multipart API response (`image`, `extraction_job`), then poll actual job | Yes |
| Analysis page | real job state is partly wired; local `queued` is also used | job get/current extraction | Render only `uploading`, `queued`, `processing`, `completed`, `failed`; do not turn a local preview into extraction success | Yes |
| Result card | server Extraction, Evidence and Decision adapter | extraction/current extraction/current decision | Wait for `current-decision`; never render a Decision without it | Yes |
| Questions sheet | backend question calls are wired; presentation state is local | question create/list | Keep server order; hide the question cards when returned list is empty | Yes |
| Merchant reply / rejudge | backend calls and poller are partly wired | merchant reply/rejudge/current decision/delta | Keep submission, failure and completion states; show server DecisionDelta | Yes |
| Buy/owned bridge | browser local store | no account API required | Preserve only local ownership/tea-stock bridge and carry `candidate_id` / `sourceDecisionId` | Yes |
| Brew feedback/journal | local store plus backend feedback helper | brew-feedback analyze | Existing bridge is retained; no UI redesign in Phase 10 | Bridge only |
| Warehouse seed data / journal seed | `defaultState` demo records | not required | Legitimate first-run visual/demo content; must never be used as a live extraction or Decision result | No |
| Camera unavailable text, toast timeout, CSS fallback | UI presentation | n/a | Legitimate visual/interaction fallback, not product data | No |

## Classification

### A. Production mocks that must be replaced or gated

1. Legacy/local candidates can be normalized with a completed status.  A
   restored local candidate without a server candidate/image/job must be
   treated as pending, not as a completed extraction.
2. Existing multi-candidate/multi-image controls exceed the current Phase 10
   P0 contract.  They must be limited to one candidate and one image rather
   than fabricated as independent backend successes.

### B. Legitimate explicit demo fallbacks

- First-run warehouse and journal cards, local post-purchase storage, camera
  availability messaging, and CSS asset fallbacks are presentation/demo
  scaffolding.  They are not sent to the backend and are not labelled as
  `live-ai`.
- The backend's documented exact-fixture fallback remains backend-only and
  must retain its `processing_mode`; the frontend must never relabel it as a
  real provider call.

### C. Visual placeholders

- Tea artwork, empty cards, wordmarks, generic illustrations, and loading dots
  are visual placeholders.  They contain no Claim, Evidence, Decision, or
  Question data.

## Resolution

The real result path now blocks until the server returns `current-decision`.
Only backend action buckets and reasons are rendered.  Legacy local data is
never upgraded to an extraction result, the UI is limited to one candidate and
one image, and active server-backed jobs are resumed after a page refresh.
