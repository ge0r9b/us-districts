# 2016 President: v2-format build (offline, not loaded by v2 yet)

Triples are [d, r, total] = [Clinton, Trump, all presidential candidates], the same as 2020/2024. ≈ (`e16`, or a 4th element `1` in `ds2016.js`) is used **only** for area-weighted values. A missing key/null means gray (no source).

## Sources
- Precincts: VEST 2016 General Election precinct boundaries and results, Harvard Dataverse doi:10.7910/DVN/NH5S2I (CC BY 4.0), dataset v98, 51 state zips (retrieved 2026-10-18; box copy `/workspace/vest16/`, not committed).
- States layer: FEC Federal Elections 2016, Table 2 (`raw/federalelections2016.xlsx`).
- County polygons for assigning precincts to counties: v2's own `v2/data/uscounties.js`, so every key exists in v2.

## Files for the app (on data/election, lazy-loaded; nothing loads them until the app adds 2016 loaders)
| File | Bytes | Global call / row shape | Load when |
|---|---|---|---|
| `v2/data/election2016.js` | 138,967 | `window.ELECTION2016={"State|County":[d,r,t],...};` same shape as `ELECTION2020`. 3,144 keys incl. Alaska boroughs and `District of Columbia|District of Columbia` (for 2020 these come from ak.js/dc.js). Exact precinct sums, never ≈. | the 2016 county view, once, like `loadE2020` |
| `v2/data/ds2016-states.js` | 1,892 | `window.__ds2016&&window.__ds2016("states",{"State":[d,r,t],...});` FEC 2016, exact. | the states list in 2016 |
| `v2/data/ds2016-cd.js` | 16,878 | `window.__ds2016&&window.__ds2016("ushouse",{"State|01":[d,r,t] or [d,r,t,1]})` | the US House list/map in 2016 |
| `v2/data/ds2016-sldu.js` | 71,940 | same, layer `"senate"`, keys `State|009` (TIGER SLDUST, as in ussldu.js) | state senate in 2016 |
| `v2/data/ds2016-sldl.js` | 175,869 | same, layer `"statehouse"`, keys `State|055` (as in ussldl.js) | state house in 2016 |
| `v2/data/ds2016-sch.js` | 822,361 | same, layer `"schools"`, keys `State|Name` with the Geo renames (`Name (County)`) | schools in 2016 |
| `v2/data/precincts2016/<State>.js` | 50 files, 44,359,377 total | `__prec(state,[[county,precinct,d,r,t,polys]],credit)`: identical to `data/precincts2020/<State>.js` (polys = delta-encoded ints ÷10000). The app can tell the year from the script src (`/precincts2016/`), the same way it detects `/precincts2020/` (index.html `is20`). | per state, on demand, like `loadPrec20(st)` |
| `v2/data/precincts2016-DC.js` | 20,151 | same `__prec("District of Columbia",...)`, like `v2/data/precincts2020-DC.js` | DC |

District values: a 4th element `1` means ≈ (area-weighted). A missing key means gray (no 2016 data). Keys match the current v2 rows exactly (0 orphans, 0 misses). There are no 2016 values in uscd/ussldu/ussldl/ussch (decision: lazy-load, don't append). Towns/places/parts: no file; v2 derives them from the precinct file.

Note on paths: v2 keeps 2020/2024 precincts and county tables in the root `data/` (`../data/precincts2020/`, `../data/election2020.js`). 2016 lives in `v2/data/` by orchestrator decision, so loaders use `data/precincts2016/...` relative to v2.

Precinct files: 0.0004° (~40 m) simplification, raised per state until each file is ≤ the smaller of its 2020/2024 equivalents (total 44.4 MB vs 49.6 MB cap). NJ, CT, RI are dissolved to towns (exact sums), like their 2020 files.

Build tools (`tools/`): `build_vest2016.py` (precincts), `build_layers2016.py` (counties, states, districts; wrote `out/ds2016.js`, which was then split into the `ds2016-*.js` files above), `append2016.py` (not used: shared files stay unchanged).

## Layer coverage
| Layer | Districts | Filled | ≈ (area-weighted) | Gray |
|---|---|---|---|---|
| ushouse | 435 | 434 | 404 | 1 |
| senate | 1,942 | 1,935 | 1,832 | 7 |
| statehouse | 4,882 | 4,860 | 4,611 | 22 |
| schools | 13,304 | 13,239 | 12,142 | 65 |
| states | 51 | 51 | 0 | 0 |
| counties | 3,144 | 3,144 | 0 | 0 |

≈ is common because 2016 precincts are weighted into 2024 district lines, so most districts contain at least one split precinct.

Gray items (reason):
- **ushouse**: Florida 20 (precinct cover 32%)
- **senate**: Florida 026 (precinct cover 49%); Florida 035 (precinct cover 16%); Hawaii 018 (precinct cover 40%); Maine 001 (precinct cover 42%); Maine 004 (precinct cover 42%); Nevada 021 (precinct cover 39%); Utah 006 (precinct cover 15%)
- **statehouse**: Florida 094 (precinct cover 41%); Florida 096 (precinct cover 4%); Georgia 164 (precinct cover 49%); Hawaii 037 (precinct cover 26%); Hawaii 039 (precinct cover 36%); Louisiana 057 (precinct cover 43%); Louisiana 094 (precinct cover 10%); Louisiana 100 (precinct cover 46%); Louisiana 089 (precinct cover 21%); Maine 072 (precinct cover 37%); Maine 030 (precinct cover 33%); Maine 001 (precinct cover 26%); Montana 015 (precinct cover 48%); Nevada 012 (precinct cover 31%); New Hampshire 306 (precinct cover 37%); New York 059 (precinct cover 44%); New York 085 (precinct cover 50%); New York 007 (precinct cover 43%); Utah 027 (precinct cover 47%); Utah 061 (precinct cover 17%); Utah 015 (precinct cover 12%); Utah 003 (precinct cover 10%)
- **schools**: Alaska Kashunamiut School District (no votes); Alaska Hydaburg City School District (no votes); Alaska Klawock City School District (no votes); Alaska Pelican City School District (no votes); Alaska Tanana City School District (no votes); Arizona Yuma Elementary District (precinct cover 20%); Arizona Yuma Union High School District (precinct cover 26%); California Sierra Sands Unified School District (precinct cover 37%); California Borrego Springs Unified School District (precinct cover 35%); California Silver Valley Unified School District (precinct cover 34%); California Coachella Valley Unified School District (precinct cover 41%); California Fillmore Unified School District (precinct cover 33%); California Oak Park Unified School District (precinct cover 27%); California Morongo Unified School District (precinct cover 42%); California Rim of the World Unified School District (precinct cover 46%); California Lake Tahoe Unified School District (precinct cover 39%); California Desert Sands Unified School District (precinct cover 23%); California Three Rivers Union Elementary School District (precinct cover 45%); California Silver Fork Elementary School District (precinct cover 45%); California Camino Union Elementary School District (precinct cover 23%); California Springville Union Elementary School District (precinct cover 33%); California Buttonwillow Union Elementary School District (precinct cover 47%); California Blochman Union Elementary School District (precinct cover 19%); California Los Olivos Elementary School District (precinct cover 15%); California Cucamonga Elementary School District (precinct cover 49%); California Hydesville Elementary School District (precinct cover 41%); California Oakley Union Elementary School District (precinct cover 40%); California Mupu Elementary School District (precinct cover 25%); California Allensworth Elementary School District (precinct cover 27%); California Woodlake Unified School District (9-12) (precinct cover 45%); Florida Broward County School District (precinct cover 34%); Georgia Fort Benning Schools (precinct cover 32%); Georgia Chattahoochee County for Fort Benning (precinct cover 41%); Georgia Muscogee County for Fort Benning (precinct cover 8%); Kentucky Fort Campbell Dependent Schools (precinct cover 38%); Maine School Administrative District 65 (no votes); Maine Aroostook Unorganized Territory (precinct cover 20%); Maine Franklin Unorganized Territory (precinct cover 31%); Maine Sagadahoc Unorganized Territory (precinct cover 4%); Maine Knox Unorganized Territory (no votes); Maine Somerset Unorganized Territory (precinct cover 31%); Maine Piscataquis Unorganized Territory (precinct cover 23%); Maine Penobscot Unorganized Territory (precinct cover 49%); Maine Hancock Unorganized Territory (precinct cover 48%); Montana Columbia Falls Elementary School District (precinct cover 46%); Nevada Storey County School District (precinct cover 49%); New Jersey Edgewater Borough School District (precinct cover 42%); New York Seaford Union Free School District (precinct cover 42%); New York Massapequa Union Free School District (precinct cover 47%); New York Mattituck-Cutchogue Union Free School District (precinct cover 46%); New York Babylon Union Free School District (precinct cover 37%); New York Fire Island Union Free School District (precinct cover 16%); New York Islip Union Free School District (precinct cover 49%); New York Oceanside Union Free School District (precinct cover 43%); New York Bellmore Union Free School District (precinct cover 44%); New York Merrick Union Free School District (precinct cover 38%); Texas Boys Ranch Independent School District (no votes); Utah Davis School District (precinct cover 42%); Utah Emery School District (precinct cover 35%); Vermont Averys Gore School District (precinct cover 2%); Vermont Lewis School District (precinct cover 1%); Vermont Warners Grant School District (precinct cover 1%); Washington Mercer Island School District (precinct cover 46%); Washington Ocosta School District (precinct cover 46%); Washington Richland School District (precinct cover 22%)

## Statewide totals: precinct-file sums vs FEC 2016
Clinton/Trump match FEC exactly in 47 states + DC. AL, CA, PA, SD are within 0.03%. The total column differs where VEST and FEC count write-ins differently (e.g. CA -0.87%, AZ +1.22%, FL +0.82%).

| State | File | Bytes (2016) | Cap (min 2020/2024) | Precincts | Clinton Δ vs FEC | Trump Δ vs FEC | Total Δ vs FEC |
|---|---|---|---|---|---|---|---|
| Alabama | Alabama.js | 1,078,066 | 1,301,829 | 1,999 | +60 (+0.01%) | +374 (+0.03%) | +452 (+0.02%) |
| Alaska | Alaska.js | 1,205,347 | 1,497,787 | 441 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Arizona | Arizona.js | 618,769 | 646,001 | 1,464 | +0 (+0.00%) | +0 (+0.00%) | +31,492 (+1.22%) |
| Arkansas | Arkansas.js | 907,928 | 993,455 | 2,486 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| California | California.js | 3,342,449 | 3,640,851 | 21,416 | -1,726 (-0.02%) | -513 (-0.01%) | -123,241 (-0.87%) |
| Colorado | Colorado.js | 942,671 | 959,265 | 2,989 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Connecticut | Connecticut.js | 58,232 | 80,468 | 169 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Delaware | Delaware.js | 99,335 | 113,643 | 428 | +0 (+0.00%) | +0 (+0.00%) | -2,224 (-0.50%) |
| District of Columbia | District_of_Columbia.js | 20,151 | 29,181 | 143 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Florida | Florida.js | 1,493,133 | 1,676,993 | 5,887 | +0 (+0.00%) | +0 (+0.00%) | +77,378 (+0.82%) |
| Georgia | Georgia.js | 1,348,184 | 1,656,561 | 2,674 | +0 (+0.00%) | +0 (+0.00%) | -22,359 (-0.54%) |
| Hawaii | Hawaii.js | 138,051 | 138,827 | 247 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Idaho | Idaho.js | 551,780 | 564,219 | 925 | +0 (+0.00%) | +0 (+0.00%) | +178 (+0.03%) |
| Illinois | Illinois.js | 1,515,847 | 1,618,074 | 10,088 | +0 (+0.00%) | +0 (+0.00%) | +53,501 (+0.97%) |
| Indiana | Indiana.js | 964,603 | 983,255 | 5,317 | +29 (+0.00%) | -46 (-0.00%) | +25,570 (+0.93%) |
| Iowa | Iowa.js | 345,775 | 373,831 | 1,680 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Kansas | Kansas.js | 622,682 | 626,664 | 3,384 | +0 (+0.00%) | +0 (+0.00%) | +9,283 (+0.78%) |
| Kentucky | Kentucky.js | 609,752 | 646,222 | 3,675 | -7 (-0.00%) | -14 (-0.00%) | -774 (-0.04%) |
| Louisiana | Louisiana.js | 1,062,553 | 1,223,369 | 3,679 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Maine | Maine.js | 165,103 | 185,580 | 577 | +0 (+0.00%) | +0 (+0.00%) | +8 (+0.00%) |
| Maryland | Maryland.js | 636,653 | 715,653 | 1,987 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Massachusetts | Massachusetts.js | 491,835 | 559,481 | 2,174 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Michigan | Michigan.js | 948,052 | 999,406 | 4,811 | -1 (-0.00%) | -2 (-0.00%) | -8,958 (-0.19%) |
| Minnesota | Minnesota.js | 825,132 | 899,216 | 4,089 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Mississippi | Mississippi.js | 804,316 | 828,359 | 1,797 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Missouri | Missouri.js | 898,975 | 940,746 | 3,061 | +0 (+0.00%) | +0 (+0.00%) | -7,156 (-0.25%) |
| Montana | Montana.js | 485,896 | 649,031 | 686 | +0 (+0.00%) | +0 (+0.00%) | -2,621 (-0.53%) |
| Nebraska | Nebraska.js | 272,709 | 296,313 | 1,373 | +0 (+0.00%) | +0 (+0.00%) | -16,051 (-1.90%) |
| Nevada | Nevada.js | 386,844 | 400,292 | 1,756 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| New Hampshire | New_Hampshire.js | 87,167 | 87,194 | 302 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| New Jersey | New_Jersey.js | 238,285 | 257,803 | 578 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| New Mexico | New_Mexico.js | 744,286 | 1,078,801 | 1,490 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| New York | New_York.js | 2,312,760 | 2,367,910 | 14,661 | +13 (+0.00%) | +19 (+0.00%) | -872 (-0.01%) |
| North Carolina | North_Carolina.js | 1,273,183 | 1,467,174 | 2,704 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| North Dakota | North_Dakota.js | 131,832 | 152,978 | 432 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Ohio | Ohio.js | 1,886,991 | 2,081,859 | 8,887 | +0 (+0.00%) | +0 (+0.00%) | -16,314 (-0.30%) |
| Oklahoma | Oklahoma.js | 667,547 | 867,638 | 1,938 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Oregon | Oregon.js | 681,319 | 686,780 | 1,336 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Pennsylvania | Pennsylvania.js | 1,862,771 | 2,219,789 | 9,163 | -285 (-0.01%) | +570 (+0.02%) | -49,787 (-0.81%) |
| Rhode Island | Rhode_Island.js | 16,766 | 23,601 | 39 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| South Carolina | South_Carolina.js | 899,334 | 1,092,654 | 2,232 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| South Dakota | South_Dakota.js | 199,673 | 225,720 | 747 | +8 (+0.01%) | +10 (+0.00%) | +18 (+0.00%) |
| Tennessee | Tennessee.js | 1,252,593 | 1,295,531 | 1,983 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Texas | Texas.js | 3,185,671 | 3,985,406 | 8,589 | -3 (-0.00%) | -191 (-0.00%) | +14,182 (+0.16%) |
| Utah | Utah.js | 625,464 | 635,158 | 2,195 | +0 (+0.00%) | +0 (+0.00%) | -55 (-0.00%) |
| Vermont | Vermont.js | 65,455 | 68,418 | 275 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Virginia | Virginia.js | 1,190,935 | 1,198,074 | 2,454 | +0 (+0.00%) | +0 (+0.00%) | -1,879 (-0.05%) |
| Washington | Washington.js | 1,479,257 | 1,631,104 | 7,079 | +0 (+0.00%) | +0 (+0.00%) | -107,805 (-3.25%) |
| West Virginia | West_Virginia.js | 932,599 | 1,049,324 | 1,721 | -2 (-0.00%) | +0 (+0.00%) | -1,374 (-0.19%) |
| Wisconsin | Wisconsin.js | 1,493,900 | 1,510,744 | 6,599 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| Wyoming | Wyoming.js | 310,917 | 340,184 | 482 | +0 (+0.00%) | +0 (+0.00%) | +0 (+0.00%) |
| **US** | 51 files | 44,379,528 | 49,568,416 | 167,288 | -1,914 (-0.00%) | +207 (+0.00%) | -149,408 (-0.11%) |

Earlier staging files (still valid): `us_president_2016_state_fec.csv` (normalized FEC rows), `../PA/pa_president_county_official_2016.csv`.
