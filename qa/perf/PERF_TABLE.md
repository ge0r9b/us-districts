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
