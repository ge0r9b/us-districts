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
  source_key    text unique,                         -- sources.csv source_id ('census-cog2022-0fba3401'); entity/officeholder/location/relation rows carry it
  source_commit text,                                -- upstream commit (congress-legislators, OpenStates) when given
  license       text,                                -- license as stated by the source, verbatim (generic provenance)
  license_id    bigint references license(id),
  license_verified boolean not null default false,   -- true once the license/terms page has been read (date in license_checked_at)
  license_checked_at date,
  robots_ok     boolean,                             -- scraped lists: robots.txt and terms of service allow it (DATA_LOADING §15.3)
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
  slug             text not null unique,             -- = the bot rows' boundary_set token (Q-E12): lowercase-hyphen,
                                                   -- e.g. 'v2-2024' (v2's 2024 polygons/GEOIDs; current + 2024), 'tiger-2020-cd116' (2020 House),
                                                   -- 'tiger-2020-sldu' / 'tiger-2020-sldl' (2020 state legislature, 2018 plans). Geometry joins on this, NOT on year.
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

-- Entity registry (agreed with Institutions; data-v3/inst/entities.csv + entity_geoid_xwalk.csv).
-- One row per government / institution, NO vintage. entity_id is opaque and frozen at first-seen
-- kind + GEOID ('county:01001', 'muni:place:0107000', 'town:cousub:0911001080', 'school:0100003',
-- 'state:01', 'nation:us', 'territory:72'); chambers use 'chamber:<st>-lower' / 'chamber:<st>-upper' ('chamber:al-lower');
-- Bot entities use bare scheme:id (like person ids): companies 'lei:<LEI>' > 'cik:<CIK>' > other documented scheme
-- (the non-canonical ids go to alias, kind='external_id'); governments 'cog:<id>', 'fr:<id>', 'bia:<slug>'.
-- unicameral Nebraska is 'chamber:ne-upper' (no -lower), DC is 'chamber:dc-council' (kind dc_council), the US House is 'us-house'.
-- Verified on data/inst-entities 8e1db01: 54,144 entities (municipality 19,525, township 18,076, school_unified 10,872,
-- county 3,080, school_elementary 1,952, school_secondary 481, chamber 100, state 51, territory 5, nation 1, dc_council 1).
-- The same entity_id carries across boundary vintages; a new id is minted only when the government
-- itself changes (merger, dissolution, incorporation, CT planning regions), linked by predecessor/successor.
-- District seats are UNITS, not entities (officeholder = chamber entity + unit + seat).
create table entity (
  entity_id     text primary key,
  kind          text not null check (kind in (
                  'nation','territory','state','county','municipality','township',
                  'school_unified','school_elementary','school_secondary',   -- Q-G4; unit_category 'school_district'
                  'chamber','dc_council',
                  'government_other',                                        -- Governments bot (special districts, authorities, foreign govts)
                  'company','nonprofit','fund',                              -- Companies bot; subsidiaries/brands are companies linked by entity_relation
                  'other')),
  state_fips    char(2),
  state         text,
  name          text not null,                       -- TIGER NAMELSAD
  label         text check (label in ('sovereign','incorporated','unincorporated')),
                                                   -- v2 wording rule: states sovereign; never 'incorporated state'
  gov_status    text check (gov_status in ('government','area_only','dependent')),  -- CoG 2022
  parent_id     text references entity(entity_id),   -- containment tree (state:42 > chamber:pa-lower); corporate ownership is entity_relation
                                                   -- predecessor_id / successor_id (;-lists in entities.csv) load into entity_succession
  valid_from    date,
  valid_to      date,
  v2_layer      text[],                              -- ';'-list in the CSV: 'v2:counties', 'v2:parts'
  v2_key        text[],                              -- 'Alabama|Autauga County' (parts rows: state|county|name)
  v2_row        text[],                              -- 'v2:counties#342' (informational; shifts between builds)
  legal_form_code text,                              -- ISO 20275 ELF code (GLEIF 'legal_form_code', e.g. 'XTIQ'); companies/nonprofits/funds
  legal_form    text,                                -- ELF label ('Corporation', 'Business Corporation'), else GLEIF OtherLegalForm
  feed          text,                                -- which build fed the row: 'tiger/cog' (54,042) or 'inst-lane' (102)
  level         text,                                -- extras: federal / state / county / local
  type          text,                                -- finer type (TIGER LSAD text, 'city'); companies: 'public','private','nonprofit'
  cog_pid6      text,                                -- CoG 2022 unit id
  flags         text[],                              -- review flags ('gov_status_unknown:...')
  origin        text not null default 'inst' check (origin in ('inst','governments_bot','companies_bot','user')),
  source_id     bigint references source(id),        -- source, source_url, retrieved_at, license
  has_region    boolean not null default true,
  icon_flag     text,
  owner_tenant_id bigint not null default 1 references tenant(id),
  meta          jsonb not null default '{}',
  check (valid_to is null or valid_from is null or valid_to >= valid_from)
);
create index entity_parent on entity (parent_id);
create index entity_kind on entity (kind, state_fips);
create index entity_v2 on entity using gin (v2_key);
create index entity_name_trgm on entity using gin (lower(name) gin_trgm_ops);

-- Government changes (merger, dissolution, incorporation, CT planning regions): many-to-many.
create table entity_succession (
  predecessor_id text not null references entity(entity_id),
  successor_id   text not null references entity(entity_id),
  effective      date,
  source_id      bigint references source(id),
  primary key (predecessor_id, successor_id)
);

-- entity_geoid_xwalk.csv: one row per entity x unit_layer x vintage (the join to geography; governments).
create table entity_geoid (
  entity_id   text not null references entity(entity_id) on delete cascade,
  unit_layer  text not null,                         -- = unit_type_def.tiger_set: 'state','county','cousub','place','unsd','elsd','scsd'
  geoid       text not null,
  vintage     smallint not null,
  relation    text not null,                         -- 'primary','coextensive','also_cousub','consolidated_city_county',
                                                   -- 'independent_city_county_equivalent','consolidated_town_city','federal_district_city'
  overlap     text check (overlap in ('equal','split','contained')),
  source_id   bigint references source(id),
  primary key (entity_id, unit_layer, geoid, vintage)
);
create index entity_geoid_lookup on entity_geoid (unit_layer, geoid, vintage);

-- Companies: parent/subsidiary ownership over time (the containment parent_id stays geographic/institutional).
create table entity_relation (
  parent_id     text not null references entity(entity_id),
  child_id      text not null references entity(entity_id),
  relation      text not null default 'direct_parent' check (relation in ('direct_parent','ultimate_parent','ex21_subsidiary',
                                                   'fund_managed_by','subfund_of','feeder_to','brand','division','joint_venture')),
  ownership_pct numeric(5,2) check (ownership_pct is null or ownership_pct between 0 and 100),
  valid_from    date,
  valid_to      date,
  source_id     bigint references source(id),
  check (parent_id <> child_id),
  check (valid_to is null or valid_from is null or valid_to >= valid_from),
  unique nulls not distinct (parent_id, child_id, relation, valid_from)
);
create index entity_relation_child on entity_relation (child_id);

-- Companies: where they are (HQ, sites). Either a point or a GEOID (or both).
create table entity_location (
  id          bigint generated always as identity primary key,
  entity_id   text not null references entity(entity_id) on delete cascade,
  role        text not null check (role in ('hq_in','site_in','registered_office','other')),  -- company_locations.csv 'relation'
  geoid_layer text,                                  -- 'place','county','state' (resolved unit via geoid at load)
  geoid       text,
  boundary_set text,                                 -- slug from the file ('v2-2024'); with geoid resolves unit_id
  unit_id     bigint references unit(id),
  point       geography(Point, 4326),                -- from lat/lon
  address_hash text,                                 -- no raw addresses stored (same rule as geocode_cache)
  valid_from  date,
  valid_to    date,
  source_id   bigint references source(id),
  check (geoid is not null or point is not null)
);
create index entity_location_entity on entity_location (entity_id);
create index entity_location_geoid on entity_location (geoid_layer, geoid);
create index entity_location_point on entity_location using gist (point);

-- Dedupe / merge across data-v3/inst (registry), data-v3/institutions (bots) and user submissions.
-- A merged-away id never disappears: it becomes an alias row pointing at the survivor (like person_alias).
create table entity_merge (
  from_id          text primary key,                 -- the id that was merged away (still resolvable)
  into_id          text not null references entity(entity_id),
  match_confidence numeric(4,3) not null check (match_confidence between 0 and 1),
  match_rule       text not null,                    -- 'same_geoid','same_lei','same_cik','name+state+trgm>=0.9','manual'
                                                   -- e.g. from_id 'cik:1750' into_id 'lei:MP76T5YQX3YK5VVAQ802'
  decided_by       text not null,                    -- 'auto' (>= 0.95) or a moderator id
  decided_at       timestamptz not null default now()
);

-- Shared names: both filters resolve aliases through one table (PA = Pennsylvania, USA = US).
-- entities.csv 'alias' (;-list) loads here.
create table alias (
  alias       text not null,                         -- lower(unaccent(...))
  entity_id   text references entity(entity_id) on delete cascade,
  unit_id     bigint references unit(id) on delete cascade,
  kind        text not null default 'abbr' check (kind in ('abbr','alt','historic','postal','external_id','merged_id')),
  scheme      text,                                  -- for external ids: 'lei','cik','ein','wikidata','cog_pid6','v2_key'
  match_confidence numeric(4,3) check (match_confidence is null or match_confidence between 0 and 1),
                                                   -- null = asserted by the source; < 1 = fuzzy match by the dedupe step
  source_id   bigint references source(id),
  check ((entity_id is null) <> (unit_id is null))
);
create index alias_alias on alias (alias text_pattern_ops);
create unique index alias_entity_uq on alias (alias, entity_id) where entity_id is not null;
create unique index alias_unit_uq   on alias (alias, unit_id)   where unit_id   is not null;

-- Resolved entity -> unit links (derived at load time: entity_geoid joined to unit.geoid within the
-- boundary sets of that vintage; chambers get one 'seat_district' row per seat unit).
--  'jurisdiction'  : the entity governs this area (state:42 -> PA polygon; county:01001 -> county)
--  'seat_district' : a chamber's seat area (chamber:pa-lower -> each sldl unit)
--  'same_as'       : entity and unit are the same thing (school:0100003 -> its polygon)
create table entity_unit (
  entity_id  text not null references entity(entity_id) on delete cascade,
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
  entity_id    text references entity(entity_id),    -- institution it belongs to (US, PA House ...)
  scope_entity_id text references entity(entity_id),      -- v2 rule: topic scoped to its entity (President -> United States)
  district_unit_type text                            -- unit_type of the seat areas, null for at-large/statewide
);

-- One race / question at one time point.
create table contest (
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

-- v2-parity display slots (Q-E13). v3 keeps every answer; this maps one answer to v2's 'd' and 'r'
-- columns for the D / R / total view. 'd' = the Democratic nominee, unless an independent beat the
-- Democrat statewide or there was no Democrat, then that independent (King ME 2024, Sanders VT, Osborn
-- NE 2024, McMullin UT 2022, Chesbro AK 2022 first round, Chambers LA 2022, Christiansen ND 2022).
-- 'r' = the Republican (AK 2022: Murkowski, first round). Colour still follows answer.party_id.
create table contest_display_slot (
  contest_id  bigint not null references contest(id) on delete cascade,
  slot        char(1) not null check (slot in ('d','r')),
  answer_id   bigint not null references answer(id) on delete cascade,
  rule        text not null default 'dem_nominee',   -- 'dem_nominee' | 'independent_beat_dem' | 'no_dem' | 'rep_nominee'
  note        text,
  primary key (contest_id, slot)
);

-- ---------------------------------------------------------------------------
-- 5b. People and officeholders (Q-I1; data-v3/inst/ on data/inst-officeholders)
-- ---------------------------------------------------------------------------
-- One canonical person_id 'scheme:id' per person, chosen in priority order (Q-I1/Q-I2, data/inst-officeholders 9d25f25):
--   bioguide:<ID> (permanent) > ocd-person:<uuid> (OpenStates, prefix normalized to 'ocd-person:'; can change on a
--   duplicate merge) > <st>-leg:<id> (session-scoped). No state legislator is bioguide-canonical; no cross-level name matching.
create table person (
  person_id     text primary key,                    -- 'bioguide:B001323', 'ocd-person:a84a3fe8-...', 'vt-leg:vt-41827'
  scheme        text not null,                        -- 'bioguide' | 'ocd-person' | '<st>-leg' (e.g. 'vt-leg')
  check (scheme in ('bioguide','ocd-person') or scheme ~ '^[a-z]{2}-leg$'),
  bioguide      text unique,
  ocd_person    text unique,
  official_ids  jsonb not null default '{}',          -- other official ids (state roster ids, FEC ...)
  sources       text,                                 -- persons.csv 'sources'
  name          text not null,
  candidate_id  bigint references candidate(id),      -- same human as an election candidate, when linked
  meta          jsonb not null default '{}'
);
create index person_name_trgm on person using gin (lower(name) gin_trgm_ops);

-- Former canonical ids (OpenStates merges, session-scoped ids that were later resolved) -> current person.
create table person_alias (
  alias_id      text primary key,                    -- e.g. an old ocd-person:<uuid>, 'mn-leg:mn-house-15367'
  person_id     text not null references person(person_id) on update cascade on delete cascade,
  kind          text not null default 'former_canonical' check (kind in ('former_canonical','session_scoped','official')),
  source_commit text                                  -- OpenStates commit where the alias was recorded
);
create index person_alias_person on person_alias (person_id);

-- Who held a seat (unit) over a date range. Vacancy = person_id null + status 'vacant'.
create table officeholder (
  id            bigint generated always as identity primary key,
  unit_id       bigint not null references unit(id),  -- seat polygon (cd116/cd119, sldl2024 ... via boundary_set)
  entity_id     text references entity(entity_id),    -- chamber entity ('us-house', 'chamber:al-lower', 'chamber:ne-upper')
  unit_layer    text,                                 -- as in the file: 'cd','sldu','sldl' (resolved to unit_id, DATA_LOADING §13)
  unit_geoid    text,
  unit_vintage  smallint,
  unit_plan     text,                                 -- 'cd116','cd119','sldl2024','sldu2024'
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
  source_id     bigint references source(id),
  source_commit text,                                 -- upstream commit (congress-legislators, OpenStates)
  check (status <> 'vacant' or person_id is null),
  unique nulls not distinct (unit_id, seat, person_id, valid_from),
  check (valid_to is null or valid_from is null or valid_to >= valid_from)
);
create index officeholder_unit_dates on officeholder (unit_id, valid_from, valid_to);
create index officeholder_person on officeholder (person_id);

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
  method        text,                                -- column 14 in the 2022/2024 Senate files (DECISIONS.md D6)
  boundary_set  text,                                -- Q-E12: boundary_set.slug ('v2-2024'); if absent, derived from the layer
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
-- 7b. Institution list ingest, refresh history and retractions (scraped lists, DATA_LOADING §15)
-- ---------------------------------------------------------------------------
create unlogged table stg_entity_row (
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
create table entity_history (
  id          bigint generated always as identity primary key,
  entity_id   text not null,
  op          text not null check (op in ('insert','update','merge','retract','restore')),
  before      jsonb,
  after       jsonb,
  batch_id    bigint references load_batch(id),
  submission_id bigint,
  at          timestamptz not null default now()
);
create index entity_history_entity on entity_history (entity_id, at);

-- Explicit retract list (DECISIONS.md D7): a row missing from a newer scrape is NOT deleted; it is closed
-- (valid_to set) only when listed here.
create table retraction (
  id          bigint generated always as identity primary key,
  target      text not null check (target in ('entity','entity_relation','entity_location','result')),
  target_key  text not null,
  reason      text not null,
  effective   date not null,
  source_id   bigint references source(id),
  batch_id    bigint references load_batch(id)
);

-- User add / upload with moderation (phase 3+, needs auth: DECISIONS.md D21).
create table app_user (
  id          bigint generated always as identity primary key,
  auth_subject text not null unique,                 -- id from the auth provider
  display_name text,
  role        text not null default 'contributor' check (role in ('contributor','moderator','admin')),
  created_at  timestamptz not null default now()
);
create table submission (
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
create index submission_queue on submission (status, created_at) where status = 'pending';
create index submission_submitter on submission (submitter_id, created_at);
create table moderation_log (
  id            bigint generated always as identity primary key,
  submission_id bigint references submission(id),
  actor_id      bigint not null references app_user(id),
  action        text not null check (action in ('approve','reject','edit','merge','ban','unban','note')),
  detail        jsonb,
  at            timestamptz not null default now()
);
create table rate_limit_bucket (
  subject     text not null,                         -- 'user:<id>' or 'ip:<hash>'
  action      text not null,                         -- 'submit','upload'
  window_start timestamptz not null,
  count       integer not null default 0,
  primary key (subject, action, window_start)
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
