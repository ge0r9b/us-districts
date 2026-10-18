# File family: officeholders + persons (data-v3/inst, institutions lane)

Files: `officeholders_house_current.csv`, `officeholders_house_2024.csv`, `officeholders_house_2020.csv`,
`officeholders_stateleg_current.csv`, `officeholders_stateleg_2024.csv`, `persons.csv`, `person_id_matches.csv`,
`stateleg_official_diffs.csv` (+ `*_summary.json`). Method notes: OFFICEHOLDERS_HOUSE.md, OFFICEHOLDERS_STATELEG.md.

Format (v3 Full Stack): UTF-8, one header row, columns read by name (stable). **Provenance is normalized (step 5):** every
row has `source_id` (a `;`-list when the row rests on several sources) pointing at `sources.csv` (README_SOURCES.md), which
holds the source name, full URL(s), licence, `retrieved_at`, the pinned upstream `commit` (OpenStates people,
unitedstates/congress-legislators) and the raw-download `sha256`. A row keeps its own `source_url` / `sha256` only when they
are row-specific (an OpenStates person file at the pinned commit); otherwise they are empty on the row and live once in
`sources.csv`. The repeated columns `source`, `license`, `retrieved_at`, `source_commit` are gone from the rows. Only open public sources are used (official legislature / House Clerk / Census sites, OpenStates CC0,
congress-legislators CC0); no paywalled or press sources.

Pipeline (idempotent): `inst_officeholders_house.py` → `inst_officeholders_stateleg.py` → `inst_stateleg_official.py` →
`inst_persons.py` → `inst_v3format.py` (step 4: chamber entity ids, unit_layer/unit_plan, full URLs, commits) →
**`inst_oh_sources.py`** (step 5: `sources.csv` + `source_id`; `--stability-test` rebuilds twice and compares).

## Key of an officeholder row

**chamber entity + unit + seat** (+ date range): `entity_id` (chamber entity of `data-v3/inst/entities.csv`) +
`unit_layer` + `unit_geoid` + `unit_vintage` + `seat`, with `term_start`/`term_end`. District seats are units, not entities.

## officeholders_house_*.csv / officeholders_stateleg_*.csv

| column | meaning |
|---|---|
| `unit_layer` | `cd`, `sldu`, `sldl` (TIGER set token) |
| `unit_geoid` | TIGER GEOID of the district unit; empty for units without TIGER geography (NH floterials, ME tribal seats, House delegates of territories) |
| `unit_vintage` | TIGER vintage year of the unit (`2024`; `2020` = cd116) |
| `unit_plan` | the former token: `cd119`, `cd116`, `sldu2024`, `sldl2024` |
| `join_status` | `joined`, `joined_unpaired_2020`, `no_v3_unit`, `no_v3_unit_floterial`, `no_v3_unit_tribal` |
| `entity_id` | chamber entity: `us-house`, `chamber:<ab>-upper`, `chamber:<ab>-lower` (Nebraska: `chamber:ne-upper`) |
| `entity_id_legacy` | former chamber slug (`al-house`, `ne-senate`, `ne-legislature`) |
| `seat` | seat label the source gives within a multi-member unit (Idaho House `A`/`B`); empty where the source gives none (WA, AZ, NJ, ND, SD, VT, MD, WV, NH list members without seat numbers) |
| `statedistrict` (House) / `state`, `chamber`, `district` (stateleg) | the source's own district label |
| `person_id` | canonical `scheme:id` (bioguide > ocd-person > `<st>-leg`); empty for vacancies |
| `name`, `party`, `caucus` | as published by the row source |
| `status` | `serving`, `elected`, `serving_at_2025-04-01`, `vacant` |
| `term_start`, `term_end`, `elected_date` | dates where the source gives them (`date_flags` marks missing ones) |
| `note` | free text: method notes, gaps |
| `source_id` | row source(s) in `sources.csv` (`openstates-people-772bae81`, `roster-tx-f415000c`, `house-clerk-memberdata-f5a438ef` ...) |
| `source_url` | row-specific URL only: the OpenStates person file at the pinned commit; empty when the row's URL is the source's own |
| `upstream_url` | OpenStates' upstream link for that person (a legislature member page), row-specific |
| `source_record_id` | id of the person/row inside the source (ocd-person id, bioguide id, roster id); was named `source_id` before step 5 |
| `sha256` | row-specific only: the OpenStates person file; the roster / Clerk / congress-legislators download hashes are in `sources.csv` |
| `official_check` | stateleg cross-check against the official roster (vocabulary below) |
| `date_flags` | `;`-list (vocabulary below) |

## persons.csv

`person_id`, `bioguide`, `ocd_person`, `official_ids`, `name`, `sources` (officeholder files that carry the person), `aliases`
(former / alternate canonical ids), `source_id` (`;`-list: every source behind the person's officeholder rows, canonical id and aliases).
Licence: CC0 1.0 (OpenStates, congress-legislators) and public domain (House Clerk), per contributing row.

## person_id_matches.csv

Each match of a bare official id to an OpenStates person: `file`, `state`, `chamber`, `district`, `official_id`, `official_name`,
`ocd_person`, `openstates_name`, `openstates_file`, `rule`, `source_url` (the OpenStates person file at the pinned commit when
there is one; empty otherwise), `source_id` (OpenStates people at the pinned commit). Licence CC0 1.0.

## stateleg_official_diffs.csv

Differences between the official roster and OpenStates: `state`, `chamber`, `unit_geoid`, `district`, `kind`, `official`,
`openstates`, `source_id` (`;`-list: the official roster + OpenStates people at the pinned commit).

## Sources and licences

| source | URL | licence |
|---|---|---|
| U.S. House Clerk MemberData.xml | https://clerk.house.gov/xml/lists/MemberData.xml | public domain |
| unitedstates/congress-legislators | https://github.com/unitedstates/congress-legislators | CC0 1.0 |
| OpenStates people | https://github.com/openstates/people | CC0 1.0 |
| 41 states' official legislature rosters / APIs | `roster-<st>-*` rows of `sources.csv` (and `inst-raw/rosters/SOURCES.txt`) | public record |
| Census TIGER/Line, Gazetteer (unit GEOIDs) | https://www2.census.gov/geo/tiger/ | public domain |

## Flags vocabulary (every value used)

**`date_flags`** (`;`-list on officeholder rows)
| value | meaning |
|---|---|
| `term_start_missing` | the source gives no start date for this person's current term in this seat; `term_start` is empty, never guessed |
| `term_end_open` | the term is still running (or the source has no end date); `term_end` is empty = open-ended |
| (empty) | both dates present, or a vacancy row, or a historical vintage file whose dates are complete |

**`join_status`**
| value | meaning |
|---|---|
| `joined` | the row's unit was found in the v3 geography (`unit_geoid` set) |
| `joined_unpaired_2020` | House 2020: the cd116 unit exists in `ushouse_2020.csv` but no v2 row carries it (district lost in reapportionment, or DC) |
| `no_v3_unit` | no TIGER unit exists for this seat (House delegates of PR, GU, VI, MP, AS) |
| `no_v3_unit_floterial` | New Hampshire floterial House seat: overlays other districts, has no TIGER SLDL polygon |
| `no_v3_unit_tribal` | Maine tribal representative: non-voting seat with no district |

**`status`**
| value | meaning |
|---|---|
| `serving` | in office on the retrieval date (Oct 18, 2026) per the row source |
| `elected` | House vintages: the member whose term started when that Congress convened |
| `serving_at_2025-04-01` | stateleg 2024 vintage: in office on 2025-04-01 (after the Nov 2024 elections) |
| `vacant` | nobody holds the unit per the row source; `person_id` is empty |

**`official_check`** (stateleg)
| value | meaning |
|---|---|
| `official` | current file: row taken from the state's official roster (`roster-<st>-*` source) |
| `openstates_fallback` | official roster not used for this state/chamber (blocked, browser-built, or not fetched); OpenStates CC0 row |
| `confirmed_current_roster` | 2024 file: the person is also on today's official roster for that unit |
| `confirmed_session_roster` | 2024 file: the person is on the official roster of the session that covers 2025-04-01 |
| `confirmed_session_roster_name_only` | 2024 file: matched on name in the session roster, but the roster no longer lists the unit (TX departed members) |
| `not_in_official_roster` | 2024 file: OpenStates lists the person, the official roster does not (kept; logged in the diffs) |
| (empty) | vacancy rows |

**`seat`**: the source's own seat label within a multi-member unit (`A`, `B` for the Idaho House); empty where the source gives none.

**`stateleg_official_diffs.csv` `kind`**
| value | meaning |
|---|---|
| `openstates_member_not_in_official_roster` | OpenStates has a current member in the unit; the official roster does not list them |
| `official_member_not_in_openstates_unit` | the official roster lists a member OpenStates does not have in that unit (the official row is used) |
| `official_member_in_unit_openstates_leaves_empty` | the official roster fills a unit OpenStates has as empty |
| `party_differs` | same person, the two sources give different parties (the official value is used where it lists party) |
| `2024_openstates_member_not_in_session_roster` | 2024 vintage member not on that session's official roster |
| `session_roster_member_not_asserted_unit_empty_in_openstates` | undated session roster lists someone where OpenStates has nobody current; not asserted as serving (may have left) |

**`person_id_matches.csv` `rule`**: `same state+chamber+district label, same last name and first initial` (matched to an
ocd-person id) or `no unique OpenStates person (N candidates); kept <st>-leg:<id>`.
