# v2 → v3 migration checklist (feature parity)

> **Scope (D25, Oct 19, 2026): v3 is US-only.** Every item below that mentions countries, provinces, Canada or foreign governments is **parked** for the US build: only the US (and its territories) is shown. Country/province search rows and flags are out of v3.

> **v2 → v3 parity:** see [V2_PARITY_CHECKLIST.md](V2_PARITY_CHECKLIST.md), one line per v2 build fix or QA item from Build 1585 on. v3 cannot ship until every line there is ticked.

Sources for every item: `REPO-RULES.md` (RR), `HANDOFF.md` (HO, build 1548 text plus later builds), `docs/us-districts-spec.md` (SPEC), `v2/index.html` at build **202610181567** (`main` 509d31d), and the 80 Playwright tests in `tests/` (at 9ac59a9) (the de facto spec). Nothing here is invented. If an item has no source, it is not listed. **v3 reaches parity when every box is checked and each listed v2 test, ported to v3, passes.**

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
- [ ] Colours: two answers on gives a red/blue margin scale (D+90…R+90 linear since 1579, was ±60; delta D+20…R+20). One answer on gives a single hue. None on gives no fill. No data is gray `#a8a29e` / `#d6d3d1`. < 50 % coverage stays gray (SPEC §6). Test: `single-candidate-shading`, `default-solid`.
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
- [ ] Types: US House, State senate, State house, School districts; data-driven per country (US only; Canada and all other countries parked by D25, own repos later) (HO §2; SPEC §3). Test: `district-ctx`.
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
- [ ] As soon as v3 has a **Cloudflare Pages preview URL (ARCHITECTURE §5c) or a servable branch on ports 8850–8859** (local static server), hand it to the Bug Tester.
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

## Added by the Oct 18, 2026 12:00 EDT drift check (main 615fa5a, Build 1576; qa/bugs 8086360)
- [ ] **Thumbnails (1576, QA-045):** candidate thumbnails are a fixed 30 px with % badges in every state and DC from the first frame; the size never derives from the crumb flag image (AL's portrait flag once made them 14.7 px). In v3 the size is a design token, not a measured value. Test `regress-1576`.
- [ ] **No list jumps (1576, QA-055):** switching results ↔ district list, or years, never moves the list box; space for the shift line is reserved; a new list starts at scroll top; hidden thumbnails never collapse the list's top offset. Test `no-jump` (frame-by-frame at 390 / 375 / 1024×653), part of the CLS = 0 gate.
- [ ] **Geo filter county rows (1576):** a county row shows its state's silhouette with the star at the county's point (from `v2/data/points`, loaded lazily per state; v3: `unit.label_point`), with no placeholder glyph. The building glyph is reserved for companies (institution filter).
- [ ] **Open QA at Build 1576 (qa/bugs 8086360):** QA-059 and QA-060 (list-view thumbnail jumps) and QA-061 (stale DC geo label) must be closed in v2 or re-checked as v3 parity tests.
- [ ] **Perf gates from the v2 baseline:** see PERFORMANCE.md "v2 measured baseline" (data URLs keyed by content hash, fit after paint, iPad pan ≥ 55 fps).

## Added by the Oct 18, 2026 14:00 EDT drift check (main e1f9ae3, Build 1583; 98 files in `tests/`; qa/bugs 110a672)
- [ ] **Margin colour scale (1579, QA-046 option a):** the two-answer margin scale is linear to D+90…R+90 (was ±60, which clamped lopsided counties' precincts to one red). Both the full and compact legends read +90, and the 2016 legend names Clinton. This replaces the D+60…R+60 wording in §B; in v3 the scale end is a design token (`margin.max = 90`). Test `scale-90`.
- [ ] **Chart menu rules (1577):** one year offers pie + bar; a range offers line + bar; an invalid pick falls back to bar. Line keeps '16>'24 / '16>'20 (QA-043), and '16>'24 plots '16, '20 and '24 with a change label per segment. Tests `line-16`, `chart-keep`.
- [ ] **Institution field (1577):** always searches institutions from any level (US/USA/America, states, counties, countries, provinces), grouped, never blank, shows "No institutions match" on a miss, and Enter/tap takes the top match. Canada lists its 13 provinces/territories in gray with a v3 note (Canada units load in v3.1, D23). The unisearch button stays top-right in the institution filter, geo filter and chart menu. In v3 this is one `/api/v1/search?scope=institution` call with grouped results. Test `inst-field`.
- [ ] **'16 ranges (1577):** the US map redraws for '16 ranges; thumbnails read their slot's year (badges and labels). A precinct's change at a '16 range reads its 2016 twin (by name, else the 2016 precinct containing the 2024 centre; about 99 % matched, interim until values-only `precincts2016`). In v3 the twin is a stored `unit_crosswalk` row built at load, never a tap-time point-in-polygon. Philadelphia ward-division 2016 twins (QA-048). Tests `y16-range`, `prec-philly`.
- [ ] **Address search switches everything (1578, QA-062/063):** an address moves crumb, thumbnails, map and field to one place. DC addresses (no state/county picker) open DC; an address landing on a precinct adds the precinct crumb so title and thumbnails agree. Bar labels avoid the sort chip at 320 px (QA-009). In v3 the geocoder response carries the full unit chain (state → county → precinct) so the client never mixes old and new place. Test `addr-place`.
- [ ] **Time slider (1580, QA-053):** endpoints come from live element rects with small '16 / '20 / '24 labels; the clock button stays fixed when the row opens or closes. Precinct names have no county prefix and are never cut (QA-065); the '16>'24 precinct list is restored on reload (QA-050). Test `slider-align`.
- [ ] **Thumbnails never jump (1581–1582):** candidate thumbnails stay hidden until results are in (fresh load) or the restored place is applied (reload), in a fixed-width badge slot. Candidate icons keep the map view's fixed spot in list, pie, bar and line; no text or tooltip beside them in chart views; the single-year bar chart is visible at phone width and clear of the button column. Tests `thumb-load`, `fixed-icons`.
- [ ] **Back chevron on WebKit touch (1583, QA-071):** acts on `pointerup` and ignores the follow-up click. v3 uses one pointer-event handler for every tap target (also needed by the native shell, NATIVE.md). Test `back-webkit` runs in WebKit and Chromium touch; v3's port must run in both engines.
- [ ] **Open QA at Build 1581 (qa/bugs 110a672):** QA-051 (thumbnail labels in lists), QA-064, QA-068 (DC pin), QA-069, QA-070 (clock button frame jump, reproduces at 375) are open; re-check as v3 parity tests if not closed in v2.

## Added by the Oct 18, 2026 16:00 EDT drift check (main ae92b92, Build 1584; qa/bugs f1a097c; perf/speed-baseline 5cd2898)
- [ ] **Map waits while a list covers it (1584):** when the list view hides the map, map moves and fits are deferred until the map shows again (v2 Back −140 ms). In v3 the map store skips camera work for a hidden map and applies the last requested view on show.
- [ ] **District picks under 100 ms in big states (1584, QA-064/QA-073):** state senate, state house and school district lists are warm before first use (v2: idle warm-up; v3: the API returns the per-state list in one indexed query and the client prefetches on idle). v2 at 1584 is still TX 231 / CA 144 / PA 121 ms for school districts; v3 must be under 100 ms everywhere. Test `tests/dist-pick-speed.py` ports as a perf test.
- [ ] **No style recalculation on every DOM change (1584):** v2 replaced `body:has(#chartDim.on)` with a class. v3 keeps `:has()` out of global selectors; state goes on a class or data attribute.
- [ ] **Perf at 1584 (PERF_TABLE.md):** Back median 37–44 ms, US House pick 68–74 ms, All States 43–49 ms, phone pan 59–60 fps; iPad pan still 47 fps. These replace the 1575 numbers as the bar v3 must beat (iPad pan ≥ 55 fps stays a v3 gate).
- [ ] **Open QA at Build 1584 (qa/bugs f1a097c):** QA-072 critical (DC > School districts or US House shows US totals under "District of Columbia"; v3: a scope with no rows of that type shows an empty state, never a parent's totals), QA-074 (same-name school districts can't be told apart and some CA districts repeat; v3 lists add a disambiguating county or LEA id and dedupe by GEOID), QA-075 (typing "Georgia" + Enter opens the country; v3 search ranks the US state first for US-context queries and lists the country second), QA-007/020 improved but open. Re-check as v3 parity tests if not closed in v2.

## Added by the Oct 18, 2026 18:05 EDT drift check (main 0c711df, Builds 1585–1587; qa/bugs cc521df; perf/speed-baseline e128cf7)
- [ ] **Bars on the thumbnail rows (1585, test `bar-rows`):** in chart views each bar sits on its candidate's thumbnail row, 6 px right of the icon, with no name label; tapping shows a white name bubble; the remainder is a gray "Other" chip. Bars run full width under the floating buttons. Range bars also sit on the icon rows.
- [ ] **Pie placement and size (1585/1586, tests `pie-fit`, `pie-render`):** the pie sits right under the slider, between the thumbnails and the buttons, sized to fit above the bottom field, and its size is guarded against NaN. It never shrinks or moves when the chart or district-type menu opens.
- [ ] **List rows never show pies (1585, test `list-charts`):** a list row shows the totaled bar (default) or the split bar (its own icon).
- [ ] **Menus are overlays (1586, test `menu-overlay`):** no screen dim, and nothing under the menu moves.
- [ ] **2016 charts after a return trip (1586, tests `chart-all-states`, `y2016-levels`):** returning to 2016 with its files already loaded must still show the pie and bars for every state. In v3, chart data comes from the year's pack each time, so there is no "already loaded" branch to forget.
- [ ] **Icons stable across a map/list switch (1586, QA-060, test `switch-stable`):** icon sizes are measured in the same frame as the switch, so there is no 12 → 4 → 12 px jump.
- [ ] **Sort chip at the right end of the bar area (1587, user, test `sort-chip-end`):** the list sort chip sits just left of the floating button column, on the same row and at the same size as before, with no jump.
- [ ] **DC scope and US-first geo search (1585, QA-072/QA-075 fixed, tests `dc-scope`, `geo-us-first`):** v3/build serves both from the API (f9a96de); port the two tests as API and UI tests. Minor: DC's delegate row reads "District 00" in v2; proposal for v3: label it as the at-large delegate seat instead (UI decision, not yet confirmed).
- [ ] **Open QA at Build 1585 (qa/bugs cc521df):** new QA-076 (the name bubble covers the photo and number on phones and floats far from it on iPad), QA-077 (the single-place range chart puts change bars under the thumbnails with labels, not on the icon rows), **QA-078 high** (split bars in a range are each scaled to their own largest change; v3 uses one common scale per list), QA-044 widened (the sort chip covers the first row's red bar at 390 and 320). Still open: QA-070, QA-007, QA-005, QA-020, QA-003. Re-check as v3 parity tests if not closed in v2.
- [ ] **Perf at 1585:** within noise of 1584 (Back 35–44 ms, US House pick 65–87 ms medians, phone pan 59.6–59.8 fps, iPad pan 43.6 fps). The 1584 bar stands, and iPad pan ≥ 55 fps stays a v3 gate.

## Added by the Oct 18, 2026 20:05 EDT drift check (main 3fc48e5, Builds 1588–1592; qa/bugs 438a549; perf/speed-baseline 5e92d72)
- [ ] **Sort by total votes (1588, user, tests `list-sort-total`, `list-sort-default`):** High to low with every answer shown ranks by total votes cast (all answers plus Other) in % and # modes, stacked and split, every year; one toggled-on answer ranks by that answer (share in %, votes in #); a range sorts by |net change| as shown. **v3/build `packages/core/src/sort.ts` needs a `total` sort key and this rule**, applied in the API and the shell alike.
- [ ] **District number labels (1588, test `district-number-labels`):** district-type rows show only the number; seat 0 / AL reads "At-large" (DC, AK, WY). Replaces the 18:05 "District 00" proposal. Open QA-080 (low): nationwide list reads `DE-00`.
- [ ] **Thumbnail column on the topic-icon axis (1588, test `thumb-axis`)** in every view; **list-all exits to the map at every level** (thumbnails and layers come back).
- [ ] **Year-correct district colours (1589 CRITICAL, test `colors-2016`):** fills use the selected year's margin (no fall-through to shift colours); the 2016 district file loads on demand and the layer redraws when it lands; DC's delegate seat uses DC's statewide result. In v3: colour function keyed by year, 2016 DC delegate row in the pack.
- [ ] ~~**Sort chip header row (1590, QA-044):**~~ *Superseded by Build 1594 (see the 22:00 section below): no header band.* Was: the chip sits on its own header row; rows start below it and scroll clipped under it, so it never covers a bar or value at any size, mode or scroll.
- [ ] **One shared scale for split bars (1590, QA-078, test `gbar-scale`):** done in v3/build 7013d5f; port the test.
- [ ] **Range bars with the time row closed (1591, QA-077, test `range-bars-closed`):** range bars stay on the icon rows, the old labelled block is gone, width capped at the floating button column.
- [ ] **Top row flush to the safe area (1592, test `top-flush`):** the Topic/Search row starts right at the safe-area top, no empty strip under the status bar.
- [ ] **Chart off returns to its origin view (1592, QA-079, test `chart-off`):** turning the chart off goes back to the view it was opened from (e.g. the map), and reload restores it.
- [ ] **Open QA at 1589 (qa/bugs 438a549):** new QA-081 medium (split-bar rows start about 40 px further from the thumbnails than in the bar list), QA-080 low; QA-020 changed (WebKit Back from Los Angeles County cities 430–473 ms, a v3 latency case). Still open: QA-054, QA-058, QA-057, QA-076, QA-005, QA-007, QA-006.

## Added by the Oct 18, 2026 22:00 EDT drift check (main c34d398, Builds 1593–1595; qa/bugs 0997a90 passes 21–22; perf/speed-baseline 1b4d427; ge0r9b/v3 v3/build 0a39df5)
- [x] **Sort by total votes (1588) and year-correct colours with the 2016 DC delegate seat (1589):** done in v3/build 42ac077 (`packages/core/src/sort.ts`, `fillDcDelegate2016`, tests `list-sort`, `colors-2016`). Both earlier flags are closed.
- [ ] **List names left-aligned at x=52 in every list mode (1593, QA-081, test `list-name-x`):** bar, split and range lists all start the name at the same x, with the bars right after the names. v3/build 42ac077 already puts split bars next to the names; port the test at phone and wide sizes.
- [ ] **Nationwide at-large rows (1593, QA-080):** the nationwide US House list reads `DE At-large` with the title "Delaware at-large" (no `DE-00`).
- [ ] **Sort chip floats over the list top (1594, user, test `sort-chip-clear`):** replaces the 1590 header band. Rows start right under the slider row; the chip floats over the top of the list; at rest, any value label, name or net figure it would cover is shifted left of the chip, and while scrolling, content passes under it like under the right-hand buttons. QA-082 (6 px row/chip bounce from the header band) is gone with it.
- [ ] **Chip and chevron line fixed from the first row's resting top (1595, QA-083, test `chip-fixed-scroll`):** the chip and back chevron never move with the list's scroll.
- [ ] **Clearer unselected floating buttons (1594, user, iOS match):** unselected Liquid Glass buttons drop the backdrop blur and use a lower-alpha white fill; the dark rim and lift keep them legible; selected buttons stay dark. Text fields (Topic, Institution, geography, search) are always opaque white. Update the glass design tokens to match (no blur on unselected).
- [ ] **State outlines on top and thicker (1595, user, test `state-lines`):** state lines draw above every sub-state layer (districts, precincts/towns, counties). Width 2.2 px at z5, 2.6 at z6, 3 px from z7 on phones, plus 0.6 px on wide screens; district lines stay 0.6–1.6 px. In v3 this is a MapLibre layer-order and line-width rule: the state line layer goes last, with a zoom-interpolated width.
- [ ] **Open QA at 1595 (pass 22):** QA-076 medium (name bubble covers the photo on phones, floats far from it on iPad); QA-007 borderline (All States row 92–101 ms); QA-005, QA-006, QA-020, QA-054, QA-057, QA-058 unchanged.
- [ ] **Perf at 1595:** within noise of 1588. All tap medians under 100 ms; phone pan 59.6–60.0 fps; iPad pan 47.9 fps, so iPad pan ≥ 55 fps stays a v3 gate.
- **Not on main, so not parity yet:** us-districts `preview/shadows` (4394663) is a UI preview lane with pressed-metal Liquid Glass buttons, a crisp drop shadow and subtle bar, pie and line shadows. Treat it as a proposal until it lands in a v2 build.

## Added by the Oct 19, 2026 00:00 EDT drift check (main f9e148f, Builds 1596–1597; qa/bugs 71e0b5d passes 23–24; ge0r9b/v3 unchanged at v3/build 0a39df5)

- [ ] **US House inside a county (1596, QA-005, test `ushouse-in-county`, Chromium + WebKit):** with US House picked inside a county, the list is "List all US House districts in <county>": the county's districts by number, split ones marked ≈, like the other district types. Deselecting returns to the townships list. In v3 this is an `/api/v1` county-to-district overlap query (whole versus partial), not browser logic.
- [ ] **Row taps use the finger's real point (1596):** a tap on a row name next to the thumbnail column drills into the row; Chromium/Android touch adjustment must never retarget it to the thumbnail and toggle the candidate. v3 list rows hit-test at the touch point (`elementFromPoint`), and native clients get the same rule.
- [ ] **Name bubble placed beside the photo (1597, QA-076, test `icon-bubble`):** the thumbnail name bubble anchors on the photo itself (not the whole 300 px chart-view row), on the photo's row at the nearest spot that covers no value label (`49.9%`, `+3.1`) and no other photo: right of the photo, left of it, or just past a label, else just above or below. On tight phone range rows it shortens to surname plus year (`Trump ’24`) with the full name as its title.
- [ ] **QA-084 HIGH, a v3 gate (open at 1596):** split-bar list rows first draw at 30 px and then grow to 44 px on every drill-in and Back (up to about 180 px drop by row 14; 150–530 ms on first visits). v3 must draw list rows once at their final height for the chosen chart, so the row height comes from the chart mode before data arrives, and skeleton rows use that same height.
- [ ] **QA-085 HIGH slow tap, a v3 latency case (open at 1596):** year taps on Pennsylvania's district-type maps take 150–425 ms to paint (state house median 346 ms at 1024×576). v3 year switches must stay under 100 ms on every layer: per-year colours come from a preloaded pack and a paint-property or feature-state change, never a source reload.
- [ ] **Open QA at 1596 (pass 24):** QA-005 fixed (both engines, 390 and 1024×768); QA-076 fixed in 1597, still to be re-verified; QA-084, QA-085 open; QA-006, QA-054, QA-057, QA-058 unchanged. Watch item, not filed: a tiny repeating layout shift (0.0004–0.0023) for about 6 s after the # toggle on the All States list, source unknown, possibly the harness.
- **Previews on main, still proposals:** main now carries `previews/shadows/` (pressed-metal Liquid Glass buttons, faint thumbnail shadow, subtle bar, pie and line shadows) and `previews/compact/` (while panning or after a map tap, the Topic and Institution bars collapse to their seal and flag icons on the thumbnail axis; tapping an icon expands its bar; the Institution filter button is dark while expanded and light when collapsed; nothing moves, only the strips fade). Both are noindex pages built by `tools/mkpreview.py` that load v2 data by relative path, and `/v2/` is untouched. They aren't parity until a v2 build adopts them. If one is adopted, v3 takes the shadows as design tokens and the compact state as a shared UI state, not page CSS.

## Added by the Oct 19, 2026 02:00 EDT drift check (main c19f7a0, Builds 1598–1599; qa/bugs 136695c pass 25; ge0r9b/v3 v3/build 8324e6f)

- [ ] **QA-084 in v3 (1598, test `gbar-rows-first-paint`):** v2 1598 lays out the first 40 split-bar rows without content-visibility so they draw at 44 px in the first frame; pass 25 says Back and repeat drill-ins are clean but first visits still go 30 → 44 px. v3/build 8324e6f locks `SPLIT_ROW_PX = 44` in `packages/core/src/parity.ts` (with a CSS test) and perf:client checks the first-frame height. Keep the gate open until perf:client passes on first-visit drill-ins at 390 and 1024×768 in WebKit too, not just Chromium.
- [ ] **QA-085 in v3 (1599, test `year-tap-speed`):** v2 now recolours district maps and the state district overlay in place, skips the hidden county layer while a district type is on, and prefetches the other years when the time row opens (WebKit medians 32–75 ms at 390/375/320). v3/build 8324e6f switches 2016/2020/2024 with feature-state and no tile or source reload, and perf:client checks each switch under 100 ms on state, county and US House. Still to add: Pennsylvania state house and state senate maps, which were the slowest QA-085 cases.
- [ ] **Boundary slivers aren't towns (1599, QA-006):** a town that appears in two counties only by a tiny boundary sliver (Rockledge borough's 0.006 km² piece on the Philadelphia line) is not listed in the other county. In v3 this is a minimum-overlap rule in the county-to-town query (area threshold in PostGIS, baked into the pack), not browser logic.
- [ ] **Typo matches only as a fallback (1599, QA-067):** search shows fuzzy matches ("America" ~ "Africa") only when nothing really matches. Put this rule in the shared search core so the Worker and native clients behave the same.
- [ ] **Range thumbnails carry their own year (1599, QA-051):** in a '16 > '20 range, list thumbnails are labelled with the candidate's year (2020), not the ending year of the view.
- [ ] **State pick clears the DC name lock (1599, QA-061)** and **a DC address opens at the address (1599, QA-068):** a geocoded DC address zooms to that point (about z15), not the whole District. In v3 the geocoder result carries the point and the client centres on it.
- [ ] **Readable NY precinct crumb (1599, QA-069):** the breadcrumb uses the display name of the precinct, not its raw id.
- [ ] **QA-086 MEDIUM (open, partly addressed in 1599, test `range-bubble-closed`):** with the time row closed on a range chart, tapping a thumbnail showed no bubble (WebKit) or the old dark party bubble over the clock button (Chromium). 1599 suppresses the dark bubble on thumbnails and shows the white icon bubble. v3 has one name-bubble component for every chart state, with no separate party bubble on thumbnails.
- [ ] **Open QA at 1598 (pass 25):** QA-076 verified fixed; QA-084 partly fixed; QA-085, QA-006 open (both addressed in 1599, not yet re-verified); new QA-086; QA-005 and the verify list hold.

## Added by the Oct 19, 2026 04:00 EDT drift check (main 5850c12, Builds 1600–1604; qa/bugs cced02f pass 26; ge0r9b/v3 unchanged)
- [ ] **QA-084 cache key (1602, test `gbar-rows-first-paint`):** any v3 row or skeleton cache must include the chart mode (bar, split bar, range, pie) in its key, so a cached 30 px bar row never paints on a first split-bar visit. Pass 26 verified 1602 clean on cold and bar-then-split visits at 390 and 320; v3 perf:client should run the same bar-then-split sequence in WebKit and Chromium.
- [ ] **List first, map second (1603, QA-020, test `back-la-speed`):** in the list view, Back, row taps and crumb taps paint the list in the same frame and let the map layers under it (precinct heat, about 25,000 CA precincts after Back from LA County) follow a frame or two later. v3 rule: list renders from the pack/API response first; MapLibre restyle is scheduled after. Budget: Back from LA County cities to CA counties under 100 ms in WebKit (v2 now 45–61 ms).
- [ ] **Alias hits suppress fuzzy look-alikes (1604, QA-067, test `inst-search-real`):** when a query matches an alias ("America" = United States), only the alias target and real substring matches are listed, never typo neighbours like South Africa or Amelia County. Put the alias table and this rule in the shared search core (Worker, browser and native), and test through the real search field, not just the ranker: pass 26 showed the unit check passing while the real field still failed.
- [ ] **QA-085 Chromium gap (pass 26):** WebKit year taps on PA district maps are now 27–68 ms medians, but Chromium is still 112–188 ms medians (1024×576 state house 188, state senate 172). v3 perf:client must check year switches on PA state house and state senate in Chromium as well as WebKit, under 100 ms.
- [ ] **QA-086 single bubble (1600/1601, verified fixed):** the name source must exist on every thumbnail in every chart state, including range charts with the time row closed. v3's one bubble component reads the name from the row's data model, not from whichever attribute a chart variant happened to set.
- [ ] **Open QA at 1602 (pass 26):** QA-006, QA-051, QA-061, QA-068, QA-069, QA-084, QA-086 verified fixed; QA-085 fixed in WebKit only; QA-067 open (addressed in 1604, not re-verified); QA-007 (All States row 114 ms at 1024×768) and the verify list hold.

## Added by the Oct 19, 2026 06:00 EDT drift check (main 101924c, Builds 1605–1607; qa/bugs 0551f80 passes 27–28; ge0r9b/v3 unchanged)
- [ ] **Address search equals the row tap (1605/1607, QA-087 CRITICAL, test `addr-from-list`):** a geocoder hit typed from any list view must end in exactly the same state as tapping that place's row (title, rows, thumbnails, field, selected row), and the selected row is scrolled into view. v3 rule: the geocoder result is turned into the same place selection the list uses (one `selectPlace` path in the shared core), never a separate title-only path. Test it from All States and from a deep list (PA > Philadelphia townships) in both engines, with the "title matches the numbers" check.
- [ ] **Fields stay usable when the focused field is removed (1605, WebKit):** v3's search fields must not stay disabled after a view swap removes the focused input; test typing in the bottom field from list views in WebKit.
- [ ] **Thumbnails never move on drill-in or Back (1606, QA-089, test `thumbs-no-drop`):** the back chevron gets reserved space at every level, including All States, so the list thumbnails keep the same y at all depths. Add the thumbnails and the sort chip to v3's layout-jump sweep.
- [ ] **Word-start matching in name search (1606, QA-088, test `inst-search-real`):** fuzzy and substring matches count only at word starts ("usa" must not hit "Colusa"). Put this in the shared search core with the alias rule from 1604, and keep the 12-query set from pass 28 (America, USA, Afrika, Penn, Ohio, Pensylvania, Philadelphia, Calif, uk, Allegheny, Georgia, Amelia) as a v3 fixture.
- [ ] **Map heat on idle in list view (1606, QA-020, test `back-la-speed`):** v2 now shows rows 158–198 ms after Back, still over 100 ms. v3 keeps its target of rows under 100 ms in both engines; build the map heat (58 CA counties) only on idle after the rows, and never build a statewide precinct layer on Back.
- [ ] **QA-085 remaining case (pass 28):** v2's Chromium PA district maps now pass, but the plain PA county map at 1024×576 is still a 129 ms median. v3 perf:client must include year switches on the PA county map at 1024×576 in Chromium, not only the district maps.
- [ ] **Open QA at 1606 (pass 28):** QA-087, QA-088, QA-089 verified fixed; QA-020 much better but over 100 ms; QA-085 open only for the PA county map in Chromium; QA-007 (All States row 101–110 ms at 375, 1024×576, 1024×768) and the verify list hold; the periodic layout-shift watch item after the # tap is gone.

## Added by the Oct 19, 2026 08:00 EDT drift check (main b3a622e, Builds 1608–1610; qa/bugs 6ef3429 passes 29–30; ge0r9b/v3 v3/build 7e89357)
- [ ] **Same-name school districts carry their county (1610, QA-074, test `school-dups`):** within a state no two school-district rows may show the same name. v3 gets `display_name` from the load (DATA_LOADING.md §9.15), and the test checks uniqueness in every state in both engines at 390.
- [ ] **Saved map position is the place the user picked (1609, QA-091):** when a map move is still pending behind the list, the saved state (URL hash and local storage) stores the pending target, not the hidden map's current view. Right after an address search the map keeps the address position (zoom 15) and later focus zooms don't override it. In v3 the saved view comes from the shared-core selection state, never read back from a hidden map. Test: a DC address from PA > Philadelphia townships, then reload and open the map in WebKit, should land on DC at zoom 15.
- [ ] **Scroll to the selected row exactly once (1609, QA-090, test `addr-from-list`):** after an address search from a list, scroll only after the re-entered list has settled, and never jump back to the top. The test samples `scrollTop` every frame.
- [ ] **Back rows under 100 ms (1608, QA-020, verified 41–79 ms in pass 30):** v2 now meets the v3 target. It got there by settling the list in the same frame, finishing Back to All States at once with no county to wait for, delaying the hidden map's move by 600 ms, and drawing the focus outline and heat on idle. v3/build 16dcf8d already paints rows before heat. Keep `back-la-speed` (both Backs) as a v3 gate in both engines.
- [ ] **QA-093 CRITICAL (open on 1609, orchestrator ruling 7:46 AM EDT):** pick DC in All States (by tap or address), then switch to the map, and v2 draws DC but titles it "United States" over US numbers. v3 rule: the title, numbers, outline and bottom field all come from one selection object, so switching views can't split them. Add "title matches the numbers after a list-to-map switch" for DC (and one state) to the v3 view-switch test. *Fixed on Build 1611 / closed in v2 (pass 32); keep as a v3 gate — see the 10:00 section (and QA-103 reload).*
- [ ] **QA-092 MEDIUM (open on 1609):** from the All States list the globe opens the map at zoom 2 (a hemisphere). For the US level v3 opens the lower-48 fit (about zoom 4) on every path, including the first switch with no drill-in before it. *Fixed on Build 1611 / closed in v2 (pass 32); keep as a v3 gate — see the 10:00 section.*
- [ ] **Open QA at 1609 (pass 30):** QA-020, QA-090 and QA-091 verified fixed. QA-085 is borderline in Chromium 1024×576 (state house median 105 ms, senate 62, county map 90; runs swing). QA-007 is at 103 ms at 1024×576 and 1024×768. QA-018, QA-073 and QA-092/093 are open. QA-067/088 and QA-006/015 hold.

## Added by the Oct 19, 2026 10:00 EDT drift check (main f435ab2 Build 1611; qa/bugs 1afb5d8 passes 31–32; perf 5a48ac1; data/election f940021; ge0r9b/v3 v3/build a7d0a0c)
- [ ] **QA-093 and QA-092 closed in v2 (verified 1611, both engines 390 and 1024×768):** mark closed in v2, but keep as v3 gates that v3/build a46349b / 37db955 already aim at (title matches numbers; US home zoom ~4; reload restores exact selection — see QA-103). QA-090/091/087 hold.
- [ ] **QA-103 CRITICAL (new at 1611, by QA-093 ruling):** reload of a DC map view must restore the exact DC selection (title "District of Columbia", Harris 90 / Trump 6), including the `dc` flag. If DC is not restored, show a clean US view at zoom 4 under the US title — never US title/numbers over a DC outline. v3: saved selection (URL / local storage) includes the DC flag and is applied before first paint.
- [ ] **QA-094 CRITICAL:** a county's city-list header and totals must be the county's own result row, not the sum of listed cities (Harris showed 56/42 vs county 52/46; also Miami-Dade, Maricopa). In v3 the list header reads the parent unit's result, never an aggregate of children.
- [ ] **QA-095 CRITICAL:** district-type list totals must match FEC / state totals (no 0.5–3.9% shortfall — MI, NY, FL). In v3 every list footer comes from the contest's official total for that unit type, not a sum of visible rows that omit write-ins or minor candidates.
- [ ] **QA-098 CRITICAL:** a non-DC address from All States must end exactly as tapping that place's row (same `selectPlace`); title and numbers come from one unit — never a precinct title over county numbers (Phoenix wrong winner). Same shared-core path as QA-087.
- [ ] **QA-096 HIGH:** city precinct map thumbnails show numbers (list > map).
- [ ] **QA-100 / QA-101 (NY counties):** election packs and load use the NYSBOE-corrected NY county rows from data/election f940021 (`d`=Dem+WF(+WEP), `r`=Rep+Con, `total`=all candidates); recheck Kings vs Brooklyn borough and NY state totals vs FEC after the builder merges to main and a live build ships.
- [ ] **QA-074 uniqueness:** v3/build 63810fb implements load-time `county_hint` + `display_name` (API/packs return it; colliding state refused). v2 labels from 1610 are still not visible in pass 32 — keep the uniqueness gate and `school-dups` test.
- [ ] **Perf (5a48ac1):** iPad pan ≥55 fps is now met in v2 1611 (57.3 fps / 10 dropped, was 47.9 / 55); keep as a v3 MapLibre gate. Back rows stay a gate (1611: 27/23/27/32 ms). Phones ~59.2–59.6 fps; bytes flat.
- [ ] **QA-085 still borderline** in Chromium 1024×576 (state house median 111 ms, senate 105, county map 103). Keep the PA year-switch Chromium checks.
- [ ] **Open QA at 1611 (pass 32):** QA-093 and QA-092 verified fixed. CRITICAL open: QA-094, QA-095, QA-098, QA-103. HIGH: QA-096, QA-100. MEDIUM: QA-097, QA-099, QA-073, QA-085, QA-007. LOW: QA-101. Unchanged: QA-018, QA-074. Orchestrator (~9:35 AM EDT): QA-103 confirmed critical; QA-100/101 data fix pending merge to main.

## Added by the Oct 19, 2026 12:20 EDT drift check (main 7739e72 Build 1614; qa/bugs b0ee03c passes 33–34; perf e048caa; data/election ff5f180; ge0r9b/v3 v3/build ac41801)
- [ ] **QA-103, QA-094, QA-095 fixed in v2 (1612/1613, both engines):** keep as v3 gates — reload restores the exact selection including DC; a county's cities list shows the county's own row; every district list shows the certified state total. v3/build ac41801 implements all three; keep `list-dc-globe` and `county-own-totals` equivalents in both engines.
- [ ] **QA-098 list view (fix in 1614, re-test pending):** after an address search from a list, staying in the list, the crumb and thumbnails both show the searched precinct (Maricopa Precinct 242 Harris 70 / Trump 28; Leon Precinct 42 74 / 24). v3 gate: title = numbers in list view, after the globe, and after reload.
- [ ] **QA-104 MEDIUM (new on 1613):** reload of a county map view (Miami-Dade, Kings) saves `lt:none` and drops the county layer while keeping title and numbers. v3: the saved view includes the active layer type and restores it before first paint; add a county-map reload case to the saved-view test.
- [ ] **QA-097 (WIP in 1614):** reload on a city-level map after a range/chart change must come back as that city map, not the county list. v3 saved view stores view mode (`map`/`list`) and chart/range together with the selection.
- [ ] **Certified state totals (data/election ff5f180, QA-003 under the user's 1%/0.1%/0.01% rule):** state and national headers, thumbnails and list totals read the certified FEC row including others, never a children sum. Gate: every state/year equals `official_state_totals.json`; national equals the sum of the 51 rows; third-party share uses `total − d − r`.
- [ ] **QA-074 suffix width:** the county/grade suffix on same-name school rows must stay visible (v2's 100 px name column cuts it). v3 list rows truncate the base name before the `display_name` suffix.
- [ ] **QA-101 LOW / Kings "New York city" row:** a county list must not label a borough-level row as the whole city; await orchestrator ruling, then mirror it in v3 place naming.
- [ ] **iPad pan 53.8 fps on 1613 (was 57.3):** keep the ≥55 fps v3 gate; flag if the next perf run stays under.

## Added by the Oct 19, 2026 14:00 EDT drift check (main 9f41265 Build 1616; qa/bugs 183963c passes 35–37; perf 40e4b1c; ge0r9b/v3 v3/build 9ff1c3d)
- [x] **Certified state totals (QA-003):** shipped in v2 1615 and in v3/build 8bfe521 from the same ff5f180 file; values match. Keep the per-state/year equality gate.
- [x] **QA-104 county layer on reload:** fixed in v2 1615; v3/build 9ff1c3d restores the layer type from the saved view, with a test.
- [ ] **QA-098 list view:** verified fixed on 1614 (8 addresses × list / list reload / map, both engines). Keep the v3 gate: title = numbers in list view, after the globe and after reload.
- [ ] **QA-097 city map reload:** fixed on 1616 (6 cities, both engines). v3 saved view stores the city (county + place id), view mode and chart/range; add a city-map reload case.
- [ ] **QA-107 CRITICAL (open on 1616, orchestrator confirmed):** a ZIP search, or an address that falls back to its ZIP, shows the ZIP on the map and in the field but the US title and US numbers. v3 gate: a ZIP result selects the precinct (or county) containing its label point, so title, numbers, outline and field all name the same place, also after reload. See GEOCODER.md.
- [ ] **QA-105 LOW (fixed on 1616):** census-GEOID precinct names read "Dauphin Precinct 0270", not "Dauphin Precinct 420430270". v3 builds this into precinct `display_name` at load.
- [ ] **QA-106 LOW (fixed on 1616):** after an address search from a list, the header names the list, never "<precinct> counties".
- [ ] **QA-108 LOW (open, orchestrator: not intended):** at 1024×768 a mouse drag on the time slider knob splits it into a '16–'24 range, while a touch drag moves the single knob. v3: mouse and touch drag the knob the same way; range only through the explicit range control.
- [x] **iPad pan:** 57.3 fps on 1615 (back over the ≥55 gate). Keep the gate.
- [ ] **Open QA at 1616 (pass 37):** CRITICAL QA-107; MEDIUM QA-099, QA-085, QA-073, QA-007; LOW QA-101, QA-108, QA-074. Fixed since 12:20: QA-003, QA-096, QA-097, QA-098, QA-104, QA-105, QA-106.
