# County-table fixes applied (v2/data/election2020.js, v2/data/election2024.js)
Script: `tools/apply_table_fixes.py` (idempotent; rewrites only the listed entries in place, keeping key order and format).
Root `data/` is v1 and is never changed: `data/election2020.js` and `data/election2024.js` stay identical to origin/main. The corrected copies, with the same format and globals (`window.ELECTION2020`, `window.ELECTION2024`), are `v2/data/election2020.js` and `v2/data/election2024.js`. Only those county tables changed. Precinct files, district layers, v2/index.html and BUILD were not touched. Values are `[d, r, t]`, where t = all presidential candidates.

## Statewide sums of the county table (D / R / total)
| Year | State | Before | After | FEC | Source | Entries |
|---|---|---|---|---|---|---|
| 2024 | Oregon | 1,228,410 / 910,702 / 2,207,592 | 1,240,600 / 919,480 / 2,244,493 | 1,240,600 / 919,480 / 2,244,493 | Oregon SOS official abstract of votes, Nov 5 2024 | 36 |
| 2020 | Kansas | 558,669 / 758,100 / 1,349,567 | 570,323 / 771,406 / 1,372,303 | 570,323 / 771,406 / 1,373,986 | VEST 2020 KS county sums (doi:10.7910/DVN/K7760H) | 105 |
| 2020 | Rhode Island | 306,210 / 199,837 / 516,383 | 307,486 / 199,922 / 517,757 | 307,486 / 199,922 / 517,757 | VEST 2020 RI county sums | 5 |
| 2020 | New York | 5,244,006 / 3,250,230 / 8,616,205 | 5,244,886 / 3,251,997 / 8,618,852 | 5,244,886 / 3,251,997 / 8,616,861 | VEST 2020 NY county d/r (fusion lines included) | 17 |
| 2020 | Maine | 430,473 / 359,899 / 813,740 | 430,473 / 359,899 / 813,742 | 435,072 / 360,737 / 819,461 | ME SOS official town results by county (`ME/raw/presandvisecnty1120.xlsx`) | 1 |
| 2024 | Virginia | 2,335,395 / 2,075,085 / 4,482,576 | unchanged | 2,333,778 / 2,074,097 / 4,503,288 | — | 0 |

Notes
- **KS**: VEST has no write-in field, so the total is 1,683 below FEC (D and R are exact).
- **NY**: d and r were replaced only in the 17 counties where they differ. t = v2 t + Δd + Δr, because VEST's NY write-in field also includes blank/void ballots in some counties (+16k statewide), so v2's other-candidate votes were kept. The total ends +1,991 vs FEC. **The "+13k" item is dropped:** v2 was below certified, not above.
- **ME**: v2's county D/R already equal the official town results summed by county. The only change is Waldo total 24,320 → 24,322 (Others/write-ins). The remaining gap to certified (4,599 D / 838 R / 5,719 total) is the SOS line **"STATE UOCAVA"**: statewide overseas and military ballots that the SOS does not assign to any town or county. Rule: they stay unassigned (no county gets them), because splitting them would be an estimate. Unorganized territories are already in the official file as town rows under their own county (e.g. "Ashland/T8 R11 Twp" under Aroostook), so no extra rule was needed. VEST's three two-county UT chunks were not used.
- **VA 2024**: left unchanged. v2's D/R equal the VA ELECT certified results. FEC's 2024 file shows 2,333,778 / 2,074,097, an FEC-side discrepancy (-1,617 / -988). v2's total leaves out 23,365 write-ins (certified total 4,505,941).

## QA-003 follow-up (Oct 18 2026), `tools/apply_table_fixes_qa003.py`
Same rules as above: only `v2/data/election2020.js` and `election2024.js` change, only entries whose D or R differ from the official certified county figure are rewritten, and root `data/` is unchanged. The official county values compared are in `qa003_official_counties.csv`.
Total rule: WI, AL and IN official files list every candidate including write-ins, and v2's totals there are on that basis, so t = official total. In CA and MA, v2's totals leave out some write-ins in every county, and PA DOS lists only 3 candidates, so t = v2 t + Δd + Δr (as for NY 2020).

| Year | State | Before (D / R / total) | After | FEC D / R | Source | Entries |
|---|---|---|---|---|---|---|
| 2020 | Pennsylvania | 3,459,923 / 3,378,263 / 6,925,255 | 3,458,229 / 3,377,674 / 6,922,972 | 3,458,229 / 3,377,674 | PA DOS certified Allegheny 429,065 / 282,324 (orchestrator-approved; the county board's own certification was 430,759 / 282,913, see PA/GAPS.md) | 1 |
| 2020 | California | 11,109,764 / 6,005,961 / 17,495,906 | 11,110,250 / 6,006,429 / 17,496,860 | 11,110,250 / 6,006,429 | CA SOS Statement of Vote, President by County (Colusa, Riverside, San Mateo) | 3 |
| 2020 | Wisconsin | 1,630,673 / 1,610,065 / 3,297,352 | 1,630,866 / 1,610,184 / 3,298,041 | 1,630,866 / 1,610,184 | WEC County by County Report, President, post recount (Dane, Milwaukee; v2 had the pre-recount canvass) | 2 |
| 2020 | Alabama | 849,648 / 1,441,168 / 2,323,304 | 849,624 / 1,441,170 / 2,323,282 | 849,624 / 1,441,170 | AL SOS Final Canvass of Results (Hale) | 1 |
| 2020 | Indiana | 1,242,495 / 1,729,852 / 3,033,198 | 1,242,416 / 1,729,519 / 3,033,117 | 1,242,416 / 1,729,519 | Indiana Election Division final results, AllOfficeResults.csv (Ohio, Parke, Scott) | 3 |
| 2024 | Massachusetts | 2,126,545 / 1,251,308 / 3,453,437 | 2,126,518 / 1,251,303 / 3,453,405 | 2,126,518 / 1,251,303 | MA electionstats President by city/town (election 165300), towns summed to counties (Bristol) | 1 |

Not changed:
- **NY 2020**: v2/data is 5,244,886 / 3,251,997, which equals the NY State Board of Elections certification of Dec 3, 2020 (Biden D+WF, Trump R+CON). The app reads `v2/data/election2020.js` (build 1570+), so QA did read v2/data. The jump from QA's earlier +13,021 / +5,432 to +13,901 / +7,199 is the a63e17e VEST fix shipping in build 1570/1571, which brought v2 up to the certified figures. The remaining +13,901 / +7,199 is the difference between NYSBOE and the FEC table (5,230,985 / 3,244,798), so it is on the FEC side. The NYSBOE county file (2020President.xlsx) could not be downloaded from the box (403), so the check is at the state level.
- **ME 2020**: -4,599 / -838 is exactly the SOS line "STATE UOCAVA" (4,599 / 838) in `ME/raw/presandvisecnty1120.xlsx`. These are overseas and military ballots that the SOS does not assign to any county. They stay unassigned.
- **VA 2024**: v2 equals the VA ELECT certification of Dec 2, 2024 (2,335,395 / 2,075,085). FEC's table is lower (2,333,778 / 2,074,097), so the difference is on the FEC side.
- **NH 2024 (+8 / +55) and NH 2020 (-16 / -6)**: the NH SOS result workbooks are not downloadable from the box (403). The only alternative is the NHPR copy of the database, a secondary source, and it also failed to download. Not trivial, so not changed.
- **IN Ohio County** (applied, but note): the Election Division lists Trump 2,054, Biden 668 and Jorgensen 353 there, which is an unusually high Libertarian share. v2 had 750 / 2,392 / 3,164. The certified file is used because its statewide sum equals the certified and FEC totals exactly.
- Blackford and Wabash (IN) and many CA and MA counties differ in the total only (write-ins). They were left as they are.

Raw files (on the box at `/workspace/qa003/raw/`, not committed), SHA-256, retrieved 2026-10-18:
```
2cb5744552cf0574234fa8e731adbe83ccee5ae3421ee4e8e28c35c47a6d7176  al20_final_canvass.pdf
d9d2e021a876f929c28cf4befb92e08e018f59d3aff225a254adab4803da0bfb  ca20_18-presidential.xlsx
6fc9a31c45a536bdd8aa139398d46d1bf595038adad901c3876e0a14c56df6c4  in20_AllOfficeResults.csv
c17c59d7b058d3901d6abd5982bf723b6b5ed650779458d9241ac6741c9afc58  ma24_president_by_town.csv
99c6631d85f465634198ff9c01107d17dd61080ad3ceefb93fb1851427458029  wi20_post_recount.pdf
```
URLs: https://elections.cdn.sos.ca.gov/sov/2020-general/sov/18-presidential.xlsx ; https://elections.wi.gov/sites/default/files/legacy/County%2520by%2520County%2520Report%2520-%2520President%2520of%2520the%2520United%2520States%2520post%2520recount.pdf ; https://www.sos.alabama.gov/sites/default/files/election-2020/Final%20Canvass%20of%20Results-Merged.pdf ; https://enr.indianavoters.in.gov/archive/2020General/download/AllOfficeResults.csv ; https://electionstats.state.ma.us/elections/download/165300/precincts_include:0/

## QA-100 / QA-101 New York county rows (Oct 19 2026)
NY county triples in `v2/data/election{2016,2020,2024}.js` replaced with NYS Board of Elections county results (all 62 keys per year, NY only). d = all Democratic-nominee lines (DEM+WOR, 2016 also WEP), r = Trump REP+CON, total = every candidate incl. write-ins/scattering (official Total Votes − Blank − Void). Sources: NYSBOE results database contests 1650 (2016), 308 (2020), 5591 (2024) county CSVs and official documents 116 / 128 / 476 (2016 county CSV lacks the Trump columns, so 2016 r is taken from doc 116 pp.2-3; internal check: CSV candidates + Trump = Total−Blank−Void in all 62 counties). Corrected rows: `ny/ny_counties_{year}.csv`; script `ny/build.py`.

| Year | Before (D / R / total) | After | FEC D / R / total |
|---|---|---|---|
| 2016 | 4,556,131 / 2,819,552 / 7,720,570 | 4,556,118 / 2,819,533 / 7,721,442 | 4,556,118 / 2,819,533 / 7,721,442 |
| 2020 | 5,244,886 / 3,251,997 / 8,618,852 | 5,244,886 / 3,251,997 / 8,616,861 | NYSBOE 5,244,886 / 3,251,997 / 8,616,861 |
| 2024 | 4,619,195 / 3,578,899 / 8,198,094 | 4,619,543 / 3,579,519 / 8,263,474 | 4,619,195 / 3,578,899 / 8,262,495 |

- 2024: total was d+r in all 62 counties (other candidates dropped), so every NY county summed to 100% (Kings 72.0/28.0 → 70.9/27.6). d/r fusion lines were already correct, except Allegany (+319 / +599) and Nassau (+29 / +21), where NYSBOE's Feb-2025 compiled certified document 476 is higher than the FEC table; NYSBOE used.
- 2016: v2 county rows were VEST precinct sums (precincts assigned to nearest county), which shifted votes among Bronx/Kings/Queens/New York/Nassau/Westchester (9 counties d/r off, up to 4,549 D); now official.
- 2020: d/r unchanged; totals differed in 41 counties (VEST write-in field incl. blank/void); now official.
