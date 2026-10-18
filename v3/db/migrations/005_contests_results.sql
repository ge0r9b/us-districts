-- Derived from docs/v3/SCHEMA.sql. Idempotent.
-- CREATE ... IF NOT EXISTS does not change an object that already exists.
-- A later schema change is a new numbered file, not an edit to this one.

set search_path = usd, public;

-- ---------------------------------------------------------------------------
-- 4. Contests, answers, candidates, parties
-- ---------------------------------------------------------------------------

create table if not exists party (
  id          bigint generated always as identity primary key,
  party_key   text not null unique,                  -- 'dem','rep','lib','grn','ind','nonpartisan'
  name        text not null,
  color       text,                                  -- hex, used for single-answer shading
  aliases     text[] not null default '{}'           -- raw spellings seen in sources ('Democratic','DEM')
);

-- People, stable across years and offices. candidate_key comes from the Election Data
-- bot's candidate directory (e.g. 'trump-donald-j'); never re-keyed.
create table if not exists candidate (
  id            bigint generated always as identity primary key,
  candidate_key text not null unique,
  full_name     text not null,
  short_name    text,
  photo_path    text,
  photo_credit  text,
  photo_license_id bigint references license(id),
  meta          jsonb not null default '{}'
);

-- An office / topic (US President, PA House, ballot question type, later polls).
create table if not exists office (
  id           bigint generated always as identity primary key,
  office_key   text not null unique,                 -- bot 'office' normalized: 'president','us_senate','us_house','state_senate','state_house','school_board','ballot_measure'
  label        text not null,                        -- 'President'
  entity_id    text references entity(entity_id),    -- institution it belongs to (US, PA House ...)
  scope_entity_id text references entity(entity_id),      -- v2 rule: topic scoped to its entity (President -> United States)
  district_unit_type text                            -- unit_type of the seat areas, null for at-large/statewide
);

-- One race / question at one time point.
create table if not exists contest (
  id               bigint generated always as identity primary key,
  contest_key      text not null unique,             -- '{year}|{state}|{office}|{district}' e.g. '2024|US|president|', '2022|GA|us_senate_runoff|'
                                                   -- office token carries special/runoff (Q-E13: us_senate, us_senate_special, us_senate_runoff);
                                                   -- stage is derived from it ('special', 'runoff', else 'general')
  office_id        bigint not null references office(id),
  year             int not null check (year between 1789 and 2100),  -- any year (2016/2020/2024 today)
  election_date    date,
  stage            text not null default 'general' check (stage in ('general','primary','runoff','special','recall','poll')),
  kind             text not null default 'candidate' check (kind in ('candidate','measure','poll')),
  state_abbr       char(2),                          -- null / 'US' for national
  district_code    text,                             -- bot 'district' ('' for statewide)
  district_unit_id bigint references unit(id),       -- seat polygon when known
  jurisdiction_entity_id text references entity(entity_id),
  vote_for         smallint not null default 1,      -- multi-seat / multi-choice
  title            text,                             -- ballot measure title
  is_static        boolean not null default true,    -- certified past election: served from static packs
  data_version     int not null default 1            -- bumped on every change; part of cache keys
);

create index if not exists contest_year_office on contest (year, office_id);

create index if not exists contest_state_year on contest (state_abbr, year);

-- Answers: any number per contest (candidates, Yes/No, multi-choice, write-ins, 'other').
-- answer_key is stable ACROSS years for the same slot ('dem_nominee') so deltas compare
-- like with like (v2 rule: answerId separate from candidateId).
create table if not exists answer (
  id            bigint generated always as identity primary key,
  contest_id    bigint not null references contest(id) on delete cascade,
  answer_key    text not null,                       -- 'dem_nominee','rep_nominee','other','yes','no','choice:3','cand:<candidate_key>'
                                                   -- presidential: dem_nominee = Clinton 2016 / Biden 2020 / Harris 2024 (one slot, any number of years)
  label         text not null,
  candidate_id  bigint references candidate(id),
  party_id      bigint references party(id),
  color         text,
  ballot_order  smallint,
  is_writein    boolean not null default false,
  is_aggregate  boolean not null default false,      -- 'All other candidates and write-ins' (v2 'other' = total - dem - rep)
  unique (contest_id, answer_key)
);

create index if not exists answer_candidate on answer (candidate_id);

-- ---------------------------------------------------------------------------
-- 5. Results
-- ---------------------------------------------------------------------------

-- One row per (contest, reporting unit, answer). weight = share of that unit's votes
-- that belongs to the contest/target (1 = whole unit; <1 = split/area-weighted).
create table if not exists result (
  contest_id     bigint not null references contest(id) on delete cascade,
  unit_id        bigint not null references unit(id),
  answer_id      bigint not null references answer(id) on delete cascade,
  votes          numeric(14,4) not null check (votes >= 0),   -- numeric: re-tabulation yields fractions
  weight         numeric(9,8)  not null default 1 check (weight > 0 and weight <= 1),
  weighted_votes numeric(16,6) generated always as (votes * weight) stored,
  is_estimate    boolean not null default false,  -- drives the ≈ mark
  method         text not null default 'official' check (method in (
                   'official','whole_county','area_weighted','allocated','town_apportioned',
                   'votes_in_split','retabulated','v2_import')),
  source_id      text not null references source(source_id),
  retrieved_at   timestamptz not null,
  load_batch_id  bigint,
  updated_at     timestamptz not null default now(),
  primary key (contest_id, unit_id, answer_id)
);

create index if not exists result_unit on result (unit_id, contest_id);

create index if not exists result_source on result (source_id);

-- Unit-level totals incl. ballots not attributed to a listed answer (undervotes etc.)
-- when the source reports them; otherwise total = sum of answers.
create table if not exists result_total (
  contest_id   bigint not null references contest(id) on delete cascade,
  unit_id      bigint not null references unit(id),
  total_votes  numeric(16,6) not null,
  coverage     real check (coverage between 0 and 1),  -- v2: < 0.5 coverage stays gray
  is_estimate  boolean not null default false,
  source_id    text references source(source_id),
  primary key (contest_id, unit_id)
);

-- History of overwritten values (audit; never lose what a source said).
create table if not exists result_history (
  contest_id bigint not null, unit_id bigint not null, answer_id bigint not null,
  votes numeric(14,4), weight numeric(9,8), source_id text, retrieved_at timestamptz,
  replaced_at timestamptz not null default now()
);

create index if not exists result_history_key on result_history (contest_id, unit_id, answer_id);

-- v2-parity display slots (Q-E13). v3 keeps every answer; this maps one answer to v2's 'd' and 'r'
-- columns for the D / R / total view. 'd' = the Democratic nominee, unless an independent beat the
-- Democrat statewide or there was no Democrat, then that independent (King ME 2024, Sanders VT, Osborn
-- NE 2024, McMullin UT 2022, Chesbro AK 2022 first round, Chambers LA 2022, Christiansen ND 2022).
-- 'r' = the Republican (AK 2022: Murkowski, first round). Colour still follows answer.party_id.
create table if not exists contest_display_slot (
  contest_id  bigint not null references contest(id) on delete cascade,
  slot        char(1) not null check (slot in ('d','r')),
  answer_id   bigint not null references answer(id) on delete cascade,
  rule        text not null default 'dem_nominee',   -- 'dem_nominee' | 'independent_beat_dem' | 'no_dem' | 'rep_nominee'
  note        text,
  primary key (contest_id, slot)
);
