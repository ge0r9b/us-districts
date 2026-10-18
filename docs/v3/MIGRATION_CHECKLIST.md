# v2 → v3 migration checklist (feature parity)

Sources for every item: `REPO-RULES.md` (RR), `HANDOFF.md` (HO, build 1548 text plus later builds), `docs/us-districts-spec.md` (SPEC), `v2/index.html` at build **202610181567** (`main` 509d31d), and the 80 Playwright tests in `tests/` (at 9ac59a9) (the de facto spec). Nothing here is invented. If an item has no source, it is not listed. **v3 reaches parity when every box is checked and each listed v2 test, ported to v3, passes.**

## Alpha.1 status (2026-10-18)

The boxes below stay unchecked. Alpha.1 is a running foundation, not v2 parity.

Done on `v3/build`:

- Vite + TypeScript + MapLibre shell (light mode, Liquid Glass year and %/# buttons, bars sorted high to low). Default view is 2016 president by state. 2020 and 2024 open Pennsylvania counties, because those years have no official state presidential totals and alpha.1 does not sum counties.
- `docs/v3/SCHEMA.sql` applies on PostgreSQL 16 + PostGIS 3.4 (tenant seed and `data_version`; see SCHEMA.md).
- Idempotent loaders: v2 presidential counties, 2016 state and district files, `uscd.js`, and the official CSVs on `data/election` (2016 FEC states, Pennsylvania president counties, 2022 and 2024 Senate). Boundary units for `v2-2024` states, counties, and congressional districts.
- Read-only `/api/v1`: manifest, contests, results, unit lookup, geocode stub, locate. Cache headers follow ARCHITECTURE.md §5. OpenAPI is `docs/v3/openapi.yaml`.
- Shared rules in `v3/packages/core` (slots, sort, filters). Design tokens and a MapLibre style a native client can reuse. See NATIVE.md and D24.
- Tests: schema, loader round-trip, API contract, in-process results latency. GitHub Actions `.github/workflows/v3.yml` runs them against PostGIS.

Left for alpha.2: full UI parity (filters, charts, time slider, back stack, hash links), precincts / schools / state legislative districts, PMTiles via tippecanoe (the shell uses GeoJSON states until an archive exists), result packs, entities and officeholders, R12–R14, ZCTA, a read-only database role, Playwright, and any Neon project.

## A. Process and global rules
- [ ] **Instant response is the top priority in every UI change** (RR 7). Budgets in PERFORMANCE.md.
- [ ] v2 stays a static app and v1 (root `index.html`, `US-districts.html`) and `/test` are never changed (RR 5). v3 does not deploy or merge to main until **v2.0 is tagged and the user approves** (RR 5).
- [ ] Data: official sources first, then VEST / MEDSL / OpenElections. Never estimate or invent numbers. Log gaps with reasons. Cite every source (RR 4; SPEC §9.1.7).
- [ ] No fades, no layout jumps (HO §3; SPEC §8). Tests: `no-jump`, `load-stable` (CLS 0), `list-scroll-stay`, `scroll-stable`.
- [ ] Local test ports: v3 lane uses 8860–8899, never 8765 (RR 6). Note: v2 tests' docstrings still say `localhost:8765`; ported tests take the URL as an argument.

## B. Visual style
- [ ] **Light mode only** (HO §3 back button: "light mode only"; v2 has no `prefers-color-scheme` / `color-scheme` rule; white panels `#fff`, stone borders `#e7e5e4`).
- [ ] **Liquid Glass on every round button** (build 1563, refined 1564/1566; `v2/index.html` CSS block "ONE Liquid Glass look for every floating/round button"): applies to district-type row and collapsed type button, search, geo filter, clock/time, chart and chart options, layers/office, #/% toggle, globe. **Unselected** = clear glass, 1 px `rgba(0,0,0,.85)` outline (crisp whole-pixel, 1566), dark glyph, `inset 0 1px 0 rgba(255,255,255,.75), 0 1px 2px rgba(0,0,0,.12)`. **Selected** (`.on`, `.typed`) = near-black smoky glass `rgba(0,0,0,.88→.92)` (1564), white outline and glyph. Sizes and tap targets unchanged (48 px circles, 8 px gap, SPEC §8). Sort chip one button width (1566). Tests: `glass`, `sort-chip`.
- [ ] Icon axis x = 27, text indent x = 52 in all lists and menus (delta rows: abbreviation about x = 44) (HO §3; SPEC §8). Test: `list-all-icons`, `delta-scale`.
- [ ] All text ≤ 32 characters per line (SPEC §8). Field text runs to one character before the round button (1563). Test: `field-noun`.
- [ ] Flags in the institution field (country / state / province); territorial silhouettes with a tiny yellow star for county/town in the geo field (HO §3; SPEC §5.2). The institution field always shows an institution icon while editing (1558). Tests: `geo-icons`, `institution-icon-editing`, `icon-subscript`.
- [ ] Boundaries white with heatmap data, black without (HO §3). County lines 0.5 px, state 1.2 px; US House outlines 1.6 px, others 1.1 px (SPEC §6). Tests: `boundary-color`, `state-line-weight`.
- [ ] Legend and attribution small, bottom left; colours plus tiny labels only; tap to magnify (HO §3; SPEC §6). Test: `legend-size`.
- [ ] No instructional text on the map; no "No data yet" bubble (SPEC §8).
- [ ] Colours: two answers on gives a red/blue margin scale (D+60…R+60; delta D+20…R+20). One answer on gives a single hue. None on gives no fill. No data is gray `#a8a29e` / `#d6d3d1`. < 50 % coverage stays gray (SPEC §6). Test: `single-candidate-shading`, `default-solid`.
- [ ] Wording: states and countries are *sovereign*; counties, cities, towns, townships and boroughs are *incorporated*; never "incorporated state" (HO §3).

## C. Filters (institution top, geography bottom; separate by design, SPEC §5)
- [ ] **Institution vs geography filters**: two filters, shared names (alias table), no shared code (SPEC §5.3). Unisearch shows two rows for government-and-place entities: an institution row (flag or type icon with label Country/State/County/Town/Township/Borough/City) and a Place row (silhouette, label Place) (SPEC §5.3, builds 1521–1524). Tests: `unisearch`, `unisearch-layout`, `filters-correspond`, `institution-search`, `institution-typing`, `institution-plural`.
- [ ] Institution hierarchy All › All countries › United States › states › counties › towns › precincts; US level adds district-type rows (SPEC §5.1). Breadcrumb ≤ 32 chars. Empty + Enter goes to the US; Backspace in an empty field goes up (SPEC §5.1). Tests: `drilldown`, `drill-top`, `filter-climb`, `menu-header`, `fold-no-chevron`.
- [ ] A state lists its own school / state house / state senate districts ("Pennsylvania school districts") (1564). Test: `geo-menu-lists`.
- [ ] Geo filter: ZIP, place, county, town, country, address; the placeholder names what is in view; double-tap locks a name; results stack upward above the keyboard; no breadcrumb (SPEC §5.2). The bottom geo field follows the view (1564). Tests: `geo-stay`, `geo-menu-lists`.
- [ ] Typing a state abbreviation or name puts the state first in both filters (SPEC §5.3). Test: `state_abbr_search`.
- [ ] Address search: Census one-line → Census components → Nominatim; ZIP row; address rows in unisearch (1548). v3: server-side (GEOCODER.md). Test: `addr-search`.
- [ ] Topic field scoped to its entity (President → US); empty topic shows plain boundaries with name-only popups (SPEC §5.4). Test: `blank-topic`.
- [ ] Context edit of the scope row (SPEC §11.8; t206). Tests: `ctx-edit`, `ctx-edit-schools`.

## D. District types (Layers button)
- [ ] **School districts = one list over three unit types** (Q-G4): `school_unified`, `school_elementary`, `school_secondary` (TIGER UNSD / ELSD / SCSD) under the parent category `school_district`. The Layers menu, list-all, counts and sort treat them as one "School districts" list exactly as v2 does. Pop-ups and the geocoder may name two school districts (elementary + secondary) for one point. Test: ported `district-list-view` / `district-consistency` on schools, plus a v3 check that an ELSD+SCSD point returns both.
- [ ] Types: US House, State senate, State house, School districts; data-driven per country (US only; Canada parked) (HO §2; SPEC §3). Test: `district-ctx`.
- [ ] Menu stays open after a pick; closes on outside tap (swallowed), main button, or the selected type; tapping the selected type deselects and restores the defaults; one dark label above the selected type while open (1563–1565; SPEC §8). Tests: `type-menu-sticky`, `type-labels`, `district-menu`.
- [ ] A selected type shows its district list (not the consolidated total) in list view; numbers equal the map pop-ups (HO §3). US House lists all 435 nationwide; other types go states → counties → districts; a district spanning counties appears under each county with whole-district numbers and ≈ (SPEC §7.3). Tests: `district-list-view`, `district-consistency`, `type-switch`, `list-all-districts`.
- [ ] **DC**: its 8 Council wards stand in for both state senate and state house; DCPS is its one school district (1559, `v2/data/dc.js`). Test: `dc-wards`.

## E. Map
- [ ] Display switching: lower 48 fits gives statewide shading; zoomed in gives county shading; one county ≥ 35 % of view (or < 1.6° wide) with a state selected gives its precincts; a district type fills that layer nationwide (SPEC §6). The US level draws only state shapes (1560). Tests: `default-solid`, `us-level-clean`.
- [ ] Map moves off the selected state: selection clears after a 4 s grace period (SPEC §6).
- [ ] Tap gives a tiny popup (name, one line per selected answer in the current format, "≈ estimate", change line in delta); double-tap zooms and puts the name in the geo field (SPEC §6). Test: `est-popup`.
- [ ] Year change recolours existing polygons (1564); in v3, feature-state.
- [ ] Basemap Esri World Street Map (current; licence check, D9).

## F. List view, bars and sort
- [ ] **Bar lists sorted high to low by default** (SPEC §5.1: "Default is high to low"), sorting by the selected answer's % or # (coordinator rule: "lists sorted by % or # descending"); rows without data go last, alphabetical. Tests: `list-sort-default`, `sort-scale`, `list-thumbs-sort`.
- [ ] Sort: one tap flips direction with a small bubble "High to low" / "Low to high" (~1.8 s, 2 s when the tap also acts, 1560); hidden while search or a full-screen filter is open or no list is visible; direction persists (HO §3). Flip moves the existing row nodes with no rebuild (1564). Tests: `sort-flip`, `sort-chip`.
- [ ] Delta sort by the magnitude of net change as displayed (% = margin points, # = vote margin), party ignored (SPEC §7.3). Test: `sort-scale`.
- [ ] # mode bars to one common scale (largest = longest, capped left of the floating buttons); % mode full-width shares (SPEC §7.3). Tests: `sort-scale`, `two-point-cols`.
- [ ] Values inside bar segments, never under the floating button column (clamp or hide) (HO §3; 1563 fit-or-hide). Test: `label-clamp`.
- [ ] Delta mode: net value at the text indent, bar length on one common scale, winner thumbnail at the bar's left end, no per-candidate change numbers (HO §3). Tests: `delta-scale`, `delta-merged`.
- [ ] List-all: first row "List all …" at each level; tapping a row keeps the list view and drills down; states use two-letter abbreviations (full name on press); "List all" row hidden from the first search keystroke (HO §3; 1543). Tests: `list-all*` (10 tests), `list-all-abbr`, `list-band`, `back-band`.
- [ ] List never jumps: scrollTop preserved, identical rebuilds skipped (HO §3). Tests: `scroll-stable`, `list-scroll-stay`.
- [ ] Rows without a 2020 side show the 2024 value with `'20 n/a` (SPEC §7.3). Test: `est-list`.
- [ ] Drill-in answers at once: cached or skeleton rows within about 15–50 ms; chevron and thumbnails appear together in their final spot (1567). Test: `drill-instant`.

## G. Answers, estimates, gray
- [ ] **2016 `[d, r, tot]` triple**: imported for every layer v2 ships it for; Clinton = `dem_nominee`, aligned with Biden (2020) and Harris (2024); Trump = `rep_nominee`; `other = tot − d − r`; gray where v2 has no 2016 source; ≈ where the `ds2016-*` value has a 4th element `1`; **missing key = gray**; source files are the lazy-loaded `v2/data/election2016.js`, `ds2016-{states,cd,sldu,sldl,sch}.js`, `precincts2016/` (DATA_LOADING.md §8, Q-E9 resolved). Main 9ac59a9 (Build 1569) has the 3-point slider and Clinton thumbnail and shows 2016 as gray until the files are wired (`tests/y2016.py`).
- [ ] **Answers shown as D and R plus the total of all candidates** (v2 data rows are `[dem, rep, total]`; `candidates.csv` `other = total − dem − rep`). v3 generalizes to N answers but must render the v2 view identically for presidential contests.
- [ ] **v2-parity d/r slot rule for Senate (Q-E13, DATA_LOADING §12)**: **d** = the Democratic nominee, unless an independent beat the Democrat statewide or there was no Democrat, then that independent; **r** = the Republican; total = all candidates. Cases: King ME 2024 (Costello in all-others), Sanders VT, Osborn NE 2024 regular, McMullin UT 2022, AK 2022 first round (d Chesbro, r Murkowski, Tshibaka in all-others), Chambers LA 2022, Christiansen ND 2022. v3 stores every answer, and this mapping is a view (`contest_display_slot`). **Colour still follows party**, so an independent in the d slot is not drawn blue. Contests: `us_senate`, `us_senate_special` (CA and NE 2024, CA and OK 2022), `us_senate_runoff` (GA 2022).
- [ ] **≈ marks area-weighted or allocated estimates** (SPEC §3, §9.1.5). Flags `est` (both years), `e24`, `e20` (per year) as read by `v2/index.html` (`ef==="e24"&&ym()!=="2020"`). ≈ prefixes the first visible in-bar value / net value (1563). Tests: `est-list`, `est-popup`, `idaho-towns`.
- [ ] **Gray = no source** (no fabricated data). The remaining 2024 gaps are listed in COVERAGE.md (HO §4 item 8).
- [ ] Format modes: # mode shows no percentages anywhere; % mode shows no counts anywhere (SPEC §8). Known v2 gap: pop-ups and legend still show "pts" in # mode (SPEC §11.3). **D10 pending: the orchestrator is triaging it in v2; v3 follows the outcome.**

## H. Charts
- [ ] **One entity gets pie, bar and line charts** (build 1557: single entity = pie/line; 1563: bar offered again, one bar per answer, sorted). Range = bar + line; single point = bar + pie; no scatter; no concentric delta pie; the button cycles only valid types, auto-switches an invalid type to bar and restores later (SPEC §7.3; HO §3). Tests: `single-entity-chart`, `bar-single`, `chart-line-single`, `chart-menu`, `chart-modes-list`, `line-two-point`.
- [ ] Chart button is dark only while a chart is displayed (inactive in the full-screen map) (HO §3).
- [ ] Line delta labels under the line, centred between the points; vertical hairlines at each slider year (1562). Pie labels one decimal (1563).

## I. Time, format, navigation, persistence
- [ ] **3-point time slider 2016 / 2020 / 2024** (orchestrator decision, Oct 18, 2026; 2016 is the last v2 vote data set). Single knob on any of the three years; two knobs = range/delta between the chosen pair; line charts get a point and hairline per year. v3 must reproduce whatever v2 ships for 2016 (e.g. which pair delta compares, how `'20 n/a` generalizes to `'16 n/a`) and port its tests. v2 build 1568 painted the list in 116 ms (US House) / 140 ms (county) median at 4× CPU (`tests/slider-fast.py`); v3 budget ≤ 100 ms (PERFORMANCE.md).
- [ ] Time slider (pre-2016 description): one knob = single year, two knobs = delta; `ym()` returns "2020" / "2024" / "delta" (HO §2). **v3 must support N years** (possible 2016 → 3-point slider 2016/2020/2024, coordinator roadmap, unconfirmed; D11). v2 roadmap target: < 150 ms to first visible response.
- [ ] % / # button, default % (SPEC §7.4).
- [ ] Back button: exists only when the history stack is non-empty; thin black chevron, 44 px target, positions per HO §3; keyboard Backspace / Alt+Left / Cmd+[, browser back via popstate (HO §2). Tests: `filter-back`, `back-band`.
- [ ] Persistence: URL hash `#s=<base64url JSON>` + `localStorage usd.state`, versioned `v:1` (HO §2). v3 reads v1 hashes and maps them (old links keep working). Tests: `state-persist`, `view-persist`.
- [ ] New builds reach open tabs (1560 BUILD check). v3: short-TTL HTML + hashed assets. Test: `build-check`.
- [ ] **Clinton thumbnail** for 2016 (v2 Build 1569: a 96 px public-domain State Department portrait in `v2/img`; copy it with its credit), shown in the Democratic slot whenever the slider is on 2016, in the same position as Biden / Harris.
- [ ] Candidate thumbnails upper left, same spot in map, list and chart; tapping toggles the answer; badges centred below the photo (SPEC §7.1; 1564). Test: `list-thumbs-sort`.

## J. iOS Safari specifics (SPEC §2)
- [ ] Inputs ≥ 16 px; one focusable field at a time; focus inside `touchend`; page pinned against visual-viewport scroll; manual double-tap detection; toolbar-only resizes (< 120 px) swallowed (HO §2); `overscroll-behavior: contain`.

## K. Data coverage parity (must equal v2 at the parity gate, DATA_LOADING.md §7)
- [ ] Coverage counts per SPEC §9.2 and the latest COVERAGE.md (2024: US House 435, senate 1,942, house 4,877/4,882, schools 13,124/13,208 at build 1539; check against the export at parity time).
- [ ] Sources and credits displayed; NYT credit kept until no NYT-derived data remains (HO §3).

## L. Port of the Playwright suite (80 tests at 9ac59a9)
Plan: copy the intent, not the selectors. Each v2 test becomes a v3 test with the same name under `v3/tests/`, run against a local v3 build (ports 8860–8899) and against v2 as the reference. Data tests (`district-consistency`, `est-*`, `data-2020`, `ak-2020`, `dc-wards`, `idaho-towns`) become API/SQL assertions plus one UI check. The HANDOFF §6 "core set" is ported first: `sort-scale, scroll-stable, type-switch, filter-back, sort-flip, label-clamp, delta-scale, chart-line-single, chart-modes-list, district-list-view, district-consistency, idaho-towns, unisearch, list-all-renders, list-all-clean`.

| Test | What it checks (from its docstring) |
|---|---|
| `addr-search` | Build 1547: typed geo-field text searches nationwide even with a state/county selected; addresses resolve via Census/OSM; |
| `y2016` | Build 1569: three-point slider (2016, 2020, 2024); Clinton thumbnail in the Democratic slot (same answerId / colour / side as Biden and Harris; Trump every year); until 2016 data lands, 2016 shows gray map, names without values, a note; the 2016 tap paints within 150 ms (4× CPU) |
| `ak-2020` | Alaska boroughs in 2020/delta: borough results (≈, from __ak.boro2020) must be present once ELECTION2020 loads, |
| `back-band` | Build 1549: list-view back chevron and sort glyph always sit inside the list band (below the time row, above the first row), |
| `bar-single` | bar-single.py URL tag -- build 1563: a single entity (US) offers bar again: ONE bar per answer in the chart panel (.seb |
| `blank-topic` | blank-topic.py URL tag -- blank topic = no results anywhere: geo-select LA County (typed and via institution) with blan |
| `boundary-color` | boundary-color.py http://localhost:8765/v2/ tag  -- boundary color: white with data plotted, black with boundaries only |
| `build-check` | build-check.py URL -- build 1557: an open tab picks up a newer deployed build (iOS Safari kept running a pre-1551 page, |
| `chart-line-single` | t250u (updated build 1557: single entity = pie/line only; build 1563: bar is offered again for a single entity, one bar per answer): line ch |
| `chart-menu` | chart-menu.py URL -- build 1563: the chart button on the intro screen (single entity 'United States') works with touch |
| `chart-modes-list` | t240/t249: list-all rows follow the chart-type setting (bar / line / pie); line labels sit under their line between the points; single-count |
| `ctx-edit-schools` | t193/t206: California school districts: list-all shows; tap the field -> menu; tap top 'California' -> states; type ohio Enter -> Ohio; Esca |
| `ctx-edit` | t206: from a district list, tap the top 'Alabama' row -> institution field with full state list; type texas + Enter -> Texas; menu pick; Esc |
| `data-2020` | build 1533: 2020 data completeness. Alaska 2020 (boroughs + House/Senate in 2024 lines, ≈), Connecticut 2020 |
| `dc-wards` | Build 1556: District of Columbia under the district types. DC has no state legislature: its 8 Council wards stand in for |
| `default-solid` | default-solid.py URL tag -- the default (initial) view and a slightly zoomed-in view show SOLID statewide fills (natPan |
| `delta-merged` | delta-merged.py URL tag -- two-point bar view: one merged block [2020 thumb]--change bar--[2024 thumb], change values o |
| `delta-scale` | t238: delta list: abbreviation at x~44, net value column, stacked bar from /R chg/+/D chg/(+oth) on one common scale, thumbnail at bar's lef |
| `district-consistency` | t246: district-type rows (list) use exactly the numbers the map pop-ups show; state rows in district-type context sum the districts |
| `district-ctx` | district-ctx.py URL tag -- district-type button group is data-driven per country: shown for the US, hidden (slot kept, |
| `district-list-view` | t241/t242/t244/t245: list view + a district type selected lists districts, never the consolidated total. US House nationwide (435), other ty |
| `district-menu` | district rows: flag icon at x=27 (no checkmarks), text at x=52, header rows fixed; AL senate/house + another state |
| `drill-instant` | Build 1567: a drill-in tap (state row -> counties, county row -> townships) shows the target list at once: cached rows of the |
| `drill-top` | Build 1552: drilling into a county row (scrolled far down the counties list) opens its townships list at the top, not at the old offset |
| `drilldown` | drilldown.py URL tag -- list-all drill-down chain in the SAME list view + settings: All States -> Florida (counties) -> |
| `est-list` | build 1563: the ≈ prefixes the first visible in-bar value ('≈82.2%'; the net value in change mode) instead of a column after the name. |
| `est-popup` | ≈ estimate mark: popups for Alabama state senate districts say "≈ estimate" exactly when the district's data row is flagged est (tests/est-a |
| `field-noun` | field-noun.py URL -- build 1563: the top field text (entity name + mid-gray level noun, e.g. 'Pennsylvania US House dis |
| `filter-back` | t225-t230: back button + history stack. Button exists only with a non-empty stack, only in filter lists / list views. Back pops one change. |
| `filter-climb` | t216u regression: climb state -> country -> all countries -> All, then All-collapse (click / type+Enter / Escape) must just close, no resele |
| `filters-correspond` | filters-correspond.py http://localhost:8765/v2/ |
| `fold-no-chevron` | fold-no-chevron.py URL -- build 1555: no back chevron (#bBack) is visible while a full-screen filter is open |
| `geo-icons` | t210: geo filter rows use territorial-shape silhouettes, never flags (states, countries, provinces); institution filter keeps flags |
| `geo-menu-lists` | geo-menu-lists.py URL -- build 1564: |
| `geo-stay` | geo-stay.py URL tag -- typing a state in the geo field + Enter keeps that state (no county auto-select, no fall back to |
| `glass` | glass.py URL -- build 1563 (Liquid Glass, approved preview v3): |
| `icon-subscript` | icon-subscript.py URL -- build 1555: the S / H subscripts (and US House dome) glyph text is black on light surfaces |
| `idaho-towns` | t231/t232: Idaho town rows: every county's towns have 2024 data (real precinct results; area-weighted + est mark where a town sits inside a |
| `institution-icon-editing` | institution-icon-editing.py URL -- build 1558: the institution field (and its rows) ALWAYS shows institution icons: |
| `institution-plural` | institution-plural.py URL -- build 1555 institution filter: institutions only (no countries outside 'All countries'), |
| `institution-search` | (no docstring) institution/geo full-screen search: lists entered rows and typed results at 1280×800 and 430×900 (SPEC §5.3) |
| `institution-typing` | institution-typing.py http://localhost:8765/v2/  (checks typing + Enter + field layout, desktop and phone) |
| `label-clamp` | t235/t236/t237: no text under the floating button column (any list level, any mode); delta shows only the net value next to the winner thumb |
| `legend-size` | legend-size.py URL tag -- bottom-left legend (labels 4px, bar 37x3) and credit (6px, NYT kept) are ~35% smaller than be |
| `line-two-point` | line-two-point.py URL tag -- two-point line view: chart directly under the time filter, line endpoints exactly under th |
| `list-all-abbr` | list-all-abbr.py URL tag -- list-all states: two-letter abbreviation at x=52 = the top fields' text, no row icon on res |
| `list-all-clean` | list-all-clean.py URL tag -- 'List all states': field says 'All States' (flag kept), no total block / Republican-Democr |
| `list-all-districts` | t205 (phone delta: segment labels only where they fit and clear of the floating buttons since build 1528, so >=1 labelled row): district lis |
| `list-all-icons` | list-all-icons.py URL tag -- every list-all row has its icon centered on x=27 and its name at x=52 (x=73 / 98 when the |
| `list-all-modes` | list-all-modes.py URL tag -- (refreshed for build 1548: clean storage per section, candidate-share % sort) list-all: 'L |
| `list-all-renders` | list-all-renders.py URL tag -- 'List all states' must render >=50 visible rows in map/list/chart(bar,line,pie) modes on |
| `list-all-tap` | list-all-tap.py URL tag -- tapping (touch) list-all rows selects that entity at every level; sort control hidden when n |
| `list-all-tap2` | list-all-tap2.py URL tag -- touch-tapping list-all rows selects the entity: DC (states list), county, township/municipa |
| `list-all-values` | list-all-values.py URL tag -- list-all bars: value written INSIDE each segment (% in % mode, votes in # mode, change in |
| `list-all` | ()=>{const LA=window.__LA; const lv=document.getElementById('listView'); const rows=[...lv.querySelectorAll('.lvrow.la')]; return {on:LA.on, |
| `list-band` | Build 1553: results lists start half the empty band higher (first row ~6px under the chevron/sort-glyph row, nothing overlapping); |
| `list-scroll-stay` | list-scroll-stay.py URL -- build 1563: a list keeps the scroll position the user leaves it at (PA counties, 2020, % mod |
| `list-sort-default` | Build 1551: every results list (% and # mode) sorts high→low by the TOP-RANKED TOGGLED-ON answer of the left thumbnail |
| `list-thumbs-sort` | Build 1546: list charts (bar/pie/line/change bars) use the left-edge candidate column (no per-row photos), ranked for the |
| `load-stable` | load-stable.py URL -- build 1557: nothing jumps on page load (t282). |
| `menu-header` | menu-header.py URL tag -- institution menu open (also after list-all, with a district type): header rows stay at the ap |
| `no-jump` | no-jump.py URL -- build 1565: the list's floating pieces (#laCands thumbnails, #bBack chevron, #laSort chip) never move |
| `scroll-stable` | t234: list-all list must never move on its own: scrollTop unchanged for 10s with simulated iOS toolbar height changes (<120px), re-render tr |
| `single-candidate-shading` | single-candidate-shading.py URL -- Harris-only / Trump-only statewide fills must follow the candidate's actual share on |
| `single-entity-chart` | single-entity-chart.py URL -- build 1563: bar offered again for a single entity (one bar per answer), chart options dis |
| `sort-chip` | Build 1566: in results lists the sort chip sits one button width (48px) + a gap left of the right button column, on the back |
| `sort-flip` | t229: one tap flips list sort direction at once; bubble names the new direction for 2 s (build 1560), no layout shift; alternates; persists |
| `slider-fast` | Build 1568: a time-slider change paints the updated list within 150 ms (median, 4× CPU, phone) for US House and county lists; map follows one frame later |
| `sort-scale` | t272-t275: delta lists sort by /net change/ as displayed (all levels, % and #); single-year # bars are proportional to total votes on one co |
| `state-line-weight` | state-line-weight.py URL tag -- state boundary lines are ~30-40% thicker than before at county-level zoom (applied at d |
| `state-persist` | state-persist.py URL tag -- state persistence: reload restores topic/geo/time range/chart/list-vs-map/#-%/layer from th |
| `state_abbr_search` | Playwright test: exact state abbreviations/names rank the state first in both filters. |
| `two-point-cols` | two-point-cols.py URL -- in the two-point view the 2020 column sits under the 2020 label (left icon axis) and the 2024 |
| `type-labels` | type-labels.py URL -- build 1563: ONE dark label (rgba(0,0,0,.8), white text) centred 4px above the SELECTED type butto |
| `type-menu-sticky` | type-menu-sticky.py URL -- build 1564: the district-type menu (expands left from the right-column type button) stays op |
| `type-switch` | t223/t224: switching district type (or state via menu) from a list-all view re-renders immediately, keeps list view/format/sort, never shows |
| `unisearch-layout` | unisearch-layout.py URL tag  -- unisearch rows: icon centered x=27, text x=52 |
| `unisearch` | t217/t218: unisearch gives TWO rows for every entity that is both a government and a place |
| `us-level-clean` | us-level-clean.py URL -- build 1559: at nationwide scope (no state picked) only state shapes draw. |
| `view-persist` | view-persist.py URL tag -- view settings (list vs map, chart type, #/%, time range/delta, sort) persist across selectio |

- [ ] **Lazy loading per year** (v2 pattern to keep): v2 loads each year's results only when that year is shown (`loadE2020`, `loadPrec20(st)`, and the 2016 files are lazy-loaded the same way), so the default 2024 view never pays for 2016/2020. v3 keeps this with **per-year result packs** (one pack per contest = per year, per unit type, per state for precincts; ARCHITECTURE.md §4, PERFORMANCE.md).

## L2. Bug Tester QA of v3 (Phase 2)
- [ ] As soon as v3 has a **Vercel preview URL or a servable branch on ports 8850–8859** (local static server), hand it to the Bug Tester.
- [ ] QA runs at **phone and iPad sizes** (the Bug Tester's harness: Chromium mobile + WebKit with touch, iOS UA; 320×568, 375, 390×844, 1024×576 and iPad portrait/landscape).
- [ ] Findings are logged in **`BUGS.md` on `qa/bugs`** (QA-### ids, severity scale as there); v3 fixes cite the id, and the parity gate needs 0 open Critical.
- [ ] The v3 lane's own Playwright port keeps using ports 8860–8899 so it never collides with QA.

## L3. Beyond parity: institution lists (v3.1+, not a parity item)
- [ ] Brands and organizations appear in the institution filter as `wikidata:Q…` entities, shown by `brand_name`. No SEC/GLEIF/LEI data and no `lei:`/`cik:` ids anywhere in the UI, API or packs (they're reserved for the v5/v6 private bridge).
- [ ] Establishments (`entity_location`, `establishment_at` / `hq_in`) render as points and resolve to units by point-in-polygon. Retracted sites are hidden, not deleted.
- [ ] Scraped brands with no QID never appear; approved user adds show with a `usd:` id until a QID appears.

## M. v2 intake alignment (UI and test side)
See DATA_LOADING.md §9 for the full artifact → table map. UI-relevant points:
- [ ] Every v2 row value shown in the UI (`[dem, rep, total]`, `est`/`e20`/`e24`/`cty`, null = gray) maps to `result` + `result_total` + `is_estimate`, and the v3 pop-up and list render identically. Gate: ported `district-consistency` and `est-*` pass on both v2 and v3 with identical numbers.
- [ ] School names: the Geo lane renamed the 132 duplicate school rows to `Name (County)`, so `state|name` is unique in every national layer (on `data/geo`; main 9ac59a9 still has the old 58 duplicate keys). v3 shows the renamed names exactly as v2 does and keys units by TIGER GEOID through a 1:1 `legacy_key → geoid` table (Q-G1). Root `data/<State>.js` is v1 and out of scope (no renames; Q-G8 resolved). **Parity source: `v2/data/` only** (precinct copies be5168d, `v2/data/states/` and `zcta2024.js` copies 6d8b443). The 8 renamed parts places (`Name (County)`, fd0f171) must display as in v2.
- [ ] Hash links from v2 (`#s=…`, names not GEOIDs) resolve through the name → GEOID crosswalk; ambiguous names open a chooser instead of guessing.
- [ ] In-flight v2 UI work to re-check before the parity gate: the 2016 data and 3-point slider (decided, not on main at e8040d3), the time-slider speed work (build 1568 shipped `slider-fast`), bug fixes from the Bug Tester's `BUGS.md` (not yet on any remote branch at the time of writing: `qa/bugs` exists only as a local clone with no BUGS.md), and the uncommitted `v2/index.html` change in the orchestrator clone (not inspected: lane rule).


## Added by the Oct 18, 2026 08:00 EDT drift check (main 58d815e, Build 1570)
- [ ] 2016 lazy loading: nothing 2016 loads until 2016 is picked; the 2016 tap paints a "Loading 2016 results…" placeholder within 150 ms (4x CPU throttle), then values fill in. 2016 map shapes always draw (gray only for no-data units). v3 equivalent: the 2016 tile/result request is made only on pick, with the same instant placeholder. Test: `y2016-data`.
- [ ] County and precinct values for 2020/2024 come from `v2/data/` (not root `data/`); PA → Jefferson County townships have values in 2016, 2020 and 2024; PA precincts draw in every year. Test: `prec-paths`.
- [ ] QA-032: list rows sort by the selected year's values (2016 included), and reload restores '16.
- [ ] The chevron does not stick when no topic is selected (back-band).
- [ ] QA pass 4 (`qa/bugs` 1ddc397): reload restore of year, # mode, chart type, range + line, list, district type, map centre and zoom (map vs list excluded, QA-034); layout sweep at 5 sizes with no overlapping or off-screen text (QA-035); throttled slider drag at 375 / 320 / 1024x576. Port `qa/restore.py` and `qa/sweep.py` as v3 parity tests.
- [ ] Contest picker readiness: 2022 and 2024 US Senate rows exist on `data/election`. v2 has no Senate UI yet; v3 must show states with no race as gray, and colour the d slot by the candidate's party (independents such as King, Sanders, Osborn and McMullin take the d slot).

## Added by the Oct 18, 2026 10:00 EDT drift check (main 7a23208, Build 1575; 88 tests in `tests/`)
- [ ] **Chart type keeps (1571):** the chosen chart type never changes with the timeline; pie in a range = end year; bar and pie are always offered; line only needs a range. 2016 shows numbers at every level (US total Clinton 48.2 / Trump 46.1 from the state table). Tests `chart-keep`, `y2016-levels`.
- [ ] **List map colours (1572):** the list map fills each unit with its own result (real D/R heat in every year, 2016 included); gray only when the unit has no data, never one pale aggregate colour. Zoomed precinct detail at '16 reads 2016 values. Test `y2016-levels` map-fill checks.
- [ ] **Pie = thumbnails only (1573):** rank order, winner on top, no names or numbers beside them; a tap shows the full name and value in the standard bubble; nothing overlaps the pie at 320 / 390 / 1024. Test `pie-thumbs`.
- [ ] **Change view from '16 (1574):** ranges '16 > '20 and '16 > '24 show shifts from 2016, end-year thumbnails, and the map coloured by shift; leaving a '16 view always rerenders (QA-038). Test `y16-range`.
- [ ] **List band (1575):** rows start 16 px below the top band (was 31 px), so the first row slides halfway under the sort chip; sort chip glass fill .05 / .03, 3 px blur, crisp 1 px outline. Tests `rows-up`, `list-band`, `back-band`, `glass`, `sort-chip`.
- [ ] **Open QA items to re-check at parity (qa/bugs e9539af):** QA-039 (2016 state totals after a drill-in must be the official state result, not county sums), QA-040 (one 2016 total per unit everywhere), QA-041 (picking Line is slow again), QA-042 (2016 `#` bar segment numbers), QA-043 (picking Line in '16 > '24 must not move the start knob). In v3 the state total always comes from the state result row (unique on year, office, stage, boundary_set, unit), never a sum.
- [ ] **Past-year precincts on 2024 polygons (after the `data/election` merge):** 2016 and 2020 precinct views draw the 2024 polygons with placed values, ≈ for split/merged rows and gray where nothing was placed (DATA_LOADING.md §9.4).
- [ ] **Search and star (once v2 ships `geo_index` / `points`):** v3 search returns the same rows and labels as `v2/data/geo_index/`; the state-icon star sits at `unit.label_point`.
