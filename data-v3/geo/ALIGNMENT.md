# Alignment answers for the Institutions bot (geo lane)

Oct 18, 2026, branch `data/geo`. Items 2, 3 and 5 first; 1, 4 and 6 follow.

## 2) Connecticut: planning regions in both years

**No, both the 2024 and the 2020 rows are the 9 planning regions.** Their GEOIDs are 09110, 09120, 09130, 09140, 09150, 09160, 09170, 09180 and 09190.
- `v2/data/uscounties.js` has only the 9 regions.
- `data/election2024.js` and `data/election2020.js` key Connecticut only by planning region.
- The 2020 values were rebuilt per town from VEST 2020 by `tools/build_ct2020.py` and summed into the regions.
- `data-v3/geo/counties.csv` lists the 9 regions.
- The 8 old counties (09001–09015) appear in no v2 file or CSV.

Caveat for 2020-vintage joins: TIGER 2020 and the 116th Congress files use the old counties. A 2020 join for Connecticut therefore has to go town (county subdivision) → planning region, using the TIGER 2022+ town GEOIDs 091x0xxxxx.

## 3) A place that is also a county subdivision

**Our view: yes, one entity with two GEOIDs.**
- `entities.csv` keeps one row per real government, with `place_geoid` (7 digits) and `cousub_geoid` (10 digits) both filled.
- A crosswalk `entity_geoids.csv` has one line per (entity, GEOID) with a relationship type:
  - `coextensive`: the subdivision and the place cover the same ground. This is TIGER county-subdivision FUNCSTAT F, places-as-MCDs.
  - `place_in_cousub`: the place lies inside a county subdivision with its own government.
  - `place_split`: the place spans several county subdivisions or counties, with one row per part.
- Use mutual overlap ≥ 90 % for `coextensive`, the same threshold as `town_pairs.js` below.

This is common. Of the town rows v2 hides as same-name duplicates, 4,171 are this pair under one identical name. For example, Chicago city has place GEOID 1714000 and county-subdivision GEOIDs 1703114000 (Cook) and 1704314000 (DuPage).

## 5) Do the hidden same-name town rows have their own GEOID?

**Yes, all of them.** v2's `townsIn()` hid 6,008 town rows, measured before the suffix-aware fix, by `tools/town_gaps.py`.

| Kind | Rows | GEOIDs |
|---|---|---|
| Identical name, same entity (the place and its county subdivision) | 4,171 | Own GEOID: the place GEOID, and the hiding row is the county subdivision (or the reverse) |
| Different name, same base name (city vs township, borough vs town, ...) | 1,837 | Own GEOID, a different entity |

Largest states:
- Identical name: PA 998, MN 800, WI 518, NJ 313, ND 298, SD 271, MI 261, OH 260.
- Different name: IL 474, NY 209, IA 173, KS 171, WI 143, MI 137, OH 96, MN 92.

## Town pairs: `v2/data/town_pairs.js` (orchestrator option A)

The orchestrator chose a suffix-aware duplicate check: real TIGER names stay, and `townsIn()` hides only identical names and pairs marked "same".

- **Format:** `window.TOWN_PAIRS={"State|Name A|Name B":"same", ...}`. **The JS file is same-only** (36 keys): a missing key means "separate". The full table with both classes is `data-v3/geo/town_pairs.csv`.
  - The names are the exact row names the app sees: v1 `data/<State>.js` towns and `v2/data/parts/<State>.js` names.
  - **Name A < Name B in plain code-point order** (JS `a<b` on the raw strings, Python `sorted`). Only that one order is listed. To look up a pair: `k = a<b ? st+"|"+a+"|"+b : st+"|"+b+"|"+a`.
- **Which pairs:** every two rows of one county whose `normT()` names are equal but whose names differ. No key occurs in two counties, so there are no conflicts and the county isn't needed in the key.
- **Class:** both rows are resolved to TIGER 2024 by exact NAMELSAD in the county (county subdivision first, then place) and clipped to the county.
  - **"same"** when each covers ≥ 90 % of the other (mutual overlap).
  - **"separate"** otherwise.
- **Counts:** 2,470 pairs, 36 "same" (the keys in the JS file) and 2,434 "separate" (only in the CSV).
  - The "same" pairs are mostly Connecticut consolidated city/towns, such as Hartford city and Hartford town.
  - Distribution of the smaller of the two overlap shares: 0 → 1,151 pairs; under 0.1 → 1,058; under 0.5 → 207; 0.5 to 0.9 → 18; ≥ 0.9 → 36.
  - The 18 pairs in the 0.5–0.9 band (e.g. Schaumburg village and township, Aurora city and township) are separate governments covering different ground and stay "separate".
- **Flag table:** `data-v3/geo/town_pairs.csv`, one line per pair, with columns state, county, name_a, geoid_a, src_a, name_b, geoid_b, src_b, a_in_b, b_in_a, class, conflict.
- Rebuild with `tools/town_pairs.py <repo> <tiger_dir> <tl_2024_us_county.zip>` after any town-row change.

## Town gap audit (Task A input)

- `tools/town_gaps.py` compares by name, per county: the v2 town layer as `townsIn()` shows it, against TIGER 2024 incorporated places (≥ 2 % of the place or ≥ 0.5 km² in the county) plus county subdivisions with a government (FUNCSTAT A, B, C, G).
- `tools/town_area_gaps.py` measures the same by area.
- Results: `town_gaps_2024.csv` (per state) and `town_gaps_2024_missing.csv` (109 missing entities).
- By name almost nothing is missing: KS 30 numbered townships, ME 28 plantations, MO 12, OK 9, TX 6, NE 5, NC 5, OR 4; the rest 0–2.
- By area the gap is the hidden different-name rows: Iowa 10.2 % of its town land, Maine 7.0 %, Kansas 3.9 %, Nebraska 2.5 %, Kentucky 3.8 %; everywhere else under 0.5 %.
