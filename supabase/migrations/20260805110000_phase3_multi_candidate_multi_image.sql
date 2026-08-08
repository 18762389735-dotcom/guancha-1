-- Phase 3: PRD P0 supports up to five candidates and two active images per candidate.
-- This migration preserves Phase 2 records and turns "current" into explicit,
-- input-set-versioned state so a late older job cannot replace a newer result.

alter table candidates
  drop constraint if exists candidates_selection_session_id_key;

alter table candidates
  add column if not exists display_order smallint,
  add column if not exists status text not null default 'active' check (status in ('active', 'deleted')),
  add column if not exists deleted_at timestamptz,
  add column if not exists image_set_version integer not null default 0;

update candidates set display_order = 1 where display_order is null;
alter table candidates alter column display_order set not null;
alter table candidates add constraint candidates_display_order_range check (display_order between 1 and 5);
create unique index if not exists candidates_active_display_order_idx
  on candidates(selection_session_id, display_order) where status = 'active';

alter table candidate_images
  drop constraint if exists candidate_images_candidate_id_key;

alter table candidate_images
  add column if not exists display_order smallint;

update candidate_images set display_order = 1 where display_order is null;
alter table candidate_images alter column display_order set not null;
alter table candidate_images add constraint candidate_images_display_order_range check (display_order between 1 and 2);
create unique index if not exists candidate_images_active_display_order_idx
  on candidate_images(candidate_id, display_order) where status <> 'deleted';

alter table analysis_jobs
  add column if not exists input_image_ids uuid[] not null default '{}',
  add column if not exists input_set_version integer not null default 0;

update analysis_jobs set input_image_ids = array[candidate_image_id] where cardinality(input_image_ids) = 0;

alter table extraction_versions
  add column if not exists source_image_ids uuid[] not null default '{}',
  add column if not exists input_set_version integer not null default 0,
  add column if not exists is_current boolean not null default false;

update extraction_versions set source_image_ids = array[source_image_id] where cardinality(source_image_ids) = 0;
create unique index if not exists extraction_versions_one_current_per_candidate_idx
  on extraction_versions(candidate_id) where is_current and status = 'completed';

create index if not exists candidate_images_candidate_active_idx
  on candidate_images(candidate_id, display_order) where status <> 'deleted';
create index if not exists analysis_jobs_candidate_input_set_idx
  on analysis_jobs(candidate_id, input_set_version, created_at);
