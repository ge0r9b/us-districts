# 2022 US Senate results (data-v3)

All 35 Senate races of Nov 8, 2022 in 34 states: the 34 regular (Class III) races plus the two specials held the same day, **California** (unexpired term, Padilla v. Meuser) and **Oklahoma** (unexpired term, Mullin v. Kendra Horn; regular race Lankford v. Madison Horn). **Georgia** also has the Dec 6 runoff (Warnock v. Walker) as `us_senate_runoff`. States without a 2022 Senate race have **no rows** (gray). Built with the same tools, columns and rules as `data-v3/results/2024/senate/`.

**Polygons: v2 has no 2022 precinct polygons, so the 2022 precinct values sit on v2's 2024 precinct polygons** (`v2/data/precincts2024/<State>.js`). 2022 precincts are bridged to them (below); where 2022 and 2024 precinct lines differ, votes are allocated and the district values are ≈. Nothing in `v2/data/`, root `data/`, `v2/index.html` or `BUILD` was touched.

## Files
All files use the 13 bot columns plus the optional 14th `method`. `.gz` = gzip of the same CSV.

| File | Rows | unit_type | Source / method |
|---|---|---|---|
| `us_senate_2022_state.csv` | 188 | `state` (state FIPS) | Clerk of the House, *Statistics of the Congressional Election of Nov 8, 2022* (official). Every candidate; fusion lines merged into their candidate (CT Blumenthal D+WF; NY Schumer D+WF, Pinion R+CON). GA regular = the Nov 8 general from the Clerk footnote (the Clerk table lists the runoff). `method=official` |
| `us_senate_2022_county.csv` | 6,699 | `county` (5-digit FIPS; CT = planning regions) | MEDSL 2022 precinct returns summed by v2 county; **CA**: Statewide Database 2022 SOV; **ID**: Idaho Secretary of State 2022 canvass (precinct); **IN**: Indiana Election Division final results (precinct in 35 counties, county total in 57). `method=retabulated` |
| `precincts/<ST>.csv.gz` (34 files) | 300,408 | `precinct` | MEDSL 2022 (CA SWDB, ID SOS, IN IED) precinct rows bridged 1:1 (or as a whole town) to a v2 2024 polygon. `method=official` |
| `us_senate_2022_ushouse.csv` | 1,142 | `ushouse` | polygons area-weighted into v2 districts. `method=retabulated` (exact) or `area_weighted` (= ≈) |
| `us_senate_2022_sldu.csv` | 4,302 | `sldu` | same |
| `us_senate_2022_sldl.csv` | 10,774 | `sldl` | same |
| `us_senate_2022_school.csv.gz` | 30,560 | `school_unified` / `school_elementary` / `school_secondary` | same |
| `statewide_vs_official.csv` | 37 | audit | precinct-source statewide sums (columns named `medsl_*` for all states) vs Clerk official |
| `precinct_match.csv` | 37 | audit | bridge rate per race |
| `GAPS.csv` | 1,520 | audit | unbridged votes by county, gray districts |
| `tools/` | | | `races22.py` (race config, d slots), `ca22_from_swdb.py` (CA SOV → MEDSL-format rows), `id22_from_sos.py` (Idaho SOS canvass → MEDSL-format rows), `in22_from_ied.py` (Indiana Election Division results → MEDSL-format rows), `build_sen2022.py` (MEDSL 2022 → v2 2024 polygons), `layers_sen2022.py` (districts), `write_csv_sen2022.py` (CSVs). `races.py` (USPS/NAME) is imported from `../../2024/senate/tools/`. |

Row conventions are as in 2024: `office` = `us_senate` / `us_senate_special` / `us_senate_runoff`, `district=statewide`; below the state level 3 rows per unit (d slot, r slot, `all-others`), total = d + r + all-others; `candidate_id` = surname-first slug of the Clerk name; precinct `unit_id` = `<ST>|<v2 county>|<v2 precinct name>` (+ `|#<row>` where the pair repeats) of the **v2 2024** precinct file; `weight` = 1; `retrieved_at` = download time (UTC).

## d-slot rule and flagged races
**d = the Democratic nominee, unless an independent (non-Republican) candidate outpolled the Democratic nominee statewide, or there was no Democratic nominee; then d = that independent. r = the Republican nominee.** Fixed per race, so d is the same candidate in every unit of a state. Rules for the 2022 special cases:

| Race | d slot | r slot | Note |
|---|---|---|---|
| UT regular | **Evan McMullin** (independent) 459,958 | Mike Lee 571,974 | **No Democratic nominee** (Utah Democrats endorsed McMullin), so d = McMullin. |
| AK regular | Patricia Chesbro (D) 27,145 | **Lisa Murkowski (R)** 113,495 | **Ranked-choice, two Republicans in the final round** (Murkowski v. Tshibaka). Rule: all values are **first-round** votes (the only round reported by precinct). d = the Democratic nominee; r = the Republican with the most first-round votes statewide (Murkowski). Kelly Tshibaka (R, 111,480) and Buzz Kelley (R) are in all-others, so all-others is large in Alaska. |
| LA regular | Gary Chambers Jr. (D, top Democrat) 246,933 | John Kennedy (R) 851,568 | Jungle primary on Nov 8 (Kennedy won outright). d = the Democrat with the most votes; Mixon, Steib and the other Democrats are in all-others. |
| GA regular / runoff | Raphael Warnock (D) | Herschel Walker (R) | Nov 8 general (no majority, Oliver 81,365 in all-others) and the Dec 6 runoff, as two races. |
| ND regular | Katrina Christiansen (Democratic-NPL) | John Hoeven | Dem-NPL counts as the Democratic nominee. Rick Becker (Independent, 44,406) is below Christiansen (59,995), so he stays in all-others. |
| CA regular / special | Alex Padilla (D) | Mark Meuser (R) | top-two general; normal |
| OK regular / special | Madison Horn (D) / Kendra Horn (D) | James Lankford / Markwayne Mullin | normal |

## How it was built
1. **MEDSL rows** (same rule as 2024): per (office, county, jurisdiction, precinct), only `mode=TOTAL` rows when present, else all modes summed; `*` = 0; under/over votes, blanks, "none of these", and MEDSL 2022 bookkeeping lines (ballots cast, registered voters, public counter, etc.) are not votes. Candidates go to d / r / other by name.
2. **California**: MEDSL 2022 has no CA Senate rows, so CA uses the Statewide Database 2022 Statement-of-Vote precinct file (`state_g22_sov_data_by_g22_srprec`: USSDEM01/USSREP01 = full term, USPDEM01/USPREP01 = unexpired term), converted to MEDSL-format rows by `ca22_from_swdb.py`. It matches the Clerk to within 9 votes.
2b. **Idaho**: MEDSL's ID 2022 Senate rows sum to about 2× the official total, so ID uses the Idaho Secretary of State's 2022 general canvass (`22 General Statewide - Precinct.xlsx`, sheet `US Sen`; 999 precincts in 44 counties; county header, `CO. TOTAL` and `GRAND TOTAL` rows skipped), converted by `id22_from_sos.py`. It sums exactly to the Clerk (590,890). The SOS sheet has no write-in column, and the Clerk lists no ID write-ins.
2c. **Indiana**: MEDSL's IN 2022 file has only 39 of 92 counties. IN uses the Indiana Election Division's final 2022 results (`AllOfficeResults.csv`, US Senator), converted by `in22_from_ied.py`. Only 35 counties report by precinct; the other 57 report a county total (Cass, Daviess, Monroe and Scott list precincts, but all at 0, plus a county total, which is used). Each county total is one `COUNTY TOTAL` row that is never bridged, so step 5 allocates it over the county's 2024 polygons by 2024 president votes. Those counties have county rows (exact) and ≈ district values, but no precinct rows. Verbatim repeats of a few write-in lines (all 0) are dropped. It sums exactly to the Clerk (1,859,851). No OpenElections IN or ID 2022 files exist.
3. **2024 polygons**: MEDSL 2024 returns are matched to the v2 2024 polygons by the president result, exactly as in 2024/senate (`build_sen2024.py` passes).
4. **Bridge 2022 → 2024 polygon**: each MEDSL 2022 precinct is bridged by (a) an identical MEDSL key (county FIPS, jurisdiction, precinct) in the matched 2024 MEDSL file; (b) the same county + a normalized name variant of a matched 2024 MEDSL precinct (leading numbers / `10_` prefixes, punctuation, "PRECINCT"/"PCT", etc.); (c) the same county + a name variant of a v2 polygon (statewide for AK, whose MEDSL rows have no county); (d) town groups (CT, VT). Bridged polygons get the exact 2022 MEDSL values and are written to `precincts/`.
5. **Unbridged votes** (county absentee/provisional buckets, and precincts whose 2022 name or lines differ from 2024) are allocated to the county's unbridged polygons by 2024 president d / r / total, or to all the county's polygons when the unbridged ones are too small to hold them (2024 president total < the residual). Votes with no usable county (AK House-district absentee/early/question rows) are spread over all polygons statewide the same way. Allocated votes appear only in districts and make them ≈; they are never precinct rows.
6. **Districts**: area-weighted into v2's `uscd` / `ussldu` / `ussldl` / `ussch`, with the same 3% / 97% sliver rule, the same ≈ rule (more than 2% of a district's total from split polygons or allocated votes) and the same gray rule (polygon cover < 50% or no votes). **One change from 2024**: a polygon's share of a district is its overlap with that district divided by min(its overlap with all districts of the layer, its own area), so polygon parts outside every simplified district shape (coastline, water) are not dropped. Without it Alaska lost ~11% of its votes. Polygons in counties with no 2022 Senate rows at all carry no shape, so districts there go gray instead of showing 0. After the ID/IN replacement no county is in that state.
7. **Counties** = MEDSL precinct sums per county (CT → planning regions via the bridged towns).

## Statewide check: MEDSL sums vs official (Clerk), D / R / total
| Race | Official | precinct source (MEDSL; CA SWDB; ID SOS; IN IED) − official |
|---|---|---|
| AK regular | 27,145 / 113,495 / 261,705 | +0 / +0 / +0 (+0.00%) |
| AL regular | 436,746 / 942,154 / 1,414,238 | +0 / +0 / +0 (+0.00%) |
| AR regular | 280,187 / 592,437 / 901,306 | -2,281 / -1,929 / -4,276 (-0.47%) |
| AZ regular | 1,322,027 / 1,196,308 / 2,572,294 | -133 / -24 / +2,086 (+0.08%) |
| CA regular | 6,621,621 / 4,222,029 / 10,843,650 | -5 / -4 / -9 (-0.00%) |
| CA special | 6,559,308 / 4,212,450 / 10,771,758 | -5 / -4 / -9 (-0.00%) |
| CO regular | 1,397,170 / 1,031,693 / 2,500,130 | +0 / +0 / +71 (+0.00%) |
| CT regular | 723,864 / 535,943 / 1,259,887 | -1 / +0 / -1 (-0.00%) |
| FL regular | 3,201,522 / 4,474,847 / 7,758,014 | +0 / -1 / +3,079 (+0.04%) |
| GA regular | 1,946,117 / 1,908,442 / 3,935,924 | +0 / +0 / +0 (+0.00%) |
| GA runoff | 1,820,633 / 1,721,244 / 3,541,877 | +0 / +0 / +0 (+0.00%) |
| HI regular | 290,894 / 106,358 / 408,517 | +0 / +0 / +0 (+0.00%) |
| IA regular | 533,330 / 681,501 / 1,216,646 | +0 / +0 / +0 (+0.00%) |
| ID regular | 169,808 / 358,539 / 590,890 | +0 / +0 / +0 (+0.00%) |
| IL regular | 2,329,136 / 1,701,055 / 4,098,896 | +0 / +0 / +1,391 (+0.03%) |
| IN regular | 704,411 / 1,090,165 / 1,859,851 | +0 / +0 / +0 (+0.00%) |
| KS regular | 372,214 / 602,976 / 1,004,956 | -3 / -5 / -8 (-0.00%) |
| KY regular | 564,311 / 913,326 / 1,477,830 | -80 / -69 / -208 (-0.01%) |
| LA regular | 246,933 / 851,568 / 1,383,290 | +0 / +0 / +0 (+0.00%) |
| MD regular | 1,316,897 / 682,293 / 2,002,336 | +0 / +0 / +0 (+0.00%) |
| MO regular | 872,694 / 1,146,966 / 2,069,130 | -348 / -742 / -1,122 (-0.05%) |
| NC regular | 1,784,049 / 1,905,786 / 3,773,924 | -174 / -183 / -369 (-0.01%) |
| ND regular | 59,995 / 135,474 / 240,140 | +0 / +0 / +0 (+0.00%) |
| NH regular | 332,193 / 275,928 / 620,975 | +0 / +0 / +0 (+0.00%) |
| NV regular | 498,316 / 490,388 / 1,008,409 | -128 / -229 / -367 (-0.04%) |
| NY regular | 3,320,561 / 2,501,151 / 5,852,707 | +2,022 / +4,795 / +13,337 (+0.23%) |
| OH regular | 1,939,489 / 2,192,114 / 4,133,342 | +0 / +0 / +0 (+0.00%) |
| OK regular | 369,370 / 739,960 / 1,150,732 | +0 / +0 / +0 (+0.00%) |
| OK special | 405,389 / 710,643 / 1,150,481 | +0 / +0 / +0 (+0.00%) |
| OR regular | 1,076,424 / 788,991 / 1,927,949 | +0 / -6 / -23 (-0.00%) |
| PA regular | 2,751,012 / 2,487,260 / 5,368,021 | -695 / -169 / -1,383 (-0.03%) |
| SC regular | 627,616 / 1,066,274 / 1,695,702 | +2,292 / +3,757 / +6,054 (+0.36%) |
| SD regular | 91,007 / 242,316 / 348,020 | +0 / +0 / +0 (+0.00%) |
| UT regular | 459,958 / 571,974 / 1,076,068 | -3 / -144 / +585 (+0.05%) |
| VT regular | 196,575 / 80,468 / 287,100 | +0 / +1 / -23 (-0.01%) |
| WA regular | 1,741,827 / 1,299,322 / 3,047,900 | -572 / -1,428 / -8,751 (-0.29%) |
| WI regular | 1,310,467 / 1,337,185 / 2,652,477 | +0 / +0 / +0 (+0.00%) |

Notes:
- **ID** and **IN**: now from official state sources (SOS / Election Division), exact to the Clerk. Before (MEDSL): ID 1,177,836 (≈2× official, cause not found) and IN 765,427 (39 of 92 counties).
- **NY** (+0.23%), **SC** (+0.36%), **WA** (−0.29%), **AR** (−0.47%): MEDSL vs certified, not reconciled. WA: MEDSL is short in some counties.
- All other races are within 0.1% on D and R, most exact. The state rows carry the official numbers.

## Coverage (bridge 2022 MEDSL → v2 2024 polygons)
| Race | source precincts bridged | v2 polygons with an exact value | Senate votes bridged |
|---|---|---|---|
| AK regular | 399 / 522 | 398 / 402 | 62.0% |
| AL regular | 1585 / 2074 | 1585 / 1911 | 76.9% |
| AR regular | 2056 / 2468 | 2040 / 2649 | 87.5% |
| AZ regular | 1527 / 1694 | 1527 / 1694 | 91.7% |
| CA regular | 16054 / 26191 | 16020 / 24202 | 67.7% |
| CA special | 16054 / 26191 | 16020 / 24202 | 67.7% |
| CO regular | 3092 / 3232 | 3092 / 3144 | 97.6% |
| CT regular | 690 / 708 | 167 / 167 | 98.1% |
| FL regular | 4396 / 6013 | 4057 / 5546 | 80.0% |
| GA regular | 2361 / 2722 | 2361 / 2636 | 87.7% |
| GA runoff | 2361 / 2711 | 2361 / 2636 | 87.7% |
| HI regular | 231 / 236 | 231 / 233 | 97.6% |
| IA regular | 1454 / 1653 | 1450 / 1650 | 90.1% |
| ID regular | 715 / 999 | 714 / 972 | 72.1% |
| IL regular | 6675 / 9459 | 6650 / 8498 | 78.0% |
| IN regular | 1851 / 2096 | 1847 / 5053 | 38.2% |
| KS regular | 3215 / 4523 | 3189 / 3665 | 88.5% |
| KY regular | 3062 / 3683 | 3062 / 3200 | 84.1% |
| LA regular | 1250 / 4039 | 1219 / 3632 | 21.4% |
| MD regular | 1936 / 2074 | 1936 / 1951 | 94.0% |
| MO regular | 500 / 3320 | 341 / 3021 | 17.7% |
| NC regular | 2221 / 2977 | 2221 / 2643 | 59.0% |
| ND regular | 361 / 398 | 361 / 379 | 96.3% |
| NH regular | 297 / 320 | 236 / 238 | 99.8% |
| NV regular | 1155 / 1691 | 1155 / 1236 | 92.8% |
| NY regular | 8771 / 13447 | 8771 / 12902 | 66.7% |
| OH regular | 8735 / 9021 | 8730 / 8786 | 97.8% |
| OK regular | 1975 / 1986 | 1974 / 1980 | 93.5% |
| OK special | 1975 / 1986 | 1974 / 1980 | 93.5% |
| OR regular | 1102 / 1277 | 1102 / 1244 | 89.8% |
| PA regular | 8656 / 9187 | 8624 / 9100 | 96.5% |
| SC regular | 2221 / 2395 | 2215 / 2302 | 97.6% |
| SD regular | 584 / 686 | 584 / 623 | 74.9% |
| UT regular | 2343 / 2846 | 2343 / 2670 | 95.9% |
| VT regular | 215 / 247 | 215 / 247 | 66.0% |
| WA regular | 7549 / 8021 | 7549 / 7912 | 96.4% |
| WI regular | 2087 / 3626 | 2086 / 6819 | 39.3% |

District layers: regular / special / GA runoff filled = US House 313 / 57 / 14, state senate 1,302 / 88 / 56, state house 3,272 / 181 / 180, schools 8,871 / 1,483 / 183. Gray (regular) = 2 US House / 16 state senate / 47 state house / 99 schools (plus 1 GA runoff school district). These are the same v2 2024 polygon gaps as in 2024 (Las Vegas: NV-01; Miami: FL-20; Utah; South Dakota reservations) and a few no-vote school districts. Idaho and Indiana have no gray districts: ID 2 / 35 / 35 / 115, IN 9 / 50 / 100 / 290. About 90% of filled districts are ≈, more than in 2024 because 2022 precincts are bridged onto 2024 polygons.

Weak bridges, so district values there lean on allocation: **MO 18%** (MEDSL 2022 MO precinct names differ from 2024), **LA 21%** (2022 names vs 2024 renumbering), **WI 39%** (reporting units vs wards, as in 2024), **NC 59%**, **AK 62%** (absentee/early by House district), **VT 66%**, **NY 67%**, **CA 68%** (SWDB SR precincts vs 2024 precincts), **IN 38%** (57 counties report only a county total, allocated; the 35 precinct counties bridge 1,851 of 2,039 precincts), ID 72%. County values are not affected by the bridge.
