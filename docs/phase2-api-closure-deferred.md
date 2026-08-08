# Phase 2 API closure deferred items

- Job response `stage`, `error_code`, and `extraction_version_id`: image upload and job polling slice.
- Image concurrent idempotency and cross-client isolation: image upload slice.
- Marking the image completed inside `complete_extraction_job()`: extraction lifecycle slice.
