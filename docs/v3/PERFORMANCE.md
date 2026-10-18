# v3 performance budget (Phase 1)

**Instant response time is the top priority in every UI change** (REPO-RULES rule 7). v2 already has budgets that v3 must match or beat: build 1564 "instant taps" (sort flip moves existing rows, no rebuild), build 1567 "drill-in answers at once (cached or skeleton rows painted in ~15–50 ms at 4× CPU)", and build 1560 "no jumps on load (CLS 0.086/0.161 → 0)". The roadmap's next v2 item is "time slider < 150 ms to first visible response" (coordinator note, not yet in the repo).

## Budget (measured on iPhone-class hardware: Playwright WebKit 390×780 with 4× CPU throttle, plus a real iPhone before release)
| Metric | Target | How it is measured |
|---|---|---|
| Tap → first visible response (any control) | **≤ 50 ms p75, ≤ 100 ms p95** (INP) | Playwright `performance.now()` around the tap until the DOM or canvas changes (port v2 `drill-instant.py`, `no-jump.py`) |
| Time slider move → map and list recoloured | **≤ 100 ms** (beats v2's 150 ms goal) | feature-state update + row refill of visible rows only |
| Sort flip, %/# toggle, answer toggle | **≤ 1 frame (16 ms)** after input, no network | local data only |
| Drill-in (tap row → child list painted) | ≤ 50 ms with prefetched pack; skeleton within 16 ms otherwise | prefetch child packs on row hover/touchstart |
| Layout shift | **CLS = 0**, no fades, no jumps (HANDOFF §3) | port `load-stable.py`, `list-scroll-stay.py` |
| HTML TTFB (CDN hit) | ≤ 50 ms p75 (US) | RUM (Cloudflare Web Analytics on Pages, or a small `PerformanceObserver` beacon) |
| First map paint (LCP) on 4G | ≤ 1.5 s | Lighthouse mobile |
| JS shipped before first paint | ≤ 300 KB gzip including MapLibre (≈ 220 KB); app code ≤ 80 KB | bundle report in CI (fails the build if over) |
| Result pack (all counties, one contest) | ≤ 25 KB gzip | build-time check |
| Precinct pack per state | ≤ 150 KB gzip (largest states may be split by county) | build-time check |
| Vector tile | ≤ 200 KB gzip each, median ≤ 50 KB | tippecanoe `--maximum-tile-bytes` |
| API p95, CDN hit | ≤ 50 ms | synthetic checks |
| API p95, origin, DB warm | ≤ 150 ms (search ≤ 80 ms DB time; point-in-polygon ≤ 20 ms DB time) | `EXPLAIN ANALYZE` in CI fixtures plus logs |
| Geocode (Census bound) | ≤ 2.5 s hard timeout; place and ZIP rows instant | GEOCODER.md |

## How the budget is met
1. **No network on the interaction path.** Packs for the selected contest(s) and the visible unit types are already in memory. Year, %/#, answer toggle and sort operate on typed arrays. Network fetches are prefetches (next zoom level, likely drill-ins, the other years for the time slider).
2. **Geometry never re-downloads for a data change.** MapLibre `setFeatureState` recolours existing features. Tiles are immutable and cached (ARCHITECTURE.md §4).
3. **Precomputed everything.** Re-tabulation, aggregates, shares, ranks and parent totals are computed at load time (`unit_contest_agg`, `answer_share`, packs). The API never aggregates raw precincts on request.
4. **Edge caching with versioned URLs.** Packs, tiles and pinned API responses are `immutable`. Only `/manifest` and the HTML have short TTLs.
5. **Lists render only what is visible.** `content-visibility:auto` (as v2 build 1564), row nodes reused on sort (moved, not rebuilt), off-screen rows filled in idle slices.
6. **One state store, no polling.** v2 has about 50 `setInterval` layout syncs plus a 250 ms "quiet window" workaround (build 1564–1565). v3 uses reactive state with a single rAF-batched render. Polling is banned by a lint rule.
7. **Database off the hot path.** Neon scale-to-zero cold starts only affect geocode, search and custom sets. The map and list stay instant even when the database is asleep.
8. **Index-only dynamic queries.** Bar lists come from `answer_share_sorted` (range scan, already in high → low order), and point-in-polygon from a partial GiST index (SCHEMA.md).
9. **Lazy per-year result files (kept from v2).** v2 loads a year's results only when that year is shown (`loadE2020`, `loadPrec20(st)`; 2016 arrives as separate `election2016.js` / `ds2016-*.js` / `precincts2016/` files instead of new row slots). v3 does the same: one pack per contest (= per year) × unit type (× state for precincts). The default 2024 view loads only 2024. The other slider years are prefetched at idle, so a slider tap stays local (v2 Build 1569: 2016 tap ≈ 30 ms).
10. **Performance tests are gates.** Every budget above has a Playwright or CI check. A PR that breaks one does not merge (same discipline as v2's "core tests before any push", HANDOFF §6).

## v2 measured baseline (perf/speed-baseline e6bd50c, Build 1575, Chromium 390×844 DPR 2, no throttle)
The perf lane measured v2 and prototyped four fixes (`qa/perf/PROPOSALS.md`, `PERF_TABLE.md`). These are the numbers v3 has to beat, and each finding maps to a v3 rule above.

| Finding in v2 | Measured | v3 rule |
|---|---|---|
| 5.27 MB of inline object literals (`PACK`, `XREF`) parsed before DOMContentLoaded | moving them to a content-hashed `pack.js` parsed with `JSON.parse`: DCL 1013 → 347 ms, first map 777 → 492 ms | no data inline in HTML; packs are separate content-hashed files (rule 4); JSON packs, not JS literals |
| Every data URL is versioned by `window.BUILD`, which changes on every push | a returning user re-downloads 3.21 MB gz after a build bump; per-file data versions cut it to 198 KB (−94 %) | pack and tile URLs carry the **content hash of that file**, never the app build number; `/manifest` maps names to hashes (ARCHITECTURE.md §4). Add a CI check that an app-only change leaves every data URL unchanged |
| `fitBounds` inside the tap handler re-projects every canvas path | All States cold 250 → 87 ms by fitting after the list paints | paint the list first, move the map in the next frame; camera moves never block the tap's first frame |
| US House pick runs precinct → district point-in-polygon in the tap (239 ms) | not yet fixed in v2 | precinct → district (and every child → parent) membership is precomputed at load (`unit_contest_agg`, rule 3); a pick is a lookup |
| About 60 `setInterval` pollers doing layout reads | source of random tap delay and idle drain | rule 6 (no polling, lint-enforced) stands |
| iPad 820×1180 pan 45 fps, p95 33 ms (phones 57–60 fps) | weakest viewport | add an iPad-size pan check (≥ 55 fps) to the perf gates; MapLibre GL rendering should clear it, but measure |
| Liquid Glass `backdrop-filter` | no measurable tap cost in headless Chromium | keep the glass; re-check on a real iPhone before release |

Port the lane's tools (`qa/perf/tools/baseline.py`, `net.py`, `idle.py`, `prof.py`) as the v3 perf harness so v2 and v3 numbers come from the same scripts at the same viewports.

## v2 re-measure at Build 1579 (perf/speed-baseline 1f8ae1f, Oct 18, 2026 14:00 EDT drift check)
- US House pick regressed in Builds 1577–1579: median 81–96 ms became 123–131 ms (over 100 ms at every viewport), cold up to 465 ms at 390×844; back median 51–71 ms became 75–92 ms, cold first back over 100 ms at 390. The likely cause is tap-time work added in 1577 (thumbnails reading slot year, 2016-twin lookup, chart-menu rules). No perf proposal has landed in v2 (PACK/XREF still inline, `aggFor` still runs in the pick).
- v3 lesson, already in the budget: anything a tap needs (2016 twins, slot-year values, child → parent membership) is precomputed at load and served as a lookup. The v3 Playwright perf gate adds a "US House pick ≤ 100 ms median, ≤ 150 ms cold at 390 with throttle" assertion so this class of regression can't ship.
