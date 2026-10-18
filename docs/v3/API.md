# v3 API design (Phase 1 plan)

Base: `/api/v1`. JSON (UTF-8), gzip/brotli. Read-only for the public. All IDs are stable **keys** (`contest_key`, `unit_key`, `answer_key`, `candidate_key`), never database surrogate ids, so URLs survive reloads.

## Versioning
- **API version** is in the path (`/api/v1`). Additive changes (new fields) stay in v1. Breaking changes go to `/api/v2`, and v1 is kept for at least 6 months.
- **Data version**: `dv` (integer, increments on every data load) and per-boundary-set `bv`. Every response includes `"dv"`. Clients pin `?dv=` from `/manifest`, which makes responses immutable and lets the CDN cache them for a year (ARCHITECTURE.md §5).
- A pinned `dv` that is no longer current still answers (old packs are kept 90 days), or returns `410 Gone` with the current manifest.

> Example numbers: the Pennsylvania / Erie / Fulton County 2024 values are copied from the v2 flat export (`/workspace/db/export/results/county.csv`, official county totals from `data/election2024.js`), with `other = total − dem − rep`. The key formats (`PA|Erie County`, `ushouse:PA:16`, `senate:PA:009`, `statehouse:…`, `schools:PA:Erie City School District`) are the ones that export uses. Placeholders in `<…>` are illustrative.

## Common conventions
- Errors: `{"error":{"code":"unit_not_found","message":"…"},"dv":42}` with 400/404/410/429/500.
- Format follows v2's rule (spec §8): **# mode returns no shares, % mode returns no counts** when `fmt=pct|num` is passed. Without `fmt`, both are returned and the client hides one. The client should omit `fmt` so a %/# toggle needs no new request.
- Estimates: every value has `est: true|false`. The client shows ≈ (spec §3, v2 `est`).
- `coverage < 0.5` means `gray: true`; the client colours it gray (v2 rule).
- Lists are returned **already sorted high → low** by the requested answer (v2 default: "High to low"; rows without data last, alphabetical). The client flips direction locally with no request (v2 build 1564 moves existing rows).

## Endpoints

### `GET /manifest`
The current data and boundary versions plus pack and tile URLs. Fetched once at load.
```json
{"dv":42,"built_at":"2026-10-18T09:00:00Z",
 "tiles":{"state-2024":"/tiles/state-2024@1.pmtiles","county-2024":"/tiles/county-2024@1.pmtiles",
          "precinct-2024":"/tiles/precinct-2024@3.pmtiles","sldl-2024":"/tiles/sldl-2024@1.pmtiles"},
 "packs":"/packs/42/{contest_key}/{unit_type}.json",
 "offices":[{"key":"president","label":"President","scope":"us"}]}
```
Cache: `public, max-age=60, s-maxage=60, stale-while-revalidate=600`.

Alpha.3 adds `tiles["precinct-2024"]` = `/tiles/precinct-2024/{ST}.pmtiles` and `precinct_packs` = `/packs/precinct/{ST}/{year}/{office}/{sha}.json`. `GET /results?unit_type=precinct&state=VT&contest=2024|US|president|` reads that pack and returns the same row shape. `GET /packs/precinct/{state}/{year}/{office}` redirects to the hashed file. Precinct result rows are not in Postgres.

### `GET /contests`
Filter: `year`, `office`, `state`, `district`, `kind` (candidate|measure|poll), `stage`, `entity` (institution key), `q` (text), `limit`, `cursor`.
```json
{"dv":42,"items":[{"key":"2024|US|president|","office":"president","label":"President","year":2024,
  "date":"2024-11-05","stage":"general","kind":"candidate","state":null,"district":null,
  "answers":[{"key":"dem_nominee","label":"Harris","candidate":"harris-kamala-d","party":"dem","color":"#2563eb"},
             {"key":"rep_nominee","label":"Trump","candidate":"trump-donald-j","party":"rep","color":"#dc2626"},
             {"key":"other","label":"All other","aggregate":true}],
  "unit_types":["state","county","precinct","ushouse","sldu","sldl","school_unified","school_elementary","school_secondary"],
  "categories":["state","county","precinct","congressional","legislative_upper","legislative_lower","school_district"]}],
 "next":null}
```

### `GET /contests/{contest_key}`
One contest with its answers, candidates (name, photo, credit), sources and licenses (for attribution), and coverage per unit type.

### `GET /officeholders` and `GET /people/{person_id}`
`/officeholders?entity=chamber:pa-lower&unit=<key>&boundary_set=<slug>&date=2026-10-18` (or `unit_layer=sldl&geoid=42101&unit_vintage=2024`) returns who held the seat on that date (or `from`/`to` for a range): `[{person_id, name, party, status, valid_from, valid_to, source}]`, with vacancies as `person_id: null, status: "vacant"`. `/people/{person_id}` accepts a canonical ID (`bioguide:B001323`, `ocd-person:<uuid>`, `vt-leg:vt-41827`) or any alias, and redirects (301) from an alias to the canonical ID. Cache: `s-maxage=86400` (rosters change rarely; pinned by data version).

### `GET /results`
Results for a contest by unit.
Params: `contest` (required, repeatable: any number of years, e.g. `contest=2016|US|president|&contest=2020|US|president|&contest=2024|US|president|` for a 3-point time slider or a delta), `unit_type` (required), `state`, `parent` (unit key, for drill-down), `units` (comma list of keys), `boundary_set` (slug, e.g. `v2-2024`; default = the contest's set for that `unit_type`; geometry and `unit_id`s are matched on it, not on year), `fmt`. Office tokens include `president`, `us_senate`, `us_senate_special` and `us_senate_runoff` (GA 2022). Each contest in the response carries `display_slots: {"d": answer_key, "r": answer_key}` for the v2-parity D/R/total view (DATA_LOADING §12); all answers are still returned, and colour follows party.
```json
{"dv":42,"contest":["2024|US|president|"],"unit_type":"county","answers":["dem_nominee","rep_nominee","other"],
 "rows":[{"unit":"PA|Erie County","name":"Erie County","votes":[67456,68866,1273],"total":137595,
          "share":[0.4903,0.5005,0.0093],"est":false,"gray":false}]}
```
The same data is pre-built as a static **pack** for every past contest × unit type (ARCHITECTURE.md §4.3). The client tries the pack URL first and calls `/results` only for combinations that are not pre-built.

**Alpha.1 shape.** `unit` is the Census GEOID (`42`, `42049`, `4201`). The v2 name (`Pennsylvania`, `Pennsylvania|Erie County`) is `legacy` on the same row. One `contest` matches the flat example above. Two or more contests return `series` on each row (one cell per contest, same vote fields) instead of a single `votes` array. The machine-readable contract is [openapi.yaml](openapi.yaml). CORS is `*` and `Authorization` is allowed; alpha.1 sets no cookie.

### `GET /aggregate`
Bar-list rows for a scope, **sorted high to low**. This is the endpoint behind list-all and the list view's bars.
Params: `contest` (1, or 2+ for delta/range: the first and last selected years define the delta), `scope` (unit or entity key: `us`, `PA`, `PA|Erie County`, `chamber:pa-lower`), `child_type` (a unit type, or a category such as `school_district`, which lists all three school types as one list, as v2 does), `sort_answer` (answer key; default = the selected answer, else the leader), `sort` (`share`|`votes`|`delta_margin`), `dir` (`desc` default | `asc`), `fmt`, `limit`, `cursor`.
```json
{"dv":42,"scope":{"key":"PA","name":"Pennsylvania","total":{"votes":[3423042,3543308,67856],"est":false}},
 "child_type":"county","sort":{"answer":"rep_nominee","by":"share","dir":"desc"},
 "rows":[{"unit":"PA|Fulton County","abbr":null,"votes":[1102,7039,36],"share":[0.1348,0.8608,0.0044],
          "rank":1,"est":false,"gray":false}],
 "no_data":[{"unit":"…","name":"…"}]}
```
Rules carried over from v2:
- Delta sort (`sort=delta_margin`) orders by the **magnitude** of the net margin change as displayed (% mode = points, # mode = vote margin), ignoring which party gained (spec §7.3, build 1530).
- For school districts, state house and state senate, scope `us` returns states first, a state returns counties, and a county returns its districts. A district spanning counties appears under each county with whole-district numbers and `est:true` (spec §7.3). US House at `us` returns all 435 (HANDOFF §4).
- States in list-all use two-letter abbreviations (`abbr`) (HANDOFF §3).
- Rows without an earlier side return the real later value with `"prev":null`, which the client shows as `'20 n/a` (spec §7.3), or `'16 n/a` for 2016 in the 3-point slider.
Served from `answer_share` (an index range scan; SCHEMA.md). Cache as `/results`.

### `GET /units/{unit_key}`
Name, type, parent chain (breadcrumb), bbox, centroid, the institutions linked through `entity_unit`, and a results summary for the requested `contest`. This is the source for map pop-ups. Pop-up numbers must equal list numbers (v2 test `district-consistency.py`).

### `GET /entities/{entity_id}` and `GET /entities/{entity_id}/children`
`entity_id` is the registry's opaque id (`state:42`, `county:01001`, `chamber:pa-lower`, `chamber:ne-upper`, `chamber:dc-council`, `school:4218990`, `us-house`, `nation:us`); a merged-away id answers 301 to the survivor (`entity_merge`). Brands and organizations (e.g. `wikidata:Q1046951`; a former QID or a re-keyed `usd:` id redirects to it; `lei:`/`cik:` are never accepted on the public API) add `?rel=parents|brands` (from `entity_relation`, current by default, `as_of=` for history) and `locations` (HQ + establishments, `?bbox=` or `?unit=` via the GIST index). Institution filter: children of US (states, plus district-type rows), of a state (counties, or a chamber's districts), and so on. Each item has an icon descriptor (flag or type icon; v2 HANDOFF §3).

### `GET /search?q=&scope=&types=`
Unisearch over entities, units, aliases, candidates, offices and ZIPs (pg_trgm plus alias prefix). A government-and-place entity returns two rows, `institution` and `place` (spec §5.3). A state abbreviation or name ranks the state first (`state_abbr_search.py`). p95 target 80 ms (PERFORMANCE.md).

### `GET /geocode?q=` and `GET /locate?lon=&lat=`
`/geocode` turns an address into a point (Census one-line, then Census components, then Nominatim) and then runs `/locate`. `/locate` is a PostGIS `ST_Covers` point-in-polygon against every current public boundary set.
```json
{"dv":42,"query":"…","point":{"lon":<lon>,"lat":<lat>},"match":"exact","provider":"census",
 "units":{"state":"PA","county":"PA|Erie County","county_subdivision":"PA|Erie County|<town>",
          "precinct":"PA|Erie County|<precinct id>","ushouse":"ushouse:PA:<nn>",
          "sldu":"senate:PA:<nnn>","sldl":"statehouse:PA:<nnn>","school":"schools:PA:<district name>"}}
```
Cache: `/locate` is `public, s-maxage=86400` on coordinates rounded to 5 decimals. `/geocode` is `private, max-age=3600`.

### `GET /locations?bbox=` and `GET /locations/clusters?bbox=&z=`
Company sites inside `west,south,east,north`. `country_code` is the ISO alpha-2 from the companies file. Clusters snap points with `ST_SnapToGrid`. The same points are a clustered PMTiles archive at `/tiles/companies.pmtiles` (manifest key `companies`) when `db:load --include=companies` has been run. Cache follows the versioned `/api/v1` rules.

### `GET /tiles/{set}/{z}/{x}/{y}.mvt` (fallback only)
Dynamic vector tiles via `ST_AsMVT` for custom or private boundary sets. Public sets use static PMTiles. Cache: `public, max-age=86400, s-maxage=31536000, immutable` when `bv` is pinned.

### `GET /sources?contest=&state=`
Provenance and licences for attribution and the commercial-readiness tracker (spec §9.3).

## Not in v1 (reserved)
- `POST /votes` (live user votes, Auth, one vote per user per topic; spec §10.3)
- Tenant endpoints for custom boundary sets (`/tenants/{t}/boundary-sets`, upload, re-tabulate)

### Submissions (phase 3+, needs auth: DECISIONS D18; not in v3.0)
All require a signed-in user. Rate-limited per user and IP hash (429 with `Retry-After`). Responses are `Cache-Control: no-store`.
- `POST /v1/submissions`: one proposed entity / relation / location (`payload`, required `evidence_url`) → `201 {id, status:"pending", match:{entity_id, match_confidence}}`.
- `POST /v1/submissions/upload` (CSV, same columns as the bots' files, ≤ 500 rows) → `202 {upload_id, rows, accepted, rejected:[{line, reason}]}`.
- `GET /v1/submissions?status=pending&mine=1&cursor=`: own submissions; moderators see the queue.
- `POST /v1/submissions/{id}/approve` and `/reject` (`{note}`), moderators only; each writes `moderation_log`.
