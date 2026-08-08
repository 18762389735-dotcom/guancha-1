-- Phase 7: expose the immutable Delta that completed a merchant rejudgement.
alter table analysis_jobs
  add column if not exists decision_delta_id uuid references decision_deltas(id);

-- Browser-local low-confidence evidence is copied into a session snapshot only.
-- It is not a user profile and cannot replace the explicit SelectionNeed.
alter table selection_sessions
  add column if not exists recent_preference_evidence jsonb not null default '[]'::jsonb;

create table if not exists brew_feedback_replays (
  anonymous_client_id uuid not null references anonymous_clients(id),
  client_feedback_id uuid not null,
  idempotency_key uuid not null,
  request_hash char(64) not null check (request_hash ~ '^[0-9a-f]{64}$'),
  response jsonb not null,
  created_at timestamptz not null default now(),
  primary key (anonymous_client_id, client_feedback_id),
  unique (anonymous_client_id, idempotency_key)
);
