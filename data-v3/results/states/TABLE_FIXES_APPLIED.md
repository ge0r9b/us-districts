# County-table fixes applied (data/election2020.js, data/election2024.js)
Script: `tools/apply_table_fixes.py` (idempotent; rewrites only the listed entries in place, keeping key order and format).
Only the county tables changed. Precinct files, district layers, v2/index.html and BUILD were not touched. Values are `[d, r, t]`, where t = all presidential candidates.

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
