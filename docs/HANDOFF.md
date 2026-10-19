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
