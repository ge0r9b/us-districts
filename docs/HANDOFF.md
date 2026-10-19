# v2 handoff — Oct 19 2026, 5:35 PM ET

Live: Build 1618 (main). This branch (handoff/2026-10-19) = 1618 + 11 UNTESTED commits for QA-115/QA-113 (city/county search ranking, ST suffix, county entry zoom, touch submit). Test (tests/heat-zoom.py, tests/geo-entry*, city list below) in WebKit+Chromium before shipping.

## Open queue (in order)
1. QA-115 CRITICAL: exact incorporated city wins (population), honor ", ST"; town pick shows the town's own title/numbers; #bGeo strict match. Test: Pittsburgh, Columbus, Cleveland, Portland, Springfield, Boston, Kansas City, Jackson, Richmond, Lancaster, Austin (bottom field + #bGeo).
2. QA-116 HIGH: bottom-field county pick (Fulton GA, Franklin OH, Lancaster NE, Jackson MO) must fly to county.
3. QA-113 HIGH: geo-filter button path leaves US House on.
4. QA-114 HIGH: FL-20 "no data" in '16 US House list (Bug Tester sweeping all districts).
5. QA-117 MED: list > map > list loses drilled-in list (Ohio > Franklin).
6. QA-112 ZIP from list -> precinct; QA-099 sort chip over first row; QA-074; QA-018; QA-105/106; QA-085 year-tap speed; slider 320px speed.
7. Glass tweak (user-approved, CSS only): unselected buttons slightly more opaque, 4-8px -webkit-backdrop-filter blur, thin highlight border; target iPhones of last 2 years; no fps regression.
Pending user decisions: QA-089 placement, compact-bars (/workspace/w/prev) and shadows (/workspace/w/shad) previews.

## Rules
- v2 frozen: fixes only, no features/data. Mirror each fix to v3 (docs/v3/V2_PARITY_CHECKLIST.md on ge0r9b/v3).
- Certified state totals win; gaps <10k votes OK.
- Tag v2.0 only when BUGS.md has nothing open and full suite passes on a clean tree.
- /workspace/countries (5.1 GB foreign files) is the ONLY copy — never delete. Never delete scraped data meeting US rules.
- v3 migration 021_us_only was never applied; Full Stack is reverting it.


## Final status (Oct 19, ~5:55 PM ET, executor)
- Live: **Build 1618** (main, 581534cf). Nothing shipped after 1618.
- This branch (handoff/2026-10-19): 1618 + QA-113/115/116 commits, last code commit 9052ceed. NOT shipped.
  - Tested: tests/geo-entry.py, enter path, Chromium 390: 15 of 16 places pass (Pittsburgh, Columbus, Cleveland, Portland OR, Springfield MO, Boston, Kansas City MO, Jackson MS, Richmond VA, Lancaster CA, Austin, Portland ME, Kansas City KS, Fulton County GA, Franklin County OH; the county ones fly to the county = QA-116). 1 FAIL: 'Springfield, IL' resolves correctly but the title shows Sangamon County (Illinois parts have no Springfield town polygon).
  - The resolver probe (window.__geoResolve) gives the right city for all 18 test strings.
  - NOT yet run: WebKit for all paths; the #bGeo, button and row paths after commits 93a85313/9052ceed. The button and row paths passed earlier in Chromium and WebKit (before those two commits).
  - Before shipping as 1619: HOW=enter,bgeo,button,row python3 tests/geo-entry.py in both engines, plus field-after-pick, geo-stay, addr-search, heat-zoom and list-dc-globe (ZIP scenarios).
- Mirrored to v3: none yet. No SendToAgent was sent to Full Stack. No docs/v3/V2_PARITY_CHECKLIST.md was found in this repo (it may be on ge0r9b/v3). Mirror these once shipped: 1615 official totals, QA-104, borough labels; 1616 QA-097/105/106; 1617 QA-107/108; 1618 QA-111/109/110 + geo entry clears district type; branch QA-113/115/116.
- QA-114 finding: FL-20 '16 is gray on purpose. The data build leaves districts with <50% precinct cover without a value (data-v3/results/2016/README.md lists FL-20 plus 7 senate and 22 house districts). This is a data decision, not a code bug. A zero-no-data test is not written.
- Glass CSS tweak: not started (the button styles are in <style id="glassCss">; unselected = the :is(...) rule with blur(14px)).
- Open queue: finish and ship the branch, QA-117, QA-112, QA-099 (tests/chip-lists.py written; passes Chromium 390), QA-074, QA-018, QA-085, slider-open speed at 320, glass tweak.
- Team structure: see docs/TEAM.md.
