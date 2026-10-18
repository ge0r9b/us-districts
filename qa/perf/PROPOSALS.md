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

---
# aggFor: the first US House pick (build 1576, measured)

Where it goes: the first US House pick in the PA counties list takes 270-390 ms. About 240 ms of that is `aggFor()` (v2/index.html line 1384). For each of PA's 9,100 precincts it finds a centroid, checks it with point-in-polygon on the precinct itself and then on the candidate districts. Then it samples 16x16 points per district for coverage. The result is cached in `AGG[state|type|year]`, so only the first pick pays. Later picks are about 80 ms, mostly the list and map render.

Test: tools/ushouse.py on local copies of 615fa5a (tools/build_proto2.py, GitHub Pages-style server). Steps: All States, drill into PA, wait until PA precincts load, wait 4 s more (a user reading the list), open the type menu, then US House pick, deselect, pick (5 picks), then Back x3. Each session uses a fresh context. 3-4 sessions per variant and size (one F 320 session lost to a renderer crash on the busy box). Raw data: raw/agg.log, raw/agg-summary.json, raw/agg-wait0.json, raw/agg-correctness.json.

| variant | viewport | first pick (each session) | first pick median | later picks median / max | Back median / max |
|---|---|---|---|---|---|
| A2 as shipped | 390x844 | 270, 389, 289, 282 | **285** | 76 / 97 | 50 / 79 |
| E idle warm-up | 390x844 | 53, 73, 70, 41 | **62** | 83 / 151 | 61 / 102 |
| F build-time table | 390x844 | 84, 72, 61, 46 | **67** | 82 / 180 | 68 / 96 |
| A2 as shipped | 320x568 | 289, 298, 358 | **298** | 86 / 149 | 68 / 102 |
| E idle warm-up | 320x568 | 46, 51, 68 | **51** | 92 / 129 | 59 / 93 |
| F build-time table | 320x568 | 65, 115 | **90** | 102 / 163 | 73 / 105 |

- Same numbers: the A2, E and F aggregates for PA US House (dem, rep, tot, precinct count and coverage for all 17 districts) are identical (raw/agg-correctness.json).
- Back does not use aggFor. It is unchanged within noise (50-73 ms median). Its cost is the map fit (see proposal 3 / patch D).
- Tap almost right after the drill (raw/agg-wait0.json, wait 0, 390): A2 292 ms, E 50 ms, F 52 ms. E's job was not finished when we checked. The tap finished it synchronously and reused the work already done. Rows stay correct.

## (a) E: idle warm-up (patch: patches/E-aggfor-idle-warm.diff, replaces lines 1384-1402)
- `aggGen(k,yr,st,P,EL)` is aggFor's exact maths as a generator. It yields every 128 precincts (about 2 ms) and after each district's coverage sampling. At the end it stores `AGG[key]`.
- `aggFor(k,yr)`: cached result -> return it. Otherwise it takes over the running job `AGGJOB[key]` (or starts one) and runs it to the end synchronously. That is the fallback for a tap before idle finishes, and no work is repeated.
- `aggWarm(k)` steps the job in `requestIdleCallback` slices while `timeRemaining()>2`. iOS Safari has no requestIdleCallback, so the shim uses `setTimeout(60)` with an 8 ms budget per slice.
- Trigger: `loadPrecincts` is wrapped. After the state's precincts and state file load, it calls `aggWarm("ushouse")` if the state is still selected. Senate and state house could be warmed the same way; they are not, to save CPU and battery.
- Cost: no bytes. About 240 ms of CPU spread over idle slices after each state drill, even if the user never picks a district type. No main-thread task over about 10 ms.

## (b) F: build-time table (patch: patches/F-aggfor-buildtime-table.diff, added after aggFor; sample data raw/pxd-Pennsylvania.js)
- The build script would emit one file per state, `v2/data/pxd/<State>.js`:
  `__pxd("Pennsylvania",{"2024":{"ushouse":{"n":["13","03",...],"a":"a,a,3,.,...","cov":[1,0.998,...]},"senate":{...},"statehouse":{...}},"2020":{...}})`
  - `n`: district names in the state's GEOM order.
  - `a`: one base36 index into `n` per precinct row, in the precinct file's order. `.` means no district.
  - `cov`: coverage per district.
  - It is computed with the same centroid and point-in-polygon rules. tools/pxd_dump.js is the reference implementation; tools/pxd_make.py ran it in a browser for PA.
- The app fetches it next to the precinct file (wrapped `loadPrecincts`). `aggFor` then sums votes by table lookup. If the table is missing or doesn't match (row count or district names), it falls back to the geometric path.
- Byte cost: PA 2024 with 3 types is 67 KB raw / **8.9 KB gzip** (9,100 precincts). Extrapolated: about 170 KB gz for all states' 2024 tables (173k precincts) and about 160 KB gz for 2020 (163k). A user only gets their state's file (PA: about 9 KB per year, 1 extra request).
- The table must be regenerated whenever precinct rows, their order, or district geometry change. The row-count and name checks catch mismatches, which then fall back to the slow path.

## Recommendation
Ship **E now**. It is one self-contained change in index.html with no data pipeline and no bytes. It removes about 80% of the first-pick cost (285-298 -> 51-62 ms median) and stays correct for an instant tap. Add **F later**, when the data build is next touched, for senate/statehouse/2020 too. It is deterministic even with no idle time and costs no device CPU or battery. E then remains the fallback when a table is missing. Together with patch D (deferred map fit), every QA-007 first tap should land under 100 ms.
