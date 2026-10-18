# File family: institution registry (data-v3/inst, institutions lane)

Files: `entities.csv`, `entity_geoid_xwalk.csv`, `entity_v2_rows.csv`, `entity_gaps.csv`, `entities_summary.json`.
Builder: `tools/inst_entities.py` (read-only inputs; deterministic). Column list and SCHEMA.sql alignment: ENTITIES_SCHEMA.md.
Format: UTF-8, one header row, stable column names (v3 reads by header). Every entity and xwalk row has `source`,
`source_url`, `retrieved_at`. Open public sources only.

## What is an entity

One row per **institution** (government, governing body, later companies), no vintage. Kinds now: `nation`, `state`
(50 + DC), `territory` (5, only because they send House delegates), `chamber` (99 state chambers + `us-house`), `dc_council`,
`county`, `municipality` (place-based government), `township` (county-subdivision government), `school_unified`,
`school_elementary`, `school_secondary`. District seats are **units** (cd / sldu / sldl GEOIDs), not entities: an officeholder
row is keyed chamber `entity_id` + `unit_layer` + `unit_geoid` + `unit_vintage` + `seat`.

`entity_id` is minted once (kind prefix + the GEOID first seen) and then frozen and opaque; it does not change when a boundary
or GEOID changes. A new id is minted only when the government itself changes, linked with `predecessor_id` / `successor_id`
(today: CT's 8 old counties → 9 planning regions, linked through the shared town FIPS codes of TIGER 2020 and 2024).

## How the rows are built (all links by Census code, never by name)

- **Municipalities and towns.** Candidates: every incorporated place (TIGER CLASSFP C*), every county subdivision with a
  governmental FUNCSTAT (A/B/C/G) or a CoG 2022 code, plus every place or county subdivision a v1/v2 row carries.
  - A place and a county subdivision with the same state + 5-digit FIPS code are one Census-coded entity: one row, place
    GEOID primary, county subdivisions in the xwalk. Example: Chicago = place 1714000 + cousubs 1703114000 (Cook) and
    1704314000 (DuPage).
  - County-subdivision-only governments with one FIPS code across counties are one entity.
  - Geo's `town_pairs.csv` "same" pairs (mutual overlap ≥ 0.9) merge only when CoG 2022 lists just one of the two codes
    (23 pairs, e.g. Hartford city / Hartford town). When CoG lists both as governments (13 pairs, e.g. Berwyn city /
    Berwyn township) they stay two entities, flagged `coextensive_separate_government`.
- **Consolidated city-counties and independent cities** (county_government.csv: no county government, the CoG municipal
  unit's code is a TIGER place): the county GEOID joins the city entity. That covers 72 counties (VA independent cities,
  Baltimore, St. Louis, SF, Denver, Philadelphia, NYC's 5 boroughs, ...). DC is one entity, `state:11`, carrying place
  1150000, county 11001 and cousub 1100150000. In 6 cases the CoG code is not in TIGER 2024 (Athens-Clarke, Honolulu,
  Greeley, Louisville, Butte-Silver Bow, Nashville-Davidson). Those counties stay county entities with `gov_status` empty
  and a flag; the cases are listed in `entity_gaps.csv`.
- **gov_status.**
  - CoG 2022 code match → `government`.
  - TIGER FUNCSTAT G with no CoG unit → `dependent` (Iowa townships, NYC boroughs as cousubs).
  - FUNCSTAT F/I/N/S → `area_only`.
  - Counties: from county_government.csv.
  - Schools: empty. CoG school lists carry no NCES or TIGER code, so no code join is possible; these are flagged.
  - Chambers: not applicable.
- **parent_id.**
  - school, county and chamber → state;
  - municipality or town → county (when ≥ 98 % of it is in one county), else state;
  - state → nation:us; us-house → nation:us.

## entity_geoid_xwalk.csv

One row per entity × unit_layer × GEOID × vintage. `relation`: `primary`, `coextensive` (mutual ≥ 0.9), `also_cousub`
(part of a place split across county subdivisions), `consolidated_city_county`, `independent_city_county_equivalent`,
`consolidated_town_city`, `federal_district_city`. `overlap` gives the geometry (equal / split / contained) and the two
`share_*` columns the area shares on TIGER 2024 (geo lane GeoJSON, EPSG:6933).

## entity_v2_rows.csv / entity_gaps.csv

`entity_v2_rows.csv` maps every v2 row (counties, schools, senate, statehouse, ushouse incl. the 2020 pairings, states, parts,
places, IA towns) and every v1 town/place row to its entity (district rows → chamber entity + unit). `entity_gaps.csv` lists
orphans, unknowns, excluded "not defined" TIGER records and CoG 2022 units not linked by code.

## Taking external feeds (governments-bot, companies-bot, user uploads)

Feeds live in `data-v3/institutions/` (owned by those bots; this lane does not write there). A feed row maps onto
entities.csv like this:

| feed field | entities.csv |
|---|---|
| feed's stable id | `entity_id` = `<feed prefix>:<feed id>` (e.g. `co:<id>`, `gov:<id>`); never reused |
| entity type | `kind` (open vocabulary: company kinds such as `company`, `subsidiary`, `brand` are added as they arrive) |
| parent / owner | `parent_id` (generic: a corporate parent, or a government parent) |
| jurisdiction | `state_fips`, `state` (empty if national or foreign) |
| GEOID, if a government | an `entity_geoid_xwalk.csv` row (relation `primary`). If the GEOID already belongs to a `tiger/cog` entity, the feed row is an alias of that entity, not a new one |
| name, other names | `name`, `alias` |
| start / end, mergers | `valid_from`, `valid_to`, `predecessor_id`, `successor_id` |
| provenance | `feed` = `governments-bot` / `companies-bot` / `user-upload`; `source`, `source_url`, `retrieved_at`, `license` from the feed row |

## Sources and licences

| source | URL | licence |
|---|---|---|
| Census 2024 / 2020 TIGER Gazetteer (counties, cousubs, places, CD119/116, SLDU/SLDL, UNSD/ELSD/SCSD) | https://www2.census.gov/geo/docs/maps-data/data/gazetteer/ | public domain |
| Census TIGER/Line 2024 county subdivisions + places (FUNCSTAT, CLASSFP, geometry; via data-v3/geo GeoJSON) | https://www2.census.gov/geo/tiger/TIGER2024/ | public domain |
| Census 2022 Census of Governments, Government Units Listing | https://www2.census.gov/programs-surveys/gus/datasets/2022/govt_units_2022.ZIP | public domain |
| ANSI/FIPS state codes | https://www.census.gov/library/reference/code-lists/ansi.html | public domain |
| data-v3/geo tables (v2 row links), data-v3/inst county_government.csv and officeholder files | this repo | as listed per file |
