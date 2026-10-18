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
| HTML TTFB (CDN hit) | ≤ 50 ms p75 (US) | RUM / Vercel Speed Insights |
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
