-- Derived from docs/v3/SCHEMA.sql. Idempotent.
-- CREATE ... IF NOT EXISTS does not change an object that already exists.
-- A later schema change is a new numbered file, not an edit to this one.

set search_path = usd, public;

-- ---------------------------------------------------------------------------
-- 2. Geography: boundary sets, units, geometry
-- ---------------------------------------------------------------------------

-- Unit types and their shared parent category (Q-G4, orchestrator, Oct 18, 2026): three school types matching
-- TIGER UNSD / ELSD / SCSD, all under the category 'school_district', so the UI can list them as one
-- "School districts" list while each unit keeps the board voters actually elect. Elementary and secondary
-- districts overlap (CA, IL, AZ, MT ...), so one point may resolve to several school units.
create table if not exists unit_category (
  category    text primary key,                    -- 'school_district', 'legislative', 'congressional', 'county', ...
  label       text not null                        -- UI list label: 'School districts'
);

create table if not exists unit_type_def (
  unit_type   text primary key,
  category    text not null references unit_category(category),
  label       text not null,                       -- 'Unified school district'
  tiger_set   text                                 -- 'unsd','elsd','scsd','cd','sldu','sldl','county','cousub','place','state'
);

-- A coherent set of polygons of one unit type and vintage, e.g. 'tiger-2024-sldl',
-- 'v2-2024' (incl. the ONE precinct set: 2016/2020 votes are placed onto the 2024 precinct polygons,
-- DATA_LOADING.md §9.4; no 'precincts-2016'/'precincts-2020' sets). Custom (paid) sets later: owner_tenant_id <> 1,
-- visibility 'private' or 'shared', license 'proprietary'.
create table if not exists boundary_set (
  id               bigint generated always as identity primary key,
  slug             text not null,                    -- = the bot rows' boundary_set token (Q-E12): lowercase-hyphen; one row per
                                                   -- (slug, unit_type), since 'v2-2024' spans every v2 layer,
                                                   -- e.g. 'v2-2024' (v2's 2024 polygons/GEOIDs; current + 2024), 'tiger-2020-cd116' (2020 House),
                                                   -- 'tiger-2020-sldu' / 'tiger-2020-sldl' (2020 state legislature, 2018 plans), 'tiger-2020-county'
                                                   -- (2020 counties incl. the 8 old CT counties). Geometry joins on (slug, unit_type), NOT on year.
  unit_type        text not null references unit_type_def(unit_type),
  country          char(2) not null default 'us',    -- ISO 3166-1 alpha-2, lowercase; units exist for any country with a registered set
  province         text,                             -- ISO 3166-2 subdivision ('ON', 'QC') for provincial sets; null for national ones
  vintage_year     int  not null,                    -- boundary year (2024 = current)
  valid_from       date,
  valid_to         date,                             -- null = still in force
  is_current       boolean not null default false,   -- v2 rule: results shown in TODAY's boundaries
  owner_tenant_id  bigint not null default 1 references tenant(id),
  visibility       text not null default 'public' check (visibility in ('public','shared','private')),
  license_id       bigint references license(id),
  source_id        text references source(source_id),
  price_tier       text,                             -- null for free/public; reserved for paid custom sets
  feature_count    int,
  tiles_url        text,                             -- versioned PMTiles archive on the CDN
  built_at         timestamptz,
  meta             jsonb not null default '{}'
);

create unique index if not exists boundary_set_slug_type on boundary_set (slug, unit_type);

create index if not exists boundary_set_type_year on boundary_set (unit_type, vintage_year);

create unique index if not exists boundary_set_one_current
  on boundary_set (owner_tenant_id, unit_type, country, coalesce(province, '')) where is_current;   -- one current set per province

-- Who else may read a 'shared' set.
create table if not exists boundary_set_grant (
  boundary_set_id bigint not null references boundary_set(id) on delete cascade,
  tenant_id       bigint not null references tenant(id) on delete cascade,
  primary key (boundary_set_id, tenant_id)
);

-- Which boundary set a bot row's (unit_type, year) resolves to. Lets 2020 results land
-- either on 2020 precincts or (re-tabulated) on 2024 districts without guessing.
create table if not exists boundary_set_default (
  unit_type        text not null,
  results_year     int  not null,
  boundary_set_id  bigint not null references boundary_set(id),
  primary key (unit_type, results_year)
);

-- A geographic unit: one polygon in one boundary set (precinct, county, district, state ...).
create table if not exists unit (
  id               bigint generated always as identity primary key,
  boundary_set_id  bigint not null references boundary_set(id),
  unit_type        text not null references unit_type_def(unit_type),  -- category via unit_type_def (school_* -> school_district)
  unit_key         text not null,                    -- canonical key = TIGER GEOID where one exists ('42001' county,
                                                   -- '4201' CD ...), else the bot's unit_id (precincts: 'PA|Erie County|420491492')
  legacy_key       text,                             -- v2 name key ('Pennsylvania|Erie County', 'Ohio|<school name> (<county>)'); unique per
                                                   -- boundary set in the national layers after the Geo renames - see DATA_LOADING.md §8
  name             text not null,
  labels           jsonb not null default '{}',      -- names by language ({"fr": "Chambre des communes"}); no name_fr column
  country          char(2) not null default 'us',    -- ISO 3166-1 alpha-2, lowercase
  province         text,                             -- ISO 3166-2 subdivision for non-US units ('ON'); US units use state_fips/state_abbr
  external_id      text,                             -- the agency's own id ('FED_NUM=10001', 'CSDUID=1001101')
  state_fips       char(2),
  state_abbr       char(2),
  geoid            text,                             -- Census GEOID where one exists
  parent_unit_id   bigint references unit(id),       -- containment: precinct -> county -> state; may cross sets (ec-2025-pd poll -> ec-2023-fed)
  parent_boundary_set text,                          -- slug of the parent's set when it differs (files: parent_boundary_set + parent_unit_key)
  area_m2          double precision,
  centroid         geometry(Point, 4326),
  label_point      geometry(Point, 4326),            -- v2/data/points: state-icon star, always inside the shape (null for zero-area slivers)
  bbox             box2d,
  meta             jsonb not null default '{}',
  unique (boundary_set_id, unit_key)
);

create index if not exists unit_parent on unit (parent_unit_id);

create unique index if not exists unit_legacy on unit (boundary_set_id, legacy_key) where legacy_key is not null;

create index if not exists unit_geoid on unit (geoid);

create index if not exists unit_state_type on unit (state_abbr, unit_type);

create index if not exists unit_name_trgm on unit using gin (lower(name) gin_trgm_ops);

-- 'seat' units (no polygon): optional link to the TIGER units they cover (an NH floterial -> its base sldl districts).
create table if not exists seat_member_unit (
  seat_unit_id   bigint not null references unit(id) on delete cascade,
  member_unit_id bigint not null references unit(id) on delete cascade,
  source_id      text references source(source_id),
  primary key (seat_unit_id, member_unit_id)       -- seat_member_units.csv (ffdf738): seat_unit_key + boundary_set -> seat_unit_id;
);                                                 -- member_unit_layer + member_unit_key + member_boundary_set -> member_unit_id

create index if not exists unit_centroid_gist on unit using gist (centroid);

-- ZCTA -> place / town / county shares (v2/data/zcta_xref, Census 2020 relationship files), for ZIP search and lists.
create table if not exists zcta_unit_share (
  zcta       char(5) not null,
  unit_id    bigint  not null references unit(id),
  share      numeric(3,2) not null check (share > 0 and share <= 1),  -- share of the ZCTA's land area
  source_id  text references source(source_id),
  primary key (zcta, unit_id)
);

create index if not exists zcta_unit_share_unit on zcta_unit_share (unit_id);

-- Geometry per level of detail. lod 0 = full detail used for point-in-polygon and
-- area weighting; lod 1..3 = simplified copies for low zooms / dynamic MVT fallback.
create table if not exists unit_geom (
  unit_id     bigint not null references unit(id) on delete cascade,
  lod         smallint not null check (lod between 0 and 3),
  tolerance_m real not null,                         -- 0, ~40, ~200, ~1000
  min_zoom    smallint not null,
  geom        geometry(MultiPolygon, 4326) not null,
  primary key (unit_id, lod)
);

create index if not exists unit_geom_gist_lod0 on unit_geom using gist (geom) where lod = 0;

create index if not exists unit_geom_gist_lod2 on unit_geom using gist (geom) where lod = 2;

-- Overlap weights between units of different sets (precinct -> district, 2020 precinct ->
-- 2024 precinct). Used to re-tabulate; weight = share of the source unit's votes assigned.
create table if not exists unit_crosswalk (
  from_unit_id bigint not null references unit(id) on delete cascade,
  to_unit_id   bigint not null references unit(id) on delete cascade,
  weight       numeric(9,8) not null check (weight > 0 and weight <= 1),
  method       text not null check (method in ('exact','area','population','votes_in_split','official')),
  source_id    text references source(source_id),
  primary key (from_unit_id, to_unit_id)
);

create index if not exists unit_crosswalk_to on unit_crosswalk (to_unit_id);
