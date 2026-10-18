-- US Districts v3: Postgres 16 + PostGIS 3 schema (Phase 1 plan, NOT applied anywhere).
-- Explanation: docs/v3/SCHEMA.md. Ingest: docs/v3/DATA_LOADING.md.
-- Conventions: text natural keys (stable, human readable) next to bigint surrogate ids;
-- every fact row points at a source; nothing is deleted on reload (idempotent upserts).

create extension if not exists postgis;
create extension if not exists pg_trgm;      -- fuzzy name search (institution + geo filters)
create extension if not exists unaccent;

create schema if not exists usd;
set search_path = usd, public;

-- ---------------------------------------------------------------------------
-- 1. Tenancy + provenance
-- ---------------------------------------------------------------------------

-- Owner of a boundary set / dataset. 'public' (id 1) owns everything shipped today.
-- Paid custom boundary sets later belong to a customer tenant.
create table tenant (
  id          bigint generated always as identity primary key,
  slug        text not null unique,                 -- 'public', 'acme-campaign'
  name        text not null,
  kind        text not null default 'public' check (kind in ('public','customer','internal')),
  created_at  timestamptz not null default now()
);

create table license (
  id             bigint generated always as identity primary key,
  code           text not null unique,              -- 'CC0','CC-BY-4.0','public-record','NYT-C-UDA','ODbL','proprietary'
  name           text not null,
  url            text,
  commercial_ok  boolean,                            -- null = not verified yet (spec 9.3 'Check')
  attribution_required boolean not null default false,
  share_alike    boolean not null default false
);

-- One row per distinct source document / download (URL + retrieval time).
create table source (
  id            bigint generated always as identity primary key,
  url           text not null,
  retrieved_at  timestamptz not null,
  publisher     text,                                -- 'MIT Election Data + Science Lab', 'Alaska Division of Elections'
  title         text,
  license_id    bigint references license(id),
  attribution   text,                                -- exact credit line to display
  sha256        text,                                -- of the raw download, when the data bot records it
  notes         text,
  unique (url, retrieved_at)
);

-- ---------------------------------------------------------------------------
-- 2. Geography: boundary sets, units, geometry
-- ---------------------------------------------------------------------------

-- Unit types and their shared parent category (Q-G4, orchestrator, Oct 18, 2026): three school types matching
-- TIGER UNSD / ELSD / SCSD, all under the category 'school_district', so the UI can list them as one
-- "School districts" list while each unit keeps the board voters actually elect. Elementary and secondary
-- districts overlap (CA, IL, AZ, MT ...), so one point may resolve to several school units.
create table unit_category (
  category    text primary key,                    -- 'school_district', 'legislative', 'congressional', 'county', ...
  label       text not null                        -- UI list label: 'School districts'
);
create table unit_type_def (
  unit_type   text primary key,
  category    text not null references unit_category(category),
  label       text not null,                       -- 'Unified school district'
  tiger_set   text                                 -- 'unsd','elsd','scsd','cd','sldu','sldl','county','cousub','place','state'
);
insert into unit_category (category, label) values
  ('country','Countries'), ('state','States'), ('county','Counties'), ('town','Towns'), ('place','Places'),
  ('precinct','Precincts'), ('congressional','US House districts'), ('legislative_upper','State senate districts'),
  ('legislative_lower','State house districts'), ('school_district','School districts'), ('ward','Wards'), ('custom','Custom');
insert into unit_type_def (unit_type, category, label, tiger_set) values
  ('country','country','Country',null), ('state','state','State','state'), ('county','county','County','county'),
  ('county_subdivision','town','Town / township','cousub'), ('place','place','Place','place'),
  ('precinct','precinct','Precinct',null), ('ushouse','congressional','US House district','cd'),
  ('sldu','legislative_upper','State senate district','sldu'), ('sldl','legislative_lower','State house district','sldl'),
  ('school_unified','school_district','Unified school district','unsd'),
  ('school_elementary','school_district','Elementary school district','elsd'),
  ('school_secondary','school_district','Secondary school district','scsd'),
  ('ward','ward','Ward',null), ('custom','custom','Custom area',null);

-- A coherent set of polygons of one unit type and vintage, e.g. 'tiger-2024-sldl',
-- 'precincts-2024', 'precincts-2020'. Custom (paid) sets later: owner_tenant_id <> 1,
-- visibility 'private' or 'shared', license 'proprietary'.
create table boundary_set (
  id               bigint generated always as identity primary key,
  slug             text not null unique,
  unit_type        text not null references unit_type_def(unit_type),
  vintage_year     int  not null,                    -- boundary year (2024 = current)
  valid_from       date,
  valid_to         date,                             -- null = still in force
  is_current       boolean not null default false,   -- v2 rule: results shown in TODAY's boundaries
  owner_tenant_id  bigint not null default 1 references tenant(id),
  visibility       text not null default 'public' check (visibility in ('public','shared','private')),
  license_id       bigint references license(id),
  source_id        bigint references source(id),
  price_tier       text,                             -- null for free/public; reserved for paid custom sets
  feature_count    int,
  tiles_url        text,                             -- versioned PMTiles archive on the CDN
  built_at         timestamptz,
  meta             jsonb not null default '{}'
);
create index boundary_set_type_year on boundary_set (unit_type, vintage_year);
create unique index boundary_set_one_current
  on boundary_set (owner_tenant_id, unit_type) where is_current;

-- Who else may read a 'shared' set.
create table boundary_set_grant (
  boundary_set_id bigint not null references boundary_set(id) on delete cascade,
  tenant_id       bigint not null references tenant(id) on delete cascade,
  primary key (boundary_set_id, tenant_id)
);

-- Which boundary set a bot row's (unit_type, year) resolves to. Lets 2020 results land
-- either on 2020 precincts or (re-tabulated) on 2024 districts without guessing.
create table boundary_set_default (
  unit_type        text not null,
  results_year     int  not null,
  boundary_set_id  bigint not null references boundary_set(id),
  primary key (unit_type, results_year)
);

-- A geographic unit: one polygon in one boundary set (precinct, county, district, state ...).
create table unit (
  id               bigint generated always as identity primary key,
  boundary_set_id  bigint not null references boundary_set(id),
  unit_type        text not null references unit_type_def(unit_type),  -- category via unit_type_def (school_* -> school_district)
  unit_key         text not null,                    -- canonical key = TIGER GEOID where one exists ('42001' county,
                                                   -- '4201' CD ...), else the bot's unit_id (precincts: 'PA|Erie County|420491492')
  legacy_key       text,                             -- v2 name key ('Pennsylvania|Erie County', 'Ohio|<school name> (<county>)'); unique per
                                                   -- boundary set in the national layers after the Geo renames - see DATA_LOADING.md §8
  name             text not null,
  state_fips       char(2),
  state_abbr       char(2),
  geoid            text,                             -- Census GEOID where one exists
  parent_unit_id   bigint references unit(id),       -- precinct -> county -> state (containment, same vintage)
  area_m2          double precision,
  centroid         geometry(Point, 4326),
  bbox             box2d,
  meta             jsonb not null default '{}',
  unique (boundary_set_id, unit_key)
);
create index unit_parent on unit (parent_unit_id);
create unique index unit_legacy on unit (boundary_set_id, legacy_key) where legacy_key is not null;
create index unit_geoid on unit (geoid);
create index unit_state_type on unit (state_abbr, unit_type);
create index unit_name_trgm on unit using gin (lower(name) gin_trgm_ops);
create index unit_centroid_gist on unit using gist (centroid);

-- Geometry per level of detail. lod 0 = full detail used for point-in-polygon and
-- area weighting; lod 1..3 = simplified copies for low zooms / dynamic MVT fallback.
create table unit_geom (
  unit_id     bigint not null references unit(id) on delete cascade,
  lod         smallint not null check (lod between 0 and 3),
  tolerance_m real not null,                         -- 0, ~40, ~200, ~1000
  min_zoom    smallint not null,
  geom        geometry(MultiPolygon, 4326) not null,
  primary key (unit_id, lod)
);
create index unit_geom_gist_lod0 on unit_geom using gist (geom) where lod = 0;
create index unit_geom_gist_lod2 on unit_geom using gist (geom) where lod = 2;

-- Overlap weights between units of different sets (precinct -> district, 2020 precinct ->
-- 2024 precinct). Used to re-tabulate; weight = share of the source unit's votes assigned.
create table unit_crosswalk (
  from_unit_id bigint not null references unit(id) on delete cascade,
  to_unit_id   bigint not null references unit(id) on delete cascade,
  weight       numeric(9,8) not null check (weight > 0 and weight <= 1),
  method       text not null check (method in ('exact','area','population','votes_in_split','official')),
  source_id    bigint references source(id),
  primary key (from_unit_id, to_unit_id)
);
create index unit_crosswalk_to on unit_crosswalk (to_unit_id);

-- ---------------------------------------------------------------------------
-- 3. Institutions (top filter) vs geography (bottom filter)
-- ---------------------------------------------------------------------------

-- Anything selectable in the institution filter: governments, chambers, school districts,
-- later companies/brands. May have no region at all (has_region = false).
create table entity (
  id            bigint generated always as identity primary key,
  entity_key    text not null unique,                -- 'us', 'us-pa', 'us-pa-house', 'us-pa-sch-4218990'
  kind          text not null check (kind in (
                  'country','state','province','county','city','town','township','borough','village',
                  'legislature','chamber','school_district','office','company','brand','subsidiary','other')),
  gov_kind      text check (gov_kind in ('sovereign','incorporated','body','private')),
                                                   -- v2 wording rule: states/countries sovereign; counties, cities,
                                                   -- towns, townships, boroughs incorporated; never 'incorporated state'
  name          text not null,
  short_name    text,                                -- 'PA'
  parent_id     bigint references entity(id),        -- institution hierarchy (US > PA > PA House)
  has_region    boolean not null default true,
  icon_flag     text,                                -- institution-field icon (flag PNG / type icon)
  owner_tenant_id bigint not null default 1 references tenant(id),
  meta          jsonb not null default '{}'
);
create index entity_parent on entity (parent_id);
create index entity_kind on entity (kind);
create index entity_name_trgm on entity using gin (lower(name) gin_trgm_ops);

-- Shared names: both filters resolve aliases through one table (PA = Pennsylvania, USA = US).
create table alias (
  alias       text not null,                         -- lower(unaccent(...))
  entity_id   bigint references entity(id) on delete cascade,
  unit_id     bigint references unit(id) on delete cascade,
  kind        text not null default 'abbr' check (kind in ('abbr','alt','historic','postal')),
  check ((entity_id is null) <> (unit_id is null))
);
create index alias_alias on alias (alias text_pattern_ops);
create unique index alias_entity_uq on alias (alias, entity_id) where entity_id is not null;
create unique index alias_unit_uq   on alias (alias, unit_id)   where unit_id   is not null;

-- How an institution relates to geography.
--  'jurisdiction'  : the entity governs this area (Pennsylvania -> PA state polygon; a county gov -> county)
--  'seat_district' : a chamber's seat area (PA House -> each sldl unit)
--  'same_as'       : entity and unit are the same thing (school district -> its polygon)
create table entity_unit (
  entity_id  bigint not null references entity(id) on delete cascade,
  unit_id    bigint not null references unit(id) on delete cascade,
  role       text not null check (role in ('jurisdiction','seat_district','same_as')),
  primary key (entity_id, unit_id, role)
);
create index entity_unit_unit on entity_unit (unit_id);

-- ---------------------------------------------------------------------------
-- 4. Contests, answers, candidates, parties
-- ---------------------------------------------------------------------------

create table party (
  id          bigint generated always as identity primary key,
  party_key   text not null unique,                  -- 'dem','rep','lib','grn','ind','nonpartisan'
  name        text not null,
  color       text,                                  -- hex, used for single-answer shading
  aliases     text[] not null default '{}'           -- raw spellings seen in sources ('Democratic','DEM')
);

-- People, stable across years and offices. candidate_key comes from the Election Data
-- bot's candidate directory (e.g. 'trump-donald-j'); never re-keyed.
create table candidate (
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
create table office (
  id           bigint generated always as identity primary key,
  office_key   text not null unique,                 -- bot 'office' normalized: 'president','us_senate','us_house','state_senate','state_house','school_board','ballot_measure'
  label        text not null,                        -- 'President'
  entity_id    bigint references entity(id),         -- institution it belongs to (US, PA House ...)
  scope_entity_id bigint references entity(id),      -- v2 rule: topic scoped to its entity (President -> United States)
  district_unit_type text                            -- unit_type of the seat areas, null for at-large/statewide
);

-- One race / question at one time point.
create table contest (
  id               bigint generated always as identity primary key,
  contest_key      text not null unique,             -- '{year}|{state}|{office}|{district}' e.g. '2024|US|president|', '2024|PA|state_house|101'
  office_id        bigint not null references office(id),
  year             int not null check (year between 1789 and 2100),  -- any year (2016/2020/2024 today)
  election_date    date,
  stage            text not null default 'general' check (stage in ('general','primary','runoff','special','recall','poll')),
  kind             text not null default 'candidate' check (kind in ('candidate','measure','poll')),
  state_abbr       char(2),                          -- null / 'US' for national
  district_code    text,                             -- bot 'district' ('' for statewide)
  district_unit_id bigint references unit(id),       -- seat polygon when known
  jurisdiction_entity_id bigint references entity(id),
  vote_for         smallint not null default 1,      -- multi-seat / multi-choice
  title            text,                             -- ballot measure title
  is_static        boolean not null default true,    -- certified past election: served from static packs
  data_version     int not null default 1            -- bumped on every change; part of cache keys
);
create index contest_year_office on contest (year, office_id);
create index contest_state_year on contest (state_abbr, year);

-- Answers: any number per contest (candidates, Yes/No, multi-choice, write-ins, 'other').
-- answer_key is stable ACROSS years for the same slot ('dem_nominee') so deltas compare
-- like with like (v2 rule: answerId separate from candidateId).
create table answer (
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
create index answer_candidate on answer (candidate_id);

-- ---------------------------------------------------------------------------
-- 5. Results
-- ---------------------------------------------------------------------------

-- One row per (contest, reporting unit, answer). weight = share of that unit's votes
-- that belongs to the contest/target (1 = whole unit; <1 = split/area-weighted).
create table result (
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
  source_id      bigint not null references source(id),
  retrieved_at   timestamptz not null,
  load_batch_id  bigint,
  updated_at     timestamptz not null default now(),
  primary key (contest_id, unit_id, answer_id)
);
create index result_unit on result (unit_id, contest_id);
create index result_source on result (source_id);

-- Unit-level totals incl. ballots not attributed to a listed answer (undervotes etc.)
-- when the source reports them; otherwise total = sum of answers.
create table result_total (
  contest_id   bigint not null references contest(id) on delete cascade,
  unit_id      bigint not null references unit(id),
  total_votes  numeric(16,6) not null,
  coverage     real check (coverage between 0 and 1),  -- v2: < 0.5 coverage stays gray
  is_estimate  boolean not null default false,
  source_id    bigint references source(id),
  primary key (contest_id, unit_id)
);

-- History of overwritten values (audit; never lose what a source said).
create table result_history (
  contest_id bigint not null, unit_id bigint not null, answer_id bigint not null,
  votes numeric(14,4), weight numeric(9,8), source_id bigint, retrieved_at timestamptz,
  replaced_at timestamptz not null default now()
);
create index result_history_key on result_history (contest_id, unit_id, answer_id);

-- ---------------------------------------------------------------------------
-- 6. Precomputed aggregates (instant reads)
-- ---------------------------------------------------------------------------

-- Per contest x unit: answers in one row, shares, winner, margin. Refreshed per contest
-- after a load (DATA_LOADING.md step 6). Reads never touch `result` directly.
create materialized view unit_contest_agg as
select r.contest_id,
       r.unit_id,
       u.unit_type,
       t.category,
       u.parent_unit_id,
       u.state_abbr,
       sum(r.weighted_votes)                                         as total,
       jsonb_object_agg(a.answer_key, round(r.weighted_votes, 2))    as votes,
       bool_or(r.is_estimate)                                         as is_estimate,
       (array_agg(a.answer_key order by r.weighted_votes desc))[1]    as leader_key
from result r
join answer a on a.id = r.answer_id
join unit   u on u.id = r.unit_id
join unit_type_def t on t.unit_type = u.unit_type
group by r.contest_id, r.unit_id, u.unit_type, t.category, u.parent_unit_id, u.state_abbr;
create unique index unit_contest_agg_pk on unit_contest_agg (contest_id, unit_id);
create index unit_contest_agg_list on unit_contest_agg (contest_id, unit_type, state_abbr);
create index unit_contest_agg_cat on unit_contest_agg (contest_id, category, state_abbr);  -- one 'School districts' list
create index unit_contest_agg_parent on unit_contest_agg (contest_id, parent_unit_id);

-- Bar-list rows: one row per contest x unit x answer with share and rank, so
-- "sorted high to low" is an index range scan, not a sort.
create materialized view answer_share as
with s as (
  select r.contest_id, r.unit_id, u.unit_type, t.category, u.parent_unit_id, u.state_abbr, a.answer_key,
         r.weighted_votes as votes,
         r.weighted_votes / nullif(sum(r.weighted_votes) over (partition by r.contest_id, r.unit_id), 0) as share,
         r.is_estimate
  from result r
  join answer a on a.id = r.answer_id
  join unit   u on u.id = r.unit_id
  join unit_type_def t on t.unit_type = u.unit_type
)
select s.*,
       rank() over (partition by contest_id, category, state_abbr, answer_key
                    order by share desc nulls last) as rank_in_list
from s;
create unique index answer_share_pk on answer_share (contest_id, unit_id, answer_key);
create index answer_share_sorted on answer_share (contest_id, category, state_abbr, answer_key, share desc nulls last);

-- ---------------------------------------------------------------------------
-- 7. Staging (see DATA_LOADING.md). Exactly the Election Data bot's row format.
-- ---------------------------------------------------------------------------

create table load_batch (
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

create unlogged table stg_result_row (
  load_batch_id bigint not null references load_batch(id) on delete cascade,
  line_no       int not null,
  state         text, year text, office text, district text,
  unit_id       text, unit_type text, candidate_id text, answer text,
  party         text, votes text, weight text, source_url text, retrieved_at text,
  method        text,                                -- optional extra column (DECISIONS.md D6)
  primary key (load_batch_id, line_no)
);

create table stg_reject (
  load_batch_id bigint not null references load_batch(id) on delete cascade,
  line_no       int not null,
  rule          text not null,                       -- 'R03_votes_not_numeric', ...
  detail        text,
  primary key (load_batch_id, line_no, rule)
);

-- ---------------------------------------------------------------------------
-- 8. Geocoder cache (no raw addresses kept; see GEOCODER.md)
-- ---------------------------------------------------------------------------
create table geocode_cache (
  query_hash   bytea primary key,                    -- sha256(normalized address)
  provider     text not null,                        -- 'census','geocodio','nominatim'
  lon          double precision, lat double precision,
  match_quality text,
  created_at   timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 9. Read-only role for the API (no writes from the web tier)
-- ---------------------------------------------------------------------------
-- create role usd_api login password '...' (set at provisioning time, not here);
-- grant usage on schema usd to usd_api; grant select on all tables in schema usd to usd_api;
-- Private/shared boundary sets are filtered in the API by tenant (and later RLS on unit/boundary_set).


-- Proposed (Oct 18, 2026 drift check; data-v3/inst on data/inst-officeholders).
-- Who holds a seat, per unit and date range. Vintage-aware like results: a 2020 House
-- member is joined to the cd116 unit, a current one to cd119.
create table officeholder (
  id           bigserial primary key,
  unit_id      bigint not null references unit(id),
  entity_id    bigint references entity(id),            -- chamber / body, e.g. us-house, pa-senate
  seat         text,                                     -- multi-member seats (NH floterial etc.)
  person_key   text not null,                            -- 'bioguide:B001323', 'ocd-person/<uuid>'
  name         text not null,
  party        text,
  status       text not null default 'serving',          -- serving | vacant | ...
  term_start   date,
  term_end     date,
  source_id    bigint references source(id),
  unique (unit_id, seat, person_key, term_start)
);
create index officeholder_unit on officeholder (unit_id);
