# BUGS: us-districts v2 (QA lane)

Tested: live https://ge0r9b.github.io/us-districts/v2/ , **build 202610181566** (`window.BUILD`, line 9 of the live v2/index.html).
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

## Critical

### QA-001 [Fix pending deploy (per orchestrator: fixed on data/election, ships with the 2016 build); still wrong on live 1569 at 6:55 AM EDT] Oregon 2024 state totals are short of the official count (~1%)
- Severity: Critical (wrong numbers) | Build 1566 | All sizes (data, seen in list at 1024x768)
- Steps: Institution filter > All States > `#` mode, 2024; find OR (or `__stTot('Oregon','2024')`).
- Expected (FEC 2024): Harris 1,240,600, Trump 919,480.
- Actual: Harris 1,228,410 (-12,190), Trump 910,702 (-8,778). List shows OR 1.23M / 911K instead of 1.24M / 919K.
- Screenshot: shots/chromium-ipad1024x768-allstates-2024-num.png

### QA-002 [Fix pending deploy (per orchestrator); still wrong on live 1569 at 6:55 AM EDT] Kansas 2020 state totals are short of the official count (~2%)
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

### QA-017 The same state shows different totals depending on the district type
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

### QA-023 Geo search "Pittsburgh" + Enter goes to East Pittsburgh borough
- Severity: Medium | Build 1568 | 390x844
- Expected: Pittsburgh city (the closest name, far more votes).
- Actual: the top suggestion and the Enter result is "East Pittsburgh borough, Allegheny County".
- Screenshot: shots/b1568-ch-390-geo-Pittsburgh.png

### QA-024 Universal search "Allegheny" + Enter: geo field and map do not follow
- Severity: Medium | Build 1568 | 390x844
- Actual: the institution becomes Allegheny County, but the geo field says "Clinton County, PA" and the map stays at zoom 6.
- Screenshot: shots/b1568-ch-390-search-Allegheny.png (suggestions; end state in `qa/gaps.log`)

### QA-025 Double-tap on the map zooms out and clears the state
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
