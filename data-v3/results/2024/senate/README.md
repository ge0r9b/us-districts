# 2024 US Senate results (data-v3)

The 34 regular (Class I) races in 33 states, plus the two specials held the same day: the **California** unexpired term (Schiff v. Garvey) and the **Nebraska** unexpired term (Ricketts v. Love). Nebraska's regular race is Fischer v. Osborn. Results are on v2's current boundaries and layers: states, counties, US House, state senate, state house, school districts and 2024 precincts. States without a 2024 Senate race (17 states and DC) have **no rows**, so they show gray. Nothing in `v2/data/`, root `data/`, `v2/index.html` or `BUILD` was touched.

## Files
All files use the 13 bot columns plus the optional 14th `method` (Q-E3). `.gz` = gzip of the same CSV.

| File | Rows | unit_type | Source / method |
|---|---|---|---|
| `us_senate_2024_state.csv` | 160 | `state` (state FIPS) | Clerk of the House, *Statistics of the Presidential and Congressional Election of Nov 5, 2024* (official). Every candidate, with fusion lines merged into their candidate (CT Murphy D+WF; NY Gillibrand D+WF, Sapraicone R+CON). Blank, over/under, void and "None of these candidates" (NV) are not votes. `method=official` |
| `us_senate_2024_county.csv` | 5,662 | `county` (5-digit FIPS; CT = planning regions) | MEDSL 2024 precinct returns summed by v2 county. `method=retabulated` |
| `precincts/<ST>.csv.gz` (33 files) | 368,271 | `precinct` | MEDSL precinct rows that matched a v2 2024 precinct polygon. `method=official` (as reported per precinct) |
| `us_senate_2024_ushouse.csv` | 1,091 | `ushouse` (GEOID) | precinct polygons area-weighted into v2 districts. `method=retabulated` (exact) or `area_weighted` (= ≈) |
| `us_senate_2024_sldu.csv` | 3,877 | `sldu` | same |
| `us_senate_2024_sldl.csv` | 9,619 | `sldl` | same |
| `us_senate_2024_school.csv.gz` | 29,646 | `school_unified` / `school_elementary` / `school_secondary` (from `data-v3/geo/schools.csv` tiger_set) | same |
| `statewide_vs_official.csv` | 35 | n/a (audit, not result rows) | MEDSL statewide sums vs Clerk official |
| `precinct_match.csv` | 35 | n/a (audit) | match rate per race |
| `GAPS.csv` | 924 | n/a (audit) | unmatched MEDSL votes by county, gray districts with reason |
| `tools/` | | | `races.py` (race config, d-slot rule), `build_sen2024.py` (MEDSL → v2 polygons), `layers_sen2024.py` (districts), `write_csv_sen2024.py` (CSVs) |

Row conventions:
- `office`: `us_senate` for regular races, `us_senate_special` for the CA and NE unexpired terms. `district=statewide`.
- Below the state level, each unit has 3 rows: the **d slot** candidate, the **r slot** candidate, and `all-others` (`answer` "All others", party `OTH`; left out when 0). The total is d + r + all-others = all candidates, write-ins included.
- `candidate_id` = surname-first slug from the Clerk name (e.g. `gallego-ruben`, `king-angus-s-jr`, `blunt-rochester-lisa`). Write-in/scattering lines are `write-ins`.
- Precinct `unit_id` = `<ST>|<v2 county>|<v2 precinct name>`, the v2 export key, with `|#<row ordinal in v2/data/precincts2024/<State>.js>` appended only where the county/name pair repeats. The polygon is that row of the v2 2024 precinct file (the president 2024 polygons).
- `source_url` = the MEDSL state zip (or the Clerk PDF for state rows). `retrieved_at` = download time (UTC). `weight` = 1.

## d-slot rule (flagged races)
**d = the Democratic nominee, unless an independent (non-Republican) candidate outpolled the Democratic nominee statewide, or there was no Democratic nominee. In those cases d = that independent. r = the Republican nominee.** The rule is fixed per race, so d is the same candidate in every unit of a state.

| Race | d slot | Note |
|---|---|---|
| ME regular | Angus King (I) 427,331 | The Democratic nominee David Costello (88,891) is in all-others. King won in the first round, so RCV was not used. |
| VT regular | Bernie Sanders (I) 229,429 | No Democratic nominee on the ballot |
| NE regular | Dan Osborn (independent, "By Petition") 436,493 | No Democratic nominee on the ballot |
| NE special | Preston Love Jr. (D) | normal |
| ND | Katrina Christiansen (Democratic-NPL) | normal |
| CA regular and special | Adam Schiff (D) v. Steve Garvey (R) | top-two general; normal |

## How it was built
1. **MEDSL rows**: within each (office, county, jurisdiction, precinct), only `mode=TOTAL` rows are used when they exist; otherwise all modes are summed. This avoids the double counting described in the MEDSL README. `*` (privacy-suppressed) counts as 0. California `202A`/`AA`/`B`/`C` sub-rows (absentee and later batches) are merged into precinct `202` (MEDSL README). Candidates are assigned to d / r / other by name, so fusion lines count for their candidate.
2. **Matching to v2 polygons**, using the 2024 **president** result, which both MEDSL and the v2 precinct file carry:
   (a) same county and identical (Harris, Trump) pair, unique on both sides;
   (b) same county and same normalized name;
   (c) statewide unique (Harris, Trump) pair;
   (d) MEDSL precincts summed by town/jurisdiction, matched to a town-level v2 polygon (RI, CT, VT, MA).
   A matched polygon gets the exact MEDSL Senate values, which are written to `precincts/`.
3. **Unmatched MEDSL votes**: county-wide absentee/provisional buckets, and precinct sets that differ from v2's (WI reporting units vs. wards, MO, WA King County reporting only a county total, NJ). These are allocated to the county's unmatched polygons (or all its polygons if none are unmatched), in proportion to each polygon's president d / r / total. Allocated votes appear only in the district layers and make them ≈ (see below). They are never written as precinct rows.
4. **Districts**: polygon values are area-weighted into v2's current `uscd` / `ussldu` / `ussldl` / `ussch` shapes, the same method as 2016. An overlap under 3% or over 97% of a polygon's area is treated as 0 or 1, because these are simplification slivers. A district is **≈** (`method=area_weighted`) when more than 2% of its total comes from polygons split by the district line, or from allocated votes. A district is **gray** (no row) when the polygons cover less than 50% of its area (gaps in the v2 2024 precinct file, e.g. Utah, Maine unorganized territory) or it has no votes.
5. **Counties** = MEDSL precinct sums per county. For CT, MEDSL uses the old 8 counties, so CT rows are the v2 planning regions of the matched towns (98% of votes were matched by town).

## Statewide check: MEDSL sums vs official (Clerk), D / R / total
| Race | Official | MEDSL − official |
|---|---|---|
| AZ regular | 1,676,335 / 1,595,761 / 3,348,814 | -12,186 / -7,169 / -13,780 (-0.41%) |
| CA regular | 9,036,252 / 6,312,594 / 15,348,846 | -6,664 / -9,941 / -16,605 (-0.11%) |
| CA special | 8,837,051 / 6,204,637 / 15,041,688 | -6,430 / -9,617 / -16,047 (-0.11%) |
| CT regular | 1,000,695 / 678,256 / 1,708,259 | +0 / +0 / +0 (+0.00%) |
| DE regular | 283,298 / 197,753 / 500,606 | +0 / +0 / +0 (+0.00%) |
| FL regular | 4,603,077 / 5,977,706 / 10,757,428 | +0 / +1 / +9,884 (+0.09%) |
| HI regular | 324,194 / 160,075 / 501,763 | +0 / +0 / +0 (+0.00%) |
| IN regular | 1,097,061 / 1,659,416 / 2,829,897 | +55,798 / +87,065 / +146,587 (+5.18%) |
| MA regular | 2,041,668 / 1,365,440 / 3,413,329 | +0 / +0 / +0 (+0.00%) |
| MD regular | 1,650,912 / 1,294,344 / 3,021,378 | +0 / +0 / +0 (+0.00%) |
| ME regular | 427,331 / 284,338 / 820,782 | -2,841 / -700 / -6,144 (-0.75%) |
| MI regular | 2,712,686 / 2,693,680 / 5,577,187 | +0 / +0 / +0 (+0.00%) |
| MN regular | 1,792,441 / 1,291,712 / 3,189,323 | +0 / +0 / +0 (+0.00%) |
| MO regular | 1,243,728 / 1,651,907 / 2,972,559 | +0 / +0 / +0 (+0.00%) |
| MS regular | 451,981 / 763,420 / 1,215,401 | -1 / +0 / -1 (-0.00%) |
| MT regular | 276,305 / 319,682 / 607,262 | -53 / -64 / -120 (-0.02%) |
| ND regular | 121,602 / 241,569 / 364,327 | +0 / +0 / +0 (+0.00%) |
| NE regular | 436,493 / 499,124 / 938,336 | +0 / +0 / -2,719 (-0.29%) |
| NE special | 349,902 / 585,103 / 935,005 | +0 / +0 / +0 (+0.00%) |
| NJ regular | 2,161,491 / 1,773,589 / 4,031,795 | -261,919 / -40,733 / -305,594 (-7.58%) |
| NM regular | 497,333 / 405,978 / 903,311 | -43 / -8 / -51 (-0.01%) |
| NV regular | 701,105 / 677,046 / 1,420,348 | -129 / -194 / -330 (-0.02%) |
| NY regular | 4,711,298 / 3,246,114 / 8,010,317 | -839 / -1,707 / -2,561 (-0.03%) |
| OH regular | 2,650,949 / 2,857,383 / 5,704,620 | +0 / +0 / -640 (-0.01%) |
| PA regular | 3,384,180 / 3,399,295 / 6,963,137 | -2,036 / -241 / -2,362 (-0.03%) |
| RI regular | 294,665 / 196,039 / 491,948 | +0 / +0 / +0 (+0.00%) |
| TN regular | 1,027,461 / 1,918,743 / 3,007,608 | +0 / +0 / +0 (+0.00%) |
| TX regular | 5,031,249 / 5,990,741 / 11,291,854 | -107 / -104 / -1,621 (-0.01%) |
| UT regular | 464,515 / 914,700 / 1,463,509 | -147 / -402 / -580 (-0.04%) |
| VA regular | 2,417,115 / 2,019,911 / 4,445,535 | +0 / +0 / +0 (+0.00%) |
| VT regular | 229,429 / 116,512 / 363,253 | +0 / +0 / +0 (+0.00%) |
| WA regular | 2,252,577 / 1,549,187 / 3,812,391 | -1,522 / -2,052 / -3,582 (-0.09%) |
| WI regular | 1,672,777 / 1,643,996 / 3,390,787 | +0 / +0 / +0 (+0.00%) |
| WV regular | 207,548 / 514,079 / 747,717 | +0 / +0 / -15 (-0.00%) |
| WY regular | 63,727 / 198,418 / 264,162 | +0 / +0 / +0 (+0.00%) |

Notes:
- **NJ** (−7.6%): MEDSL's NJ file mixes TOTAL and per-mode rows inconsistently by county (e.g. Mercer has no early-vote rows). Treat NJ county and district values as low.
- **IN** (+5.2%): MEDSL warns that some Indiana county sources fold straight-party votes into candidate totals, so they are overreported.
- **ME** (−0.75%): probably the statewide UOCAVA ballots, which are not in town counts (as for president 2020). Not verified.
- **AZ** (−0.4%): MEDSL is short. Cause not verified.
- All other states are within 0.1% on D and R, most exact.
- `us_senate_2024_state.csv` has the official values, so the states layer is exact.

## Coverage
| Race | MEDSL precincts matched | v2 polygons with an exact value | Senate votes matched |
|---|---|---|---|
| AZ regular | 1666 / 1682 | 1666 / 1694 | 99.9% |
| CA regular | 23249 / 25783 | 23249 / 24202 | 96.9% |
| CA special | 23249 / 25783 | 23249 / 24202 | 96.9% |
| CT regular | 739 / 758 | 167 / 167 | 98.2% |
| DE regular | 525 / 530 | 525 / 525 | 99.3% |
| FL regular | 5504 / 5710 | 5504 / 5546 | 98.8% |
| HI regular | 233 / 467 | 233 / 233 | 91.7% |
| IN regular | 4962 / 5300 | 4960 / 5053 | 92.4% |
| MA regular | 2327 / 2394 | 2327 / 2337 | 97.3% |
| MD regular | 1942 / 1958 | 1942 / 1951 | 99.8% |
| ME regular | 453 / 511 | 453 / 490 | 93.3% |
| MI regular | 3913 / 4423 | 3910 / 3975 | 94.9% |
| MN regular | 4056 / 4103 | 4055 / 4067 | 99.9% |
| MO regular | 1486 / 3285 | 1415 / 3021 | 36.4% |
| MS regular | 1703 / 1736 | 1702 / 1703 | 98.8% |
| MT regular | 720 / 727 | 720 / 720 | 99.2% |
| ND regular | 379 / 385 | 379 / 379 | 99.9% |
| NE regular | 1326 / 1326 | 1326 / 1326 | 100.0% |
| NE special | 1326 / 1326 | 1326 / 1326 | 100.0% |
| NJ regular | 4328 / 5262 | 4327 / 6378 | 75.0% |
| NM regular | 2134 / 2169 | 2134 / 2164 | 99.2% |
| NV regular | 1232 / 1640 | 1232 / 1236 | 99.7% |
| NY regular | 12737 / 13112 | 12737 / 12902 | 98.5% |
| OH regular | 8784 / 8878 | 8784 / 8786 | 98.9% |
| PA regular | 8641 / 9187 | 8640 / 9100 | 96.3% |
| RI regular | 370 / 458 | 38 / 39 | 89.2% |
| TN regular | 1846 / 1862 | 1845 / 1845 | 99.4% |
| TX regular | 9058 / 9712 | 9058 / 9712 | 97.5% |
| UT regular | 2670 / 3105 | 2670 / 2670 | 99.6% |
| VA regular | 2384 / 2669 | 2384 / 2518 | 91.6% |
| VT regular | 276 / 283 | 243 / 247 | 96.0% |
| WA regular | 4962 / 5356 | 4962 / 7912 | 70.5% |
| WI regular | 2138 / 3601 | 2138 / 6819 | 40.4% |
| WV regular | 1603 / 1651 | 1603 / 1611 | 96.4% |
| WY regular | 415 / 431 | 415 / 415 | 94.9% |

District layers (regular / special): US House 325 / 55 filled (2 gray), state senate 1,253 / 89 (14 gray), state house 3,159 / 129 (44 gray), schools 9,328 / 1,216 (124 + 2 gray). About 85-90% of the filled districts are ≈, because precinct and district lines differ slightly and county-wide absentee votes are allocated. Gray districts and unmatched votes are listed with reasons in `GAPS.csv`.

Gaps worth knowing: WI (40% of votes matched: MEDSL has reporting units, v2 has wards), MO (36%: different precinct combinations), WA (70%: King County has only a county total in MEDSL), NJ (75%, and low overall).
