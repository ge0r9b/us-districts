-- Derived from docs/v3/SCHEMA.sql. Idempotent.
-- CREATE ... IF NOT EXISTS does not change an object that already exists.
-- A later schema change is a new numbered file, not an edit to this one.

set search_path = usd, public;

-- ---------------------------------------------------------------------------
-- 7. Staging (see DATA_LOADING.md). Exactly the Election Data bot's row format.
-- ---------------------------------------------------------------------------

create table if not exists load_batch (
  id            bigint generated always as identity primary key,
  file_name     text not null,
  file_sha256   text not null,
  git_commit    text,                                -- data commit the file came from
  row_count     int,
  status        text not null default 'staged' check (status in ('staged','validated','rejected','applied','superseded')),
  started_at    timestamptz not null default now(),
  finished_at   timestamptz,
  report        jsonb not null default '{}',
  unique (file_sha256)                               -- same file twice = no-op
);

create unlogged table if not exists stg_result_row (
  load_batch_id bigint not null references load_batch(id) on delete cascade,
  line_no       int not null,
  state         text, year text, office text, district text,
  unit_id       text, unit_type text, candidate_id text, answer text,
  party         text, votes text, weight text, source_url text, retrieved_at text,
  method        text,                                -- column 14 in the 2022/2024 Senate files (DECISIONS.md D6)
  boundary_set  text,                                -- Q-E12: boundary_set.slug ('v2-2024'); if absent, derived from the layer
  primary key (load_batch_id, line_no)
);

create table if not exists stg_reject (
  load_batch_id bigint not null references load_batch(id) on delete cascade,
  line_no       int not null,
  rule          text not null,                       -- 'R03_votes_not_numeric', ...
  detail        text,
  primary key (load_batch_id, line_no, rule)
);

-- ---------------------------------------------------------------------------
-- 7b. Institution list ingest, refresh history and retractions (scraped lists, DATA_LOADING §15)
-- ---------------------------------------------------------------------------
create unlogged table if not exists stg_entity_row (
  batch_id      bigint not null references load_batch(id) on delete cascade,
  line_no       integer not null,
  origin        text not null,                       -- 'inst','governments_bot','companies_bot','user'
  raw           jsonb not null,                      -- the CSV row as read (columns by header name)
  proposed_id   text,                                -- entity_id from the file, or null
  matched_id    text,                                -- set by the dedupe step
  match_confidence numeric(4,3),
  action        text check (action in ('insert','update','merge','retract','review','reject')),
  primary key (batch_id, line_no)
);

-- Every applied change to an entity (refresh diffs, merges, moderation). Nothing is silently deleted.
create table if not exists entity_history (
  id          bigint generated always as identity primary key,
  entity_id   text not null,
  op          text not null check (op in ('insert','update','merge','retract','restore')),
  before      jsonb,
  after       jsonb,
  batch_id    bigint references load_batch(id),
  submission_id bigint,
  at          timestamptz not null default now()
);

create index if not exists entity_history_entity on entity_history (entity_id, at);

-- Explicit retract list (DECISIONS.md D7): a row missing from a newer scrape is NOT deleted; it is closed
-- (valid_to set) only when listed here.
create table if not exists retraction (
  id          bigint generated always as identity primary key,
  target      text not null check (target in ('entity','entity_relation','entity_location','result')),
  target_key  text not null,
  reason      text not null,
  effective   date not null,
  source_id   text references source(source_id),
  batch_id    bigint references load_batch(id)
);

-- User add / upload with moderation (phase 3+, needs auth: DECISIONS.md D21).
create table if not exists app_user (
  id          bigint generated always as identity primary key,
  auth_subject text not null unique,                 -- id from the auth provider
  display_name text,
  role        text not null default 'contributor' check (role in ('contributor','moderator','admin')),
  created_at  timestamptz not null default now()
);

create table if not exists submission (
  id            bigint generated always as identity primary key,
  submitter_id  bigint not null references app_user(id),
  channel       text not null check (channel in ('form','csv')),
  upload_id     uuid,                                -- groups rows from one CSV upload
  target_entity_id text references entity(entity_id),-- null = proposed new entity
  payload       jsonb not null,                      -- proposed entity / relation / location fields
  evidence_url  text not null,                       -- public source backing the claim
  status        text not null default 'pending' check (status in ('pending','approved','rejected','withdrawn')),
  match_confidence numeric(4,3),                     -- dedupe result against existing entities
  created_at    timestamptz not null default now(),
  decided_at    timestamptz,
  decided_by    bigint references app_user(id),
  decision_note text
);

create index if not exists submission_queue on submission (status, created_at) where status = 'pending';

create index if not exists submission_submitter on submission (submitter_id, created_at);

create table if not exists moderation_log (
  id            bigint generated always as identity primary key,
  submission_id bigint references submission(id),
  actor_id      bigint not null references app_user(id),
  action        text not null check (action in ('approve','reject','edit','merge','ban','unban','note')),
  detail        jsonb,
  at            timestamptz not null default now()
);

create table if not exists rate_limit_bucket (
  subject     text not null,                         -- 'user:<id>' or 'ip:<hash>'
  action      text not null,                         -- 'submit','upload'
  window_start timestamptz not null,
  count       integer not null default 0,
  primary key (subject, action, window_start)
);

-- ---------------------------------------------------------------------------
-- 8. Geocoder cache (no raw addresses kept; see GEOCODER.md)
-- ---------------------------------------------------------------------------
create table if not exists geocode_cache (
  query_hash   bytea primary key,                    -- sha256(normalized address)
  provider     text not null,                        -- 'census','geocodio','nominatim'
  lon          double precision, lat double precision,
  match_quality text,
  created_at   timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 8b. Global data version (ARCHITECTURE.md §5). One row, bumped by ingest.
-- ---------------------------------------------------------------------------
create table if not exists data_version (
  id        smallint primary key default 1 check (id = 1),
  dv        integer not null default 1,
  built_at  timestamptz not null default now()
);
