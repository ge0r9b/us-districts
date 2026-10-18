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

### QA-022 [Fixed at 1024x768 on 1582 (pass 14)] iPad line list: the sort chip sits on the first row's lines; change labels collide
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

### QA-025 [Fixed on 1582 (verified pass 14, Chromium touch emulation)] Double-tap on the map zooms out and clears the state
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

### QA-039 [LOW on 1577: gap 0.02%, still open] 2016 state totals after a drill-in are county sums, not the official state result
- Severity: Critical (wrong numbers, small) | Build 1571 | All sizes (data; seen at 1024x768)
- Steps: All States > slider '16 > `#` > tap PA; read the bar panel.
- Expected (FEC 2016, `qa/fec16.json`): Trump 2,970,733, Clinton 2,926,441 (the app's own `DS16.states` has these).
- Actual: Trump 2,971,303 (+570), which is the sum of the PA rows in `ELECTION2016` (Clinton sum 2,926,156, -285). Same as QA-017, but for 2016 drill-ins.
- Other states whose 2016 county rows do not add up to FEC (D / R difference): CA -1,726 / -513, AL +60 / +374, TX -3 / -191, IN +29 / -46, NY +13 / +19, SD +8 / +10, KY -7 / -14, MI -1 / -2, WV -2 / 0.
- Screenshot: shots/b1571-ch-1024x768-y16-PA-counties.png

### QA-040 [LOW on 1577: gap 0.19%, still open] Philadelphia County shows three different 2016 totals
- Severity: Critical (wrong numbers, small) | Build 1571 | 1024x768 (Chromium)
- Steps: '16 > All States > PA > Philadelphia > Philadelphia city; read the bar panel at each level.
- Expected: one total for the same area at every level.
- Actual: county table `ELECTION2016` Clinton 582,697 / Trump 108,711; panel at the county's towns list Clinton 582,909 / Trump 108,945; panel at Philadelphia city precincts Clinton 584,025 / Trump 108,748. (Rockledge borough still listed under Philadelphia, QA-006.)
- Screenshots: shots/b1571-ch-1024x768-y16-phila.png, shots/b1571-ch-1024x768-y16-lvl4.png

### QA-041 [Fixed on 1577 (verified pass 12, 12:55 PM EDT)] Picking Line in the chart menu is slow again (regression)
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

### QA-043 [Fixed on 1577 (verified pass 12, 12:55 PM EDT)] Picking Line in a '16 > '24 range moves the start knob to '20
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
- Safari regression check (build 1575; WebKit and Chromium; 1440x900 desktop, 1024x768, 390x844; AL Blount County, PA Lancaster, MA Worcester, GA Cobb; county view then +1, +2, +3 zoom). Results are **the same in WebKit and Chromium at every size, and the same on 1574** (served from `36b6ced` on port 8850), so these are not Safari-only and not new in 1575: shrunken thumbnails in AL and GA (QA-045; full sweep: 33 states); Blount County precincts all one colour (QA-046; full sweep: 338 counties). Jagged precinct outlines: **not confirmed** in headless WebKit at 2x: the outlines look the same as Chromium (shots/b1575-saf-1440-Al-z3-we-vs-ch-crop.png, shots/b1575-saf-1440-Pe-z3-we-vs-ch-crop.png). The stair-step edge of Jefferson County in the Blount view matches the real section-line boundary (shots/b1575-saf-ch-1440-Al-county-jefferson-crop.png). Needs a real desktop Safari screenshot to go further.
- Map/list stability sweep (Chromium 1024x768 and 390x844; user path MA > Worcester County > time row > US House > President, then map/list, years, drill-in and back; boxes before/after and every frame for 2.2 s): QA-053 to QA-058. Unlike pass 7 this samples every frame, so it also catches jumps that settle back.

## New on builds 1574 / 1575 (pass 8)

### QA-045 [Fixed on 1576 (verified pass 10, 11:55 AM EDT)] Candidate thumbnails shrink in 33 of 50 states (up to -66% in Delaware), not just Alabama
- **Re-test on 1576 (`615fa5a`, live line 9 = 202610181576), Chromium, one browser, 1024x768 and 390x844, all 50 states + DC: FIXED.** Every switch shows 30 x 30 px photos in a 42 x 36 box at the first painted frame (12-46 ms after the switch, the earliest rAF that has thumbnails), at 300 ms and settled at 3 s, 0 frames at any other size (`qa/b1576-thumbs-{1024x768,390}.json`, every rAF for 1.2 s). Transitions: DE after DC 30 px from the first frame (14/16 ms); AK after AL 30 px (13 ms); Blount County 30 px, then the US view (298/308 ms) and US > All States list (214/291 ms) 30 px. `--thw` is now a constant 30px; the crumb icon still uses the state outline (e.g. DE 22x48 drawn 10.1x22), which no longer matters. No clipping (img inside its box and the viewport, all states), no overlapping thumbnail boxes, the new % badge (20 x 11) sits on the photo's lower-right corner inside the 42 px box, every crumb icon loaded (stateflags/<State>.png, US flag at US/DC). No page errors. Two thumbnail jumps in list mode remain/appear: QA-059, QA-060. Shots: shots/b1576-thumbs-ch-{1024x768,390}-{AL,DE,NH,GA,NE,DC,DE-after-DC,AK-after-AL,Blount,Blount-list,US-after-Blount,USlist-after-Blount}.png. Script `qa/b1576-thumbs.py`.
- Severity: HIGH | Build 1575 (same on 1574) | WebKit and Chromium, 1440x900, 1024x768, 390x844 (full sweep: Chromium 1024x768 and 390x844, every state plus DC)
- Steps: pick any state from the state menu (e.g. Delaware, New Hampshire, Illinois, Alabama) and look at the candidate thumbnails; compare with United States or Pennsylvania.
- Expected: the same thumbnail size everywhere (30 x 30 px photo in a 42 x 36 box).
- Actual: the thumbnail width copies the rendered width of the crumb icon `#crumbs .cic img` (`--thw`, refreshed every 700 ms). For a state that icon is `img/stateflags/<State>.png`, the flag cut to the state's outline (not the rectangular `img/flags/<State>.png`; e.g. Alabama is 32x48 in stateflags and 54x36 in flags). It is drawn 22 px tall and capped at 30 px wide, so **thumbnail = min(30, 22 x w/h of the state outline)**. Tall, narrow states get small thumbnails. Results are identical at 1024x768 and 390x844 (51/51 match):
  - **Shrunk (33), worst first, as px (shrink), with the stateflag's natural size:** DE 10.1 (-66%, 22x48); NH 11.9 (-60%, 26x48); NJ 12.4 (-59%, 27x48); IL 12.8 (-57%, 28x48); MS 14.2 (-53%, 31x48); VT 14.2 (-53%, 31x48); AL 14.7 (-51%, 32x48); ID 14.7 (-51%, 32x48); IN 14.7 (-51%, 32x48); RI 14.7 (-51%, 32x48); ME 15.1 (-50%, 33x48); NV 15.6 (-48%, 34x48); UT 17.4 (-42%, 38x48); AZ 18.8 (-37%, 41x48); CA 19.3 (-36%, 42x48); GA 19.3 (-36%, 42x48); MI 19.3 (-36%, 42x48); NM 19.7 (-34%, 43x48); MN 20.2 (-33%, 44x48); OH 20.2 (-33%, 44x48); WI 21.1 (-30%, 46x48); FL 22.5 (-25%, 48x47); LA 23 (-23%, 48x46); TX 23 (-23%, 48x46); WV 24 (-20%, 48x44); MO 24.5 (-18%, 48x43); AR 25.1 (-16%, 48x42); SC 27.1 (-10%, 48x39); NY 27.8 (-7%, 48x38); WY 27.8 (-7%, 48x38); OR 28.5 (-5%, 48x37); CO 29.3 (-2%, 48x36); CT 29.3 (-2%, 48x36).
  - **Normal 30 px (17 + DC):** AK 48x34, HI 48x33, IA 48x32, KS 48x27, KY 48x24, MD 48x27, MA 48x31, MT 48x28, NE 48x24, NC 48x21, ND 48x30, OK 48x25, PA 48x30, SD 48x32, TN 48x15, VA 48x23, WA 48x33. **DC**: 30 px. DC isn't in the state menu; when opened from All States the crumb stays "All States" with the US flag (68x36), so `--thw` stays 30. (`stateflags/District_of_Columbia.png` is 39x48, which would give 17.9 px if it were ever used.)
  - **Persistence:** yes. Measured 300 ms after switching state, the thumbnails still have the previous state's size in about half of the switches (1024: AK 14.7 after AL; FL 10.1 after DE; IL 14.7 after ID; IN 12.8 after IL; IA 14.7 after IN; MD 15.1 after ME; MT 24.5 after MO; NC 27.8 after NY; OK 20.2 after OH; WY 21.1 after WI). They correct at the next 700 ms tick. The reverse also happens (DE after DC stays 30 for 300 ms, then drops to 10.1). As logged before, the small size lasts indefinitely when the crumb icon doesn't change (US precinct list stayed 14.7 after Blount).
- Fix idea: size the thumbnails from a constant or from the rectangular flag, not from the outline icon's width.
- Screenshots: shots/b1575-thumbs-ch-1024x768-{AL,GA,OH,NE,DC,DE-after-DC}.png, shots/b1575-thumbs-ch-390-{AL,GA,OH,NE,DC,DE-after-DC}.png, earlier shots/b1575-saf-we-1440-Al-county.png, shots/b1575-saf-we-1440-Ge-county.png
- Data: `qa/b1575-thumbs-1024a.json` (AL..NH), `qa/b1575-thumbs-1024b.json` (NH..WY), `qa/b1575-thumbs-390.json`, `qa/b1575-dc.json`, logs `qa/b1575-th-a.log`, `qa/b1575-th-b.log`; scripts `qa/b1575-thumbs.py`, `qa/b1575-dc.py`

### QA-046 [Fixed on 1579, verified on 1583 (pass 15, 2:35 PM EDT)] 338 counties in 26 states (plus DC) render as one solid colour because every precinct is past the colour scale's end
- **Re-check on 1583** (live line 9 = 202610181583; Chromium only). Live `marginColor` stops are now ±0.15 / ±0.45 / **±0.9** (comment: "build 1579 (QA-046, option a): linear to +-90"). The precinct fill still goes through `heatC` > `marginColor`. Precinct data is unchanged since 1575 (`v2/data/precincts2024*` has no diff from 615fa5a), so I recounted from the same files with `qa/b1583-clamp.py` (> `qa/b1583-clamp90.json`, same method, clamp 0.9).
  - **Solid counties at ±90 (n >= 2, all or all-but-one precincts beyond): 2, down from 338.** Both are all-but-one, and **0 counties have every precinct clamped** (212 before). TX 1 (Roberts County 4/5, lowest R+87.8); ND 1 (Nelson County 1/2, a 2-precinct county). Every other state has 0. **DC: 0**, with 7 of 144 precincts beyond D+90 and the rest D+54 to D+90 (143/144 beyond ±60 before). So the worst-10 list is just these two. Highest share beyond ±90 among counties with 5+ precincts: Roberts TX 4/5, LaSalle Parish LA 13/21, Borden TX 3/5, Sherman TX 4/7, Harding SD 4/8, Niobrara WY 3/6, Motley TX 3/6, Lamar AL 10/24, Logan KS 5/12, Sheridan KS 6/15. 562 counties have at least one precinct beyond ±90.
  - **The four counties from 1575, now:**

    | County | Precincts | Margin range | Distinct colours (computed) | 1575 > 1583 |
    |---|---|---|---|---|
    | Campbell WY | 36 | R+60.9 to R+92.5 (2 beyond ±90) | 31 | 1 > 31 |
    | Jackson AL | 30 | R+60.8 to R+89.2 | 24 | 1 > 24 |
    | Jefferson ID | 21 | R+61.1 to R+86.3 | 18 | 1 > 18 |
    | Blount AL | 23 | R+74.7 to R+88.2 | 17 | 1 > 17 |

    Blount's colour span is the narrowest (36 levels on one channel, vs 66-77 for the other three), so its shading is visible but subtle.
  - **Screenshot pixel variance**, same views and zooms as 1575 (centre crop; distinct fill colours; luminance s.d. of fill pixels; `qa/b1583-variance.json`):

    | County | z | Fill colours 1575 > 1583 | Lum s.d. 1575 > 1583 |
    |---|---|---|---|
    | Campbell WY | 1 | 145 > 212 | 7.9 > 8.7 |
    | Campbell WY | 2 | 114 > 195 | 9.0 > 10.3 |
    | Jackson AL | 1 | 95 > 192 | 7.9 > 11.5 |
    | Jackson AL | 2 | 58 > 119 | 6.0 > 10.6 |
    | Jefferson ID | 1 | 43 > 105 | 5.2 > 13.4 |
    | Jefferson ID | 2 | 35 > 87 | 4.2 > 13.6 |
    | Blount AL (1440) | 2 | 118 > 157 | 10.1 > 10.6 |
    | Blount AL (1440) | 3 | 55 > 76 | 4.2 > 5.4 |

    Visually, Jackson, Jefferson and Campbell now show distinct precinct shades, and Blount shows a few lighter and darker precincts.
  - **Competitive counties are not washed out:** Lancaster PA still has 206 distinct computed precinct colours (197 at ±60). The screenshot is lighter but clearly shaded: z2 fill colours 454 > 369, lum s.d. 31.9 > 23.8 (-25%). Cobb GA: z2 203 > 165, s.d. 33.9 > 28.4 (-16%). Blue cores and red edges are both still clear.
  - Shots, 1583 (same names as 1575): shots/b1583-solid-ch-1024x768-{Wy,Al,Id}-county{,-z1,-z2}.png (Campbell, Jackson, Jefferson), shots/b1583-saf-ch-1440-{Al,Pe,Ge}-county{,-z1,-z2,-z3}.png (Blount, Lancaster, Cobb). Side by side 1575 | 1583: shots/b1583-cmp-Jackson-AL-z1-1575-vs-1583.png, shots/b1583-cmp-Campbell-WY-z1-1575-vs-1583.png, shots/b1583-cmp-Jefferson-ID-z1-1575-vs-1583.png, shots/b1583-cmp-Blount-AL-z2-1575-vs-1583.png, shots/b1583-cmp-Lancaster-PA-z2-1575-vs-1583.png, shots/b1583-cmp-Cobb-GA-z2-1575-vs-1583.png
  - Verdict: fixed. Optional polish (not filed): Blount-type counties (all precincts between R+75 and R+88) are distinguishable but low-contrast. A perceptual or steeper top segment would help without affecting competitive counties.
- Severity: HIGH (as reported; it is the colour scale clamping, not missing data) | Build 1575 (same on 1574) | all engines and sizes
- Steps: Alabama > Blount County (or Wyoming > Campbell County, Alabama > Jackson County, Idaho > Jefferson County) and zoom in 1-3 levels.
- Expected: precincts shaded by their own result, as in Lancaster PA or Cobb GA.
- Actual: precinct fill is `heatC` > `marginColor((rep-dem)/tot)`, whose stops end at **±0.6, i.e. R+60 / D+60** (the legend reads "Harris +60 … Trump +60"). *Correction to the first write-up:* the clamp is ±60, not R+20; ±20 is only the shift legend. The colours are also already very dark from about R+45 upward (0.3 > 0.6 runs 222,45,38 > 103,0,13). Any county whose precincts are all beyond ±60 draws as one flat colour, with only the outlines showing.
- Method: from the app's own `data/precincts2024/*.js` (byte-identical to live), for each county I counted the precincts with |margin| >= 60 on the same side. A county is "solid" when it has at least 2 precincts and clamped >= n-1 ("all" = every precinct clamped). `qa/b1575-clamp.py` > `qa/b1575-clamp.json`.
- **Per state, as solid/counties (all clamped):** TX 87/254 (63); NE 30/93 (23); MO 28/115 (19); GA 24/159 (8); KS 24/105 (16); TN 24/95 (12); OK 19/77 (15); KY 15/120 (8); ND 11/53 (7); ID 10/44 (5); AL 8/67 (5): Cullman 47/48, Jackson 30/30, Marshall 24/25, Blount 23/23, Winston 18/18, Marion 15/15, Cleburne 14/14, Bibb 7/8; MT 8/56 (4); SD 8/58 (5); VA 6/133 (6), incl. D-side Charlottesville 8/8, Petersburg 7/7, Falls Church 3/3 (the only D-side solid counties); CO 5/64 (3); UT 5/29 (2); WY 5/23 (4); FL 4/67 (1); WV 4/55 (2); AR 3/75 (0); NV 3/17 (1); LA 2/64 (1); MS 2/81 (1); IL 1/102 (1); IA 1/99 (0); NC 1/100 (0); **DC 1/1**: 143 of 144 precincts (`precincts2024-DC.js`) are beyond D+60, so DC draws solid blue. **0:** AK, AZ, CA, CT, DE, HI, IN, MA, MD, ME, MI, MN, NH, NJ, NM, NY, OH, OR, PA, RI, SC, VT, WA, WI. Total 338 counties + DC (212 with every precinct clamped).
- **10 worst nationally** (every precinct clamped, most precincts first; lowest |margin| in brackets): 1. Campbell County WY 36/36 (R+60.9); 2. Jackson County AL 30/30 (R+60.8); 3. Blount County AL 23/23 (R+74.7); 4. Jefferson County ID 21/21 (R+61.1); 5. Winston County AL 18/18 (R+73.5); 6. McCreary County KY 18/18 (R+65.7); 7. Franklin County ID 18/18 (R+63.0); 8. Converse County WY 18/18 (R+61.0); 9. Van Zandt County TX 18/18 (R+60.4); 10. Sherman County KS 18/18 (R+60.2). Next: Scott County VA 17/17, Leslie County KY 17/17. Cullman AL (47 of 48) is the largest almost-all county.
- Fix idea: extend the scale past ±60 (e.g. stops at 0.8/1.0) or switch to a relative scale inside the county when zoomed to precincts.
- Screenshots (Chromium 1024x768, county view then +1, +2 zoom): shots/b1575-solid-ch-1024x768-Wy-county{,-z1,-z2}.png (Campbell WY), shots/b1575-solid-ch-1024x768-Al-county{,-z1,-z2}.png (Jackson AL), shots/b1575-solid-ch-1024x768-Id-county{,-z1,-z2}.png (Jefferson ID); earlier shots/b1575-saf-we-1440-Al-county-z2.png (Blount), shots/b1575-saf-ch-1440-Pe-county-z2.png (Lancaster for comparison). The thumbnails in the AL and ID shots are also shrunk (QA-045).
- Data: `qa/b1575-clamp.json`, `qa/b1575-solid-chromium.json`; scripts `qa/b1575-clamp.py`, `qa/b1575-solid.py`

### QA-047 [Fixed on 1577 (verified pass 12, 12:55 PM EDT)] [Critical] US map in a '16 range is coloured with the '20>'24 shift
- Severity: Critical (wrong map) | Build 1574 and 1575 | 390x844, 320x568, 1024x768 (Chromium)
- Steps: US map > time row > set '16>'24 or '16>'20 > wait 12 s.
- Expected: states coloured by the '16 shift (CO D +6.1 and KS D +4.5 blue for '16>'24; most states blue for '16>'20).
- Actual: the state colours are pixel-identical to '20>'24 for both '16 ranges: CO (251,186,162) light red, KS (249,211,197), IL (239,119,99), FL (223,50,42). The single-year '16 map does change colours (CO (178,211,231)), so only the ranges are stuck. The list rows for the same ranges are right.
- Screenshots: shots/b1575-usmap-ch-1024x768-20-24.png, shots/b1575-usmap-ch-1024x768-16-24.png, shots/b1575-usmap-ch-1024x768-16-20.png, shots/b1575-usmap-ch-1024x768-2016.png, shots/b1574-ch-390-r16-20-US.png

### QA-048 [Fixed on 1577 (verified pass 12, 12:55 PM EDT)] [Critical] Precinct list in a '16 range shows "'20 n/a · '24 ..." and no change values
- Severity: Critical (missing numbers, wrong year) | Build 1574/1575 | 390x844, 320x568, 1024x768 (Chromium)
- Steps: All States > set '16>'24 (or '16>'20) > PA > Philadelphia > Philadelphia city.
- Expected: 1,703 precinct rows with '16 change values (2016 precincts are loaded; the single-year '16 view shows them), and thumbnails with numbers.
- Actual: every row reads "'20 n/a · '24 D 94.7%" (`#`: "'20 n/a · '24 D 431"). In '16>'20 the label still says '24 (Delaware Precinct 317 "'20 n/a · '24 D 97.9%"). Both thumbnails are blank. The county and towns levels above show change values correctly.
- Screenshots: shots/b1574-ch-390-r16-24-prec-pct.png, shots/b1574-ch-390-r16-24-prec-num.png, shots/b1574-ch-390-r16-20-prec-pct.png, shots/b1574-ch-1024x768-r16-24-prec-pct.png

### QA-049 [Fixed on 1577 (verified pass 12, 12:55 PM EDT)] [High] '16>'20 on the US map: the Biden 2020 thumbnail has no number
- Severity: High (missing number) | Build 1574/1575 | 390x844, 320x568 (Chromium)
- Steps: US map > time row > '16>'20.
- Expected: four thumbnails with numbers (Trump 46% / Clinton 48% | Trump 47% / Biden 51%).
- Actual: Biden 2020 shows no percentage; the 2020 Trump badge reads 46% (2020 national is 46.8%, so this may be fine). Reload keeps the blank.
- Screenshot: shots/b1574-ch-390-r16-20-US.png

### QA-050 [High, still open on 1577] Reload on the precinct list in a '16 range lands on the county summary
- Severity: High (navigation lost) | Build 1574/1575 | 390x844, 320x568, 1024x768 (Chromium)
- Steps: '16>'24 > PA > Philadelphia > Philadelphia city precincts > reload.
- Expected: the same precinct list.
- Actual: the app opens "Philadelphia County" as a single-place summary (2016 Trump 15.4% / Clinton 82.5% | 2024 Trump 20.0% / Harris 78.8%, "R+8.3 shift") and no list. The range itself is kept.
- Screenshot: shots/b1574-ch-390-r16-24-prec-reload.png

### QA-051 Low (still open on 1577 in the lists; fixed on the US map) '16>'20 list thumbnails are labelled "Joe Biden 2024"
- Build 1574/1575 | 390x844. All States in '16>'20: the thumbnails show the right 2020 values (Biden 51%, Trump 47%), but their aria-label and hover title say "Joe Biden 2024" / "Donald Trump 2024". Screenshot: shots/b1574-ch-390-r16-20-states-pct.png

### QA-052 Medium Tapping into the Philadelphia city precincts is slow in a '16 range
- Build 1574/1575 | Chromium. Tap to paint 150-161 ms at 390 and 320, 93-115 ms at 1024x768 (other drill-ins 7-50 ms). Data: `qa/b1574-range-chromium-390_320.json` (`Prec.tap_lat`).

### QA-053 [HIGH] Opening the time row moves the time button down 5 px
- Build 1575 | 1024x768 and 390x844 (Chromium) | US and Worcester County map views
- Steps: tap the clock (time) button.
- Actual: `#bTime` moves dx 0 / dy +5 / dw 0 / dh 0 (122 > 127). The thumbnails also drop dy +68 to make room for the slider (likely intended, logged so it can be confirmed).
- Screenshots: shots/b1574-ch-1024x768-ls04-open-time-slider-before.png / -after.png, shots/b1574-ch-390-ls04-open-time-slider-before.png / -after.png

### QA-054 [Changed on 1582: settled photo no longer moves; transient now QA-060] [HIGH] Thumbnails jump 3 px when switching between map and list
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

### QA-058 [HIGH, chart views fixed on 1582; plain range list still open] Turning on a range in a place summary shifts the thumbnails 23 px
- Build 1575 | 1024x768 and 390x844 (Chromium) | Worcester County list summary
- Year > range ('16>'24): thumbnails dy +23 and narrow (-175 / -138 px) to make room for the two year columns; back to one year: dy -23. Probably by design (column headers); logged as asked.
- Screenshots: shots/b1574-ch-1024x768-ls15-list-range-16-24-before.png / -after.png, shots/b1574-ch-390-ls15-list-range-16-24-after.png

## New on build 1576 (pass 10, Oct 18 ~11:30-11:55 AM EDT)

### QA-059 [HIGH] List view: candidate thumbnails drop 30 px after switching state (DE after DC)
- Severity: HIGH (QA-054-style jump) | Build 1576 | Chromium 1024x768 and 390x844
- Steps: Geo > All States > tap the DC row; then pick Delaware in the state menu (stays in the list view, "Delaware counties").
- Expected: thumbnails painted at their final place.
- Actual: the first frame (14 ms) has the thumbnails at y=131/183; at 258 ms (1024) / 448 ms (390) they move to y=161/213: **dx 0, dy +30, dw 0, dh 0**, layout-shift entry on `laCands` (0.0004 / 0.0013). Per-state switches in the results view had no jumps (0 of 100).
- Screenshots: shots/b1576-jump-390-DEafterDC-before-after.png, shots/b1576-jump-{1024x768,390}-DEafterDC-{before,after}.png (the "before" capture landed after the move even with 6x CPU throttle; the rAF positions above are the evidence), shots/b1576-thumbs-ch-{1024x768,390}-DE-after-DC.png
- Data: `qa/b1576-thumbs-*.json` > trans.DE_after_DC.frames, `qa/b1576-jump.json`

### QA-060 [HIGH, widened on 1582: every map/list switch, see pass 14] Blount County results > list: thumbnails jump 8 px left and back
- Severity: HIGH (QA-054-style jump) | Build 1576 | Chromium 1024x768 and 390x844
- Steps: Geo > Alabama > Blount County (results view), then tap the globe/list button.
- Expected: thumbnails stay at x=12.
- Actual: 390: x 12 > 4 at 16 ms (**dx -8**) > 12 at 261 ms (**dx +8**), shifts on `cands` (0.0013) and the two IMGs. 1024: first frame at x=4 (23 ms), then x=12 at 256 ms (**dx +8, dy 0, dw 0, dh 0**).
- Screenshots: shots/b1576-thumbs-ch-{1024x768,390}-Blount.png (before), shots/b1576-thumbs-ch-{1024x768,390}-Blount-list.png (after)
- Data: `qa/b1576-thumbs-*.json` > trans.Blount_list.frames

### QA-061 [MEDIUM] Bottom geo field keeps saying "District of Columbia" after switching to another state
- Severity: MEDIUM | Build 1576 (same on 1575) | Chromium 1024x768 and 390x844
- Steps: Geo > All States > DC row; then pick Delaware in the state menu.
- Expected: bottom field reads Delaware (or the current area).
- Actual: top crumb says "Delaware counties", the bottom field shows the Delaware outline icon but the text "District of Columbia" (DC's `nameLock`/placeholder isn't cleared).
- Screenshots: shots/b1576-thumbs-ch-1024x768-DE-after-DC.png, shots/b1576-thumbs-ch-390-DE-after-DC.png, shots/b1575-thumbs-ch-390-DE-after-DC.png (1575)

## New on build 1576 (pass 11, Oct 18 ~11:50 AM-12:30 PM EDT)

### QA-062 [Critical] Searching a DC address from a state or county moves the map but keeps the old place's name and numbers
- Severity: Critical (wrong numbers shown for the place) | Build 1576 | Chromium 390x844 and 375x667, WebKit 1024x768 (touch)
- Steps: type "Franklin County, OH" in the bottom geo field, Enter. Then type "1600 Pennsylvania Ave NW, Washington, DC 20500", Enter.
- Expected: title, bottom field and thumbnails switch to DC (as they do from a fresh load, QA-004), or to the address.
- Actual: the map flies to the White House (centre 38.8987, -77.0352, zoom 15), but the title stays "Franklin County", the field stays "Franklin County, OH", and the thumbnails keep Franklin County's 64% / 35%. Same from "Allegheny County, PA" (60% / 39%) and from "Pennsylvania" (50% / 49%). Both engines. A New York address from Allegheny County works (switches to New York County, 76% / 22%).
- Screenshots: shots/b1576p11-ch-390-addr2-1.png (Franklin), shots/b1576p11-ch-390-addr2-2.png (Allegheny), shots/b1576p11-ch-390-addr2-3.png (Pennsylvania), shots/b1576p11-ch-375x667-addr-from-county.png, WebKit: shots/b1576p11-we-1024-addr2-{1,2,3}.png
- Data: `qa/b1576p11-addr2-{chromium-390,webkit-1024}.json`, `qa/b1576p11-verify-chromium-375x667.json`

### QA-063 [Medium] Address inside the current county: thumbnails show a precinct but the title still says the county
- Severity: Medium | Build 1576 | Chromium 390x844, WebKit 1024x768
- Steps: "Allegheny County, PA" > Enter; then "100 Ross St, Pittsburgh, PA 15219" > Enter.
- Expected: the label matches the numbers (the address or "Pittsburgh Ward 1 Dist 1", as the New York case puts the address in the field).
- Actual: popup "Pittsburgh Ward 1 Dist 1, Harris 76.4%, Trump 22.3%" and the thumbnails switch to 76% / 22%, but the title and bottom field still read "Allegheny County" / "Allegheny County, PA" (Allegheny is 60% / 39%).
- Screenshot: shots/b1576p11-ch-390-addr2-4.png, shots/b1576p11-we-1024-addr2-4.png

### QA-064 [Fixed on 1584 (verified pass 16 on a quiet box, 2:55 PM EDT)] [Medium] Picking State senate or State house inside a big state is slow
- Severity: Medium (slow tap, over 100 ms) | Build 1576 | Chromium 390x844
- Steps: type a state in the geo field > Enter > district-type button > State senate (or State house).
- Actual tap-to-next-paint: Texas senate 952 / 804 ms, Texas house 1,102 ms, California senate 1,579 ms, California house 1,215 / 960 ms, New York 381-475 ms, Minnesota house 456 ms, Ohio 219-327 ms, Nebraska 143 ms. It grows with the state's size. At the US level the same picks were 118-156 ms (pass 9).
- Caveat: other jobs on the test machine had the load average at 37-72 during these runs, so the absolute numbers are inflated; the size pattern is still clear. One Chromium renderer crash right after Texas > State senate happened under that load and did not repeat in a solo run (heap 188 MB, no errors).
- Screenshots: shots/b1576p11-ch-390-senate-Texas-solo.png, shots/b1576p11-ch-390-statehouse-California-solo.png
- Data: `qa/b1576p11-txcrash-chromium-390.json`, `qa/p11-dist2.py` output

## Re-test status, build 1576 (pass 11, Chromium smoke at all 5 sizes, Oct 18 ~11:50 AM-12:30 PM EDT)
- Live build still 202610181576. No v3 preview or live URL yet (`/us-districts/v3/` is 404).
- Smoke flow (institution menu, All States, sort, `#`, slider, range, chart menu pie/line, PA > Allegheny > Pittsburgh drill-ins, back, US House type, reload, address): no console errors, page errors or failed requests at any size.
- Still on 1576: QA-003 (same per-state gaps, ME 2020 Biden -4,599 is still the largest), QA-005 (US House from a county list: 0 rows, all sizes), QA-007 (All States 248-292 ms, US House pick 243-308 ms), QA-041 (Line 124-165 ms), QA-044 ("−1.83M" under the sort chip at 390/375), QA-009 (320: "CA" under the sort chip, "−1.83M" under Chart), QA-018 (OH bar tap stays on states), QA-034 (map view restores as list).
- Layout-stability sweep (MA > Worcester County, US House, years, range, drill-in and back) at 390/375/320/1024x576: same jumps as before and nothing new. QA-054 (thumbnails 3 px map/list), QA-058 (23 px on a range), QA-053 (time button 5 px), QA-057 (chart button hidden on US House).
- One CLS 0.229 shift on `.cpanel` at 375x667 around the `#` pick in the smoke flow did not reproduce in two focused runs (0 shift), so it is not logged.
- Not done this pass: WebKit smoke (screenshots timed out under the machine load), school-district lists per state.

## Re-test status, build 1577 (pass 12, `6099604`, live line 9 = 202610181577; Chromium 390x844 and 1024x768, WebKit 390x844; Oct 18 ~12:33-12:55 PM EDT)
Same steps as first logged. One browser at a time. WebKit 390 matched Chromium on every check. No page errors.
- **QA-043 fixed:** All States > full range > drag the left knob to '16 ('16>'24, FL R +11.9) > Line. The knob stays at [0,2], the rows are '16>'24 (FL +7.1 / -4.8), and reload keeps '16>'24 + Line. '16>'20 + Line keeps [0,1]. Shots: shots/b1577-ch-{390,1024x768}-r16-24-afterdrag.png, -r16-24-line.png, -r16-24-line-reload.png, -r16-20-line.png, shots/b1577-we-390-r16-24-line.png
- **QA-047 fixed:** pixel samples at state centres on the US map: '16>'24 CO (103,163,206) blue, KS (131,183,216) blue, GA (160,203,225), FL (199,36,33); '16>'20 CO (58,131,190), TX (150,197,222), PA (191,219,233); '20>'24 unchanged (CO 251,186,162). The three maps differ at all 9 sample points, identical across Chromium 390/1024 and WebKit 390. Shots: shots/b1577-ch-1024x768-US-{20-24,16-24,16-20,2016}.png (same for 390, and we-390)
- **QA-048 fixed:** '16>'24 > PA > Philadelphia > Philadelphia city gives 1,703 rows with change values marked ≈ (2016 twin matching), e.g. "Precinct 5836 ≈R +65.9 · +32.9 / -33.0". `#` mode shows votes (Precinct 534 R +613). '16>'20 also has values (Precinct 5809 R +53.4). Thumbnails have numbers (Harris 79% / Trump 20%). New problem: QA-065 (names cut off). Shots: shots/b1577-ch-{390,1024x768}-prec-16-24.png, -prec-16-24-num.png, -prec-16-20.png
- **QA-049 fixed:** the US map at '16>'20 shows four numbered thumbnails: Trump 2016 46%, Clinton 2016 48%, Trump 2020 47%, Biden 2020 51%. They survive a reload. Shots: shots/b1577-ch-390-US-16-20.png, -US-16-20-reload.png
- **QA-050 still open:** reload on the '16>'24 Philadelphia city precinct list lands on the "Philadelphia County" summary (0 rows, level lost; the range [0,2] is kept). Chromium 390/1024 and WebKit 390. Shots: shots/b1577-ch-{390,1024x768}-prec-16-24-reload.png, shots/b1577-we-390-prec-16-24-reload.png
- **QA-051 still open in the lists:** the US map labels are now right ("Joe Biden 2020", "Donald Trump 2020"). All States in '16>'20 (Bar and Line) and the Philadelphia precinct list in '16>'20 still label the thumbnails "Joe Biden 2024" / "Donald Trump 2024" (aria-label and title) while showing 2020 values (51% / 47%, 81% / 18%). Shots: shots/b1577-ch-390-r16-20-states.png, shots/b1577-ch-390-prec-16-20.png
- **New 1577 chart-menu rule: passes.** One year (2016 and 2024; US map and All States list) offers Pie + Bar. A range ('20>'24, '16>'24, '16>'20) offers Line + Bar. Seen at both sizes and in WebKit.
- **'16 line plot: passes for a single place, partly for lists.** US and Pennsylvania '16>'24 Line plot three points ('16/'20/'24) with per-segment labels, and the values match the official shares within rounding: US Clinton 48.2 > Biden 51.3 (+3.1) > Harris 48.3 (-2.9); Trump 46.1 > 46.8 (+0.8) > 49.8 (+3.1). PA Clinton 47.5 > 50.0 (+2.5) > 48.7 (-1.3); Trump 48.2 > 48.8 (+0.6) > 50.4 (+1.6). The All States list rows only draw '16 > '24 (QA-066). The list values are plausible: FL Trump +7.1 / Clinton > Harris -4.8, NV +5.1 / -0.4, VT '16>'20 +0.4 / +9.4. NY Trump +7.1 vs about +6.8 from the certified share, likely the app's 2024 NY total (8,198,094 vs the certified total, which includes others). Under 0.5 points, so LOW, not filed. Shots: shots/b1577-ch-1024x768-US-16-24-line.png, shots/b1577-ch-1024x768-PA-16-24-line.png
- **Institution field always shows results: passes.** At US and at Pennsylvania (Chromium 390/1024):
  - The empty field lists 55 / 68 rows. "US" and "America" give United States; "penn" gives Pennsylvania plus PA district types; "phila" gives Philadelphia County, PA; "cook" gives 15 Cook counties; "ontario" gives Ontario, Canada plus Ontario County, NY. All are grouped by kind.
  - "zzqx" shows "No institutions match"; nothing was ever blank.
  - Typing "ohio" and pressing Enter opens Ohio.
  - Small oddity: QA-067. Shots: shots/b1577-ch-{390,1024x768}-inst-{US,PA}-{penn,zzqx}.png, -inst-enter-ohio.png
- **QA-039 still open, now LOW:** '16 > All States > PA panel shows Trump 2,971,303 / Clinton 2,926,156 vs FEC 2,970,733 / 2,926,441 (+570 / -285, 0.02%). `__stTot` returns the FEC values. Shot: shots/b1577-ch-1024x768-y16-PA-counties.png
- **QA-040 still open, now LOW:** Philadelphia 2016 is still three totals: county table 582,697 / 108,711, towns-level panel 582,909 / 108,945, precinct-level panel 584,025 / 108,748. The biggest gap is 1,328 of 706K (0.19%). Shots: shots/b1577-ch-1024x768-y16-phila.png, -y16-lvl4.png
- **QA-041 fixed:** list, '20>'24 > chart > Line, tap-to-paint 14.5 / 17.9 / 17.5 ms (1024), 28.4 / 15.1 / 15.1 ms (390), 10 / 11 / 17 ms (WebKit 390).
- Data: `qa/b1577-chromium-1024x768.json`, `qa/b1577-chromium-390.json`, `qa/b1577-webkit-390.json`, `qa/b1577-lineprobe.json`, `qa/b1577-y16.log`; scripts `qa/b1577-retest.py`, `qa/b1577-lineprobe.py`, `qa/b1577-y16drill.py`

## New on build 1577 (pass 12)

### QA-065 [HIGH] Precinct list in a '16 range: every name is cut to "Philadelph…", so the rows can't be told apart
- Severity: HIGH (rows unidentifiable) | Build 1577 | Chromium 390x844 and 1024x768, WebKit 390x844
- Steps: All States > '16>'24 (or '16>'20) > PA > Philadelphia > Philadelphia city.
- Expected: the precinct name, or at least its number ("Philadelphia Precinct 5836"), readable.
- Actual: the name column is about 90 px even at 1024 px wide (the new "≈R +65.9" label takes the space), so all 1,703 rows read "Philadelph…" and the precinct number is never visible. The crumb also cuts off at "Philadelphia County Philadelphi…".
- Screenshots: shots/b1577-ch-1024x768-prec-16-24.png, shots/b1577-ch-390-prec-16-24.png, shots/b1577-we-390-prec-16-24.png

### QA-066 [MEDIUM] All States Line in '16>'24 draws only '16 and '24 (no '20 point)
- Severity: MEDIUM | Build 1577 | Chromium 390x844 and 1024x768, WebKit 390x844
- Steps: All States > '16>'24 > Line.
- Expected (1577 note: "'16>'24 plots '16/'20/'24 with per-segment change labels"): each row has a '20 point and two segment labels, as the single-place chart does (US and PA show three points).
- Actual: each row has two 2-point polylines (e.g. FL `0,49.6 100,54.9` / `0,48.3 100,40.5`) and one net label per candidate (+7.1 / -4.8). The thumbnails show only the 2024 candidates.
- Screenshots: shots/b1577-ch-1024x768-r16-24-line.png (list), shots/b1577-ch-1024x768-US-16-24-line.png (single place, 3 points)

### QA-067 [LOW] Institution search "America" lists South Africa
- Build 1577 | Chromium 390/1024. Typing "America" in the institution field gives COUNTRY United States, then South Africa, then counties. South Africa doesn't contain "America" and isn't a synonym, so this looks like a loose fuzzy match. Data: `qa/b1577-chromium-1024x768.json` > inst.

## Re-test status, builds 1578 / 1579 / 1580 (pass 13, Oct 18 ~12:56-1:45 PM EDT)
The live build moved during the pass: 1578 at 12:56, 1579 by ~1:05, 1580 by ~1:30 PM EDT. Each item says which build it was seen on. Chromium and WebKit, one browser at a time, load average 2-3 (quiet box).
- **QA-062 fixed (critical, 1578 and 1579):** from Franklin County OH, Allegheny County PA and Pennsylvania, Enter on "1600 Pennsylvania Ave NW, Washington, DC 20500" now switches the title to "District of Columbia", the field to the address and the thumbnails to 90% / 6% (popup Harris 90.3%, Trump 6.5%). Chromium 375x667 and WebKit 1024x576. New side issue: QA-068. Shots: shots/b1577p13-ch-375-addr2-{1,2,3}.png, shots/b1577p13-we-1024-addr2-{1,2,3}.png. Data: `qa/b1577p13-addr2-{chromium-375,webkit-1024}.json` (script `qa/p13-addr2.py`).
- **QA-063 mostly fixed (1578/1579):** Allegheny > "100 Ross St, Pittsburgh, PA 15219" now titles the view "Pittsburgh Ward 1 Dist 1" with 76% / 22%, matching the popup. The bottom field still says "Allegheny County, PA" (the New York case puts the address there). Shot: shots/b1577p13-ch-375-addr2-4.png
- **QA-053 fixed on 1580 (390x844):** opening the time row no longer moves the clock button (MA > Worcester and US). On 1579 at 375/320/1024x576 it still moved 5 px; not rechecked there on 1580.
- **QA-065 fixed on 1580 (names):** '16>'24 > Philadelphia city precincts read "Precinct 5802", "Precinct 3301"... at 390 and 1024x768. The crumb still cuts off at "Philadelphia County Philadelphi…" (LOW). Shot: shots/b1580p13-ch-390-prec-16-24.png
- **QA-050 fixed on 1580:** reload on the '16>'24 Philadelphia precinct list stays on 1,703 precinct rows with range [0,2]. Shot: shots/b1580p13-ch-{390,1024x768}-prec-16-24-reload.png
- **QA-051 still open on 1580:** Philadelphia precinct list at '16>'20 labels the thumbnails "Joe Biden 2024" / "Donald Trump 2024" while showing 2020 values (81% / 18%). Data: `qa/b1580p13-chromium-390.json` > prec_lbl_16_20
- **QA-064 confirmed on a quiet box (1578, Chromium 390x844, load ~2.7):** tap-to-next-paint for the district-type pick is Texas senate 794 ms, Texas house 834 ms, California senate 1,102 ms, California house 1,197 ms, New York 403 / 376 ms, Minnesota house 342 ms, Ohio 218 / 261 ms, Nebraska 136 ms. Same pattern as pass 11, so it isn't machine load. The page closed on the next fresh load (Florida school districts) and the run ended, so school lists are still not done. Data: `qa/p13-run.log`
- **QA-061 still open on 1579:** after DC then Delaware, the title is "Delaware counties" but the bottom field still reads "District of Columbia" (4 of 4 runs). Shot: shots/b1579p13-ch-390-DE-after-DC.png
- **QA-009 partly fixed (1579, 320x568):** All States % rows are clear of the sort chip. The chip still grazes the first row's left label by 4 px in two lists: PA counties "86.1%" (Fulton, 22 x 4 px) and Delaware "32.9%" (New Castle, 11 x 4 px). At 390/375 the chip grazes Delaware's "65.5%" by 4 px. The range-bar "−1.83M" case was not rechecked. Data: `qa/b1579p13-labels-chromium.json` (script `qa/p13-labels.py`). Labels under the right-hand buttons are QA-013 (accepted).
- **Thumbnails (QA-045 family), 1579 at 390:** AL, DE and DC are 30 px from the first frame with no jumps. The DE-after-DC step (QA-059) and Blount (QA-060) were not reached (harness page closed).
- **Layout-stability sweep:** 375/320/1024x576 on 1579 matched pass 11 exactly (QA-053 5 px, QA-054 3 px map/list, QA-058 23 px on a range, QA-057 chart button hidden on US House). 390 on 1580: QA-053 gone, others unchanged, one new frame jump (QA-070).
- **Smoke:** WebKit 375/320/1024x576 (1579) and Chromium 375/1024x576 (1580): no console errors, page errors or failed requests; CLS 0 to 0.0002. All States 253-377 ms and US House 312-371 ms (QA-007 still open). US House from a county list still gives 0 rows (QA-005). Data: `qa/b1577p13-flow-*.json`
- No v3 preview or live URL yet.

## New on builds 1578-1580 (pass 13)

### QA-068 [MEDIUM] A DC address from another place puts the pin in the middle of DC, not at the address
- Build 1578 / 1579 | Chromium 375x667, WebKit 1024x576
- Steps: "Franklin County, OH" > Enter; then "1600 Pennsylvania Ave NW, Washington, DC 20500" > Enter.
- Expected: the pin and map at the White House (38.8977, -77.0365), as a fresh-load DC address search did on 1568 (zoom 15).
- Actual: the map centres on 38.8926, -77.0145 at zoom 11 and the pin sits there, about 2 km east of the White House. The title and numbers are right (QA-062 fix).
- Screenshots: shots/b1577p13-we-1024-addr2-1.png, shots/b1577p13-ch-375-addr2-1.png

### QA-069 [LOW] New York address: title shows a raw id "015/75"
- Build 1578 | Chromium 375x667, WebKit 1024x576
- Steps: "Allegheny County, PA" > Enter; then "350 5th Ave, New York, NY 10118" > Enter.
- Actual: the popup says "New York AD 75 ED 15, Harris 76.0%, Trump 22.1%" and the thumbnails match, but the title (crumb) reads "015/75".
- Expected: a readable name such as "AD 75 ED 15" (as the popup has).
- Screenshot: shots/b1577p13-ch-375-addr2-0.png

### QA-070 [HIGH, seen once, recheck] Opening All States: the clock button jumps off screen for one frame
- Build 1580 | Chromium 390x844
- Steps: US map > geo button > All States row.
- Actual: `#bTime` sits at (334,122) then at 1,758 ms jumps to (1336,488) (**dx +1002, dy +366**, so it vanishes) and returns to (334,122) at 1,801 ms. New on 1580 (the clock-button change); not seen on 1579 at 375/320/1024x576.
- Screenshots: shots/b1577p13-ch-390-ls25-geo-menu-all-states-{before,after}.png. Data: `qa/b1577p13-layout-chromium-390.json` > step 25 transient

### QA-071 [Fixed on 1583 (verified pass 14, 2:10 PM EDT)] [HIGH] Back chevron ignores touch taps in WebKit
- Builds 1575-1580 (every WebKit run so far) | WebKit 390x844, 375x667, 320x568, 1024x576 with touch
- Steps: All States > PA > Allegheny County > Pittsburgh (precinct list), then tap the back chevron.
- Expected: back to the towns list, as in Chromium (precincts > townships).
- Actual: the list stays on precincts. The tap fires pointerdown, touchstart, pointerup and touchend on the chevron but no click; the button's `pointerdown` handler calls `preventDefault()` and the action only runs on `click`. A scripted `click()` does go back. Other touch taps (rows, sort chip, chart menu) work in the same WebKit runs. If iOS Safari behaves the same, back is dead on iPhones and iPads.
- Screenshot: shots/b1579p13-we-390-back-after-touch.png. Data: `qa/b1579p13-wkback-390.json` (script `qa/p13-wkback.py`), `qa/b1577p13-flow-webkit-*.json` > after_back

## Re-test status, build 1581 (pass 13 addendum, Oct 18 ~1:35-1:50 PM EDT)
Live line 9 = 202610181581 (main `8d94cc9`, 1:28 PM EDT). Chromium, quiet box.
- **QA-070 reproduces on 1581 at 375x667 (no longer "seen once"):** US map > geo button > All States row: `#bTime` at (319,122), then at 1,693 ms at (1276,488) (**dx +957, dy +366**, off screen), back at (319,122) at 1,952 ms, so the clock button disappears for about 260 ms. Data: `qa/b1577p13-layout-chromium-375.json` (build 1581) > step 25 transient; log `qa/p13-layout375b.log`.
- **QA-053 fixed on 1581 at 375x667 too:** opening the time row leaves the clock button in place at MA > Worcester and at the US (was +5 px on 1579). Only the thumbnails move down 68 px to make room for the row, as before.
- QA-054 (thumbnails -3 / +3 px map/list) and QA-058 (+23 px on a '16>'24 range in the list) still on 1581 at 375x667.
- **QA-050 and QA-065 (rows) still fixed on 1581,** Chromium 390: reload keeps 1,703 precinct rows at '16>'24, rows read "Precinct 5802" etc.; the crumb is still cut ("Philadelphia County Philadelphi…"). **QA-051 still open on 1581** ("Joe Biden 2024" label at '16>'20, 81% / 18%). Shots: shots/b1581p13-ch-390-prec-16-24{,-reload,-num}.png, shots/b1581p13-ch-390-prec-16-20.png. Data: `qa/b1581p13-chromium-390.json`
- Commit `e92d7d4` only added scripts, logs and shots; its message lists the pass 13 bugs with numbers that differ from the BUGS.md entries above. BUGS.md (QA-068 DC pin, QA-069 "015/75", QA-070 clock jump, QA-071 WebKit back) is the record.

## Re-test status, build 1582 (pass 14, Oct 18 ~1:52-2:22 PM EDT)
Live line 9 was 202610181582 at the start; **1583 went live during the pass** (main `e1f9ae3`, 1:58 PM EDT: "back chevron works on WebKit touch (QA-071)"). The 1582 icon checks, misc checks and the 390 layout sweep ran on 1582; the 375/1024x768 layout sweeps, thumbnail transitions, smoke flows, WebKit back and DC checks ran on 1583. Each item says which. Load average 1.3-5.3 (several of my browsers at once), so **tap-to-paint numbers in this pass are inflated and need a quiet-box recheck**. No console errors, page errors or failed requests in any run; CLS 0 in all smoke flows.

**1582 change (candidate icons keep the map view's spot; no text/tooltip in chart views; single-year bar at phone width)** - MA, map > list > pie > bar > pie > map at '24, then '20>'24 and '16>'24 map > list > bar > line > bar > map. Chromium 390x844, 375x667, 320x568, 1024x576, 1024x768 and WebKit 390x844, 1024x768 (touch). Script `qa/p14-icons.py`, data `qa/b1582p14-icons-{chromium,webkit}-<size>.json`, shots `shots/b1582p14-{ch,we}-<size>-icons-<view>.png`.
- **Passes when settled:** in list, pie, bar and line the icon rects equal the map view's to the half pixel at every size and in both engines (e.g. 390: (12,122) and (12,166) single year; (12,190), (12,234), (292,190), (292,234) in a range).
- **Passes:** no name/number text next to the icons in pie, bar or line (`.cpt/.cn/.cs/.cw` hidden, no text node within 40 px), and tapping an icon opens no tooltip (`#partyBub` hidden) in pie, bar, '20>'24 bar and line.
- **Passes:** the single-year bar chart is on screen at phone width (390/375/320: top 211, bottom 317) and ends before the button column: track right edge 324 / 309 / 254 vs the button column at 334 / 319 / 264 (10 px gap); fill ends 239 / 230 / 196. Same in WebKit 390. Rows high to low (Harris 61.6%, Trump 36.2%, Other 2.2%). Shot: shots/b1582p14-ch-320-icons-bar24.png
- **Fails during the switch:** see QA-060 (8 px sideways jump for 250-560 ms on every map/list switch) and QA-058 (plain range list, no chart).
- The MA '20>'24 line shows Biden 65.6 > Harris 61.6 (-4.0) and Trump 32.1 > 36.2 (+4.1); the 2020 shares match the certified MA result (Biden 65.6%, Trump 32.1%).
- List rows/labels: no new overlaps (`qa/p14-labels.py`, `qa/b1582p14-labels-chromium.json`); only the known QA-044 / QA-013 cases below.

**Status per bug**
- **QA-071 fixed on 1583 (WebKit 390x844 and 1024x768, touch):** Pittsburgh precinct list > touch tap on the back chevron goes to townships (pointerdown/touchstart/pointerup/touchend; the follow-up click is ignored). The next taps go back one level each (counties, then states), no double back. On 1582 it still failed (stayed on precincts). WebKit smoke flow on 1583: precincts > back > townships at both sizes. Data: `qa/b1583p14-wkback-{390,1024}.json`, `qa/b1582p14-wkback-390.json` (1582). Shot: shots/b1583p14-we-390-back-after-touch.png
- **QA-025 fixed (1582, Chromium 390 touch emulation, 2 taps 120 ms apart):** Erie County, PA (zoom 6) > double-tap the map: zoom 6 > 8 around the tap point, the state stays Pennsylvania, and the geo field shows the tapped area "Juniata County, PA". The title still reads "Erie County" (it is the institution). Real-device check still advised. Shot: shots/b1582p14-ch-390x844-qa025-dbltap.png
- **QA-022 fixed at 1024x768 (1582):** All States '20>'24 Line: the sort chip sits above the NY row's lines (no overlap) and none of the visible change labels collide. Shot: shots/b1582p14-ch-1024x768-lbl-states-rline-pct.png
- **QA-054 changed (settled jump gone for the photo):** the icon image no longer ends up 3 px off after a map/list switch (image rects identical at all 5 sizes, both engines). The `.cand` container box still moves -3 / +3 px and is 50 px wide for 475-709 ms after list > map (390 on 1582, 375 and 1024x768 on 1583), and the photo jumps 8 px sideways during the switch (now tracked under QA-060).
- **QA-060 changed, wider than Blount (HIGH):** see the entry below "New on build 1582".
- **QA-058 changed:** fixed in the chart views (bar and line keep the map's spot in '20>'24 and '16>'24 at all sizes). Still open in the plain range summary (a range list with no chart picked, e.g. after tapping the active Bar again): the left column drops dy +23 and the right column moves left dx -94 (390), -86.5 (375), -59 (320), -783 (1024x576 and 1024x768), both engines, because the plain summary lays the two years out as named columns ("2020 / 2024"). Shots: shots/b1582p14-ch-390-icons-rbar.png (plain list), shots/b1582p14-ch-390-icons-map2024r.png (map)
- **QA-055 not reproduced (likely fixed):** list back from Worcester to MA and to All States, and back in bar mode: no transient first-row or chevron positions at 390 (1582), 375 and 1024x768 (1583). Data: `qa/b1582p14-layout-chromium-{390,375,1024x768}.json` steps 28, 29, 32.
- **QA-056 not reproduced:** no thumbnail flash when the geo menu closed (steps 1-3, three sizes).
- **QA-070 still open, now also at 1024x768 (1583):** US map > time row > geo button > All States: `#bTime` jumps to (3872,488) (dx +2904, dy +366, off screen) for about 107 ms, then returns to (968,122). 390 on 1582: (1336,488) for about 75 ms; 375 on 1583: (1276,488) for about 56 ms. Data: layout JSONs step 25 `transient`. Shots: shots/b1582p14-ch-{390,375,1024x768}-ls25-geo-menu-all-states-{before,after}.png
- **QA-059 still open (1583, Chromium 390 and 1024x768):** DC row then Delaware: thumbnails at y 131/183 for the first frame, then y 161/213 at 526 ms (dx 0, dy +30), layout shift 0.0013 on `laCands`. Shots: shots/b1582p14-thumbs-ch-{390,1024x768}-DE-after-DC.png. Data: `qa/b1582p14-thumbs-{390,1024x768}.json`
- **QA-061 still open (1583, both sizes):** after DC then Delaware the title says "Delaware" but the geo field placeholder is still "District of Columbia".
- **QA-023 still open (1582, 390):** "Pittsburgh": the first suggestion is "East Pittsburgh borough"; Enter leaves the view on Allegheny County with the field reading "No match: East Pittsburgh borou…". Shot: shots/b1582p14-ch-390x844-qa023-pittsburgh.png
- **QA-044 still open (1582):** All States '20>'24 Line: NY "−4.5" is under the sort chip by 7 x 9 px (390), 14 x 9 (375), 15 x 9 (320); `#` mode "−1.83M" under the chip at 390 and 320 (Chromium smoke) and in WebKit 390. Clear at 1024x576/1024x768.
- **QA-057 still open (1582/1583):** chart button hidden while the layers row is open; on US House the crumb changes Worcester County > Massachusetts.
- **QA-051 still open (1582):** All States '16>'20: the thumbnails are labelled "Joe Biden 2024" / "Donald Trump 2024" with 2020 values (51% / 47%).
- **QA-066 still open (1582):** All States '16>'24 Line: each row still has two 2-point polylines (FL +7.1 / −4.8, NY +7.1 / −2.7, PA +2.2 / +1.2), no '20 point. Shot: shots/b1582p14-ch-390x844-qa066-line-16-24.png
- **QA-063 still open (1582, WebKit 390):** "100 Ross St, Pittsburgh" from Allegheny: title "Pittsburgh Ward 1 Dist 1", 76% / 22%, field still "Allegheny County, PA".
- **QA-068 still open (1582, WebKit 390):** DC address from Franklin County OH, Allegheny PA and Pennsylvania: centre 38.8926, -77.0145 at zoom 11, not the White House. Title/numbers right (District of Columbia, 90% / 6%), so QA-062 stays fixed.
- **QA-069 still open (1582, WebKit 390):** "350 5th Ave, New York" titles the view "015/75" (76% / 22%).
- **QA-064 still open (1582/1583, Chromium 390, load 3-5):** State senate pick Texas 708 ms, Ohio 226 ms. School districts are slower still (QA-073).
- **QA-018 still open (1582):** tapping the OH row on its bar leaves the list on All States.
- **QA-005 still open (1583):** US House from the Pittsburgh towns list gives 0 rows (Chromium 390/320/1024x576, WebKit 390/1024x768).
- **QA-007 still open (1583, load ~3):** All States 255-278 ms (Chromium), 423-431 ms (WebKit); US House pick 274-345 ms (Chromium), 242-247 ms (WebKit).
- **QA-015 still open (1583):** reload at Allegheny County list: `lt` counties > none, and `ll` jumps to the fixed point 40.435, -80.0249.
- **QA-009 (320):** single year All States labels under the right buttons are QA-013 (accepted). In the Delaware list the sort chip touches the "New Castle" name by 5 x 4 px (range bar mode).
- **Per-state school district lists, reached for the first time** (Chromium 390, `qa/p14-dist2.py`, `qa/p14-school2.py`, data `qa/b1582p14-dist2-chromium-390.json`, `qa/b1582p14-school2-chromium-390.json`): row counts FL 67, HI 1, MD 24, NV 17 (all match the number of districts), PA 500 (PA has 500 school districts), OH 611, TX 1,019, CA 974, GA 184, VT 131, AK 53. No n/a, NaN or empty values, rows high to low. Problems: QA-072 (DC), QA-073 (slow), QA-074 (repeated names). Earlier passes never reached this because the harness used the key `school`; the button is `schools`.
- Harness note, not a bug: after a district-type pick the layers row stays open, and the first tap anywhere only closes it (the globe tap is swallowed; the second tap works). Data: `qa/b1582p14-globe-chromium-390.json`
- Not reached (carry over): QA-046 visual recheck on the ±90 scale (1579), QA-050/QA-065 (fixed in pass 13, not rechecked), QA-039/040/042, QA-010-014/016/021, WebKit at 375/320/1024x576, layout sweep at 320/1024x576 and in WebKit, school lists for the other 37 states, all timing on a quiet box. No v3 preview or live URL yet.

## New on build 1582 (pass 14)

### QA-072 [Critical] DC > School districts (or US House) shows the national numbers under "District of Columbia"
- Severity: Critical (wrong numbers under a place's name) | Build 1583 (also seen in the 1582/1583 school run at ~2:05 PM EDT) | Chromium 390x844
- Steps: type "District of Columbia" in the geo field > Enter (title District of Columbia, thumbnails Harris 90% / Trump 6%) > district-type button > School districts (or US House). Then the globe (list) button.
- Expected: DC's one school district (DC Public Schools) with DC's numbers (90% / 6%), or DC's delegate district; the title and numbers agree.
- Actual: on the map the title stays "District of Columbia" but the thumbnails switch to the US totals, Trump 50% / Harris 48%. The list then shows the 51 state rows (WY 72.3%, WV 70.0%...) titled "District of Columbia states" for School districts, or all 436 House districts (AL-04, KY-05...) for US House, still titled "District of Columbia". States behave correctly (Texas > State senate keeps Texas 56% / 42% and lists 31 Texas districts).
- Screenshots: shots/b1582p14-ch-390-DC-schools-map.png, shots/b1582p14-ch-390-DC-schools-list.png, shots/b1582p14-ch-390-DC-ushouse-list.png, shots/b1582p14-ch-390-schools-DistrictofColumbia-list.png
- Data: `qa/b1583p14-dcschools-chromium-390.json` (script `qa/p14-dcschools.py`)

### QA-073 [Changed on 1584: much faster, still over 100 ms in TX/CA/PA (pass 16)] [HIGH] Picking School districts in a big state takes 1-4 s
- Severity: HIGH (tap-to-next-paint far over 100 ms) | Build 1582/1583 | Chromium 390x844
- Steps: type a state in the geo field > Enter > district-type button > School districts.
- Actual tap-to-next-paint: California 3,990 ms, Texas 2,980 ms, Pennsylvania 1,105 ms, Ohio 767 ms, Florida 411 ms, Vermont 291 ms, DC 141 ms, Nevada 134 ms, Hawaii 101 ms, Alaska 64 ms, Maryland 2 ms. It grows with the number of districts (CA 974, TX 1,019). Same pattern as QA-064 (state senate/house), but 3-4x slower.
- Caveat: load average 3-5 during the run, so the absolute numbers are inflated; the size pattern is clear.
- Screenshots: shots/b1582p14-ch-390-schools-California-list.png, shots/b1582p14-ch-390-schools-Texas-list.png
- Data: `qa/b1582p14-dist2-chromium-390.json` (`lat_type`)

### QA-074 [MEDIUM] School district lists: same-name rows can't be told apart, and some California districts appear 2-3 times
- Severity: MEDIUM | Build 1582/1583 | Chromium 390x844
- Steps: Ohio (or California, Texas, Vermont) > district-type > School districts > list.
- Expected: one row per district, and districts that share a name labelled so they can be told apart (e.g. with the county).
- Actual: Ohio has three "Eastern Local School District" rows (81.4%, 81.0%, 80.1%) and two each of Crestview, Southern, Buckeye, Madison, Green Local; Texas two each of Big Sandy, Centerville, Chapel Hill, Dawson ISD. These are different real districts with the same name, but the rows carry no county or other label. California has "Santa Cruz City High School District" three times (83.6%; 20.0% / 76.3%; ...) and "Santa Barbara Unified", "Healdsburg Unified" and "Eureka City Unified" twice each. These look like one district split into several rows with different numbers. In Vermont two long names are cut to the same "Southwest Vermont Union Element…" / "West River Valley Modified Unio…", so they read as duplicates too.
- Screenshots: shots/b1582p14-ch-390-schools-Ohio.png, shots/b1582p14-ch-390-schools-California.png, shots/b1582p14-ch-390-schools-Vermont-list.png
- Data: `qa/b1582p14-school2-chromium-390.json` (`dups`, `order_dups`)

### QA-060 (widened, HIGH, was "Blount County results > list") Candidate icons jump 8 px sideways for 250-560 ms on every map/list switch
- Severity: HIGH (layout jump; contradicts the 1582 "fixed spot" rule while it lasts) | Build 1582 (Blount on 1583) | Chromium 390x844, 375x667, 320x568, 1024x576, 1024x768; WebKit 390x844, 1024x768
- Steps: Massachusetts > globe button (map > list), then a chart pick, then globe again (list > map). Same at '24, '20>'24 and '16>'24.
- Expected: the icons stay at the map's spot in every frame (x 12).
- Actual: map > list: the icons go to x 4 (**dx -8**) on the first frame (23-45 ms) and return to x 12 at 262-561 ms. List > map: the left column goes to x 20 (**dx +8**) at 15-34 ms and returns at 265-624 ms (in a range only the left column moves). Settled positions match. Blount County (1583, 390): 12 > 4 at 22 ms > 12 at 273 ms, as first logged.
- Screenshots: shots/b1582p14-ch-390-icons-list24.png, shots/b1582p14-ch-390-icons-map24b.png (end states; the jump is in the per-frame data)
- Data: `qa/b1582p14-icons-*.json` > `frames` (list24, map24b, map2024r2, map1624r2); `qa/b1582p14-thumbs-390.json` > trans.Blount_list

## Re-test status, build 1584 (pass 16, Oct 18 ~2:50-3:20 PM EDT)
- Live build 202610181584 (speed build: idle warm-up for district types, deferred fit, Back map moves wait for the list). No v3 preview or live URL yet.
- Timing on a quiet box (load 0.4-1.6), Chromium 390x844 touch, state > district-type pick (tap-to-next-paint):
  - **QA-064 fixed**: California senate 65 ms, California house 71 ms, Texas house 85 ms, Pennsylvania house 76 ms, Texas senate 104 ms, Ohio senate 62 ms (were 800-1,600 ms on 1576).
  - **QA-073 changed** (was 1-4 s): Texas 231 ms, California 144 ms, Pennsylvania 121 ms, Ohio 103 ms; under 100 ms for Florida 71, Vermont 72, Nevada 93, Alaska 53, Maryland 50, Hawaii 48, DC 49. Still over 100 ms in the three biggest states. Data: `qa/b1584p16-dist2-chromium-390.json`.
  - QA-020 / QA-007 improved but open: Back from a county's towns to the PA counties list 184 / 184 ms (was 253-313 ms); All States row 76-111 ms (was 248-292 ms). Other taps 11-75 ms (geo menu, drill to PA, county, town, Back to towns, Back to All States, globe). Data: `qa/b1584p16-lat-chromium-390.json`.
- **QA-072 still open (Critical)**: DC > School districts or US House still shows US totals (50% / 48%) under "District of Columbia" on the map; the list shows the 51 state rows or the 436 House rows. Data: `qa/b1584p16-dcschools-chromium-390.json`, shots/b1584p16-ch-390-DC-*.png.
- QA-074 unchanged (Ohio/Texas/California/Vermont same duplicate names).
- Back works in Chromium and WebKit at 1024x768 by touch, mouse, keyboard Enter and script click; a second Back 3 s after the first also works (WebKit 390 and 1024). Data: `qa/b1584p16-backclick-*.json`, `qa/b1584p16-back2-webkit-*.json`.
- Layout sweep at 1024x768 (Chromium): identical to pass 14, nothing new and nothing fixed (QA-058 23 px in the plain range list, QA-054/060 transient on map/list, QA-070 clock button off screen for one frame on All States). The 390 sweep and the 5-size flow run crashed after step 12 when another job pushed the load average to 40; carry over.

### QA-075 [HIGH] Typing "Georgia" + Enter in the geo field opens the country Georgia, not the US state
- Severity: HIGH (navigation goes to the wrong place; a US state can't be reached by its name) | Build 1584 | Chromium 390x844 touch
- Steps: fresh load > type "Georgia" in the bottom geo field > Enter.
- Expected: the US state of Georgia (its map, thumbnails and district types), or at least the US state listed first.
- Actual: the map flies to the Caucasus (Tbilisi), the crumb shows the Georgian flag with "Georgia" and a "No data yet" tag, and the district-type menu has no visible buttons (US House, State senate, State house, School districts are all hidden). "Texas" + Enter on the same run works normally.
- Screenshot: shots/b1584p16-ch-390-Georgia-layers.png
- Script: `qa/p16-ga.py`

## Passed on 1571 (pass 5)
- Layout sweep, 5 sizes x {All States, PA counties} x {%, #} x {bar, pie, range line, range bar} (Chromium): no new overlaps; only QA-009 at 320 ("+5.9", "−1.83M", "+3.7", "−35K" under the Chart button) and the known QA-011 name cut-offs (Montgomery, Westmoreland, Northampton, Susquehanna). Shots: shots/b1571-ch-*-sw-*.png
- Chart type kept for pie and bar while the slider moves '16 > '20 > '24; pie in a 2020 > 2024 range is offered (per the 1571 notes).
- Not done: random-tap monkey (harness argument error, rerun next pass), WebKit range-from-'16 (needs a touch drag that WebKit's driver lacks).
