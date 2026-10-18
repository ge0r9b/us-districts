# 2016 President: v2-format build (offline, not loaded by v2 yet)

Triples are [d, r, total] = [Clinton, Trump, all presidential candidates], the same as 2020/2024. ≈ is used **only** for area-weighted values. In the `ds2016-*.js` files it is a 4th element `1` (`[d,r,t,1]`); there is no separate flag field. A missing key/null means gray (no source).

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
| `v2/data/precincts2016/<State>.js` | 50 files, 7,836,659 total (was 44,359,377 with polygons) | `window.__prec16&&window.__prec16(state,[[county,precinct,d,r,t] or [county,precinct,d,r,t,1] or [county,precinct]],{credit})`. **No geometry.** One row per row of `v2/data/precincts2024/<State>.js`, same order, same `[county,precinct]` key. See "2016 precincts on 2024 polygons" below for the loader contract. | per state, on demand, after (or with) the 2024 precinct file of that state |
| `v2/data/precincts2016-DC.js` | 7,972 (was 20,151) | same `__prec16("District of Columbia",...)`, rows aligned with `v2/data/precincts2024-DC.js` | DC |

District values: a 4th element `1` means ≈ (area-weighted). A missing key means gray (no 2016 data). Keys match the current v2 rows exactly (0 orphans, 0 misses). There are no 2016 values in uscd/ussldu/ussldl/ussch (decision: lazy-load, don't append). Towns/places/parts: no file; v2 derives them from the precinct file.

Note on paths: v2 keeps 2020/2024 precincts and county tables in the root `data/` (`../data/precincts2020/`, `../data/election2020.js`). 2016 lives in `v2/data/` by orchestrator decision, so loaders use `data/precincts2016/...` relative to v2.

Precinct files: since this build no 2016 precinct polygons are stored anywhere (user rule: only current 2024 precinct polygons are kept; past years' votes are placed onto them). The old polygon files (44,379,528 bytes incl. DC) were overwritten in place by the value files.

Build tools (`tools/`): `build_vest2016.py` (reads the VEST zips, assigns precincts to v2 counties, writes the county table and the full-resolution geometry pickles in `/workspace/vest16/geom/<ab>.pkl` on the box; its old polygon-writing step is superseded and must not be used to write `v2/data/precincts2016/` again), `build_prec16_on24.py` (places the VEST votes onto the 2024 polygons and writes `v2/data/precincts2016/*.js` + a report JSON, committed as `prec16_on24_report.json`; usage `build_prec16_on24.py <repo> <vest_geom_dir> <report.json> [ab ...]`), `build_layers2016.py` (counties, states, districts; wrote `out/ds2016.js`, which was then split into the `ds2016-*.js` files above), `append2016.py` (**obsolete, unused**: it was written to append 2016 triples to the shared layer files, which the lazy-load decision replaced; it is not run and nothing ships from it).


## 2016 precincts on 2024 polygons (values only, no geometry)

**Format.** `v2/data/precincts2016/<State>.js` (file names as in `precincts2024/`, spaces → `_`) and `v2/data/precincts2016-DC.js`:

```
window.__prec16&&window.__prec16("<State>",[ROW,...],{"credit":"..."});
ROW = [county, precinct, d, r, t]      exact 2016 votes for this 2024 polygon
    | [county, precinct, d, r, t, 1]   ≈ (votes from a 2016 precinct that was split into, or merged with, this polygon)
    | [county, precinct]               gray: no 2016 votes placed on this polygon
```

d/r/t = Clinton / Trump / all presidential candidates (VEST 2016), integers.

**Loader contract.**
1. Row *i* of the 2016 file belongs to row *i* of `precincts2024/<State>.js` (or `precincts2024-DC.js`). The arrays have the same length and order, and `[county, precinct]` of each row is identical; verified for all 51 files at build time (173,276 rows, 0 mismatches). A loader can zip by index, or key by `county|precinct` for safety.
2. The geometry always comes from the 2024 file. The 2016 file only swaps the value triple: use `row16[2..4]` instead of the 2024 votes, show ≈ when `row16[5]===1`, and show gray when the row has length 2.
3. The global is `window.__prec16(state, rows, meta)`, a separate name from `__prec`, so the 2016 file cannot overwrite the cached 2024 polygons. DC is `precincts2016-DC.js` (the 2024 stub `precincts2024/District_of_Columbia.js` is empty and has no 2016 counterpart).
4. Towns, places and parts in 2016 are derived from these rows the same way as from the 2024 rows (sum by polygon).

**How votes are placed** (`tools/build_prec16_on24.py`, full-resolution VEST geometry in EPSG:5070 vs the decoded 2024 polygons):
- **Name match:** if a VEST precinct has the same normalized name as a 2024 polygon in the same county, and at least 50% of its area lies in that polygon, it goes wholly to it.
- **Otherwise area-weighted:** share = overlap ÷ min(total overlap with 2024 polygons, own area). Shares below 3% count as 0 and above 97% as 1; the rest is renormalized. If less than half of a precinct is covered by 2024 polygons, its own area is the denominator and the uncovered part stays **unplaced**.
- **Exact vs ≈:** a 2024 polygon is exact when exactly one 2016 precinct contributes with share 1 (whole, unsplit precinct, matched by name or by area) and that precinct goes to no other polygon. It is ≈ when any contributing precinct was split, or several 2016 precincts were merged into it. Allocated values are rounded to integers.
- **Unplaced votes:** these come from VEST precincts in areas without a 2024 polygon. Example: South Dakota has no 2024 precincts for Brown, Brookings, Lawrence, Yankton, Hughes, Potter, Haakon and Sully counties (61,676 votes). These votes are still in `election2016.js` and in the `ds2016-*` district values, but they appear on no precinct.

**Totals:** 51 files, 173,276 rows: 88,703 exact, 73,738 ≈, 10,835 gray. 52.2% of VEST votes sit on exact rows. Placed: D 65,275,114 / R 62,281,408 / T 135,162,569 of VEST D 65,851,600 / R 62,985,035 / T 136,519,868 (99.01% of all votes).

**Size:** 44,379,528 bytes before (51 polygon files) → 7,844,631 bytes after (−82.3%).

| State | VEST precincts | 2024 rows | Exact | ≈ | Gray | Votes on exact rows | Votes placed (T) | Bytes before | Bytes after |
|---|---|---|---|---|---|---|---|---|---|
| Alabama | 1,999 | 1,911 | 1,501 | 406 | 4 | 68.5% | 2,060,810 of 2,123,824 (97.03%) | 1,078,066 | 102,398 |
| Alaska | 441 | 402 | 184 | 216 | 2 | 33.9% | 318,611 of 318,608 (100.00%) | 1,205,347 | 22,720 |
| Arizona | 1,464 | 1,694 | 1,031 | 638 | 25 | 63.0% | 2,604,652 of 2,604,657 (100.00%) | 618,769 | 70,954 |
| Arkansas | 2,486 | 2,649 | 1,656 | 839 | 154 | 61.1% | 1,118,713 of 1,130,676 (98.94%) | 907,928 | 114,267 |
| California | 21,416 | 24,202 | 2,414 | 17,062 | 4,726 | 9.5% | 14,031,848 of 14,058,363 (99.81%) | 3,342,449 | 988,794 |
| Colorado | 2,989 | 3,144 | 1,454 | 1,669 | 21 | 43.4% | 2,759,634 of 2,780,247 (99.26%) | 942,671 | 141,567 |
| Connecticut | 169 | 167 | 161 | 6 | 0 | 90.2% | 1,530,672 of 1,644,920 (93.05%) | 58,232 | 12,055 |
| Delaware | 428 | 525 | 173 | 348 | 4 | 38.6% | 441,183 of 441,590 (99.91%) | 99,335 | 22,102 |
| District of Columbia | 143 | 144 | 138 | 6 | 0 | 94.6% | 311,268 of 311,268 (100.00%) | 20,151 | 7,972 |
| Florida | 5,887 | 5,546 | 3,013 | 2,283 | 250 | 54.1% | 9,239,577 of 9,497,417 (97.29%) | 1,493,133 | 222,238 |
| Georgia | 2,674 | 2,636 | 1,581 | 1,013 | 42 | 59.9% | 4,047,702 of 4,092,373 (98.91%) | 1,348,184 | 108,276 |
| Hawaii | 247 | 233 | 30 | 196 | 7 | 10.9% | 422,336 of 428,937 (98.46%) | 138,051 | 10,039 |
| Idaho | 925 | 972 | 323 | 647 | 2 | 28.4% | 690,004 of 690,433 (99.94%) | 551,780 | 37,934 |
| Illinois | 10,088 | 8,498 | 4,455 | 4,004 | 39 | 45.2% | 5,568,563 of 5,589,925 (99.62%) | 1,515,847 | 364,290 |
| Indiana | 5,317 | 5,053 | 4,102 | 936 | 15 | 78.2% | 2,747,143 of 2,760,528 (99.52%) | 964,603 | 215,593 |
| Iowa | 1,680 | 1,650 | 707 | 932 | 11 | 37.8% | 1,563,136 of 1,566,031 (99.82%) | 345,775 | 80,675 |
| Kansas | 3,384 | 3,665 | 2,791 | 729 | 145 | 75.8% | 1,184,060 of 1,193,685 (99.19%) | 622,682 | 159,788 |
| Kentucky | 3,675 | 3,200 | 1,380 | 1,808 | 12 | 38.9% | 1,875,078 of 1,923,375 (97.49%) | 609,752 | 126,172 |
| Louisiana | 3,679 | 3,632 | 2,763 | 740 | 129 | 78.9% | 2,020,061 of 2,029,032 (99.56%) | 1,062,553 | 149,715 |
| Maine | 577 | 490 | 439 | 51 | 0 | 78.0% | 741,954 of 747,935 (99.20%) | 165,103 | 22,614 |
| Maryland | 1,987 | 1,951 | 1,007 | 923 | 21 | 53.9% | 2,764,098 of 2,781,446 (99.38%) | 636,653 | 91,032 |
| Massachusetts | 2,174 | 2,337 | 935 | 1,374 | 28 | 42.6% | 3,262,040 of 3,325,046 (98.11%) | 491,835 | 134,783 |
| Michigan | 4,811 | 3,975 | 2,602 | 1,373 | 0 | 56.2% | 4,744,729 of 4,790,326 (99.05%) | 948,052 | 250,317 |
| Minnesota | 4,089 | 4,067 | 2,947 | 1,097 | 23 | 53.5% | 2,937,555 of 2,944,813 (99.75%) | 825,132 | 190,822 |
| Mississippi | 1,797 | 1,703 | 1,408 | 286 | 9 | 77.6% | 1,186,441 of 1,209,357 (98.11%) | 804,316 | 78,997 |
| Missouri | 3,061 | 3,021 | 1,319 | 1,642 | 60 | 44.8% | 2,751,171 of 2,801,449 (98.21%) | 898,975 | 139,256 |
| Montana | 686 | 720 | 326 | 386 | 8 | 29.5% | 491,693 of 494,526 (99.43%) | 485,896 | 32,487 |
| Nebraska | 1,373 | 1,326 | 575 | 742 | 9 | 37.2% | 827,329 of 828,176 (99.90%) | 272,709 | 61,402 |
| Nevada | 1,756 | 1,236 | 568 | 633 | 35 | 33.7% | 1,119,375 of 1,125,385 (99.47%) | 386,844 | 46,233 |
| New Hampshire | 302 | 238 | 226 | 12 | 0 | 72.6% | 744,290 of 744,296 (100.00%) | 87,167 | 12,038 |
| New Jersey | 578 | 6,378 | 78 | 3,412 | 2,888 | 1.2% | 3,870,353 of 3,874,046 (99.90%) | 238,285 | 373,941 |
| New Mexico | 1,490 | 2,164 | 1,201 | 651 | 312 | 68.4% | 797,538 of 798,319 (99.90%) | 744,286 | 85,569 |
| New York | 14,661 | 12,902 | 4,932 | 7,901 | 69 | 35.5% | 7,678,399 of 7,720,570 (99.45%) | 2,312,760 | 589,148 |
| North Carolina | 2,704 | 2,643 | 2,378 | 265 | 0 | 88.3% | 4,726,483 of 4,741,564 (99.68%) | 1,273,183 | 118,016 |
| North Dakota | 432 | 379 | 111 | 250 | 18 | 17.3% | 344,074 of 344,360 (99.92%) | 131,832 | 14,997 |
| Ohio | 8,887 | 8,786 | 7,493 | 1,220 | 73 | 84.4% | 5,410,058 of 5,480,173 (98.72%) | 1,886,991 | 434,484 |
| Oklahoma | 1,938 | 1,980 | 673 | 1,294 | 13 | 32.0% | 1,452,981 of 1,452,992 (100.00%) | 667,547 | 81,615 |
| Oregon | 1,336 | 1,244 | 724 | 478 | 42 | 38.5% | 1,930,479 of 2,001,336 (96.46%) | 681,319 | 49,566 |
| Pennsylvania | 9,163 | 9,100 | 7,066 | 2,030 | 4 | 77.2% | 6,077,499 of 6,115,691 (99.38%) | 1,862,771 | 442,361 |
| Rhode Island | 39 | 39 | 39 | 0 | 0 | 100.0% | 464,144 of 464,144 (100.00%) | 16,766 | 2,482 |
| South Carolina | 2,232 | 2,302 | 2,122 | 150 | 30 | 94.8% | 2,096,431 of 2,103,027 (99.69%) | 899,334 | 108,435 |
| South Dakota | 747 | 623 | 325 | 286 | 12 | 39.3% | 302,173 of 370,111 (81.64%) | 199,673 | 25,389 |
| Tennessee | 1,983 | 1,845 | 890 | 938 | 17 | 39.1% | 2,494,806 of 2,508,027 (99.47%) | 1,252,593 | 88,228 |
| Texas | 8,589 | 9,712 | 6,951 | 1,886 | 875 | 76.0% | 8,983,401 of 8,983,408 (100.00%) | 3,185,671 | 359,355 |
| Utah | 2,195 | 2,670 | 383 | 2,206 | 81 | 13.6% | 1,106,823 of 1,131,375 (97.83%) | 625,464 | 106,713 |
| Vermont | 275 | 247 | 222 | 25 | 0 | 68.0% | 313,617 of 315,067 (99.54%) | 65,455 | 12,229 |
| Virginia | 2,454 | 2,518 | 1,368 | 1,141 | 9 | 54.1% | 3,907,494 of 3,982,752 (98.11%) | 1,190,935 | 133,600 |
| Washington | 7,079 | 7,912 | 5,734 | 1,705 | 473 | 78.3% | 3,186,628 of 3,209,214 (99.30%) | 1,479,257 | 323,681 |
| West Virginia | 1,721 | 1,611 | 952 | 602 | 57 | 56.5% | 696,812 of 713,049 (97.72%) | 932,599 | 57,483 |
| Wisconsin | 6,599 | 6,819 | 2,571 | 4,173 | 75 | 34.2% | 2,973,750 of 2,976,150 (99.92%) | 1,493,900 | 401,277 |
| Wyoming | 482 | 415 | 281 | 128 | 6 | 53.0% | 242,900 of 255,849 (94.94%) | 310,917 | 18,532 |
| **US** | 167,288 | 173,276 | 88,703 | 73,738 | 10,835 | 52.2% | 135,162,569 of 136,519,868 (99.01%) | 44,379,528 | 7,844,631 |

## Size of historic district values (2016 vs 2020)

| Layer | 2016 values: own file (bytes) | 2020 values inside the shared layer file (bytes of the `[d,r,t]` element, incl. comma) | 2024 values, same file | Shared layer file total (geometry bytes) |
|---|---|---|---|---|
| states | `ds2016-states.js` 1,892 | n/a (from `election2020.js`) | n/a | n/a |
| US House | `ds2016-cd.js` 16,878 | 9,900 in `uscd.js` (435 rows) | 9,902 | 614,849 (586,163) |
| state senate | `ds2016-sldu.js` 71,940 | 38,621 in `ussldu.js` (1,942 rows) | 38,696 | 1,256,870 (1,136,122) |
| state house | `ds2016-sldl.js` 175,869 | 91,655 in `ussldl.js` (4,882 rows) | 91,839 | 2,062,537 (1,770,022) |
| schools | `ds2016-sch.js` 822,361 | 218,139 in `ussch.js` (13,304 rows) | 219,348 | 4,750,426 (3,629,752) |
| **total** | 1,088,940 | 358,315 | 359,785 | 8,684,682 |

The 2020 and 2024 district values sit inline in each layer row (`[state, name, geometry, [d,r,t]2020, [d,r,t]2024, flag]`) and carry no geometry of their own. The 2016 files have no geometry either; they are larger because their keys (`"State|district"`) are repeated in each file, while the 2020 values reuse the row the layer file already has (and schools keys are long names). There are no historic district polygons to remove.

For comparison, the 2020 precinct side has two parts. `v2/data/x20/<State>.js` holds 2020 votes on the 2024 polygons, keyed by `"county|precinct"` (50 files, 7,052,987 bytes, no geometry). `v2/data/precincts2020/` (49,976,587 bytes, plus `precincts2020-DC.js` 29,181) still stores the 2020 precinct **polygons**. Under the same rule those are historic boundaries too; this lane has not touched them.

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

## Statewide totals: VEST 2016 precinct sums vs FEC 2016 (before placement onto 2024 polygons)
Clinton/Trump match FEC exactly in 47 states + DC. AL, CA, PA, SD are within 0.03%. The total column differs where VEST and FEC count write-ins differently (e.g. CA -0.87%, AZ +1.22%, FL +0.82%). These are the sums of the full VEST data, which also feed `election2016.js`. The "Bytes (2016)" column is the size of the old polygon files, which are gone; for what the value files place, see the next section.

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

**boundary_set (Q-E12).** These two CSVs are the only 13-column rows for 2016 presidential. Both now have `boundary_set` as column 14, right after `retrieved_at` (no `method` column), set to `v2-2024` on every row: 153 FEC state rows and 335 PA county rows. The state rows use `v2-2024` for consistency, although a state's outline does not depend on a boundary vintage. Both files keep their CRLF line endings. The 2016 **district** values exist only in JS (`v2/data/ds2016-cd.js`, `-sldu`, `-sldl`, `-sch`, plus `ds2016-states.js`) and have no boundary_set field. They are area-weighted into v2's current district shapes, so they are on **v2-2024** too. The 2016 precinct files (`v2/data/precincts2016/`) now carry values keyed to v2's 2024 precinct polygons, so they are on **v2-2024** as well; they have no CSV rows and no boundary_set field. Format going forward: lowercase with hyphens (e.g. `v2-2024`, `tiger-2020`, `v2-2016-precincts`).
