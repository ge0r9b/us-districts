# File family: officeholders + persons (data-v3/inst, institutions lane)

Files: `officeholders_house_current.csv`, `officeholders_house_2024.csv`, `officeholders_house_2020.csv`,
`officeholders_stateleg_current.csv`, `officeholders_stateleg_2024.csv`, `persons.csv`, `person_id_matches.csv`,
`stateleg_official_diffs.csv` (+ `*_summary.json`). Method notes: OFFICEHOLDERS_HOUSE.md, OFFICEHOLDERS_STATELEG.md.

Format (v3 Full Stack): UTF-8, one header row, columns read by name (stable). Every row has `source_url` (full URLs,
` ; `-separated when a row used several), `retrieved_at` (download date) and `source_commit` (the pinned upstream git
commit: OpenStates people or unitedstates/congress-legislators; empty for official rosters and the House Clerk XML, which
have no commit). Only open public sources are used (official legislature / House Clerk / Census sites, OpenStates CC0,
congress-legislators CC0); no paywalled or press sources.

Pipeline (idempotent): `inst_officeholders_house.py` → `inst_officeholders_stateleg.py` → `inst_stateleg_official.py` →
`inst_persons.py` → **`inst_v3format.py`** (step 4: chamber entity ids, unit_layer/unit_plan, full URLs, commits, provenance
of the persons / matches / diffs files).

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
| `source`, `source_url`, `source_commit`, `upstream_url` | row source (name), its URL(s), pinned commit, and OpenStates' upstream link for that person |
| `source_id` | id of the person/row in the source |
| `retrieved_at` | download date |
| `sha256` | of the raw download |
| `license` | `public domain (US government work)`, `CC0 1.0`, `official state legislature website (public record)` |
| `official_check` | stateleg: `official`, `openstates_fallback`, cross-check result |
| `date_flags` | `term_start_missing`, `term_end_open` |

## persons.csv

`person_id`, `bioguide`, `ocd_person`, `official_ids`, `name`, `sources` (officeholder files that carry the person), `aliases`
(former / alternate canonical ids), `source_url` (all row URLs for the person), `retrieved_at`, `source_commit`.
Licence: CC0 1.0 (OpenStates, congress-legislators) and public domain (House Clerk), per contributing row.

## person_id_matches.csv

Each match of a bare official id to an OpenStates person: `file`, `state`, `chamber`, `district`, `official_id`, `official_name`,
`ocd_person`, `openstates_name`, `openstates_file`, `rule`, `source_url` (the OpenStates person file at the pinned commit),
`retrieved_at`, `source_commit`. Licence CC0 1.0.

## stateleg_official_diffs.csv

Differences between the official roster and OpenStates: `state`, `chamber`, `unit_geoid`, `district`, `kind`, `official`,
`openstates`, `source_url` (official roster + OpenStates tree), `retrieved_at`, `source_commit` (OpenStates).

## Sources and licences

| source | URL | licence |
|---|---|---|
| U.S. House Clerk MemberData.xml | https://clerk.house.gov/xml/lists/MemberData.xml | public domain |
| unitedstates/congress-legislators | https://github.com/unitedstates/congress-legislators | CC0 1.0 |
| OpenStates people | https://github.com/openstates/people | CC0 1.0 |
| 41 states' official legislature rosters / APIs | listed per row in `source_url` and in `inst-raw/rosters/SOURCES.txt` | public record |
| Census TIGER/Line, Gazetteer (unit GEOIDs) | https://www2.census.gov/geo/tiger/ | public domain |
