-- Phase 8: auditable fixed-demo fallback modes.  This migration adds only
-- observability values; it does not alter product data or public routes.

alter table analysis_jobs
  drop constraint if exists analysis_jobs_processing_mode_check,
  add constraint analysis_jobs_processing_mode_check
    check (processing_mode in ('fake-provider', 'openai-vision', 'test-fixture', 'live-ai', 'cache-fallback'));

alter table ai_call_logs
  drop constraint if exists ai_call_logs_processing_mode_check,
  add constraint ai_call_logs_processing_mode_check
    check (processing_mode in ('fake-provider', 'openai-vision', 'test-fixture', 'live-ai', 'cache-fallback'));
