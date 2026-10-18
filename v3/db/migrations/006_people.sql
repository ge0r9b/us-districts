-- Derived from docs/v3/SCHEMA.sql. Idempotent.
-- CREATE ... IF NOT EXISTS does not change an object that already exists.
-- A later schema change is a new numbered file, not an edit to this one.

set search_path = usd, public;

-- ---------------------------------------------------------------------------
-- 5b. People and officeholders (Q-I1; data-v3/inst/ on data/inst-officeholders)
-- ---------------------------------------------------------------------------
-- One canonical person_id 'scheme:id' per person, chosen in priority order (Q-I1/Q-I2, data/inst-officeholders 9d25f25):
--   bioguide:<ID> (permanent) > ocd-person:<uuid> (OpenStates, prefix normalized to 'ocd-person:'; can change on a
--   duplicate merge) > <st>-leg:<id> (session-scoped). No state legislator is bioguide-canonical; no cross-level name matching.
create table if not exists person (
  person_id     text primary key,                    -- 'bioguide:B001323', 'ocd-person:a84a3fe8-...', 'vt-leg:vt-41827'
  scheme        text not null,                        -- 'bioguide' | 'ocd-person' | '<st>-leg' (e.g. 'vt-leg')
  check (scheme in ('bioguide','ocd-person','ca-mp') or scheme ~ '^[a-z]{2}-leg$' or scheme ~ '^ca-[a-z]{2}-leg$'),
                                                      -- ca-mp:<House of Commons PersonId>; ca-<iso>-leg:<agency id>
  bioguide      text unique,
  ocd_person    text unique,
  official_ids  jsonb not null default '{}',          -- other official ids (state roster ids, FEC ...)
  sources       text,                                 -- persons.csv 'sources' (which officeholder files list the person)
  source_record_id text,                              -- id inside the primary source, when given; sources: person_source
  name          text not null,
  candidate_id  bigint references candidate(id),      -- same human as an election candidate, when linked
  meta          jsonb not null default '{}'
);

create index if not exists person_name_trgm on person using gin (lower(name) gin_trgm_ops);

-- Former canonical ids (OpenStates merges, session-scoped ids that were later resolved) -> current person.
create table if not exists person_alias (
  alias_id      text primary key,                    -- e.g. an old ocd-person:<uuid>, 'mn-leg:mn-house-15367'
  person_id     text not null references person(person_id) on update cascade on delete cascade,
  kind          text not null default 'former_canonical' check (kind in ('former_canonical','session_scoped','official')),
  source_commit text                                  -- OpenStates commit where the alias was recorded
);

create index if not exists person_alias_person on person_alias (person_id);

-- Who held a seat (unit) over a date range. Vacancy = person_id null + status 'vacant'.
create table if not exists officeholder (
  id            bigint generated always as identity primary key,
  unit_id       bigint not null references unit(id),  -- seat polygon (cd116/cd119, sldl2024 ... via boundary_set)
  entity_id     text references entity(entity_id),    -- chamber entity ('us-house', 'chamber:al-lower', 'chamber:ne-upper')
  unit_layer    text,                                 -- as in the file: 'cd','sldu','sldl' (resolved to unit_id, DATA_LOADING §13)
  unit_geoid    text,
  unit_vintage  smallint,
  unit_plan     text,                                 -- 'cd116','cd119','sldl2024','sldu2024'; Canada 'rep-order-2023'
  unit_key      text,                                 -- file unit_key: seat keys, Canadian keys (FED_NUM); unit_id = (boundary_set, unit_key)
  boundary_set  text,                                 -- file 'boundary_set' ('v2-2024', 'tiger-2020-cd116'); seat units use the same slug
  join_status   text,                                 -- 'joined','joined_unpaired_2020','no_v3_unit','no_v3_unit_floterial','no_v3_unit_tribal'
  source_record_id text,                              -- the record's id inside its source ('AK00', OpenStates file); was 'source_id'
  seat          text,                                 -- seat number within a multi-member district (NH, VT, WV ...)
  person_id     text references person(person_id) on update cascade,
  name          text not null,                        -- name as recorded in the roster row
  party         text,
  status        text not null,                        -- 'elected','serving','serving_at_2025-04-01','vacant'
  date_flags    text,                                 -- 'term_start_missing', 'term_end_open' (;-list)
  valid_from    date,
  valid_to      date,                                 -- null = open-ended / current
  elected_date  date,
                                                      -- sources: officeholder_source; the upstream commit comes from source.commit
  check (status <> 'vacant' or person_id is null),
  unique nulls not distinct (unit_id, seat, person_id, valid_from),
  check (valid_to is null or valid_from is null or valid_to >= valid_from)
);

create index if not exists officeholder_unit_dates on officeholder (unit_id, valid_from, valid_to);

create index if not exists officeholder_person on officeholder (person_id);

-- County government status (data-v3/inst/county_government.csv, f1d64f6): one row per county GEOID x vintage
-- (3,144 for 2024 + 8 for the 2020 CT counties).
create table if not exists county_government (
  entity_id          text not null references entity(entity_id),   -- 'county:<county_geoid>' (exists for all 3,152 rows)
  county_geoid       char(5) not null,
  vintage            smallint not null,
  boundary_set       text not null,                  -- 'v2-2024' (2024) / 'tiger-2020-county' (2020)
  county_name        text not null,
  has_own_government text not null check (has_own_government in ('yes','no','unknown')),
  gov_status         text check (gov_status in ('government','area_only','dependent')),
  government_kind    text,                           -- 'county', 'consolidated_city_county', ...
  cog_pid6           text,
  govbot_entity_id   text,                           -- Governments bot id ('cog:100001')
  cog_unit_name      text,
  cog_unit_type      text,                           -- '1 - COUNTY'
  tiger_funcstat     char(1),
  agrees_with_tiger  text,                           -- 'yes' / 'no'
  government_note    text,
  source_record_id   text,
  primary key (county_geoid, vintage)                -- sources: county_government_source
);

create index if not exists county_government_entity on county_government (entity_id);

-- Row <-> source link tables (files cite a ';'-list of sources.csv source_ids per row).
create table if not exists entity_source (
  entity_id  text not null references entity(entity_id) on delete cascade,
  source_id  text not null references source(source_id),
  ord        smallint not null default 1,            -- position in the row's ';'-list
  primary key (entity_id, source_id)
);

create table if not exists entity_geoid_source (
  entity_id text not null, unit_layer text not null, geoid text not null, vintage smallint not null,
  source_id text not null references source(source_id),
  ord       smallint not null default 1,
  primary key (entity_id, unit_layer, geoid, vintage, source_id),
  foreign key (entity_id, unit_layer, geoid, vintage) references entity_geoid on delete cascade
);

create table if not exists entity_location_source (
  location_id bigint not null references entity_location(location_id) on delete cascade,
  source_id   text not null references source(source_id),
  ord         smallint not null default 1,
  primary key (location_id, source_id)
);

create table if not exists officeholder_source (
  officeholder_id bigint not null references officeholder(id) on delete cascade,
  source_id       text not null references source(source_id),
  ord             smallint not null default 1,
  primary key (officeholder_id, source_id)
);

create table if not exists person_source (
  person_id  text not null references person(person_id) on update cascade on delete cascade,
  source_id  text not null references source(source_id),
  ord        smallint not null default 1,
  primary key (person_id, source_id)
);

create table if not exists county_government_source (
  county_geoid char(5) not null, vintage smallint not null,
  source_id    text not null references source(source_id),
  ord          smallint not null default 1,
  primary key (county_geoid, vintage, source_id),
  foreign key (county_geoid, vintage) references county_government on delete cascade
);

create index if not exists entity_source_source on entity_source (source_id);

create index if not exists officeholder_source_source on officeholder_source (source_id);
