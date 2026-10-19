# v2 → v3 parity checklist

**Rule: v2 is feature-frozen. Every v2 build is a pure fix, mirrored into v3/build build by build (never in daily batches).**

**Rule: v3 cannot ship until every line below is ticked.** A line is ticked only when a v3 test or gate exists on `ge0r9b/v3` `v3/build` and passes as far as recorded. Planned or untested items stay unticked. The "Next-version trajectory check" adds a line for every new v2 build fix or QA item (from `us-districts` main, `BUILD` and `qa/bugs`).

Scope: v2 Build 1585 through Build 1617 (us-districts main bc9bb19), plus the user-reported 1617 heat-map bug. Paths are under `v3/` on `v3/build` (9ff1c3d). `perf:client` = `npm run perf:client` (`scripts/perf-client.ts`, Chromium + WebKit, Fast 4G).

- [x] Build 1585 / QA-072: DC keeps its scope for district types (no US totals under DC) — v3 test/gate: tests/api.test.ts::"QA-072 DC totals stay in DC and QA-074 labels same-name units", passing
- [x] Build 1585 / QA-075: US states/counties rank above same-name countries on Enter — v3 test/gate: tests/api.test.ts::"QA-075 ranks the US state Georgia ahead of the country", passing
- [ ] Build 1585: bars sit on thumbnail rows, pie under the slider, list rows never show pies (totaled or split bar) — v3 test/gate: none, untested
- [ ] Build 1586: '16 charts not blank after returning to '16 with 2016 files loaded — v3 test/gate: none, untested
- [ ] Build 1586: menus are overlays (no dim, pie never shrinks/moves when a menu opens) — v3 test/gate: none, untested
- [ ] Build 1586 / QA-060: icons re-measured in the same frame as a map/list switch (no 12>4>12 px jump) — v3 test/gate: none, untested
- [ ] Build 1586 / QA-070: clock button never chases an off-screen spot while All States opens — v3 test/gate: none, untested
- [ ] Build 1587 / Build 1594: sort chip at the right end of the bar area, floats over list top, covered value labels move left; rows start under the slider row — v3 test/gate: none, untested
- [x] Build 1588: High→low ranks by total votes; one toggled answer ranks by that answer — v3 test/gate: tests/list-sort.test.ts::"uses total when every answer is shown, in % and in #" + "ranks a single toggled answer by its votes or its share", passing
- [x] Build 1588: district-type lists show only the number (At-large for 0/AL) — v3 test/gate: tests/parity.test.ts::"shows the district number, and seat 0 as At-large", passing
- [ ] Build 1588: thumbnail column on the topic-icon axis; list-all exits to the map at every level — v3 test/gate: none, untested
- [x] Build 1589 (CRITICAL): '16 district maps colour by the 2016 margin; DC delegate seat takes DC's 2016 statewide result — v3 test/gate: tests/colors-2016.test.ts::"colors Philadelphia, Brooklyn, DC, and rural Pennsylvania from that year's margin" + "fills an empty 2016 delegate seat from DC's statewide votes", passing
- [ ] Build 1590 / QA-044: sort chip line never covers a bar or value at any size/mode/scroll — v3 test/gate: none, untested
- [x] Build 1590 / QA-078: split-bar lists use one shared scale — v3 test/gate: tests/parity.test.ts::"QA-078 uses one shared max for split bars in a range", passing
- [x] Build 1591 / QA-077: range bars stay on icon rows with the time row closed — v3 test/gate: tests/parity.test.ts::"QA-077 returns icon-row changes and no names", passing
- [ ] Build 1592: Topic/Search row flush at the safe-area top — v3 test/gate: none, untested
- [ ] Build 1592 / QA-079: chart off returns to the view it was opened from; reload restores it — v3 test/gate: none, untested
- [x] Build 1593 / QA-081: list names/bars start at one left edge in every list mode — v3 test/gate: tests/parity.test.ts::"starts split bars at the same left edge as stacked bars", passing — PARTIAL tick: the test checks only the shared bar left edge, not names left-aligned at x=52 in every list mode; add a name-x check before ship
- [ ] Build 1593 / QA-080: nationwide at-large rows read "DE At-large" (title "Delaware at-large") — v3 test/gate: none for the nationwide label, untested
- [ ] Build 1594: unselected floating buttons without backdrop blur; text fields always opaque white — v3 test/gate: none, untested
- [ ] Build 1595: state outlines on top of every sub-state layer and thicker — v3 test/gate: none, untested
- [ ] Build 1595 / QA-083: chip/chevron line fixed from the first row's resting top — v3 test/gate: none, untested
- [ ] Build 1596 / QA-005: US House inside a county lists that county's districts (split ones ≈); row tap at the real finger point — v3 test/gate: none, untested
- [x] Build 1597 / QA-076: name bubble beside the photo, never over a photo or label — v3 test/gate: tests/parity.test.ts::"QA-076 anchors the name bubble on the photo", passing
- [x] Build 1598 / Build 1602 / QA-084: split-bar rows at final 44 px height in the first frame, cache keyed by chart mode — v3 test/gate: tests/parity.test.ts::"locks split-bar rows at 44px, above the 30px thumbnail slot", passing
- [x] Build 1599 / Build 1605 / QA-085: year taps recolour in place, fast — v3 test/gate: perf:client paCountyYears + paHouseYears (PA county / state house, <6 ms, both engines), passing
- [ ] Build 1599 / QA-006: boundary slivers dropped from county town lists (Rockledge) — v3 test/gate: none, untested
- [ ] Build 1599 / Build 1604 / QA-067: typo matches only when nothing really matches; a synonym hit drops look-alikes — v3 test/gate: none, untested
- [ ] Build 1599 / QA-051: '16>'20 list thumbnails labelled 2020 — v3 test/gate: none, untested
- [ ] Build 1599 / QA-061: a state pick clears the DC name lock — v3 test/gate: none, untested
- [ ] Build 1599 / QA-068: a DC address opens at the address — v3 test/gate: planned (perf:client savedAddress covers the list case only), untested
- [ ] Build 1599 / QA-069: readable NY precinct crumb — v3 test/gate: none, untested
- [ ] Build 1599 / QA-086: white icon bubble on range-chart thumbnails with the time row closed — v3 test/gate: none, untested
- [x] Build 1603 / 1606 / 1608 / QA-020: list Back/drill paints rows first, Back under 100 ms — v3 test/gate: perf:client listBackRows (5 ms Chromium / 17 ms WebKit), passing
- [x] Build 1605 / QA-087 (CRITICAL): a DC address from a list view selects DC like tapping its row — v3 test/gate: tests/parity.test.ts::"selects a list address and a row tap the same way" + perf:client listAddressCase, passing
- [x] Build 1605: WebKit releases fields when the focused field is removed — v3 test/gate: perf:client detachedField, passing
- [x] Build 1606 / QA-088: "USA" lists only United States (word-start match) — v3 test/gate: perf:client search checks (names.json word-start), passing
- [x] Build 1606 / QA-089: list thumbnails never move on drill-in/Back — v3 test/gate: perf:client listAddressCase thumbs sameBox check, passing
- [x] Build 1607 / Build 1609 / QA-090: DC row scrolled into view exactly once after a DC address search — v3 test/gate: perf:client scrollOnce, passing
- [x] Build 1609 / QA-091: saved map position after that search is DC (zoom 15) — v3 test/gate: perf:client savedAddress + tests/saved-view.test.ts::"stores the address target and ignores the map hidden behind the list", passing
- [x] Build 1610 / QA-074: same-name school districts labelled with their county; names unique per state — v3 test/gate: tests/schools.test.ts::"finds Brown, Pike, and Meigs from the district outlines" + "keeps every state's display names unique, and the suffixes to a few KB", passing
- [ ] Build 1612 / QA-074: school rows drop "School District" with a short county suffix; suffix never cut — v3 test/gate: planned, untested
- [x] Build 1611 / QA-093: DC picked in All States then the globe shows DC's title and numbers — v3 test/gate: perf:client dcOnMap (Harris 90 / Trump 6), passing
- [x] Build 1611 / QA-092: All States keeps the zoom-4 lower-48 view — v3 test/gate: perf:client usGlobe, passing
- [ ] Build 1612 / QA-103: one selection path; reload restores the exact selection incl. DC — v3 test/gate: implemented in ac41801, no dedicated reload test, untested
- [x] Build 1612 / QA-094: a county's cities list shows the county's own result — v3 test/gate: tests/parity.test.ts::"shows the county total on a city list and the official total when a district sum misses 0.1%", passing
- [x] Build 1612 / QA-095: a state's district list shows the official state total — v3 test/gate: tests/parity.test.ts::"shows the county total on a city list and the official total when a district sum misses 0.1%" + tests/district-fec.test.ts, passing
- [ ] Build 1612 / QA-096: a city's precinct list > globe shows the city's numbers — v3 test/gate: none, untested
- [x] Build 1613 / QA-100: NY county data from official NYSBOE results (62 counties) — v3 test/gate: tests/ny-counties.test.ts::"loads all 62 counties for 2016, 2020, and 2024 from f940021" + "sums to the NYSBOE state totals, and 2016 matches the FEC state row", passing (not yet loaded on Neon)
- [ ] Build 1613: a DC address searched from a list opens the map on the address (field, pin, zoom 15) — v3 test/gate: planned, untested
- [ ] Build 1612 / 1614 / QA-098: list view after an address search shows the searched precinct (title = numbers in list, after globe, after reload) — v3 test/gate: planned, untested
- [x] Build 1615 / QA-003: certified state totals for state rows, thumbnails, national sum — v3 test/gate: tests/official-states.test.ts::"matches the file within 0.1% per state and 0.01% for the United States" + "uses the certified row when a county sum misses the file" (v3 8bfe521), passing
- [x] Build 1615 / QA-104: county layer restored on reload — v3 test/gate: tests/saved-view.test.ts::"keeps a county layer and never stores lt none" + perf:client countyMapLayer (v3 9ff1c3d), passing
- [ ] Build 1615 / QA-101: NYC borough rows read "New York city (Brooklyn part)" — v3 test/gate: awaiting orchestrator ruling, untested
- [ ] Build 1616 / QA-097: city map reload restores the city — v3 test/gate: planned, untested
- [ ] Build 1616 / QA-105: census-GEOID precinct names read "Dauphin Precinct 0270" — v3 test/gate: planned (precinct display_name at load), untested
- [ ] Build 1616 / QA-106: header never reads "<precinct> counties" after a list address search — v3 test/gate: none, untested
- [ ] Build 1617 / QA-099: chip lists — v3 test/gate: none, untested
- [ ] Build 1617 / QA-107 (CRITICAL): a ZIP search (or address→ZIP fallback) selects the containing precinct: title, numbers, field, saved state — v3 test/gate: planned (GEOCODER.md), untested
- [ ] Build 1617 / QA-108: mouse drag moves the single slider knob, same as touch — v3 test/gate: none, untested
- [ ] Build 1617 (user-reported heat map): with no district type selected, three shading tiers: state shading when more than one state spans the width, county shading at a few counties across, precinct shading at about one county across — v3 test/gate: perf:client at 390 and 1024×768 in Chromium and WebKit checks the shading layer per zoom tier (state / county / precinct), planned, untested
- [x] Perf gate (1613/1615): iPad panning ≥ 55 fps — v3 test/gate: perf:client ipadPan (61.6–62 fps WebKit), passing
