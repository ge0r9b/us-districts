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
  share_alike    boolean not null default false,
  non_commercial boolean not null default false      -- licence forbids commercial use (DGEQ open-data metadata)
);
-- Canadian licences (data/inst-canada b4dc491 sources_ca.csv, CANADA_SCHEMA_PROPOSALS.md item 9).
insert into license (code, name, url, commercial_ok, attribution_required, non_commercial) values
  ('OGL-CA',         'Open Government Licence - Canada', 'https://open.canada.ca/en/open-government-licence-canada', true, true, false),
  ('OGL-NB',         'Open Government Licence - New Brunswick', null, true, true, false),
  ('StatCan-OL',     'Statistics Canada Open Licence', 'https://www.statcan.gc.ca/en/terms-conditions/open-licence', true, true, false),
  ('EO-OUDPL',       'Elections Ontario Open Use Data Product Licence', null, true, true, false),
  ('DGEQ-OD',        'Licence d''utilisation des données ouvertes du DGEQ (Élections Québec)', null, false, true, true),
  ('EBC-OD',         'Elections BC Open Data Licence', null, true, true, false),
  ('PEI-OD',         'Government of Prince Edward Island open data', null, null, true, false),
  ('not-stated',     'No licence stated on the agency download page (AB, MB, SK, NL)', null, null, true, false),
  ('HoC-website',    'House of Commons website (no reuse grant; factual fields only)', 'https://www.ourcommons.ca', null, true, false),
  ('ca-public-record','Official legislature website (public record; factual fields only)', null, null, true, false),
  ('ca-federal-law', 'Reproduction of Federal Law Order (SI/97-5)', 'https://laws-lois.justice.gc.ca/eng/const/page-1.html', true, true, false);

-- One row per source (sources.csv; election rows mint one per distinct url + retrieved_at). Unique on source_id only.
create table source (
  source_id     text primary key,                    -- sources.csv source_id, stable '<slug>-<sha8(url|commit)>' ('census-cog2022-0fba3401')
  title         text,                                -- sources.csv 'source' (human-readable description)
  publisher     text,                                -- 'U.S. Census Bureau', 'OpenStates' (optional)
  url           text,                                -- first / primary URL; every URL (incl. this one) is in source_url
  retrieved_at  timestamptz,
  commit        text,                                -- upstream commit (congress-legislators, OpenStates) when given
  license       text,                                -- license as stated by the source, verbatim (generic provenance)
  license_id    bigint references license(id),
  non_commercial boolean not null default false,    -- no commercial use: never shown in paid features (Élections Québec data)
  attribution_required boolean not null default false,
  license_verified boolean not null default false,   -- true once the license/terms page has been read (date in license_checked_at)
  license_checked_at date,
  robots_ok     boolean,                             -- scraped lists: robots.txt and terms of service allow it (DATA_LOADING §15.3)
  attribution   text,                                -- exact credit line to display
  sha256        text,                                -- of the raw download, when the data bot records it
  notes         text
);
-- Sources with several URLs (sources.csv 'source_url' as a ' ; '-list, e.g. a legislature's House + Senate pages).
create table source_url (
  source_id   text not null references source(source_id) on delete cascade,
  ord         smallint not null,                     -- position in the ' ; '-list (1 = source.url)
  url         text not null,
  label       text,                                  -- optional ('house', 'senate', 'cousub', 'place')
  primary key (source_id, ord)
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
  ('legislative_lower','State house districts'), ('school_district','School districts'), ('ward','Wards'), ('custom','Custom'), ('seat','Seats without a district'),
  ('federal_district','Federal electoral districts (Canada)'), ('provincial_district','Provincial electoral districts (Canada)');
insert into unit_type_def (unit_type, category, label, tiger_set) values
  ('country','country','Country',null), ('state','state','State','state'), ('county','county','County','county'),
  ('county_subdivision','town','Town / township','cousub'), ('place','place','Place','place'),
  ('precinct','precinct','Precinct',null), ('ushouse','congressional','US House district','cd'),
  ('sldu','legislative_upper','State senate district','sldu'), ('sldl','legislative_lower','State house district','sldl'),
  ('school_unified','school_district','Unified school district','unsd'),
  ('school_elementary','school_district','Elementary school district','elsd'),
  ('school_secondary','school_district','Secondary school district','scsd'),
  ('ward','ward','Ward',null), ('custom','custom','Custom area',null),
  ('seat','seat','Seat without a district polygon',null),   -- NH floterials, ME tribal seats, House delegates of territories
  -- Canada (prefixed ca_; the inst-canada files say fed/poll/ped/ppoll/cd/csd and the loader maps them)
  ('ca_fed','federal_district','Federal electoral district (Canada)',null),            -- key FED_NUM ('35075')
  ('ca_poll','precinct','Federal polling division (Canada)',null),                     -- '<FED_NUM>:<PD_NUM>-<SFX>' ('10001:78-0')
  ('ca_ped','provincial_district','Provincial / territorial electoral district',null), -- agency code (ON ED_ID, QC CO_CEP, BC 'ABM')
  ('ca_ppoll','precinct','Provincial polling division / voting area / section de vote',null),  -- '<district key>:<poll code>'
  ('ca_cd','county','Census division (Canada)',null),                                  -- StatCan CDUID
  ('ca_csd','town','Census subdivision (Canada)',null);                                -- StatCan CSDUID

-- A coherent set of polygons of one unit type and vintage, e.g. 'tiger-2024-sldl',
-- 'v2-2024' (incl. the ONE precinct set: 2016/2020 votes are placed onto the 2024 precinct polygons,
-- DATA_LOADING.md §9.4; no 'precincts-2016'/'precincts-2020' sets). Custom (paid) sets later: owner_tenant_id <> 1,
-- visibility 'private' or 'shared', license 'proprietary'.
create table boundary_set (
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
create unique index boundary_set_slug_type on boundary_set (slug, unit_type);
-- Agreed registry (Election + Institutions, Oct 18, 2026). Units are loaded per (slug, unit_type).
insert into boundary_set (slug, unit_type, vintage_year, is_current)
select v.slug, t.unit_type, v.yr, v.cur
from (values ('v2-2024', 2024, true), ('tiger-2020-cd116', 2020, false), ('tiger-2020-sldu', 2020, false),
             ('tiger-2020-sldl', 2020, false), ('tiger-2020-county', 2020, false)) as v(slug, yr, cur)
join unit_type_def t on
     (v.slug = 'v2-2024'           and t.unit_type in ('state','county','county_subdivision','place','precinct','ushouse','sldu','sldl',
                                                       'school_unified','school_elementary','school_secondary','ward','seat'))
  or (v.slug = 'tiger-2020-cd116'  and t.unit_type in ('ushouse','seat'))
  or (v.slug = 'tiger-2020-sldu'   and t.unit_type = 'sldu')
  or (v.slug = 'tiger-2020-sldl'   and t.unit_type = 'sldl')
  or (v.slug = 'tiger-2020-county' and t.unit_type = 'county');   -- the 8 old CT counties (09001 ... 09015)
-- Canada (b4dc491): 24 sets, slug pattern '<agency>-<boundary year>-<set>'.
insert into boundary_set (slug, unit_type, country, province, vintage_year, is_current) values
  ('ec-2023-fed','ca_fed','ca',null,2023,true),   ('ec-2013-fed','ca_fed','ca',null,2013,false),
  ('ec-2025-pd','ca_poll','ca',null,2025,true),   ('ec-2021-pd','ca_poll','ca',null,2021,false), ('ec-2019-pd','ca_poll','ca',null,2019,false),
  ('eo-2022-ed','ca_ped','ca','ON',2022,true),
  ('eq-2026-ced','ca_ped','ca','QC',2026,true),   ('eq-2026-sv','ca_ppoll','ca','QC',2026,true),
  ('eq-2022-ced','ca_ped','ca','QC',2022,false),  ('eq-2022-sv','ca_ppoll','ca','QC',2022,false),   -- 2022 general election (3bbb54a)
  ('ebc-2023-ed','ca_ped','ca','BC',2023,true),   ('ebc-2024-va','ca_ppoll','ca','BC',2024,true),
  ('ea-2019-ed','ca_ped','ca','AB',2019,true),    ('ea-2026-va','ca_ppoll','ca','AB',2026,true),
  ('em-2018-ed','ca_ped','ca','MB',2018,true),    ('em-2023-va','ca_ppoll','ca','MB',2023,true),
  ('esk-2022-ed','ca_ped','ca','SK',2022,true),   ('esk-2024-va','ca_ppoll','ca','SK',2024,true),
  ('enb-2024-ed','ca_ped','ca','NB',2024,true),   ('enb-2024-pd','ca_ppoll','ca','NB',2024,true),
  ('epei-2017-ed','ca_ped','ca','PE',2017,true),  ('epei-2017-poll','ca_ppoll','ca','PE',2017,true),  -- vintage not stated by the source
  ('enl-2015-ed','ca_ped','ca','NL',2015,true),   ('enl-2019-poll','ca_ppoll','ca','NL',2019,false), -- maybe superseded
  ('statcan-2021-cd','ca_cd','ca',null,2021,true), ('statcan-2021-csd','ca_csd','ca',null,2021,true);
create index boundary_set_type_year on boundary_set (unit_type, vintage_year);
create unique index boundary_set_one_current
  on boundary_set (owner_tenant_id, unit_type, country, coalesce(province, '')) where is_current;   -- one current set per province

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
create index unit_parent on unit (parent_unit_id);
create unique index unit_legacy on unit (boundary_set_id, legacy_key) where legacy_key is not null;
create index unit_geoid on unit (geoid);
create index unit_state_type on unit (state_abbr, unit_type);
create index unit_name_trgm on unit using gin (lower(name) gin_trgm_ops);

-- 'seat' units (no polygon): optional link to the TIGER units they cover (an NH floterial -> its base sldl districts).
create table seat_member_unit (
  seat_unit_id   bigint not null references unit(id) on delete cascade,
  member_unit_id bigint not null references unit(id) on delete cascade,
  source_id      text references source(source_id),
  primary key (seat_unit_id, member_unit_id)       -- seat_member_units.csv (ffdf738): seat_unit_key + boundary_set -> seat_unit_id;
);                                                 -- member_unit_layer + member_unit_key + member_boundary_set -> member_unit_id
create index unit_centroid_gist on unit using gist (centroid);

-- ZCTA -> place / town / county shares (v2/data/zcta_xref, Census 2020 relationship files), for ZIP search and lists.
create table zcta_unit_share (
  zcta       char(5) not null,
  unit_id    bigint  not null references unit(id),
  share      numeric(3,2) not null check (share > 0 and share <= 1),  -- share of the ZCTA's land area
  source_id  text references source(source_id),
  primary key (zcta, unit_id)
);
create index zcta_unit_share_unit on zcta_unit_share (unit_id);

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
  source_id    text references source(source_id),
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
-- Bot entities use bare scheme:id (like person ids). Companies/brands/organizations: 'wikidata:Q<id>' is the ONLY
-- canonical company id in v3 (scraped brands with no QID get no entity and are excluded); moderated user adds get
-- 'usd:<uuid>' on approval and are re-keyed to 'wikidata:Q...' when a QID appears (usd: kept in entity_alias).
-- 'lei:' / 'cik:' are NOT ingested in v3: reserved entity_alias schemes for the v5/v6 bridge to the user's private
-- corporate database. Governments: 'cog:<id>', 'fr:<id>', 'bia:<slug>'.
-- unicameral Nebraska is 'chamber:ne-upper' (no -lower), DC is 'chamber:dc-council' (kind dc_council), the US House is 'us-house'.
-- Verified on data/inst-entities 8e1db01: 54,144 entities (municipality 19,525, township 18,076, school_unified 10,872,
-- county 3,080, school_elementary 1,952, school_secondary 481, chamber 100, state 51, territory 5, nation 1, dc_council 1).
-- The same entity_id carries across boundary vintages; a new id is minted only when the government
-- itself changes (merger, dissolution, incorporation, CT planning regions), linked by predecessor/successor.
-- District seats are UNITS, not entities (officeholder = chamber entity + unit + seat).
create table entity (
  entity_id     text primary key,
  kind          text not null check (kind in (
                  'nation','territory','province','state','county','municipality','township',  -- province: Canadian provinces (parent nation:ca)
                  'school_unified','school_elementary','school_secondary',   -- Q-G4; unit_category 'school_district'
                  'chamber','dc_council',
                  'indigenous_government',                                   -- First Nations (Canada: 'first_nation:ca-<band number>'); US tribes later
                  'government_other',                                        -- Governments bot (special districts, authorities, foreign govts)
                  'brand','organization','company','nonprofit','fund',       -- Companies bot (Wikidata): brands.csv kind brand|organization
                  'other')),
  state_fips    char(2),
  state         text,
  country       char(2),                             -- ISO 3166-1 alpha-2, lowercase ('ca'); null = US registry row
  province      text,                                -- ISO 3166-2 subdivision ('ON')
  external_id   text,                                -- agency id / extra ('seats=343(2023_rep_order)' in the CA files)
  labels        jsonb not null default '{}',         -- names by language ({"fr": "Assemblée législative de l'Alberta"})
  name          text not null,                       -- TIGER NAMELSAD
  label         text check (label in ('sovereign','incorporated','unincorporated')),
                                                   -- v2 wording rule: states sovereign; never 'incorporated state'
  gov_status    text check (gov_status in ('government','area_only','dependent')),  -- CoG 2022; Governments bot independent->government,
                                                   -- federally_recognized->government (+ meta.recognition='federal')
  parent_id     text references entity(entity_id),   -- containment tree (state:42 > chamber:pa-lower); corporate ownership is entity_relation
                                                   -- predecessor_id / successor_id (;-lists in entities.csv) load into entity_succession
  valid_from    date,
  valid_to      date,
  v2_layer      text[],                              -- ';'-list in the CSV: 'v2:counties', 'v2:parts'
  v2_key        text[],                              -- 'Alabama|Autauga County' (parts rows: state|county|name)
  v2_row        text[],                              -- 'v2:counties#342' (informational; shifts between builds)
  brand_name    text,                                -- public-facing brand / label (Wikidata label), shown in the institution filter
  legal_form_code text,                              -- optional ISO 20275 ELF code when Wikidata states one (P1454); no GLEIF ingest in v3
  legal_form    text,                                -- optional legal-form label
  feed          text,                                -- raw file value; mapped to origin on load (DATA_LOADING §15.1)
  level         text,                                -- extras: federal / state / county / local
  type          text,                                -- finer type (TIGER LSAD text, 'city'); brands: Wikidata P31 class label
  cog_pid6      text,                                -- CoG 2022 unit id
  flags         text[],                              -- review flags ('gov_status_unknown:...')
  origin        text not null default 'inst' check (origin in ('inst','governments_bot','companies_bot','user')),
  -- World geography: nations are 'nation:<iso2>' lowercase (the existing US row is 'nation:us', 348f410); foreign
  -- dependencies are kind 'territory' with the sovereign nation as parent; provinces have parent 'nation:ca'.
  -- Units exist for any country with a registered boundary set (Canada first); other non-US places stay entity-only
  -- (no entity_geoid / entity_unit rows; entity_location.unit_id and boundary_set null).
  check (kind <> 'nation' or entity_id ~ '^nation:[a-z]{2}$'),
  -- Canada: municipality:ca-<CSDUID>, county:ca-<CDUID> (county / regional governments), first_nation:ca-<band number>
  check (country is distinct from 'ca' or kind <> 'municipality' or entity_id ~ '^municipality:ca-[0-9]{7}$'),
  check (country is distinct from 'ca' or kind <> 'county' or entity_id ~ '^county:ca-[0-9]{4}$'),
  check (country is distinct from 'ca' or kind <> 'indigenous_government' or entity_id ~ '^first_nation:ca-[0-9]+$'),
  -- territory ids: 'territory:<2-digit US FIPS>' (parent nation:us), 'territory:<iso2>' (foreign dependency, parent = sovereign),
  -- 'territory:ca-(nt|nu|yt)' (Canada's territories, parent nation:ca). Provinces: 'province:ca-<code>' (parent nation:ca).
  check (kind <> 'territory' or (parent_id like 'nation:%'
         and (entity_id ~ '^territory:[0-9]{2}$' or entity_id ~ '^territory:[a-z]{2}$' or entity_id ~ '^territory:ca-(nt|nu|yt)$'))),
  check (kind <> 'territory' or entity_id !~ '^territory:ca-' or parent_id = 'nation:ca'),
  check (kind <> 'territory' or entity_id !~ '^territory:[0-9]{2}$' or parent_id = 'nation:us'),
  check (kind <> 'province' or (parent_id = 'nation:ca' and entity_id ~ '^province:ca-[a-z]{2}$')),
  check (kind not in ('brand','organization','company','nonprofit','fund') or entity_id ~ '^(wikidata:Q[0-9]+|usd:[0-9a-f-]{36})$'),
  source_record_id text,                              -- the entity's id inside its primary source (CoG pid6, Wikidata QID, ...)
                                                   -- sources: entity_source (sources.csv ';'-list)
  wikidata      text unique check (wikidata ~ '^wikidata:Q[0-9]+$'),   -- entities.csv 'wikidata' (bare 'Q228' in the file; prefixed on load)
  has_region    boolean not null default true,
                                                   -- seals / flags / logos: entity_image (replaces the old icon_flag column)
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
  source_id      text references source(source_id),
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
  boundary_set text not null,                       -- xwalk 'boundary_set': 'v2-2024' (58,655 rows), 'tiger-2020-county' (8, old CT counties)
  overlap     text check (overlap in ('equal','split','contained')),
  share_of_geoid_in_entity numeric(5,4) check (share_of_geoid_in_entity between 0 and 1),
  share_of_entity_in_geoid numeric(5,4) check (share_of_entity_in_geoid between 0 and 1),
  source_record_id text,
  primary key (entity_id, unit_layer, geoid, vintage)  -- sources: entity_geoid_source
);
create index entity_geoid_lookup on entity_geoid (unit_layer, geoid, vintage);

-- Brands/organizations: brand -> parent QID links over time (Wikidata P749 parent organization / P127 owned by).
-- No ownership percentages in v3 (corporate ownership detail stays in the user's private database, v5/v6 bridge).
create table entity_relation (
  parent_id     text not null references entity(entity_id),   -- 'wikidata:Q...'
  child_id      text not null references entity(entity_id),   -- the brand
  relation      text not null default 'parent_org' check (relation in ('parent_org','owned_by','brand_of','consolidated_with')),
                                                   -- brands.csv parent_brand_id = P749 = parent_org; consolidated_with links a consolidated
                                                   -- city-county's county entity (parent) and its place entity (child)
  valid_from    date,
  valid_to      date,
  source_id     text references source(source_id),   -- one source per link (Wikidata)
  source_record_id text,                              -- e.g. the Wikidata statement id of the P749 claim
  check (parent_id <> child_id),
  check (valid_to is null or valid_from is null or valid_to >= valid_from),
  unique nulls not distinct (parent_id, child_id, relation, valid_from)
);
create index entity_relation_child on entity_relation (child_id);

-- Locations / establishments: one row per site (store, branch, venue) or HQ. Point-in-polygon by GIST.
create table entity_location (
  location_id  bigint generated always as identity primary key,
  location_key text unique,                          -- '<brand file stem>:<store_id>' ('walgreens:15196', 'marriott:NYCMQ');
                                                   -- store_id is unique only within a brand file
  entity_id    text not null references entity(entity_id) on delete cascade,   -- brand_qid ('wikidata:Q1591889')
  sub_entity_id text references entity(entity_id),  -- sub_brand_qid (Duane Reade, CVS Pharmacy y más), when given
  role         text not null check (role in ('hq_in','establishment_at')),
  name         text,                                 -- site name ('Target Store T-1234')
  address      text,                                 -- public business address as published: address, city, state zip
  geom         geometry(Point, 4326),                -- from lat/lon
  geoid        text,                                 -- county FIPS (locations/*.csv county_geoid, Census 2024 point-in-polygon)
  boundary_set text,                                 -- 'v2-2024' when geoid is a v2 county; null for PR/VI (not in v2's county layer)
  unit_id      bigint references unit(id),           -- resolved by point-in-polygon at load; null + flag 'no_unit_resolved' when the point
                                                   -- falls in no unit (e.g. Wawa 9598/9599, in the Atlantic); the row still loads
  valid_from   date,
  valid_to     date,
  source_record_id text,                             -- store_id / MARSHA code inside the brand's source; sources: entity_location_source
  retrieved_at timestamptz,                          -- source_date
  flags        text[],                               -- the bot's review flags ('coordinates_from_atp', ...)
  meta         jsonb not null default '{}',          -- phone, sub_brand, status, store_type, country_code, source_url
  retracted    boolean not null default false,       -- set via the retract list; never deleted
  check (geom is not null or geoid is not null)
);
create index entity_location_entity on entity_location (entity_id) where not retracted;
create index entity_location_geoid on entity_location (geoid);
create index entity_location_geom on entity_location using gist (geom);   -- point-in-polygon / bbox queries

-- Seals, flags and logos: inst entity_images.csv (seals/flags) + Companies brands.csv logo_* (logos).
-- The image is a static asset (/img/<role>/<entity_id>.<ext>), not a DB blob. Only freely licensed files are served
-- publicly in v3; fair_use rows load with public = false until D22 is decided.
create table entity_image (
  id            bigint generated always as identity primary key,
  entity_id     text references entity(entity_id) on update cascade on delete cascade,
  feed_entity_id text,                               -- feed id when the image's entity is not in the registry ('bia:...'); see entity_feed_map
  role          text not null check (role in ('seal','flag','logo')),
  file          text,                                -- Commons / Wikipedia file name ('Walgreens 2020 primary logo.svg')
  file_url      text,                                -- Commons file URL (entity_images.csv commons_url)
  license       text not null,                       -- licence id or Commons wording, verbatim ('LicenseRef-PublicDomain', 'fair-use')
  fair_use      boolean not null default false,
  usage_basis   text,                                -- fair-use rationale ('identification icon, small size')
  is_trademark  boolean not null default false,      -- licence mentions 'trademarked': trademark notice, never altered
  public        boolean not null default true,       -- served publicly; forced false for fair_use rows (v3 rule)
  attribution   text,
  source_url    text,                                -- file description page / article the file came from
  wikidata      text,                                -- 'wikidata:Q...' the image statement belongs to
  served_path   text,                                -- '/img/logo/wikidata-Q1591889.svg' once the build step fetched and optimised it
  sha256        text,                                -- checksum of the served asset (cache-busting + change detection)
  flags         text[],                              -- brands.csv logo_flags, review flags
  retrieved_at  timestamptz,                         -- sources: entity_image_source (';'-list)
  check (entity_id is not null or feed_entity_id is not null),
  check (not fair_use or not public),
  unique nulls not distinct (entity_id, feed_entity_id, role)
);
create table entity_image_source (
  image_id   bigint not null references entity_image(id) on delete cascade,
  source_id  text not null references source(source_id),
  ord        smallint not null default 1,
  primary key (image_id, source_id)
);

-- Feed id -> registry entity (inst entity_feed_map.csv): which bot ids map to an entity, which stay feed-only.
create table entity_feed_map (
  feed           text not null,                      -- 'governments-bot' (raw feed value)
  feed_id        text not null,                      -- entity_feed_map.csv feed_entity_id ('cog:161834', 'bia:cherokee-nation')
  feed_type      text,                               -- 'special_district', 'municipality', 'tribe', ...
  entity_id      text references entity(entity_id) on update cascade,
  status         text not null check (status in ('mapped','feed_only','unmapped')),
  match          text,                               -- 'geoid+cog_pid6', 'nces_leaid+cog_pid6', 'state_fips', 'geoid', 'nces_leaid'
  note           text,                               -- file note ('feed_only:special_district', 'no_geoid_or_cog_link'); 'consolidated'
  source_id      text references source(source_id),
  primary key (feed, feed_id),
  check ((status = 'mapped') = (entity_id is not null))
);
create index entity_feed_map_entity on entity_feed_map (entity_id);

-- Dedupe / merge across data-v3/inst (registry), data-v3/institutions (bots) and user submissions.
-- A merged-away id never disappears: it becomes an entity_alias row pointing at the survivor (like person_alias).
create table entity_merge (
  from_id          text primary key,                 -- the id that was merged away (still resolvable)
  into_id          text not null references entity(entity_id),
  match_confidence numeric(4,3) not null check (match_confidence between 0 and 1),
  match_rule       text not null,                    -- 'same_geoid','same_qid','qid_redirect','usd_to_qid','name+state+trgm>=0.9','manual'
                                                   -- e.g. from_id 'usd:3f2c…' into_id 'wikidata:Q1046951'
  decided_by       text not null,                    -- 'auto' (>= 0.95) or a moderator id
  decided_at       timestamptz not null default now()
);

-- Shared names: both filters resolve aliases through one table (PA = Pennsylvania, USA = US).
-- entities.csv 'alias' (;-list) loads here; also external ids, former QIDs (Wikidata merges/redirects), usd: ids
-- re-keyed to a QID, and the reserved lei:/cik: schemes (no v3 loader; v5/v6 bridge only, never served publicly).
create table entity_alias (
  alias       text not null,                         -- lower(unaccent(...))
  entity_id   text references entity(entity_id) on delete cascade,
  unit_id     bigint references unit(id) on delete cascade,
  kind        text not null default 'abbr' check (kind in ('abbr','alt','historic','postal','external_id','merged_id','former_qid','reserved')),
  scheme      text,                                  -- external ids: 'wikidata','cog_pid6','v2_key','usd'; reserved (v5/v6): 'lei','cik'
  match_confidence numeric(4,3) check (match_confidence is null or match_confidence between 0 and 1),
                                                   -- null = asserted by the source; < 1 = fuzzy match by the dedupe step
  source_id   text references source(source_id),
  check ((entity_id is null) <> (unit_id is null)),
  check (scheme not in ('lei','cik') or kind = 'reserved')   -- reserved schemes: stored only for the future bridge
);
create index alias_alias on entity_alias (alias text_pattern_ops);
create unique index alias_entity_uq on entity_alias (alias, entity_id) where entity_id is not null;
create unique index alias_unit_uq   on entity_alias (alias, unit_id)   where unit_id   is not null;

-- Resolved entity -> unit links (derived at load time: entity_geoid joined to unit.geoid within the
-- boundary sets of that vintage; chambers get one 'seat_district' row per seat unit).
--  'jurisdiction'  : the entity governs this area (state:42 -> PA polygon; county:01001 -> county)
--  'seat_district' : a chamber's seat area (chamber:pa-lower -> each sldl unit)
--  'same_as'       : entity and unit are the same thing (school:0100003 -> its polygon)
create table entity_unit (
  id         bigint generated always as identity primary key,
  entity_id  text not null references entity(entity_id) on delete cascade,
  unit_id    bigint not null references unit(id) on delete cascade,
  role       text not null check (role in ('jurisdiction','seat_district','same_as','reserve_of')),  -- reserve_of: a First Nation's reserve /
                                                   -- settlement / land ca_csd units (many-to-many, one row per band x CSD x reserve)
  method     text check (method in ('overlay')),     -- how the link was derived; null = taken from the source as-is
  is_estimate boolean not null default false,        -- approximate (≈) link; every reserve_of row is
  share_of_geoid_in_entity numeric(5,4) check (share_of_geoid_in_entity between 0 and 1),   -- reserve_of: share of the CSD inside the reserve
  share_of_entity_in_geoid numeric(5,4) check (share_of_entity_in_geoid between 0 and 1),   -- reserve_of: share of the reserve inside the CSD
  source_record_id text,                             -- one id per row ('isc_reserve_no=06000')
  flags      text[],                                 -- 'shared_reserve', 'several_reserves_in_csd'
  unique nulls not distinct (entity_id, unit_id, role, source_record_id)
);
create table entity_unit_source (
  entity_unit_id bigint not null references entity_unit(id) on delete cascade,
  source_id      text not null references source(source_id),
  ord            smallint not null default 1,
  primary key (entity_unit_id, source_id)
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
  source_id      text not null references source(source_id),
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
  source_id    text references source(source_id),
  primary key (contest_id, unit_id)
);

-- History of overwritten values (audit; never lose what a source said).
create table result_history (
  contest_id bigint not null, unit_id bigint not null, answer_id bigint not null,
  votes numeric(14,4), weight numeric(9,8), source_id text, retrieved_at timestamptz,
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
create index officeholder_unit_dates on officeholder (unit_id, valid_from, valid_to);
create index officeholder_person on officeholder (person_id);

-- County government status (data-v3/inst/county_government.csv, f1d64f6): one row per county GEOID x vintage
-- (3,144 for 2024 + 8 for the 2020 CT counties).
create table county_government (
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
create index county_government_entity on county_government (entity_id);

-- Row <-> source link tables (files cite a ';'-list of sources.csv source_ids per row).
create table entity_source (
  entity_id  text not null references entity(entity_id) on delete cascade,
  source_id  text not null references source(source_id),
  ord        smallint not null default 1,            -- position in the row's ';'-list
  primary key (entity_id, source_id)
);
create table entity_geoid_source (
  entity_id text not null, unit_layer text not null, geoid text not null, vintage smallint not null,
  source_id text not null references source(source_id),
  ord       smallint not null default 1,
  primary key (entity_id, unit_layer, geoid, vintage, source_id),
  foreign key (entity_id, unit_layer, geoid, vintage) references entity_geoid on delete cascade
);
create table entity_location_source (
  location_id bigint not null references entity_location(location_id) on delete cascade,
  source_id   text not null references source(source_id),
  ord         smallint not null default 1,
  primary key (location_id, source_id)
);
create table officeholder_source (
  officeholder_id bigint not null references officeholder(id) on delete cascade,
  source_id       text not null references source(source_id),
  ord             smallint not null default 1,
  primary key (officeholder_id, source_id)
);
create table person_source (
  person_id  text not null references person(person_id) on update cascade on delete cascade,
  source_id  text not null references source(source_id),
  ord        smallint not null default 1,
  primary key (person_id, source_id)
);
create table county_government_source (
  county_geoid char(5) not null, vintage smallint not null,
  source_id    text not null references source(source_id),
  ord          smallint not null default 1,
  primary key (county_geoid, vintage, source_id),
  foreign key (county_geoid, vintage) references county_government on delete cascade
);
create index entity_source_source on entity_source (source_id);
create index officeholder_source_source on officeholder_source (source_id);

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
  source_id   text references source(source_id),
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
