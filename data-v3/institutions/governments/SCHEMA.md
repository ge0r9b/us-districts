# Schema proposal: data-v3/institutions/governments

Status: **proposal** for the orchestrator and the Institution filter bot (Oct 18, 2026). The CSVs in this folder
already use it. It follows the institutions spec on `data/inst-audit` (`data-v3/inst/ENTITIES_SCHEMA.md`) where the
two overlap, and the Geography bot's GEOID conventions (TIGER 2024, strings with leading zeros).

## Entity files (same columns in every file)
`states.csv`, `local/<USPS>.csv`, `federal_agencies.csv`, `tribes.csv`. UTF-8, header row, comma separated,
RFC 4180 quoting, `\n` line ends. Empty string = unknown / not applicable. Column names are stable; new columns
are only ever appended (`nces_leaid`, `tiger_status`, then `flags`, `valid_from`, `valid_to` added Oct 18, 2026).

| column | example | meaning |
|---|---|---|
| `entity_id` | `cog:100001`, `state:01`, `fr:12`, `bia:navajo-nation` | `scheme:id`, deterministic from the source ID, stable across refreshes (see below) |
| `name` | `COUNTY OF AUTAUGA` | name exactly as the source prints it (CoG names are upper case) |
| `type` | `county` | fixed list, see Types |
| `subtype` | `unified`, `water supply utility`, `alaska_native` | type-specific detail, see Types |
| `gov_status` | `independent` / `dependent` / `federally_recognized` | CoG independent vs dependent flag; `federally_recognized` for BIA rows |
| `parent_id` | `state:01`, `fr:538`, `nation:us` | containment only where the source gives it (never inferred). Local units → their state (DC units: empty). States and top-level federal agencies → `nation:us` (defined in `data-v3/inst/entities.csv`, branch `data/inst-entities`; no nation row is created here). Tribes: empty. Dependent school systems keep the state and carry the flag `owner_unknown` (CoG does not name the owning government). |
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
| `ocd_id` | | optional, empty |
| `wikidata_qid` | `Q356979` | only from exact identifier links, never from names: states P5087 (FIPS 5-2 numeric) = state FIPS; counties P882 (FIPS 6-4) = county GEOID; municipalities P774 (FIPS 55-3, digits) = place GEOID, else P590 (GNIS ID) = TIGER ANSI code (if both exist and disagree: none); townships P590 only (MCD and place FIPS codes collide). Set only when exactly one item links and that item links to no other entity; `flags` says `qid_by_p5087` / `qid_by_p882` / `qid_by_p774` / `qid_by_p590`. Tribes: exact BIA-name = Wikidata label/P1448 among instances of Q7840353 (`qid_by_p1448` / `qid_by_label`; Wikidata has no BIA-ID property). Federal agencies, special and school districts: none (no identifier property).; federal agencies: P856 (official website) = Federal Register `agency_url`, host + path after normalisation, item an organisation (P31/P279* Q43229) |
| `is_active` | `Y` / `N` / `false` | CoG `IS_ACTIVE` (`N` = dormant but still a government); `false` = the government has ceased to exist (dissolved, merged, deorganized, consolidated) on `valid_to`, per a cited record in `changes_since_cog2022.csv`. Rows are never deleted. |
| `note` | | free text (why a value is blank, cross-reference text, etc.) |
| `source` | `cog2022;f33_2024;gaz2024` | `;`-separated stable source codes, defined in `sources.csv`: the record's source first, then the source(s) of its GEOID / QID |
| `source_url` | | only when row-specific (FR agency page, change records); otherwise empty and the URL is in `sources.csv` |
| `source_date` | `2023-08-24` | publication date (server Last-Modified for Census files, FR publication date). The FR agencies API has no date, so its retrieval date is used. |
| `retrieved_at` | `2026-10-18T13:16:51Z` | UTC time the cached copy was downloaded |
| `license` | `public domain (U.S. Government work, 17 U.S.C. 105)` | |
| `nces_leaid` | `0100270` | school districts: NCES LEAID from the F-33 file (filled even when TIGER 2024 has no polygon for it) |
| `flags` | `owner_unknown` | `;`-separated machine flags: `owner_unknown` (dependent school system, owning government not given by CoG), `qid_by_p1448` / `qid_by_label` (how a tribe QID was matched), `ceased` (see `valid_to`), `not_in_cog2022` (unit created after the CoG 2022 snapshot, see `valid_from`) |
| `valid_from`, `valid_to` | `2023-04-01` | ISO dates (`YYYY-MM-DD`, or `YYYY-MM` when the source fixes only the month) from a cited change record (`changes_since_cog2022.csv`); empty = in force at the CoG 2022 snapshot / still in force. Some CoG 2022 units had already ceased before the snapshot (CoG was stale), so `valid_to` can be earlier than 2022. |
| `tiger_status` | `current_2024` / `absent_2024` | whether `geoid` exists in TIGER 2024; `absent_2024` = an older-vintage GEOID was carried (dissolved / merged / re-coded unit) |

### Frozen IDs: id_registry.csv
`entity_id, source_key, first_seen`. Every build looks each record's source key up in the registry and reuses the
registered `entity_id`; a new ID is minted only for a key never seen before, and registry rows are never deleted.
Source keys: `fips_state:SS`, `cog_pid6:<PID6>`, `fr_agency:<id>`, `bia_name:<normalized current name>`, and for
units added from state registries `<registry code>:<registry id or normalized name>`. A renamed tribe is looked up by
the former name the BIA list prints in parentheses, keeps its ID, and gains a registry row for the new name; the
former name stays in `alias`.

### sources.csv
`source_id, source, source_url, license, retrieved_at, commit`. One row per stable source code used anywhere in this
folder. `retrieved_at` = latest retrieval of the cached file(s); `commit` = upstream version (only for git-hosted
sources; empty for files served over HTTP).

### entity_id schemes
| scheme | id | stability |
|---|---|---|
| `state:` | 2-digit state FIPS | permanent |
| `cog:` | CoG `CENSUS_ID_PID6` | Census internal unit ID, kept across CoG cycles |
| `fr:` | Federal Register API agency `id` | permanent in the API |
| `bia:` | slug of the listed name at first registration | frozen in `id_registry.csv`; renames keep the ID (former name in `alias`) |
| `gcn:` | Census code of a unit created after CoG 2022: place `SSPPPPP`, or cousub GEOID `SSCCCMMMMM` (registry key `census_code:place:` / `census_code:cousub:`) | frozen in the registry |
| `nces_leaid:` | NCES LEAID of a school district created after CoG 2022 | permanent |
| `tceq_wdd:` | TCEQ Water Districts Database district ID (Texas special district created after CoG 2022) | frozen in the registry |
| `wi_mds_incorporation:` | Wisconsin DOA Municipal Data System incorporation record ID (unit not yet in any Census file) | frozen in the registry |

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

## images.csv
Seal and flag image records, long format, one row per (entity, image_kind). URLs and metadata only; no image files.

| column | meaning |
|---|---|
| `entity_id` | entity row (`nation:us` = Q30, defined on `data/inst-entities`; `territory:60/66/69/72/78` = US territories, kind `territory`, parent `nation:us`, rows kept outside this folder per docs/v3/SCHEMA.md 62cb622 on v3/plan; ID conventions for future foreign work: `nation:<iso2>`, `territory:<iso2>`, `province:ca-<code>`, `territory:ca-<code>`) |
| `image_kind` | `seal` (Wikidata P158 or the enwiki fallback), `flag` (P41; nation, states, DC, territories only) or `logo` (federal agencies only: the Federal Register agency logo, last resort) |
| `commons_file`, `commons_url` | Commons file name and description page (empty for files hosted only on English Wikipedia) |
| `license` | SPDX-style id from Commons `LicenseShortName` (`LicenseRef-PublicDomain`, `CC0-1.0`, `CC-BY-SA-4.0`, ...), or `fair-use` |
| `attribution` | Commons/Wikipedia `Artist` (else `Credit`), HTML stripped |
| `wikidata_qid` | the item the image came from |
| `retrieved_at` | metadata retrieval time |
| `usage_basis` | fair-use rows only: `identification icon, small size` |
| `source_url` | fallback rows only: the English Wikipedia file page (fair use) or article (free file shown there) |

Selection: P158/P41 of the entity's QID; several files → most open license first (PD/CC0, CC BY, CC BY-SA, other).
Fallback for seals (nation, states, DC, territories, counties, municipalities, townships, tribes without P158): the seal file on the item's own
English Wikipedia article (its enwiki sitelink), only if exactly one file named "...seal..." is on the page, that
file is on no other fetched article (navbox images such as state seals are excluded), is no other item's P158, and
is not named only for a state (`Seal of the State of Ohio.svg`, `Seal utah.png`).
School-district seals/logos are skipped by rule.

## foreign/nations.csv, foreign/dependencies.csv, foreign/subdivisions.csv
Columns: `entity_id, name, official_name, type, subtype, gov_status, parent_id, iso_alpha2, iso_alpha3, iso_numeric,
iso_3166_2, un_status, un_admission_date, wikidata_qid, capital_qid, capital, head_of_government_office_qid,
head_of_government_office, external_ids, alias, is_active, note, flags, source, source_url, retrieved_at, license`.

| column | values |
|---|---|
| `entity_id` | `nation:<iso2>` (sovereign), `territory:<iso2>` (foreign dependency), `province:ca-<code>` / `territory:ca-<code>` (Canada), `subdivision:<iso 3166-2 lowercased>` (**proposal for the Institution filter bot**: other countries' first-level subdivisions, e.g. `subdivision:mx-jal`; not yet in v3 SCHEMA 62cb622), `territory:74` (U.S. Minor Outlying Islands, FIPS like the other U.S. territories) |
| `type` | `sovereign` (nations, incl. the two flagged non-UN rows) or `foreign` (dependencies and subdivisions) |
| `subtype` | nations: `state` or `non_un_state`; dependencies: ISO 3166-2 type of the place in its sovereign's list, else `dependency`; subdivisions: ISO 3166-2 type lowercased (`province`, `state`, `region`, `canton`, ...) |
| `gov_status` | `independent`, `disputed_or_unrecognized` (Taiwan, Western Sahara), `dependent`, `subnational` |
| `parent_id` | nations: empty; dependency → sovereign `nation:`; subdivision → its country's `nation:` / `territory:` row |
| `un_status` | `member`, `observer` (Holy See, State of Palestine), `none` |
| `un_admission_date` | ISO date from the un.org Member States page |
| `wikidata_qid` | P297 (nations, dependencies) or P300 (subdivisions) exact code; one live item per code and one code per item |
| `capital*`, `head_of_government_office*` | Wikidata P36 and P1313 of that item (several joined by `;`), English labels |
| `external_ids` | `statcan_sgc:<code>` for Canada |
| `flags` | `qid_by_p297`, `qid_by_p297_and_p463`, `qid_by_p300`, `no_qid:<why>`, `review_status` |

`foreign/iso_domestic_crosswalk.csv`: `iso_code, iso_name, entity_id, relation (domestic_row | same_wikidata_item |
duplicate_of_iso_3166_1), source, source_url`.

## images_gaps.csv
`entity_id, image_kind, wikidata_qid, reason`: in-scope entities (nation, states, DC, territories, counties,
municipalities, townships, tribes, federal agencies) with no image: `no_qid` (no exact identifier link; federal
agencies add why: `no_agency_url`, `no_item`, `multiple_items`, `url_shared`, `agency_url_rejected`, and
`no Federal Register logo`), `no_P158_on_wikidata; enwiki article fallback: no single seal file | not attempted
for this type`, `commons_file_missing`.

## changes_since_cog2022.csv
One row per (government, change) after the 2022 Census of Governments snapshot. Built by `scripts/build_changes.py`.

| column | meaning |
|---|---|
| `entity_id` | the CoG unit, or the new unit's ID (new rows are added to `local/<USPS>.csv` with `valid_from`) |
| `change_type` | `dissolution` (disincorporated, merged into another unit, deorganized, township organization discontinued), `incorporation` (new municipality), `new_township` (new organized township), `consolidation_abolished` / `consolidation_new_entity` (school district consolidations), `reclassification` (legal kind changed, e.g. town to city; name and ID unchanged), `rename`, `creation` (new special district, TCEQ WDD) |
| `effective_date` | ISO date (or `YYYY-MM`) from the source |
| `name`, `state` | CoG name (for a rename: the new name) and USPS code |
| `source_url` | the record's URL (several separated by ` ; ` when a state source and the Census record both cite it) |
| `retrieved_at` | retrieval time of the source |
| `source_id` | codes in `sources.csv` (`census_gcn`, or a state source such as `sc_legislature`, `wi_mds`) |
| `successor_id` | the government that took over, where the source names one |
| `cog_id` | CoG PID6 of the affected unit (empty for new units) |
| `detail` | the source's own description; GCN rows cite file year and line number |

`changes_curated.csv` is the committed, hand-entered input for changes cited to state sources (legislature acts,
state agency registries, official election results); every row has its URL and retrieval date.

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
