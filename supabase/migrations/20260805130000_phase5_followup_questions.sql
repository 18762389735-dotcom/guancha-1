-- Phase 5: immutable next-best-question records for a current DecisionVersion.

create table question_generation_runs (
  decision_version_id uuid primary key references decision_versions(id),
  idempotency_key uuid not null,
  status text not null check (status in ('not_started', 'processing', 'completed', 'failed')),
  error_code text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table followup_questions (
  id uuid primary key,
  decision_version_id uuid not null references decision_versions(id),
  selection_session_id uuid not null references selection_sessions(id),
  candidate_id uuid not null references candidates(id),
  field_key text not null check (field_key in (
    'aroma_style', 'roast_level', 'season', 'origin_text', 'year_or_batch',
    'price', 'weight_grams', 'sample_available', 'return_policy', 'process_text'
  )),
  question_text text not null,
  reason text not null,
  affected_decision jsonb not null default '[]'::jsonb,
  answer_branches jsonb not null default '[]'::jsonb,
  priority integer not null check (priority between 0 and 4),
  value_score integer not null,
  value_components jsonb not null,
  status text not null check (status = 'completed'),
  created_at timestamptz not null default now(),
  unique (decision_version_id, candidate_id, field_key)
);

create index followup_questions_current_read_idx
  on followup_questions(decision_version_id, priority desc, candidate_id, field_key);

create function prevent_followup_question_mutation() returns trigger language plpgsql as $$
begin
  raise exception 'followup_questions are immutable';
end;
$$;

create trigger followup_questions_immutable
  before update or delete on followup_questions
  for each row execute function prevent_followup_question_mutation();
