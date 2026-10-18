# US House officeholders (v3; institutions lane)

This is built by `tools/inst_officeholders_house.py`, following `OFFICEHOLDERS_PLAN.md` (branch `data/inst-audit`). It is v3 only: nothing in v2 loads it.

| file | rows | content | join |
|---|---|---|---|
| `officeholders_house_current.csv` | 441 | House Clerk `MemberData.xml` (publish-date Oct 1, 2026; retrieved Oct 18, 2026): 439 serving, 2 **vacant** (FL-20, TX-23) | 436 joined to `data-v3/geo/ushouse.csv` (cd119); 5 `no_v3_unit` (PR, GU, VI, MP, AS (Clerk code `AQ`)) |
| `officeholders_house_2024.csv` | 441 | 119th Congress as elected in Nov 2024: congress-legislators terms starting 2025-01-03. 440 elected; **FL-01 vacant** (no member sworn when the Congress convened). 12 rows note that the Clerk now shows a different member or a vacancy (special elections, deaths, resignations) | 436 joined (cd119), 5 `no_v3_unit` |
| `officeholders_house_2020.csv` | 441 | 117th Congress as elected in Nov 2020, on the 116th-Congress lines (TIGER 2020 Gazetteer 116 CDs): 439 elected; **LA-05 and NY-22 vacant** at convening (no term starting 2021-01-03) | **pending**: `unit_geoid` left empty, `join_status=pending_geo_2020`, until geo's 2020-vintage GEOID tables land. The TIGER 2020 GEOID is given in `note` |

Joins are by code only, never by name. `statedistrict` maps to state + 2-digit district and then to the `ushouse.csv` geoid. At-large seats are `00`; DC is `1198`.

Sources:
- House Clerk `MemberData.xml`: public domain. sha256 `01833c6c646873b2…`.
- unitedstates/congress-legislators commit `d5af3d2` (2026-09-24), CC0 1.0. sha256 per file is in every row.

Names and parties are written exactly as each source gives them: the Clerk uses `R`/`D`/`I`, congress-legislators uses `Republican`/`Democrat`. Summary: `officeholders_house_summary.json`.
