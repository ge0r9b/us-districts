# US House officeholders (v3; institutions lane)

This is built by `tools/inst_officeholders_house.py`, following `OFFICEHOLDERS_PLAN.md` (branch `data/inst-audit`). It is v3 only: nothing in v2 loads it.

| file | rows | content | join |
|---|---|---|---|
| `officeholders_house_current.csv` | 441 | House Clerk `MemberData.xml` (publish-date Oct 1, 2026; retrieved Oct 18, 2026): 439 serving, 2 **vacant** (FL-20, TX-23) | 436 joined to `data-v3/geo/ushouse.csv` (cd119); 5 `no_v3_unit` (PR, GU, VI, MP, AS (Clerk code `AQ`)) |
| `officeholders_house_2024.csv` | 441 | 119th Congress as elected in Nov 2024: congress-legislators terms starting 2025-01-03. 440 elected; **FL-01 vacant** (no member sworn when the Congress convened). 12 rows note that the Clerk now shows a different member or a vacancy (special elections, deaths, resignations) | 436 joined (cd119), 5 `no_v3_unit` |
| `officeholders_house_2020.csv` | 441 | 117th Congress as elected in Nov 2020, on the 116th-Congress lines (TIGER 2020 Gazetteer 116 CDs): 439 elected; **LA-05 and NY-22 vacant** at convening (no term starting 2021-01-03) | `unit_geoid` = the cd116 GEOID, joined to `data-v3/geo/ushouse_2020.csv` (geo `data/geo` e8599a6): **428 `joined`** (the 2020 district is paired with at least one v2 row; `note` lists the v2 rows, match type and overlap both ways), **8 `joined_unpaired_2020`** (CA-53, DC, IL-18, MI-14, NY-27, OH-16, PA-18, WV-03: 2020 districts lost in reapportionment or, for DC, served from `dc.js`; no v2 row carries them), 5 `no_v3_unit` (territories) |

Joins are by code only, never by name. `statedistrict` maps to state + 2-digit district and then to the `ushouse.csv` geoid. At-large seats are `00`; DC is `1198`.

Sources:
- House Clerk `MemberData.xml`: public domain. sha256 `01833c6c646873b2…`.
- unitedstates/congress-legislators commit `d5af3d2` (2026-09-24), CC0 1.0. sha256 per file is in every row.

Names and parties are written exactly as each source gives them: the Clerk uses `R`/`D`/`I`, congress-legislators uses `Republican`/`Democrat`. Summary: `officeholders_house_summary.json`.

**Connecticut (2020 vintage).** TIGER 2020 and the 116th-Congress files use CT's 8 old counties (09001–09015). data-v3 and v2 use the 9 planning regions (09110–09190) for both years. So any county-level 2020 join for CT has to go town → planning region, using the TIGER 2022+ town GEOIDs 091x0xxxxx (`data-v3/geo/ALIGNMENT.md` §2). The House join is by district code, so it isn't affected. Each CT row in `officeholders_house_2020.csv` carries this note.

## Person IDs and dates (v3 spec, 2026-10-18)

`tools/inst_persons.py` runs after `inst_officeholders_house.py` and edits the three House files in place.
- `person_id` was already canonical (`bioguide:<ID>`). Vacant seats keep an empty `person_id` and status `vacant`: 2 seats for 2020, 1 for 2024 and 2 for current.
- `persons.csv` links each bioguide ID to its OpenStates `data/us` ocd-person ID (in `ocd_person`) where OpenStates' record lists that bioguide. No name matching is used.
- New `date_flags` column:
  - `term_start_missing`: 0 rows in all three files.
  - `term_end_open`: 439 rows in the current file. The Clerk's member XML gives no term end.
  - The 2020 and 2024 files have full start and end dates from congress-legislators.

## v3 format (step 4, `tools/inst_v3format.py`)

Rows are keyed **chamber entity + unit + seat**: `entity_id` is now the chamber entity of `entities.csv` (`us-house`,
`chamber:<ab>-upper|lower`; old slug in `entity_id_legacy`), the unit is `unit_layer` + `unit_geoid` + `unit_vintage`
(TIGER year; the old `cd119`/`sldl2024` token is in `unit_plan`), and `seat` carries the source's seat label (Idaho House A/B).
Every row has full `source_url`s, `retrieved_at` and `source_commit`. Columns: README_OFFICEHOLDERS.md.
