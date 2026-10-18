# Proposed schema: data-v3/inst/entities.csv (institution registry)

Approved by the orchestrator (QUESTIONS.md Q-G6). **Not built yet.** This is the proposed schema only. It lives under `data-v3/inst/` (institutions lane), not under `data-v3/geo/`.

One row per government or institution (not per place):

| column | example | meaning |
|---|---|---|
| `entity_id` | `county:01001`, `muni:place:0107000`, `town:cousub:0900104720`, `school:0100003`, `chamber:al-upper`, `us-house`, `state:01` | stable ID = kind prefix + TIGER GEOID; chambers and national bodies use fixed slugs |
| `kind` | `state`, `county`, `municipality`, `township`, `school_unified`, `school_elementary`, `school_secondary`, `chamber`, `district_seat`, `dc_council` | Q-G4: three school types, no single "school" type |
| `state_fips`, `state` | `01`, `Alabama` | |
| `name` | `Autauga County` | TIGER 2024 NAMELSAD |
| `alias` | `Autauga` | `;`-separated search aliases (v2 names, old pre-9ff4c00 school names, abbreviations) |
| `label` | `sovereign` / `incorporated` / `unincorporated` | the app's existing type labels (from PACK/XREF, read-only) |
| `gov_status` | `government` / `area_only` / `dependent` | from the 2022 Census of Governments: e.g. CT/RI counties = `area_only`; dependent school systems = `dependent` |
| `unit_layer`, `geoid`, `vintage` | `counties`, `01001`, `2024` | join to `data-v3/geo/<layer>.csv`; one row per vintage when the boundary changed |
| `geoid_alt` | `cousub:1900190000` | second GEOID when one government is both a place and a county subdivision. Geo answered Q3: such a government is **one entity carrying both GEOIDs**, and the relationship goes in the crosswalk below |
| `parent_entity_id` | `state:01` | containment for the institution search tree |
| `v2_layer`, `v2_row` | `schools`, `1` | back-link to the v2 row (from `data-v3/geo`), empty if v2 doesn't show it |
| `source`, `license` | `TIGER 2024; CoG 2022` | |

Build inputs (all read-only): `data-v3/geo/*.csv`; TIGER 2024 Gazetteer (counties, cousub, place, sld, CD, school sets); CoG 2022 Government Units Listing (government status); `PACK`/`XREF` in `v2/index.html` for labels and aliases. Expected size: about 65k rows (3,144 counties + about 22.5k cousubs + 19,465 places + 13,305 schools + 7,276 district rows (436 + 1,950 + 4,890) + chambers). That is v3 only, with no v2 load.

## Geo's answers that shape this schema (Oct 18, 2026)

- **Q3, one government with two Census GEOIDs** (place = county subdivision, consolidated city-county, independent city): this is one row in `entities.csv`. `geoid` is the primary (place) GEOID and `geoid_alt` the second. A crosswalk, `data-v3/inst/entity_geoid_xwalk.csv`, records the relationship type:

  | column | example | meaning |
  |---|---|---|
  | `entity_id` | `muni:place:1938595` | |
  | `geoid_layer`, `geoid` | `cousub`, `<10-digit state+county+cousub GEOID>` | every GEOID that names this entity, the primary one included |
  | `relation` | `coextensive` / `consolidated_city_county` / `independent_city_county_equivalent` / `primary` | how this GEOID relates to the entity |
  | `vintage` | `2024` | |
  | `source` | `TIGER 2024 place-cousub relationship file` | |

- **Q1, has its own government** is an institutions-lane attribute, not geography. It goes in `data-v3/inst/county_government.csv`, keyed by county GEOID:

  | column | example | meaning |
  |---|---|---|
  | `county_geoid` | `09001` | TIGER county GEOID (2024 vintage; a 2020-vintage row is added where the county set differs, e.g. CT planning regions) |
  | `has_own_government` | `yes` / `no` / `unknown` | `no` = an area with no county government (CT, RI, parts of MA, unorganized AK borough areas); `unknown` until a source is cited |
  | `government_note` | `county government abolished 1960; functions held by state/towns` | short free text |
  | `source` | `Census of Governments 2022, Government Units Listing` | required for every value other than `unknown` |

  `entities.csv` takes `gov_status` from this file for `kind=county`. Filling it from CoG 2022 is optional this round (geo's ruling), so the file starts as the 3,144 GEOIDs set to `unknown`. Nothing is guessed.
- **Q2, Q4, Q5** (v1 town alignment, keying to v1 towns): pending in geo's `data-v3/geo/ALIGNMENT.md` and `v1_towns.csv`. `alias` and `v2_row` will follow those once they land.
- **Q6:** geo is building the 2020-vintage GEOID tables. `vintage=2020` rows will join to them.
