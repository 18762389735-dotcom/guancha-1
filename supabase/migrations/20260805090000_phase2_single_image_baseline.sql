-- Phase 2 authoritative baseline. This is the first migration intended for execution.
-- User images are temporary private objects and are never persisted as accessible paths.

create table anonymous_clients (
  id uuid primary key,
  created_at timestamptz not null default now()
);

create table selection_sessions (
  id uuid primary key,
  anonymous_client_id uuid not null references anonymous_clients(id),
  need jsonb not null default '{}'::jsonb,
  idempotency_key uuid not null,
  request_hash char(64) not null check (request_hash ~ '^[0-9a-f]{64}$'),
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (anonymous_client_id, idempotency_key)
);

create table candidates (
  id uuid primary key,
  selection_session_id uuid not null references selection_sessions(id),
  display_label text not null check (char_length(display_label) between 1 and 32),
  display_name text,
  idempotency_key uuid not null,
  request_hash char(64) not null check (request_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now(),
  unique (selection_session_id),
  unique (selection_session_id, idempotency_key)
);

create table candidate_images (
  id uuid primary key,
  candidate_id uuid not null references candidates(id),
  content_type text not null check (content_type in ('image/jpeg', 'image/png')),
  size_bytes integer not null check (size_bytes between 1 and 5242880),
  source_sha256 char(64) not null check (source_sha256 ~ '^[0-9a-fA-F]{64}$'),
  sanitized_sha256 char(64) not null check (sanitized_sha256 ~ '^[0-9a-fA-F]{64}$'),
  width integer not null check (width > 0),
  height integer not null check (height > 0),
  status text not null check (status in ('received', 'processing', 'completed', 'failed', 'deleted')),
  error_code text,
  created_at timestamptz not null default now(),
  temporary_object_expires_at timestamptz,
  deleted_at timestamptz,
  unique (candidate_id)
);

create table extraction_versions (
  id uuid primary key,
  candidate_id uuid not null references candidates(id),
  source_image_id uuid not null references candidate_images(id),
  status text not null check (status in ('queued', 'processing', 'completed', 'failed', 'stale')),
  provenance jsonb not null default '{}'::jsonb,
  schema_version text not null,
  created_at timestamptz not null default now()
);

create table analysis_jobs (
  id uuid primary key,
  candidate_id uuid not null references candidates(id),
  candidate_image_id uuid not null references candidate_images(id),
  extraction_version_id uuid references extraction_versions(id),
  idempotency_key uuid not null,
  request_hash char(64) not null check (request_hash ~ '^[0-9a-f]{64}$'),
  status text not null check (status in ('queued', 'processing', 'completed', 'failed', 'stale')),
  stage text not null default 'queued' check (stage in ('queued', 'claimed', 'provider', 'persisting', 'cleaning', 'completed', 'failed')),
  attempt smallint not null check (attempt between 1 and 2),
  error_code text,
  processing_mode text check (processing_mode in ('fake-provider', 'openai-vision', 'test-fixture')),
  claimed_at timestamptz,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (candidate_id, idempotency_key)
);

create table evidence_items (
  id uuid primary key,
  extraction_version_id uuid not null references extraction_versions(id),
  field_name text not null,
  raw_text text,
  normalized_value text,
  model_confidence numeric(4,3) check (model_confidence between 0 and 1),
  information_status text not null check (information_status in ('explicit', 'inferred', 'unknown', 'conflict')),
  source_type text not null check (source_type in ('product-claim', 'merchant-claim', 'user-input', 'system-inference', 'brew-feedback')),
  verification_status text not null check (verification_status in ('unverified', 'user-confirmed', 'system-consistent', 'conflicting')),
  source_image_id uuid not null references candidate_images(id),
  source_location text not null,
  evidence_strength text not null check (evidence_strength in ('low', 'medium', 'high')),
  created_at timestamptz not null default now()
);

create table ai_call_logs (
  id uuid primary key,
  analysis_job_id uuid not null references analysis_jobs(id),
  provider text not null,
  model_identifier text not null,
  provider_version text,
  request_metadata jsonb not null default '{}'::jsonb,
  processing_mode text not null check (processing_mode in ('fake-provider', 'openai-vision', 'test-fixture')),
  latency_ms integer check (latency_ms >= 0),
  input_tokens integer check (input_tokens >= 0),
  output_tokens integer check (output_tokens >= 0),
  error_code text,
  created_at timestamptz not null default now()
);

create index selection_sessions_client_idx on selection_sessions(anonymous_client_id);
create index analysis_jobs_status_idx on analysis_jobs(status);
create index evidence_items_version_idx on evidence_items(extraction_version_id);
