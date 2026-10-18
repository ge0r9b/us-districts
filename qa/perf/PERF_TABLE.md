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

Raw JSON: raw/b1575-live-<viewport>.json (per-try latencies, top-10 resources, notes).

## Top 10 resources, PA session, build 1575 (same at every viewport)
| resource | gz KB | raw KB |
|---|---|---|
| v2/index.html | 915 | 5,920 |
| data/Pennsylvania.js (v1 state file) | 870 | 2,349 |
| v2/data/precincts2024/Pennsylvania.js | 761 | 2,220 |
| v2/data/uscounties.js | 384 | 1,044 |
| v2/data/uscd.js | 228 | 615 |
| v2/data/ctryshape.js | 57 | 196 |
| lib/leaflet.js | 43 | 148 |
| v2/data/election2020.js | 47 | 138 |
| v2/data/election2024.js | 47 | 138 |
| v2/data/usstates.js | 49 | 123 |

ussch.js (4.6 MB) and data/precincts2024/Alaska.js (3.7 MB) are **not** fetched in a PA session on 1575: ussch.js only loads for the School districts type (loadDS), Alaska precincts only when Alaska is one of <=4 states in view. index.html is 5.9 MB because PACK (4.18 MB lists) and XREF (1.09 MB) are inline.

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
