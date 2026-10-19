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

### QA-005 [Fixed on 1596 (verified pass 24)] Picking a district type (US House) in list view shows no district list, and the header names the wrong place
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


### QA-006 [Fixed on 1599 (verified pass 26)] Rockledge borough (Montgomery County) listed under Philadelphia County
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

### QA-020 [Fixed on 1608 (verified pass 30): both Backs 41-79 ms] Slow taps that remain after the 1567 drill rewrite
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

### QA-044 [Fixed on 1588 (verified pass 20)] [Changed on 1587, see pass 19] Line list: the first row's change number is hidden under the sort chip
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

### QA-051 [Fixed on 1599 (verified pass 26)] Low '16>'20 list thumbnails are labelled "Joe Biden 2024"
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

### QA-060 [Fixed on 1586 (verified pass 19)] [HIGH, widened on 1582: every map/list switch, see pass 14] Blount County results > list: thumbnails jump 8 px left and back
- Severity: HIGH (QA-054-style jump) | Build 1576 | Chromium 1024x768 and 390x844
- Steps: Geo > Alabama > Blount County (results view), then tap the globe/list button.
- Expected: thumbnails stay at x=12.
- Actual: 390: x 12 > 4 at 16 ms (**dx -8**) > 12 at 261 ms (**dx +8**), shifts on `cands` (0.0013) and the two IMGs. 1024: first frame at x=4 (23 ms), then x=12 at 256 ms (**dx +8, dy 0, dw 0, dh 0**).
- Screenshots: shots/b1576-thumbs-ch-{1024x768,390}-Blount.png (before), shots/b1576-thumbs-ch-{1024x768,390}-Blount-list.png (after)
- Data: `qa/b1576-thumbs-*.json` > trans.Blount_list.frames

### QA-061 [Fixed on 1599 (verified pass 26)] [MEDIUM] Bottom geo field keeps saying "District of Columbia" after switching to another state
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

### QA-067 [Fixed for "America" on 1604 (verified pass 27); "USA" leftover filed as QA-088] [LOW] Institution search "America" lists South Africa
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

### QA-068 [Fixed on 1599 (verified pass 26)] [MEDIUM] A DC address from another place puts the pin in the middle of DC, not at the address
- Build 1578 / 1579 | Chromium 375x667, WebKit 1024x576
- Steps: "Franklin County, OH" > Enter; then "1600 Pennsylvania Ave NW, Washington, DC 20500" > Enter.
- Expected: the pin and map at the White House (38.8977, -77.0365), as a fresh-load DC address search did on 1568 (zoom 15).
- Actual: the map centres on 38.8926, -77.0145 at zoom 11 and the pin sits there, about 2 km east of the White House. The title and numbers are right (QA-062 fix).
- Screenshots: shots/b1577p13-we-1024-addr2-1.png, shots/b1577p13-ch-375-addr2-1.png

### QA-069 [Fixed on 1599 (verified pass 26)] [LOW] New York address: title shows a raw id "015/75"
- Build 1578 | Chromium 375x667, WebKit 1024x576
- Steps: "Allegheny County, PA" > Enter; then "350 5th Ave, New York, NY 10118" > Enter.
- Actual: the popup says "New York AD 75 ED 15, Harris 76.0%, Trump 22.1%" and the thumbnails match, but the title (crumb) reads "015/75".
- Expected: a readable name such as "AD 75 ED 15" (as the popup has).
- Screenshot: shots/b1577p13-ch-375-addr2-0.png

### QA-070 [Fixed on 1586 (verified pass 19, 6:10 PM EDT)] [HIGH] Opening All States: the clock button jumps off screen for one frame
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

### QA-072 [Fixed on 1585 (verified pass 18, 5:00 PM EDT)] [Critical] DC > School districts (or US House) shows the national numbers under "District of Columbia"
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

### QA-060 [Fixed on 1586 (verified pass 19, 6:10 PM EDT)] (widened, HIGH, was "Blount County results > list") Candidate icons jump 8 px sideways for 250-560 ms on every map/list switch
- Severity: HIGH (layout jump; contradicts the 1582 "fixed spot" rule while it lasts) | Build 1582 (Blount on 1583) | Chromium 390x844, 375x667, 320x568, 1024x576, 1024x768; WebKit 390x844, 1024x768
- Steps: Massachusetts > globe button (map > list), then a chart pick, then globe again (list > map). Same at '24, '20>'24 and '16>'24.
- Expected: the icons stay at the map's spot in every frame (x 12).
- Actual: map > list: the icons go to x 4 (**dx -8**) on the first frame (23-45 ms) and return to x 12 at 262-561 ms. List > map: the left column goes to x 20 (**dx +8**) at 15-34 ms and returns at 265-624 ms (in a range only the left column moves). Settled positions match. Blount County (1583, 390): 12 > 4 at 22 ms > 12 at 273 ms, as first logged.
- Screenshots: shots/b1582p14-ch-390-icons-list24.png, shots/b1582p14-ch-390-icons-map24b.png (end states; the jump is in the per-frame data)
- Data: `qa/b1582p14-icons-*.json` > `frames` (list24, map24b, map2024r2, map1624r2); `qa/b1582p14-thumbs-390.json` > trans.Blount_list

## Re-test status, build 1613 (pass 34, Oct 19 ~11:04-11:20 AM EDT; line 9 = 202610181613)
- **QA-098 [CRITICAL, orchestrator ruling 11:03 AM: any title over another place's numbers] STILL OPEN in list view on 1613 (Chromium 390x844):** All States > address > Enter, staying in the list: Phoenix: crumb "Maricopa Precinct 242" over Trump 51% / Harris 48% (Maricopa County; precinct is Harris 70 / Trump 28); Tallahassee: "Leon Precinct 42" over Harris 60 / Trump 39 (Leon County; precinct 74 / 24); Austin: "Travis Precinct 300" over 69 / 29 (Travis County 68.8/29.4; precinct 69.3/28.4, close by chance). Michigan (Detroit) shows "Wayne County" over Wayne numbers: OK. After the globe all three show the precinct numbers (70/28, 74/24, 69/28): map side fixed. Shots: shots/b1613p33-ch-390x844-addr2-{AZ,FL,TX}-list.png (+ -tomap). Data qa/b1613p33-addr2-chromium-390x844.json.
- **QA-094 / QA-095 FIXED in WebKit 390x844 too (1613):** Harris 52/46, Miami-Dade 55/44 (55.4/43.9), Maricopa 51/48; FL senate # header 6.11M / 4.68M; 0 page errors (qa/p34-cot-wk.log, FAILS 0).
- **FL state house list reload (Chromium 390, 1613):** restores the same list (120 rows, same header and rows, `la:districts`); only the saved center moves 0.0125° at zoom 5 (invisible in list view). Not filed.
- **New: QA-104 [MEDIUM] Reload of a county map view drops the county layer.** Steps: Florida > counties > Miami-Dade > (Miami city) > back to the Miami-Dade map, saved state `"lt":"counties"`; reload. Expected the same state. Actual: saved state becomes `"lt":"none"`; title "Miami-Dade County" and Trump 55 / Harris 44 are kept, view kept (25.832,-80.218 z10). Chromium 390x844, build 1613. Data qa/b1612p33-states-chromium-390x844-r1613.json (filename prefix stale; build field 1613) > Florida.drill.reload.
- **QA-098 list view also still open in WebKit 390x844 (1613):** same crumbs over county numbers (Maricopa Precinct 242 over 51/48, Leon Precinct 42 over 60/39); map path and globe fine (qa/b1613p33-addr2-webkit-390x844.json).
- **QA-095 WebKit 390 (1613) FIXED:** MI 2.82M / 2.74M and NY 4.62M / 3.58M in all four district lists.
- **QA-100 FIXED on 1613 (NY data merge live):** NY state Harris 56% / Trump 43% (4,619,543 / 3,579,519, total 8,263,474 incl. others); Kings County = NYSBOE for 2016/2020/2024 (2024 601,265 / 233,964, other 12,705), Kings row 27.6 / 70.9 (orchestrator test qa/p34-ny-ch.log FAILS 0). **QA-101 now LOW:** Kings 27.6/70.9 vs Brooklyn borough 27.3/70.6 (0.3 pt). Side note: Kings County's list also has a "New York city" row with Brooklyn's numbers (27.3/70.6), labelled as the whole city; LOW, orchestrator to rule.
- **QA-003 re-rated under the new user rule (Oct 19 11:28 AM): state and national figures must equal the certified totals; gaps under 10,000 votes are accepted.** cmp.py on 1613 (qa/p34-cmp.log): accepted (<10k): all other states. **Still over 10k (open, MED):** NY 2020 Biden +13,901 (app 5,244,886 vs 5,230,985), NY 2020 total +22,035; 2024 total-vote gaps (others missing): IL -40,942, WA -25,408, MD -22,684, VA -20,712 (also Harris +1,617 / Trump +988), MA -20,231. National 2024 Harris +2,000, Trump +1,668 (accepted), total -258,202 (others); national 2020 Biden +10,404 (just over), Trump +6,685, total +40,722. ME 2020 Biden -4,599 is under 10k: accepted.
- **QA-003 re-judged under the UPDATED user rule (Oct 19 11:30 AM, supersedes the 10k rule above): pass if gap < 1% for a precinct, < 0.1% for a large state, < 0.01% for the whole country; state figures must use the certified state total.** 1613, qa/p34-cmp.log:
  - **Fail, country:** US 2024 total votes -0.166% (others short 258,202; Harris +0.0027%, Trump +0.0022% pass); US 2020 Biden +0.0128% (+10,404) and total +0.026%; Trump 2020 +0.009% pass.
  - **Fail, states (> 0.1%):** NY 2020 Biden +0.27% / Trump +0.22% / total +0.26% (large state; the 2024 NY merge did not fix 2020); PA 2020 total +0.14% (candidates pass); ME 2020 Biden -1.06%, Trump -0.23%; total-vote shortfalls 2024 (others missing, so third-party % is wrong): WY -1.00, ND -0.84, VT -0.82, MD -0.75, IL -0.73, WA -0.65, MA -0.58, RI -0.53, NE -0.53, NH -0.49, VA -0.46 (VA Harris +0.07 pass), AK 2020 -0.55, NH 2020 -0.22.
  - **Pass:** every other state/year (all candidate gaps < 0.1%). Severity: MED (wrong totals vs certified); fix = use certified state totals including others.
- **Chromium smoke, 5 sizes (390x844, 375x667, 320, 1024x576, 1024x768), build 1613:** console, page errors, failed requests all empty; CLS 0; no overlaps, clipping or off-screen controls. Over 100 ms: All States row 116-127 ms (QA-007 still open, all sizes except 320); US House deselect 124 ms at 1024x576. Data qa/b1612p33-flow-chromium-.json (filename prefix stale, run 11:23-11:31 AM on 1613).

- **Hourly run (11:04-11:40 AM EDT) additions on 1613, run alongside the pass-34 queue (shared log names):**
  - **Layout-stability sweep holds, no new jumps:** Chromium 390x844, 1024x768, 1024x576 and WebKit 375x667 (16 steps: slider open, All States, MA drill, '20/'24 year changes, Worcester, US House, Back x2, grouped bar, drill/back again, map). Step-for-step identical to pass 32 (`moved` lists equal): thumbnails, top fields, right buttons, slider, first row and bottom bar steady on year changes, drill-ins and Back; only the known items (slider opening pushes the map thumbnails down 68 px, chart button hidden on US House = QA-057, first row +14 px tall on the grouped-bar switch). Logs qa/p34-lay3-{ch390,ch768,ch576,wk375}.log; data qa/b1612p33-layout3-*.json (prefix stale, build 1613).
  - **Orchestrator verify list holds (Chromium):** PA '16 bar 48.2 / 47.5 / 4.4, pie 48.2 / 47.5; '24 50.4 / 48.7 / 1.0; '16 again identical (qa/p34-pa16-ch.log; official 48.18 / 47.46). Menus overlay at all 5 sizes, US and Alabama, nothing dimmed or shrunk (backdrop rgba(0,0,0,0), pie box 52,114-324,386 at 390, 210,114-800,704 at 1024x768), 0 errors (qa/p34-menus-ch.log).
  - **1613 change "DC address from a list opens the map on the address" + QA-093/103 hold in WebKit 390x844:** orchestrator test list-dc-globe 73 ok, FAILS 0 (DC row and DC address > globe show DC 90 / 6; map-DC reload keeps title, numbers, field, z15 view and colours; Phoenix / Tallahassee / Austin map searches show precinct numbers). qa/p34-dcg-wk.log.
  - **QA-104 also in WebKit 390x844 on New York:** Kings County map (`lt:counties`) > reload saves `lt:none`; title Kings County and 71 / 28 kept. qa/p34-states-wk.log > New York drill.reload.
  - **Unchanged on 1613 (Chromium 390, qa/b1613p33-{chip,074,other}-chromium-*.json):** QA-099 open (sort chip 288-322 x 177-199 overlaps the first row's Harris label box 258-376 x 194-216 in FL and TX county and city lists, time row open). QA-074 changed: no duplicate visible names left in CA/OH/TX, but the county / grade suffix that tells same-name rows apart is cut by the 100 px name column (e.g. "Eastern Local (Brown)" vs "(Meigs)" both read "Eastern Local…"; OH 50, CA 58, TX 23 rows); still MEDIUM. QA-073 School districts tap-to-paint CA 150, TX 203, PA 149, OH 110 ms (open). QA-018 open (bar tap on OH stays on All States). QA-006 / QA-015 hold.

## Re-test status, build 1612 (pass 33 rush, Oct 19 ~10:40-11:05 AM EDT; live line 9 moved to 202610181613 at 11:02 AM)
- Build **1612** (`7beb223`), every run read `window.BUILD` = 202610181612. Chromium 390x844 touch; WebKit 390x844 for QA-103.
- **QA-103 [CRITICAL] FIXED on 1612 (Chromium + WebKit 390x844):** all three ways (DC address from the map; All States > tap DC > globe; All States > DC address > globe) then reload: title "District of Columbia", Harris 90% / Trump 6%, saved `dc:1` kept, map coloured, same view (z15 / z11). 0 page errors. Precinct variant (Austin, map + list > globe) also survives reload (orchestrator test 0 FAILS). Shots: qa/b1612p32-{ch,we}-390x844-dcreload-{mapaddr,dcrow,listaddr}-{before,after}.png. Data: qa/b1612p32-dcreload-{chromium,webkit}-390x844.json, qa/p33-orch-dcg-ch.log.
- **QA-094 [CRITICAL] FIXED on 1612 (Chromium 390):** Harris County cities list thumbnails Harris 52% / Trump 46% (row 52.0/46.4); Miami-Dade Trump 55 / Harris 44 (55.4/43.9); Maricopa Trump 51 / Harris 48 (51.2/47.7). Reload keeps Harris County 52/46. Log qa/p33-orch-cot-ch.log; data qa/b1612p33-states-chromium-390x844-r1612.json.
- **QA-095 [CRITICAL] FIXED on 1612 (Chromium 390):** # mode thumbnails show the official state total in every district list (senate, state house, schools, US House): MI 2.82M / 2.74M, NY 4.62M / 3.58M, FL 6.11M / 4.68M (also WI 1.70M / 1.67M).
- **QA-098 [CRITICAL] FIXED on the map, PARTLY in the list (Chromium 390):** All States > Phoenix / Tallahassee / Austin address > Enter > globe: Maricopa Precinct 242 Harris 70 / Trump 28; Leon Precinct 42 74 / 24; Travis Precinct 300 69 / 28; same as a map search. **Remaining (list view, before the globe):** the crumb reads "Maricopa Precinct 242" while thumbnails show Maricopa County 51 / 48 (Leon Precinct 42 over 60 / 39; Austin 69/29 ok-ish since Travis matches). Severity: CRITICAL (orchestrator ruling 11:03 AM). Data qa/b1612p33-addr2-chromium-390x844.json > AZ-list/FL-list.
- **QA-100 / QA-101 still open:** NY counties still two-party only (Kings 28.0 / 72.0; Brooklyn borough 27.3 / 70.6); NY state 56 / 44 (= 4.62M / 3.58M, no others), Trump should be 43.3%. NY data merge not live in 1612.
- Note: FL statehouse list reload dropped `la`?/same flag false for FL statehouse & Miami-Dade drill reload (MI/NY same=true); needs a re-look on 1613, not filed yet.

## Re-test status, build 1611 (pass 32, live line 9 = 202610181611 at start ~8:50 AM and end ~9:30 AM; Oct 19 ~8:50-9:35 AM EDT)
- Build **1611** (`f435ab2`, origin/main 8:47 AM: QA-093 DC picked in All States then the globe shows DC's title and numbers; QA-092 All States keeps the zoom-4 US view). Every pass-32 run read `window.BUILD` = 202610181611 (each JSON has `build`); data and shots are prefixed `b1611p32-*`. One engine at a time (Chromium runs 8:50-9:17, WebKit 9:17-9:27), touch on; the Chromium functional runs went 2-3 browsers in parallel, so their tap timings (school-district picks, Texas counties, city drill-ins) are noisy and not used for QA-073 / QA-102; QA-085 and the smoke flow ran alone (QA-085 state house overlapped one other Chromium run for its first ~1 min). No console errors or page errors in any pass-32 run (one `net::ERR_ABORTED` on the `?bc=` reload request in the Arizona reload step, a navigation abort, not an app error). No v3 yet (https://ge0r9b.github.io/us-districts/v3/ 404 at 8:50 AM and ~9:30 AM; no v3 in HANDOFF.md on origin/main `f435ab2`).
- **QA-093 [CRITICAL] fixed on 1611 (verified pass 32), both engines, 390x844 and 1024x768:** All States > tap DC (thumbnails Harris 90% / Trump 6%) > globe: title "District of Columbia", thumbnails Harris 90% / Trump 6% (# mode 90.3% / 6.5% when toggled), map at 38.893, -77.014, zoom 11; the address path ("1600 Pennsylvania Ave NW, Washington, DC 20500" + Enter from All States) the same at 38.899, -77.032, zoom 15. Toggling the globe 4 times keeps DC each time. Orchestrator test `tests/list-dc-globe.py` against the live site: 0 FAILS in Chromium and WebKit 390 (copied as `qa/p32-orch-list-dc-globe.py`, logs `qa/p32-orch-{ch,wk}.log`). Shots: shots/b1611p32-{ch,we}-390x844-globe-{tapdc,addr}-1.png, shots/b1611p32-{ch,we}-1024x768-globe-{tapdc,addr}-1.png. Data: `qa/b1611p32-globe-{chromium,webkit}-{390x844,1024x768}.json` > `tapdc`, `addr`. **But a reload of that DC map view brings the QA-093 screen back: new QA-103 below.**
- **QA-092 [MEDIUM] fixed on 1611 (verified pass 32), both engines, 390x844 and 1024x768:** fresh load > All States > globe: map at 39.775, -98.613, **zoom 4**, title "United States", Trump 50% / Harris 48% (pass 31: 48.225, -94.219, zoom 2); the same as after Back > Back from LA County (39.775, -98.613, zoom 4). The hidden map under the All States list now also sits at zoom 4. Shots: shots/b1611p32-{ch,we}-{390x844,1024x768}-globe-fresh-1.png. Data: `qa/b1611p32-globe-*.json` > `fresh`.
- **QA-090 / QA-091 / QA-087 still fixed (1611):** DC address search from a list, `#listView.scrollTop` per frame: Chromium 390 All States 0 > 882 at 771 and 840 ms, Philadelphia 900 ms; WebKit 390 Philadelphia 1070 ms, All States 794 ms: one scroll each (5/5), no return to the top; end state "All States" header, DC row "DC | 90.3%" selected (`lasel`) and on screen (y 710-740), thumbnails Harris 90% / Trump 6% (QA-087 holds). WebKit saves DC (38.8987, -77.0352, zoom 15) and the globe opens there (QA-091 holds). Data: `qa/b1611p32-addr-{chromium,webkit}-390x844.json`.
- **New: QA-103 [CRITICAL by the QA-093 ruling]** a DC map view does not survive a reload: the saved state now has `"dc":1`, but after the reload the title and numbers are the US's over the DC outline (both engines, all three ways to pick DC). Details below.
- **Open bugs, all unchanged on 1611 (Chromium 390x844):**
  - QA-094 [CRITICAL] still open: Harris County cities list thumbnails **Harris 56% / Trump 42%** (county row 46.4% / 52.0%, county map after reload 52% / 46%); Miami-Dade **Trump 53% / Harris 46%** (county 55.4% / 43.9%); Maricopa **Trump 50% / Harris 49%** (county 51.2% / 47.7%). Same as 1610.
  - QA-095 [CRITICAL] still open (# thumbnails, Trump / Harris): Florida senate 6.03M / 4.62M, house 6.03M / 4.64M, US House 6.06M / 4.66M, schools 6.11M / 4.68M; New York senate Harris 4.56M / Trump 3.48M, house 4.51M / 3.46M, schools 4.63M / 3.59M, US House 4.62M / 3.58M; Michigan senate 2.72M / 2.63M, house 2.74M / 2.66M, schools 2.73M / 2.64M, US House 2.81M / 2.73M; Texas 6.39-6.40M / 4.83-4.84M. All identical to 1610 (FEC FL 6,110,125 / 4,683,038; NY 4,619,195 / 3,578,899; MI 2,816,636 / 2,736,533; `qa/fec24.json`).
  - QA-098 [CRITICAL] still open: from the All States list, "1700 W Washington St, Phoenix, AZ 85007" > title "Maricopa Precinct 242", thumbnails **Trump 51% / Harris 48%**, one row "Maricopa | 51.2% | 47.7%"; globe: same title and numbers (from the map: Harris 70% / Trump 28%, popup 70.4% / 28.3%). Tallahassee "Leon Precinct 42" Harris 60% / Trump 39% (map path 74% / 24%); Austin "Travis Precinct 300" 69% / 29% (map path 69% / 28%, popup 69.3% / 28.4%). Shots shots/b1611p32-ch-390x844-addr2-{AZ,FL,TX}-list{,-tomap}.png. Data `qa/b1611p32-addr2-chromium-390x844.json`.
  - QA-096 [HIGH] still open: city precinct list > globe, both thumbnails empty ("Kamala Harris 2024 / ") for Houston city, Miami city, Brooklyn borough, Phoenix city (4/4). Shots shots/b1611p32-ch-390x844-st-*-drill-sub-map.png.
  - QA-100 [HIGH] still open: NY county rows Kings 28.0% / 72.0%, Suffolk 55.0 / 45.0, Nassau 52.1 / 47.9, Queens 37.7 / 62.3 (sum 100%); Brooklyn borough 27.3% / 70.6%; Kings map after reload 72% / 28%.
  - QA-101 [LOW] still open: NY map Trump 44%; `__stTot` total 8,198,094 (FEC 8,262,495).
  - QA-097 [MEDIUM] still open (exact pass-31 steps with the Florida range step, `qa/b1611p32-states-chromium-390x844-fl097.json`): saved `"vw":"map"` before, `"vw":"list"` after the reload; the Miami-Dade bar chart 55.4% / 43.9% / 0.7% in list view. Shot shots/b1611p32-ch-390x844-st-Florida-drill-reload.png. Without the range step (TX, FL, NY, AZ in the main run) the county map is restored as before.
  - QA-099 [MEDIUM] still open: chip at x 288-322, y 177-199; first row's bar at y 194-216 (5 px under the chip) in the Florida and Texas county lists and the Miami-Dade and Harris city lists; first rows "Miami-Dade | 55.4%", "Harris | 46.4%", "Miami city | 48.7%" still show one label. `qa/b1611p32-chip-chromium-390.json`, shots shots/b1611p32-ch-390-chip-*.png.
  - QA-102 [MEDIUM] not re-measured cleanly (the state run shared the CPU with 2 other browsers: "Texas counties" 125 ms, Houston city 362 ms, Miami city 131, Brooklyn 128, Phoenix 53); treat as unchanged.
  - QA-073 [MEDIUM] same caveat (parallel run): School districts picks California 133 ms, Texas 205 / 169, Pennsylvania 261, Ohio 172, New York 214, Michigan 177, Florida 28-50. Still over 100 ms; the numbers are inflated by the shared CPU, not comparable with pass 31.
  - QA-085 [borderline, now a little worse] Chromium 1024x576 alone (except the first ~1 min), PA year taps '16 > '24 > '20 > '24 x3 (12 taps, min / median / max): state house 99 / **111** / 155 ms (11 of 12 over 100; pass 30: median 105), state senate 19 / **105** / 142 (6/12; pass 30: 62), PA county map 29 / **103** / 174 (6/12; pass 30: 90). Picking State house 90 ms, State senate 81. 1611 changed nothing here, so part of this is run-to-run noise; still open. Shot shots/b1611p32-ch-1024x576-ylat-PA-statehouse.png. Data `qa/b1611p32-ylat-chromium-1024x576.json`.
  - QA-007 [MEDIUM] still open: Chromium smoke flow (alone) All States row tap **108 ms** at 390x844, 83 at 375, 88 at 320, **108 at 1024x576, 114 at 1024x768** (pass 30 Chromium: 94 / 82 / 74 / 103 / 103).
  - QA-018 still open (OH row tapped at 55% of its width, on the bar `I.sg rep`: stays on All States), shot shots/b1611p32-ch-390-018-OHbar.png. QA-074 still open on screen: Ohio 611 rows, 16 names repeated, Texas 1,019 rows / 12 names, California 974 rows; visible text cut to 31 characters + "…", "(County)" never visible (`qa/b1611p32-074-chromium-390x844.json`, shots shots/b1611p32-ch-390x844-074-*.png). QA-006 still fixed (Philadelphia 1 row, 20.0% / 78.5%). QA-015 the same (40.0029 > 40.0027, -75.118, z10, `lt` kept). Data `qa/b1611p32-other-chromium-390.json`.
- **Fresh coverage, the same five states (Chromium 390x844):** 2016 / 2020 / 2024 state thumbnails unchanged and matching FEC (TX 52/43, 52/46, 56/42; FL 49/48, 51/48, 56/43; NY 59/37, 61/38, 56/44; MI 47/47, 51/48, 50/48; AZ 52/47 in 2024); row counts TX 31 / 150 / 1,019 / 38, FL 40 / 120 / 67 / 28, NY 63 / 150 / 680 / 26, MI 38 / 110 / 540 / 13; no overlaps, clipping or off-screen text in any list (% and #); state house list reloads restore the list (TX, FL, NY, MI). Data `qa/b1611p32-states-chromium-390x844-b.json`, summary `python3 qa/p32-sum.py <json>`.
- **Orchestrator verify list holds (1611):** Chromium 390 own-check identical to pass 31 field for field except timings ('16 colours: CA, NY, IL, CO, VA, WA blue; TX, OH, KS red; FL, PA, MI, WI near-white red tint, script flag "?" as before; official 2016 margins there are all under 1.2 points (PA Trump 48.2 / Clinton 47.5), so a pale red is right; US '16 Clinton 48% / Trump 46%; PA rows number only "1", "4", "17" / "10", "12"; DE "At-large", DC "At-large 90.3%"; thumbnails on the icon axis in all views), `qa/b1611p32-own-chromium-iphone390.json`. PA '16 bar 48.2 / 47.5 / 4.4, pie 48.2 / 47.5; '24 50.4 / 48.7 / 1.0, pie 50.4 / 48.7; '16 again the same (WebKit 390, `qa/b1611p32-pa16-webkit-390x844.json`; official PA 2016 48.18 / 47.46, 2024 50.37 / 48.66). Menus overlay with nothing dimmed or shrunk at all 5 sizes, US and Alabama (pie box 52,114-324,386 at 390, 210,114-800,704 at 1024x768, backdrop rgba(0,0,0,0), open 13-25 ms; WebKit, `qa/b1611p32-menus-webkit-.json`). Sort chip: clear in All States (smoke flow, no overlaps) but not in county / city lists (QA-099). The 60-check sort-chip harness was not re-run.
- **Smoke flow, Chromium, all 5 sizes, touch (1611, run alone):** every recorded field (rows, sort flip, # mode, 2020, range, chart options, PA / Philadelphia / townships, Back, US House rows, restore, address suggestions) identical to the pass-30 Chromium run at all 5 sizes; no overlaps, clipping or off-screen elements; reload restores PA > Philadelphia County list, bar, #, 2024. Taps over 100 ms: only the All States row (QA-007, above). All others 10-79 ms. Data `qa/b1611p32-flow-chromium-.json`, shots shots/b1611p32-ch-{390,375,320,1024x576,1024x768}-*.png, compare `python3 qa/p32-flowcmp.py qa/b1609p30-flow-chromium-.json qa/b1611p32-flow-chromium-.json`.
- **Layout sweep (16 steps, 1611), WebKit 390x844 and 1024x768:** nothing moved on any view switch (MA > Worcester County results with the slider > US House list), year change, drill-in or Back except the expected ones (map thumbnails +68 px when the time row opens, first row 30 > 44 px for split bar, chart button hidden with the type row open, back chevron appears / goes); no transients. Data `qa/b1611p32-layout3-webkit-{390,1024x768}.json`, shots shots/b1611p32-we-*-ls3??-*.png.
- Skipped (time): sort-chip 60-check harness; WebKit smoke flow (ran in pass 31); layout sweep at 375 / 320 / 1024x576; clean single-browser re-measure of QA-073 / QA-102; WebKit QA-085; institution / type flows in WebKit; QA-005 / QA-064 / QA-072 direct re-runs.

### QA-103 [CRITICAL by the QA-093 ruling (same screen); orchestrator to confirm] A DC map view does not survive a reload: US title and US numbers over the DC outline
- Severity: CRITICAL by the QA-093 ruling (the same mixed screen QA-093 had: DC drawn, the US title and numbers); the user just has to reload. Not a regression of 1611: the pass-30 data (`qa/b1609p30-addr-chromium-390x844.json` > `after_reload`) already showed "United States" 50% / 48% at DC zoom 15 after a reload, but it was not looked at then. New on 1611: the saved state now carries `"dc":1`, and it is dropped on load. | Build 1611 | Chromium and WebKit 390x844, touch
- Steps: (a) from the map: type "1600 Pennsylvania Ave NW, Washington, DC 20500" + Enter; or (b) geo button > All States > tap the DC row > globe; or (c) All States > the same address + Enter > globe. Then reload the page.
- Expected: the DC view comes back (title "District of Columbia", Harris 90% / Trump 6%), as the saved state says (`{"v":1,...,"vw":"map","dc":1,"ll":[38.8926,-77.0142,11]}`); or, if DC is not restored, the US view (zoom 4) under the US title.
- Actual: the map comes back on DC (zoom 15 for (a) and (c), zoom 11 for (b)) with DC's white outline and DC itself unshaded, but the title is **"United States"**, the thumbnails **Trump 50% / Harris 48%**, the bottom field "DC 20220" / "DC 20565" / "DC 20045" (a ZIP name); the saved state after the load has lost `"dc":1`. Same in both engines, all 3 paths (6/6).
- Screenshots: shots/b1611p32-ch-390x844-dcreload-dcrow-after.png (compare shots/b1611p32-ch-390x844-dcreload-dcrow-before.png), shots/b1611p32-ch-390x844-dcreload-{mapaddr,listaddr}-after.png, shots/b1611p32-we-390x844-dcreload-*-after.png
- Data: `qa/b1611p32-dcreload-{chromium,webkit}-390x844.json` (`before`, `snap_before`, `after`, `snap_after`); script `qa/p32-dcreload.py`

## Re-test status, build 1610 (pass 31, live line 9 = 202610181609 at the start ~7:58 AM, 202610181610 from ~8:00 AM; Oct 19 ~7:58-8:50 AM EDT)
- **The build changed at the start of this pass:** line 9 read 202610181609 at 7:58 AM; **1610** (`b3a622e`, 7:57 AM: QA-074 same-name school districts labelled with their county) was live by the first run (7:59 AM). Every pass-31 run read `window.BUILD` = 202610181610 (each JSON has `build`), so all data and shots are prefixed `b1610p31-*`. Line 9 at the end: 202610181610 (~8:44 AM). One engine at a time (the Chromium state/address probes ran during the Chromium part of the queue, the WebKit runs after them), touch on. No console errors, page errors or failed requests in any pass-31 run. No v3 yet (https://ge0r9b.github.io/us-districts/v3/ 404 at 7:58 AM and 404 at ~8:44 AM).
- **New: 9 bugs, 3 of them CRITICAL (wrong numbers):** QA-094 [CRITICAL] county city lists show the sum of the cities, not the county (Harris County 56% / 42% vs 52% / 46%; Miami-Dade, Maricopa); QA-095 [CRITICAL, QA-017 family] state senate / house / US House / school lists show state totals 0.5-3.9% below FEC (MI senate 2.72M / 2.63M vs 2.82M / 2.74M; NY, FL); QA-098 [CRITICAL, QA-087 family] a non-DC address searched from the All States list shows the precinct's title over the county's numbers, wrong winner in Phoenix; QA-096 [HIGH] city precinct list > map: thumbnails without numbers; QA-100 [HIGH, may be critical] NY county rows are two-party only (Kings 28.0 / 72.0 vs Brooklyn borough 27.3 / 70.6); QA-097 [MEDIUM] Florida city map reload comes back as the county list; QA-099 [MEDIUM] sort chip 5 px over the first row's bar in county / city / district lists; QA-102 [MEDIUM] Texas counties list 131-150 ms, city precinct drill-ins 106-108 ms; QA-101 [LOW] NY map Trump 44% (FEC 43.3%). Details below. The first four only show outside Pennsylvania (PA counties are fully covered by municipalities; PA and CA were the states tested so far).
- **QA-074 (1610 change) still open on screen:** the labels exist but cannot be seen. The row text is cut to 31 characters plus "…" in the DOM (`.nmx` textContent, no title or aria-label) and about 14 characters are visible at 390, so the "(County)" suffix never shows: Ohio 39 rows / 16 names still look identical (Buckeye, Crestview, Eastern, Highland, Madison, ... Local School District), Texas 24 rows / 12 names (Big Sandy, Centerville, Chapel Hill, Dawson, Edgewood, ... Independent School District), California the same as pass 30 (Caruthers, Eureka City, Healdsburg, Hope, ...). Shots: shots/b1610p31-ch-390x844-074-{Ohio,Texas,California}.png. Data: `qa/b1610p31-074-chromium-390x844.json` (`dup_visible`, `paren_rows`, `sw` > `cw`), `qa/b1610p31-other-chromium-390.json`, script `qa/p31-074.py`.
- **QA-092 still open (1610), both engines:** fresh load > All States > globe: map at 48.225, -94.219, zoom 2, thumbnails Trump 50% / Harris 48%; after Back > Back from LA County the map opens at 39.775, -98.613, zoom 4 (Chromium and WebKit 390). Shots: shots/b1610p31-{ch,we}-390-globe-fresh-1.png. Data: `qa/b1610p31-globe-{chromium,webkit}-390.json`.
- **QA-093 [CRITICAL] still open (1610), both engines:** All States > tap DC (thumbnails Harris 90% / Trump 6%) > globe: map at DC (38.893, -77.014, zoom 11) but title "United States" and thumbnails Trump 50% / Harris 48%; the address path the same (zoom 15). Not fixed. Shots: shots/b1610p31-{ch,we}-390-globe-{tapdc,addr}-1.png.
- **Fresh coverage outside PA / CA / OH (Chromium 390x844, Texas, Florida, New York, Michigan, Arizona):** 2016 / 2020 / 2024 state thumbnails match FEC for all five (TX 52/43, 52/46, 56/42; FL 49/48, 51/48, 56/43; NY 59/37, 61/38, 56/44 (QA-101); MI 47/47, 51/48, 50/48; AZ 49/45, 49/49, 52/47); `__stTot` 2024 equals FEC for Trump and Harris in all five, totals within 0.08% except NY. Texas ranges (bar chart, # numbers): '20>'24 Trump +503K, Biden/Harris -424K (FEC +503,250 / -423,876); '16>'24 line +1.21M / +1.38M then +503K / -424K (FEC right). District types: TX 31 senate / 150 house / 1,019 school / 38 US House rows, FL 40 / 120 / 67 / 28, NY 63 / 150 / 680 / 26, MI 38 / 110 / 540 / 13; the first rows of every list run high to low by total votes (# mode), % and # both switch (the sort flip was not exercised here: the script's chip check missed the fixed-position chip), no overlaps / clipping / off-screen text in any list (layout check), all type picks 40-78 ms except School districts (QA-073). Reload of a state house list restores it (TX, FL, NY, MI: same `st`, `lt`, `vw` list, row count; only `ll` moves a little, QA-015). Drill-ins to precinct level: Harris County > Houston city (636 precincts), Miami-Dade > Miami city (123), Kings > Brooklyn borough (1,306 election districts), Maricopa > Phoenix city (303); precinct list headers match the city's row. Range chart menu (FL, TX): '16>'20 / '20>'24 / '16>'24 each offer the other chart types; line and bar draw, no overlaps; the 4M line-chart axis label sits at the right end (moved off the lines, not filed). Data: `qa/b1610p31-states-chromium-390x844-b.json`, `qa/b1610p31-states-chromium-390x844-tx-run1.json` (Texas types and ranges; the first run's '#' step left `__numMode` in a bad test state, its # / % fields after the senate step are not used), script `qa/p31-states.py`, summary `qa/p31-sum.py`.
- **Address search, non-DC (Chromium 390x844):** from the map, all four go to the precinct with matching popup and thumbnails: "1100 Congress Ave, Austin, TX 78701" > Travis Precinct 300 (Harris 69.3% / Trump 28.4%, zoom 13), "400 S Monroe St, Tallahassee, FL 32399" > Leon Precinct 42 (73.6% / 24.0%), "1700 W Washington St, Phoenix, AZ 85007" > Maricopa Precinct 242 (70.4% / 28.3%, zoom 14), "2 Woodward Ave, Detroit, MI 48226" > Wayne County (63% / 34%, no precinct layer). A reload brings back the county (Travis County 69% / 29%, Leon 60% / 39%, Maricopa 51% / 48%) at the same map position (the precinct is not saved; QA-015 style). From the All States list: QA-098. Data: `qa/b1610p31-addr2-chromium-390x844.json`.
- **Layout sweep (16 steps), WebKit 375x667 and 320x568, Chromium 1024x576 (1610):** nothing moved on any view switch, year change, drill-in or Back except the expected ones (map thumbnails +68 px when the time row opens, first row 30 > 44 px for split bar, chart button hidden with the type row open, back chevron appears/goes); Chromium 1024x576 step 2 crumbs transient (the same as 1024x768 in passes 28-30). Data: `qa/b1610p31-layout3-{webkit-375,webkit-320,chromium-1024x576}.json`, shots shots/b1610p31-{we,ch}-*-ls3??-*.png.
- **Smoke flow, WebKit, all 5 sizes, touch (1610; skipped in passes 29-30):** every recorded field (All States rows, sort flip, # mode, 2020, range, chart options, PA / Philadelphia / precincts, Back, US House rows, address suggestions, DC result) identical to the pass-30 Chromium run at all 5 sizes; no overlaps, clipping or off-screen elements; CLS 0 everywhere; reload restores PA > Philadelphia County list, bar, #, 2024 (`lt` counties > none as before). Taps over 100 ms: All States row 110 / 126 / 108 / 121 / 119 ms (390 / 375 / 320 / 1024x576 / 1024x768, QA-007), opening the geo menu 106 ms and Back 101 ms at 375, type deselect 108 ms on both iPad sizes, and once Philadelphia city > precincts **765 ms** at 375 (35-40 ms at the other sizes; a first-visit spike, not repeated). Data: `qa/b1610p31-flow-webkit-.json`, shots shots/b1610p31-we-*.png.
- **QA-085 at 390x844 (WebKit, 1610):** PA year taps '16 > '24 > '20 > '24 x3 (12 taps, min / median / max, tap > next paint): state house 13 / 64 / 108 ms (1 of 12 over 100), state senate 11 / 35 / 47 (0/12), PA county map 16 / 37 / 51 (0/12); picking State house 89 ms, State senate 83. Fine at the phone size in WebKit; still only the Chromium 1024x576 state house median (105 ms in pass 30) is borderline. Chromium 390 not run (time). Data: `qa/b1610p31-ylat-webkit-390x844.json`, shot shots/b1610p31-we-390x844-ylat-PA-statehouse.png.
- **Older open bugs, quick status (Chromium 390x844, 1610):** QA-018 still open (OH row tapped at 55% of its width, on the bar `I.sg rep`: stays on All States). QA-006 still fixed (Philadelphia townships 1 row "Philadelphia city | 20.0% | 78.5%"). QA-015 the same (40.0024, -75.1176 > 40.0027, -75.118, z10, `lt` kept). QA-073 still over 100 ms: School districts tap-to-next-paint California 157 ms, Texas 255 (and 256 in the state run), Pennsylvania 88, Ohio 123, New York 169, Michigan 132, Florida 74. QA-007: WebKit smoke flow All States row 108-126 ms at all 5 sizes (Chromium pass 30: 74-103 ms), still open. Shot: shots/b1610p31-ch-390-018-OHbar.png. Data: `qa/b1610p31-other-chromium-390.json`.
- **Orchestrator verify list holds (1610):** Chromium 390 own-check identical to pass 30 field for field ('16 colours: CA, NY, IL, CO, VA, WA blue; TX, OH, KS red; FL, PA, MI, WI near-white red tint as before, script flag "?"; US '16 labels Clinton 48% / Trump 46%, PA '16 Trump 48% / Clinton 47%; PA US House rows number only "1", "4", "17", senate "10", "12"; DE "At-large", DC "At-large 90.3%"; thumbnails on the icon axis in all views; layer picks 2-86 ms). `qa/b1610p31-own-chromium-iphone390.json`. Exception: the sort chip is not clear of the first row in the county, city and district lists (QA-099); the All States checks of pass 30 were not re-run.
- Skipped (time): Chromium QA-085 at 390x844 (WebKit only), sort-chip 60-check harness, PA '16 pie/bar and menus re-runs (not in the 1610 change), institution / type flows in WebKit, QA-005 / QA-064 / QA-072 direct re-runs.

### QA-094 [CRITICAL (wrong numbers)] County "townships" list: the thumbnails show the sum of the cities, not the county, where part of the county is unincorporated
- Severity: CRITICAL (wrong numbers under the county's title; gaps of 2-4 points) | Build 1610 | Chromium 390x844, touch
- Steps: type "Texas" in the bottom field + Enter > geo button > "Texas counties" > tap the Harris row (Harris County cities list). Same with Florida > Miami-Dade and Arizona > Maricopa.
- Expected: title "Harris County" with Harris County's numbers (its row in the Texas counties list is 46.4% Trump; the county map and a reload show Harris 52% / Trump 46%).
- Actual: the thumbnails show **Harris 56% / Trump 42%** (in # mode 499K / 374K, while the county row is 809K / 723K), which is the sum of the 34 city rows only (Houston 433K / 272K, ...); the unincorporated part of the county is left out. Miami-Dade County: thumbnails **Trump 53% / Harris 46%**; the county is 55.4% / 43.9% (its row, and the bar chart after a reload). Maricopa County: thumbnails **Trump 50% / Harris 49%**; the county row 51.2% / 47.7%, county map 51% / 48%. Pennsylvania counties do not show it (every PA county is fully covered by townships/boroughs/cities), which is likely why it was not seen before.
- Screenshots: shots/b1610p31-ch-390x844-st-Texas-drill-Harris.png, shots/b1610p31-ch-390x844-st-Florida-drill-Miami-Dade.png, shots/b1610p31-ch-390x844-st-Arizona-drill-Maricopa.png (compare shots/b1610p31-ch-390x844-st-Florida-drill-reload.png: Miami-Dade 55.4% / 43.9%)
- Data: `qa/b1610p31-states-chromium-390x844-b.json` > `<state>.drill` (`rows1` county rows, `th2` thumbnails in the county list, `reload.th`); `qa/b1610p31-states-chromium-390x844-tx-run1.json` > `Texas.drill` (# mode: `th2` 499K / 374K, `rows1` "Harris | 723K | 809K"); script `qa/p31-states.py`

### QA-095 [CRITICAL (wrong numbers, QA-017 family)] State district lists: the state totals in the thumbnails are 0.5-3.9% below the official totals
- Severity: CRITICAL (wrong numbers over the 0.5% line; same family as QA-017, which was critical) | Build 1610 | Chromium 390x844, touch
- Steps: type a state + Enter > district-type button > State senate (or State house, US House, School districts) > globe button (list) > `#` button > `#`.
- Expected: the state's thumbnails show the state's result, as on the state map (`__stTot` = FEC exactly for FL, MI; NY see QA-101).
- Actual (# thumbnails, Trump / Harris, vs FEC 2024):
  - Florida (FEC 6,110,125 / 4,683,038): State senate **6.03M / 4.62M** (-1.3% / -1.3%), State house **6.03M / 4.64M** (-1.3% / -0.9%), US House 6.06M / 4.66M (-0.8% / -0.5%); School districts 6.11M / 4.68M (right).
  - New York (FEC Harris 4,619,195 / Trump 3,578,899): State senate **4.56M / 3.48M** (-1.3% / -2.8%), State house **4.51M / 3.46M** (-2.4% / -3.3%), School districts 4.63M / 3.59M (+0.2% / +0.3%), US House 4.62M / 3.58M (right). The % thumbnails in the senate and house lists read Trump 43% while the NY map reads 44%.
  - Michigan (FEC Trump 2,816,636 / Harris 2,736,533): State senate **2.72M / 2.63M** (-3.4% / -3.9%), State house 2.74M / 2.66M (-2.7% / -2.8%), School districts 2.73M / 2.64M (-3.1% / -3.5%), US House 2.81M / 2.73M (right).
  - Texas: all four lists within 0.1% (6.39-6.40M / 4.83-4.84M).
  The thumbnails look like the sum of the list rows (district estimates, some labelled "≈ estimate"), which do not add up to the state.
- Screenshots: shots/b1610p31-ch-390x844-st-Michigan-senate-list-num.png, shots/b1610p31-ch-390x844-st-NewYork-statehouse-list-num.png, shots/b1610p31-ch-390x844-st-Florida-senate-list-num.png
- Data: `qa/b1610p31-states-chromium-390x844-b.json` > `<state>.types.<type>.th_num` (and `tot` = `__stTot`), FEC `qa/fec24.json`; script `qa/p31-states.py`

### QA-096 [HIGH] City / borough precinct list > globe: the map thumbnails show no numbers
- Severity: HIGH (numbers missing on the main view) | Build 1610 | Chromium 390x844, touch
- Steps: state + Enter > geo button > "<state> counties" > a county > the first city (Houston city, Miami city, Phoenix city, Brooklyn borough) > globe button (list > map).
- Expected: the map with the place's numbers next to the thumbnails (as in the precinct list just before: Houston city Harris 60% / Trump 38%).
- Actual: title "Harris County Houston city" (and "Miami city", "Maricopa County Phoenix city", "Brooklyn borough"), the precinct heat drawn, but both thumbnails have **no number** at all (empty label), in 4 of 4 states. The map stays at the county view (Houston: zoom 8, 30.017, -95.433).
- Screenshots: shots/b1610p31-ch-390x844-st-Texas-drill-sub-map.png, shots/b1610p31-ch-390x844-st-Florida-drill-sub-map.png, shots/b1610p31-ch-390x844-st-NewYork-drill-sub-map.png, shots/b1610p31-ch-390x844-st-Arizona-drill-sub-map.png
- Data: `qa/b1610p31-states-chromium-390x844-b.json` > `<state>.drill.map3` (thumbnail text "Kamala Harris 2024 / " with nothing after it), `th3` (list values)

### QA-097 [MEDIUM] Reload on the city-level map (Florida, after a range/chart change) comes back as the county list view
- Severity: MEDIUM (wrong view restored) | Build 1610 | Chromium 390x844, touch
- Steps: Florida + Enter > time button, '16>'20 / '20>'24 / '16>'24 with each chart, back to '24 > geo > "Florida counties" > Miami-Dade > Miami city > globe (map) > reload.
- Expected: the map view restored (saved `vw` "map").
- Actual: saved state `{"co":"Miami-Dade County","lt":"counties","tb":true,"ch":"bar","vw":"map",...}`; after the reload `"lt":"none","vw":"list"`: the Miami-Dade single-place bar chart (55.4% / 43.9%) in the list view. The same path in Texas, New York and Arizona (no range step) restores the county map. The city level itself is not restored in any state (not in the saved state; QA-015 style, not filed).
- Screenshots: shots/b1610p31-ch-390x844-st-Florida-drill-sub-map.png (before), shots/b1610p31-ch-390x844-st-Florida-drill-reload.png (after)
- Data: `qa/b1610p31-states-chromium-390x844-b.json` > `Florida.drill.reload` (`before`, `after`)

### QA-098 [CRITICAL (wrong numbers, QA-087 family)] Non-DC address search from the All States list: the title is the precinct, the numbers are the county's (wrong winner in Phoenix)
- Severity: CRITICAL (wrong numbers under the place's title; like QA-087, ruled critical) | Build 1610 | Chromium 390x844, touch
- Steps: fresh load > geo button > All States > tap the bottom field > type "1700 W Washington St, Phoenix, AZ 85007" > Enter; then the globe button.
- Expected: as the same search from the map does: title "Maricopa Precinct 242", Harris 70% / Trump 28% (popup Harris 70.4% / Trump 28.3%).
- Actual: list header "Maricopa Precinct 242 counties" with one row (Maricopa 51.2% / 47.7%) and thumbnails **Trump 51% / Harris 48%** (Maricopa County's numbers, wrong winner for the precinct); map position zoom 6 (34.21, -111.93). Globe > map: title still "Maricopa Precinct 242", thumbnails still **Trump 51% / Harris 48%**, no popup. Same pattern: "400 S Monroe St, Tallahassee, FL 32399": title "Leon Precinct 42", thumbnails **Harris 60% / Trump 39%** (Leon County) vs the precinct's 73.6% / 24.0% from the map path; "1100 Congress Ave, Austin, TX 78701": "Travis Precinct 300" with Travis County's 69% / 29% (precinct 69.3% / 28.4%). Detroit ("2 Woodward Ave") resolves to Wayne County on both paths (no precinct), consistent. From the map all four are right.
- Screenshots: shots/b1610p31-ch-390x844-addr2-AZ-list.png, shots/b1610p31-ch-390x844-addr2-AZ-list-tomap.png, shots/b1610p31-ch-390x844-addr2-FL-list.png, shots/b1610p31-ch-390x844-addr2-FL-list-tomap.png, shots/b1610p31-ch-390x844-addr2-TX-list.png (compare shots/b1610p31-ch-390x844-addr2-AZ-map.png)
- Data: `qa/b1610p31-addr2-chromium-390x844.json` > `<ST>-list` (`res`, `rows`, `tomap`) vs `<ST>-map`; script `qa/p31-addr2.py`

### QA-099 [MEDIUM] Sort chip overlaps the first row's bar by 5 px and hides its second label (time row open, county and city lists)
- Severity: MEDIUM (overlap; verify-list rule "chip clear of every row's bars and labels") | Build 1610 | Chromium 390x844, touch
- Steps: Florida (or Texas) + Enter > time button (row open) > geo button > "<state> counties"; then tap Miami-Dade (or Harris).
- Expected: the chip clear of the first row, as in All States.
- Actual: chip at x 288-322, y 177-199; the first row's bar is at y 194-216, so the chip sits 5 px over the blue bar (34 px wide), and the first row shows only one label: "Miami-Dade | 55.4%" (43.9% not shown), "Harris | 46.4%" (52.0% not shown), "Miami city | 48.7%" (50.0%), while rows 2-3 show both labels. Same in the Florida and Texas county lists and the Miami-Dade and Harris County city lists (measured). The Michigan state senate list without the time row looks the same in the screenshot (chip over row 37's blue bar; not measured).
- Screenshots: shots/b1610p31-ch-390-chip-Florida-Miami-Dade.png, shots/b1610p31-ch-390-chip-Texas-Harris.png, shots/b1610p31-ch-390x844-st-Michigan-senate-list-num.png
- Data: `qa/b1610p31-chip-chromium-390.json` (`chip`, `rows[0].hit`); script `qa/p31-chip.py`

### QA-100 [HIGH, may be CRITICAL] New York county rows add up to exactly 100% (no other candidates), so Kings County and Brooklyn borough show different numbers
- Severity: HIGH (the same area shows two results ~1.4 points apart; may count as wrong numbers) | Build 1610 | Chromium 390x844, touch
- Steps: "New York" + Enter > geo button > "New York counties"; then Kings > the Brooklyn borough row.
- Expected: one result for Brooklyn (Kings County = Brooklyn borough), others included as everywhere else.
- Actual: the county rows each sum to 100.0%: Kings 28.0% / 72.0%, Suffolk 55.0% / 45.0%, Nassau 52.1% / 47.9%, Queens 37.7% / 62.3%; the Kings County map / reload thumbnails Harris 72% / Trump 28%. One level down, "Brooklyn borough | 27.3% | 70.6%" (others ~2%), and its precinct list header Harris 71% / Trump 27%. The NY county rows look two-party only. Data lane to check against the NY BOE county results.
- Screenshots: shots/b1610p31-ch-390x844-st-NewYork-drill-Kings.png, shots/b1610p31-ch-390x844-st-NewYork-drill-reload.png
- Data: `qa/b1610p31-states-chromium-390x844-b.json` > `New York.drill` (`rows1`, `rows2`, `th3`, `reload.th`)

### QA-101 [LOW] New York 2024 map: Trump 44% (FEC 43.3%), the state total is 0.78% below FEC
- Severity: LOW (gap under 0.5 points) | Build 1610 | Chromium 390x844
- Steps: "New York" + Enter (map, 2024).
- Expected: Harris 56% / Trump 43% (FEC 55.91% / 43.31%).
- Actual: Harris 56% / **Trump 44%**. `__stTot('New York','2024')` = Harris 4,619,195 and Trump 3,578,899 (both exact) but total 8,198,094 vs FEC 8,262,495 (-64,401), so Trump's share is 43.66%. Texas, Florida, Michigan, Arizona totals are within 0.08% and all 2016 / 2020 / 2024 thumbnails for TX, FL, NY '16/'20, MI, AZ match FEC.
- Data: `qa/b1610p31-states-chromium-390x844-b.json` > `New York.tot`, `thumbs_by_year`; `qa/fec24.json`

### QA-102 [MEDIUM] Tap-to-paint over 100 ms: "Texas counties" from the geo menu and city precinct drill-ins
- Severity: MEDIUM (instant-response rule; QA-007 family) | Build 1610 | Chromium 390x844, touch
- Steps: Texas + Enter > geo button > "Texas counties"; a county > its first city.
- Actual (tap > next paint): "Texas counties" **131 and 150 ms** (Florida 56, New York 60, Arizona 51); Houston city precincts (636 rows) **108 ms** (327 ms in the first run), Miami city (123 rows) **106 ms**, Brooklyn borough (1,306 rows) **106 ms** (Phoenix city 38 ms). Picking School districts: New York 169 ms, Michigan 132 ms (QA-073 family, added there).
- Data: `qa/b1610p31-states-chromium-390x844-b.json` > `<state>.drill.lat_counties`, `lat_sub`, `types.schools.lat`

## Re-test status, builds 1608 / 1609 (pass 30, live line 9 = 202610181608 at start ~7:00 AM, 202610181609 from ~7:08-7:09 AM; Oct 19 ~6:58-7:45 AM EDT)
- Builds since pass 29: **1608** (`cbc5777`, QA-020 Back rows) and, during this pass, **1609** (`35b9e7d`, QA-090 scroll once after the list settles; QA-091 saved map position after the search is DC). Runs before ~7:08 AM read `window.BUILD` = 202610181608 (QA-020 back2 runs, WebKit address runs); every run from 7:09 AM read 202610181609 (Chromium address run, QA-085, layout sweep, verify list, smoke flow, older-bug checks, globe probe, WebKit address and Back re-runs). Data and shots are prefixed with the build they ran on (`b1608p30-*` / `b1609p30-*`). One engine at a time, touch on. No console errors, page errors or failed requests in any pass-30 run. No v3 yet (https://ge0r9b.github.io/us-districts/v3/ 404; no v3 link in HANDOFF.md on origin/main `35b9e7d`).
- **QA-020 fixed on 1608 (verified pass 30):** Back from Los Angeles County cities to the CA counties, touch (tap > first frame / first list DOM change / CA rows on screen): WebKit 390 50 / 50 / 50 and 22 / 48 / 52 ms; WebKit 1024x768 20 / 55 / 60 and 53 / 53 / 53 ms; Chromium 390 2 / 35 / 41 and 11 / 39 / 52 ms. Second Back (CA counties > All States) rows: WebKit 390 51 and 67 ms, WebKit 1024x768 79 and 58 ms, Chromium 390 46 and 53 ms (pass 29: 141-450 ms). Re-run on 1609 (WebKit 390, 1 rep): Back 60 ms, second Back 58 ms. All under 100 ms. Drill-ins still correct (CA > 58 counties starting Los Angeles, LA > cities starting Los Angeles city); first frame 0-43 ms, rows 14-627 ms (first visit slowest, as before). The hidden map's heat reaches the 58 counties at 768-1063 ms; in 1 of 2 reps per size it first passes through the 24202-shape statewide layer (1313-1689 ms), now built when idle after the rows (per the 1603 code note), not seen by the user in the list view. After Back > Back to All States, the globe button shows the US map at 39.775, -98.613 zoom 4, title "United States", thumbnails Trump 50% / Harris 48%, state heat drawn (WebKit 390 and 1024x768, Chromium 390, both engines on 1609). Shots: shots/b1608p30-{we,ch}-*-back2-us-map.png. Data: `qa/b1608p30-back2-{webkit,chromium}.json`, `qa/b1609p30-back2-webkit.json`, `qa/b1609p30-globe-{chromium,webkit}-390.json` (`backback`).
- **New: QA-092 [MEDIUM]** (All States list > globe: the map opens at zoom 2, the US small in a hemisphere view) and **QA-093 [CRITICAL, ruled by the orchestrator Oct 19 7:46 AM EDT]** (a DC row picked in All States, by tap or address search, then the globe: the map shows DC's outline and precincts and the bottom field says "District of Columbia", but the title is "United States" over the US numbers). Details below.
- **QA-090 not seen on 1608 or 1609; 1609 fix verified (pass 30):** "1600 Pennsylvania Ave NW, Washington, DC 20500" + Enter, `#listView.scrollTop` every frame. 1608 WebKit 390x844: All States 0 > 882 at 769 and 737 ms; PA > Philadelphia 0 > 882 at 985, 973 and 983 ms: one scroll, no return to the top (5/5; pass 29: 7/11 jumped). 1609 Chromium 390x844: All States 745 ms, Philadelphia 829 ms; 1609 WebKit 390x844: Philadelphia 1111 and 1036 ms, All States 817 ms: one scroll each (5/5). End state every time: header "All States", DC row "DC | 90.3%" selected (`lasel`) on screen inside the list (y 710-740, scrollTop 882), thumbnails Harris 90% / Trump 6%; no chrome moved (transient empty). From the map: DC, popup Harris 90.3% / Trump 6.5%, zoom 15. Data: `qa/b1608p30-addr-webkit-390x844{,-rep}.json`, `qa/b1609p30-addr-chromium-390x844.json`, `qa/b1609p30-addr-webkit-390x844-b1609.json`, script `qa/p30-addr.py`.
- **QA-091 still open on 1608, fixed on 1609 (verified pass 30):** WebKit 390x844, PA > Philadelphia townships > the DC address. 1608 (3/3 runs): saved `ll` 39.8, -98.6, zoom 4 (the US view; no longer Minnesota zoom 2), the globe opens the map there and a reload restores it; the All States path saved DC 38.8926, -77.0145, zoom 11. 1609 (2/2 Philadelphia, 1/1 All States): saved `ll` 38.8987, -77.0352, zoom 15 (DC), the map opens there and a reload keeps it. Chromium 1609: the same DC position on both paths. Shots: shots/b1608p30-we-390x844-addr-phila*-tomap.png, shots/b1609p30-we-390x844-addr-phila-r?-tomap.png.
- **QA-085 still borderline (1609, Chromium 1024x576):** PA year taps '16 > '24 > '20 > '24 x3 (12 taps, min / median / max, tap > next paint): state house 87 / 105 / 156 ms (9 of 12 over 100; pass 29: medians 116 and 113), state senate 26 / 62 / 137 (3/12), PA county map 22 / 90 / 127 (4/12). Picking State house took 101 ms, State senate 56. Only the state house median is over 100. Shot: shots/b1609p30-ch-1024x576-ylat-PA-statehouse.png. Data: `qa/b1609p30-ylat-chromium-1024x576.json`.
- **QA-007 (All States row tap), smoke flow 1609:** 94 ms at 390, 82 at 375, 74 at 320, **103 at 1024x576, 103 at 1024x768** (pass 29: 101 at 1024x768 only). Still just over 100 ms on the iPad sizes. The verify-list run measured 85 ms at 390.
- **Older open bugs, quick status (Chromium 390x844 unless noted, 1609):** QA-018 still open (OH row tapped at 55% of its width, on the bar `I.sg rep`: stays on All States). QA-006 still fixed (Philadelphia County townships list has 1 row, "Philadelphia city | 20.0% | 78.5%", no Rockledge). QA-015 essentially fixed: PA > Philadelphia list `ll` 40.0029, -75.118, z10 before reload, 40.0027, -75.118, z10 after, `lt` kept. QA-067 / QA-088 hold (Chromium 375x667: "America" and "USA" list only United States; the other 10 queries unchanged). QA-073 still over 100 ms: School districts tap-to-next-paint California 150 ms, Texas 229, Pennsylvania 109, Ohio 113 (1582: 1-4 s). QA-074 still open: California 974 rows with repeated names (Eureka City Unified, Healdsburg Unified, Santa Barbara Unified, Caruthers Unified, Hope Elementary, ...), Ohio 611 rows (Eastern, Buckeye, Crestview, Green, Madison Local, ...), no county labels. QA-005, QA-064, QA-072 not re-run (fixed in earlier passes; the smoke flow's US House step and the verify list's DC "At-large" row cover parts). Shots: shots/b1609p30-ch-390-018-OHbar.png, shots/b1609p30-ch-390-schools-{California,Ohio}.png, shots/b1609p30-ch-375x667-inst-*.png. Data: `qa/b1609p30-other-chromium-390.json`, `qa/b1609p30-067.json`, scripts `qa/p30-other.py`, `qa/p30-067.py`.
- **Orchestrator verify list holds (1609):** Chromium 390 own-check identical to pass 29 field for field ('16 colours: CA, NY, IL, CO, VA blue; FL, PA, MI, WI near-white red tint as before, script flag "?"; PA rows number only "1", "4", "17" and "10", "12"; DE "At-large", DC "At-large 90.3%"; thumbnails on the icon axis in all views), `qa/b1609p30-own-chromium-iphone390.json`. PA '16 bar 48.2 / 47.5 / 4.4, pie 48.2 / 47.5; '24 50.4 / 48.7 / 1.0, pie 50.4 / 48.7; '16 again the same (WebKit 390, `qa/b1609p30-pa16-webkit-390x844.json`). Sort-chip 60-check harness (`p30-v95.py`, Chromium 390): chip shown in 60/60 checks at x 288-322 (y 111-133, or 177-199 with the time row open, as on 1604), over no row's bars or labels; names at x 52-77, bars from x 83; one bar scale per list (spread 1.007-1.037); CLS over the run 0.354 (1604: 0.360), `qa/b1609p30-v-chromium-iphone390.json`. Menus overlay with nothing dimmed or shrunk (pie box 52,114-324,386 phone and 210,114-800,704 iPad, backdrop transparent, open in 12-19 ms; WebKit 390x844 and 1024x768, US and Alabama), `qa/b1609p30-menus-webkit-iphone390_ipad1024x768.json`.
- **Layout sweep (16 steps, 1609), WebKit 390 and Chromium 1024x768:** nothing moved on any year change, drill-in or Back except the expected ones (map thumbnails +68 px when the time row opens, first row 30 > 44 px for split bar, chart button hidden with the type row open, back chevron appears/goes). Chromium 1024x768 step 2 crumbs transient the same as 1606/1607 (not new). Data: `qa/b1609p30-layout3-{webkit-390,chromium-1024x768}.json`, shots shots/b1609p30-{we,ch}-*-ls3??-*.png.
- **Smoke flow, Chromium, all 5 sizes, touch (1609):** every recorded field (rows, sort, # mode, 2020, range, chart options, PA / Philadelphia / townships, Back, US House rows, restore, address suggestions) identical to pass 29 at all 5 sizes; no overlaps, clipping or off-screen elements; CLS 0 everywhere; reload restores PA > Philadelphia County list, bar, #, 2024. Taps over 100 ms: only the All States row at 1024x576 and 1024x768 (103 ms, QA-007); all others under 95 ms. Data: `qa/b1609p30-flow-chromium-.json`, shots shots/b1609p30-ch-*.png.
- Skipped (time): WebKit smoke flow, layout sweep at 375 / 320 / 1024x576, QA-085 at 390x844, QA-005 / QA-064 / QA-072 direct re-runs.

### QA-092 [Fixed on 1611 (verified pass 32)] [MEDIUM] All States list > globe: the map opens at zoom 2, with the US small in a hemisphere view
- Severity: MEDIUM (wrong map position; numbers right) | Build 1609 | Chromium and WebKit 390x844, touch
- Steps: fresh load > geo button > All States (list) > globe button (list > map).
- Expected: the US map at its usual view (as after Back > Back to All States: 39.775, -98.613, zoom 4).
- Actual: the map opens at 48.225, -94.219, **zoom 2** (most of the Americas, Greenland to Argentina, the US small in the middle), title "United States", thumbnails Trump 50% / Harris 48%. Toggling the globe again keeps zoom 2. While the All States list is up the hidden map sits at 48.275, -94.192, zoom 2 (the same spot pass 29 saw saved in QA-091). After drilling into a state and Back > Back to All States the map opens at zoom 4 as expected. Not checked on 1607/1608.
- Screenshots: shots/b1609p30-ch-390-globe-fresh-1.png, shots/b1609p30-we-390-globe-fresh-1.png (compare shots/b1609p30-ch-390-globe-backback-1.png)
- Data: `qa/b1609p30-globe-{chromium,webkit}-390.json` > `fresh` (`globe1`..`globe4`, `ll`); script `qa/p30-globe.py`

### QA-093 [Fixed on 1611 (verified pass 32); reload variant is QA-103] [CRITICAL (orchestrator ruling, Oct 19 7:46 AM EDT)] A DC row picked in All States: on switching to the map, DC is drawn but the title and numbers are the US's
- Severity: HIGH (mixed screen: the map and bottom field are DC, the title and thumbnails the US; like QA-087 the other way round, so it may count as wrong numbers) | Build 1609 (also on 1608 for the address path) | Chromium and WebKit 390x844, touch
- Steps: geo button > All States > tap the DC row (or type "1600 Pennsylvania Ave NW, Washington, DC 20500" + Enter) > globe button (list > map).
- Expected: the map shows DC as picked (title "District of Columbia", DC numbers Harris 90% / Trump 6%), as the address search from the map does.
- Actual: the map is zoomed on DC (tap: 38.893, -77.014, zoom 11; address: 38.899, -77.035, zoom 15) with DC's white outline and its precinct heat, and the bottom field reads "District of Columbia", but the title is "United States" and the thumbnails show the US numbers (Trump 50% / Harris 48%); no popup. In the list just before, the thumbnails were DC's (Harris 90% / Trump 6%). Same in both engines, tap and address.
- Screenshots: shots/b1609p30-ch-390-globe-tapdc-1.png, shots/b1609p30-ch-390-globe-addr-1.png, shots/b1609p30-we-390-globe-tapdc-1.png
- Data: `qa/b1609p30-globe-{chromium,webkit}-390.json` > `tapdc`, `addr`; `qa/b1608p30-addr-webkit-390x844.json` > `st_map`

## Re-test status, build 1607 (pass 29, live line 9 = 202610181607 at start ~5:56 AM and end ~6:28 AM; Oct 19 ~5:56-6:40 AM EDT)
- Build since pass 28: **1607** (`101924c`, after a DC address search from a list view the selected DC row is scrolled into view). Every pass-29 run read `window.BUILD` = 202610181607 (the smoke-flow JSON does not store it; live line 9 read 1607 before and after that run). One browser engine at a time, touch on. No console errors, page errors or failed requests in any pass-29 run. No v3 preview or live URL yet (no v3 link in HANDOFF.md on origin/main at `101924c`; https://ge0r9b.github.io/us-districts/v3/ returns 404).
- **New: QA-090 [HIGH (layout jump rule)]**: the 1607 scroll lands, but in 7 of 11 list-view runs the list jumps to the DC row, back to the top (CA) for 56-316 ms, then to DC again; in 1 of 11 (WebKit 390, from PA > Philadelphia) it ends at the top with DC off screen. Details below.
- **1607 change (DC row scrolled into view) mostly works:** "1600 Pennsylvania Ave NW, Washington, DC 20500" + Enter from the All States list and from PA > Philadelphia townships, WebKit 390x844 (5 runs) and 375x667, Chromium 390x844 and 375x667. End state in 10 of 11 runs: header "All States", 51 rows, thumbnails Harris 90% / Trump 6%, bottom field placeholder "District of Columbia", DC row "DC | 90.3%" selected (`lvrow la lasel cmp`) and fully on screen inside the list (390: y 710-740, list 106-782, scrollTop 882; 375: y 533-563, list 106-605, scrollTop 1059; `elementFromPoint` hits the row). The tap-DC result in All States is the same except the scroll: tapping DC leaves the list at scrollTop 0 with the DC row at y 1592 (off screen), so only the scroll differs, as intended. Thumbnails, top fields, right buttons, slider and bottom bar did not move in any frame during the address search (per-frame boxes, `transient` empty in every run, CLS 0). The sort chip appears on the phila path (Philadelphia townships list has none). From the map it still goes to DC (title "District of Columbia", popup Harris 90.3% / Trump 6.5%, zoom 15), WebKit and Chromium 390, 375. Shots: shots/b1607p29-{we,ch}-{390x844,375x667}-addr-{tapdc,allstates,phila,map}.png, shots/b1607p29-we-390x844-addr-{phila,allstates}-r?.png. Data: `qa/b1607p29-addr-webkit-390x844.json`, `qa/b1607p29-addr-webkit-390x844-rep.json`, `qa/b1607p29-addr-webkit-375x667.json`, `qa/b1607p29-addr-chromium-390x844_375x667.json` (`scroll_changes` per frame), script `qa/p29-addr.py`.
- **Back chevron after the address search from PA > Philadelphia (note, not filed):** in both engines the All States screen reached by the address search from the Philadelphia townships list keeps a back chevron at the top left (shots/b1607p29-ch-390x844-addr-phila.png, shots/b1607p29-we-390x844-addr-phila-r0.png); the same search from All States, and tapping DC in All States, show none. It was already in the pass-28 WebKit shot (shots/b1605p28-we-390-addr-phila.png), so pass 28's "no stray back chevron" was wrong for that path. It is the normal Back button (`#bBack`, aria "Back"); tapping it returns to the Philadelphia County townships list (thumbnails Harris 79% / Trump 20%, row "Philadelphia city | 20.0% | 78.5%"), so it works as "back to before the search". Probably by design; listed so the orchestrator can confirm. Shots: shots/b1607p29-ch-390-chev-addr_phila.png, shots/b1607p29-ch-390-chev-addr_phila-tapped.png. Data: `qa/b1607p29-chev-chromium-390.json`, script `qa/p29-chev.py`. (Also: on WebKit the phila path saves map position 48.275, -94.1922, zoom 2 instead of DC's 38.8926, -77.0145, zoom 11 as in Chromium and the All States path; the list view hides the map, so not checked further.)
- **QA-020 still open (1607, unchanged from 1606):** Back from Los Angeles County cities to the CA counties, touch, 2 reps (tap > first frame / first list DOM change / CA rows on screen): WebKit 390 51 / 169 / 173 and 44 / 165 / 179 ms; WebKit 1024x768 52 / 267 / 305 and 47 / 185 / 188 ms; Chromium 390 9 / 134 / 141 and 12 / 188 / 209 ms. Second Back (CA counties > All States) rows: WebKit 390 430 and 450 ms, WebKit 1024x768 306 and 263 ms, Chromium 390 218 and 297 ms. Drill-ins: first frame 1-31 ms, rows 13-1155 ms (first visit slowest). Data: `qa/b1607p29-back2-{webkit,chromium}.json`.
- **QA-085 Chromium PA county map at 1024x576 (1607):** year taps '16 > '24 > '20 > '24 x3 (12 taps, min / median / max, tap > next paint), run 1: PA county map 56 / 88 / 177 ms (4 of 12 over 100; pass 28: median 129, 10/12), state house 25 / 116 / 296 (10/12; pass 28: 88, 2/12), state senate 35 / 84 / 129 (5/12; pass 28: 60, 2/12). Run 2 (same build, minutes later): PA county map 24 / 96 / 158 (5/12), state house 44 / 113 / 152 (8/12), senate 34 / 59 / 151 (4/12). The numbers swing a lot between runs with no code change in this area, so the 1024x576 Chromium year taps stay open as a borderline item (medians 59-116 ms; the county map's median is now under 100 in both runs, the state house's over 100 in both). Shot: shots/b1607p29-ch-1024x576-ylat-PA-statehouse.png. Data: `qa/b1607p29-ylat-chromium-1024x576-run1.json`, `qa/b1607p29-ylat-chromium-1024x576-run2.json`.
- **QA-007 (All States row tap), smoke flow 1607:** 83 ms at 390, 75 at 375, 77 at 320, 96 at 1024x576, **101 ms at 1024x768** (pass 28: 101 at 375, 107 at 1024x576, 110 at 1024x768). Only 1024x768 is still just over 100 ms.
- **Orchestrator verify list holds (1607):** '16 colours, PA '16 county labels and colours, PA US House and senate rows (number only: "1", "4", "17"; "10", "12"), DE "At-large", DC "At-large 90.3%", US House rows, and thumbnails on the icon axis (x 27) in all checked views: identical to pass 28, field for field (Chromium 390, `qa/b1607p29-own-chromium-iphone390.json`). US '16 House map labels Clinton 48% / Trump 46%; FL, PA, MI, WI near-white red tint as before (Trump's narrow wins, script flag "?", not a bug). PA '16 bar 48.2 / 47.5 / 4.4, pie 48.2 / 47.5, '24 bar 50.4 / 48.7 / 1.0, pie 50.4 / 48.7, '16 again the same (WebKit 390, `qa/b1607p29-pa16-webkit-390x844.json`). Menus overlay with nothing dimmed or shrunk (pie box 52,114-324,386 phone and 210,114-800,704 iPad unchanged, backdrop transparent, open in 12-19 ms; WebKit 390x844 and 1024x768, US and Alabama; `qa/b1607p29-menus-webkit-iphone390_ipad1024x768.json`). Sort chip: held its place (no move) through every layout-sweep step; the 60-check sort-chip overlap harness (`p28-v95.py`) was not re-run this pass (time).
- **Layout sweep (16 steps, 1607), WebKit 390 and Chromium 1024x768:** nothing moved on any year change, drill-in or Back except the expected ones (map thumbnails +68 px when the time row opens, first row 30 > 44 px for split bar, chart button hidden with the type row open, back chevron appears/goes). Chromium 1024x768 step 2 (geo menu > All States): the crumbs row sits at y 3 for ~1.5 s while the menu is open, the same as on 1606 (`qa/b1606p28-layout3-chromium-1024x768.json`), not new. Data: `qa/b1607p29-layout3-{webkit-390,chromium-1024x768}.json`, shots shots/b1607p29-{we,ch}-*-ls3??-*.png.
- **Smoke flow, Chromium, all 5 sizes, touch (1607):** same numbers and rows as pass 28 (CA 38.3 / 58.5; Philadelphia 569K), no overlaps, clipping or off-screen elements, CLS 0 at every size, reload restores PA > Philadelphia County list, bar, #, 2024; the address step ends on DC. Taps over 100 ms: only the All States row at 1024x768 (101 ms, QA-007); all others 7-81 ms. Data: `qa/b1607p29-flow-chromium-.json`, shots shots/b1607p29-ch-*.png.
- Skipped (time): WebKit smoke flow, sort-chip 60-check harness (`p28-v95.py`), layout sweep at 375, 320 and Chromium 1024x576, QA-085 at 390x844, v3 smoke (no v3 URL).

### QA-090 [Fixed on 1609 (verified pass 30); also not seen on 1608] [HIGH (layout jump rule)] DC address search from a list view: the list jumps to the DC row, back to the top, then to DC again; once (WebKit, from Philadelphia) it stays at the top
- Severity: HIGH by the layout-jump rule (the whole list jumps 882-1059 px twice in a few hundred ms; numbers are right) | Build 1607 | WebKit 390x844 and 375x667, Chromium 390x844 and 375x667 (touch)
- Steps: fresh load > geo button > All States (or then PA > Philadelphia townships) > tap the bottom field > type "1600 Pennsylvania Ave NW, Washington, DC 20500" > Enter. Record `#listView.scrollTop` every frame.
- Expected: one scroll to the DC row (the 1607 change), then it stays.
- Actual (time after Enter, scrollTop): All States, Chromium 390: 746 ms 882 (DC) > 934 ms 0 (top) > 1063 ms 882; Chromium 375: 726 ms 1059 > 812 ms 0 > 1042 ms 1059; WebKit 390: 893 ms 882 > 930 ms 0 > 1161 ms 882, and 885 > 917 > 1233 ms; WebKit 375: 920 > 985 > 1249 ms. Philadelphia path, Chromium 390: 739 > 748 > 1047 ms; Chromium 375: 736 > 997 > 1053 ms. So the top of the list (CA, TX, ...) shows for 56-316 ms between two DC frames in 7 of 11 runs. WebKit from Philadelphia scrolled once and stayed in 3 runs (390 r0 at 919 ms, r1 at 916 ms, 375 at 1017 ms), but in the first WebKit 390 run it went to 882 at 1267 ms and **back to 0 at 1599 ms and stayed there**: end state DC row off screen, the thing 1607 was meant to fix. Thumbnails, top fields, right buttons and bottom bar did not move in any frame.
- Likely: the list is rendered a second time after the scroll (scrollTop reset to 0), and the scroll is re-applied only if it runs after that render.
- Screenshots: shots/b1607p29-we-390x844-addr-phila.png (end state at the top, DC off screen), shots/b1607p29-we-390x844-addr-phila-r0.png (DC on screen), shots/b1607p29-ch-390x844-addr-allstates.png. The jump itself is in the per-frame data.
- Data: `qa/b1607p29-addr-*.json` > `<size>-<path>` > `scroll_changes` ([ms, scrollTop]) and `dc`; script `qa/p29-addr.py`.

## Re-test status, builds 1605 / 1606 (pass 28, live line 9 = 202610181605 at start, 202610181606 from ~5:15 AM; Oct 19 ~4:50-5:35 AM EDT)
- Builds since pass 27: **1605** (`d225ecc`, QA-087 DC address from a list view, WebKit fields released, QA-085 Chromium county heat) and **1606** (`2d1ae5d`, QA-089, QA-088, QA-020). Each item names the build its runs read from `window.BUILD`. One browser engine at a time. No console errors, page errors or failed requests in any pass-28 run. No v3 preview or live URL yet.
- **QA-087 fixed (1605, holds on 1606):** "1600 Pennsylvania Ave NW, Washington, DC 20500" + Enter from the All States list and from PA > Philadelphia townships now ends exactly as tapping the DC row in All States: header "All States", the 51 state rows, thumbnails Harris 90% / Trump 6%, bottom field "District of Columbia", DC row selected (`lasel`), no stray back chevron. The tap-DC and address results match field for field (`qa/b1605p28-dc-chromium-390.json`). WebKit 390 now takes the typed address in list views (the bottom field is no longer stuck), same result. From the map it still goes to DC (popup Harris 90.3% / Trump 6.5%, zoom 15). Small note, not filed: the selected DC row stays where it is in the list (y 1592 at 390, off screen) after an address search; the thumbnails and field show DC. Shots: shots/b1605p28-ch-390-addr-phila.png, shots/b1605p28-we-390-addr-phila.png, shots/b1605p28-ch-390-dc-tapdc.png, shots/b1605p28-ch-390-dc-addr.png. Data: `qa/b1605p28-addr-{chromium,webkit}-390.json`, `qa/b1606p28-addr-chromium-390.json`, script `qa/p28-addr.py`, `qa/p28-dc.py`.
- **QA-088 fixed (1606):** "USA" lists COUNTRY "United States" only (WebKit 390x844, Chromium 375x667, real taps and typing). The other 11 queries are unchanged from 1604/1605 (America, Afrika, Penn, Ohio, Pensylvania, Philadelphia, Calif, uk, Allegheny, Georgia, Amelia). On 1605 "USA" still listed Colusa County. Data: `qa/b1606p28-067.json` (vs `qa/b1605p28-067.json`).
- **QA-089 fixed (1606):** layout sweep, WebKit 390 and Chromium 1024x768: the list thumbnails no longer move on drill-in from All States (step 3) or on Back to All States (step 15); only the back chevron appears and goes. Still on 1605 (dy +30 / -30, WebKit 390, Chromium 1024x768 and 1024x576). Data: `qa/b1606p28-layout3-{webkit-390,chromium-1024x768}.json` vs `qa/b1605p28-layout3-*.json`.
- **QA-020 much better on 1606, still just over 100 ms:** Back from Los Angeles County cities to the CA counties (touch, tap > first frame / first list DOM change / CA rows on screen): WebKit 390 43-45 / 163-169 / 167-187 ms, WebKit 1024x768 39-51 / 164-192 / 167-198 ms, Chromium 390 5-16 / 130-171 / 158-183 ms (1605: 558-787 ms; 1604: 400-760). The 24202-feature statewide layer is gone; the 58-county heat follows at 566-796 ms. Second Back (CA counties > All States): rows 275-411 ms WebKit 390, 142-162 ms WebKit 1024x768, 275-318 ms Chromium 390. First-visit drill-ins: first frame 0-33 ms, rows 165-737 ms. Data: `qa/b1606p28-back2-{webkit,chromium}.json`, `qa/b1605p28-back2-*.json`.
- **QA-085 Chromium mostly fixed (1605):** PA year taps (12 per map, min / median / max, tap > next paint): 1024x576 state house 28 / 88 / 110 ms (2 of 12 over 100), senate 30 / 60 / 113 (2/12), **PA county map 23 / 129 / 193 (10/12, still slow)**; 390x844 state house 29 / 64 / 92 (0/12), senate 26 / 51 / 106 (1/12), county map 20 / 78 / 106 (3/12). 1604 medians were 124-173. The district maps now pass; the plain county map at 1024x576 is what remains. Shot: shots/b1605p28-ch-1024x576-ylat-PA-statehouse.png. Data: `qa/b1605p28-ylat-chromium-{1024x576,390x844}.json`.
- **Orchestrator verify list holds (1605/1606):** '16 colours, PA US House / senate / state house maps, thumbnail axis, rows number-only with "At-large" labels, sort chip (Chromium 390, 1606): identical to pass 27. PA '16 bar 48.2 / 47.5 / 4.4 and pie 48.2 / 47.5, '24 50.4 / 48.7 (WebKit 390, 1606). Menus overlay with no dimming or shrinking (WebKit 390x844 and 1024x768, 1605): unchanged. Data: `qa/b1605p28-own-chromium-iphone390.json`, `qa/b1605p28-pa16-webkit-390x844.json`, `qa/b1605p28-menus-webkit-iphone390_ipad1024x768.json`.
- **Layout sweep (16 steps):** on 1605 the same as 1604 (only QA-089); on 1606 nothing moves on any year change, drill-in or Back except the expected ones (map thumbnails +68 px when the time row opens, rows 30 > 44 px for split bar, chart button hidden with the type row open).
- **Smoke flow, Chromium, all 5 sizes, touch (1605):** same numbers and rows as pass 27, no overlaps, clipping or off-screen elements, reload restores PA > Philadelphia County list, bar, #, 2024. The address step now ends on DC (field "District of Columbia"). Taps over 100 ms: only the All States row (QA-007), 101 ms at 375, 107 at 1024x576, 110 at 1024x768 (91-99 at 390 and 320); all others 8-74 ms. **Watch item gone:** the tiny periodic layout shifts after the # tap no longer show (CLS 0 at 390, 375, 320, 1024x768; one 0.0043 shift at 1024x576). Data: `qa/b1605p28-flow-chromium-.json`.
- Not re-run on 1606: smoke flow (ran on 1605), WebKit year taps (fixed on 1599).

## Re-test status, build 1604 (pass 27, live line 9 = 202610181604 at start and end; Oct 19 ~2:51-4:15 AM EDT)
- Builds since pass 26: **1603** (`e9a932d`, QA-020: list-view Back/drill paints the list first, map heat two frames later) and **1604** (`5850c12`, QA-067: a synonym hit drops typo look-alikes). Every pass-27 run read `window.BUILD` = 202610181604 (live), except the local A/B runs marked 1602. Most runs are from the 2:51-3:42 AM run (it crashed before writing this section); added at 3:56-4:08 AM: Chromium live Back timing and the address probe (`qa/p27-addr.py`). One browser engine at a time; no runs killed. No console errors, page errors or failed requests in any pass-27 run. No v3 preview or live URL yet.
- **New: QA-087 [CRITICAL]** (address search from a list view titles the screen "District of Columbia" over the national All States list and US totals), **QA-088 [LOW]** ("USA" still lists Colusa County, CA), **QA-089 [HIGH, layout jump, long-standing]** (list thumbnails drop 30 px on every drill-in from All States and rise 30 px on Back). Details below.
- **QA-067 fixed for "America" (1604):** real taps and typing in the institution field, WebKit 390x844, Chromium 375x667, WebKit 1024x768: "America" lists COUNTRY "United States" only (no South Africa, no Amelia County). Other queries look right and are the same in all 3 runs: "Afrika" Central African Republic, South Africa; "uk" United Kingdom, Ukraine; "Penn" Pennsylvania, then Pennington County SD/MN and the PA counties; "Pensylvania" (typo) Pennsylvania + PA counties; "Ohio" Ohio + Ohio County WV/KY/IN + OH counties; "Calif" California + CA counties; "Georgia" the state + GA counties; "Philadelphia", "Allegheny", "Amelia" only their own county. One leftover of the same kind: QA-088 ("USA"). Shots: shots/b1604p27-ch-375x667-inst-America.png, shots/b1604p27-we-390x844-inst-America.png, shots/b1604p27-we-1024x768-inst-America.png. Data: `qa/b1604p27-067.json`, script `qa/p27-067.py`.
- **QA-020 still open (1604): the first frame is fast now, but the new rows still take 400-760 ms.** Back from the Los Angeles County cities to the California counties, touch, per tap (tap > first frame / first list DOM change / CA county rows on screen):
  - WebKit live 390: 41-43 / 387-491 / 399-515 ms; 320: 40-53 / 395-440 / 413-462 ms; 1024x768: 43-59 / 477-481 / 489-497 ms. Older harness (`qa/p27-back.py`, tap > next paint): 41-53 ms at all 5 sizes; rows at 381-536 ms at 390, 320, 1024x576 and 1024x768, but at **1001 and 1393 ms at 375x667** (there the rows and the county heat arrive in the same frame). On local 1602 the same WebKit tap was 366 ms first frame and 1374 ms to the rows, so 1603 cut WebKit roughly in half.
  - Chromium live 390: 3-5 / 608-634 / 622-646 ms; 1024x768: 1 / 656-727 / 677-761 ms (local 1602 at 390: rows at 654 ms, so no change in Chromium).
  - Until then the old cities list stays up with no change (longest frame gap 358-875 ms; up to 1332 ms at WebKit 1024x768). The map heat does not come "two frames later": in every run, Chromium and WebKit, 1602 and 1604, the heat layer first jumps from 3087 to **24202** features and only reaches the 58 counties 570-2180 ms after the tap. In Chromium the 24202 layer shows up (466-496 ms) before the list rows change (622-761 ms), so the list is not painted first there. Probably the cause: something builds a 24202-feature statewide layer on Back before the county one.
  - Second Back (CA counties > All States): rows at 157-503 ms WebKit, 184-268 ms Chromium. Drill-ins CA and Los Angeles: first frame 3-33 ms, rows 14-1066 ms (first visit slowest).
  - Data: `qa/b1604p27-back2-webkit-live.json`, `qa/b1604p27-back2-chromium-live.json`, `qa/b1604p27-back-webkit.json`, local A/B `qa/b1602p27-back2-{chromium,webkit-local}.json` vs `qa/b1604p27-back2-{chromium,webkit}-local390.json`; logs `qa/p27-back*.log`. Shots: shots/b1604p27-we-*-back-rep*.png, shots/b1604p27-we-*-map-after-back.png (map heat after Back matches the first CA visit: same colours, signature aca8426749, all sizes).
- **QA-085 still open in Chromium (1604, no change vs 1601):** PA year taps '16 > '24 > '20 > '24 x3 (12 taps, min / median / max, tap > next paint): 1024x576 state house 95 / 173 / 225 ms (11 of 12 over 100), state senate 109 / 170 / 229 (12/12), PA county map 83 / 167 / 180 (11/12); 390x844 state house 88 / 134 / 209 (10/12), senate 27 / 124 / 225 (9/12), county map 14 / 98 / 147 (6/12). Pass 26 on 1601: 1024x576 state house median 188, senate 172; 390 state house 142. WebKit not re-measured (fixed on 1599). Shot: shots/b1604p27-ch-1024x576-ylat-PA-statehouse.png. Data: `qa/b1604p27-ylat-chromium-{1024x576,390x844}.json`, script `qa/p27-ylat.py`.
- **Orchestrator verify list holds (1604):**
  - '16 colours (Chromium 390): US House map 27.2% blue / 72.8% red at '16 (labels Clinton 48% / Trump 46%); PA county map 26.3% blue, PA US House 26.8%, senate 25.1%, state house 24.0% (labels Trump 48% / Clinton 47%). Philadelphia and Pittsburgh D, rural PA and Lancaster R in every map. US '16 states: CA, NY, IL, CO, VA, WA blue; TX, OH, KS red; FL, PA, MI, WI near-white with a red tint (e.g. MI 247,245,245), which fits Trump's 0.2-1.2 pt wins there (my script flags them as "?", not a bug). PA '16 counties: Philadelphia, Allegheny, Lackawanna D; Lancaster, Westmoreland, Erie, Clearfield R. Data: `qa/b1604p27-col16-chromium-iphone390.json`, `qa/b1604p27-own-chromium-iphone390.json`.
  - PA '16 bar 48.2 / 47.5 / Other 4.4 and pie 48.2 / 47.5 (WebKit 390); '24 bar 50.4 / 48.7 / 1.0, pie 50.4 / 48.7; '16 again the same. Data: `qa/b1604p27-pa16-webkit-390x844.json`.
  - Sort chip: 60 checks (bar, split bar, range, %, #, scrollTop 0 / 13 / 47 / 200) at 390: chip at x 288-322, y 111-133 every time, over no row's bars or labels. Rows number-only (CA 38.3% 58.5%; PA US House "1", "4", "17"; PA senate "10", "12"); at-large rows "DE At-large" and DC "At-large"; names at x 52-77 and bars from x 83 in bar, split and range split lists; one bar scale per list (spread 1.007-1.037). Data: `qa/b1604p27-v-chromium-iphone390.json`, `qa/b1604p27-own-chromium-iphone390.json` (`pa_rows`, `dc_rows`, `us_rows`).
  - Thumbnails centred on the topic-icon axis (x 27) in all 12 checked views (US map '24/'16, PA map '16/'24, PA US House map/list/back, PA senate list/back, DC, US list). Data: `own` > `ax`.
  - Menus (WebKit 390x844 and 1024x768, US and Alabama): pie box unchanged when the type and chart menus open (52,114-324,386 phone; 210,114-800,704 iPad), backdrop transparent, nothing dimmed, open in 12-20 ms. Data: `qa/b1604p27-menus-webkit-iphone390_ipad1024x768.json`.
  - Chart off returns to the map (bar and pie), reload restores it; top rows flush, no overlaps or off-screen elements on map, chart bar, chart pie and list. CLS over the whole verify run 0.360, the same as pass 26 (0.360). The script note "line button not visible" at one year is the same as pass 26 (line is offered in a range: chart options `gbar, line` in the range, `gbar` at one year).
- **Layout sweep (16 steps, 1604): Chromium 390 and 1024x768, WebKit 390.** US map > time row > geo menu All States > MA > 2020 > 2024 > Worcester > US House list > type off > Back > Back > split bar > MA > Worcester > Back > Back > globe to map. Slider, top fields, right buttons, first list row and bottom bar did not move on any year change, drill-in or Back (no transients). Expected changes only: map thumbnails +68 px when the time row opens, row height 30 > 44 px when switching bar > split bar, chart button hidden while the type row is open. The new sweep (`layout3`, now also tracking the list thumbnails and the sort chip) found the 30 px thumbnail drop on drill-in from All States and the 30 px rise on Back to All States: filed as QA-089. Shots: shots/b1604p27-{ch,we}-*-ls2??-*.png, shots/b1604p27-{ch,we}-*-ls3??-*.png. Data: `qa/b1604p27-layout2-{chromium,webkit}-390.json`, `qa/b1604p27-layout3-{webkit-390,chromium-1024x768}.json`.
- **Smoke flow, Chromium, all 5 sizes, touch (1604):** institution menu > All States, sort flip, % / #, time row, 2020 and the range, chart menu (split bar, line in the range; split bar at one year), PA > Philadelphia > townships, Back, district-type menu, US House (Districts 5 / 3 / 2 from the Philadelphia list), reload restores PA > Philadelphia County list, bar, #, 2024. Numbers unchanged (CA 38.3 / 58.5, PA 50.4 / 48.7). No layout overlaps or off-screen elements. Taps over 100 ms: only the All States row, 118 ms at 390 and 121 ms at 1024x768 (QA-007; 88-90 ms at 375, 320 and 1024x576); all others 4-76 ms. Watch item unchanged: tiny periodic layout shifts after the # tap (0.0003-0.0032 each, every ~250 ms; the first names `#laCands`). The address step at the end of this flow is QA-087 (it ends on the national list, not DC). Data: `qa/b1604p27-flow-chromium-.json`, shots shots/b1604p27-ch-*-{allstates-*,drill-*,chart-*,type-*,after-reload,addr-*}.png.
- **Address from the map still works (QA-062/068 hold, 1604):** fresh load, map view, "1600 Pennsylvania Ave NW, Washington, DC 20500" + Enter: title "District of Columbia", thumbnails Harris 90% / Trump 6%, popup Harris 90.3% / Trump 6.5%, map at 38.8987, -77.0352, zoom 15; Chromium and WebKit 390. Shots: shots/b1604p27-ch-390-addr-map.png, shots/b1604p27-we-390-addr-map.png. Data: `qa/b1604p27-addr-{chromium,webkit}-390.json`.
- Correction to pass 26: its smoke-flow line "White House address goes to DC" was wrong. The 1601 shot shows QA-087 already (shots/b1599p26-ch-390-addr-result.png: "District of Columbia states" over the national list, 77.30M / 75.02M).
- Not re-run this pass: WebKit year-tap speed (fixed on 1599), smoke flow in WebKit.

### QA-087 [Fixed on 1605 (verified pass 28)] [CRITICAL] Address search from a list view titles the screen "District of Columbia" but shows the national All States list and the US totals
- Severity: CRITICAL (wrong numbers under a place title) | Build 1604 (also on 1601, see the pass-26 shot) | Chromium 390x844 (probe), smoke flow at 390, 375, 320, 1024x576, 1024x768 (touch)
- Steps: fresh load > geo button > All States > PA > Philadelphia (townships list, %), then tap the bottom field, type "1600 Pennsylvania Ave NW, Washington, DC 20500" > Enter, wait 7 s.
- Expected: DC's own result, as from the map: title "District of Columbia", thumbnails Harris 90% / Trump 6% (DC row "At-large 90.3%").
- Actual: the title says **"District of Columbia" states**, but the list is the 51 state rows (CA 38.3% 58.5%, TX 56.2% 42.5%, ...) and the thumbnails show the national **Trump 50% / Harris 48%** (77.30M / 75.02M in # mode). A back chevron shows at the top level. The bottom field shows "1600 PENNSYLVANIA AVE NW, WASHI…"; the saved state has `dc:1`, `la:"states"`, map 38.8987, -77.0352, zoom 15. In # mode on the 390 flow run the title said "All States" instead, with the same national list (shots/b1604p27-ch-390-addr-result.png).
- Also: from the All States list itself the same search changes nothing you can see (title "All States", national list and thumbnails stay; saved state has `dc:1`).
- WebKit (390): from the map it works; in the list views my harness's typing did not reach the field (it stayed empty with the place menu open), so WebKit list views are not judged.
- Shots: shots/b1604p27-ch-390-addr-phila.png, shots/b1604p27-ch-1024x768-addr-result.png, shots/b1604p27-ch-390-addr-allstates.png, shots/b1599p26-ch-390-addr-result.png (1601). Data: `qa/b1604p27-addr-chromium-390.json` (`phila`, `allstates`, `map`), `qa/b1604p27-flow-chromium-.json` > `addr_result`; script `qa/p27-addr.py`.

### QA-088 [Fixed on 1606 (verified pass 28)] [LOW] Institution search "USA" also lists Colusa County, CA
- Build 1604 | WebKit 390x844, Chromium 375x667, WebKit 1024x768 (real taps and typing)
- Steps: institution field > type "USA".
- Expected: COUNTRY "United States" only, like "America" on 1604 (a synonym hit drops typo look-alikes).
- Actual: COUNTRY "United States", then COUNTIES "Colusa County, CA" (looks like a loose fuzzy match: "usa" is inside "Colusa"). Same leftover as QA-067.
- Data: `qa/b1604p27-067.json` > `q.USA` (all 3 runs). No screenshot of this query.

### QA-089 [Fixed on 1606 (verified pass 28)] [HIGH (layout jump rule), long-standing, maybe by design] List thumbnails drop 30 px on every drill-in from All States and rise 30 px on Back
- Build 1604 (same since 1567: an early pass noted `#laCands` at y 191 on the US list and y 221 below it, "room for the back chevron", but it was never filed) | WebKit 390x844, Chromium 1024x768 (touch)
- Steps: geo button > All States (list) > tap "MA". Later Back to All States.
- Expected: thumbnails stay put on drill-in and Back, like the slider, top fields, right buttons, first row and bottom bar do.
- Actual: the two list thumbnails (`#laCands .lact`) move from y 187 / 239 to y 217 / 269 (**dx 0, dy +30**) when the back chevron appears at y 166, and back up (**dy −30**) on Back to All States. Same numbers at Chromium 1024x768. Deeper drill-ins and Backs (MA > Worcester > Back) don't move them. If this is the intended room for the chevron, mark it by design.
- Shots: shots/b1604p27-we-390-ls303-list-drill-MA-before.png, shots/b1604p27-we-390-ls303-list-drill-MA-after.png, shots/b1604p27-we-390-ls315-list-back-gbar-2-after.png. Data: `qa/b1604p27-layout3-webkit-390.json`, `qa/b1604p27-layout3-chromium-1024x768.json` (steps 3 and 15), script `qa/p27-lay3.py`.

## Re-test status, builds 1599-1602 (pass 26, live line 9 = 202610181599 at start; Oct 19 ~1:54-2:50 AM EDT)
- Builds: **1599** (`c19f7a0`, QA-085 recolour in place, QA-006, QA-067, QA-051, QA-061, QA-068, QA-069, QA-086 first try) at the start; **1600/1601** (`06d369f`/`2ad6b2d`, QA-086 name from data-party; 1601 only fixes the build number) by ~2:10 AM; **1602** (`6d73ec1`, QA-084 cached rows keyed by chart mode) by ~2:30 AM. Each item names the build its runs read from `window.BUILD`. No console errors, page errors or failed requests in any pass-26 run. No v3 preview or live URL yet.
- **QA-086 fixed on 1600/1601:** with the time row closed, a range-chart thumbnail tap now shows the white bubble beside the photo in both engines (WebKit 390 38-44 ms after the tap, Chromium 390 57-64 ms): "Donald Trump 2020" x 11-154, y 89-117 above the photo (x 11-41, y 121-151), "Donald Trump 2024" x 185-328 left of the clock button (x 334-382), "Joe Biden 2020" x 47-159 beside the photo, "Harris ’24" x 212-292. No dark bubble. The orchestrator's `tests/range-bubble-closed.py` failed all 16 closed-row taps on 1599 (run 1:55-2:00 AM, before 1600 landed); my probe on 1601 passes. Shots: shots/b1599p26-we-390x844-rangebub-closed-0.png, shots/b1599p26-ch-390x844-rangebub-closed-1.png. Data: `qa/b1599p26-rangebub-{webkit,chromium}-390x844.json`, `qa/p26-t-rangeclosed.log`.
- **QA-084 fixed on 1602:** orchestrator `tests/gbar-rows-first-paint.py` 0 fails (cold first visits and bar-then-split, 390 and 320). Layout sweep 390 (Chromium and WebKit, 1602): no transient row on the first-visit split-bar drill-ins (MA, Worcester) or Back. Data: `qa/p26-t-gbar.log`, `qa/b1599p26-layout2-{chromium,webkit}-390.json`.
- **QA-085 fixed in WebKit, still slow in Chromium (1599-1601):** orchestrator `tests/year-tap-speed.py` (WebKit) 0 fails: 390 state house median 67 ms (1/12 over 100), senate 47, US House 31, county map 48; 375 and 320 the same range (27-68 ms medians, at most 1/12 over 100). Chromium (own `qa/p26-ylat.py`, 1601): 1024x576 state house 125 / 188 / 230 ms (min / median / max, 12 of 12 over 100), state senate 106 / 172 / 353 (12/12); 390 state house 18 / 142 / 170 (11/12), county map 28 / 112 / 212 (7/12). Better than 1598 (196 / 307 / 531 at 1024x576) but still over 100 ms. Shot: shots/b1599p26-ch-1024x576-ylat-PA-statehouse.png. Data: `qa/b1599p26-ylat-chromium-{1024x576,390x844}.json`, `qa/p26-t-yeartap.log`.
- **QA-006 fixed (1599):** Philadelphia County townships list shows only "Philadelphia city" at all 5 sizes in the smoke flow; orchestrator `tests/qa-batch-1600.py` confirms Rockledge stays in Montgomery County.
- **QA-067 still open in the real search (1599 and 1601):** the orchestrator's unit check passes (it ranks a 3-item test list), but typing "America" in the institution field (real taps and typing, WebKit 390x844, Chromium 375x667, WebKit 1024x768 on 1601) still lists COUNTRY "United States", **"South Africa"**, then COUNTIES "Amelia County, VA". Both South Africa and Amelia look like loose fuzzy matches shown next to a real match. "Afrika" lists Central African Republic and South Africa (fine). Shots: shots/b1599p26-ch-375x667-inst-America.png, shots/b1601p26-we-1024x768-inst-America.png. Data: `qa/b1599p26-batch-*.json`, script `qa/p26-batch.py`, `qa/p26-067.py`.
- **QA-068 fixed (1599):** "Franklin County, OH" > Enter, then "1600 Pennsylvania Ave NW, Washington, DC 20500" > Enter: map at 38.8987, -77.0352, zoom 15 (about 150 m from the White House point, was 2 km at zoom 11); title "District of Columbia". WebKit 390 and Chromium 375. Shot: shots/b1599p26-we-390x844-qa068.png
- **QA-069 fixed (1599):** "Allegheny County, PA", then "350 5th Ave, New York, NY 10118": title reads "New York AD 75 ED 15". Shot: shots/b1599p26-we-390x844-qa069.png
- **QA-061 fixed (1599):** All States > tap DC > state menu Delaware: crumb "Delaware", bottom field "Delaware" (was "District of Columbia"). Shot: shots/b1599p26-we-390x844-qa061-DE.png
- **QA-051 fixed (1599):** '16>'20 All States list thumbnails labelled "Joe Biden 2020" / "Donald Trump 2020" (51% / 47%), aria-label and title. Shot: shots/b1599p26-we-390x844-qa051.png
- **Orchestrator verify list holds (1601/1602):** '16 colours (Chromium 390): US House map 27.2% blue at '16 (Clinton 48% / Trump 46%), PA map 26.3%, PA US House 26.8%, senate 25.1%, state house 24.0%; Philadelphia and Pittsburgh D, rural PA and Lancaster R in every map. PA '16 bar 48.2 / 47.5 / Other 4.4 and pie 48.2 / 47.5 (WebKit 390, 1602; '24 bar 50.4 / 48.7). Rows number-only, names x 52-77 and bars from x 83 in bar, split and range split lists, one bar scale (spread 1.007-1.037), chip clear (no chip issue in the verify run). Data: `qa/b1599p26-{col16,v}-chromium-iphone390.json`, `qa/b1599p26-pa16-webkit-390x844.json`.
- **Smoke flow, Chromium, all 5 sizes, touch (1601/1602):** institution menu > All States, sort flip, % / #, time row, 2020 and the range, chart menu, PA > Philadelphia > townships, Back, district-type menu, US House (Districts 5 / 3 / 2 from the Philadelphia list), reload restores PA > Philadelphia County list, bar, #, 2024; White House address goes to DC. Numbers unchanged (CA 38.3 / 58.5, PA 50.4 / 48.7). No layout overlaps or off-screen elements. Only tap over 100 ms: All States row at 1024x768 114 ms (QA-007; 86-96 ms at the other sizes). Watch item unchanged: tiny periodic layout shifts after the # tap (0.0003-0.0023 each, every ~250 ms; first names `#laCands`). Data: `qa/b1599p26-flow-chromium-.json`.
- **Layout sweep 390 (Chromium and WebKit, 1602):** slider, top fields, right buttons, bottom bar and first row did not move on year changes, drill-ins or Back. Only change: row height 30 > 44 px when switching the chart from bar to split bar (expected, same as pass 25).

## Re-test status, build 1597 (pass 25, live line 9 = 202610181597; Oct 18-19 ~11:55 PM-12:50 AM EDT)
- Builds: 1597 (`8b3ccbc`, QA-076 name bubble beside the photo) was live at the start; **1598** (`43a3de5`, QA-084 split-bar rows draw at their final height in the first frame) went live at ~12:02 AM EDT mid-pass. Runs from ~12:04 AM on read `window.BUILD` = 202610181598 (each data file records its build). Box quiet, one browser per process; no runs killed. No console errors, page errors, failed requests or HTTP errors in any pass-25 run.
- **QA-076 fixed (1597, still fixed on 1598):** orchestrator's `tests/icon-bubble.py` on live: 0 fails (WebKit 390x844, 375x667, 320x568, 1024x768; Chromium 390x844; bar, pie and range bar with the time row open). Own probe `qa/p25-bubble.py` (fresh load US 2024 > chart button > Bar > tap Trump, then Harris; also PA): Chromium 390x844, 375x667, 320x568, 1024x576, 1024x768 and WebKit 390x844, 1024x768 all give the same boxes: "Donald Trump" bubble x 92-201, y 115-143 next to the photo at x 12-42, y 114-144; "Kamala Harris" x 92-201, y 159-187 next to the photo at y 158-188; the 50 px gap holds the value label ("49.9%" / "48.4%"), which the bubble no longer covers; inside the screen, over no other photo. PA ('24) same boxes. Range 2020 > 2024 with the time row open (WebKit 390): "Donald Trump 2020" x 12-155, y 150-178 right above the photo (y 182-212), "Harris ’24" x 206-286 left of the photo at x 292-322; none over a photo or label. Shots: shots/b1597p25-ch-390x844-bubble-us-0.png, shots/b1597p25-ch-1024x768-bubble-us-0.png, shots/b1597p25-we-390x844-bubble-pa-1.png, shots/b1597p25-we-390x844-rangebub-open-0.png. Data: `qa/b1597p25-bubble-*.json`, `qa/p25-icon-bubble.log`, `qa/b1597p25-rangebub-*.json`.
- **New: QA-086** (range chart with the time row closed: no name bubble in WebKit, the old dark bubble over the clock button in Chromium).
- **QA-084 changed (1598, partly fixed):** Back and repeat drill-ins now draw 44 px split-bar rows from the first frame in both engines (was 30 px for 6-91 ms). First-visit drill-ins still draw 30 px rows first, with the real names already in them: Chromium 390 MA 188 ms (frames 39 > 227 ms), Worcester 134 ms; WebKit 390 MA 179 ms, Worcester 253 ms; then 44 px (rows 2 and 3 drop 14 / 28 px). Layout sweep agrees (transient first row only on the two first-visit split-bar drill-ins, Back clean). Data: `qa/b1597p25-rowfr-{chromium,webkit}-390x844.json`, `qa/b1597p25-layout2-{chromium,webkit}-390.json`, orchestrator test log `qa/p25-gbar-first-paint.log`.
- **QA-085 still open (1598):** Chromium 1024x576 PA state house year taps 196 / 307 / 531 ms (min / median / max, 12 of 12 over 100), state senate 130 / 212 / 349 (12/12); Chromium 390 state house 188 / 275 / 369 (12/12; the first tap is no longer fast), county map 27 / 93 / 161 (4/12). Data: `qa/b1597p25-ylat-chromium-{1024x576,390x844}.json`, shot shots/b1597p25-ch-1024x576-ylat-PA-statehouse.png.
- **QA-005 still fixed:** `tests/ushouse-in-county.py` on live 0 fails (Chromium and WebKit); smoke flow lists Districts 5 / 3 / 2 from the Philadelphia townships list at all 5 sizes. `qa/p25-ushouse.log`.
- **QA-006 still open:** Philadelphia County townships list still shows "Rockledge borough | 520" at all 5 sizes.
- **QA-007:** no tap over 100 ms in the 5-size smoke flow (All States row 81-100 ms: 92.8 at 390, 80.7 at 375, 84.9 at 320, 98.2 at 1024x576, 99.8 at 1024x768; US House pick 53-91 ms). Borderline, not over.
- **QA-054 / 057 / 058:** not re-measured this pass (WebKit sweep only ran the list steps); layout sweep at 390 still shows the thumbnails moving 68 px down when the time row opens on the map, as on 1596 (not a jump: the row pushes them).
- **Orchestrator verify list holds on 1598:** '16 colours (Chromium 390): US House map 27.2% blue / 72.8% red at '16, PA map 26.3% blue, PA US House 26.8%, PA senate 25.1%; Philadelphia and Pittsburgh D, rural PA and Lancaster R in all; labels Clinton 48% / Trump 46% (US), Trump 48% / Clinton 47% (PA). FL, PA, MI, WI statewide '16 pale (margins under 1.2 points), as in pass 23. PA '16 bar 48.2 / 47.5 / Other 4.4 and pie 48.2 / 47.5, unchanged after '16 > '24 > '16 (WebKit 390, '24 50.4 / 48.7). Sort chip clear of every row (no chip issue in the 390 verify run); names at x 52-77, bars from x 83 (bar %, split %/#, range split); one bar scale (spread 1.007-1.037). Rows number-only (PA 1, 4, 17; senate 10, 12, 16), DC "At-large", nationwide "DE At-large". Thumbnails on the topic-icon axis in every view (no axis issue). Menus overlay without shrinking or dimming (WebKit 390 and 1024x768, US and Alabama, pie box unchanged, backdrop transparent, open 13-20 ms). Data: `qa/b1597p25-{col16,own,v95}-chromium-iphone390.json`, `qa/b1597p25-pa16-webkit-390x844.json`, `qa/b1597p25-menus-webkit-*.json`.
- **Smoke flow, Chromium, all 5 sizes, touch (`qa/p25-flow.py`):** institution menu > All States, sort flip, % / #, time row, 2020 and 2020 > 2024 range, chart menu (split bar, line in the range; bar/pie at one year), PA > Philadelphia > townships, Back, district-type menu, US House, reload restores PA > Philadelphia County list, bar, #, 2024; White House address goes to DC. Numbers unchanged (PA 50.4 / 48.7, CA 38.3 / 58.5). Layout checks: no overlaps or off-screen elements. Data: `qa/b1597p25-flow-chromium-.json`, shots shots/b1597p25-ch-{390,375,320,1024x576,1024x768}-*.png.
- **Watch item (layout shifts after #), still seen, still not found:** the smoke flow logs the same tiny periodic shifts at all 5 sizes (0.0003-0.0023 each, every ~240-250 ms from ~2 s after the # tap until the time row opens; the first one names `#laCands`, 0.0006-0.0073, the rest have no source). Two focused probes (`qa/p25-numjit.py` with and without the sort flips, per-frame rects of rows, chip, buttons, `#laCands`) saw no periodic shifts and no moving element: only the one input-caused shift when the bars change to #. Still looks like the harness; keep watching.
- **Layout sweep 390 (Chromium and WebKit, `qa/p25-lay2.py`):** slider, top fields, right buttons and bottom bar did not move on year changes, drill-ins or Back. Only the remaining QA-084 first-visit transient. Chromium 1024x768: same result as 390 (`qa/b1597p25-layout2-chromium-1024x768.json`).
- **Previews (not v2, not v3), sanity load at Chromium 390x844:** /previews/shadows/ and /previews/compact/ both load (HTTP 200, BUILD 202610181597, title "PREVIEW …", robots noindex,nofollow), no console errors, page errors or failed requests; thumbnails Trump 50% / Harris 48%, map drawn, All States list rows CA 38.3 / 58.5, TX 56.2 / 42.5 (same as v2). Shots: shots/b1597p25-ch-390-preview-{shadows,compact}{,-list}.png. No polish bugs filed (as asked).

### QA-086 [Fixed on 1600/1601 (verified pass 26)] [MEDIUM] Range chart with the time row closed: tapping a thumbnail shows no name bubble (WebKit) or the old dark bubble over the clock button (Chromium)
- Build 1597 and 1598 | WebKit 390x844 and 1024x768 (no bubble), Chromium 390x844 (dark bubble) (touch). With the time row open both engines show the new 1597 bubble correctly.
- Steps: fresh load (US) > clock button > select 2020 > 2024 > tap the clock button again to close the time row > chart button > Bar > tap a thumbnail (Trump 2020 at left, Trump 2024 / Harris 2024 at right).
- Expected: the same white name bubble as with the row open / at one year, beside the photo, not over a photo, label, field or button.
- Actual: WebKit: nothing appears (no `#iconBub` or `#partyBub` in any frame for 2.5 s after each of 4 taps). Chromium: the old black `#partyBub` appears instead for ~1.8 s, centred above the photo: "Donald Trump 2020" x 6-136, y 93-117 (over the bottom of the geo field, which ends at ~y 106), "Donald Trump 2024" x 248-378, y 93-117, "Kamala Harris 2024" x 248-378, y 141-165, on top of the clock button (x 334-382, y 114-162).
- WebKit 1024x768 on 1598: row closed, 4 taps (Trump 2020 at x 11-41, Trump 2024 at x 932-962, Biden 2020, Harris 2024), no bubble in any frame; row open, the white bubble appears 33-46 ms after each tap beside the photo ("Donald Trump 2020" x 48-191, y 183-211 next to the photo at x 12-42; "Kamala Harris 2024" x 777-920 left of the photo at x 926-956). Data: `qa/b1597p25-rangebub-webkit-1024x768.json`, shots shots/b1597p25-we-1024x768-rangebub-{closed,open}-0..3.png.
- Shots: shots/b1597p25-ch-390x844-rangebub-closed-3.png (dark bubble over the clock button), shots/b1597p25-we-390x844-bubble-range-0.png (WebKit, nothing after the tap), shots/b1597p25-we-390x844-rangebub-open-0.png (row open: fine). Data: `qa/b1597p25-rangebub-{webkit,chromium}-390x844.json` (per-frame bubble boxes), script `qa/p25-rangebub.py`

## Re-test status, build 1596 (pass 24, live line 9 = 202610181596; Oct 18 ~10:57-11:30 PM EDT)
- Build since pass 23: 1596 (`16c1d3c`: QA-005 US House inside a county lists that county's US House districts, deselect returns to the townships list; row taps found at the finger's real point so a tap on a row name next to the thumbnail column drills in instead of toggling the candidate). No v3 preview or live URL yet. Box quiet (load 0.3-1.3). No console errors, page errors, failed requests or HTTP errors in any pass-24 run.
- **QA-005 fixed (1596):** orchestrator's `tests/ushouse-in-county.py` on live: 0 fails in Chromium and WebKit at 390x844 and at 1024x768 (Philadelphia > US House lists Districts 2, 3, 5; Allegheny lists 12 and 17; deselect returns to the same townships list; a tap on the thumbnail itself still toggles the candidate and back). The 5-size smoke flow agrees: US House from the Philadelphia townships list now shows 3 rows ("5 | 147K | 267K", "3 | 347K", "2 | 93K | 199K") at every size (was 0 rows). Logs: `qa/p24-qa005.log`, `qa/p24-qa005-1024.log`.
- **Smoke flow, Chromium, all 5 sizes, touch (`qa/p24-flow.py`):** institution menu, All States (104 ms at 390, otherwise under 100), sort flip, % / #, time row, 2020, '20 > '24 range, chart menu (split bar, line in the range, split bar at one year), PA > Philadelphia > Philadelphia city precincts, Back, district-type menu, US House (100.2 ms at 1024x768), deselect, reload restores PA > Philadelphia County list, bar, #, 2024; White House address goes to DC. Numbers unchanged from pass 23 (PA 50.4 / 48.7, CA 38.3 / 58.5). Data: `qa/b1596p24-flow-chromium-.json`, shots shots/b1596p24-ch-*.png.
- **Orchestrator verify list holds on 1596:** '16 colours (Chromium 390): US House map 27% blue / 73% red, PA map 26% blue at '16, Philadelphia and Pittsburgh D, labels Clinton 48% / Trump 46% (US), Trump 48% / Clinton 47% (PA); shots shots/b1596p24-ch-390-col16-*.png. PA '16 bar 48.2 / 47.5 / Other 4.4 and pie 48.2 / 47.5, still right after '16 > '24 > '16 (WebKit 390, `qa/p24-pa16-wk390.log`). Sort chip covered no row name, label or value in 60 checks (Chromium 390); names at x 52-77, bars from x 83; one shared bar scale (spread 1.007-1.037). Menus overlay without shrinking or dimming (WebKit 390 and 1024x768, US and Alabama, open in 12-24 ms). Top rows flush, no overlaps or off-screen elements on map, chart bar, chart pie or list; chart off returns to the map.
- **QA-084 still open (1596):** split bar list rows still draw at 30 px first, then 44 px. Chromium 390: first-visit drill-in 184-228 ms of short rows, Back 13-16 ms, repeat drill-ins flip 44 > 30 > 44 again for 12-17 ms. WebKit 390: first-visit drill-in 314-416 ms, Back 18-73 ms, repeats flip twice. Plain bar list: no change. Data: `qa/b1596p24-rowfr-{chromium,webkit}-390x844.json`.
- **QA-085 still open (1596):** Chromium 1024x576 year taps on PA's state house map 212 / 349 / 424 ms (min / median / max, 12 of 12 over 100 ms), state senate 149 / 262 / 399 ms (12 of 12). Data: `qa/b1596p24-ylat-chromium-1024x576.json`, shot shots/b1596p24-ch-1024x576-ylat-PA-statehouse.png.
- **Layout sweep 390 (Chromium, `qa/p24-lay2.py`):** slider, top fields, right buttons and bottom bar did not move on year changes, drill-ins or Back. Only the known QA-084 (first row transient in the split bar list on drill-in and Back). Data: `qa/b1596p24-layout2-chromium-390.json`.
- **Still open, unchanged:** QA-076 (Chromium 390: name bubble at x 6-116, y 115-143 over the photo at x 12-42), QA-006 (Rockledge borough still listed under Philadelphia County), QA-054/057/058 as in pass 23.
- Watch item, not filed: in the smoke flow on 1596 (all 5 sizes, twice at 390) the browser logged a tiny layout shift (score 0.0004-0.0023, no source element) every ~240 ms for about 6 s, starting ~1.3 s after the # button is tapped on the All States list; earlier builds logged none in the same script. Three focused probes (same steps, per-frame position diff of every visible element) found nothing moving, so the element is unknown and it may come from the test harness. Re-check next pass. Data: `qa/b1596p24-flow2-chromium-iphone390.json` (`shifts`), probes `qa/p24-numjit.py`, `qa/p24-numjit2.py`.

## Re-test status, build 1595 (pass 23, live line 9 = 202610181595; Oct 18 ~9:50-10:40 PM EDT)
- Live build unchanged since pass 22 (1595, `c34d398`). No v3 preview or live URL yet. Box quiet (load 0.7-1.5); one browser and one viewport per process, so no runs were killed this time. No console errors, page errors, failed requests or HTTP errors in any pass-23 run (19 data files).
- **1024x576 verify (Chromium, touch) passes, carried over from pass 22:**
  - Smoke flow (`qa/p23-flow.py`): institution menu > All States 95 ms, sort flip 23 ms, % / # 33 ms, time row 28 ms, 2020 and 2020 > 2024 range, chart menu (split bar, line in the range; bar and split bar at one year), drill PA 23 ms > Philadelphia 26 ms > Philadelphia city precincts 56 ms, Back 37 ms, district-type menu 5 ms, US House 63 ms, reload restores PA > Philadelphia County list, bar, #, 2024 (map position and the unselected type differ, as in pass 21), White House address goes to DC (field "1600 PENNSYLVANIA AVE NW, WASHI…"). CLS 0. US House from the Philadelphia townships list still 0 rows (QA-005).
  - '16 colours (`qa/p23-col16.py`, `qa/p23-own.py`): US House map at '16 shows blue and red districts (shot below); PA counties 25% blue, PA US House 23%, state senate 20%, state house 23% at '16; Philadelphia and Pittsburgh blue, rural PA and Lancaster red in all five maps; PA points Philadelphia, Allegheny, Lackawanna blue, Lancaster, Westmoreland, Erie, Clearfield red. Statewide '16: CA, NY, IL, CO, VA blue, TX, OH, KS red, FL, PA, MI, WI pale pink (margins under 1.2 points). WA's sample point sits under the open time row at this height (harness, not the app). At 1024 wide the US pixel share counts the blue sea too (57% "blue" at '16 and 56% at '24), so it is not comparable with the 27% at 390. Thumbnails: US Clinton 48% / Trump 46%, PA Trump 48% / Clinton 47%. Shot: shots/b1595p23-ch-1024x576-col16-US-ushouse.png
  - **PA '16 bar** 48.2% / 47.5% / Other 4.4% and **pie** 48.2% / 47.5%, both still drawn after '16 > '24 > '16 ('24: 50.4 / 48.7). Shots: shots/b1595p23-ch-1024x576-PA-{bar,pie}-16b.png
  - Sort chip (x 922-956, y 111-133; y 177-199 with the time row open) covered no row name, label or value in 60 checks (bar %/#, split %/#, range bar/split %/#, '16 > '24, '16, scroll 0/13/47/200). Bars on one scale (spread 1.007-1.037). Names at x 52-77, bars from x 83 in the bar, split and range split lists. List rows number-only (PA US House 1, 4, 17; senate 10, 12, 16), DC "At-large", nationwide "DE At-large".
  - Thumbnails exactly on the topic-icon axis (x 27, icon x 27) in all 12 views checked (US map '24 and '16, PA map '16/'24, PA US House map, list and map again, PA senate list and map again, DC US House list and map again, US House list).
  - Menus overlay: pie box (306,114)-(704,512) unchanged with the district-type menu and the chart menu open, backdrop transparent, no tinted layer, open in 14-28 ms (US and Alabama). Top flush: search bar top 0, map top 0, no overlaps or off-screen elements on map, chart bar, chart pie and list. Chart off (bar and pie) returns to the map, and reload stays on the map.
  - Tap latencies over 100 ms here: US House pick on the PA map 130 ms (QA-007), PA senate list > map 106 ms. All States row 90-95 ms (under 100 at this size now).
- **WebKit 320x568 jitter (carry-over) passes:** All States list, `#laSort` top 111 at every rest (scrollTop 10, 22, 25, 40, 97), after wheel drags of 40 / 60 / −100 / 25 px and after smooth scrolls to 60 and 0 (rows move only while scrolling, nothing changes in the 1-3 s after the stop); chip top 111 at scrollTop 15-35. Data: `qa/b1595p23-jit-webkit-320x568.json`. Shot: shots/b1595p23-we-320-jitter.png
- **WebKit layout sweep 390x844 and 1024x768 (carry-over), 32 + 14 steps each:** slider, top fields, right buttons and bottom bar did not move on year changes (2020, 2016, 2024, '20 > '24, '16 > '24, in the map and the list), drill-ins or Back. Same known items as Chromium: QA-054 (thumbnails −3 / +3 px on map > list / list > map), QA-058 (+23 / −23 px when the range turns on / off in the Worcester list; at 1024x768 the thumbnails also narrow 300 > 123 > 125 px over 355 ms), QA-057 (chart button hidden while the layers row is open; crumb Worcester County > Massachusetts on US House). **New: QA-084** (split bar list rows jump on every drill-in and Back, both engines). Data: `qa/b1595p23-layout-webkit-{390,1024x768}.json`, `qa/b1595p23-layout2-webkit-{390,1024x768}.json`, `qa/b1595p23-rowfr-*.json`
- **QA-076 still open:** WebKit 390: bubble x 6-116, y 115-143 over the photo at x 12-42; Chromium 1024x576: x 316-426, 274 px right of the photo. Shots: shots/b1595p23-we-390-bubble.png, shots/b1595p23-ch-1024x576-v-bubble.png
- **New: QA-085** (year taps on PA district-type maps 150-425 ms).
- Seen, not filed: on a first visit the drilled list shows a gray placeholder (skeleton rows, no thumbnails or back chevron) for 230-430 ms while the data loads (both engines); repeat visits draw at once. Looks intended. Shot: shots/b1595p23-we-390-drillgap-OH.png
- Harness note: the layout sweep's "chart-bar" step does nothing because Bar is already the list's chart, and its "MA" tap at 1024x768 can land on the thumbnail column; `qa/p23-lay2.py` and `qa/p23-rowfr.py` tap the row name instead.

### QA-084 [Fixed on 1602 (verified pass 26)] [HIGH] Split bar list: rows first draw at the plain bar height (30 px), then grow to 44 px, so every row below the first drops 14 px per row on each drill-in and Back
- Build 1595 (earlier builds not checked) | Chromium 390x844, 1024x576; WebKit 390x844, 1024x768 (touch)
- Steps: All States list > chart button > Split bar (2024, %) > tap "MA" > tap "Worcester" > Back > Back. (Bar list, same steps: no change.)
- Expected: the new rows draw once at their final size; nothing moves afterwards.
- Actual: the new list first draws with 30 px rows (row tops 122 / 152 / 182) and then switches to 44 px rows (122 / 166 / 210): row 2 moves down 14 px, row 3 28 px, row n 14 x (n−1) px (Nantucket, the 14th MA row, about 182 px). How long the short rows stay up: WebKit 390: drill-in 346 / 326 ms on a first visit, Back 19-22 ms, repeat drill-ins flip twice (30 > 44 > 30 > 44, 20-85 ms each). WebKit 1024x768: drill-in 531 / 324 ms, Back 84 / 91 ms, repeats 21-54 ms. Chromium 390: drill-in 200 / 183 ms, Back 6-20 ms, repeats 12-13 ms. Chromium 1024x576: drill-in 150 / 229 ms, Back 12-19 ms, repeats 11-17 ms. In WebKit's long first-visit phase the short rows are a faded single stacked bar per row with names cut to "M…", "W…", and no thumbnails or back chevron, and then the split bars appear (see the mid shot).
- Shots: shots/b1595p23-we-390-rowfr-gbar-drillMA-0-mid.png (short rows, ~210 ms), shots/b1595p23-we-390-rowfr-gbar-drillMA-0-end.png (final). Data: `qa/b1595p23-rowfr-{webkit-390x844,webkit-1024x768,chromium-390x844,chromium-1024x576}.json` (per-frame tops and heights of the first 3 rows), script `qa/p23-rowfr.py`

### QA-085 [1611 Chromium 1024x576: state house median 111 ms, senate 105, county map 103 (pass 32)] [1609 Chromium 1024x576: state house median 105 ms, senate 62, county map 90 (pass 30)] [WebKit fixed on 1599; Chromium district maps fixed on 1605, PA county map at 1024x576 still 129 ms median (pass 28)] [HIGH (slow tap)] Year taps on Pennsylvania's district-type maps take 150-425 ms to paint
- Build 1595 (pass 21's '16-colour run on 1592-1594 at 390 already logged 131-335 ms for these taps, not filed then) | Chromium 1024x576, 390x844; WebKit 390x844 (touch)
- Steps: geo field "Pennsylvania" + Enter > district-type button > State house (or State senate, US House) > close the row > clock button > tap '16, '24, '20, '24 on the slider (x3).
- Expected: under 100 ms from tap to next paint.
- Actual, 12 taps each, min / median / max: Chromium 1024x576: state house 184 / 346 / 425 ms (12 of 12 over 100), state senate 154 / 221 / 282 (12/12), US House 105 / 172 / 369 (12/12), PA county map 77 / 168 / 193 (10/12). Chromium 390: state house 34 / 274 / 336 (11/12), county map 19 / 109 / 254 (6/12). WebKit 390: state house 10 / 177 / 203 (11/12), county map 7 / 43 / 57 (0/12). At 390 the first tap after the type change is fast (34 ms Chromium, 10 ms WebKit) and the later ones are slow; at 1024x576 every tap is slow. Box load under 1.5 throughout.
- Shot: shots/b1595p23-ch-1024x576-ylat-PA-statehouse.png. Data: `qa/b1595p23-ylat-{chromium-1024x576,chromium-390x844,webkit-390x844}.json`, script `qa/p23-ylat.py`

## Re-test status, build 1595 (pass 22, live line 9 = 202610181595; Oct 18 ~8:57-9:25 PM EDT)
- Build since pass 21: 1595 (`c34d398`: state outlines drawn on top of every sub-state layer and thicker; QA-083 sort chip/chevron fixed at the first row's resting top). No v3 preview or live URL yet.
- **QA-083 fixed (1595):** All States list at 390x844, `#laSort` top stays 111 px at scrollTop 15, 20, 22, 25, 28, 30, 35 and 0 in Chromium and WebKit (was 106-109 at 22-25 on 1594). Touch drags 40 / 40 / -80 / 20 px (scrollTop 25 / 50 / 0 / 5): chip 111-133 every time, geo and time rows still. Data: `qa/p22-chiptop-{ch,wk}.log`, `qa/p22-drag.log`.
- **QA-082 still fixed:** per-frame jitter probe, Chromium 390 / 1024x768 / 320 and WebKit 390 / 1024x768: one change per scroll (the rows), chip constant at 111. Shots shots/b1595p22-{ch,we}-*-jitter.png. (WebKit 320 not run; the browser was closed by the box running out of memory.)
- **1595 state outlines:** PA > US House at '16 (390x844): thick white state lines drawn over the district fills, district lines thinner. Looks as described. Shot: shots/b1595p22-ch-390-col16-Pennsylvania-ushouse.png
- **Orchestrator verify list still holds on 1595:** '16 US House map 27% blue / 73% red by pixel share, PA map and PA US House 26-27% blue, Philadelphia and Pittsburgh D, rural PA and Lancaster R; labels Clinton 48% / Trump 46% (US), Trump 48% / Clinton 47% (PA). Sort chip covered no row element in 60 checks each at 375x667 and 1024x768 (bar, split, range, scrolled). Row names at x 52-77 and bars from x 83 in every list mode; at-large rows unchanged. Top rows flush (bar top 0), no overlaps or off-screen elements on map, chart bar, chart pie and list. Chart off returns to the map and reload restores it. Data: `qa/b1595p22-v-chromium-iphone375_ipad1024x768.json`, `qa/p22-col16-ch.log`.
- **Menus overlay without shrinking or dimming (WebKit, all 5 sizes, US and Alabama):** pie box unchanged, backdrop transparent, menu open 10-21 ms. Data: `qa/b1595p22-menus-webkit.json`.
- **Layout sweep 390 (Chromium, 32 steps):** same as pass 20/21, nothing new: QA-054 thumbnails -3 / +3 px on list/map, QA-058 +23 px in the plain range list, QA-057 chart button hidden while the layers row is open. Slider, top fields, right buttons, first row and bottom bar did not move on year changes, drill-ins or Back. Data: `qa/b1595p22-layout-chromium-390.json`.
- **Still open:** QA-076 (name bubble at x 6-116 over the photo at 375; at x 316-426, 270 px from the photo, at 1024x768). QA-007 borderline: All States row 92 ms at 375, 101 ms at 1024x768. QA-005/006/020/054/057/058 not changed by 1595.
- Environment: two runs (2016 colours past PA US House, verify at 1024x576) were killed by the box's out-of-memory killer, not by the app. Carry over: 1024x576 verify, WebKit 320 jitter, WebKit layout sweep.

## Re-test status, builds 1592 / 1593 / 1594 (pass 21, live line 9 = 202610181592 at start; Oct 18 ~7:51-8:40 PM EDT)
- Builds since pass 20: 1590 (`702f3b4`: QA-044 sort-chip header row, QA-078 one shared split-bar scale), 1591 (`dd2ab96`: QA-077 range bars on the icon rows with the time row closed), 1592 (`3fc48e5`: Topic/Search row flush with the safe-area top, QA-079 chart off returns to the map). **Live changed twice mid-pass:** 1593 (`e27bbed`: QA-081 list names at x 52 in every mode, QA-080 "DE At-large") was live by ~8:05 PM, and 1594 (`7eccb65`, user: 1590 header band removed, sort chip floats over the list top and nudges value labels left, clearer unblurred floating buttons, opaque white text fields) by ~8:22 PM. The 1590-1592 checks ran on 1592 (Chromium 375/320 and WebKit 390/1024x768) and 1593 (Chromium 390/1024x576/1024x768); the changed items were re-checked on 1593 and 1594 as noted. No v3 preview or live URL yet. Box load 1-4, so latencies are comparable with pass 20.
- **QA-079 fixed (1592):** fresh load > chart button > Bar (and Pie) > chart button > chart button again returns to the map (`listmode` off, no chart), and a reload comes back on the map. Chromium 5 sizes, WebKit 390x844 and 1024x768, by touch; the off tap paints in 13-38 ms. The orchestrator's `tests/chart-off.py` on live: 0 fails (WebKit 390/375/320; from a list it stays on the list). Shot: shots/b1592p21-ch-390-v-chartoff-reload.png. Data: `qa/b159[234]p21-v-*.json` (`off`).
- **QA-077 fixed (1591):** US map > time row 2020 > 2024 > close the time row > Bar: three range rows (+3.1 / −2.9 / −0.2) on the icon rows, no old "Republican +3.1 pts … R+5.9 shift" block, no "pts"/"shift" text; rows end at x 328 with the button column at 334 (390), 962 vs 968 (1024x768). Same after reopening and closing the time row again. Chromium 5 sizes, WebKit 390 and 1024x768. `tests/range-bars-closed.py` on live: 0 fails. Shot: shots/b1592p21-ch-375-v-range-closed-bar.png
- **QA-078 still fixed (1590 shared scale):** width/value ratios across all split bars agree within 0.7-3.7% (30-140 bars) in '24 %, '24 #, 2020 > 2024 % and #, 2016 > 2024 % and #, and '16 %, at every size in Chromium and WebKit 390/1024x768 (CA's −1.83M is the longest bar in # mode, FL −614K about a third of it). `tests/gbar-scale.py` on live: 0 fails. Shot: shots/b1592p21-ch-320-v-list-range-gbar-num.png
- **QA-044 (1590 header row):** the chip covered no row element (bars, names, values) in bar %, bar #, split %/#, range bar %/#, range split %/#, range line %/#, '16 > '24 split and '16 split, at scroll 0/13/47/200, Chromium 5 sizes and WebKit 390/1024x768; `tests/sort-chip-clear.py` 0 fails. **On 1594** the header band is gone by the user's choice (rows start at y 122 under the chip at 111-133, bars may pass under it, value labels are nudged left): a value/name-only check is clean at Chromium 390 and 320 and WebKit 390 in all those modes, and the updated `sort-chip-clear.py` on live passed 396/396 (WebKit 390, 375, 320, 1024x768, 1280x800, 1600x900; names, labels and values at scroll 0/13/47). See QA-082 (1590-1593 only) and QA-083 (1594).
- **Top flush (1592) verified:** `#barSearch` top 0, map top 0, nothing above y 0, and no overlap between the top rows, right buttons, thumbnails, crumbs and sort chip on the map, chart bar, chart pie and list at all 5 sizes (Chromium) and WebKit 390/1024x768, including 375x667 and 320x568. `tests/top-flush.py` on live (with 0/47/59 px insets): 0 fails. Shot: shots/b1592p21-ch-320-v-top-map.png
- **QA-081 fixed (1593):** 2020 > 2024 split bar list: names at x 52-77 and bars from x 83, the same as the bar list (Chromium 390, 320, 1024x576, 1024x768 on 1593; WebKit 390 on 1594). Was 90-115 / 121 on 1592. `tests/list-name-x.py` on live: 27/27.
- **QA-080 fixed (1593):** nationwide US House list first row "DE At-large" (title "Delaware at-large"); DC's list still "At-large". Chromium 5 sizes.
- **Orchestrator verify list still holds (1593/1594):** with '16 selected the US House map is 27% blue / 73% red by pixel share, PA counties/US House/state senate/state house 24-27% blue (no gray maps); Philadelphia, Allegheny and Lackawanna blue, Lancaster, Westmoreland, Erie and Clearfield red; statewide '16: CA, NY, IL, CO, VA, WA blue, TX, OH, KS red, FL, PA, MI, WI pale pink (margins under 1.2 points, as in pass 20). Thumbnails at '16: US Clinton 48% / Trump 46%, PA Trump 48% / Clinton 47%. **PA '16 bar** 48.2% / 47.5% / Other 4.4% and **pie** 48.2% / 47.5%, both still drawn after '16 > '24 > '16 (1594, Chromium 390; official 48.18 / 47.46). '24: 50.4 / 48.7 (official 50.37 / 48.66). Sort chip at x 288-322 (390), just left of the button column. List rows number-only (PA US House 1, 4, 17; senate 10, 12, 16), DC "At-large", bars right after the names. Thumbnails on the topic-icon axis within 1 px in every view checked (Chromium 5 sizes). Menus are overlays: pie rect unchanged, `#chartDim` transparent, no tinted layer (Chromium 5 sizes, US and Alabama). Shots: shots/b1594p21-ch-390-PA-{bar,pie}-16b.png, shots/b1592p21-ch-390-own-US-2016.png
- **5-size smoke flow (Chromium and WebKit, touch):** no console errors, page errors, failed requests or HTTP errors; CLS 0. Institution menu, All States, sort flip, % / #, time row, range, chart menu (split bar, line; pie offered on a single place), drill to state > county > towns > precincts and Back, district-type menu, reload (restores PA > Philadelphia list, bar, #, 2024) and the White House address (field shows "1600 PENNSYLVANIA AVE NW, WASHI…") all work. Geo field + Enter still works on 1594.
- **Layout sweep** (Chromium 390 and 1024x768, WebKit 390; ran on 1593): the same as pass 20, nothing new: slider, top fields, right buttons and bottom bar did not move on year changes, drill-ins or Back. Still QA-054 (thumbnails dy −3/+3 on map/list), QA-058 (+23 px in the plain range list), QA-057 (chart button hidden while the layers row is open; crumb Worcester County > Massachusetts on US House). At 1024x768 the first MA county row came in at y 200 and settled at 202 300 ms after the drill-in (2 px, once; did not reproduce in 4 more drill-ins at 390 or 1024x768 in `p21-fr.py`). Data: `qa/b1592p21-layout-*.json`
- **Still open, unchanged:** QA-005 (US House from the Philadelphia townships list: 0 rows, Chromium all 5 sizes; WebKit from the Los Angeles County cities: 8 rows), QA-006 (Rockledge borough, 520 votes, still under Philadelphia County on 1593), QA-007 (All States row 86-148 ms Chromium, 121-208 ms WebKit; US House pick 88-129 ms WebKit in the list, 108-174 ms Chromium on the PA map), QA-020 (WebKit Back from the Los Angeles County cities to the California counties 393-453 ms at all 5 sizes; Chromium Back 21-31 ms), QA-076 (bubble x 6-116 over the photo at x 12-42 on phones, x 316-426 on iPad, both engines), QA-003 (same per-state gaps: ME 2020 Biden −4,599, NY 2020 +13,901, PA 2020 +1,694, VA 2024 +1,617; `qa/p21-cmp.log`), QA-013 (the longest split bar runs under the clock button, e.g. NY +5.9 at 375 and CA −1.83M at 320), QA-012 (phone # rows: Philadelphia shows only 569K).
- **Not covered this pass:** the full verify script on 1594 at 375x667 / 1024x576 / 1024x768 and WebKit menus; the layout sweep on 1594; a close look at 1594's clearer floating buttons and opaque text fields (they looked fine in the screenshots).

### QA-082 [Fixed on 1594 (header band removed)] [HIGH] List rows and sort chip bounce 6 px up and down every 300 ms while the list rests at some scroll positions (Chromium)
- Build 1593 (and probably 1590-1592, which had the same header band) | Chromium 390x844, 1024x768, 320x568 | Not checked in WebKit on 1593 (the WebKit run already got 1594)
- Steps: All States list (2024, bar %) > scroll the list a little: a touch drag of 60 px (list rests at 70 px), or a scroll offset of 10, 40 or 97 px > stop touching.
- Expected: once the list stops, nothing moves.
- Actual: the sort chip goes 111 > 105 > 111 and every row 6 px up and down, about every 300 ms, nonstop (11 changes in 3 s at every size). At a 25 px rest it was stable. Looks like the header band's padding/clip fighting Chromium's scroll anchoring. Gone on 1594 at all three sizes (stable at every stop).
- Shot: none (motion only; a still image doesn't show it). Data: `qa/p21-jit-1593.txt` (per-frame values), `qa/b1594p21-jit-chromium.json` (1594, stable)

### QA-083 [Fixed on 1595 (verified pass 22)] [HIGH (layout jump rule), small] Sort chip jumps up 2-5 px when the list stops about 22-26 px down
- Build 1594 | Chromium 390x844, 1024x768, 320x568; WebKit 390x844
- Steps: All States list > drag the list up 40 px (it rests at 25 px), or set the list's scroll offset to 22-26 px.
- Expected: the chip stays at its spot (top 111) at every scroll position.
- Actual: the chip's own `top` style changes to 109 px at 22 and 106 px at 25 (moves up 5 px) and stays there until the list is scrolled further; at 0-20 and 28+ it is 111 again. The rows don't move. Same in both engines.
- Shot: shots/b1594p21-ch-390-drag-chip.png. Data: `qa/b1594p21-jit-chromium.json` (`drag40`), `qa/p21-chiptop-1594.txt`

## Re-test status, builds 1588 / 1589 (pass 20, live line 9 = 202610181589; Oct 18 ~6:58-7:35 PM EDT)
- Builds since pass 19: 1588 (`5a7711c`: thumbnails on the topic-icon axis in every view, list-all exits on the map at every level, High to low ranks by total votes, district-type rows show only the number with At-large for 0/AL) and 1589 (`4245b05`, CRITICAL: '16 district maps coloured by the 2016 margin). Live switched to 1589 mid-pass; the 1589-specific checks below ran on 1589. No v3 preview or live URL yet. Box load 1-5.
- **2016 colours (CRITICAL) fixed on 1589, verified by touch in Chromium and WebKit 390x844 and Chromium 1024x768:** with the slider on '16, the US House map, Pennsylvania counties, PA US House, PA state senate and PA state house all show blue in Philadelphia and Pittsburgh and red in rural central PA and Lancaster (pixel samples at zoom 9; none gray). Statewide '16 map: CA, NY, IL, CO, VA, WA blue; TX, OH, KS red; FL, PA, MI, WI pale pink, as expected for margins under 1.2 points. Thumbnails at '16: US Clinton 48% / Trump 46%, PA Trump 48% / Clinton 47% (official 48.2/46.1 and 48.2/47.5). The orchestrator's `tests/colors-2016.py`, pointed at the live site, also passes in both engines (24/24). Data: `qa/b1589p20-col16-*.json`, `qa/p20-o-colors16-*.log`. Shots: shots/b1589p20-{ch,we}-390-col16-*.png, shots/b1588p20-ch-390-own-{US,PA}-2016.png
- **1588 thumbnail axis verified:** thumbnails centred on the row icon within 1 px on the US map, US list, bar and pie, US House map at '16/'20/'24, PA map and list, Allegheny map, PA US House map and list, PA state senate list, DC US House list (Chromium 5 sizes by touch, WebKit 390 and 1024x768; `tests/thumb-axis.py` on live: 42/42 in both engines).
- **1588 list-all exit verified:** PA > US House > list > map and PA > State senate > list > map, and DC > US House > list > map: the thumbnails come back and `body.listall` is off (Chromium 5 sizes, WebKit 390 and 1024x768).
- **1588 district labels verified:** PA US House rows read 1, 4, 17, ...; PA state senate rows 10, 12, 16 (no "District 0xx"); DC's row reads "At-large"; Alaska and Wyoming read "At-large"; bars start right next to the number. `tests/district-number-labels.py` on live: 168/168 in both engines. See new QA-080 for the nationwide list.
- **1588 High to low by total votes verified:** All States 2024 order CA 15.86M, TX 11.38M, FL 10.89M, NY 8.20M, PA 7.03M, OH, NC, MI; 2016 order CA 14.18M, FL 9.42M, TX 8.97M, NY 7.72M, PA 6.17M, IL, OH, MI (matches the official totals). One candidate toggled on ranks by that candidate (2016 Trump only: TX, FL, CA; Clinton only: CA, NY, FL). `tests/list-sort-total.py` on live: 30/30 in both engines.
- **QA-078 fixed (HIGH):** All States > 2020 > 2024 > split bar: change bars share one scale (NY +5.9 longest, CT +2.7 about half). Shot: shots/b1588p20-ch-390-new-sort-range-gbar.png
- **QA-044 fixed:** the sort chip no longer covers any first-row bar or label in bar %, bar #, range bar, split bar, line and line # lists at 390, 375 and 320 (Chromium). Data: `qa/b1588p20-new-chromium-*.json`
- **5-size smoke flow, Chromium and WebKit (touch):** no console errors, page errors or failed requests; CLS 0; slider, top fields, right buttons and bottom bar still don't move on year changes, drill-ins or Back (layout sweep Chromium 390 and 1024x768, WebKit 390). Menus open as overlays.
- **Still open, unchanged:** QA-054 (thumbnails dy -3/+3 on map/list), QA-058 (+23 px in the plain range list), QA-057 (chart button hidden while the layers row is open), QA-076 (bubble x 6-116 phones, 316-426 iPad), QA-077 (US 2020 > 2024 chart still shows the old "Republican +3.1 pts" block), QA-005 (US House from the Philadelphia precincts list: 0 rows, Chromium all sizes; WebKit from Los Angeles cities lists 8 rows), QA-007 (All States row 76-121 ms Chromium, 106-152 ms WebKit), QA-006 (Rockledge borough under Philadelphia County), QA-079.
- **QA-020 changed (WebKit only):** the flow now drills the first row (California > Los Angeles County > its cities, because High to low ranks by total votes), and Back from the Los Angeles County cities to the California counties takes 430-473 ms at all 5 sizes. Chromium Back on its path (Philadelphia) is 26 ms.

### QA-080 [Fixed on 1593 (verified pass 21)] [LOW, question] Nationwide US House list: at-large seats read "DE-00", not "At-large"
- Build 1588/1589 | Chromium 390x844, 375x667, 320x568, 1024x576, 1024x768; WebKit 390x844, 1024x768
- Steps: US map > district-type button > US House > globe (list).
- Expected (orchestrator's item: "at-large districts and DC labelled 'At-large'"): the at-large seats read e.g. "DE At-large".
- Actual: the first row reads "DE-00" (title "Delaware district 00"). State lists already read "At-large" (DC, AK, WY), so only the nationwide list differs. May be intended since nationwide rows need the state; flagging so it's a decision.
- Shot: shots/b1588p20-ch-390-own-DC-ushouse-list.png (DC's state list, for comparison). Data: `qa/b1588p20-own-*.json` (`us_rows`)

### QA-081 [Fixed on 1593 (verified pass 21)] [MEDIUM] Split bar list: bars start about 40 px further from the thumbnails than in the bar list
- Build 1588/1589 (same on 1587) | Chromium 390x844
- Steps: All States list > bar (bars start at x 82, names left-aligned at x 52) > time row 2020 > 2024 > split bar.
- Expected: bars start right next to the names, as in the bar list and the new district-number lists.
- Actual: in the split bar list the state names move to a right-aligned column at x 89-107 and the bars start at x 121, leaving about 45 px of empty space after the thumbnails; the names and bars jump right when switching bar > split bar.
- Shots: shots/b1588p20-ch-390-new-sort-bar-pct.png, shots/b1588p20-ch-390-new-sort-range-gbar.png

## Re-test status, build 1587 (pass 19, live line 9 = 202610181587; Oct 18 ~5:57-6:30 PM EDT)
- Builds since pass 18: 1586 (`ec95444`: '16 charts blank after returning to '16, menus are overlays with no dim, QA-060 icons re-measured, QA-070 clock button) and 1587 (`0c711df`: list sort chip at the right end of the bar area). No v3 preview or live URL yet. Box quiet (load 1-2).
- **QA-070 fixed (HIGH):** US map > time row > geo button > All States: `#bTime` no longer leaves its spot in any frame (Chromium 390 and 1024x768, WebKit 390; only the geo field moves, as the full-screen menu opens). Data: `qa/b1587p19-layout-*.json` step 25.
- **QA-060 fixed (HIGH):** map > list and list > map at MA > Worcester County: no transient icon positions in any frame (Chromium 390 and 1024x768, WebKit 390). Was 50 px wide for 550-620 ms on 1585. Data: same files, steps 9 and 17.
- **1586 '16 chart fix verified (Chromium 390):** Pennsylvania and Alabama, bar and pie, '16 > '24 > '16 > '20 > '16: the chart is drawn at every step. Data: `qa/b1587p19-new-chromium-iphone390.json` (`y16_*`).
- **1586 menus verified (Chromium and WebKit, all 5 sizes, US and Alabama):** with the pie showing, opening the district-type menu or the chart menu leaves the pie at the same rect, `#chartDim` is transparent and no tinted full-screen layer appears. Taps 5-26 ms. Data: `qa/b1587p19-menus-{chromium,webkit}.json`, shots shots/b1587p19-*-menus-*.png.
- **1587 sort chip:** same spot in every list mode (bar %, #, range bar, split bar, line); it moves only with the time row, as specced, and is never under a floating button (5 sizes Chromium, WebKit 390). But see QA-044 (changed).
- **5-size smoke flow, Chromium and WebKit (touch):** no console errors, page errors or failed requests; CLS 0; reload restores PA > Allegheny list, bar, #, 2024; the DC address opens DC. DC > School districts / US House still show DC's own 90% / 6% (QA-072 stays fixed). "Georgia", "Texas", "Washington" + Enter open the US states (QA-075 stays fixed).
- **Layout sweep 390 (Chromium, WebKit) and 1024x768 (Chromium):** slider, top fields, right buttons and bottom bar did not move on year changes, drill-ins or Back. Still: QA-054 thumbnails dy -3/+3 on map/list, QA-058 +23 px in the plain range list (at 1024x768 the icons also narrow 300 > 123 px over 95 ms), QA-057 chart button hidden while the layers row is open. (WebKit steps 26-32 skipped: harness could not find the MA row, as in pass 17.)
- **Still open, unchanged:** QA-076 (bubble x 6-116 on phones, 316-426 on iPad), QA-077 (US 2020 > 2024 chart still shows the old "Republican +3.1 pts" block below the icons), QA-078 (split bar rows each full width: NY +5.9 and CT +2.7 the same length), QA-005 (US House from the Pittsburgh towns list: 0 rows, Chromium all sizes), QA-007 (All States row 70-113 ms Chromium, 104-169 ms WebKit), QA-020 (WebKit Back from Harris County towns 268 ms at 390), QA-003.
- Shots: shots/b1587p19-ch-390-chart-us-range.png, shots/b1587p19-ch-390-chart-list-gbar.png, shots/b1587p19-ch-390-chart-bubble.png

### QA-044 [Fixed on 1588 (verified pass 20)] [Changed on 1587] Sort chip now sits on the first row's bar end in split bar and range bar lists
- Severity: MEDIUM | Build 1587 | Chromium 390x844, 375x667, 320x568; WebKit 390x844 (touch). Not seen at 1024x576 / 1024x768.
- Steps: All States list > time row 2020 > 2024 > chart button > split bar (also: range bar at 375; back to '24 in split bar at 320).
- Expected: the chip clear of every row's bars and labels.
- Actual: chip at x 288-322 (390), 273-307 (375), 218-252 (320), y 119-141, on top of NY's red split bar (bar to x 347 / 334 / 286). At 375 in the range bar list it also covers the top of NY's "−4.5" label (label x 256-278, y 139-150). At 320 after going back to '24 it sits on WY's red bar end. The old "−1.83M under the chip" in the range line list did not reproduce in % mode (the chip is now right of the lines); # mode not re-checked.
- Shots: shots/b1587p19-ch-390-new-sort-range-gbar.png, shots/b1587p19-ch-375-new-sort-range-bar.png, shots/b1587p19-ch-320-new-sort-back-2024.png, shots/b1587p19-we-390-new-sort-range-gbar.png
- Data: `qa/b1587p19-new-*.json` (`iss`, `sort_seen`)

### QA-079 [Fixed on 1592 (verified pass 21)] [LOW, question] Turning the chart off from a chart opened on the map leaves an almost empty gray list instead of the map
- Build 1587 (same on 1585, checked on a local copy) | Chromium and WebKit 390x844 and 1024x768, US and Alabama, bar and pie
- Steps: fresh load (US map) > chart button > Bar (or Pie) > chart button (menu opens) > chart button again.
- Expected: hunch only: back to the map the user started from (the spec says picking a chart opens the list view, but says nothing about turning it off).
- Actual: the chart turns off, the map stays hidden and the screen is gray with just the two thumbnails (the place's list view with no rows). This state is saved, so a reload comes back to the same gray screen; one globe tap brings the map back.
- Shots: shots/b1587p19-ch-390-chartoff-US-bar.png, shots/b1587p19-ch-390-chartoff-reload.png, shots/b1587p19-ch-390-chartoff-globe1.png
- Data: `qa/b1587p19-chartoff-{chromium,webkit}.json`

## Re-test status, build 1585 (pass 18, `5a0df17`, live line 9 = 202610181585; Oct 18 ~4:55-5:35 PM EDT)
- No v3 preview or live URL yet. Box quiet (load 1-4).
- **QA-072 fixed (Critical, verified Chromium and WebKit 390x844 touch):** DC > School districts shows DC's own numbers (Harris 90% / Trump 6%) with one row "District of Columbia Public Sch… 90.3%"; DC > US House shows 90% / 6% and one row "District 00 90.3%". Official DC 2024: Harris 90.28%. Data: `qa/b1585p18-dcschools-{chromium,webkit}-390.json`, shots shots/b1585p18-{ch,we}-390-DC-*.png. (Minor: the DC delegate row is labelled "District 00".)
- **QA-075 fixed:** "Georgia" + Enter opens the US state (crumb Georgia, US House / State senate / State house / School districts buttons all visible). Washington, New Mexico and Texas also open the US states. Log `qa/p18-ga.log`, shot shots/b1585p18-ch-390-Georgia-layers.png.
- **New chart layout (1585), Chromium 5 sizes + WebKit 390 and 1024x768:** single-place bars sit on their thumbnail rows (centre within 3 px, start 6 px right of the icon), gray "Other" chip present, labels never under a button, pie fits between thumbnails and buttons and above the bottom field (272 px at 390, 370 px at 1024x576), list chart menu offers bar / split bar / line and never pie, no list row draws a pie, Other-chip bubble says "Other" and bubbles close after 3 s, thumbnail tap never toggles the candidate. No console errors. Taps 3-45 ms. Data: `qa/b1585p18-chart-*.json`.
- **5-size smoke flow, Chromium and WebKit:** no console errors, page errors or failed requests; CLS 0; reload restores the list, bar, #, 2024; DC address opens DC. (WebKit drill to PA was skipped by the harness: the chart menu was left open, and in WebKit the tap only closes it; not an app bug.)
- **Layout sweep 390 (Chromium, WebKit) and 1024x768 (Chromium):** same as pass 17: QA-054 dy -3/+3 on map/list, QA-058 +23 px in the plain range list, QA-057 chart button hidden while the layers row is open, QA-060 left column 50 px wide for ~550-620 ms on list > map. Slider, top fields, right buttons and bottom bar did not move on year changes, drill-ins or Back.
- **Still open:** QA-070 (`#bTime` off screen at (1336,488) for 258 ms Chromium 390 and at (3872,488) for 185 ms at 1024x768; not seen in WebKit this run), QA-007 (All States row 94-121 ms Chromium, 109-144 ms WebKit, 168-226 ms in the chart probe), QA-005 (US House from the Pittsburgh towns list: 0 rows, Chromium all sizes), QA-044 ("−1.83M" under the sort chip in the range line list at 390/375/320, both engines; also widened, see below), QA-020 (WebKit Back from Harris County towns to the Texas counties 268-447 ms), QA-003 unchanged.

### QA-076 [Fixed on 1597 (verified pass 25)] [MEDIUM] Chart view: the thumbnail's name bubble covers the photo and the bar's number (phone) or floats far from the photo (iPad)
- Build 1585 | Chromium 390x844, 375x667, 320x568, 1024x576, 1024x768; WebKit 390x844, 1024x768 (touch)
- Steps: fresh load (US, 2024) > chart button > Bar > tap Trump's thumbnail.
- Expected: the white "Donald Trump" bubble next to the photo (the code aims for 8 px right of the icon), not covering the photo or the 49.9% label.
- Actual: phones: the bubble sits at x 6-116, y 123-151, on top of the photo and the "49.9%" label. iPad: it sits at x 316-426 in the middle of the bar, 270 px away from the photo. Looks like it is placed from the wide `.cand` row box (318 px wide) instead of the photo.
- Screenshots: shots/b1585p18-ch-390-chart-bubble.png, shots/b1585p18-ch-1024x768-chart-bubble.png

### QA-077 [Fixed on 1591 (verified pass 21)] [MEDIUM] Range chart for one place: change bars are below the thumbnails with name labels, not on the icon rows
- Build 1585 | Chromium and WebKit 390x844 (all sizes in the chart probe)
- Steps: fresh load > chart button > Bar > time row: select 2020 > 2024.
- Expected (1585 note): range bars sit on their icon rows (Republican, Democratic, Other at 44 px steps), no name labels.
- Actual: the two thumbnails stay alone at the top; under them is the old block "Republican +3.1 pts / Democratic -2.9 pts / Other -0.2 pts / Change 2020 → 2024 / R+5.9 shift" with text labels, 100 px lower than the icons.
- Screenshots: shots/b1585p18-ch-390-chart-us-range.png, shots/b1585p18-we-390-chart-us-range.png

### QA-078 [Fixed on 1588 (verified pass 20)] [HIGH] Split bar list in a range: each row is scaled to its own biggest change, not one common scale
- Build 1585 | Chromium 390x844, 320x568 (seen in every row)
- Steps: All States list > time row 2020 > 2024 > chart button > split bar.
- Expected: change bars on one common scale for the whole list (spec rule, and the 1585 code comment says "the change on the list's common scale").
- Actual: every row's largest change is drawn full width: NY +5.9 (red) and CT −2.8 (blue) are both about 275 px long at 390, as are NJ −5.2, CA −5.0, RI −3.5, SC −3.1. Bar lengths can't be compared across rows.
- Screenshots: shots/b1585p18-ch-390-chart-list-gbar.png, shots/b1585p18-ch-320-chart-list-gbar.png

### QA-044 [Fixed on 1588; re-verified on 1590 and 1594 (pass 21)] (widened on 1585) Split bar list: the sort chip also covers the first row's red bar (+5.9 for NY) at 390 and 320
- Shots: shots/b1585p18-ch-390-chart-list-gbar.png, shots/b1585p18-ch-320-chart-list-gbar.png

## Re-test status, build 1584 (pass 17, Oct 18 ~3:55-4:20 PM EDT)
- Live build still 202610181584; no v3 preview or live URL yet. Box quiet (load 3-9), so the pass 16 carry-overs ran to the end.
- **5-size smoke flow, Chromium and WebKit (touch), all 5 sizes:** no console errors, page errors or failed requests; CLS 0 to 0.014 (the 0.014 is the range slider track on Chromium 390). Reload restores PA > Allegheny list, pie, #, 2024. The DC address goes to District of Columbia (294K Harris in the pie). Data: `qa/b1584p17-flow-{chromium,webkit}-.json`, shots shots/b1584p17-{ch,we}-*.png.
- **QA-007 improved, nearly fixed:** All States row 79-114 ms in Chromium and 105-123 ms in WebKit (was 253-431 ms on 1583). US House pick 56-81 ms in Chromium (fixed there) and 89-110 ms in WebKit (over 100 ms at 320, 1024x576 and 1024x768). One-off Chromium 375 values: institution menu 107 ms, drill to PA 123 ms. Every other tap 5-79 ms.
- **QA-070 changed (HIGH, longer now):** US map > time row > geo button > All States. `#bTime` leaves (334,122) for (1002,366) for about **228 ms** in Chromium 390 and for (1336,488) for about **340 ms** in WebKit 390 (dx +668..+1002, dy +244..+366, off screen), then comes back. On 1582/1583 it was 56-107 ms. Shots: shots/b1584p17-ch-390-ls25-geo-menu-all-states-{before,after}.png, shots/b1584p17-we-390-ls25-geo-menu-all-states-{before,after}.png. Data: `qa/b1584p17-layout-{chromium,webkit}-390.json` step 25 `transient`.
- **Layout sweep 390 (Chromium full, WebKit to step 25):** otherwise the same as pass 14/16: QA-054 thumbnails dy -3/+3 on map/list (Chromium also 50 px wide for ~520 ms on list > map), QA-058 +23 px in the plain range list, QA-057 chart button hidden while the layers row is open and crumb Worcester County > Massachusetts on US House. Slider, top fields, right buttons and bottom bar did not move on year changes, drill-ins or Back. WebKit steps 26-32 did not run because the harness could not find the MA row (not an app result).
- **Still open on 1584:** QA-072 critical (DC > School districts and DC > US House map show US 50% / 48% under "District of Columbia"; lists show 51 states / 436 House rows; shots/b1584p17-ch-390-DC-*.png), QA-075 ("Georgia" + Enter opens the country, no district-type buttons; shots/b1584p17-ch-390-Georgia-layers.png), QA-005 (US House from the Pittsburgh towns list: 0 rows, all sizes, both engines), QA-044 ("−1.83M" under the sort chip in the range line list at 390/375/320, both engines).
- **QA-003 unchanged** (`qa/cmp.py`): same per-state gaps as pass 5; national 2024 75,019,265 / 77,303,628 vs FEC 75,017,613 / 77,302,580.

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

### QA-075 [Fixed on 1585 (verified pass 18)] [HIGH] Typing "Georgia" + Enter in the geo field opens the country Georgia, not the US state
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

### QA-091 [Fixed on 1609 (verified pass 30); on 1608 saved the US view zoom 4] [MEDIUM] WebKit saves the map position as zoom 2 over Minnesota after a DC address search from a list view
- Build 1607, WebKit 390x844, touch. Filed per the orchestrator's ruling (Oct 19, 6:35 AM EDT).
- Steps: PA > Philadelphia townships list, tap the bottom field, type "1600 Pennsylvania Ave NW, Washington, DC 20500", press Enter, then reload or inspect the saved state.
- Expected: the saved map position is DC's (near 38.90, -77.04).
- Actual: the saved position is zoom 2 centred over Minnesota.
- Data: qa/b1607p29-addr-*.json.
- Ruled by design, not filed: after this search, All States shows a Back button that returns to Philadelphia County, because Back returns to the previous view.

### Orchestrator notes, Oct 19 ~9:35 AM EDT
- QA-103 is confirmed CRITICAL: reload must restore the exact selection.
- QA-100 and QA-101 (NY county data): Historic Election Data fixed them at f940021 on data/election, and the builder is merging it into main next. Once a build with it is live, recheck Kings County against Brooklyn borough and the NY state totals against FEC.
