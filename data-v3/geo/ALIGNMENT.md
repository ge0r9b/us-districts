# Alignment answers for the Institutions bot (geo lane)

Oct 18, 2026, branch `data/geo`.

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

## 1) A has-own-government column for counties

**Proposal: Institutions owns `has_own_government` in `data-v3/inst/`, keyed by our county GEOID (the `geoid` of `counties.csv`). Geo adds only the TIGER attribute, as a side file.**

- **Why not simply add it to `counties.csv`:** it isn't a geographic fact and TIGER doesn't settle it.
  - TIGER 2024 county FUNCSTAT gives **3,032 "A" (active government)** out of 3,144 county equivalents. The Census of Governments 2022 gives **3,031** county governments. Close, but not the same list.
  - The Census of Governments counts some consolidated city-counties (e.g. TIGER "C": San Francisco, Denver, Philadelphia, Nashville, Anchorage, the 5 NYC boroughs) as municipal governments, not county governments.
  - Some "A" counties have only a vestigial government.
  - Which government row an attribute or officeholder belongs to is an institutions question.
- **Geo provides `data-v3/geo/county_funcstat.csv`:** geoid, tiger_name, tiger_funcstat, meaning, in_counties_csv, with all 3,144 matching `counties.csv`. Institutions can use it as a cross-check and starting point.
- TIGER 2024 FUNCSTAT counts (50 states + DC):

| FUNCSTAT | Count | Where |
|---|---|---|
| A | 3,032 | Active county government |
| F | 42 | Virginia's 38 independent cities, Baltimore city, St. Louis city, Carson City, DC |
| C | 33 | Consolidated city-counties: GA 8, NY 5 (NYC boroughs), AK 4, TN 3, CO 2, KS 2, MT 2, KY 2, PA, CA, FL, IN, LA |
| N | 23 | No county government: CT's 9 planning regions, 9 Massachusetts counties, Rhode Island's 5 counties |
| S | 11 | Alaska census areas (unorganized borough) |
| B | 2 | Lafayette and East Baton Rouge parishes (partly consolidated) |
| G | 1 | Kalawao County, HI |

## 4) Town counts above TIGER (KS +50, NE +14, NH +7, VT +5) and below it (ME −33)

**No duplicates and no merged places. Each difference comes from the audit's TIGER count, which left out county subdivisions with FUNCSTAT I (inactive), N (nonfunctioning) and S (statistical), while v1 shows the real units.**

The side table is `data-v3/geo/v1_towns.csv`, made by `tools/v1_towns.py`. It has columns layer, state, county, row, v1_name, geoid, tiger_name, tiger_kind, funcstat, classfp, match, overlap:
- Every root `data/` **towns** row (20,935) has a TIGER 2024 GEOID: 20,933 matched by name in their county and 2 by name plus overlap (Ohio, Union County: the two "Washington township" rows, 3915981662 and 3915981242).
- Every **places** row (19,477) has a TIGER 2024 place GEOID: 22 told apart by overlap (the Q-G8 duplicate names).
- No GEOID is used twice in either layer.

By state:
- **Kansas, 1,441 rows:** 1,232 A, 128 F (cities as county subdivisions) and **81 I** (inactive townships, real TIGER units). Against the 1,391 counted that is +81, minus **30 missing**: numbered townships ("Township 1"–"Township 6") of Harper, Morris and others. The Step 2 town files fill them.
- **Nebraska, 410:** 315 A, 74 F and **21 I**, minus **5 missing** (Washington County Townships 1, 2, 5, 6, 7); the town files fill them.
- **New Hampshire, 241:** 221 A, 13 F, **6 N** (unincorporated Coos County townships: Success, Dixville, Kilkenny, Millsfield, Odell, …) and **1 I** (Livermore).
- **Vermont, 252:** 237 A, 10 F and **5 I** (Glastenbury, Somerset, Ferdinand, Averill, Lewis).
- **Maine, 453 against 486** (TIGER 459 A + 27 F): **28 plantations are missing** (e.g. Cyr, Garfield, Glenwood, Macwahoc, Moro, Nashville, Reed, St. John plantation in Aroostook), plus F units not in v1. Maine's 42 S units (unorganized territories) are rightly not counted. The town files fill the plantations.

## 6) 2020-vintage GEOID tables

Built by `tools/v3_geoids_2020.py` from TIGER 2020: `tl_2020_us_cd116`, and `tl_2020_SS_sldu` / `_sldl` (the 2018 plans). The format is documented in README.md ("2020-vintage GEOID tables"). Each v2 row is paired with the 2020-plan district of the same code, with the overlap in both directions.

| File | v2 rows | code+same | code | overlap (no same code) | Unpaired 2020 districts |
|---|---|---|---|---|---|
| `ushouse_2020.csv` | 435 | 55 | 372 | 8 | 8 (incl. DC delegate from `dc.js`) |
| `senate_2020.csv` | 1,942 | 215 | 1,679 | 48 | 9 (DC 8 wards from `dc.js`, MA 1) |
| `statehouse_2020.csv` | 4,882 | 418 | 4,293 | 171 | 75 (MA 59, VT 10, NH 4, MD 2: renumbered or merged plans) |

Most rows are `code`: the district keeps its number but its boundary changed in the 2021–22 redistricting. Only `code+same` rows (each ≥ 90 % inside the other) are the same ground. Nebraska's state house rows pair with its 2020 SLDU districts.
