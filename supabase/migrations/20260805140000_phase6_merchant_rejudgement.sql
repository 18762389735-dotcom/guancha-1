-- Phase 6: append-only merchant reply rejudgement lineage.

alter table decision_versions
  add column if not exists parent_decision_version_id uuid references decision_versions(id),
  add column if not exists trigger_type text,
  add column if not exists trigger_resource_id uuid;

alter table analysis_jobs
  drop constraint if exists analysis_jobs_job_kind_check,
  add constraint analysis_jobs_job_kind_check
    check (job_kind in ('extraction', 'session_decision', 'merchant_rejudgement'));

create table merchant_replies (
  id uuid primary key,
  selection_session_id uuid not null references selection_sessions(id),
  decision_version_id uuid not null references decision_versions(id),
  followup_question_id uuid not null references followup_questions(id),
  candidate_id uuid not null references candidates(id),
  anonymous_client_id uuid not null references anonymous_clients(id),
  idempotency_key uuid not null,
  request_hash char(64) not null check (request_hash ~ '^[0-9a-f]{64}$'),
  raw_text text not null check (length(raw_text) between 1 and 4000),
  parse_status text check (parse_status in ('answered','partially-answered','evasive','not-answered','conflicting')),
  status text not null check (status in ('submitted', 'parsed', 'failed')),
  processing_status text not null check (processing_status in ('queued', 'processing', 'completed', 'failed')),
  created_at timestamptz not null default now(),
  unique (anonymous_client_id, followup_question_id, idempotency_key)
);

create table merchant_claims (
  id uuid primary key,
  merchant_reply_id uuid not null references merchant_replies(id),
  candidate_id uuid not null references candidates(id),
  field_key text not null check (field_key in ('tea_subtype','aroma_style','roast_level','season','origin_text','year_or_batch','price','weight_grams','sample_available','return_policy','process_text')),
  raw_text text not null,
  normalized_value text,
  information_status text not null check (information_status in ('explicit','inferred','unknown','conflict')),
  source_type text not null check (source_type = 'merchant-claim'),
  verification_status text not null check (verification_status = 'unverified'),
  evidence_strength text not null check (evidence_strength in ('low','medium','high')),
  conflicts_with_evidence_id uuid references evidence_items(id),
  created_at timestamptz not null default now(),
  unique (merchant_reply_id, field_key)
);

create table decision_deltas (
  id uuid primary key,
  selection_session_id uuid not null references selection_sessions(id),
  old_decision_version_id uuid not null references decision_versions(id),
  new_decision_version_id uuid not null references decision_versions(id),
  merchant_reply_id uuid not null references merchant_replies(id),
  -- `merchant_reply_id` remains the stable anchor for backward-compatible job
  -- lineage.  The batch is authoritative for aggregate rejudgement traceability.
  merchant_reply_ids uuid[] not null default '{}',
  added_facts jsonb not null default '[]'::jsonb,
  updated_fields jsonb not null default '[]'::jsonb,
  unresolved_fields jsonb not null default '[]'::jsonb,
  resolved_risks jsonb not null default '[]'::jsonb,
  added_risks jsonb not null default '[]'::jsonb,
  ranking_changed boolean not null,
  action_tier_changed boolean not null,
  old_top_candidate_id uuid references candidates(id),
  new_top_candidate_id uuid references candidates(id),
  explanation text not null,
  created_at timestamptz not null default now(),
  unique (merchant_reply_id)
);

alter table analysis_jobs
  add column if not exists merchant_reply_id uuid references merchant_replies(id);

create index merchant_replies_session_idx on merchant_replies(selection_session_id, created_at desc);
create index merchant_claims_reply_idx on merchant_claims(merchant_reply_id);
create unique index analysis_jobs_merchant_rejudge_reply_idx
  on analysis_jobs(merchant_reply_id) where job_kind = 'merchant_rejudgement';
