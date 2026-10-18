# Data coverage audit (geo & institution data lane)

Branch `data/geo`. Generated Oct 18, 2026 (America/New_York) from `main` at 08d298c by `tools/coverage_audit.py` (read-only on all data files).
The long-form per-build coverage log, sources and licences stay in `v2/data/COVERAGE.md`; this file is the lane's audit matrix and gap list and does not replace it.

Re-run: `python3 tools/coverage_audit.py . --csv /tmp/cov.csv --md /tmp/cov.md` (downloads the Census 2024 Gazetteer once to `~/.cache/us-districts/tiger2024`; about 5 s).

## What is checked
- **Layers and files:** states `v2/data/usstates.js`; counties `v2/data/uscounties.js` + `data/election2020.js` / `data/election2024.js` (+ `v2/data/ak.js` boroughs); towns (county subdivisions) `data/<State>.js` `towns` + `v2/data/parts/<State>.js`; precincts `data/precincts20XX/<State>.js` (+ `v2/data/precincts20XX-DC.js`); US House `v2/data/uscd.js`; state senate `v2/data/ussldu.js`; state house `v2/data/ussldl.js`; school districts `v2/data/ussch.js`; DC wards `v2/data/dc.js` (applied over the national files the way the app does at runtime).
- **Expected counts:** Census TIGER 2024 Gazetteer (public domain): counties, county subdivisions, 119th CDs, SLDU, SLDL, unified + elementary + secondary school districts; "not defined" (ZZ/ZZZ) units dropped. Towns are expected only in states with governmental county subdivisions (FUNCSTAT A/B/C/G); expected count = all cousubs except FUNCSTAT N/S/I. Nebraska state house = its 49 LDs (unicameral); DC = 8 wards under senate, house and wards, 1 school district (DCPS), 1 delegate district.
- **Per cell (layer x year x state):** feature count vs TIGER (exact for states/counties/CD/SLD, 2 % for towns/schools), features without results (gray, listed by name), empty geometries, duplicate or missing names, broken references (election rows without a shape, shapes without results, precinct county names not in the county layer, `v2/data/x20` keys with no 2024 precinct, per-state file vs national file feature counts), precinct vote sum vs official state total (98-102 %) and per county (90-110 %).
- **Status:** P present; S suspect (any check fails); M missing; `-` not applicable. Boundaries are 2024 for both years (app rule), so the 2020 column differs only in results.

## Matrix (2020/2024)
| State | states | counties | towns | precincts | ushouse | senate | statehouse | schools | dcwards |
|---|---|---|---|---|---|---|---|---|---|
| AL | P/P | P/P | -/- | P/S | P/P | P/P | P/S | P/S | -/- |
| AK | P/P | P/P | -/- | P/P | P/P | P/P | P/P | S/S | -/- |
| AZ | P/P | P/P | -/- | P/P | P/P | P/P | P/P | P/P | -/- |
| AR | P/P | P/P | -/- | P/P | P/P | P/P | P/P | S/S | -/- |
| CA | P/P | P/P | -/- | P/P | P/P | P/P | P/P | S/S | -/- |
| CO | P/P | P/P | -/- | P/S | P/P | P/P | P/P | P/S | -/- |
| CT | P/P | P/P | P/P | P/S | P/P | P/P | P/P | P/P | -/- |
| DE | P/P | P/P | -/- | P/P | P/P | P/P | P/P | P/P | -/- |
| DC | P/P | P/P | -/- | P/P | P/P | P/P | P/P | P/P | P/P |
| FL | P/P | P/P | -/- | P/P | P/P | P/P | P/P | P/P | -/- |
| GA | P/P | P/P | -/- | P/S | P/P | P/P | P/P | P/P | -/- |
| HI | P/P | P/P | -/- | P/P | P/P | P/P | P/P | P/P | -/- |
| ID | P/P | P/P | -/- | S/P | P/P | P/P | P/P | P/P | -/- |
| IL | P/P | P/P | P/P | P/S | P/P | P/P | P/P | S/S | -/- |
| IN | P/P | P/P | P/P | P/P | P/P | P/P | P/P | P/P | -/- |
| IA | P/P | P/P | S/S | P/P | P/P | P/P | P/P | P/P | -/- |
| KS | P/P | P/P | S/S | P/S | P/P | P/P | P/P | P/P | -/- |
| KY | P/P | P/P | -/- | P/P | P/P | P/P | P/P | P/S | -/- |
| LA | P/P | P/P | -/- | P/P | P/P | P/P | P/S | P/P | -/- |
| ME | P/P | P/P | S/S | P/P | P/P | P/P | P/P | S/S | -/- |
| MD | P/P | P/P | -/- | P/P | P/P | P/P | P/P | P/P | -/- |
| MA | P/P | P/P | P/P | P/S | P/P | P/P | P/P | P/P | -/- |
| MI | P/P | P/P | P/P | P/S | P/P | P/P | P/P | P/P | -/- |
| MN | P/P | P/P | P/P | P/P | P/P | P/P | P/P | P/P | -/- |
| MS | P/P | P/P | -/- | P/S | P/P | P/P | P/S | P/S | -/- |
| MO | P/P | P/P | P/P | P/S | P/P | P/P | P/P | S/S | -/- |
| MT | P/P | P/P | -/- | P/S | P/P | P/P | P/P | S/S | -/- |
| NE | P/P | P/P | S/S | P/P | P/P | P/P | P/S | P/P | -/- |
| NV | P/P | P/P | -/- | P/P | P/P | P/P | P/P | P/P | -/- |
| NH | P/P | P/P | S/S | P/P | P/P | P/P | P/P | P/P | -/- |
| NJ | P/P | P/P | P/P | P/P | P/P | P/P | P/P | S/S | -/- |
| NM | P/P | P/P | -/- | P/P | P/P | P/P | P/P | S/P | -/- |
| NY | P/P | P/P | P/P | P/P | P/P | P/P | P/P | S/S | -/- |
| NC | P/P | P/P | -/- | P/S | P/P | P/P | P/P | P/P | -/- |
| ND | P/P | P/P | P/P | S/S | P/P | P/P | P/P | P/P | -/- |
| OH | P/P | P/P | P/P | P/S | P/P | P/P | P/P | S/S | -/- |
| OK | P/P | P/P | -/- | P/P | P/P | P/P | P/P | S/S | -/- |
| OR | P/P | P/P | -/- | P/S | P/P | P/P | P/P | P/S | -/- |
| PA | P/P | P/P | P/P | P/P | P/P | P/P | P/P | P/P | -/- |
| RI | P/P | P/P | P/P | P/P | P/P | P/P | P/P | P/P | -/- |
| SC | P/P | P/P | -/- | P/P | P/P | P/P | P/P | P/P | -/- |
| SD | P/P | P/P | P/P | P/S | P/P | P/P | P/P | P/S | -/- |
| TN | P/P | P/P | -/- | P/S | P/P | P/P | P/P | P/P | -/- |
| TX | P/P | P/P | -/- | P/P | P/P | P/P | P/P | S/S | -/- |
| UT | P/P | P/P | -/- | P/P | P/P | P/P | P/P | P/P | -/- |
| VT | P/P | P/P | S/S | P/P | P/P | P/P | P/P | S/S | -/- |
| VA | P/P | P/P | -/- | P/S | P/P | P/P | P/S | P/P | -/- |
| WA | P/P | P/P | -/- | P/P | P/P | P/P | P/P | P/P | -/- |
| WV | P/P | P/P | -/- | P/S | P/P | P/P | P/P | P/P | -/- |
| WI | P/P | P/P | P/P | P/P | P/P | P/P | P/P | P/S | -/- |
| WY | P/P | P/P | -/- | P/S | P/P | P/P | P/S | P/S | -/- |

| Layer | Year | Features | TIGER 2024 expected | With results | P | S | M |
|---|---|---|---|---|---|---|---|
| states | 2020 | 51 | 51 | 51 | 51 | 0 | 0 |
| states | 2024 | 51 | 51 | 51 | 51 | 0 | 0 |
| counties | 2020 | 3144 | 3144 | 3143 | 51 | 0 | 0 |
| counties | 2024 | 3144 | 3144 | 3143 | 51 | 0 | 0 |
| towns | 2020 | 20894 | 22450 | 20894 | 15 | 6 | 0 |
| towns | 2024 | 20894 | 22450 | 20894 | 15 | 6 | 0 |
| precincts | 2020 | 163570 |  | 163051 | 49 | 2 | 0 |
| precincts | 2024 | 173276 |  | 166529 | 31 | 20 | 0 |
| ushouse | 2020 | 436 | 436 | 436 | 51 | 0 | 0 |
| ushouse | 2024 | 436 | 436 | 436 | 51 | 0 | 0 |
| senate | 2020 | 1950 | 1950 | 1950 | 51 | 0 | 0 |
| senate | 2024 | 1950 | 1950 | 1950 | 51 | 0 | 0 |
| statehouse | 2020 | 4890 | 4890 | 4890 | 51 | 0 | 0 |
| statehouse | 2024 | 4890 | 4890 | 4885 | 45 | 6 | 0 |
| schools | 2020 | 13209 | 13305 | 13183 | 37 | 14 | 0 |
| schools | 2024 | 13209 | 13305 | 13125 | 30 | 21 | 0 |
| dcwards | 2020 | 8 | 8 | 8 | 1 | 0 | 0 |
| dcwards | 2024 | 8 | 8 | 8 | 1 | 0 | 0 |

Notes: town rows carry no results of their own (values come from precincts at runtime), so towns are judged on boundaries only. 2020 and 2024 US House / senate / counties show no gray because ≈ estimates count as "with results" (the ≈ share is in `v2/data/COVERAGE.md`: e.g. 2024 house 1,241 ≈, schools 4,879 ≈).

## Cross-check with the gray inventory in `v2/data/COVERAGE.md` (build 1539/1559)
| Item | Inventory | This audit | Agrees |
|---|---|---|---|
| 2024 state house gray | 5: AL 004, LA 057, MS 115, VA 089, WY 054 | same 5 | yes |
| 2024 school districts gray | 84 | 84 (SD 26, ME 14, VT 8, MO 8, AK 5, KY 3, then 2/1 each) | yes |
| 2020 school districts gray | 26 (AK 14, CA 4, VT 3 …) | 26 | yes |
| 2024 counties with no precinct file | 9 (SD 8, MS Issaquena) | 9, same counties | yes |
| 2024 counties outside 90-110 % | 41 (OR 6) | 40 (OR 5: Columbia, Gilliam, Jefferson, Lane, Sherman) | off by one, OR (threshold/rounding; not yet traced) |
| Counties | 3,112 | 3,144 shapes = TIGER 3,144; 3,143 with results (Alaska's 30 via `ak.js` ≈; Kalawao reported with Maui) | yes (inventory counts Alaska/DC differently) |
| US House / senate / house boundaries | 435 / 1,942 / 4,882 | 436 / 1,950 / 4,890 incl. DC delegate + 8 wards; all equal TIGER 2024 | yes |
| School district boundaries | 13,208 | 13,209 incl. DCPS vs TIGER 13,305: Oklahoma short by 96 (all other states within 2 %) | **new gap** |

Not yet checked against official state sources beyond what the inventory already records (county totals = certified). That is the next pass.

## Prioritized gaps (with reasons and likely source)
1. **Oklahoma school districts: 96 missing boundaries.** Layer has 413 = TIGER 2024 unified districts; the 96 TIGER 2024 elementary districts (ELSD) are absent in both years. Source: Census TIGER 2024 ELSD (+ results from OK State Election Board precinct returns via MEDSL, CC0).
2. **Iowa townships missing.** 60 town rows (cities only) vs 1,660 TIGER county subdivisions (1,598 townships, FUNCSTAT G). Town drill-down in Iowa has no townships. Source: TIGER 2024 COUSUB.
3. **South Dakota 2024 precincts: 81.6 % of official votes;** 8 counties have no precincts (Brookings, Brown, Haakon, Hughes, Lawrence, Potter, Sully, Yankton: vote centers or no published shapes), Pennington outside 90-110 %; causes 26 gray 2024 school districts. Partly structural (vote centers have no geography). Source: SD SOS official results; county GIS for Lawrence.
4. **2024 state house gray (5): AL 004, LA 057, MS 115, VA 089, WY 054.** Precinct polygons cover 39-80 % of the districts (AL Limestone/Morgan, LA St. John the Baptist, MS Harrison, VA Suffolk/Chesapeake, WY Fremont 05-1 split). Source: official 2024 precinct shapes with district attributes from state/county GIS.
5. **Oregon 2024 precincts: 97.0 % of official;** 5 counties outside 90-110 % (Columbia, Gilliam, Jefferson, Lane, Sherman); 2 gray schools (Pleasant Hill 1, Scappoose 1J). Source: county clerk precinct results + county precinct GIS (OR SOS).
6. **Wyoming 2024 precincts: 95.9 % of official;** Albany, Fremont, Uinta, Weston outside 90-110 % (shape names do not match 2024 codes); HD 054 + 2 schools gray. Source: WY SOS precinct results + county clerk precinct maps.
7. **Missouri 2024:** 6 counties outside 90-110 % (Cape Girardeau, Cole, Dallas, Miller, Pettis, Shelby; renumbered/merged precincts) and 8 gray schools. Source: county clerk 2024 precinct maps; MEDSL official returns (CC0).
8. **District rows have no stable ids (GEOID) and some (state, name) keys collide:** OH 49, NJ 27, CA 22, TX 22, AR 4, IL/MO/MT/OK 2 duplicate school names (all real TIGER duplicates). An earlier pass summed same-named districts (see `v2/data/COVERAGE.md`). Fix: add TIGER GEOID as an extra trailing row element (the app's `decRows` ignores extra elements; needs orchestrator sign-off). Source: TIGER 2024.
9. **No institution attributes beyond name:** no district rows carry representatives/officeholders, party of member, or GEOIDs in any layer (only state, name/number, geometry, results). Source: official rosters (Clerk of the House, state legislature sites); out of scope for this pass, logged.
10. **Alaska schools:** 14 gray (2020), 5 gray (2024), area-weighting rejected; **Maine:** 14 gray 2024 (unorganized territories reported combined with towns) and 453 town rows vs 486 TIGER. Mostly structural. Source: AK Division of Elections precinct results + AK DEED REAA boundaries; ME SOS town returns.
11. Smaller: VT 8 gores (structural, no voters), KY 3, CO 2 (Aspen, Salida), AL 2 (Fort Rucker, Guntersville), MS/MT/NY/OH 2 each, AR/NJ/TX/WI 1 gray 2024 schools; 2020: CA 4, VT 3, ME/NJ/NM/NY/TX 1. 2024 precinct counties outside 90-110 % elsewhere: AL 2, CO 3, GA 3, OH 3, KS 2, VA 2, CT/IL/MA/MI/MT/NC/ND/TN/WV 1; MS Issaquena has no precincts. 2020 (VEST): Idaho Camas, North Dakota Sioux outside 90-110 %.
12. Town counts slightly above TIGER (KS 1,441 vs 1,391, NE 410 vs 396, NH 241 vs 234, VT 252 vs 247): probably places merged into town rows; verify for duplicates. `data/Nebraska.js` has no `statehouse` key (the national file has 49 rows; app uses the national file).

Info: 2024 California precinct file has 6,154 zero-vote rows of 24,202 (Statewide Database SR precincts), Texas 364, Washington 206; 2020 Nevada 152, Texas 157, Washington 108, Maryland 41, Kentucky 20. Not counted as gaps.

## All suspect cells
| State | Layer | Year | Features | TIGER | Reasons |
|---|---|---|---|---|---|
| Alabama | precincts | 2024 | 1911 |  | 2 counties outside 90-110% |
| Alabama | statehouse | 2024 | 105 | 105 | gray 1/105 (004) |
| Alabama | schools | 2024 | 141 | 141 | gray 2/141 (Fort Rucker School District, Guntersville City School District) |
| Alaska | schools | 2020 | 53 | 53 | gray 14/53 (Yupiit School District, Kashunamiut School District, Dillingham City School District, Galena City School District, Hoonah City School District, Hydaburg City School District, Kake City School District, Klawock City School District …) |
| Alaska | schools | 2024 | 53 | 53 | gray 5/53 (Kashunamiut School District, Hydaburg City School District, Klawock City School District, Pelican City School District, Tanana City School District) |
| Arkansas | schools | 2020 | 234 | 234 | 4 duplicate names |
| Arkansas | schools | 2024 | 234 | 234 | gray 1/234 (Jessieville School District); 4 duplicate names |
| California | schools | 2020 | 974 | 974 | gray 4/974 (Washington Unified School District, Mountain View Elementary School District, Ocean View Elementary School District, Kashia Elementary School District); 22 duplicate names |
| California | schools | 2024 | 974 | 974 | 22 duplicate names |
| Colorado | precincts | 2024 | 3144 |  | 3 counties outside 90-110% |
| Colorado | schools | 2024 | 178 | 178 | gray 2/178 (Aspen School District 1, Salida School District R-32) |
| Connecticut | precincts | 2024 | 167 |  | 1 counties outside 90-110% |
| Georgia | precincts | 2024 | 2636 |  | 3 counties outside 90-110% |
| Idaho | precincts | 2020 | 934 |  | 1 counties outside 90-110% |
| Illinois | precincts | 2024 | 8498 |  | 1 counties outside 90-110% |
| Illinois | schools | 2020 | 862 | 862 | 2 duplicate names |
| Illinois | schools | 2024 | 862 | 862 | 2 duplicate names |
| Iowa | towns | 2020 | 60 | 1660 | count 60 vs TIGER 1660 |
| Iowa | towns | 2024 | 60 | 1660 | count 60 vs TIGER 1660 |
| Kansas | towns | 2020 | 1441 | 1391 | count 1441 vs TIGER 1391 |
| Kansas | towns | 2024 | 1441 | 1391 | count 1441 vs TIGER 1391 |
| Kansas | precincts | 2024 | 3665 |  | 2 counties outside 90-110% |
| Kentucky | schools | 2024 | 177 | 177 | gray 3/177 (Somerset Independent School District, East Bernstadt Independent School District, Laurel County School District for East Bernstadt ISD) |
| Louisiana | statehouse | 2024 | 105 | 105 | gray 1/105 (057) |
| Maine | towns | 2020 | 453 | 486 | count 453 vs TIGER 486 |
| Maine | towns | 2024 | 453 | 486 | count 453 vs TIGER 486 |
| Maine | schools | 2020 | 267 | 267 | gray 1/267 (Sagadahoc Unorganized Territory) |
| Maine | schools | 2024 | 267 | 267 | gray 14/267 (Indian Island, Kingsbury Plantation, School Administrative District 41, Oxford Unorganized Territory, Franklin Unorganized Territory, Sagadahoc Unorganized Territory, Kennebec Unorganized Territory, Lincoln Unorganized Territory …) |
| Massachusetts | precincts | 2024 | 2337 |  | 1 counties outside 90-110% |
| Michigan | precincts | 2024 | 3975 |  | 1 counties outside 90-110% |
| Mississippi | precincts | 2024 | 1703 |  | 1 counties with no precincts |
| Mississippi | statehouse | 2024 | 122 | 122 | gray 1/122 (115) |
| Mississippi | schools | 2024 | 137 | 137 | gray 2/137 (South Delta School District, Western Line School District) |
| Missouri | precincts | 2024 | 3021 |  | 6 counties outside 90-110% |
| Missouri | schools | 2020 | 516 | 516 | 2 duplicate names |
| Missouri | schools | 2024 | 516 | 516 | gray 8/516 (Eldon R-I School District, La Monte R-IV School District, Sweet Springs R-VII School District, Cape Girardeau 63 School District, Miller County R-III School District, Cole Camp R-I School District, Delta C-7 School District, Pettis County R-XII School District); 2 duplicate names |
| Montana | precincts | 2024 | 720 |  | 1 counties outside 90-110% |
| Montana | schools | 2020 | 398 | 398 | 2 duplicate names |
| Montana | schools | 2024 | 398 | 398 | gray 2/398 (Lambert Elementary School District, Lambert High School District); 2 duplicate names |
| Nebraska | towns | 2020 | 410 | 396 | count 410 vs TIGER 396 |
| Nebraska | towns | 2024 | 410 | 396 | count 410 vs TIGER 396 |
| Nebraska | statehouse | 2024 | 49 | 49 | data/Nebraska.js statehouse has 0 features vs 49 in v2 national file |
| New Hampshire | towns | 2020 | 241 | 234 | count 241 vs TIGER 234 |
| New Hampshire | towns | 2024 | 241 | 234 | count 241 vs TIGER 234 |
| New Jersey | schools | 2020 | 557 | 557 | gray 1/557 (Ocean Township School District); 27 duplicate names |
| New Jersey | schools | 2024 | 557 | 557 | gray 1/557 (Gibbsboro Borough School District); 27 duplicate names |
| New Mexico | schools | 2020 | 89 | 89 | gray 1/89 (Loving Municipal Schools) |
| New York | schools | 2020 | 680 | 680 | gray 1/680 (New Suffolk Common School District) |
| New York | schools | 2024 | 680 | 680 | gray 2/680 (Bath Central School District, Geneva City School District) |
| North Carolina | precincts | 2024 | 2643 |  | 1 counties outside 90-110% |
| North Dakota | precincts | 2020 | 422 |  | 1 counties outside 90-110% |
| North Dakota | precincts | 2024 | 379 |  | 1 counties outside 90-110% |
| Ohio | precincts | 2024 | 8786 |  | 3 counties outside 90-110% |
| Ohio | schools | 2020 | 611 | 611 | 49 duplicate names |
| Ohio | schools | 2024 | 611 | 611 | gray 2/611 (Shelby City School District, Carey Exempted Village School District); 49 duplicate names |
| Oklahoma | schools | 2020 | 413 | 509 | count 413 vs TIGER 509; 2 duplicate names |
| Oklahoma | schools | 2024 | 413 | 509 | count 413 vs TIGER 509; 2 duplicate names |
| Oregon | precincts | 2024 | 1244 |  | votes 97.0% of official; 5 counties outside 90-110% |
| Oregon | schools | 2024 | 197 | 197 | gray 2/197 (Pleasant Hill School District 1, Scappoose School District 1J) |
| South Dakota | precincts | 2024 | 623 |  | votes 81.6% of official; 8 counties with no precincts; 1 counties outside 90-110% |
| South Dakota | schools | 2024 | 148 | 148 | gray 26/148 (Britton-Hecla School District 45-4, Agar-Blunt-Onida School District 58-3, Groton Area School District 06-6, Aberdeen School District 06-1, Arlington School District 38-1, Brookings School District 05-1, Elkton School District 05-3, Frederick Area School District 06-2 …) |
| Tennessee | precincts | 2024 | 1845 |  | 1 counties outside 90-110% |
| Texas | schools | 2020 | 1019 | 1019 | gray 1/1019 (Boys Ranch Independent School District); 22 duplicate names |
| Texas | schools | 2024 | 1019 | 1019 | gray 1/1019 (Boys Ranch Independent School District); 22 duplicate names |
| Vermont | towns | 2020 | 252 | 247 | count 252 vs TIGER 247 |
| Vermont | towns | 2024 | 252 | 247 | count 252 vs TIGER 247 |
| Vermont | schools | 2020 | 131 | 131 | gray 3/131 (Averys Gore School District, Lewis School District, Warners Grant School District) |
| Vermont | schools | 2024 | 131 | 131 | gray 8/131 (Buels Gore School District, Ferdinand School District, Glastenbury School District, Somerset School District, Averill School District, Averys Gore School District, Warners Grant School District, Warrens Gore School District) |
| Virginia | precincts | 2024 | 2518 |  | 2 counties outside 90-110% |
| Virginia | statehouse | 2024 | 100 | 100 | gray 1/100 (089) |
| West Virginia | precincts | 2024 | 1611 |  | 1 counties outside 90-110% |
| Wisconsin | schools | 2024 | 421 | 421 | gray 1/421 (Sturgeon Bay School District) |
| Wyoming | precincts | 2024 | 415 |  | votes 95.9% of official; 4 counties outside 90-110% |
| Wyoming | statehouse | 2024 | 62 | 62 | gray 1/62 (054) |
| Wyoming | schools | 2024 | 48 | 48 | gray 2/48 (Uinta County School District 4, Weston County School District 1) |
