# Schema proposal: data-v3/institutions/governments

Status: **proposal** for the orchestrator and the Institution filter bot (Oct 18, 2026). The CSVs in this folder
already use it. It follows the institutions spec on `data/inst-audit` (`data-v3/inst/ENTITIES_SCHEMA.md`) where the
two overlap, and the Geography bot's GEOID conventions (TIGER 2024, strings with leading zeros).

## Entity files (same columns in every file)
`states.csv`, `local/<USPS>.csv`, `federal_agencies.csv`, `tribes.csv`. UTF-8, header row, comma separated,
RFC 4180 quoting, `\n` line ends. Empty string = unknown / not applicable. Column names are stable; new columns
are only ever appended (`nces_leaid`, `tiger_status` added Oct 18, 2026).

| column | example | meaning |
|---|---|---|
| `entity_id` | `cog:100001`, `state:01`, `fr:12`, `bia:navajo-nation` | `scheme:id`, deterministic from the source ID, stable across refreshes (see below) |
| `name` | `COUNTY OF AUTAUGA` | name exactly as the source prints it (CoG names are upper case) |
| `type` | `county` | fixed list, see Types |
| `subtype` | `unified`, `water supply utility`, `alaska_native` | type-specific detail, see Types |
| `gov_status` | `independent` / `dependent` / `federally_recognized` | CoG independent vs dependent flag; `federally_recognized` for BIA rows |
| `parent_id` | `state:01`, `fr:538` | containment only where the source gives it (never inferred) |
| `state_fips`, `state` | `01`, `AL` | |
| `county_geoid` | `01001` | CoG `COUNTY_AREA_NAME` county (the county area the unit mainly serves or is headquartered in). Not a parent. |
| `geoid` | `0100124` | primary TIGER GEOID (string). County 5, place 7, cousub 10, school 7 (= NCES LEAID), state 2, AIANNH as TIGER prints it (`0010R`) |
| `geoid_layer` | `counties` / `place` / `cousub` / `unsd` / `elsd` / `scsd` / `states` / `aiannh` | which TIGER layer `geoid` belongs to (matches `data-v3/geo/` layer names where they exist) |
| `geoid_vintage` | `2024` | TIGER vintage of `geoid` (2022 or 2020 only for units missing from TIGER 2024) |
| `geoid_match` | `fips`, `f33_ncesid_2024`, `ansi_via_2022`, `fallback_name_2024` | how `geoid` was found, or why it is blank (full list in README); names starting `fallback_` are name matches |
| `cog_id` | `100001` | 2022 CoG `CENSUS_ID_PID6` (Institution filter bot join key) |
| `cog_gidid` | `01100100100000` | legacy CoG 14-digit `CENSUS_ID_GIDID` (Census is phasing it out) |
| `fips_place` | `07000` | CoG `FIPS_PLACE` as given (general-purpose governments only) |
| `alias` | `AO;administrative-office-...` | `;`-separated other names from the source (FR short name + slug; BIA former / aka names; state USPS) |
| `gnis_id` | `02403054` | ANSI/GNIS feature code of the matched TIGER feature (TIGER `ANSICODE` / `AIANNHNS` / `STATENS`) |
| `ocd_id`, `wikidata_qid` | | optional, empty in this first pull |
| `is_active` | `Y` / `N` | CoG `IS_ACTIVE` (`N` = dormant but still a government) |
| `note` | | free text (why a value is blank, cross-reference text, etc.) |
| `source` | `U.S. Census Bureau, 2022 Census of Governments ...` | human-readable citation |
| `source_url` | | URL of the exact file/document read |
| `source_date` | `2023-08-24` | publication date (server Last-Modified for Census files, FR publication date). The FR agencies API has no date, so its retrieval date is used. |
| `retrieved_at` | `2026-10-18T13:16:51Z` | UTC time the cached copy was downloaded |
| `license` | `public domain (U.S. Government work, 17 U.S.C. 105)` | |
| `nces_leaid` | `0100270` | school districts: NCES LEAID from the F-33 file (filled even when TIGER 2024 has no polygon for it) |
| `tiger_status` | `current_2024` / `absent_2024` | whether `geoid` exists in TIGER 2024; `absent_2024` = an older-vintage GEOID was carried (dissolved / merged / re-coded unit) |

### entity_id schemes
| scheme | id | stability |
|---|---|---|
| `state:` | 2-digit state FIPS | permanent |
| `cog:` | CoG `CENSUS_ID_PID6` | Census internal unit ID, kept across CoG cycles |
| `fr:` | Federal Register API agency `id` | permanent in the API |
| `bia:` | slug of the current listed name | the BIA list has no numeric ID; a rename creates a new slug (the old name stays in `alias` for several years, so a refresh can link them). Open question below. |

## Types
| type | definition | source | maps from Grok Bot's draft names |
|---|---|---|---|
| `state` | one of the 50 state governments | Census state codes (CoG counts 50) | `state` |
| `county` | CoG general-purpose type 1: county government (parish in LA, borough in AK) | CoG | `county` |
| `municipality` | CoG type 2: city, village, borough, town (where incorporated as a municipality), consolidated governments CoG classes as municipal | CoG | `municipal` |
| `township` | CoG type 3: town / township governments (New England, NY, NJ, PA, Midwest) | CoG | `township` |
| `school_district` | independent school district (CoG School District tab) or dependent school system (CoG DEP School Dist tab, `gov_status=dependent`). `subtype` = `unified` / `elementary` / `secondary` / `post_secondary` / `special_vocational` / `non_operating` from CoG `SCHOOL_LEVEL_DESCRIPTION` | CoG | `school` |
| `special_district` | CoG special-district government; `subtype` = CoG function name (e.g. `water supply utility`) | CoG | `special` |
| `federal_agency` | agency or sub-agency in the Federal Register agency list; `subtype` = `agency` / `sub_agency` | FR API | (new) |
| `tribe` | entity on the BIA list of federally recognized tribes; `subtype` = `contiguous_48` / `alaska_native` / `cross_reference` | BIA FR notice | `tribal` |
| `sovereign`, `foreign` | reserved for later non-US rows (countries, foreign governments); not used yet | | `sovereign`, `foreign` |

## Crosswalk: governments_geoid_xwalk.csv
Shape of `data-v3/inst/entity_geoid_xwalk.csv`. One row per (entity, GEOID); the entity's primary GEOID is included.

| column | example | meaning |
|---|---|---|
| `entity_id` | `cog:124214` | |
| `unit_layer` | `place` | TIGER layer |
| `geoid` | `1150000` | |
| `vintage` | `2024` | |
| `relation` | `primary` / `coextensive_cousub` / `independent_city_county_equivalent` / `consolidated_city_county` / `consolidated_city` (TIGER CONCITY, layer `concity`) / `balance_place` / `county_part` / `prior_vintage_code` / `predecessor_code` / `trust_land` (`;shared_area` appended when several tribes share the area) | |
| `match` | same codes as `geoid_match` | |
| `source`, `source_date` | `cog2022;gaz2024`, `2023-08-24` | short source codes, expanded in README |

## county_government_check.csv
Every TIGER 2024 county (and each CoG county FIPS not in TIGER) with whether CoG 2022 lists a county government
there. This is input for `data-v3/inst/county_government.csv` (`has_own_government`). CoG is authoritative over TIGER
on whether a county government exists.
Columns: `county_geoid, tiger_name, state, cog_county_government (yes/no), cog_id, cog_name, note, source, source_date`.
