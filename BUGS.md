# BUGS: us-districts v2 (QA lane)

Tested: live https://ge0r9b.github.io/us-districts/v2/ , **build 202610181566** (`window.BUILD`, line 9 of the live v2/index.html).
Date: Oct 18, 2026, ~5:40-6:20 AM EDT. Branch `qa/bugs` from `08d298c`.
Harness: Playwright (Python) 1.x, Chromium (isMobile + hasTouch, iOS UA) and WebKit (hasTouch, iOS UA). Scripts in `qa/` (`flow.py`, `cmp.py`, `nums.py`, `load.py`).
Official sources: FEC "Official 2024 Presidential General Election Results" (https://www.fec.gov/documents/5644/2024presgeresults.pdf, compiled from state election offices, Jan 16 2025) and FEC "Official 2020 Presidential General Election Results" (https://www.fec.gov/resources/cms-content/documents/2020presgeresults.pdf). PA and GA 2024 also confirmed against the PA DOS certification and GA SOS results pages.
Tap latency = touch/pointer event timestamp -> first rAF + task after it (headless approximation of tap-to-next-paint). Flag > 100 ms.

Severity: **Critical** = wrong numbers, crashes, broken buttons/flows. High = spec violation that breaks a flow. Medium = visible spec violation. Low = polish.

## Critical

### QA-001 Oregon 2024 state totals are short of the official count (~1%)
- Severity: Critical (wrong numbers) | Build 1566 | All sizes (data, seen in list at 1024x768)
- Steps: Institution filter > All States > `#` mode, 2024; find OR (or `__stTot('Oregon','2024')`).
- Expected (FEC 2024): Harris 1,240,600, Trump 919,480.
- Actual: Harris 1,228,410 (-12,190), Trump 910,702 (-8,778). List shows OR 1.23M / 911K instead of 1.24M / 919K.
- Screenshot: shots/chromium-ipad1024x768-allstates-2024-num.png

### QA-002 Kansas 2020 state totals are short of the official count (~2%)
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

## High

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

## Medium

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

## Low

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
