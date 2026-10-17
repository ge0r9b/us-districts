# US Districts: HANDOFF (updated at build 202610171534, Oct 17, 2026)

Read this first, then `docs/us-districts-spec.md` (full spec, also as `.docx`) and `v2/data/COVERAGE.md` (data coverage, sources, licenses).

## 1. Purpose and live URL
A static map and results viewer for US elections (President 2020 and 2024, plus state legislatures, US House and school districts where data exists). Users pick an **institution** (top field) and a **geo** (bottom field), see a map or a list, and compare results by bar, line or pie.
- Live: https://ge0r9b.github.io/us-districts/v2/ (GitHub Pages, branch `main`)
- Repo: github.com/ge0r9b/us-districts. App = `v2/index.html`. Data = `v2/data/*.js` (+ `COVERAGE.md`).

## 2. Architecture
- **One file app:** `v2/index.html` (HTML, CSS and about 3,400 lines of JS, Leaflet from `lib/`). No build step. Every change is an edit to this file.
- **Data:** per-state precinct files (`v2/data/<State>.js`), `ELECTION2020/2024` county tables, district summaries (`DS`: US House, state senate/house, school districts), legislative boundary files (`ussldu.js`, `ussldl.js`), town polygons. Results are aggregated into today's (2024) boundaries for every year; estimates are flagged `≈`.
- **Per-country config:** the district-type menu is data-driven per country (US only today; Canada is parked).
- **Key subsystems (search the file for the names):**
  - `LA` list-all machinery: `level()`, `itemsFor()`, `render()`, `rowHtml()`, `enter()/exit()/settle()`, `__laPick`. Row graphics: bars, delta bars (common scale), two-point lines, single-point pie.
  - Chart button (`#chartBox`): bar/pie/line, validity by time selection, auto-switch and restore (`sync`, `okT`).
  - Time filter `yslider` (`ym()` returns "2020", "2024" or "delta"), `numMode` (# or %), sort control `#laSort` (tap flips, bubble `#laSortBub`).
  - Unified search (`unisearch`, `usIndex`), full-screen institution/geo pickers (`openFold`, body class `foldfs`), contextual edit (`ctxEdit`).
  - History stack + back button `#bBack` (push on institution/geo/topic/district-type change; keyboard Backspace/Alt+Left/Cmd+[, browser back via popstate).
  - Persistence: URL hash `#s=<base64url JSON>` + `localStorage usd.state`, versioned `v:1`.
  - iOS Safari guard: an early capture-phase `resize` listener swallows toolbar-only height changes (<120 px).
  - Estimate marking (`est`, `__estRow`, `candLines`) and the Idaho/town area-weighting (`townAreaVals`, `__townAudit`).

## 3. Rules and standing preferences (all user rules, condensed; the spec has the long form)
**Process:** no unrequested changes; push small builds, verify live, test desktop and phone, report with build number and screenshot paths. Destructive git steps need confirmation. **No fades, no layout jumps. No fabricated data** (real sources only; estimates marked ≈; say per item when data cannot be obtained). Keep the NYT credit until NYT data is fully replaced (check OpenElections licence first). 2016 data is prepared offline only. Canada is parked. USA scope only for now.
**Layout:** icon axis x=27, text indent x=52 in all lists and menus (delta list rows: abbreviation about x=44). Flags for countries/states/provinces in the institution field; territorial-shape silhouettes (tiny star for county/town) for places in the geo field. States/countries are *sovereign* governments, counties/cities/towns/townships/boroughs are *incorporated* (never call a state incorporated). Boundaries white with heatmap data, black without. 2024 boundaries for all years. Legend/attribution small, bottom left.
**Lists:** list-all states use two-letter abbreviations (full name on hover/press). Tapping a row keeps list view and view settings and drills down. Values go inside bar segments, never under the floating button column (labels clamp or hide). Delta mode: net value at standard text indent, bar length on one common scale for the whole list, winner thumbnail at the bar's left end, no per-candidate change numbers. List must never jump (scrollTop preserved, identical rebuilds skipped).
**Charts:** single point = bar + pie only; range = bar + line only (no concentric delta pie, no scatter); the button cycles only valid types, auto-switches an invalid type to bar and restores the previous choice. Chart button is dark only when a chart is displayed (inactive style in full-screen map). Line delta labels sit under their line, centred between the two points. Future option, not built: pie of most gains for races with many candidates.
**Sort:** one tap flips direction and shows a small bubble ("High to low"/"Low to high") for about 1.8 s; hidden whenever search/full-screen filter is open or no list is visible; direction persists with view settings.
**Back button:** only exists when the history stack is non-empty; shown in institution/geo filter lists and list views (row under the institution bar, x about 27, under the expanded time filter when it is open).
**District type:** a selected type must show its district list (not the consolidated total) in list view; numbers must equal the map pop-ups (same tallies, same area weighting and ≈ rules); map mode unchanged.

## 4. Status at build 1534
Fixed and live (verified by the tests named; run them yourself, section 6):
| Item | Build | Test |
|---|---|---|
| District-type change re-renders list-all immediately (t223/t224) | 1527 | `type-switch.py` |
| Safari list jumping (t234 and t203): scroll preserved, redundant rebuilds skipped, iOS toolbar resize swallowed, `overscroll-behavior: contain` | 1527 | `scroll-stable.py` (Chromium emulation; **not verified on real iPhone or WebKit**) |
| Back button, keyboard, popstate, history stack (t225–t230) | 1527 | `filter-back.py` |
| Delta sort by |net| as displayed (t272/t273), # bars to scale (t274/t275), Arizona 2020 precincts, `'20 n/a` rows | 1530 | `sort-scale.py` |
| Sort tap-flip + bubble (t229); sort hidden under search/full-screen filter (t239) | 1527 / 1528 | `sort-flip.py` (no dedicated test for t239 yet) |
| Idaho/all-state town rows area-weighted with ≈ instead of "no data" (t231/t232) | 1527 | `idaho-towns.py` |
| No text under floating buttons (t235/t236); delta net/scale layout (t237/t238) | 1528 | `label-clamp.py`, `delta-scale.py` |
| List-all line and pie rows; chart-type rule; chart button in map; line delta labels (t240, t249–t254) | 1528 | `chart-modes-list.py`, `chart-line-single.py` |
| District-type list at national scope: US House nationwide (435 rows); other types list states first | 1528 | `district-list-view.py`, `district-consistency.py` (list values = pop-up values) |
| Alaska and Connecticut 2020, ≈ 2020 for re-drawn 2024 precincts, gray districts filled, Idaho 2024 | 1533 | `data-2020.py`, `est-list.py`, `est-popup.py`, `district-consistency.py` |
| 2024 gray legislative districts from official precinct returns (OK, VT, WY, AR, GA, MO, TN), WI and CA 2024 precinct files rebuilt, 84 gray schools filled | 1534 | all suites in section 6 (data: `district-consistency.py`, `est-list.py`, `est-popup.py`, `data-2020.py`) |
| Unisearch two-row rule, sovereign/incorporated wording, geo silhouettes, editable scope row, ≈ marks in list rows, 12 gray districts filled | 1519–1527 | `unisearch.py`, `ctx-edit.py`, `geo-icons.py`, `est-list.py` |

**Still open / known gaps (be honest about these):**
1. ~~County tier~~ **Done in 1530:** school districts / state house / state senate list as states -> counties -> districts (`distInCounty`, `level()` `dt` flag); a district spanning counties appears under each county it touches, marked ≈. `tests/district-list-view.py` covers it.
2. Safari jumping needs confirmation on a real iPhone; WebKit tests were not run.
3. No dedicated regression test for the sort-under-search bug (t239).
4. Old `tests/list-all-modes.py` delta assertions use class names from before the delta redesign (stale; `delta-scale.py` covers the new layout).
5. **Data gaps (build 1533, details and per-item reasons in COVERAGE.md):** 2020 is now complete at county level (3,112 incl. Connecticut) and at precinct level (every county within 90-110 % of the official total, VEST 2020 CC BY 4.0 replacing failing counties); Alaska 2020 boroughs/House/Senate and Connecticut 2020 towns added (≈ for Alaska, flag `e20`); 99.3 % of 2024 precincts now have a 2020 side (exact same-shape, else ≈ area-weighted from `v2/data/x20/<State>.js`, tool `tools/build_x20.py`); gray districts filled by area-weighting with county scaling (`tools/fill_gray.py`, flags `e20`/`e24`/`est`); Idaho 2024 Owyhee and Idaho County from the official SOS workbook (`tools/fix_id2024.py`). **Still gray:** 2024 senate 8, house 33 (OK, VT, WY mostly), schools 174; 2020 schools 26 (AK 14). Cause: 2024 precinct polygons cover too little of those districts; they need official 2024 precinct results. 101 counties' 2024 precinct files are outside 90-110 % of official and 13 have none (SD 10, GA Butts, MA Nantucket, MS Issaquena). 1,202 2024 precincts still show `'20 n/a` (2020 cover under 50 %).
6. **Data at build 1534:** 2024 senate 1,941/1,942, house 4,876/4,882, schools 13,118/13,208 (2020: 1,942 / 4,882 / 13,182). New tools: `tools/fix_ok2024.py` (Oklahoma, State Election Board shapes + MEDSL returns), `tools/fix_vt2024.py` (Vermont town returns), `tools/dist_from_returns.py` (any state: districts from MEDSL precinct returns; split precincts apportioned by legislative-race votes, ≈ only when ≤ 30 % of the district), `tools/build_wi2024.py` (LTSB wards), `tools/build_ca2024.py` (Statewide Database SR precincts). **Still gray 2024:** senate AR 006; house WY 054, MO 156, LA 057, MS 115, VA 089, AL 004; schools 90 (SD 26 vote-center counties, ME 14 unorganized territories reported with towns, MO 9, VT 8 gores, AK 5 …). 73 counties' 2024 precinct files are still outside 90-110 % of official (TN 9, MO 8, OR 6 …), 13 have none. California and Wisconsin no longer use NYT precinct data.
7. NYT-to-official source replacement and 2016 data are parked (NYT credit stays).

## 5. Future plans (approved direction, not started)
2016 presidential data (staging folder, official sources first); Canada (per-country config exists, parked); move to Supabase or Neon + PostGIS when data reaches 700–800 MB (about 190 MB today; a flat export of all results and boundaries for a database lives on the box in `/workspace/db/export/` with its own README; schema proposal in spec 4.2); presets and navigation tabs; offline copy; lighter-data plan (tiles/CDN for past elections); live user votes (`vote` table, Auth, one vote per user per topic); businesses/brands/international directories.

## 6. Tests
Playwright (Python). Serve locally: `cd us-districts && python3 -m http.server 8765`, then
`python3 tests/<name>.py http://localhost:8765/v2/` (or the live URL). Each test prints `OK`/`FAIL` lines and `FAILS <n>`, and exits non-zero on failure. Most check desktop (1280x800) and phone (390x780, touch). Run one at a time (they are heavy; parallel runs clobber timing). Core set before any push: `sort-scale, scroll-stable, type-switch, filter-back, sort-flip, label-clamp, delta-scale, chart-line-single, chart-modes-list, district-list-view, district-consistency, idaho-towns, unisearch, list-all-renders, list-all-clean`. Others in `tests/` cover icons, abbreviations, persistence, menus, estimates. Screenshots are written to `/tmp` by some tests.

## 7. Build, bump, deploy
1. Edit `v2/index.html`; syntax check (extract the last big `<script>` and `new Function(...)`).
2. Bump `window.BUILD` on line 9 (format `YYYYMMDDNNNN`, e.g. `202610151528`).
3. Run the core tests locally, then `git add -A && git commit -m "Build NNNN: …" && git push` (branch `main`). GitHub Pages deploys in about 1–2 minutes: poll `curl -s https://ge0r9b.github.io/us-districts/v2/?x=1 | grep -o 'BUILD="[0-9]*"'`.
4. Re-run the relevant tests against the live URL; report with the build number and screenshot paths.
5. Spec: edit `docs/us-districts-spec.md`; regenerate `.docx` with a markdown-to-docx script (python-docx; fixed table widths). Update the changelog table.

## 8. Data sources and licenses
See `v2/data/COVERAGE.md` (per-state sources, licenses: MEDSL CC0, OpenElections per repo, state SOS public records, Census TIGER public domain, Natural Earth, CA SWDB terms; gray-district inventory; Idaho town audit; Texas timing). Check OpenElections' licence before replacing NYT data.
