-- Derived from docs/v3/SCHEMA.sql. Idempotent.
-- CREATE ... IF NOT EXISTS does not change an object that already exists.
-- A later schema change is a new numbered file, not an edit to this one.

set search_path = usd, public;

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
create table if not exists entity (
  entity_id     text primary key,
  kind          text not null check (kind in (
                  'nation','territory','province','state','county','municipality','township',  -- province: Canadian provinces (parent nation:ca)
                  'school_unified','school_elementary','school_secondary',   -- Q-G4; unit_category 'school_district'
                  'chamber','dc_council',
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

create index if not exists entity_parent on entity (parent_id);

create index if not exists entity_kind on entity (kind, state_fips);

create index if not exists entity_v2 on entity using gin (v2_key);

create index if not exists entity_name_trgm on entity using gin (lower(name) gin_trgm_ops);

-- Government changes (merger, dissolution, incorporation, CT planning regions): many-to-many.
create table if not exists entity_succession (
  predecessor_id text not null references entity(entity_id),
  successor_id   text not null references entity(entity_id),
  effective      date,
  source_id      text references source(source_id),
  primary key (predecessor_id, successor_id)
);

-- entity_geoid_xwalk.csv: one row per entity x unit_layer x vintage (the join to geography; governments).
create table if not exists entity_geoid (
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

create index if not exists entity_geoid_lookup on entity_geoid (unit_layer, geoid, vintage);

-- Brands/organizations: brand -> parent QID links over time (Wikidata P749 parent organization / P127 owned by).
-- No ownership percentages in v3 (corporate ownership detail stays in the user's private database, v5/v6 bridge).
create table if not exists entity_relation (
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

create index if not exists entity_relation_child on entity_relation (child_id);

-- Locations / establishments: one row per site (store, branch, venue) or HQ. Point-in-polygon by GIST.
create table if not exists entity_location (
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

create index if not exists entity_location_entity on entity_location (entity_id) where not retracted;

create index if not exists entity_location_geoid on entity_location (geoid);

create index if not exists entity_location_geom on entity_location using gist (geom);   -- point-in-polygon / bbox queries

-- Seals, flags and logos: inst entity_images.csv (seals/flags) + Companies brands.csv logo_* (logos).
-- The image is a static asset (/img/<role>/<entity_id>.<ext>), not a DB blob. Only freely licensed files are served
-- publicly in v3; fair_use rows load with public = false until D22 is decided.
create table if not exists entity_image (
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

create table if not exists entity_image_source (
  image_id   bigint not null references entity_image(id) on delete cascade,
  source_id  text not null references source(source_id),
  ord        smallint not null default 1,
  primary key (image_id, source_id)
);

-- Feed id -> registry entity (inst entity_feed_map.csv): which bot ids map to an entity, which stay feed-only.
create table if not exists entity_feed_map (
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

create index if not exists entity_feed_map_entity on entity_feed_map (entity_id);

-- Dedupe / merge across data-v3/inst (registry), data-v3/institutions (bots) and user submissions.
-- A merged-away id never disappears: it becomes an entity_alias row pointing at the survivor (like person_alias).
create table if not exists entity_merge (
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
create table if not exists entity_alias (
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

create index if not exists alias_alias on entity_alias (alias text_pattern_ops);

create unique index if not exists alias_entity_uq on entity_alias (alias, entity_id) where entity_id is not null;

create unique index if not exists alias_unit_uq   on entity_alias (alias, unit_id)   where unit_id   is not null;

-- Resolved entity -> unit links (derived at load time: entity_geoid joined to unit.geoid within the
-- boundary sets of that vintage; chambers get one 'seat_district' row per seat unit).
--  'jurisdiction'  : the entity governs this area (state:42 -> PA polygon; county:01001 -> county)
--  'seat_district' : a chamber's seat area (chamber:pa-lower -> each sldl unit)
--  'same_as'       : entity and unit are the same thing (school:0100003 -> its polygon)
create table if not exists entity_unit (
  entity_id  text not null references entity(entity_id) on delete cascade,
  unit_id    bigint not null references unit(id) on delete cascade,
  role       text not null check (role in ('jurisdiction','seat_district','same_as')),
  primary key (entity_id, unit_id, role)
);

create index if not exists entity_unit_unit on entity_unit (unit_id);
