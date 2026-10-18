# Pennsylvania: gaps and mismatches (2020 and 2024 President)

Audit only, per orchestrator instruction of 2026-10-18 05:41 EDT: nothing in `data/` was changed. Reference: PA Department of State certified county results (see SOURCES.md). Full machine-readable list incl. "all candidates" totals: `pa_v2_vs_official_mismatches.csv`.

## Summary

| Year | v2 layer | Counties with Dem and Rep exact | Statewide Dem v2 / official | Statewide Rep v2 / official |
|---|---|---|---|---|
| 2020 | precinct file sum | 49/67 | 3,457,439 / 3,458,229 (-790) | 3,378,366 / 3,377,674 (+692) |
| 2020 | county table | 66/67 | 3,459,923 / 3,458,229 (+1,694) | 3,378,263 / 3,377,674 (+589) |
| 2024 | precinct file sum | 36/67 | 3,400,309 / 3,423,042 (-22,733) | 3,513,270 / 3,543,308 (-30,038) |
| 2024 | county table | 67/67 | 3,423,042 / 3,423,042 (+0) | 3,543,308 / 3,543,308 (+0) |

## Mismatches: Dem/Rep candidate votes (county, candidate, v2, official, diff)

### 2020 county table (`data/election2020.js`)

| County | Candidate | v2 | Official | Diff | % | Exact alternative source |
|---|---|---|---|---|---|---|
| Allegheny County | Biden | 430,759 | 429,065 | +1,694 | +0.39 | - |
| Allegheny County | Trump | 282,913 | 282,324 | +589 | +0.21 | - |

### 2020 precinct sums (`data/precincts2020/Pennsylvania.js`)

| County | Candidate | v2 | Official | Diff | % | Exact alternative source |
|---|---|---|---|---|---|---|
| Adams County | Biden | 18,260 | 18,207 | +53 | +0.29 | none (needs county official precinct results) |
| Adams County | Trump | 37,567 | 37,523 | +44 | +0.12 | none (needs county official precinct results) |
| Allegheny County | Biden | 429,474 | 429,065 | +409 | +0.10 | none (needs county official precinct results) |
| Allegheny County | Trump | 282,858 | 282,324 | +534 | +0.19 | none (needs county official precinct results) |
| Berks County | Biden | 92,946 | 92,895 | +51 | +0.05 | none (needs county official precinct results) |
| Berks County | Trump | 109,657 | 109,736 | -79 | -0.07 | none (needs county official precinct results) |
| Cambria County | Biden | 21,762 | 21,730 | +32 | +0.15 | VEST, OpenElections |
| Cambria County | Trump | 47,778 | 48,085 | -307 | -0.64 | VEST, OpenElections |
| Centre County | Biden | 40,560 | 40,055 | +505 | +1.26 | VEST, OpenElections |
| Centre County | Trump | 36,954 | 36,372 | +582 | +1.60 | VEST, OpenElections |
| Cumberland County | Biden | 62,789 | 62,245 | +544 | +0.87 | VEST, OpenElections |
| Cumberland County | Trump | 77,554 | 77,212 | +342 | +0.44 | VEST, OpenElections |
| Dauphin County | Biden | 78,974 | 78,983 | -9 | -0.01 | VEST, OpenElections |
| Dauphin County | Trump | 66,287 | 66,408 | -121 | -0.18 | VEST, OpenElections |
| Delaware County | Biden | 206,411 | 206,423 | -12 | -0.01 | none (needs county official precinct results) |
| Delaware County | Trump | 118,460 | 118,532 | -72 | -0.06 | none (needs county official precinct results) |
| Fayette County | Biden | 20,456 | 20,444 | +12 | +0.06 | none (needs county official precinct results) |
| Fayette County | Trump | 41,243 | 41,227 | +16 | +0.04 | none (needs county official precinct results) |
| Lackawanna County | Biden | 62,222 | 61,991 | +231 | +0.37 | VEST, OpenElections |
| Lackawanna County | Trump | 52,475 | 52,334 | +141 | +0.27 | VEST, OpenElections |
| Lehigh County | Biden | 98,315 | 98,288 | +27 | +0.03 | none (needs county official precinct results) |
| Lehigh County | Trump | 84,279 | 84,259 | +20 | +0.02 | none (needs county official precinct results) |
| Luzerne County | Biden | 64,657 | 64,873 | -216 | -0.33 | VEST, OpenElections |
| Luzerne County | Trump | 86,617 | 86,929 | -312 | -0.36 | VEST, OpenElections |
| Monroe County | Biden | 43,329 | 44,060 | -731 | -1.66 | none (needs county official precinct results) |
| Monroe County | Trump | 38,125 | 38,726 | -601 | -1.55 | none (needs county official precinct results) |
| Northampton County | Biden | 85,172 | 85,087 | +85 | +0.10 | VEST, OpenElections |
| Northampton County | Trump | 83,911 | 83,854 | +57 | +0.07 | VEST, OpenElections |
| Northumberland County | Biden | 12,703 | 12,677 | +26 | +0.21 | none (needs county official precinct results) |
| Northumberland County | Trump | 28,975 | 28,952 | +23 | +0.08 | none (needs county official precinct results) |
| Philadelphia County | Biden | 601,797 | 603,790 | -1,993 | -0.33 | none (needs county official precinct results) |
| Philadelphia County | Trump | 132,592 | 132,740 | -148 | -0.11 | none (needs county official precinct results) |
| Westmoreland County | Biden | 72,300 | 72,129 | +171 | +0.24 | none (needs county official precinct results) |
| Westmoreland County | Trump | 130,589 | 130,218 | +371 | +0.28 | none (needs county official precinct results) |
| York County | Biden | 88,139 | 88,114 | +25 | +0.03 | VEST, OpenElections |
| York County | Trump | 146,935 | 146,733 | +202 | +0.14 | VEST, OpenElections |

### 2024 precinct sums (`data/precincts2024/Pennsylvania.js`)

| County | Candidate | v2 | Official | Diff | % | Exact alternative source |
|---|---|---|---|---|---|---|
| Allegheny County | Harris | 429,601 | 429,916 | -315 | -0.07 | MEDSL, OpenElections |
| Allegheny County | Trump | 283,887 | 283,595 | +292 | +0.10 | MEDSL, OpenElections |
| Armstrong County | Harris | 9,124 | 8,553 | +571 | +6.68 | MEDSL, OpenElections |
| Armstrong County | Trump | 28,908 | 28,296 | +612 | +2.16 | MEDSL, OpenElections |
| Berks County | Harris | 89,305 | 91,125 | -1,820 | -2.00 | MEDSL, OpenElections |
| Berks County | Trump | 114,820 | 116,677 | -1,857 | -1.59 | MEDSL, OpenElections |
| Bucks County | Harris | 198,024 | 198,431 | -407 | -0.21 | MEDSL, OpenElections |
| Bucks County | Trump | 198,283 | 198,722 | -439 | -0.22 | MEDSL, OpenElections |
| Butler County | Harris | 40,057 | 40,661 | -604 | -1.49 | MEDSL, OpenElections |
| Butler County | Trump | 78,861 | 79,773 | -912 | -1.14 | MEDSL, OpenElections |
| Carbon County | Harris | 10,692 | 11,394 | -702 | -6.16 | MEDSL |
| Carbon County | Trump | 22,197 | 23,708 | -1,511 | -6.37 | MEDSL |
| Centre County | Harris | 40,993 | 41,119 | -126 | -0.31 | MEDSL, OpenElections |
| Centre County | Trump | 38,416 | 38,829 | -413 | -1.06 | MEDSL, OpenElections |
| Chester County | Harris | 181,326 | 184,281 | -2,955 | -1.60 | MEDSL, OpenElections |
| Chester County | Trump | 134,656 | 137,299 | -2,643 | -1.92 | MEDSL, OpenElections |
| Clarion County | Harris | 4,558 | 4,562 | -4 | -0.09 | MEDSL |
| Clarion County | Trump | 15,163 | 15,036 | +127 | +0.84 | MEDSL |
| Crawford County | Harris | 12,319 | 12,858 | -539 | -4.19 | MEDSL, OpenElections |
| Crawford County | Trump | 28,040 | 29,685 | -1,645 | -5.54 | MEDSL, OpenElections |
| Cumberland County | Harris | 65,810 | 66,255 | -445 | -0.67 | MEDSL, OpenElections |
| Cumberland County | Trump | 79,790 | 80,267 | -477 | -0.59 | MEDSL, OpenElections |
| Dauphin County | Harris | 77,118 | 78,327 | -1,209 | -1.54 | MEDSL, OpenElections |
| Dauphin County | Trump | 68,044 | 69,474 | -1,430 | -2.06 | MEDSL, OpenElections |
| Delaware County | Harris | 202,016 | 201,324 | +692 | +0.34 | MEDSL, OpenElections |
| Delaware County | Trump | 122,766 | 123,421 | -655 | -0.53 | MEDSL, OpenElections |
| Erie County | Harris | 66,832 | 67,456 | -624 | -0.93 | MEDSL, OpenElections |
| Erie County | Trump | 67,824 | 68,866 | -1,042 | -1.51 | MEDSL, OpenElections |
| Fayette County | Harris | 18,964 | 19,548 | -584 | -2.99 | MEDSL, OpenElections |
| Fayette County | Trump | 42,394 | 43,633 | -1,239 | -2.84 | MEDSL, OpenElections |
| Indiana County | Harris | 12,451 | 12,697 | -246 | -1.94 | MEDSL, OpenElections |
| Indiana County | Trump | 28,542 | 29,215 | -673 | -2.30 | MEDSL, OpenElections |
| Lancaster County | Harris | 119,486 | 120,119 | -633 | -0.53 | MEDSL |
| Lancaster County | Trump | 165,484 | 166,261 | -777 | -0.47 | MEDSL |
| Luzerne County | Harris | 61,737 | 62,504 | -767 | -1.23 | MEDSL, OpenElections |
| Luzerne County | Trump | 91,145 | 92,444 | -1,299 | -1.41 | MEDSL, OpenElections |
| Mercer County | Harris | 19,765 | 20,145 | -380 | -1.89 | MEDSL, OpenElections |
| Mercer County | Trump | 37,149 | 37,761 | -612 | -1.62 | MEDSL, OpenElections |
| Mifflin County | Harris | 4,703 | 4,735 | -32 | -0.68 | MEDSL, OpenElections |
| Mifflin County | Trump | 17,163 | 17,184 | -21 | -0.12 | MEDSL, OpenElections |
| Monroe County | Harris | 41,055 | 42,007 | -952 | -2.27 | MEDSL, OpenElections |
| Monroe County | Trump | 41,759 | 42,676 | -917 | -2.15 | MEDSL, OpenElections |
| Montgomery County | Harris | 316,875 | 317,103 | -228 | -0.07 | MEDSL, OpenElections |
| Montgomery County | Trump | 197,979 | 198,311 | -332 | -0.17 | MEDSL, OpenElections |
| Northampton County | Harris | 84,488 | 86,655 | -2,167 | -2.50 | MEDSL, OpenElections |
| Northampton County | Trump | 86,111 | 89,817 | -3,706 | -4.13 | MEDSL, OpenElections |
| Northumberland County | Harris | 12,916 | 12,863 | +53 | +0.41 | MEDSL, OpenElections |
| Northumberland County | Trump | 30,362 | 30,240 | +122 | +0.40 | MEDSL, OpenElections |
| Philadelphia County | Harris | 564,852 | 568,571 | -3,719 | -0.65 | OpenElections |
| Philadelphia County | Trump | 144,260 | 144,311 | -51 | -0.04 | OpenElections |
| Schuylkill County | Harris | 20,334 | 20,882 | -548 | -2.62 | MEDSL, OpenElections |
| Schuylkill County | Trump | 50,336 | 51,665 | -1,329 | -2.57 | MEDSL, OpenElections |
| Venango County | Harris | 7,348 | 7,624 | -276 | -3.62 | MEDSL, OpenElections |
| Venango County | Trump | 18,251 | 18,883 | -632 | -3.35 | MEDSL, OpenElections |
| Washington County | Harris | 44,843 | 44,910 | -67 | -0.15 | MEDSL, OpenElections |
| Washington County | Trump | 75,827 | 75,929 | -102 | -0.13 | MEDSL, OpenElections |
| Wayne County | Harris | 8,984 | 9,150 | -166 | -1.81 | MEDSL |
| Wayne County | Trump | 19,759 | 20,071 | -312 | -1.55 | MEDSL |
| Westmoreland County | Harris | 73,579 | 74,904 | -1,325 | -1.77 | MEDSL, OpenElections |
| Westmoreland County | Trump | 132,963 | 135,008 | -2,045 | -1.51 | MEDSL, OpenElections |
| York County | Harris | 89,717 | 91,926 | -2,209 | -2.40 | MEDSL, OpenElections |
| York County | Trump | 150,764 | 154,884 | -4,120 | -2.66 | MEDSL, OpenElections |

### "All candidates" totals

99 county rows differ in the total column. In 2020 most of these counties have exact Dem/Rep and differ only by write-ins: v2 totals include write-ins (MEDSL), DOS publishes no presidential write-ins. Not an error; listed in the CSV.

## Notes and reasons
- **2020 Allegheny, county table:** v2 Biden 430,759 / Trump 282,913 equals the Allegheny County Board of Elections certified result; the DOS certified statewide total has 429,065 / 282,324 (likely cause, not verified: on 2020-11-23 the county board first certified only the ballots not under legal challenge, and DOS certified the state on 2020-11-24). Two official figures disagree; v2 should pick one explicitly. Not changed.
- **2020 precinct mismatches with no exact secondary source** (Adams, Allegheny, Berks, Delaware, Fayette, Lehigh, Monroe, Northumberland, Philadelphia, Westmoreland): VEST and OpenElections both differ from DOS here. A fix needs official county precinct-level results (county election offices). Not obtained in this pass.
- **2020 Monroe:** v2 precinct sum = VEST, which is short of DOS by 731 Dem / 601 Rep (-1.7%).
- **2020 Centre, Cumberland, Cambria, Dauphin, Lackawanna, Luzerne, Northampton, York:** VEST and OpenElections match DOS exactly, so these can be fixed from VEST, keeping the precinct shapes. Not applied (audit only).
- **2024:** 31 counties off, from -6.4% (Carbon) to +6.7% (Armstrong Dem). MEDSL 2024 matches DOS exactly in 30 of them, and OpenElections matches in Philadelphia. A fix means joining those returns to the v2 precinct shapes (NYT GEOIDs or Census VTDs). Not applied (audit only).
- **COVERAGE.md is stale for PA:** it lists e.g. Butler -32.9%, Clarion -26.6%; the current file has Butler -1.5% Dem, Clarion +0.8% Rep.
- **REPO-RULES.md** did not exist at task start (main c4bad05); read after main moved to 08d298c.
