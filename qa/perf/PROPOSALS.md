# Speed: top speed wins for build 1575 (measured)

Prototypes are local copies of origin/main 7a23208 (v2/index.html untouched on main), built by tools/build_proto.py and served by
tools/serve.py (GitHub Pages emulation: gzip, ETag, max-age=600). 390x844 (+320x568 for taps), Chromium, DPR 2, no throttling.
Raw: raw/proto-A.json, raw/proto-D.json, raw/proto-startup-ABC.json, raw/proto-startup-AC-detail.json, raw/prof-A.txt.

## 1. Move PACK + XREF (5.27 MB raw) out of index.html into a content-hashed pack.js, parsed with JSON.parse  [TESTED: B]
- Today v2/index.html is 5.92 MB raw / 915 KB gz; lines 678 (`const PACK = {...}` 4.18 MB) and 683 (`const XREF = {...}` 1.09 MB) are inline object literals.
- Change: delete lines 678 and 683 from the big inline `<script>`, add `<script src="pack.js?v=<sha1-of-content>"></script>` right before it.
  pack.js = `const PACK = { lists: JSON.parse('<lists JSON>'), geom: {...} }` and `const XREF = JSON.parse('<xref JSON>');` (top-level consts stay global, so no other code changes).
- Measured (median of 3, cold cache): DCL 1013 -> 347 ms (-66%), first map 777 -> 492 ms (-37%), long-task total 568 -> 285 ms, load 1066 -> 623 ms. Cold bytes unchanged (index 198 KB gz + pack.js 705 KB gz).
- Also makes the 705 KB gz pack cacheable across builds (it changes only when the lists change); index.html drops to 198 KB gz per build.

## 2. Version data files by content (or a data version), not window.BUILD  [TESTED: C = B + this]
- Every loader builds `"?v="+window.BUILD` (42 places, e.g. loadState `"../data/"+STATE_FILES[st]+"?v="+window.BUILD`, loadPrecincts, loadNat, loadCD, loadDS, usstates/ctryshape/canada...). BUILD changes on every push (5 pushes in 3 h today), so every returning user re-downloads all data even when nothing changed.
- Prototype: `window.DATAV="<hash>"` next to window.BUILD and `?v=`+window.DATAV in those 42 URLs (regex in build_proto.py). Production version: per-file hash map written by the build script.
- Measured, repeat visit after a build bump, PA session: A re-downloads 3.21 MB gz (index 903 KB, data/Pennsylvania.js 837 KB, precincts2024/Pennsylvania.js 734 KB, uscounties 369 KB, ...); C downloads only index.html 198 KB gz (-94%). (The test server ignores the update checker's Range header, so it adds a 654 KB raw index re-fetch in B/C runs that GitHub Pages answers with a 2 KB 206; excluded here.)

## 3. List-all enter(): fit the map after the list paints, not inside the tap  [TESTED: D, part 1]
- Profile (raw/prof-A.txt): cold All States 266 ms, 124 ms of it in `fit()` -> `map.fitBounds(...,{animate:false})` -> Leaflet _resetView re-projecting every canvas path; same call is 150 ms of the US House pick and ~120 ms of back.
- Change, v2/index.html line 3687 (end of `async function enter()`):
  `... try{ layoutSide(); }catch(e){} fit(); }` -> `... try{ layoutSide(); }catch(e){} requestAnimationFrame(()=>setTimeout(fit,0)); }`
- Measured A -> D (5 tries): All States cold 250 -> 87 ms (390), 230 -> 86 ms (320); median 122 -> 53 / 78 -> 50 ms. Final map view identical (zoom/center recorded: [2, 48.225, -94.219] US, [6, 41.133, -77.605] PA). US House pick cold 313 -> 139 ms at 320 but 336 -> 303 at 390; back mixed (noise). Patch: patches/D-tap-latency.diff.

## 4. US House pick: precinct->district aggregation runs inside the tap  [partly tested: D, part 2]
- 239 ms of the cold pick is `aggFor()` (line 1384): for every PA precinct it runs `pointInItem` on the precinct itself and then on candidate districts (200 ms self time in the ring loop, line 1072).
- D rewrote pointInItem lines 1072-1079 as indexed loops (no forEach closure / array destructuring, same even-odd + hole rule): helps only modestly. Real fix: precompute precinct->district ids offline in the precinct files (or warm `aggFor` in requestIdleCallback after loadPrecincts) so the pick is a table lookup. Not prototyped yet.

## 5. Other observations
- ussch.js (4.6 MB) and precincts2024/Alaska.js (3.7 MB) are already lazy on 1575: not fetched at startup nor in a PA session (ussch only for the School districts type; Alaska only with Alaska in view). No action needed for a PA session.
- data/Pennsylvania.js (v1 file, 2.35 MB raw / 870 KB gz) + precincts2024/Pennsylvania.js (2.22 MB / 761 KB) both load on the PA drill-in; the list shows only 67 county rows. Candidate: county list from election2024.js, precincts on demand.
- ~60 setInterval pollers (80-1500 ms, most doing getBoundingClientRect/getComputedStyle) run all the time: a source of random tap delay and idle battery drain. Worth consolidating (tools/idle.py measures it; not yet run).
- Liquid Glass/backdrop-filter: earlier run (/workspace/perf/perf1.log, 390, 4x CPU throttle) shows glass vs no-glass taps within noise (#bNum 32 vs 33 ms, sort 410-450 ms both), map pan ~30 fps both. Not a measurable tap cost in headless Chromium (iOS Safari GPU may differ).
- iPad 820x1180 pan is the weakest: 45 fps, p95 33 ms, 82 dropped of 241 frames (phones 57-60 fps).
