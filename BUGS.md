# BUGS: us-districts v2 (QA lane)

Tested (pass 1): live https://ge0r9b.github.io/us-districts/v2/ , **build 202610181566** (`window.BUILD`, line 9 of the live v2/index.html).
Date: Oct 18, 2026, ~5:40-6:20 AM EDT. Branch `qa/bugs` from `08d298c`.
Harness: Playwright (Python) 1.x, Chromium (isMobile + hasTouch, iOS UA) and WebKit (hasTouch, iOS UA). Scripts in `qa/` (`flow.py`, `cmp.py`, `nums.py`, `load.py`).
Official sources: FEC "Official 2024 Presidential General Election Results" (https://www.fec.gov/documents/5644/2024presgeresults.pdf, compiled from state election offices, Jan 16 2025) and FEC "Official 2020 Presidential General Election Results" (https://www.fec.gov/resources/cms-content/documents/2020presgeresults.pdf). PA and GA 2024 also confirmed against the PA DOS certification and GA SOS results pages.
Tap latency = touch/pointer event timestamp -> first rAF + task after it (headless approximation of tap-to-next-paint). Flag > 100 ms.

Severity: **Critical** = wrong numbers, crashes, broken buttons/flows. High = spec violation that breaks a flow. Medium = visible spec violation. Low = polish.

## Re-test status (builds 1567 / 1568, Oct 18 ~6:00-6:40 AM EDT)
- QA-001, QA-002, QA-003: **still reproduce on 1568** (same numbers, `qa/cmp.py`).
- QA-004: **not reproduced on 1568** in Chromium 390x844. Enter on the White House address now goes to DC at zoom 15, Enter on "350 5th Ave, New York, NY 10118" goes to New York County, and tapping a suggestion also works. The WebKit run at 375/320/1024x576, made while the build switched from 1567 to 1568, still failed (b1567-we-375-addr-result.png). Recheck in WebKit.
- QA-005: reproduces in WebKit at all 5 sizes (1566 and the 1567/1568 switchover run). Not rechecked in Chromium on 1568.
- QA-006 (Rockledge in Philadelphia County): **still on 1567**, all sizes (b1567-ch-390-drill-county.png).
- QA-011 (names cut off): **still on 1567**. The name column is 84 px wide; "Philadelphia city" needs 107 px, "Rockledge borough" 129, "Philadelphia Precinct 5844" 173 (b1567-ch-390-drill-county.png, b1567-ch-390-drill-town.png).
- QA-007: in WebKit at 375/320/1024x576, All States is 273-388 ms and the US House pick 219-285 ms, so these still reproduce. Deselecting the type is 107 ms at 320 and opening the institution menu 180 ms at 375. Drill-ins are now fast (6-45 ms), except the cases in QA-020.
- QA-009 reproduces in WebKit at 320x568.

## Re-test status, build 1569 (Oct 18 ~6:35-6:55 AM EDT)
- QA-001/002: fix pending deploy. Live 1569 still shows OR 2024 1,228,410 / 910,702 and KS 2020 558,669 / 758,100. Re-verify when the data build ships.
- QA-004: **fixed in Chromium and WebKit** (390x844): Enter on the White House address goes to DC at zoom 15; the NYC address goes to New York County.
- QA-005: **still on 1569 in Chromium** (390x844). Allegheny townships list (131 rows) > US House: 0 rows, header "Pennsylvania", county still Allegheny. shots/b1569-ch-390-qa005-ushouse.png
- QA-017: **still on 1569**, and the state house list differs as well (see QA-029).
- QA-018: **still on 1569** (tapping the OH bar stays on `states`).

## Re-test status, build 1569 (pass 4, Oct 18 ~7:00-7:30 AM EDT)
- The live build was still 1569 (data fixes for QA-001/002 not deployed).
- QA-015: **not reproduced on 1569**. Reload restored the same map centre and zoom for 2020 list, # + pie, range + line, OH counties and State senate. 2016 list: centre moved 0.05 degrees at the same zoom.
- QA-009 also hits more rows at 320x568: "+5.9" (states, % delta bar), "+3.7" and "−35K" (PA counties, delta bar) under the Chart button (shots/b1569-ch-320-sw-*-rangebar.png).
- QA-030 at 4x CPU, 1569, more sizes. List median/max ms: US House 95.5/**185** (375), 77/139 (320), 82.5/128 (1024x576); county 95/147 (375), 93/115 (320), 90.5/98 (1024x576). Map median/max ms: US House 164/504 (375), 131/231 (320), 137.5/266 (1024x576); county 232/340 (375), 243/278 (320), 221/431 (1024x576). Fast drags always end consistent on 2020.

## Re-test status, build 1571 (pass 5, Oct 18 ~8:05-8:35 AM EDT)
- Live build moved 1569 > 1570 (07:12) > 1571 (08:02). Smoke flow at all 5 sizes in Chromium and WebKit (touch), FEC compare, 2016 checks (`qa/y16.py`, `qa/y16b.py`, `qa/y16c.py`).
- QA-001: **fixed on 1571** (OR 2024 matches FEC). QA-002: **fixed on 1571** (KS 2020 matches FEC).
- QA-003: RI 2020 now matches. **Still on 1571**: ME 2020 Biden -4,599 / Trump -838; PA 2020 +1,694 / +589; CA 2020 -486 / -468; WI 2020 -193 / -119; IN 2020 +79 / +333; AL 2020 +24 / -2; VA 2024 +1,617 / +988; MA 2024 +27 / +5; NH 2024 +8 / +55. NY 2020 changed: now Biden 5,244,886 / Trump 3,251,997, which is +13,901 / +7,199 against the FEC table (was +13,021 / +5,432); needs a check against the NY BOE certification. National 2024 badges 77.30M / 75.02M now match FEC.
- 2016 US total (thumbnails and bar panel): Clinton 65,853,514 / Trump 62,984,828 = FEC exactly. The 2016 state table (`DS16.states`) matches FEC for all 51.
- 2016 at every level shows numbers now (states, PA counties, Philadelphia towns, precincts). Chart type pie and bar stays when the slider moves '16 > '20 > '24 (1571 fix verified).
- QA-005: **still on 1571**, all 5 sizes, both engines (US House from a county list: 0 rows).
- QA-007: **still on 1571**. All States 200-298 ms (Chromium), 294-432 ms (WebKit); US House pick 208-350 ms (Chromium), 230-405 ms (WebKit).
- QA-009: **still on 1571** at 320x568 ("−1.83M" under the Chart button), both engines.
- QA-015 / QA-034: unchanged on 1571 (2016 list reload moves the map centre 0.05 degrees; map view reloads as list).
- No console errors, page errors or failed requests in any run.

## Re-test status, builds 1573 / 1574 (pass 6, Oct 18 ~9:00-9:50 AM EDT)
- Live build moved 1571 > 1572 > 1573 (seen 09:01) > 1574 (seen ~09:25, mid-run). Checks: `qa/pie1574.py`, `qa/y16b1574.py`, `qa/r16reload1574.py`, `qa/r16line1574.py` (Chromium, touch).
- The box was overloaded during this pass (load average up to 184 on 8 cores, then memory full from other lanes' data builds), so the full 5-size smoke flow and the WebKit runs crashed with page timeouts and "Target crashed". Those failures are the environment, not the app; tap timings from this pass are only from the quiet windows. Full smoke at all 5 sizes is carried to the next pass.
- QA-038: **fixed on 1574** (390x844, Chromium). A '16 > '24 range now shows the change rows (FL R +11.9, CA R +10.0, NY R +9.8), Line is offered, and reload restores '16 > '24 for Bar and Pie. A new problem with Line in this range is logged as QA-043.
- 1573 pie (thumbnails only): **passes** at 390x844, 320x568, 1024x576, 1024x768 for United States, Massachusetts and Pennsylvania in # and %: two thumbnails, winner on top (Harris in MA, Trump in US and PA), no names or numbers beside them, nothing overlaps the pie, and a touch tap shows the standard bubble with the full name and value ("Kamala Harris · 2.13M" in MA). Tap to paint 14-34 ms. 375x667 passed for US and MA # before the run was cut off. Screenshots shots/b1574-ch-390-pie-*.png, shots/b1574-ch-320-pie-*.png, shots/b1573-ch-1024-pie-*.png.
- Not checked this pass: 1572 per-unit 2016 map colours (the list map is drawn on canvas, so my path count found nothing; needs a pixel check next pass), QA-039..QA-042 and QA-005/007.

## Re-test status, build 1575 (pass 7, Oct 18 ~9:52-10:30 AM EDT)
- Live build moved 1574 > 1575 (first rows start 16px lower band instead of 31px, so the first row slides halfway under the sort chip; clearer chip glass). Checks: `qa/b1575-rows.py` (5 sizes x All States / PA counties / Philadelphia towns x % / # x bar / pie / range line / range bar, plus back to states), `qa/flow1575.py` (smoke at all 5 sizes), `qa/r16line1575.py`, `qa/b1575-numjump.py`. Chromium, touch. Box load was moderate this pass; no crashes.
- 1575 rows-up: works as described for bar and pie rows. The first row top is 198 px at every size, level, mode and chart type, and the sort chip, slider, chart button, top fields and time row did not move on any view switch, drill-in or back. The chip only grazes text at 320x568 range bar (4 px of the name's 20 px height) and the pie at 320 (6 px), both still readable. **New: QA-044** (line rows at 390 and 375: the first row's change number sits under the chip).
- Layout sweep: no jumps on 1575. `#laCands` (thumbnails) sits at y 191 on the US list and y 221 below it (room for the back chevron), unchanged since 1567 (see QA-021). One smoke run at 1024x576 logged a 0.176 layout shift on `#laCands` / `#listView` right after the `#` toggle; not reproduced in a second smoke run or in 12 more `#` taps at 1024x576 (`qa/b1575-numjump.py`), so not logged as a bug yet.
- QA-022: the chip-on-lines half **not reproduced on 1575** at 1024x768 (the chip now sits above NY's lines). The WY label collision was not rechecked.
- QA-043: **still on 1575** (390x844). '16 > '24 range, then Line: the left knob jumps to '20 and the rows show '20 > '24 (NY +5.9 / -4.5); reload keeps '20 > '24.
- QA-005: **still on 1575**, all 5 sizes (US House from the Allegheny townships list: 0 rows).
- QA-007: **still on 1575**. All States 238-380 ms (762 ms in one 1024x576 run under load, 253 ms on the rerun); US House pick 205-528 ms.
- QA-041: **still on 1575**. Line from the chart menu 126-277 ms (390: 139, 375: 219, 320: 131, 1024x576: 277 / 126 on the rerun, 1024x768: 131).
- QA-009: **still on 1575** at 320x568 ("−1.83M" under the Chart button in the range bar list).
- QA-039 / QA-040 / QA-042: not rechecked (1575 changed no data).
- No console errors, page errors or failed requests in any run.

## Re-test status, build 1575 (pass 9, older open bugs + WebKit smoke + stability at 375/320/1024x576, Oct 18 ~11:00-11:25 AM EDT)
- Live build still 1575 (`window.BUILD` 202610181575; `main` unchanged since 7a23208, 9:46 AM EDT). The box restarted at ~10:55 AM EDT (Playwright browsers and WebKit system libraries had to be reinstalled; the clone was restored and pass 8's commit f84390e is intact). Scripts: `qa/b1575p9-gaps.py` (search, double-tap), `qa/b1575p9-retest.py` (QA-004/005/017/018), `qa/b1575p9-layout.py` (per-frame stability sweep, now also 375x667, 320x568, 1024x576), `qa/flow1575.py webkit <size>` (smoke at all 5 sizes, `qa/flow1575b-webkit-*.json`), `qa/b1575p9-sort.py`.
- **QA-017: fixed on 1575** (390x844, Chromium). Plain All States, State senate, State house and School district lists now show the same state rows: WY 72.3%, ND 67.5% / 30.8%, PA 50.4% / 48.7%, CA 38.3% / 58.5% in all four. The state house list (QA-029) matches too.
- **QA-024: fixed on 1575.** Universal search "Allegheny" + Enter: institution, geo field ("Allegheny County, PA"), crumb and map (zoom 9) all go to Allegheny County.
- **QA-023: changed on 1575, now HIGH.** "Pittsburgh" + Enter in the geo field: the map and crumb go to Allegheny County (zoom 9), but the geo field reads **"No match: East Pittsburgh borou…"**, and East Pittsburgh borough is still the top suggestion above Pittsburgh city. Expected: Pittsburgh city (or at least the picked place's name, not "No match"). Shot: shots/b1575p9-ch-390-geo-Pittsburgh.png
- **QA-025: changed on 1575.** Double-tap at Erie County, PA (zoom 9): the state is now kept, but the map zooms out 9 > 8 and the geo field says "Crawford County, PA" while the crumb still says Erie County. Shot: shots/b1575p9-ch-390-dbltap.png
- Still on 1575: QA-005 (Allegheny townships > US House: 0 rows, crumb "Pennsylvania"), QA-018 (tap on the OH bar stays on `states`), QA-026 (White House > "DC 20220"), QA-028 (ZIP shows "16501"), QA-006 (Rockledge under Philadelphia, data unchanged since 1574). Address Enter (QA-004) still works: NYC address > New York County, zoom 15.
- WebKit smoke at all 5 sizes (touch): no console errors, page errors or failed requests; CLS 0 at 1024x768. QA-044 confirmed in WebKit at 390 and 375 ("−1.83M" under the sort chip in the range line list). QA-009 confirmed in WebKit at 320. QA-007 still: All States 388-652 ms, US House pick 298-350 ms (1,280 ms once at 390 under load), deselect 101-232 ms, opening the institution menu 115-152 ms on phones. QA-041 still: Line 179-247 ms. Also slow in Chromium 390: picking State senate (156 ms) and State house (118 ms) in the institution menu (QA-007 family).
- One 160 ms sort-chip tap in WebKit 1024x768 was not reproduced in 24 repeat taps (12-75 ms WebKit, 15-38 ms Chromium), so not logged.
- Stability sweep at 375x667, 320x568, 1024x576 (Chromium, every frame): QA-053 (time button +5 px), QA-054 (thumbnails -3 / +3 px map/list, 50 px wide for 250-400 ms), QA-057 (chart button hidden while the layers row is open; crumb Worcester > Massachusetts on US House) and QA-058 (thumbnails +23 px on a range) all reproduce at all three sizes with the same pixel shifts. QA-055 (first row jumps on back) and QA-056 (thumbnail flash after the geo menu) did **not** reproduce at these three sizes. Data: `qa/b1575p9-layout-chromium-{375,320,1024x576}.json`; shots shots/b1575p9-ch-*-ls*.png.

## Critical

### QA-001 [Fixed on 1571 (verified 8:10 AM EDT)] Oregon 2024 state totals are short of the official count (~1%)
- Severity: Critical (wrong numbers) | Build 1566 | All sizes (data, seen in list at 1024x768)
- Steps: Institution filter > All States > `#` mode, 2024; find OR (or `__stTot('Oregon','2024')`).
- Expected (FEC 2024): Harris 1,240,600, Trump 919,480.
- Actual: Harris 1,228,410 (-12,190), Trump 910,702 (-8,778). List shows OR 1.23M / 911K instead of 1.24M / 919K.
- Screenshot: shots/chromium-ipad1024x768-allstates-2024-num.png

### QA-002 [Fixed on 1571 (verified 8:10 AM EDT)] Kansas 2020 state totals are short of the official count (~2%)
- Severity: Critical | Build 1566 | All sizes
- Steps: All States > time slider to '20 > `#` mode; KS (or `__stTot('Kansas','2020')`).
- Expected (FEC 2020): Biden 570,323, Trump 771,406.
- Actual: Biden 558,669 (-11,654), Trump 758,100 (-13,306); total 1,349,567 vs 1,372,303.
- Screenshot: shots/chromium-ipad1024x768-allstates-2020-num.png

### QA-003 Other state totals that differ from official (smaller)
- Severity: Critical (wrong numbers, small) | Build 1566 | All sizes
- Compared every state D/R vs FEC (`qa/cmp.py`). Exact matches for 2024: all states except below; PA/GA/MI/WI/AZ/NV/NC 2024 exact.
- 2024: VA Harris +1,617 / Trump +988 over official (2,335,395/2,075,085 vs 2,333,778/2,074,097); MA +27/+5; NH +8/+55.
- 2020: ME Biden -4,599 / Trump -838 (430,473/359,899 vs 435,072/360,737); PA Biden +1,694 / Trump +589 (3,459,923/3,378,263 vs certified 3,458,229/3,377,674); RI Biden -1,276; CA Biden -486 / Trump -468; WI -193/-119; IN +79/+333; AL +24/-2. NY 2020 differs by +13,021 D / +5,432 R vs the FEC table (may be party-line vs fusion totals; needs checking against NY BOE).
- Knock-on: national thumbnails show Trump **77.29M** / Harris **75.01M**; official is 77,302,580 (77.30M) / 75,017,613 (75.02M). App sums: 77,294,850 / 75,007,075.
- Also: "total votes" are low in many 2024 states because write-ins/others are left out (e.g. NY total 8,198,094 vs 8,262,495; IL 5,592,368 vs 5,633,310). That changes every % share slightly (shares are computed on a smaller total). Decide whether the total should be the official total.
- Screenshot: shots/chromium-iphone390-08-allstates-delta.png (77.29M / 75.01M badges)

### QA-004 Address search: Enter does not go to the address
- Severity: Critical (broken flow) | Build 1566 | All 5 sizes (Chromium)
- Steps: any view > tap the bottom geo field > type `1600 Pennsylvania Ave NW, Washington, DC 20500` > wait 2.5 s (two Address suggestions show: "1600 PENNSYLVANIA AVE NW, WASHI…", "White House, 1600, Pennsylvania…") > Enter > wait 7 s.
- Expected (spec 5.2): top match wins; the address pins the point and opens its precinct/county (DC).
- Actual: nothing moves. The field empties, placeholder still shows the previous county ("Philadelphia County, PA" / "Allegheny County, PA"), state/county unchanged, no popup. No console errors, no failed requests.
- Screenshots: shots/chromium-iphone390-18-addr-typing.png, shots/chromium-iphone390-19-addr-result.png (same for iphone375/iphone320/ipad1024x576/ipad1024x768)
- WebKit (390x844, 1024x768): same result.
- Not tested: tapping a suggestion row instead of Enter.

### QA-005 Picking a district type (US House) in list view shows no district list, and the header names the wrong place
- Severity: Critical (wrong label on numbers + spec violation) | Build 1566 | All 5 sizes
- Steps: list view > All States > PA > a county (Philadelphia or Allegheny) > county's townships list > tap district-type button > US House.
- Expected (HANDOFF rule "District type"): list view shows the US House district list (PA's districts), numbers equal the map popups.
- Actual (Chromium and WebKit): the list is replaced by a single-entity chart. The institution field says **"Pennsylvania"** but the numbers are the county's (Allegheny: Harris 429,916 / Trump 283,595; Philadelphia line: -35K / +12K). No district rows (`.lvrow.la` count 0). 
- Screenshots: shots/chromium-iphone375-16-type-ushouse.png, shots/chromium-iphone390-16-type-ushouse.png

### QA-017 [Fixed on 1575 (verified pass 9, 11:15 AM EDT)] The same state shows different totals depending on the district type
- Severity: Critical (wrong numbers) | Build 1568 | 390x844 (Chromium)
- Steps: institution menu > State senate districts > reopen menu > All States. Do the same with School districts. Compare with plain All States.
- Expected: one state total everywhere (WY 2024: Trump 72.3%, Harris 26.1% in the plain list, already computed without write-ins; FEC: 71.6% / 25.8%).
- Actual: State senate list WY 71.5% / 26.4%, ND 67.0% / 30.5%. School list WY 71.8%, ND 67.0% / 30.4%. Plain list WY 72.3% / 26.1%, ND 67.5% / 30.8%. The state rows seem to be sums of district estimates, not the state result.
- Evidence: `qa/last.py` output (senate/school level 1). Screenshot of the end state: shots/b1568-ch-390-senate-list.png


### QA-006 Rockledge borough (Montgomery County) listed under Philadelphia County
- Severity: High (wrong geography in results list) | Build 1566 | 390x844 (data issue, all sizes)
- Steps: All States > time range '20-'24 > PA > Philadelphia > townships list.
- Expected: Philadelphia County contains only Philadelphia city.
- Actual: rows "Philadelphia city" and "Rockledge borough" (-12 / +7). Rockledge is a borough of Montgomery County, PA.
- Screenshot: shots/chromium-iphone390-13-drill-county.png

### QA-007 Slow taps (> 100 ms tap-to-next-paint)
- Severity: High (REPO-RULES 7: instant response is the top priority) | Build 1566
- "All States" row in the institution menu: 185 ms (1024x768), 243 ms (320x568), 261 ms (375x667), 352 ms (1024x576).
- District-type pick (US House) in list view: 433 ms (390x844), 262 ms (375), 265 ms (320), 269 ms (1024x576), 293 ms (1024x768).
- Deselecting the type: 110 ms (375x667). Drill into a town's precincts (Philadelphia city): 141 ms (390x844).
- WebKit confirms: All States 303 ms (390x844) / 431 ms (1024x768); US House pick 319 / 260 ms; town drill-in 195 ms (390x844).
- All other measured taps (sort, %/#, time, chart menu, chart options, drill to state/county, back) were 6-75 ms.
- Steps: see `qa/flow.py` (lat dict in `qa/flow-*.json`).

### QA-008 Delta (change) bar list prints a per-candidate change number inside the bar
- Severity: High (spec violation) | Build 1566 | all sizes
- Steps: All States > `#` > time slider range '20-'24 > bar chart.
- Expected (HANDOFF Lists rule): delta mode = net value at the text indent, bars on one scale, winner thumbnail, **no per-candidate change numbers**.
- Actual: CA row bar shows "−1.83M" (Harris change) inside the bar.
- Screenshots: shots/chromium-iphone390-08-allstates-delta.png, shots/chromium-iphone320-08-allstates-delta.png

### QA-018 Tapping a row's bar or line does not drill in; only the name works
- Severity: High (broken tap target; rule "tapping a row drills down") | Build 1567 | 390x844 and 1024x768, Chromium and WebKit, bar and line lists
- Steps: All States > tap the OH row on its bar or line (55% across the row).
- Expected: drills into Ohio counties.
- Actual: nothing happens (still `states`). Tapping the name "OH" drills in. All 8 combinations behave the same.
- Screenshots: shots/b1567-ch-1024-line-rowtap.png, shots/b1567-we-390-bar-rowtap.png, shots/b1567-ch-1024x768-drill-PA.png

### QA-019 [By design (per orchestrator), not counted as open] State senate and school district lists skip the county level
- Severity: High (spec 7.3 / HANDOFF: school, state house and state senate list as states > counties > districts) | Build 1568 | 390x844
- Steps: institution menu > State senate districts > menu > All States > PA.
- Expected: PA counties, then districts.
- Actual: goes straight to "districts" (50 PA senate districts; 500 PA school districts). One more tap opens precincts.
- Screenshots: shots/b1568-ch-390-senate-list.png, shots/b1568-ch-390-school-list.png

### QA-020 Slow taps that remain after the 1567 drill rewrite
- Severity: High (REPO-RULES 7) | Builds 1567/1568
- Town > precincts drill-in (Philadelphia city): first frame 145 ms (390), 177 ms (375), 205 ms (320) in Chromium on 1567.
- Back from townships to counties: first frame 253-313 ms (phones, 1567).
- State senate district > precincts: 222 ms. School district > precincts: 103 ms (390, 1568).
- Measured from the touch event to the first animation frame. The new rows themselves appear 440-1070 ms after the tap (old rows stay up until then; no skeleton was seen).
- Data: `qa/drill-chromium.json`, `qa/last.py` output


### QA-009 320x568: delta label "−1.83M" sits under the floating chart button
- Severity: Medium (values under the button column) | Build 1566 | 320x568
- Steps: as QA-008 at 320x568.
- Expected: values never under the floating buttons (clamp or hide).
- Actual: "−1.83M" overlaps the chart button (layout check: text box intersects `Chart` button).
- Screenshot: shots/chromium-iphone320-08-allstates-delta.png

### QA-010 Layout shift when switching the list to pie at 320x568 (CLS 0.175)
- Severity: Medium (no layout jumps rule) | Build 1566 | 320x568
- Steps: All States > `#` > single year 2024 > chart menu > pie.
- Expected: CLS 0.
- Actual: one layout shift of 0.175 from `.cpanel` right after the pie switch; small `#listView` shifts (0.003-0.012) at 375x667, 1024x576, 1024x768 around the same step.
- Screenshot: shots/chromium-iphone320-11-chart-pie-single.png

### QA-011 County names truncated with room to spare (delta line list)
- Severity: Medium (clipped text) | Build 1566 | 390x844
- Steps: All States > range '20-'24 > line chart > PA counties.
- Actual: "Montgom…", "Northamp…", "Philadelph…", "Rockledge …" cut at ~110 px although there is empty space before the line column.
- Screenshots: shots/chromium-iphone390-12-drill-PA-counties.png, shots/chromium-iphone390-13-drill-county.png

### QA-012 Phone `#` lists: many rows show no number at all
- Severity: Medium | Build 1566 | 320x568, 375x667
- Steps: All States > `#` (2024 or 2020).
- Expected: a readable value per row.
- Actual: values hide when the scaled bar is too short; at 320x568 PA, OH, NC, MI rows show no numbers (only NY shows one of two); at 375x667 MI shows none.
- Screenshots: shots/chromium-iphone320-05-allstates-num.png, shots/chromium-iphone375-05-allstates-num.png

### QA-021 Thumbnails disappear for a few frames on some drill-ins and backs
- Severity: Medium (no jumps / one-frame rule from 1567) | Build 1567 | 390, 375, 320 (Chromium)
- Steps: delta line list > PA > Philadelphia > Philadelphia city, then back.
- Actual: `#laCands` goes 4,221 > hidden > 4,221 on the town drill-in and on the back to counties. On the back to states it ends at 4,191 with the chevron hidden (expected: chevron hidden at US level).
- Data: `qa/drill-chromium.json` (pos_seq)

### QA-022 iPad line list: the sort chip sits on the first row's lines; change labels collide
- Severity: Medium | Build 1567 | 1024x768 (Chromium)
- Actual: the sort chip (862,185) covers the MO row's red and blue lines. On the WY row, "+2.4" and "−0.5" overlap.
- Screenshot: shots/b1567-ch-1024x768-drill-PA.png

### QA-023 [Changed on 1575, now HIGH] Geo search "Pittsburgh" + Enter goes to East Pittsburgh borough
- Severity: Medium | Build 1568 | 390x844
- Expected: Pittsburgh city (the closest name, far more votes).
- Actual: the top suggestion and the Enter result is "East Pittsburgh borough, Allegheny County".
- Screenshot: shots/b1568-ch-390-geo-Pittsburgh.png

### QA-024 [Fixed on 1575 (verified pass 9, 11:10 AM EDT)] Universal search "Allegheny" + Enter: geo field and map do not follow
- Severity: Medium | Build 1568 | 390x844
- Actual: the institution becomes Allegheny County, but the geo field says "Clinton County, PA" and the map stays at zoom 6.
- Screenshot: shots/b1568-ch-390-search-Allegheny.png (suggestions; end state in `qa/gaps.log`)

### QA-025 [Changed on 1575] Double-tap on the map zooms out and clears the state
- Severity: Medium (spec 6: double-tap zooms to the area and puts its name in the geo field) | Build 1568 | 390x844 (Chromium touch emulation: 2 taps 120 ms apart)
- Steps: Erie County, PA view (zoom 6) > double-tap the map.
- Actual: zoom 6 > 4, state cleared, geo field "Albemarle County, VA". Real-device check needed.
- Screenshot: shots/b1568-ch-390-dbltap.png


### QA-013 % bars run under the floating buttons
- Severity: Low | Build 1566 | 390x844
- Steps: All States, % mode, time row closed.
- Actual: WY/WV/ND bars pass under the clock and chart buttons; KS/TX bars under the type button (their blue labels sit right next to it). Values are hidden there (OK), but the bar ends are covered.
- Screenshot: shots/chromium-iphone390-02-allstates-list.png

### QA-014 Line chart axis label "600K" collides with the Harris endpoint
- Severity: Low (overlapping labels) | Build 1566 | 390x844
- Screenshot: shots/chromium-iphone390-16-type-ushouse.png

### QA-015 Reload restores a slightly different map position
- Severity: Low | Build 1566 | all sizes
- Steps: list view at a county > reload.
- Actual: state, county, chart, #, list view and sort all restore. `ll` changes (e.g. 40.0449,-75.1112 z10 -> 40.0024,-75.1176 z10; Allegheny: every run restores to the same fixed point 40.435,-80.0249 whatever the saved view was, e.g. z11 -> z10) and `lt` "counties" -> "none".

### QA-016 Phone first load cuts off both coasts
- Severity: Low | Build 1566 | 390x844, 375x667, 320x568
- Actual: the initial US map is zoomed to the middle (WA/CA/East Coast off-screen). iPad fits the lower 48.
- Screenshots: shots/chromium-iphone390-initial.png, shots/webkit-iphone320-initial.png

## Passed
- Load at all 5 sizes in Chromium and WebKit: build 202610181566, no console errors, no page errors, no failed requests, no HTTP >= 400, no horizontal overflow, CLS 0 on load (Chromium; WebKit has no layout-shift API).
- Institution menu (All countries / US / All States / district rows / states), All States list, drill-ins US > PA > county > town > precincts, back chevron.
- Sort: default high to low (WY 72.3% first); one tap reverses (DC first); delta sorts by |net| (Philadelphia first).
- % / # toggle; time slider single year 2020 / 2024 and range (delta).
- Chart menu: range offers line + bar, single year offers pie + bar; choices apply.
- 2024 D and R totals exact for 46 states + DC (all but OR, VA, MA, NH), incl. PA, GA, MI, WI, AZ, NV, NC, AK.
- Light mode only and Liquid Glass round buttons (visual check).

### QA-026 White House address is named "DC 20220"
- Severity: Low | Build 1568 | 390x844
- Actual: after Enter or a suggestion tap, the geo field shows "DC 20220". The White House ZIP is 20500.
- Screenshot: shots/b1568-ch-390-addr-wh-enter.png

### QA-027 [By design (per orchestrator), not counted as open] US House list has 436 rows
- Severity: Low | Build 1568 | all sizes
- Actual: the list starts "DC-00 | 92.1%". HANDOFF says 435. Decide whether the DC delegate belongs in it.

### QA-028 ZIP search shows "16501", not "Near ZIP 16501"
- Severity: Low (spec 5.2) | Build 1568 | 390x844
- Screenshot: shots/b1568-ch-390-geo-16501.png

## Passed on 1568 (time slider, list view, Chromium, no CPU throttle)
| Size | US House list ms (median/max) | US House map ms | County list ms | County map ms |
|---|---|---|---|---|
| 390x844 | 19.5 / 22 | 33 / 52 | 22 / 26 | 58.5 / 155 |
| 375x667 | 18 / 29 | 30 / 59 | 23.5 / 37 | 63 / 123 |
| 320x568 | 17 / 20 | 29.5 / 77 | 23 / 25 | 62.5 / 84 |
| 1024x576 | 19 / 22 | 36.5 / 50 | 23.5 / 34 | 62.5 / 150 |
| 1024x768 | 19.5 / 36 | 31.5 / 50 | 23 / 61 | 68 / 104 |
- 8 changes per cell (2020 <> 2024). Time = input event to the first frame where the list text or the map fill colours changed. List first, map later, every time. Everything is under 150 ms except the county map at 390 (max 155 ms) and 1024x576 (150 ms).
- Fast repeated drags (16 changes, 25 ms apart, ending at 2020): list, thumbnails ("Joe Biden 2020") and map popup (KS-01 Biden 34.1% / Trump 63.7%; PA total Biden 50.0% / Trump 48.8%) all show 2020.
- Layout shift during slider changes: only the slider knob itself (`kn a`, 0.005-0.026 per run, programmatic input). No list or thumbnail shifts.
- Map popup = data: Cumberland County, PA popup Harris 66,255 / Trump 80,267 = ELECTION2024 table.
- Searches: "16501" gives a ZIP; "Erie County" lists NY, OH and PA; "PA" and "Ohio" go to the state; "Cook County, IL" works; "PA-07" opens the US House district.
- No console or page errors anywhere; only aborted Esri tiles during map moves.
- Not done: the slider timings with 4x CPU throttle (the orchestrator's numbers likely use it), and the state house list (senate and school only).

## Passed on 1569 (pass 3)
- State house list: drill timing PA > districts 26 ms, district > precincts 43 ms (390, Chromium). It goes states > districts with no county level (QA-019, by design).
- WebKit slider on 1569 (no throttle). List median/max ms: US House 44.5/60 (390), 40.5/98 (1024x768); county 28.5/40 (390), 27.5/33 (1024x768). Map median/max ms: US House 95.5/118 (390), 112.5/133 (1024x768); county 85.5/108 (390), 99.5/163 (1024x768).
- Fast repeated drags (Chromium 4x and WebKit): list, thumbnails and map pop-up all end on 2020. No layout shift except the knob itself (WebKit has no layout-shift API, so 0 there means not measured).
- 2016 shows names only, no numbers (no fabricated data).
- Not done: CPU throttling in WebKit (Playwright has no WebKit CPU throttle), slider timing at 375/320/1024x576 throttled, reload restore of 2016.

## Passed on 1569 (pass 4)
- Reload restore (Chromium 390): '16, 2020, # mode, pie, range + line, OH counties list, State senate type, map centre and zoom all restored (except map vs list, QA-034).
- Layout sweep, 5 sizes x {All States, PA counties} x {%, #} x {bar, pie, range line, range bar}: no text overlapping other text, no text off-screen; issues only as in QA-009 and QA-035.
- 400 random taps: no errors, no failed requests.
- Not done: official totals for the 4 counties above, WebKit monkey and sweep, and reload restore in WebKit.

## New on build 1571 (pass 5)

### QA-038 A time range that starts at '16 never shows the change view, and Line is not offered
- Severity: Critical (broken flow) | Build 1571 | 390x844, 320x568, 1024x768 (Chromium, touch)
- Steps: All States list > open the time row > drag the left knob to '16 so the range is '16 > '24 > wait 10 s > open the chart menu.
- Expected (1571 notes): shows 2016 only until the 2016 change view lands, then the '16 > '24 change rows and change thumbnails; Line is offered for a range.
- Actual: both knobs show '16 > '24, but after 10 s the list and thumbnails still show 2016 single-year values ("DC 90.9%", Hillary Clinton 2016 / Donald Trump 2016). The chart menu offers only Pie and Bar; picking Line does nothing (chart mode stays empty). Reload restores the same stuck state. No "Loading 2016 results" text, no errors.
- Screenshots: shots/b1571-ch-390-y16-range16-10000ms.png, shots/b1571-ch-390-y16-range16-line.png, shots/b1571-ch-320-y16-range16-10000ms.png, shots/b1571-ch-1024-y16-range16-10000ms.png

### QA-039 2016 state totals after a drill-in are county sums, not the official state result
- Severity: Critical (wrong numbers, small) | Build 1571 | All sizes (data; seen at 1024x768)
- Steps: All States > slider '16 > `#` > tap PA; read the bar panel.
- Expected (FEC 2016, `qa/fec16.json`): Trump 2,970,733, Clinton 2,926,441 (the app's own `DS16.states` has these).
- Actual: Trump 2,971,303 (+570), which is the sum of the PA rows in `ELECTION2016` (Clinton sum 2,926,156, -285). Same as QA-017, but for 2016 drill-ins.
- Other states whose 2016 county rows do not add up to FEC (D / R difference): CA -1,726 / -513, AL +60 / +374, TX -3 / -191, IN +29 / -46, NY +13 / +19, SD +8 / +10, KY -7 / -14, MI -1 / -2, WV -2 / 0.
- Screenshot: shots/b1571-ch-1024x768-y16-PA-counties.png

### QA-040 Philadelphia County shows three different 2016 totals
- Severity: Critical (wrong numbers, small) | Build 1571 | 1024x768 (Chromium)
- Steps: '16 > All States > PA > Philadelphia > Philadelphia city; read the bar panel at each level.
- Expected: one total for the same area at every level.
- Actual: county table `ELECTION2016` Clinton 582,697 / Trump 108,711; panel at the county's towns list Clinton 582,909 / Trump 108,945; panel at Philadelphia city precincts Clinton 584,025 / Trump 108,748. (Rockledge borough still listed under Philadelphia, QA-006.)
- Screenshots: shots/b1571-ch-1024x768-y16-phila.png, shots/b1571-ch-1024x768-y16-lvl4.png

### QA-041 Picking Line in the chart menu is slow again (regression)
- Severity: Medium (slow tap) | Build 1571 | All 5 sizes, Chromium and WebKit
- Steps: list view, 2020 > 2024 range > chart button > Line.
- Expected: under 100 ms tap-to-paint (it was 9-29 ms on 1566-1569).
- Actual: 137-197 ms in Chromium (390: 197, 375: 137.5, 320: 141, 1024x576: 147, 1024x768: 155) and 141-184 ms in WebKit.
- Evidence: `qa/flow-chromium-.json`, `qa/flow-webkit-.json` (`lat.chart_line`).

### QA-042 2016 `#` bar: Philadelphia's Trump segment has no number
- Severity: Low | Build 1571 | 1024x768
- Steps: '16 > All States > `#` > PA counties.
- Actual: the Philadelphia row's red segment is about 125 px wide but shows no "109K" label (2024 shows "144K" in the same spot). In the Philadelphia towns list, "Philadelphia city" shows only "583K".
- Screenshot: shots/b1571-ch-1024x768-y16-PA-counties.png

## New on build 1574 (pass 6)

### QA-043 Picking Line in a '16 > '24 range moves the start knob to '20
- Severity: High (silently changes the chosen range) | Build 1574 | 390x844, 320x568, 1024x768 (Chromium, touch); 3 of 3 runs at 390
- Steps: All States list > open the time row > select the full range > drag the left knob to '16 so the range is '16 > '24 (the list shows the '16 > '24 change rows: FL R +11.9) > open the chart menu > pick Line.
- Expected: the range stays '16 > '24 and Line plots '16, '20 and '24.
- Actual: the left knob jumps to '20 and the list shows the '20 > '24 line rows (NY +5.9 / -4.5, NJ +4.8 / -5.2). Reload keeps '20 > '24, so the '16 start is lost. Bar and Pie in the same range keep '16 > '24. No console errors.
- Screenshots: shots/b1574-ch-390-r16-line-afterdrag.png (before picking Line), shots/b1574-ch-390-r16-line-before.png (after), shots/b1574-ch-390-r16-line-reload.png, shots/b1574-ch-1024-r16-line-before.png, shots/b1574-ch-320-r16-line-before.png

## New on build 1575 (pass 7)

### QA-044 Line list: the first row's change number is hidden under the sort chip
- Severity: High (a number on the first row can't be read; regression from the 1575 rows-up change) | Build 1575 | 390x844 and 375x667 (Chromium, touch). Not at 320x568, 1024x576 or 1024x768, where the chip sits clear of the labels.
- Steps: All States list > open the time row > select the full range ('20 > '24) > chart button > Line. Same in `#`, and in PA counties.
- Expected: the first row's numbers stay fully readable (they were clear on 1574, when the rows started 15 px lower).
- Actual: the first row's top change label sits under the chip and its 1px outline. At 390: NY "−4.5" is covered 20 x 7 px of its 22 x 11 px box (%), CA "−1.83M" 28 x 7 of 39 x 11 (#), PA counties Monroe "−3.4" 20 x 5 of 22 x 11. At 375: 13 x 7 (NY), 21 x 7 (CA), 13 x 5 (Monroe). In the crops the label reads as "-4.5" / "-1.83M" with the top half behind the arrows.
- Screenshots: shots/b1575-ch-390-qa044-crop-num.png, shots/b1575-ch-390-qa044-crop-pct.png (crops), shots/b1575-ch-390-states-num-rangeline.png, shots/b1575-ch-390-states-pct-rangeline.png, shots/b1575-ch-390-PA-pct-rangeline.png, shots/b1575-ch-375-states-num-rangeline.png
- Data: `qa/b1575-rows-chromium-390.json`, `qa/b1575-rows-chromium-375_320_1024x576_1024x768.json` (`cov`)

## Re-test status, builds 1574 / 1575 (pass 8, '16 ranges + Safari check + map/list stability, Oct 18 ~9:26-10:50 AM EDT)
- Live build: 1574 at the start (`window.BUILD` 202610181574), 1575 from ~9:50 AM EDT. 1575 only changed the list top band and sort-chip glass, so the '16-range results below hold for both. Scripts: `qa/b1574-range.py` (US map / All States / PA counties / Philadelphia city precincts x '16>'24 and '16>'20; touch drag of a knob, CDP touch in Chromium, touch pointer events in WebKit), `qa/b1574-check.py` (state rows vs FEC 2016/2020/2024), `qa/b1574-layout.py` (per-frame box sampling), `qa/b1575-saf.py` (Safari check), `qa/b1575-usmap.py`. The box was overloaded (several OOM kills), so the WebKit '16-range run and the 1024x768 '16>'20 run were cut off; WebKit got the Safari check instead.
- QA-038: confirmed fixed (390x844, 320x568, 1024x768 Chromium). '16>'24 All States: FL R +11.9, CA R +10.0, NY R +9.8 with change bars; '16>'20: VT D +9.0, CO D +8.6. Candidates are the end year's (Trump / Harris, or Biden / Trump for '16>'20). Reload restores both ranges at US, All States and PA counties (not at precincts, see QA-050). Bar and Pie keep the range.
- '16 change values vs FEC: all 51 state margin shifts within 0.15 pts except VT, ND, WY, AL, MD ('16>'24) and ME ('16>'20), 0.15-0.44 pts off: **LOW**, caused by the 2024/2020 state totals leaving out write-ins (QA-003; e.g. VT 2024 total 366,389 vs FEC 369,422). PA '16>'24: margin R +1.0 (FEC R +0.99), `#` R +76K (FEC +75,974), Trump +2.2 / Harris +1.2 pts (FEC +2.01 / +1.03 on the full total: LOW). Philadelphia county R +8.3, Philadelphia city R +8.6.
- QA-043: **still on 1574/1575**, and wider than logged: picking Line resets '16>'24 and '16>'20 to '20>'24 at the US map, All States, PA counties and precinct levels (`pick()` calls `__ySelectAll`). Once Line is on, re-choosing '16 works and the Line rows are right (FL +7.1 / -4.8, PA Philadelphia +4.6 / -3.7). Reload with Line on also comes back as '20>'24.
- QA-041: still. Line pick 187 ms (390, All States) and 246 ms (1024x768); Bar pick 137-161 ms.
- QA-039 / QA-040: not rechecked (the check run was killed by an out-of-memory event on the box).
- Safari regression check (build 1575; WebKit and Chromium; 1440x900 desktop, 1024x768, 390x844; AL Blount County, PA Lancaster, MA Worcester, GA Cobb; county view then +1, +2, +3 zoom). Results are **the same in WebKit and Chromium at every size, and the same on 1574** (served from `36b6ced` on port 8850), so these are not Safari-only and not new in 1575: shrunken thumbnails in AL and GA (QA-045); Blount County precincts all one colour (QA-046). Jagged precinct outlines: **not confirmed** in headless WebKit at 2x: the outlines look the same as Chromium (shots/b1575-saf-1440-Al-z3-we-vs-ch-crop.png, shots/b1575-saf-1440-Pe-z3-we-vs-ch-crop.png). The stair-step edge of Jefferson County in the Blount view matches the real section-line boundary (shots/b1575-saf-ch-1440-Al-county-jefferson-crop.png). Needs a real desktop Safari screenshot to go further.
- Map/list stability sweep (Chromium 1024x768 and 390x844; user path MA > Worcester County > time row > US House > President, then map/list, years, drill-in and back; boxes before/after and every frame for 2.2 s): QA-053 to QA-058. Unlike pass 7 this samples every frame, so it also catches jumps that settle back.

## New on builds 1574 / 1575 (pass 8)

### QA-045 [HIGH] Candidate thumbnails shrink to half size in Alabama (and by a third in Georgia)
- Severity: HIGH | Build 1575 (same on 1574) | WebKit and Chromium, 1440x900, 1024x768, 390x844
- Steps: geo menu > Alabama > Blount County (any AL view); compare the thumbnails with United States or PA/MA.
- Expected: the same thumbnail size everywhere (30 x 30 px photo in a 42 x 36 box).
- Actual: AL 14.7 x 14.7 px photo in a 34.4 x 20.7 box (-51%); GA (Cobb) 19.3 px in 36.7 x 25.3 (-36%). PA and MA 30 px. Cause: the thumbnail width copies the rendered width of the flag in `#crumbs .cic img` (`--thw`), and the AL flag image is portrait (32 x 48 natural, drawn 14.7 x 22) and GA's is 42 x 48 (drawn 19.3 x 22). The small size stays after leaving AL until the flag changes.
- Screenshots: shots/b1575-saf-we-1440-Al-county.png, shots/b1575-saf-we-1024x768-Al-county.png, shots/b1575-saf-we-390-Al-county.png, shots/b1575-saf-we-1440-Ge-county.png, shots/b1575-saf-ch-1440-Al-county.png, shots/b1575-saf-v1574-ch-1440-Al-county.png (1574)
- Data: `qa/b1575-saf-webkit.json`, `qa/b1575-saf-chromium.json`

### QA-046 [HIGH] Blount County, AL looks filled solid instead of shaded per precinct
- Severity: HIGH (as reported; may be the colour scale by design) | Build 1575 (same on 1574) | WebKit and Chromium, all 3 sizes
- Steps: Alabama > Blount County, zoom in 1-3 levels.
- Expected: precincts shaded by their own result, as in Lancaster PA or Cobb GA.
- Actual: all 23 Blount precincts draw the same darkest red, with only the white outlines and a few town shapes showing; distinct colours in the centre crop 48 > 28 > 18 > 11 as you zoom in (Lancaster 135 > 71, Cobb 120 > 23). The precinct data is there (`precincts2024/Alabama.js` has 23 Blount rows, R 87-93%), but every one is past the legend's R+20 end, so the heat scale clamps them all to one colour. A wider scale, or more steps past ±20, would show them.
- Screenshots: shots/b1575-saf-we-1440-Al-county.png, shots/b1575-saf-we-1440-Al-county-z2.png, shots/b1575-saf-ch-1440-Pe-county-z2.png (comparison)

### QA-047 [Critical] US map in a '16 range is coloured with the '20>'24 shift
- Severity: Critical (wrong map) | Build 1574 and 1575 | 390x844, 320x568, 1024x768 (Chromium)
- Steps: US map > time row > set '16>'24 or '16>'20 > wait 12 s.
- Expected: states coloured by the '16 shift (CO D +6.1 and KS D +4.5 blue for '16>'24; most states blue for '16>'20).
- Actual: the state colours are pixel-identical to '20>'24 for both '16 ranges: CO (251,186,162) light red, KS (249,211,197), IL (239,119,99), FL (223,50,42). The single-year '16 map does change colours (CO (178,211,231)), so only the ranges are stuck. The list rows for the same ranges are right.
- Screenshots: shots/b1575-usmap-ch-1024x768-20-24.png, shots/b1575-usmap-ch-1024x768-16-24.png, shots/b1575-usmap-ch-1024x768-16-20.png, shots/b1575-usmap-ch-1024x768-2016.png, shots/b1574-ch-390-r16-20-US.png

### QA-048 [Critical] Precinct list in a '16 range shows "'20 n/a · '24 ..." and no change values
- Severity: Critical (missing numbers, wrong year) | Build 1574/1575 | 390x844, 320x568, 1024x768 (Chromium)
- Steps: All States > set '16>'24 (or '16>'20) > PA > Philadelphia > Philadelphia city.
- Expected: 1,703 precinct rows with '16 change values (2016 precincts are loaded; the single-year '16 view shows them), and thumbnails with numbers.
- Actual: every row reads "'20 n/a · '24 D 94.7%" (`#`: "'20 n/a · '24 D 431"). In '16>'20 the label still says '24 (Delaware Precinct 317 "'20 n/a · '24 D 97.9%"). Both thumbnails are blank. The county and towns levels above show change values correctly.
- Screenshots: shots/b1574-ch-390-r16-24-prec-pct.png, shots/b1574-ch-390-r16-24-prec-num.png, shots/b1574-ch-390-r16-20-prec-pct.png, shots/b1574-ch-1024x768-r16-24-prec-pct.png

### QA-049 [High] '16>'20 on the US map: the Biden 2020 thumbnail has no number
- Severity: High (missing number) | Build 1574/1575 | 390x844, 320x568 (Chromium)
- Steps: US map > time row > '16>'20.
- Expected: four thumbnails with numbers (Trump 46% / Clinton 48% | Trump 47% / Biden 51%).
- Actual: Biden 2020 shows no percentage; the 2020 Trump badge reads 46% (2020 national is 46.8%, so this may be fine). Reload keeps the blank.
- Screenshot: shots/b1574-ch-390-r16-20-US.png

### QA-050 [High] Reload on the precinct list in a '16 range lands on the county summary
- Severity: High (navigation lost) | Build 1574/1575 | 390x844, 320x568, 1024x768 (Chromium)
- Steps: '16>'24 > PA > Philadelphia > Philadelphia city precincts > reload.
- Expected: the same precinct list.
- Actual: the app opens "Philadelphia County" as a single-place summary (2016 Trump 15.4% / Clinton 82.5% | 2024 Trump 20.0% / Harris 78.8%, "R+8.3 shift") and no list. The range itself is kept.
- Screenshot: shots/b1574-ch-390-r16-24-prec-reload.png

### QA-051 Low '16>'20 list thumbnails are labelled "Joe Biden 2024"
- Build 1574/1575 | 390x844. All States in '16>'20: the thumbnails show the right 2020 values (Biden 51%, Trump 47%), but their aria-label and hover title say "Joe Biden 2024" / "Donald Trump 2024". Screenshot: shots/b1574-ch-390-r16-20-states-pct.png

### QA-052 Medium Tapping into the Philadelphia city precincts is slow in a '16 range
- Build 1574/1575 | Chromium. Tap to paint 150-161 ms at 390 and 320, 93-115 ms at 1024x768 (other drill-ins 7-50 ms). Data: `qa/b1574-range-chromium-390_320.json` (`Prec.tap_lat`).

### QA-053 [HIGH] Opening the time row moves the time button down 5 px
- Build 1575 | 1024x768 and 390x844 (Chromium) | US and Worcester County map views
- Steps: tap the clock (time) button.
- Actual: `#bTime` moves dx 0 / dy +5 / dw 0 / dh 0 (122 > 127). The thumbnails also drop dy +68 to make room for the slider (likely intended, logged so it can be confirmed).
- Screenshots: shots/b1574-ch-1024x768-ls04-open-time-slider-before.png / -after.png, shots/b1574-ch-390-ls04-open-time-slider-before.png / -after.png

### QA-054 [HIGH] Thumbnails jump 3 px when switching between map and list
- Build 1575 | 1024x768 and 390x844 (Chromium) | Worcester County, President, time row open
- Map > list: thumbnails dy -3 (190 > 187; they widen +258/+276 to show names, by design). List > map: dy +3, and for about 250-700 ms the photo box is 50 px wide before it settles at 42 px.
- Screenshots: shots/b1574-ch-1024x768-ls09-view-list-Worcester-before.png / -after.png, shots/b1574-ch-1024x768-ls17-view-map-Worcester-before.png / -after.png, shots/b1574-ch-390-ls17-view-map-Worcester-after.png

### QA-055 [HIGH] First list row jumps up and back on back and drill-in
- Build 1575 | 390x844 and 1024x768 (Chromium) | All States > MA > Worcester, then back twice; also All States > MA in bar mode
- At 390, after the back tap the first row is drawn at y 8 (over the top fields) for 210-670 ms, then returns to y 198: dy -190 then +190. At 1024x768 it flickers dy -8 (198 > 190 > 198, about 120-200 ms), and the back chevron moves dy +4 and back. The settled positions match (which is why the pass 7 sweep saw no jump).
- Screenshots: shots/b1574-ch-390-ls28-list-back-1-before.png / -after.png, shots/b1574-ch-390-ls29-list-back-2-before.png / -after.png, shots/b1574-ch-1024x768-ls28-list-back-1-before.png / -after.png
- Data: `qa/b1574-layout-chromium-390.json`, `qa/b1574-layout-chromium-1024x768.json` (`transient`)

### QA-056 [HIGH] Thumbnails flash at the top of the screen when the geo menu closes
- Build 1575 | 1024x768 (Chromium), seen once | after the geo menu closed over Massachusetts.
- For about 450 ms the thumbnails are drawn at y 8 (over the President field), 54 px wide, then drop to y 190 (dy +182) and narrow to 42 px. The crumb field also slides in from x 32.
- Screenshots: shots/b1574-ch-1024x768-ls15-year-2020-before.png / -after.png

### QA-057 [HIGH] User's path: switching to US House hides the chart button and changes the place
- Build 1575 | 1024x768 and 390x844 (Chromium) | MA > Worcester County, President, time row open, then layers > US House, then back to President (map and list view)
- No box moved on the switch itself, but the chart button (968,186) disappears while the layers row is open and comes back when it closes, and the crumb changes Worcester County > Massachusetts while the list still shows Worcester's President result (Harris 53.9% / Trump 43.9%; QA-005 family). Back to President returns to Worcester County.
- Screenshots: shots/b1574-ch-1024x768-ls10-list-switch-USHouse-before.png / -after.png, shots/b1574-ch-1024x768-ls12-list-switch-back-President-before.png / -after.png, shots/b1574-ch-390-ls10-list-switch-USHouse-after.png

### QA-058 [HIGH] Turning on a range in a place summary shifts the thumbnails 23 px
- Build 1575 | 1024x768 and 390x844 (Chromium) | Worcester County list summary
- Year > range ('16>'24): thumbnails dy +23 and narrow (-175 / -138 px) to make room for the two year columns; back to one year: dy -23. Probably by design (column headers); logged as asked.
- Screenshots: shots/b1574-ch-1024x768-ls15-list-range-16-24-before.png / -after.png, shots/b1574-ch-390-ls15-list-range-16-24-after.png

## Passed on 1571 (pass 5)
- Layout sweep, 5 sizes x {All States, PA counties} x {%, #} x {bar, pie, range line, range bar} (Chromium): no new overlaps; only QA-009 at 320 ("+5.9", "−1.83M", "+3.7", "−35K" under the Chart button) and the known QA-011 name cut-offs (Montgomery, Westmoreland, Northampton, Susquehanna). Shots: shots/b1571-ch-*-sw-*.png
- Chart type kept for pie and bar while the slider moves '16 > '20 > '24; pie in a 2020 > 2024 range is offered (per the 1571 notes).
- Not done: random-tap monkey (harness argument error, rerun next pass), WebKit range-from-'16 (needs a touch drag that WebKit's driver lacks).
