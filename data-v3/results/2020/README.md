# 2020 President precincts on 2024 polygons (values only, no geometry)

Same method and format as 2016 (see `../2016/README.md`, section "2016 precincts on 2024 polygons"). User rule: only the current (2024) precinct polygons are stored; past votes are placed onto them.

**Input:** the former `v2/data/precincts2020/<State>.js` and `v2/data/precincts2020-DC.js` (2020 polygons + [Biden, Trump, all candidates]), copied to `/workspace/prec20_orig/` on the box before being overwritten (not committed; also in git history before this commit). Each file's original source credit is kept inside the new credit string.

**Format:** `v2/data/precincts2020/<State>.js`, `v2/data/precincts2020-DC.js`:
```
window.__prec20&&window.__prec20("<State>",[ROW,...],{"credit":"..."});
ROW = [county, precinct, d, r, t]      exact (one 2020 precinct, whole, onto this 2024 polygon; incl. same shape under a different name)
    | [county, precinct, d, r, t, 1]   ≈ (split or merged 2020 precinct)
    | [county, precinct]               gray: no 2020 votes placed
```
Row i = row i of `precincts2024/<State>.js` (or `precincts2024-DC.js`), same `[county, precinct]`; verified for all 51 files (173,276 rows, 0 mismatches). Geometry always comes from the 2024 file. Global `__prec20` (separate from `__prec`). DC: `precincts2020-DC.js` aligned with `precincts2024-DC.js`; the empty 2024 stub `precincts2024/District_of_Columbia.js` has no 2020 counterpart.

**Placement:** `tools/build_prec20_on24.py <repo> /workspace/prec20_orig <report.json> [ab ...]` (name match ≥50% area, else area-weighted with 3%/97% snapping; one state per worker process, 2 workers, ~1 min total). Report: `prec20_on24_report.json`.

**Totals:** 173,276 rows: 94,202 exact (54.4%), 68,393 ≈ (39.5%), 10,681 gray (6.2%). Votes: 54.7% of 2020 votes on exact rows, 44.4% on ≈ rows. Placed D 80,498,249 / R 73,346,769 / T 156,727,534 of D 81,151,820 / R 74,132,877 / T 158,194,257 (99.07%). Unplaced votes are in areas without a 2024 polygon (e.g. South Dakota counties missing from precincts2024: 81.95% placed); they remain in the county and district totals.

**Size:** 50,005,768 bytes before (51 polygon files) → 7,901,190 bytes after (−84.2%).

| State | 2020 precincts | 2024 rows | Exact | ≈ | Gray | Votes on exact rows | Votes placed (T) | Bytes before | Bytes after |
|---|---|---|---|---|---|---|---|---|---|
| Alabama | 1,971 | 1,911 | 1,593 | 316 | 2 | 75.0% | 2,252,463 of 2,323,282 (96.95%) | 1,301,829 | 103,209 |
| Alaska | 440 | 402 | 179 | 220 | 3 | 32.1% | 357,566 of 357,569 (100.00%) | 1,497,787 | 23,250 |
| Arizona | 1,482 | 1,694 | 1,072 | 596 | 26 | 65.3% | 3,384,974 of 3,384,980 (100.00%) | 646,001 | 72,402 |
| Arkansas | 2,555 | 2,649 | 1,797 | 703 | 149 | 66.0% | 1,205,611 of 1,218,760 (98.92%) | 993,455 | 114,957 |
| California | 17,507 | 24,202 | 3,808 | 15,622 | 4,772 | 16.2% | 17,466,951 of 17,466,979 (100.00%) | 3,640,851 | 991,182 |
| Colorado | 3,200 | 3,144 | 1,780 | 1,333 | 31 | 53.2% | 3,230,726 of 3,256,980 (99.19%) | 959,265 | 142,060 |
| Connecticut | 169 | 167 | 167 | 0 | 0 | 98.2% | 1,791,535 of 1,823,857 (98.23%) | 80,468 | 12,383 |
| Delaware | 430 | 525 | 179 | 339 | 7 | 38.6% | 499,208 of 501,604 (99.52%) | 113,643 | 22,591 |
| District of Columbia | 144 | 144 | 140 | 4 | 0 | 96.2% | 344,356 of 344,356 (100.00%) | 29,181 | 8,114 |
| Florida | 5,952 | 5,546 | 3,069 | 2,255 | 222 | 54.4% | 10,761,660 of 11,087,666 (97.06%) | 1,752,286 | 224,586 |
| Georgia | 2,609 | 2,636 | 1,712 | 858 | 66 | 66.6% | 4,871,206 of 4,923,010 (98.95%) | 1,656,561 | 109,515 |
| Hawaii | 250 | 233 | 29 | 197 | 7 | 9.8% | 565,168 of 574,469 (98.38%) | 138,827 | 10,892 |
| Idaho | 934 | 972 | 345 | 627 | 0 | 29.3% | 866,624 of 867,281 (99.92%) | 564,219 | 38,983 |
| Illinois | 10,070 | 8,498 | 4,535 | 3,917 | 46 | 47.0% | 6,011,298 of 6,032,878 (99.64%) | 1,618,074 | 365,837 |
| Indiana | 5,108 | 5,053 | 4,528 | 492 | 33 | 88.1% | 3,013,217 of 3,028,256 (99.50%) | 983,255 | 215,403 |
| Iowa | 1,661 | 1,650 | 714 | 921 | 15 | 38.7% | 1,687,821 of 1,690,871 (99.82%) | 373,831 | 81,514 |
| Kansas | 3,393 | 3,665 | 2,720 | 819 | 126 | 73.3% | 1,360,202 of 1,371,690 (99.16%) | 626,664 | 161,443 |
| Kentucky | 1,223 | 3,200 | 402 | 1,801 | 997 | 11.7% | 2,083,311 of 2,135,315 (97.56%) | 646,222 | 116,047 |
| Louisiana | 3,719 | 3,632 | 2,854 | 671 | 107 | 81.9% | 2,138,258 of 2,147,501 (99.57%) | 1,223,369 | 150,897 |
| Maine | 543 | 490 | 431 | 59 | 0 | 80.3% | 811,630 of 819,369 (99.06%) | 185,580 | 23,358 |
| Maryland | 2,029 | 1,951 | 1,083 | 836 | 32 | 58.3% | 3,013,674 of 3,035,629 (99.28%) | 819,381 | 91,695 |
| Massachusetts | 2,172 | 2,337 | 904 | 1,403 | 30 | 41.7% | 3,559,865 of 3,629,707 (98.08%) | 559,481 | 136,175 |
| Michigan | 4,750 | 3,975 | 2,938 | 1,036 | 1 | 64.8% | 5,483,214 of 5,537,048 (99.03%) | 999,406 | 251,448 |
| Minnesota | 4,077 | 4,067 | 2,972 | 1,072 | 23 | 54.5% | 3,268,616 of 3,277,171 (99.74%) | 899,216 | 192,289 |
| Mississippi | 1,763 | 1,703 | 1,481 | 212 | 10 | 83.6% | 1,291,682 of 1,313,677 (98.33%) | 828,359 | 79,693 |
| Missouri | 3,480 | 3,021 | 1,765 | 1,211 | 45 | 54.5% | 2,969,660 of 3,023,191 (98.23%) | 940,746 | 139,402 |
| Montana | 663 | 720 | 354 | 354 | 12 | 30.7% | 600,252 of 603,640 (99.44%) | 649,031 | 33,280 |
| Nebraska | 1,373 | 1,326 | 548 | 768 | 10 | 34.1% | 944,777 of 945,800 (99.89%) | 296,313 | 62,348 |
| Nevada | 1,862 | 1,236 | 586 | 624 | 26 | 35.7% | 1,395,595 of 1,404,669 (99.35%) | 474,367 | 47,486 |
| New Hampshire | 302 | 238 | 226 | 12 | 0 | 72.8% | 803,824 of 803,833 (100.00%) | 87,454 | 12,746 |
| New Jersey | 726 | 6,378 | 75 | 4,065 | 2,238 | 1.2% | 4,544,631 of 4,549,353 (99.90%) | 257,803 | 383,650 |
| New Mexico | 1,923 | 2,164 | 1,736 | 310 | 118 | 86.5% | 908,049 of 908,366 (99.97%) | 1,078,801 | 88,204 |
| New York | 15,193 | 12,902 | 4,731 | 8,117 | 54 | 34.1% | 8,582,724 of 8,632,253 (99.43%) | 2,367,910 | 592,366 |
| North Carolina | 2,661 | 2,643 | 2,543 | 96 | 4 | 95.4% | 5,504,992 of 5,523,005 (99.67%) | 1,467,174 | 118,899 |
| North Dakota | 422 | 379 | 111 | 250 | 18 | 17.1% | 361,710 of 362,024 (99.91%) | 152,978 | 15,704 |
| Ohio | 8,930 | 8,786 | 7,350 | 1,419 | 17 | 81.9% | 5,842,386 of 5,919,356 (98.70%) | 2,081,859 | 436,951 |
| Oklahoma | 1,938 | 1,980 | 1,029 | 891 | 60 | 48.2% | 1,560,711 of 1,560,699 (100.00%) | 867,638 | 81,221 |
| Oregon | 1,320 | 1,244 | 801 | 401 | 42 | 47.5% | 2,288,005 of 2,374,321 (96.36%) | 686,780 | 50,483 |
| Pennsylvania | 9,160 | 9,100 | 8,499 | 599 | 2 | 92.7% | 6,879,913 of 6,924,589 (99.35%) | 2,328,625 | 441,677 |
| Rhode Island | 418 | 39 | 2 | 37 | 0 | 0.7% | 515,251 of 515,251 (100.00%) | 98,761 | 3,305 |
| South Carolina | 2,257 | 2,302 | 2,174 | 98 | 30 | 96.1% | 2,500,738 of 2,507,042 (99.75%) | 1,092,654 | 109,585 |
| South Dakota | 737 | 623 | 322 | 289 | 12 | 39.7% | 346,325 of 422,609 (81.95%) | 225,720 | 26,094 |
| Tennessee | 1,957 | 1,845 | 928 | 898 | 19 | 40.0% | 3,036,098 of 3,052,626 (99.46%) | 1,295,531 | 89,387 |
| Texas | 8,862 | 9,712 | 6,850 | 2,201 | 661 | 72.0% | 11,248,027 of 11,248,020 (100.00%) | 3,985,406 | 365,886 |
| Utah | 2,262 | 2,670 | 483 | 2,110 | 77 | 16.6% | 1,467,807 of 1,487,676 (98.66%) | 635,158 | 108,762 |
| Vermont | 275 | 247 | 222 | 25 | 0 | 67.6% | 365,702 of 367,428 (99.53%) | 68,418 | 12,942 |
| Virginia | 2,476 | 2,518 | 1,448 | 1,063 | 7 | 57.5% | 4,379,138 of 4,459,747 (98.19%) | 1,198,074 | 134,638 |
| Washington | 7,375 | 7,912 | 6,188 | 1,350 | 374 | 81.8% | 4,024,932 of 4,079,396 (98.66%) | 1,631,104 | 326,132 |
| West Virginia | 1,671 | 1,611 | 952 | 589 | 70 | 57.2% | 777,407 of 794,652 (97.83%) | 1,049,324 | 58,183 |
| Wisconsin | 6,695 | 6,819 | 2,564 | 4,181 | 74 | 33.7% | 3,296,104 of 3,298,041 (99.94%) | 1,510,744 | 402,672 |
| Wyoming | 480 | 415 | 283 | 126 | 6 | 53.7% | 261,940 of 276,765 (94.64%) | 340,184 | 19,264 |
