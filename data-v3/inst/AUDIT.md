# Institutions gap inventory, 2020 and 2024 (institutions lane, read-only round)

- **Audited:** branch `data/geo` at `a14a9eb` (includes geo's `0c4afbc`; main `e8040d3` does not have data/geo yet). The audit ran on a detached worktree of `origin/data/geo`. Nothing in `v2/data/`, root `data/` or `v2/index.html` was changed.
- **Run:** `python3 tools/inst_audit.py <checkout of data/geo>` (about 13 s). It runs the geo lane's `tools/coverage_audit.py` without changes, then adds the institution checks. Outputs: `data-v3/inst/inst_gaps.csv` (one row per type × year, with gray names and reasons) and `data-v3/inst/inst_audit.json` (all details: PACK checks, county shortfalls, the 37 pairs, file sizes).
- **Expected counts and where they come from.** Each one is cited; anything without a source is marked *unknown*.
  - Census TIGER 2024 Gazetteer (public domain). The app draws these lines for both years.
  - Census TIGER 2020 Gazetteer: 116th Congress CDs and the 2018 state-legislative plans, which are the lines the 2020 elections were held on. Downloaded untouched to `/workspace/w/inst-raw/tiger2020/` with SHA256SUMS.
  - 2024 place Gazetteer (`/workspace/w/inst-raw/tiger2024/`).
  - 2 U.S.C. §2a: 435 House seats.
  - 2022 Census of Governments, technical documentation (`2022_gov_org_meth_tech_doc.pdf`): 3,031 county, 19,491 municipal and 16,214 town/township governments. These are national figures only.
  - House Clerk `MemberData.xml`, published Oct 1, 2026, saved at `/workspace/w/inst-raw/clerk/MemberData_2026-10-18.xml` (sha256 `01833c6c…`).
- **Status of the geo handoff.**
  - Done by geo, not repeated here: Oklahoma schools 509; unique school names (58 groups, 132 rows); 12 copied-figure pairs fixed.
  - Geo is still working on these, so they are only noted here: 5 gray 2024 state house districts (AL 004, LA 057, MS 115, VA 089, WY 054) and South Dakota district values.
  - Now owned by this lane and ranked below: OR/WY/MO 2024 precinct shortfalls; the 37 partly-overlapping identical pairs; Alaska and Maine schools; officeholders; `entities.csv`.

## 1. Per type × year

"Expected" is the TIGER 2024 count, which is the line set the app draws. "Election-year lines" is TIGER 2020 (116th CDs, 2018 SLD plans): the districts that existed when the 2020 votes were cast. Gray means the district has no value for that year. ≈ means an area-weighted estimate (`est` = both years, `e24` = 2024 only, `e20` = 2020 only).

| Type | Year | Have | Expected (TIGER 2024) | Election-year lines (TIGER 2020) | With results | exact / ≈ | Gray | Officeholders |
|---|---|---|---|---|---|---|---|---|
| US House (CD, incl. DC delegate) | 2020 | 436 | 436 (435 seats, 2 U.S.C. §2a, + DC) | 436 | 436 | 363 / 73 | 0 | no |
| US House | 2024 | 436 | 436 | | 436 | 363 / 73 | 0 | no |
| State senate (SLDU, + 8 DC wards) | 2020 | 1,950 | 1,950 | 1,946 | 1,950 | 1,409 / 541 | 0 | no |
| State senate | 2024 | 1,950 | 1,950 | | 1,949 | 1,410 / 539 | 1 (WY 018) | no |
| State house (SLDL, NE = 49 LDs, + 8 DC wards) | 2020 | 4,890 | 4,890 | 4,842 | 4,890 | 3,594 / 1,296 | 0 | no |
| State house | 2024 | 4,890 | 4,890 | | 4,885 | 3,644 / 1,241 | 5 (geo, in progress) | no |
| School districts, unified (incl. DCPS) | 2020 | 10,872 | 10,872 | 10,849 | 10,846 | 7,117 / 3,729 | 26 | no |
| School districts, unified | 2024 | 10,872 | 10,872 | | 10,792 | 7,008 / 3,784 | 80 | no |
| School districts, elementary | 2020 | 1,952 | 1,952 | 1,945 | 1,949 | 1,056 / 893 | 3 | no |
| School districts, elementary | 2024 | 1,952 | 1,952 | | 1,948 | 1,041 / 907 | 4 | no |
| School districts, secondary | 2020 | 481 | 481 | 473 | 481 | 209 / 272 | 0 | no |
| School districts, secondary | 2024 | 481 | 481 | | 479 | 194 / 285 | 2 | no |
| DC wards | 2020 | 8 | 8 | 8 (2012 plan) | 8 | 8 / 0 | 0 | no |
| DC wards | 2024 | 8 | 8 | | 8 | 8 / 0 | 0 | no |
| Counties (county-equivalents) | 2020 | 3,144 | 3,144 (governments: 3,031, CoG 2022) | 3,143 (CT 8 counties) | 3,143 | 3,113 / 30 (AK boroughs) | 1 (Kalawao, reported with Maui) | no |
| Counties | 2024 | 3,144 | 3,144 | | 3,143 | 3,113 / 30 | 1 | no |
| Towns/townships (county subdivisions) | both | 22,319 | 22,450 (township governments: 16,214, CoG 2022) | 22,504 | values are computed at runtime from precincts | n/a | n/a | no |
| Municipalities (incorporated places, v1 `places` without CDP) | both | 19,476 | 19,465 (TIGER 2024 place FUNCSTAT A; municipal governments: 19,491, CoG 2022) | unknown | unknown (no stored results) | n/a | unknown | no |
| Precincts | 2020 | 163,570 | unknown (no TIGER count; EAC EAVS 2020 not fetched) | | 163,051 with votes (519 zero-vote rows) | n/a | n/a | no |
| Precincts | 2024 | 173,276 | unknown (EAC EAVS 2024 not fetched) | | 166,529 with votes (6,747 zero-vote rows) | n/a | n/a | no |

- **States missing:** none in any district layer, for either year.
- **District count vs TIGER 2024 by state:** every state matches in CD, SLDU, SLDL and all three school sets.
- **Towns:** IA 1,485 vs 1,660 (173 hidden by `normT()`), KS 1,441 vs 1,391, ME 453 vs 486, NE 410 vs 396, NH 241 vs 234, VT 252 vs 247.
- **Places:** only CT is off by more than 2 % (30 vs 29).
- **Precinct votes vs official state totals:** 2024 OR 97.0 %, SD 81.6 %, WY 95.9 %. All other states, and all of 2020, are within 98-102 %.

**Attributes present.** The district rows are `[state, name/code, geometry, 2024 [D,R,total], 2020 [D,R,total], flag]` and nothing else. GEOIDs and the TIGER school type exist only in `data-v3/geo/*.csv` (orchestrator ruling: v2 rows get no GEOIDs). Counties are keyed `State|County` by name in `data/election20XX.js`, with no FIPS code. Precincts are keyed `County|Precinct`, which is not unique. **No officeholder, party-of-member, term or board-member data exists anywhere.** A regex for bioguide/officeholder/incumbent/party fields hits 0 times in every `v2/data/*.js` file and once in `v2/index.html` (a comment).

**2020 vintage.** The app shows 2020 results on the **2024 lines**. That is correct as "2020 president by today's districts", but it is not the 2020 election geography:

| Layer | States whose district count changed from TIGER 2020 to 2024 |
|---|---|
| CD | 13: CA 53→52, CO 7→8, FL 27→28, IL 18→17, MI 14→13, MT 1→2, NY 27→26, NC 13→14, OH 16→15, OR 5→6, PA 18→17, TX 36→38, WV 3→2 |
| SLDU | 2: VT 13→16, WY 30→31 |
| SLDL | 6: MD 67→71, NH 161→164, ND 47→48, VT 104→109, WV 67→100, WY 60→62 |
| Schools | sum of per-state count changes: unified 81, elementary 43, secondary 16 |

Lines also moved in states whose count stayed the same, because of 2021-22 redistricting. Officeholders elected in 2020 have to be attached to 2020-vintage districts, not to these rows (see `OFFICEHOLDERS_PLAN.md`).

## 2. Key mismatches and duplicates

1. **`PACK.lists.schools` (embedded in `v2/index.html`) is out of sync with `v2/data/ussch.js` on data/geo.** It has 13,324 rows but only 13,250 unique (state, name) pairs.
   - **132 rows still carry the old pre-9ff4c00 names.** So 132 renamed districts are missing from the list, and the 58 old names now match no data row.
   - **3 names are mojibake:** "La CaÃ±ada Unified", "EspaÃ±ola Municipal Schools", "PeÃ±asco Independent Schools", against the correct UTF-8 names in the data.
   - **20 states have a "School District Not Defined" ghost row:** AZ, CA, CT, IL, IN, KY, MA, MI, MN, NH, NJ, NY, OH, OR, PA, RI, SC, TN, WI, WY. These are TIGER ZZZ areas.
   - `rowsFor()` and `rowOf()` (index.html lines ~1437 and ~1828) match these lists to data by name. The school type labels agree with TIGER for every matched row.
   - This becomes user-visible the moment data/geo merges.
2. **`PACK.lists.statehouse` has no Nebraska rows** (4,833 vs 4,882 data rows). The 49 LDs exist in `ussldl.js` and in the senate list. v1 `data/Nebraska.js` also has no `statehouse` key.
3. **At-large CDs.** AK, DE, ND, SD, VT and WY are coded `00` consistently in `uscd.js`, PACK and XREF, and in the GEOID `SS00` (TIGER at-large; TIGER also lists PR, which the app doesn't show). However, the map pop-up label in `v2/index.html` (`aname` override near line 2845: `"District "+String(code).replace(/^0+(?=\d)/,"")`) renders `00` as **"District 0"**. I confirmed this by evaluating the same expression in node. The Clerk XML uses `AK00` with district "At Large", so the join stays clean. The DC delegate is `98` / GEOID 1198 in data-v3, but there is no DC row in `uscd.js` (it is injected from `dc.js`).
4. **Name vs GEOID joins.**
   - District rows are joined by `state|name` everywhere in the app.
   - Codes are zero-padded strings (`"001"`), while TIGER names are "State Senate District 1". `data-v3/geo` matched every row (no unmatched rows, no GEOID used twice in any layer). 2 CD, 23 SLDU, 39 SLDL and 49 school rows matched by code or name only, without the point test.
   - Counties and precincts are joined by name only.
   - Officeholder and entity joins should use the data-v3 GEOID plus vintage, never `state|name`.
5. **Duplicates.** There are no duplicate (state, name) pairs in any district layer on data/geo. Precinct keys still repeat (QUESTIONS.md Q-G7).
6. **v1 vs v2.** `data/Oklahoma.js` lists 413 schools vs 509 in v2, so `schoolsInCounty()` misses the 96 elementary districts. Nebraska statehouse is absent in v1. Root `data/` is never touched; this needs an app-side change.
7. **Identical figures.** All **37** partly-overlapping pairs listed in COVERAGE.md (12 in 2024, 25 in 2020; mostly Montana elementary/high-school pairs) were found by name, and all 37 **still share identical figures** at a14a9eb.

## 3. Gaps ranked by user impact

The source order is official first, then TIGER, VEST, MEDSL and OpenElections. Sizes are raw / gzip -9 of the files as they are now.

| # | Gap | Who sees it | Proposed source | Files | Expected before → after | Size / load cost |
|---|---|---|---|---|---|---|
| 1 | School and state-house menu lists out of sync (§2.1, §2.2) | Anyone opening school districts in OH, NJ, CA, TX, AR, IL, MO, MT, OK and the 20 ghost-row states, and Nebraska state house | `v2/data/ussch.js` / `ussldl.js` themselves, `data-v3/geo/v2_name_collisions.csv`, TIGER 2024 names | `v2/index.html` PACK (**orchestrator only**) | Schools list rows matching data 13,169 → 13,304 (ghosts 20 → 0, mojibake 3 → 0); NE state house list 0 → 49 | Measured: schools list 777,673 → 777,862 B (+189); statehouse list 223,361 → 225,557 B (+2,196). This is eager inline data in a 5.9 MB / 884 KB-gz page, under +0.05 %. |
| 2 | At-large CD label "District 0" (§2.3) | Every pop-up in AK, DE, ND, SD, VT, WY | TIGER 2024 CD119 (`SS00` = at-large); House Clerk "At Large" | `v2/index.html` `aname` (**orchestrator only**) | 6 wrong labels → 0 | 0 B data; about 30 B of code |
| 3 | 2024 precinct shortfalls OR / WY / MO → gray and ≈ districts | OR (2 gray schools: Pleasant Hill 1, Scappoose 1J), WY (Uinta 4, Weston 1; HD 054 is geo's), MO (8 gray schools); ≈ rows in 2024 schools: MO 492/516, OR 101/197, WY 27/48 | Official: OR SOS / county clerk precinct results + county precinct GIS; WY SOS precinct results + county clerk maps; MO SOS / county clerk results + county precinct maps. Then MEDSL 2024 official (CC0), with VEST 2020 shapes for unchanged precincts. | Root `data/precincts2024/*` is v1 and read-only, with no override allowed. So only the district values in `ussch.js` (and `ussldl.js` / `ussldu.js`) can change, recomputed offline. **Those files are being edited by the Election Data bot (2016 triples): needs orchestrator coordination and a rebase on main.** | Missing votes in counties outside 90-110 % (Dem+Rep): OR 32,986 in Columbia, Gilliam, Jefferson, Lane, Polk, Sherman (state shortfall 65,712); WY 8,700 in Albany, Fremont, Uinta, Weston (10,966); MO 22,250 in Cape Girardeau, Cole, Dallas, Miller, Pettis, Shelby (50,301). Gray: 12 → 0 only if shaped official 2024 precincts are found; otherwise unknown. | Values only: about 20 B per changed triple, so +0.3 KB for 12 rows. Precinct files themselves: OR 793 KB / 265 KB gz, WY 342 / 116, MO 1,052 / 360 (unchanged). |
| 4 | Alaska and Maine school districts | AK gray 2024: 7 (incl. Kake, Nenana); 2020: 14; ≈ 43/53. ME gray 2024: 14; 2020: 1. | AK Division of Elections official precinct results + AK DEED district boundaries (+ TIGER 2024 UNSD); ME SOS (Division of Elections) official town results | `v2/data/ussch.js` (**coordination + rebase**) | AK: values that can be computed exactly from whole precincts inside a district; the rest stays gray with a reason (count unknown until computed). ME: the 14 combined units ("Brownville/Twps") have no official split, so they are expected to stay structural. Proposal: a "reported with <town>" note instead of plain gray. | About +0.4 KB to `ussch.js` (4.75 MB / 1.58 MB gz) |
| 5 | 37 partly-overlapping pairs with identical figures (§2.7) | 37 rows in list views (MT elementary/high-school pairs, IL Grand Prairie, CA, OR Harney) | MT SOS official 2024 precinct results; VEST 2020 MT/CA/IL/OR (CC BY 4.0); TIGER 2024 ELSD/SCSD | `v2/data/ussch.js` (**coordination + rebase**) | 37 → 0 unverified pairs. Each one is either confirmed legitimate (empty extra territory) or recomputed exactly or ≈. | About 0 B |
| 6 | No officeholders on any district layer | Every district pop-up and list | House Clerk MemberData.xml; official legislature rosters; OpenStates `people` (CC0) as fallback (see `OFFICEHOLDERS_PLAN.md`) | v3: `data-v3/inst/officeholders_*.csv`. A v2 file would need an app change (orchestrator). | US House 0 → 435 seats (433 filled + 2 vacant in the Oct 1, 2026 Clerk file: FL-20, TX-23) + DC delegate; legislatures: 0 → per-chamber roster counts (seat totals unknown until fetched) | Measured, House only: a minimal lazy file `[statedistrict, name, party, bioguide]` × 441 rows = 17,742 B raw / 7,010 B gz. Legislatures would be about 15× the rows, so roughly 100 KB gz projected, lazy per state. |
| 7 | No institution registry (`entities.csv`) | The institution search finds only countries, states and provinces plus district-type plurals; no county, town or school board is a searchable government | TIGER 2024 (GEOIDs from data-v3/geo), 2022 Census of Governments (government status), PACK/XREF (read-only) | v3: `data-v3/inst/entities.csv` (schema in `ENTITIES_SCHEMA.md`) | 0 → about 3,144 counties + 22k cousubs + 19.5k places + 13.3k schools + 7.3k district rows | v3 only; no v2 load cost |
| 8 | 2020 shown on 2024 lines | 2020 / change views in the 13 CD, 2 SLDU and 6 SLDL states above | TIGER 2020 (116th CD, 2018 SLD) + VEST 2020 precincts (CC BY 4.0) | v3: per-vintage layers (`<layer>_2020`) | Label only in v2; 2020-vintage districts in v3 | v3 only |

Smaller items, already in COVERAGE.md and not repeated here: VT gores, KY 3, CO 2, AL 2 and other 1-2 gray schools per state.

## 4. Top 5 v2 fixes, ranked by visible impact

The rows below are gaps 1-5 above. Every one of them touches files outside this lane's write scope (`v2/index.html`) or files the Election Data bot is editing right now (`ussch.js`, `ussldl.js`, `ussldu.js`, `uscd.js`). So **none can be applied without the orchestrator.** Fixes 3-5 need a rebase on main after the 2016 triples land.

1. PACK school and state-house list sync: +2.4 KB in index.html (inline).
2. At-large "At large" label: 0 B data.
3. OR/WY/MO 2024 district values recomputed from official shaped precincts: up to 12 gray → 0, fewer ≈ rows, about +0.3 KB.
4. Alaska exact school values, plus a Maine "reported with" reason: up to 21 gray (2024) / 15 (2020) affected, about +0.4 KB.
5. Check the 37 identical pairs: 37 unverified → 0, about 0 B.

## 5. Questions for the geography bot: one-time alignment of counties, municipalities and towns

1. **Counties as governments vs county-equivalents.** Can `data-v3/geo/counties.csv` gain a `gov_status` column? CoG 2022 has 3,031 county governments vs 3,144 TIGER county-equivalents. The gaps are CT planning regions and RI, which have no county government; consolidated city-counties, which CoG counts as municipal; and Alaska's Unorganized Borough census areas. Which source do you want: CoG 2022 Government Units Listing, or TIGER FUNCSTAT on the county file?
2. **Connecticut.** The app has 9 county rows in 2024 and 8 in 2020 per TIGER, but results are keyed `State|County` by name. Are the 2024 CT rows the 9 planning regions (GEOID 091xx) and 2020 the 8 old counties? Entities need both vintages.
3. **Municipalities vs towns.** v1 `places` (19,476 non-CDP rows) and county subdivisions overlap in the 12 strong-MCD states (New England, NY, NJ, PA, MI, WI, MN…). Should a place-as-MCD (cousub FUNCSTAT F; cities like Iowa's 62) be one entity with two GEOIDs (place SSPPPPP + cousub), or two entities? I propose one entity, `kind=municipality`, with `geoid_place` and `geoid_cousub`.
4. **Town counts above TIGER** (KS +50, NE +14, NH +7, VT +5) and below (ME −33). Are these places merged into town rows, or duplicates? I'd like your `v1_towns.csv` GEOID table (planned under Q-G1) before building entities.
5. **`normT()` hidden rows** (IL 473, NY 197, KS 154, IA 173…). For entities I will key on GEOID, not on name. Can you confirm each hidden parts row has a distinct cousub GEOID?
6. **Vintage.** Will you add 2020-vintage GEOID tables (116th CD, 2018 SLD, 2020 schools and county subdivisions)? The 2020 officeholders must join to those.

## 6. Sources and licences used in this audit
| Source | Use | Licence |
|---|---|---|
| Census TIGER 2024 / 2020 Gazetteer (counties, cousubs, 119CDs / 116CDs, sldu, sldl, unsd, elsd, scsd, place) | expected counts | Public domain |
| 2 U.S.C. §2a | 435 seats | Public law |
| 2022 Census of Governments technical documentation (www2.census.gov/programs-surveys/gus/datasets/2022/2022_gov_org_meth_tech_doc.pdf) | national government counts | Public domain |
| House Clerk MemberData.xml (clerk.house.gov/xml/lists/MemberData.xml), published Oct 1, 2026 | officeholder plan, size measurement | Public domain (US government work) |
| openstates/people LICENSE (checked Oct 18, 2026) | fallback roster source | CC0 1.0 |
| unitedstates/congress-legislators LICENSE (checked Oct 18, 2026) | historical House terms (2020 vintage) | CC0 1.0 |
