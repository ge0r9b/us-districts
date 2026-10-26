# Speed: performance table (one row per build x viewport)

Method (tools/baseline.py): headless Chromium (Playwright), is_mobile, DPR 2, iPhone/iPad UA, no CPU throttling, live URL with `?v=<ms>`, fresh context (cold cache) per viewport.
Box is shared and was loaded (load avg 3-5) so treat single numbers as +/-30%.

- **Bytes**: CDP Network, app origin only (tiles excluded). *initial* = load + networkidle + 3 s. *PA session* = initial + All States list + slider/chart taps + drill into PA (counties) + US House pick in PA. Shown as transferred (gzip) / decoded MB.
- **DCL / load**: Navigation Timing (ms). **first map** = first rAF where both a basemap tile is loaded and a Leaflet canvas pane has non-transparent pixels (states/county fill).
- **Taps**: `touchscreen.tap` on the element's centre, latency = event.timeStamp to rAF+setTimeout(0) after it (same as QA's flow.py). Reported median / max over 5 tries (time step: 10). "cold" = first try in the session.
  - All States = `li.la-row` in the institution menu (`#bGeo`); US House = `#lyrRow .lbtn[data-k=ushouse]` (pick, inside PA counties list); Line = `#chartBox .copts button[data-ch=line]` in a 2020>2024 range; drill = PA row (`#listView .lvrow.la` with .nmx PA); back = `#bBack`; time step = `#ysl .tk[data-i=1|2]`.
- **Pan**: 3 touch drags (24 moves each, CDP touch events) on the US map; rAF frame intervals: fps, p95, max, dropped (= sum(round(dt/16.7)-1)).

| build (sha) | viewport | initial MB gz / raw | PA session MB gz / raw | DCL | load | first map | longest task | All States ms | US House pick ms | Line pick ms | drill PA ms | back ms | time step ms | pan |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1575 (7a23208) | 390x844 | 1.57 / 7.76 | 3.64 / 13.28 | 1155 | 1184 | 787 | 208 | 117 / 334 (cold 334) | 96 / 299 (cold 299) | 20 / 35 | 18 / 22 | 71 / 74 | 53 / 90 | 58.1 fps, p95 16.8, max 83.4, dropped 8/250 |
| 1575 (7a23208) | 375x667 | 1.57 / 7.76 | 3.64 / 13.28 | 549 | 958 | 788 | 137 | 100 / 308 (cold 308) | 81 / 305 (cold 305) | 18 / 20 | 14 / 72 | 59 / 241 | 54 / 75 | 57.0 fps, p95 16.8, max 83.3, dropped 14/263 |
| 1575 (7a23208) | 320x568 | 1.57 / 7.76 | 3.64 / 13.28 | 690 | 956 | 697 | 166 | 82 / 276 (cold 276) | 89 / 315 (cold 315) | 19 / 35 | 19 / 56 | 52 / 215 | 45 / 67 | 59.8 fps, p95 16.7, max 33.3, dropped 1/278 |
| 1575 (7a23208) | ipad820x1180 | 1.57 / 7.76 | 3.64 / 13.28 | 1417 | 1442 | 1147 | 214 | 150 / 233 (cold 233) | 93 / 372 (cold 372) | 18 / 22 | 15 / 19 | 51 / 62 | 53 / 73 | 44.8 fps, p95 33.4, max 166.6, dropped 82/241 |
| 1576 (615fa5a) | 390x844 | 1.57 / 7.76 | 3.64 / 13.29 | 930 | 976 | 630 | 177 | 82 / 240 (cold 240) | 102 / 346 (cold 346) | 21 / 25 | 15 / 20 | 53 / 57 | 55 / 116 | 59.3 fps, p95 16.7, max 50, dropped 3/273 |
| 1576 (615fa5a) | 375x667 | 1.57 / 7.76 | 3.64 / 13.29 | 845 | 880 | 752 | 132 | 99 / 260 (cold 260) | 101 / 272 (cold 272) | 8 / 12 | 15 / 140 | 76 / 278 | 49 / 71 | 59.4 fps, p95 16.8, max 50, dropped 3/277 |
| 1576 (615fa5a) | 320x568 | 1.57 / 7.76 | 3.64 / 13.29 | 1044 | 1092 | 990 | 176 | 84 / 270 (cold 270) | 78 / 374 (cold 374) | 9 / 33 | 14 / 34 | 46 / 58 | 64 / 82 | 60.0 fps, p95 16.7, max 16.8, dropped 0/278 |
| 1576 (615fa5a) | ipad820x1180 | 1.57 / 7.76 | 3.64 / 13.29 | 1158 | 1179 | 793 | 174 | 170 / 195 (cold 190) | 81 / 353 (cold 353) | 17 / 23 | 18 / 34 | 57 / 94 | 49 / 66 | 47.4 fps, p95 33.4, max 83.3, dropped 60/226 |
| 1579 (479deb7) | 390x844 | 1.58 / 7.78 | 3.65 / 13.30 | 785 | 828 | 697 | 124 | 101 / 240 (cold 240) | 131 / 465 (cold 465) | 25 / 36 | 21 / 74 | 92 / 253 | 65 / 89 | 59.6 fps, p95 16.7, max 33.4, dropped 2/267 |
| 1579 (479deb7) | 375x667 | 1.58 / 7.78 | 3.65 / 13.30 | 701 | 982 | 641 | 165 | 105 / 282 (cold 282) | 131 / 271 (cold 271) | 21 / 28 | 28 / 131 | 83 / 289 | 66 / 82 | 59.1 fps, p95 16.8, max 50, dropped 4/272 |
| 1579 (479deb7) | 320x568 | 1.58 / 7.78 | 3.65 / 13.30 | 528 | 854 | 784 | 125 | 93 / 263 (cold 263) | 123 / 315 (cold 315) | 23 / 33 | 22 / 142 | 75 / 282 | 75 / 145 | 60.0 fps, p95 16.7, max 16.8, dropped 0/279 |
| 1579 (479deb7) | ipad820x1180 | 1.58 / 7.78 | 3.65 / 13.31 | 1215 | 1260 | 764 | 168 | 136 / 199 (cold 199) | 128 / 380 (cold 380) | 22 / 26 | 14 / 25 | 91 / 97 | 72 / 86 | 51.4 fps, p95 33.4, max 116.6, dropped 42/250 |
| 1582 (16b1393) | 390x844 | 1.58 / 7.79 | 3.65 / 13.32 | 756 | 806 | 677 | 131 | 96 / 232 (cold 232) | 102 / 260 (cold 260) | 15 / 28 | 16 / 19 | 99 / 283 | 57 / 75 | 59.6 fps, p95 16.8, max 33.3, dropped 2/274 |
| 1582 (16b1393) | 375x667 | 1.58 / 7.79 | 3.65 / 13.31 | 714 | 733 | 651 | 108 | 94 / 237 (cold 237) | 111 / 333 (cold 333) | 16 / 24 | 13 / 16 | 90 / 242 | 66 / 85 | 60.0 fps, p95 16.7, max 16.8, dropped 0/279 |
| 1582 (16b1393) | 320x568 | 1.58 / 7.79 | 3.65 / 13.32 | 796 | 843 | 620 | 120 | 74 / 261 (cold 261) | 100 / 242 (cold 242) | 15 / 24 | 16 / 19 | 102 / 278 | 54 / 73 | 60.0 fps, p95 16.7, max 16.8, dropped 0/278 |
| 1582 (16b1393) | ipad820x1180 | 1.58 / 7.79 | 3.65 / 13.31 | 629 | 1017 | 638 | 167 | 146 / 191 (cold 191) | 116 / 347 (cold 347) | 19 / 33 | 14 / 87 | 106 / 134 | 69 / 89 | 44.5 fps, p95 33.4, max 83.3, dropped 73/209 |
| 1584 (ae92b92) | 390x844 | 1.59 / 7.79 | 3.65 / 13.32 | 801 | 812 | 585 | 149 | 37 / 118 (cold 118) | 74 / 122 (cold 47) | 14 / 24 | 28 / 32 | 46 / 52 | 51 / 60 | 59.4 fps, p95 16.8, max 33.3, dropped 3/277 |
| 1584 (ae92b92) | 375x667 | 1.59 / 7.79 | 3.65 / 13.31 | 458 | 684 | 644 | 100 | 37 / 104 (cold 104) | 72 / 94 (cold 41) | 13 / 22 | 12 / 16 | 43 / 49 | 41 / 58 | 59.8 fps, p95 16.7, max 33.4, dropped 1/272 |
| 1584 (ae92b92) | 320x568 | 1.59 / 7.79 | 3.66 / 13.32 | 750 | 791 | 574 | 117 | 44 / 93 (cold 93) | 68 / 76 (cold 53) | 17 / 21 | 19 / 73 | 44 / 58 | 42 / 77 | 60.0 fps, p95 16.7, max 16.8, dropped 0/278 |
| 1584 (ae92b92) | ipad820x1180 | 1.59 / 7.79 | 3.65 / 13.32 | 576 | 1255 | 993 | 167 | 34 / 117 (cold 117) | 69 / 74 (cold 55) | 11 / 19 | 14 / 88 | 49 / 64 | 44 / 63 | 47.1 fps, p95 33.4, max 83.3, dropped 61/222 |
| 1585 (5a0df17) | 390x844 | 1.59 / 7.80 | 3.66 / 13.32 | 672 | 1072 | 810 | 148 | 39 / 83 (cold 83) | 69 / 111 (cold 61) | 17 / 22 | 15 / 18 | 34 / 40 | 48 / 74 | 59.8 fps, p95 16.7, max 33.4, dropped 1/278 |
| 1585 (5a0df17) | 375x667 | 1.59 / 7.80 | 3.66 / 13.33 | 669 | 868 | 671 | 121 | 44 / 93 (cold 93) | 65 / 88 (cold 55) | 15 / 27 | 13 / 50 | 36 / 46 | 42 / 66 | 59.8 fps, p95 16.8, max 33.3, dropped 1/279 |
| 1585 (5a0df17) | 320x568 | 1.59 / 7.80 | 3.66 / 13.33 | 445 | 747 | 554 | 130 | 35 / 91 (cold 91) | 87 / 94 (cold 66) | 24 / 31 | 14 / 15 | 36 / 41 | 41 / 76 | 59.6 fps, p95 16.8, max 33.3, dropped 2/277 |
| 1585 (5a0df17) | ipad820x1180 | 1.59 / 7.80 | 3.66 / 13.32 | 1046 | 1340 | 638 | 170 | 44 / 91 (cold 91) | 74 / 133 (cold 133) | 22 / 33 | 14 / 33 | 45 / 47 | 44 / 57 | 43.6 fps, p95 33.4, max 133.4, dropped 79/210 |
| 1588 (5a7711c) | 390x844 | 1.59 / 7.81 | 3.66 / 13.33 | 794 | 1155 | 974 | 100 | 39 / 99 (cold 99) | 72 / 121 (cold 57) | 14 / 22 | 13 / 26 | 39 / 51 | 47 / 58 | 59.8 fps, p95 16.7, max 33.4, dropped 1/277 |
| 1588 (5a7711c) | 375x667 | 1.59 / 7.81 | 3.66 / 13.34 | 611 | 955 | 911 | 118 | 33 / 83 (cold 83) | 68 / 88 (cold 47) | 14 / 33 | 15 / 76 | 36 / 42 | 40 / 62 | 60.0 fps, p95 16.7, max 16.8, dropped 0/280 |
| 1588 (5a7711c) | 320x568 | 1.59 / 7.81 | 3.66 / 13.34 | 460 | 833 | 674 | 120 | 45 / 79 (cold 79) | 68 / 86 (cold 44) | 14 / 26 | 13 / 18 | 35 / 37 | 43 / 52 | 60.0 fps, p95 16.7, max 16.8, dropped 0/280 |
| 1588 (5a7711c) | ipad820x1180 | 1.59 / 7.81 | 3.66 / 13.34 | 459 | 973 | 689 | 135 | 36 / 155 (cold 155) | 61 / 81 (cold 49) | 12 / 20 | 18 / 74 | 43 / 61 | 49 / 76 | 47.7 fps, p95 33.4, max 83.2, dropped 55/214 |
| 1595 (c34d398) | 390x844 | 1.59 / 7.81 | 3.66 / 13.34 | 425 | 750 | 669 | 101 | 34 / 88 (cold 88) | 70 / 80 (cold 55) | 15 / 33 | 13 / 34 | 33 / 37 | 46 / 52 | 59.6 fps, p95 16.7, max 33.4, dropped 2/278 |
| 1595 (c34d398) | 375x667 | 1.59 / 7.81 | 3.66 / 13.34 | 580 | 739 | 557 | 107 | 46 / 95 (cold 95) | 74 / 77 (cold 70) | 22 / 35 | 27 / 71 | 36 / 37 | 41 / 49 | 60.0 fps, p95 16.8, max 16.8, dropped 0/280 |
| 1595 (c34d398) | 320x568 | 1.59 / 7.81 | 3.66 / 13.34 | 730 | 775 | 565 | 113 | 32 / 85 (cold 85) | 86 / 127 (cold 47) | 18 / 23 | 15 / 22 | 41 / 51 | 42 / 58 | 59.8 fps, p95 16.8, max 33.2, dropped 1/279 |
| 1595 (c34d398) | ipad820x1180 | 1.59 / 7.81 | 3.66 / 13.34 | 1067 | 1148 | 891 | 163 | 44 / 130 (cold 130) | 67 / 78 (cold 47) | 24 / 34 | 14 / 24 | 40 / 43 | 46 / 75 | 47.9 fps, p95 33.4, max 66.7, dropped 55/217 |
| 1611 (f435ab2) | 390x844 | 1.60 / 7.83 | 3.67 / 13.35 | 599 | 972 | 929 | 145 | 35 / 91 (cold 91) | 75 / 103 (cold 55) | 16 / 31 | 16 / 46 | 27 / 32 | 49 / 138 | 59.6 fps, p95 16.8, max 50, dropped 2/278 |
| 1611 (f435ab2) | 375x667 | 1.60 / 7.83 | 3.67 / 13.36 | 694 | 699 | 642 | 111 | 44 / 103 (cold 103) | 74 / 96 (cold 51) | 18 / 26 | 16 / 35 | 22 / 38 | 56 / 88 | 59.2 fps, p95 16.7, max 83.3, dropped 4/279 |
| 1611 (f435ab2) | 320x568 | 1.60 / 7.83 | 3.67 / 13.35 | 665 | 670 | 624 | 99 | 40 / 116 (cold 116) | 114 / 213 (cold 54) | 11 / 19 | 15 / 52 | 27 / 33 | 46 / 78 | 59.4 fps, p95 16.8, max 49.9, dropped 3/281 |
| 1611 (f435ab2) | ipad820x1180 | 1.60 / 7.83 | 3.67 / 13.35 | 931 | 993 | 650 | 135 | 59 / 112 (cold 112) | 79 / 87 (cold 36) | 14 / 21 | 16 / 29 | 32 / 43 | 50 / 84 | 57.3 fps, p95 16.8, max 66.7, dropped 10/210 |

Raw JSON: raw/b<build>-live-<viewport>.json (per-try latencies, top-10 resources, notes).

1579 run (2026-10-18 13:11-13:27 EDT, load avg 1-4, same tools/baseline.py, unchanged selectors): every selector above still resolves on 1579 (thumbnails, list layout, chart menu and institution field changed in 1576-1579 but `li.la-row`, `#lyrRow .lbtn[data-k=ushouse]`, `#chartBox .copts button[data-ch=line]` in the 2020>2024 range, `#listView .lvrow.la`/.nmx PA, `#bBack`, `#ysl .tk` all found; 0 notes, 0 page errors). iPad was run twice: run 1 (raw/b1579-live-ipad820x1180-run1.json) recorded a 2.8 ms first US House pick, a known harness artefact (also seen once each in 1575/1576 later tries) that loses the cold sample, so the row uses run 2. Run 1 for reference: DCL 1377, first map 1109, longest task 183, All States 162 / 208 (cold 208), US House 126 / 175, back 100 / 176, pan 47.9 fps, 65 dropped.

## Top 10 resources, PA session, build 1575 / 1579 (same at every viewport)
| resource | gz KB | raw KB |
|---|---|---|
| v2/index.html | 915 (1579: 921) | 5,920 (1579: 5,938) |
| data/Pennsylvania.js (v1 state file) | 870 | 2,349 |
| v2/data/precincts2024/Pennsylvania.js | 761 | 2,220 |
| v2/data/uscounties.js | 384 | 1,044 |
| v2/data/uscd.js | 228 | 615 |
| v2/data/ctryshape.js | 57 | 196 |
| lib/leaflet.js | 43 | 148 |
| v2/data/election2020.js | 47 | 138 |
| v2/data/election2024.js | 47 | 138 |
| v2/data/usstates.js | 49 | 123 |

ussch.js (4.6 MB) and data/precincts2024/Alaska.js (3.7 MB) are **not** fetched in a PA session on 1575: ussch.js only loads for the School districts type (loadDS), Alaska precincts only when Alaska is one of <=4 states in view. index.html is 5.9 MB because PACK (4.18 MB lists) and XREF (1.09 MB) are inline. 1579: list unchanged; only index.html grew (+6 KB gz / +18 KB raw), request count 77-80 -> 78-79 (small files outside the top 10; the 1576 v2/data/points loader is the only new data URL in the diff). Totals 1.58 / 7.78 MB initial, 3.65 / 13.30 MB PA session.

## vs open bugs (build 1575, Chromium)
- QA-007 All States (238-380 ms): **still reproduces on the first tap** (cold 233-334 ms), later taps median 82-150 ms. Within the old range, so not a regression.
- QA-007 US House pick (205-528 ms): **still reproduces on the first tap** (cold 299-372 ms, measured inside the PA counties list), later picks median 81-96 ms.
- QA-041 Line pick (126-277 ms): **not reproduced**. 18-20 ms median, max 35 ms at all 4 sizes. Looks fixed by 1573-1575; QA should confirm in WebKit.
- Also slow: first back is 215-241 ms at 375/320. iPad pan drops 82 of 241 frames.
- No earlier qa/perf data on any perf/ branch, so this is the first baseline row. Nothing to diff against yet.

## Prototype rows (local copy of 7a23208, see PROPOSALS.md)
| variant | viewport | DCL | first map | All States cold / median | US House cold / median | repeat-visit PA bytes after a build bump |
|---|---|---|---|---|---|---|
| A (as shipped) | 390x844 | 1013 | 777 | 250 / 122 | 336 / 85 | 3.21 MB |
| B (pack.js + JSON.parse) | 390x844 | 347 | 492 | - | - | - |
| C (B + data version URLs) | 390x844 | 357 | 570 | - | - | 0.20 MB |
| D (deferred fit + pointInItem loop) | 390x844 | - | - | 87 / 53 | 303 / 87 | - |
| A | 320x568 | - | - | 230 / 78 | 313 / 95 | - |
| D | 320x568 | - | - | 86 / 50 | 139 / 99 | - |

## 1576 vs 1575 (live, Chromium, same method; box load 2-5, so ±30% noise)
- Bytes are the same: 1.57 MB initial, 3.64 MB PA session, same top 10 files.
- Startup is mixed and probably noise. 390: DCL 1155 -> 930, first map 787 -> 630 (better). 320: DCL 690 -> 1044, first map 697 -> 990 (worse). 375: DCL 549 -> 845. iPad: DCL 1417 -> 1158. If 320/375 stay high on the next build, treat it as a regression.
- Taps are the same within noise. All States cold 190-270 ms (1575: 233-334). US House pick cold 272-374 ms (299-372). Line 8-21 ms median. Drill 14-18 ms. First Back 278 ms at 375 (1575: 241). Time step median 49-64 ms.
- Pan: iPad 47 fps, 60 dropped of 226 frames (1575: 45 fps, 82 of 241). Phones 59-60 fps.
- No regression above noise. QA-007 (first All States / US House) still reproduces. QA-041 (Line) still fixed.

## 1579 (479deb7) vs 1575 (7a23208)
Noise is about +/-30%. Medians compared with medians, cold (first try) with cold.
- **Regression: US House pick** median 96/81/89/93 -> 131/131/123/128 ms (390/375/320/iPad; +35/+63/+38/+38%), now over 100 ms at every size (was under). Cold 299/305/315/372 -> 465/271/315/380 (390 +55%, others within noise). Deselect follows: median 58/36/41/42 -> 76/56/65/60. The 1576 run (rows above, raw/b1576-live-*.json) had pick median 102/101/78/81 and deselect 35/43/37/40, so this came in with 1577-1579 (likely 1577: thumbnails reading slot year / 2016-twin lookup / chart-menu rules), not 1576.
- **Regression: back** median 71/59/52/51 -> 92/83/75/91 (+29/+41/+45/+77%); cold 74/241/215/62 -> 253/289/282/86, so the first back is now over 100 ms at 390 too (was 74). 1576: 53/76/46/57.
- Softer (borderline +20-40%, all under 100 ms median): time step 53/54/45/53 -> 65/66/75/72 (320 max 145, was 67); institution menu open 19/18/18/19 -> 23/26/24/25; Line pick 20/18/19/18 -> 25/21/23/22 (max 36). drill PA median within noise, but single spikes 131/142 ms at 375/320 (1575 max 72/56).
- **Startup better or same**: DCL 1155/549/690/1417 -> 785/701/528/1215, first map 787/788/697/1147 -> 697/641/784/764, longest task 208/137/166/214 -> 124/165/125/168 (no code change in the startup path; treat as noise/box load). Bytes +0.4% (index.html +6 KB gz).
- All States: no change beyond noise (median 117/100/82/150 -> 101/105/93/136, cold 334/308/276/233 -> 240/282/263/199).
- Pan: phones 59-60 fps; iPad 44.8 fps / 82 dropped -> 51.4 fps / 42 dropped (run 1: 47.9 / 65), still the weakest.
- Proposals (PROPOSALS.md): **none landed** in 1576-1579. index.html still has `const PACK`/`const XREF` inline (lines 682/687, 5.94 MB raw); still `?v=`+window.BUILD (39 places, was 38: new data/points loader); enter() still ends `layoutSide(); }catch(e){} fit(); }` (line 3730); aggFor (line 1388) still runs inside the pick, no idle warm-up / precomputed table (prototypes E/F not landed either).
- QA-007 All States (238-380 ms): **still reproduces on the first tap** (cold 199-282 ms), median 93-136. QA-007 US House pick (205-528 ms): **still reproduces and got worse** (cold 271-465 ms, median now 123-131 ms vs 81-96). QA-041 Line pick (126-277 ms): **still not reproduced** in Chromium (median 21-25, max 36).

## 1582 (16b1393) vs 1579 (479deb7)
Run 2026-10-18 13:55-14:06 EDT, load avg 2-4.5, same tools/baseline.py and selectors, 0 notes, 0 page errors. 1580-1582 are UI fixes (time slider, thumbnails, candidate icons); the diff has no aggFor / idle warm-up / fit() change, so the US House fix (and patches D/E) is not in yet.
- **Back crossed 100 ms**: median 92/83/75/91 -> 99/90/102/106 ms (390/375/320/iPad); 320 +35% and iPad now over 100 ms (both were under). Cold back 253/289/282/86 -> 283/242/278/134. Trend since 1576 (53/76/46/57): about 2x.
- US House pick slightly better but still above 1576: median 131/131/123/128 -> 102/111/100/116 (1576: 102/101/78/81); cold 465/271/315/380 -> 260/333/242/347. Deselect 77/57/65/61 -> 51/54/53/58.
- Same within noise: All States median 96/94/74/146 (cold 191-261), time step 54-69, drill PA 13-16 (no spikes, max 87 iPad), Line pick 15-19 median (max 33; QA-041 still not reproduced), institution menu 20-26.
- Startup same or better: DCL 756/714/796/629, first map 677/651/620/638, longest task 108-167. Bytes +0.2% (1.58 / 7.79 MB initial, 3.65 / 13.31 MB PA session).
- Pan: phones 59.6-60 fps; iPad 44.5 fps, 73 of 209 dropped (1579: 51.4 / 42; within the 1575-1579 range of 45-51).
- Proposals: none landed. PACK/XREF still inline (lines 686/691), ?v=+BUILD in 43 places, enter() still ends with a synchronous fit() (line 3755).

## 1584 (ae92b92) vs 1582 (16b1393) and 1576 (615fa5a)
Run 2026-10-18 14:55-15:13 EDT, same tools/baseline.py. Box load 4-9, except a spike to 80+ from other jobs at 15:02-15:06: the first 375 and 320 runs crashed (Target crashed) and were rerun at load 5-8.5; the iPad run ran during the spike, so its startup numbers (first map 993, load 1255) are not trustworthy. 1583 is the WebKit back-chevron fix; 1584 is the speed build (patch E idle aggFor warm-up, patch D deferred fit, rowOf map, chartDim class instead of body:has).
- **US House pick fixed, better than 1576**: median 74/72/68/69 ms (390/375/320/iPad; 1582: 102/111/100/116, 1576: 102/101/78/81). Worst pick (first tap) 122/94/76/74 (1582: 260/333/242/347, 1576: 346/272/374/353). Deselect 51/41/42/44.
- **Back fixed, better than 1576**: median 46/43/44/49 (1582: 99/90/102/106, 1576: 53/76/46/57), max 52/49/58/64 (1582: 283/242/278/134).
- **All States much faster**: median 37/37/44/34 (1582: 96/94/74/146), first tap 118/104/93/117 (1582: 232/237/261/191).
- Time step median 51/41/42/44 (1582: 57/66/54/69). Line pick and drill-in within noise (drill 390 median 28 vs 16, max 32, under 100 ms).
- Bytes +0.2% (index.html +2.4 KB gz). Startup within noise at phones (DCL 801/458/750, first map 585/644/574). Pan unchanged (phones 59-60 fps, iPad 47 fps, 61 dropped of 222).
- Proposals: **#3 (deferred fit, patch D) and #4 (aggFor idle warm-up, patch E) landed**. #1 (PACK/XREF out of index.html, still 5.95 MB raw) and #2 (data versioned by content; window.BUILD still 47 refs) not landed.
- QA-007 All States (238-380 ms): **no longer reproduces** (first tap 93-118 ms). QA-007 US House pick (205-528 ms): **no longer reproduces** (first tap 74-122 ms, median 68-74). QA-041 Line pick: still fixed (median 11-17). Worth WebKit confirmation by QA.

## 1585 (5a0df17) vs 1584 (ae92b92)
Run 2026-10-18 16:50-17:05 EDT, load avg 0.4-4.5 (other bots' browsers running), same tools/baseline.py and selectors (0 notes, 0 page errors). 1585 is a chart/thumbnail layout build with no speed changes. Medians vs medians (390/375/320/iPad).
- Taps all within noise. All States 37/37/44/34 -> 39/44/35/44, first tap 118/104/93/117 -> 83/93/91/91. US House pick 74/72/68/69 -> 69/65/87/74 (320 +28%, still under 100). Back 46/43/44/49 -> 34/36/36/45. Time step 51/41/42/44 -> 48/42/41/44. Line 17/15/24/22, drill 13-15.
- iPad run 1 had one US House pick at 133 ms (first tap; 1584: 55). An iPad rerun (raw/b1585-live-ipad820x1180-run2.json) had picks 66/91/90/82/97 and All States 116 then 38-46, back 35-63, so the 133 was noise, not a regression.
- Startup within noise: DCL 801/458/750/576 -> 672/669/445/1046, first map 585/644/574/993 -> 810/671/554/638 (iPad 1584 was during a load spike; rerun first map 755). Bytes unchanged at 1.59 MB gz initial, 3.66 MB PA session.
- Pan: phones 59.6-59.8 fps; iPad 47.1 fps / 61 dropped -> 43.6-43.7 fps / 79-82 dropped (back to 1575 level, within noise; iPad pan is still the weakest spot).
- Proposals: nothing new landed (#1 PACK/XREF still inline, #2 content versioning not landed). QA-007 and QA-041 still not reproduced.


## 1588 (5a7711c) vs 1585 (5a0df17)
Run 2026-10-18 18:49-19:01 EDT, load avg 0.7-2.0 (QA bot's browser running alongside), same tools/baseline.py and selectors (0 notes, 0 page errors). 1586-1588 are chart, menu, list-sort and thumbnail builds with no speed changes; 1588 is the newest, 1586/1587 were not measured separately. Medians vs medians (390/375/320/iPad).
- Bytes: 1.59 / 7.81 MB initial and 3.66 / 13.34 MB PA session (+0.01 MB raw), flat.
- Taps flat or slightly better: All States 39/33/45/36 (1585: 39/44/35/44), US House pick 72/68/68/61 (69/65/87/74), Line 14/14/14/12 (17/15/24/22), back 39/36/35/43 (34/36/36/45), time step 47/40/43/49 (48/42/41/44). Every median under 100 ms; maxes over 100 only on cold or single tries (390 US House one 121 ms try; iPad All States cold 155 ms, 1584 cold 117, 1582 cold 191), within the usual spread.
- First map 974/911/674/689 ms (1585: 810/671/554/638); 375x667 is +36%, just past the +/-30% band, but within the 620-1147 ms range seen since 1575 and DCL/load were flat or faster, so treated as noise, not a regression. Pan unchanged (60 fps phones, iPad 47.7 fps, 55 dropped).
- No proposal landed in 1586-1588; QA-007 and QA-041 remain fixed-looking (All States median 33-45 ms, Line 12-14 ms).


## 1595 (c34d398) vs 1588 (5a7711c)
Run 2026-10-18 20:52-21:04 EDT, load avg 0.6-2.1, same tools/baseline.py and selectors (0 notes, 0 page errors). 1589-1595 are 2016 colours, list header/sort chip, name alignment, top-flush, range bars and state outline builds with no speed changes; 1595 is the newest, 1589-1594 were not measured separately. Medians vs medians (390/375/320/iPad).
- Bytes: 1.59 / 7.81 MB initial and 3.66 / 13.34 MB PA session, flat (the on-demand 2016 district file from 1589 is not in the default 2024 PA session). index.html still 5.97 MB raw.
- Taps flat: All States 34/46/32/44 (1588: 39/33/45/36), US House pick 70/74/86/67 (72/68/68/61), Line 15/22/18/24 (14/14/14/12), drill PA 13/27/15/14, back 33/36/41/40 (39/36/35/43), time step 46/41/42/46 (47/40/43/49). Every median under 100 ms. Maxes over 100 only on single tries: 320 US House one 127 ms try (cold 47), iPad All States cold 130 ms (1588 cold 155).
- First map 669/557/565/891 ms (1588: 974/911/674/689), phones faster; iPad +29% (inside the band and the 638-1147 ms range since 1575), iPad DCL 459 -> 1067 and long tasks 720 ms total is a single-run outlier pattern seen before (1575 DCL 1417, 1579 1215), so noise, not a regression. Pan unchanged (phones 59.6-60 fps, iPad 47.9 fps, 55 dropped).
- No proposal landed (PACK still inline, no data versioning); QA-007 and QA-041 still look fixed.

## 1611 (f435ab2) vs 1595 (c34d398)
Run 2026-10-19 08:51-09:09 EDT, load avg 0.5-1.9 (other bots' Chromium/WebKit tests running alongside), same tools/baseline.py and selectors (0 notes, 0 page errors). 1596-1611 are list, DC, school-district, address-search and Back-speed builds; 1611 is the newest, 1596-1610 were not measured separately. Medians vs medians (390/375/320/iPad).
- Bytes: 1.60 / 7.83 MB initial and 3.67 / 13.35 MB PA session (+0.01 gz, +0.02 raw), flat. index.html 5.99 MB raw; PACK/XREF still inline.
- Back is faster (1608 QA-020: list re-entry within a frame, hidden map move and focus outline deferred): 27/23/27/32 ms (1595: 33/36/41/40).
- iPad pan improved: 57.3 fps, 10 dropped (1595: 47.9 fps, 55 dropped; 43-48 fps since 1575). Phones unchanged at 59.2-59.6 fps.
- Other taps flat: All States 35/44/40/59 (34/46/32/44; iPad +33% but max 112 vs cold 130 before), US House pick 75/74/114/79 (70/74/86/67), Line 16/18/11/14, drill PA 16/16/15/16, time step 49/56/46/50. The 320 US House median of 114 ms (tries 54/78/147/114/213) did not reproduce: rerun raw/b1611-live-320x568-run2.json gave 50/70/71/98/83, median 71, so noise, not a regression.
- First map 929/642/624/650 ms (1595: 669/557/565/891). 390 is +39% but its TTFB was 147 ms (others 59-63), so network noise, inside the 557-1147 ms range since 1575; iPad -27%.
- No proposal landed (PACK still inline, no data versioning); QA-007 and QA-041 still look fixed.
| 1613 (81be4c7) | 390x844 | 1.60 / 7.84 | 3.67 / 13.37 | 831 | 860 | 588 | 167 | 42 / 95 (cold 95) | 87 / 133 (cold 38) | 17 / 18 | 14 / 24 | 25 / 34 | 53 / 75 | 59.8 fps, p95 16.8, max 33.3, dropped 1/278 |
| 1613 (81be4c7) | 375x667 | 1.60 / 7.84 | 3.67 / 13.36 | 461 | 745 | 572 | 117 | 46 / 106 (cold 106) | 80 / 96 (cold 57) | 17 / 34 | 13 / 20 | 28 / 33 | 52 / 108 | 59.8 fps, p95 16.7, max 33.3, dropped 1/280 |
| 1613 (81be4c7) | 320x568 | 1.60 / 7.84 | 3.67 / 13.35 | 480 | 707 | 697 | 106 | 52 / 171 (cold 104) | 75 / 88 (cold 55) | 16 / 18 | 25 / 30 | 30 / 30 | 54 / 87 | 60.0 fps, p95 16.8, max 16.8, dropped 0/279 |
| 1613 (81be4c7) | ipad820x1180 | 1.60 / 7.84 | 3.67 / 13.35 | 1035 | 1078 | 718 | 148 | 56 / 137 (cold 137) | 90 / 109 (cold 86) | 16 / 35 | 18 / 31 | 38 / 60 | 62 / 190 | 53.8 fps, p95 33.3, max 100, dropped 24/207 |
| 1615 (6dfa3f1) | 390x844 | 1.60 / 7.85 | 3.67 / 13.37 | 799 | 1170 | 962 | 141 | 61 / 102 (cold 102) | 96 / 158 (cold 70) | 25 / 28 | 13 / 17 | 28 / 33 | 51 / 92 | 59.6 fps, p95 16.8, max 33.3, dropped 2/279 |
| 1615 (6dfa3f1) | 375x667 | 1.60 / 7.85 | 3.67 / 13.37 | 714 | 971 | 788 | 130 | 40 / 111 (cold 111) | 82 / 106 (cold 72) | 18 / 25 | 13 / 18 | 26 / 36 | 55 / 88 | 60.0 fps, p95 16.7, max 16.8, dropped 0/279 |
| 1615 (6dfa3f1) | 320x568 | 1.60 / 7.85 | 3.67 / 13.36 | 856 | 898 | 807 | 131 | 48 / 150 (cold 150) | 80 / 93 (cold 73) | 15 / 17 | 12 / 44 | 30 / 38 | 49 / 124 | 59.8 fps, p95 16.8, max 33.4, dropped 1/279 |
| 1615 (6dfa3f1) | ipad820x1180 | 1.60 / 7.85 | 3.67 / 13.37 | 1161 | 1213 | 1021 | 218 | 46 / 149 (cold 149) | 80 / 85 (cold 63) | 17 / 30 | 26 / 45 | 26 / 53 | 52 / 101 | 57.3 fps, p95 16.8, max 66.6, dropped 10/210 |

## 1615 (6dfa3f1) vs 1613 (81be4c7)
Run 2026-10-19 12:51-13:05 EDT, load avg 0.9-3.4 (other bots' Chromium/WebKit tests alongside), same tools/baseline.py and selectors. 1614 (QA-098 list thumbnails) and 1615 (QA-003 official certified state totals, QA-104 county layer on reload) have no speed changes; 1614 was not measured separately. Medians vs medians (390/375/320/iPad).
- Bytes: 1.60 / 7.85 MB initial and 3.67 / 13.37 MB PA session (+4.5 KB gz, +9 KB raw for the official state totals), flat.
- Taps flat, every median under 100 ms: All States 61/40/48/46 (1613: 42/46/52/56; 390 +45% but max 102 = cold try), US House pick 96/82/80/80 (87/80/75/90), Line 25/18/15/17 (17/17/16/16), drill PA 13/13/12/26, back 28/26/30/26, time step 51/55/49/52. Maxes over 100 only on cold first tries (All States cold 102-150, 1613 cold 95-137) and one 390 US House try of 158 ms.
- First map 962/788/807/1021 ms (1613: 588/572/697/718). 390 and 375 had slow TTFB (315 and 209 ms vs 63-74 before), so network noise; iPad rerun (raw/b1615-live-ipad820x1180-run2.json, TTFB 68) gave 617 ms, DCL 858, longest task 120, so the first iPad run (TTFB 142, longest task 218) was noise, not a regression. All values inside the 557-1147 ms range since 1575.
- iPad pan 57.3 fps, 10 dropped (1613: 53.8 fps, 24 dropped); phones 59.6-60 fps.
- No proposal landed (PACK/XREF still inline, no data versioning); QA-007 and QA-041 still look fixed.
| 1617 (bc9bb19) | 390x844 | 1.60 / 7.85 | 3.67 / 13.37 | 895 | 978 | 687 | 138 | 44 / 93 (cold 93) | 71 / 104 (cold 67) | 25 / 30 | 15 / 59 | 22 / 30 | 49 / 76 | 60.0 fps, p95 16.8, max 16.8, dropped 0/280 |
| 1617 (bc9bb19) | 375x667 | 1.60 / 7.85 | 3.67 / 13.37 | 667 | 674 | 616 | 103 | 39 / 97 (cold 97) | 77 / 89 (cold 55) | 14 / 24 | 12 / 14 | 34 / 68 | 46 / 84 | 60.0 fps, p95 16.7, max 16.8, dropped 0/279 |
| 1617 (bc9bb19) | 320x568 | 1.60 / 7.85 | 3.67 / 13.37 | 697 | 703 | 651 | 111 | 40 / 139 (cold 139) | 99 / 117 (cold 49) | 22 / 34 | 14 / 27 | 33 / 45 | 50 / 81 | 59.2 fps, p95 16.7, max 83.3, dropped 4/279 |
| 1617 (bc9bb19) | ipad820x1180 | 1.60 / 7.85 | 3.67 / 13.37 | 1094 | 1140 | 852 | 176 | 60 / 105 (cold 105) | 69 / 74 (cold 60) | 17 / 19 | 15 / 16 | 25 / 48 | 53 / 81 | 52.7 fps, p95 33.3, max 50, dropped 30/215 |

## 1617 (bc9bb19) vs 1615 (6dfa3f1)
Run 2026-10-19 14:50-15:05 EDT, load avg 0.5-4.7 (other bots' Chromium tests alongside), same tools/baseline.py and selectors (0 page errors). 1616 (QA-097 city reload, QA-105/106 precinct labels) and 1617 (QA-107 ZIP selection through the shared path, QA-108 mouse drag moves the single slider knob) have no intended speed changes; 1616 was not measured separately. Medians vs medians (390/375/320/iPad).
- Bytes: 1.60 / 7.85 MB initial and 3.67 / 13.37 MB PA session, flat.
- Time slider open at 320x568 went over 100 ms: 119 ms, and the rerun raw/b1617-live-320x568-run2.json gave 106 ms (one try per run; 1611-1615 at 320: 41/55/49). The other viewports are flat at 36/38/39 (1615: 44/45/70). Possibly the QA-108 slider change at narrow width; worth a profile if it holds next build. Time step itself flat: 49/46/50/53 (1615: 51/55/49/52).
- Other taps flat, every median under 100 ms: All States 44/39/40/60 (1615: 61/40/48/46), US House pick 71/77/99/69 (96/82/80/80; 320 rerun median 81), Line 25/14/22/17, drill PA 15/12/14/15, back 22/34/33/25. Maxes over 100 only on cold first tries (All States cold 93-139) and single US House tries of 104-118 ms.
- First map 687/616/651/852 ms (1615: 962/788/807/1021; 320 rerun 676), faster, inside the 557-1147 ms range since 1575.
- Pan: phones 59.2-60 fps; iPad 52.7 fps, 30 dropped (1615: 57.3, 10 dropped) with load avg 4.7 during that run, same as 1613's 53.8, so noise.
- No proposal landed (PACK/XREF still inline, no data versioning); QA-007 and QA-041 still look fixed.
| 1618 (581534c) | 390x844 | 1.61 / 7.85 | 3.67 / 13.37 | 671 | 1039 | 829 | 143 | 34 / 97 (cold 97) | 80 / 86 (cold 62) | 16 / 18 | 24 / 27 | 23 / 50 | 57 / 115 | 60.0 fps, p95 16.8, max 16.8, dropped 0/277 |
| 1618 (581534c) | 375x667 | 1.61 / 7.85 | 3.68 / 13.37 | 458 | 686 | 533 | 101 | 62 / 106 (cold 106) | 72 / 104 (cold 60) | 12 / 17 | 12 / 22 | 29 / 33 | 52 / 79 | 59.8 fps, p95 16.7, max 33.3, dropped 1/277 |
| 1618 (581534c) | 320x568 | 1.61 / 7.85 | 3.68 / 13.37 | 653 | 658 | 612 | 98 | 35 / 90 (cold 90) | 76 / 94 (cold 57) | 17 / 27 | 15 / 21 | 27 / 67 | 45 / 81 | 60.0 fps, p95 16.8, max 16.8, dropped 0/279 |
| 1618 (581534c) | ipad820x1180 | 1.61 / 7.85 | 3.68 / 13.38 | 831 | 934 | 754 | 125 | 52 / 116 (cold 116) | 72 / 78 (cold 57) | 17 / 20 | 12 / 34 | 23 / 25 | 52 / 99 | 55.5 fps, p95 16.8, max 66.7, dropped 17/208 |

## 1618 (581534c) vs 1617 (bc9bb19)
Run 2026-10-19 16:54-17:06 EDT, load avg 1.1-3.5 (other bots' Chromium/WebKit tests alongside), same tools/baseline.py and selectors (0 page errors). 1618 (QA-111 heat after district-type deselect, geo-filter clears district type, QA-109 field names picked place, QA-110 state above same-name country) has no intended speed change. Medians (390/375/320/iPad).
- Bytes: 1.61 / 7.85 MB initial and 3.67-3.68 / 13.37 MB PA session, flat (index.html 6.01 MB raw).
- Time slider open at 320x568 back to 36 ms (1617: 119, rerun 106), so 1617's jump was noise or load. Other viewports 26/30/37 (1617: 36/38/39). Time step 57/52/45/52, flat.
- Taps, every median under 100 ms: All States 34/62/35/52 (1617: 44/39/40/60; 375 up but within noise and well under 100), US House pick 80/72/76/72 (71/77/99/69), Line 16/12/17/17, drill PA 24/12/15/12, back 23/29/27/23. Maxes over 100 only on cold first tries (All States cold 90-116) and one US House try of 104 ms.
- First map 829/533/612/754 ms (1617: 687/616/651/852), inside the usual range.
- Pan: phones 59.8-60 fps; iPad 55.5 fps, 17 dropped (1617: 52.7, 30 dropped).
- No proposal landed (PACK/XREF still inline, no data versioning); QA-007 and QA-041 still look fixed.
| 1620 (09b6cd9) | 390x844 | 1.61 / 7.86 | 3.68 / 13.38 | 565 | 933 | 669 | 188 | 45 / 84 (cold 84) | 80 / 105 (cold 40) | 18 / 21 | 10 / 26 | 34 / 47 | 48 / 84 | 60.0 fps, p95 16.8, max 16.8, dropped 0/286 |
| 1620 (09b6cd9) | 375x667 | 1.61 / 7.86 | 3.68 / 13.38 | 495 | 735 | 575 | 112 | 50 / 106 (cold 106) | 82 / 151 (cold 43) | 14 / 23 | 25 / 28 | 27 / 31 | 42 / 75 | 60.0 fps, p95 16.7, max 16.8, dropped 0/278 |
| 1620 (09b6cd9) | 320x568 | 1.61 / 7.86 | 3.68 / 13.38 | 571 | 853 | 803 | 136 | 44 / 75 (cold 75) | 67 / 114 (cold 39) | 15 / 19 | 12 / 16 | 28 / 48 | 42 / 63 | 60.0 fps, p95 16.7, max 16.8, dropped 0/278 |
| 1620 (09b6cd9) | ipad820x1180 | 1.61 / 7.86 | 3.68 / 13.38 | 445 | 800 | 574 | 116 | 37 / 90 (cold 90) | 68 / 91 (cold 33) | 13 / 28 | 24 / 32 | 27 / 30 | 48 / 70 | 59.0 fps, p95 16.7, max 33.4, dropped 4/224 |

## 1620 (09b6cd9) vs 1618 (581534c)
Run 2026-10-25 16:57-17:20 EDT, load avg 1.0-5.2 (other bots' Chromium/WebKit tests alongside), same tools/baseline.py and selectors (0 notes, 0 page errors). Live v2 served BUILD 202610251620, byte-identical to main 09b6cd98. 1619 (QA-113/115/116 search fixes; #bGeo sheet entry of an exact place resolves like the bottom field) and 1620 (QA-119/121, QA-124/126 place-membership gate: a precinct named for another town of the county counts under that town) have no intended speed change; 1619 was not measured separately. Medians (390/375/320/iPad).
- Bytes: 1.61 / 7.86 MB initial and 3.68 / 13.38 MB PA session (+3 KB gz, +9 KB raw), flat. index.html 6.02 MB raw.
- Taps flat, every median under 100 ms: All States 45/50/44/37 (1618: 34/62/35/52), US House pick 80/82/67/68 (80/72/76/72), Line 18/14/15/13 (16/12/17/17), drill PA 10/25/12/24 (24/12/15/12; 12-26 ms swings seen since 1613), back 34/27/28/27 (23/29/27/23), time step 48/42/42/48 (57/52/45/52), time slider open 29/25/24/31 (26/30/36/37). Maxes over 100 only on the cold All States try at 375 (106) and single US House tries of 105/151/114 ms (390/375/320).
- 390 (All States +32%, back +48%, longest task 188) and 320 (first map 803, +31%; longest task 136) were rerun (raw/b1620-live-390x844-run2.json, raw/b1620-live-320x568-run2.json) at lower load: 390 All States 30, back 24, US House 66, first map 500, longest task 110; 320 All States 33, US House 63, first map 531, longest task 206 (one load-time task; first run 136). So noise, not a regression.
- Startup: DCL 565/495/571/445 (1618: 671/458/653/831), first map 669/575/803/574 (829/533/612/754), inside the usual range.
- Pan: phones 60 fps, 0 dropped; iPad 59.0 fps, 4 dropped (1618: 55.5, 17 dropped).
- /workspace/perf/perf.py (390, 4x CPU throttle, 1 round, raw/b1620-live-perfpy.json): glass/no-glass taps #bNum 22/17, #bTime 29/26, #bLyr 22/17 ms; map pan+pinch 41/39 fps; list scroll 59.8/59.3 fps (436 rows); list sort 73/75 ms (perf1.log on 1575: 410-450 ms).
- No proposal landed: PACK/XREF still inline in index.html, data still versioned by window.BUILD (50 refs), ussch.js and precincts2024/Alaska.js still lazy (not fetched in a PA session), index.html not trimmed. QA-007 (All States, US House pick) and QA-041 (Line pick) still look fixed.

| 1621 (844c703) | 390x844 | 1.61 / 7.86 | 3.68 / 13.38 | 542 | 718 | 661 | 115 | 44 / 82 (cold 82) | 73 / 127 (cold 43) | 12 / 24 | 18 / 19 | 24 / 28 | 45 / 66 | 60.0 fps, p95 16.7, max 16.8, dropped 0/279 |
| 1621 (844c703) | 375x667 | 1.61 / 7.86 | 3.68 / 13.38 | 889 | 906 | 831 | 122 | 50 / 95 (cold 95) | 65 / 86 (cold 43) | 19 / 29 | 13 / 15 | 26 / 30 | 51 / 82 | 60.0 fps, p95 16.8, max 16.8, dropped 0/280 |
| 1621 (844c703) | 320x568 | 1.61 / 7.86 | 3.68 / 13.38 | 504 | 737 | 606 | 95 | 77 / 166 (cold 77) | 78 / 86 (cold 40) | 17 / 27 | 24 / 30 | 23 / 28 | 55 / 73 | 58.1 fps, p95 16.7, max 116.7, dropped 9/281 |
| 1621 (844c703) | ipad820x1180 | 1.61 / 7.86 | 3.68 / 13.38 | 533 | 905 | 839 | 150 | 43 / 203 (cold 203) | 79 / 171 (cold 43) | 24 / 40 | 10 / 51 | 29 / 39 | 57 / 88 | 56.6 fps, p95 16.8, max 99.9, dropped 14/230 |

## 1621 (844c703) vs 1620 (09b6cd9)
Run 2026-10-25 18:52-19:13 EDT, load avg 2.8-9.5 (other bots' Chromium/WebKit tests alongside), same tools/baseline.py and selectors (0 notes, 0 page errors). Live v2 served BUILD 202610251621. 1621 (QA-128 strict town-membership rule, QA-129 geo entry with a district type) has no intended speed change. Medians (390/375/320/iPad).
- Bytes: 1.61 / 7.86 MB initial and 3.68 / 13.38 MB PA session (+1 KB gz, +2 KB raw), flat.
- Taps, every median under 100 ms: All States 44/50/77/43 (1620: 45/50/44/37), US House pick 73/65/78/79 (80/82/67/68), Line 12/19/17/24 (18/14/15/13), drill PA 18/13/24/10, back 24/26/23/29, time step 45/51/55/57 (48/42/42/48), time slider open 27/29/26/28.
- Startup: first map 661/831/606/839 (1620: 669/575/803/574).
- Pan: 390/375 60 fps, 320 58.1 fps (9 dropped), iPad 56.6 fps (14 dropped; load 9.5 during that run).
- 375, 320 and iPad were rerun (raw/b1621-live2-*.json, load 5.8 at start): 375 first map 510, All States 38; 320 All States 43, first map 802 (1620's first run was also 803), pan 60 fps; iPad first map 680, Line 16, US House 59, pan 59.2 fps. So the first-run outliers (320 All States +75%, 375/iPad first map +45%) were load noise, not a regression.
- /workspace/perf/perf.py (390, 4x CPU throttle, 1 round, raw/b1621-live-perfpy.txt, load 7.2): glass/no-glass taps #bNum 23/132 (no-glass outlier), #bTime 25/38, #bLyr 19/28 ms; map pan+pinch 40/33 fps; list scroll 59.6/59.5 fps (436 rows); list sort 80/85 ms.
- No proposal landed (bytes unchanged: PACK/XREF still inline, ussch.js and Alaska precincts still lazy, index.html not trimmed). QA-007 and QA-041 still look fixed.
| 1621 (844c703) rerun | 375x667 | 1.61 / 7.86 | 3.68 / 13.39 | 425 | 887 | 510 | 105 | 38 / 89 (cold 89) | 68 / 120 (cold 65) | 16 / 16 | 29 / 42 | 22 / 32 | 44 / 75 | 60.0 fps, p95 16.8, max 16.8, dropped 0/279 |
| 1621 (844c703) rerun | 320x568 | 1.61 / 7.86 | 3.68 / 13.38 | 828 | 841 | 802 | 121 | 43 / 109 (cold 109) | 70 / 106 (cold 48) | 17 / 29 | 19 / 27 | 25 / 27 | 42 / 72 | 60.0 fps, p95 16.7, max 16.8, dropped 0/277 |
| 1621 (844c703) rerun | ipad820x1180 | 1.61 / 7.86 | 3.68 / 13.39 | 438 | 801 | 680 | 122 | 38 / 103 (cold 103) | 59 / 63 (cold 53) | 16 / 27 | 12 / 42 | 23 / 30 | 44 / 71 | 59.2 fps, p95 16.8, max 33.4, dropped 3/221 |
| 1622 (0863b89) | 390x844 | 1.61 / 7.86 | 3.68 / 13.38 | 470 | 721 | 548 | 117 | 37 / 93 (cold 93) | 75 / 93 (cold 44) | 16 / 28 | 15 / 33 | 22 / 48 | 48 / 92 | 60.0 fps, p95 16.8, max 16.8, dropped 0/279 |
| 1622 (0863b89) | 375x667 | 1.61 / 7.86 | 3.68 / 13.38 | 462 | 690 | 551 | 101 | 49 / 93 (cold 93) | 65 / 109 (cold 40) | 14 / 28 | 12 / 25 | 19 / 19 | 54 / 75 | 60.0 fps, p95 16.7, max 16.8, dropped 0/279 |
| 1622 (0863b89) | 320x568 | 1.61 / 7.86 | 3.68 / 13.39 | 438 | 632 | 504 | 92 | 33 / 80 (cold 80) | 67 / 112 (cold 66) | 18 / 20 | 13 / 22 | 21 / 74 | 42 / 76 | 60.0 fps, p95 16.7, max 16.8, dropped 0/278 |
| 1622 (0863b89) | ipad820x1180 | 1.61 / 7.86 | 3.68 / 13.39 | 484 | 899 | 658 | 129 | 40 / 95 (cold 95) | 65 / 76 (cold 44) | 11 / 25 | 12 / 106 | 28 / 50 | 54 / 80 | 58.9 fps, p95 16.7, max 50, dropped 4/217 |

## 1622 (0863b89) vs 1621 (844c703)
Run 2026-10-25 20:53-21:11 EDT, load avg 1.0-2.8 (another bot's WebKit tests alongside), same tools/baseline.py and selectors (0 notes, 0 page errors). Live v2 served BUILD 202610251622, byte-identical to main 0863b89c. 1622 (QA-131 United States + Enter returns to the US; 3-line index.html change) has no intended speed change. Medians (390/375/320/iPad).
- Bytes: 1.61 / 7.86 MB initial and 3.68 / 13.38-13.39 MB PA session (+1.3 KB raw index.html, 6.02 MB), flat.
- Taps flat, every median under 100 ms: All States 37/49/33/40 (1621: 44/50/77/43), US House pick 75/65/67/65 (73/65/78/79), Line 16/14/18/11 (12/19/17/24), drill PA 15/12/13/12 (18/13/24/10), back 22/19/21/28 (24/26/23/29), time step 48/54/42/54 (45/51/55/57), time slider open 32/34/24/32 (27/29/26/28). Maxes over 100 only on single US House tries of 109/112 ms (375/320) and one iPad drill PA try of 106 ms.
- 390 Line (16 vs 12, +33%, 4 ms) was rerun (raw/b1622-live2-390x844.json, load 1.6): Line 16, All States 33, US House 68, first map 541. Line 16 matches 1620's 18, so within noise, not a regression.
- Startup: DCL 470/462/438/484 (1621: 542/889/504/533), first map 548/551/504/658 (661/831/606/839), longest task 117/101/92/129 (115/122/95/150); faster with lower load, inside the usual range.
- Pan: phones 60 fps, 0 dropped; iPad 58.9 fps, 4 dropped (1621: 56.6, 14 dropped).
- /workspace/perf/perf.py (390, 4x CPU throttle, 1 round, raw/b1622-live-perfpy.txt, load 1.6): glass/no-glass taps #bNum 17/20, #bTime 33/34, #bLyr 25/20 ms; map pan+pinch 42/37 fps; list scroll 59.7/59.9 fps (436 rows); list sort 82/77 ms.
- No proposal landed (PACK/XREF still inline in index.html, data still versioned by window.BUILD, ussch.js and Alaska precincts still lazy, index.html not trimmed). QA-007 and QA-041 still look fixed.
| 1622 (0863b89) rerun | 390x844 | 1.61 / 7.86 | 3.68 / 13.38 | 447 | 715 | 541 | 124 | 33 / 107 (cold 107) | 68 / 101 (cold 61) | 16 / 33 | 11 / 19 | 22 / 32 | 45 / 84 | 60.0 fps, p95 16.8, max 16.8, dropped 0/279 |
