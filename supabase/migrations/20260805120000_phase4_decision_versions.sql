-- Phase 4: immutable, session-scoped decision snapshots.

create table decision_versions (
  id uuid primary key,
  selection_session_id uuid not null references selection_sessions(id),
  anonymous_client_id uuid not null references anonymous_clients(id),
  version integer not null check (version >= 1),
  status text not null check (status in ('completed', 'stale')),
  rule_version text not null,
  need_snapshot jsonb not null default '{}'::jsonb,
  input_fingerprint char(64) not null check (input_fingerprint ~ '^[0-9a-f]{64}$'),
  top_candidate_id uuid references candidates(id),
  is_current boolean not null default false,
  created_at timestamptz not null default now(),
  unique (selection_session_id, version)
);

create unique index decision_versions_one_current_per_session_idx
  on decision_versions(selection_session_id) where is_current and status = 'completed';

create table candidate_decisions (
  id uuid primary key,
  decision_version_id uuid not null references decision_versions(id),
  candidate_id uuid not null references candidates(id),
  extraction_version_id uuid not null references extraction_versions(id),
  action_bucket text not null check (action_bucket in (
    'currently-selectable', 'ask-before-buying', 'sample-first',
    'not-recommended-now', 'insufficient-information'
  )),
  rank_within_bucket integer not null check (rank_within_bucket >= 1),
  overall_order integer not null check (overall_order >= 1),
  reasons jsonb not null default '[]'::jsonb,
  risk_flags jsonb not null default '[]'::jsonb,
  missing_critical_fields jsonb not null default '[]'::jsonb,
  score_components jsonb not null default '{}'::jsonb,
  internal_score numeric not null,
  created_at timestamptz not null default now(),
  unique (decision_version_id, candidate_id),
  unique (decision_version_id, overall_order)
);

alter table analysis_jobs
  add column if not exists job_kind text not null default 'extraction'
    check (job_kind in ('extraction', 'session_decision')),
  add column if not exists decision_version_id uuid references decision_versions(id),
  add column if not exists decision_need_snapshot jsonb not null default '{}'::jsonb,
  add column if not exists expected_extraction_version_ids uuid[] not null default '{}';

create unique index analysis_jobs_session_decision_idempotency_idx
  on analysis_jobs(candidate_id, idempotency_key) where job_kind = 'session_decision';
create index decision_versions_session_current_idx
  on decision_versions(selection_session_id, created_at desc);
create index candidate_decisions_version_order_idx
  on candidate_decisions(decision_version_id, overall_order);
