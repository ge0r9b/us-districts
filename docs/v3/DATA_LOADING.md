# v3 data loading plan (Phase 1)

> Plan only. Nothing has been loaded and no database exists yet. Data files belong to the data lanes (REPO-RULES: Election Data owns `data-v3/results/`, Geo & Institution Data owns `data-v3/geo/`). v3 only reads them.

## 0. Intake paths (priority order)
1. **Primary: `data-v3/`** at the repo root (read-only for v3).
   - `data-v3/results/**.csv`: long rows in the Election Data bot format (§1). In flight on `origin/data/election` (7faa12d): `PA/pa_president_county_official.csv` (2020 + 2024), `PA/pa_president_county_official_2016.csv`, `2016/us_president_2016_state_fec.csv`, plus audit CSVs that are **not** result rows (`*_mismatches.csv`, `states/v2_state_totals_vs_official.csv`; skipped by header check R01).
   - `data-v3/geo/` (on `origin/data/geo` 6d8b443; answers in its `QUESTIONS.md`): **committed today:** GEOID tables for every v2 layer (`ushouse.csv` 436, `senate.csv` 1,950, `statehouse.csv` 4,890, `schools.csv` 13,305 with `tiger_set` unsd/elsd/scsd, `counties.csv` 3,144, `towns.csv` 1,598 Iowa townships; columns `layer, state, row, v2_name, geoid, tiger_name, tiger_set, match`), `v2_name_collisions.csv` (old → new names + GEOID), `summary.json`, `README.md`. **Decided, not yet committed:** `towns_2024.geojson` (TIGER county subdivisions, 20,935 rows, ~2.48 MB gz) and `places_2024.geojson` (TIGER places, 19,477 rows, ~4.01 MB gz), keyed by GEOID, gzipped above ~5 MB; `zcta2024.csv` (ZCTA, internal-point lat/lon, land area, from the TIGER 2024 Gazetteer, built by a script in `tools/`); `v1_towns.csv` + a places crosswalk (in progress); `entities.csv`; per-year `precincts_<year>.csv` + a 2020→2024 area crosswalk. Full-resolution TIGER is fetched from census.gov at build time, joined on `geoid` (never committed).
2. **Legacy fallback: `v2/data/*.js` only** (global-loader JS, wide `[dem, rep, total]`), read by the legacy v2 importer (§8). It is used for everything `data-v3/` does not cover yet, and as the **only parity source**. The root `data/` folder (`data/<State>.js`, `data/election20XX.js`, `data/precincts20XX/`, `data/zcta2024.js`) is **v1 and out of scope** (orchestrator, Oct 18, 2026): v2 is moving off it, it will not be renamed, and v3 never reads it.
3. **Precedence (confirmed by the orchestrator, Oct 18, 2026, Q-E8): official values win over v2's, and v2's are kept in history.** When both exist for the same (contest, unit, answer), the official `data-v3/` row is current, whatever its `retrieved_at`: the loader ranks `method = official` above `v2_import` before comparing timestamps. The legacy row is kept in `result_history`, and differences are written to a diff report for the data lanes (they already publish such audits, e.g. `PA/pa_v2_vs_official_mismatches.csv`).

## 1. Input: the Election Data bot's row format (exact)
One CSV (UTF-8, header row, RFC 4180 quoting) per batch: the 13 base columns below, then **`boundary_set` as column 14 and `method` as column 15** (confirmed by Election Data at `data/election` 06421a6 across 772,887 rows; verified, see §13a). **The loader maps columns by header name, not position**, and reads `.csv` or `.csv.gz` (gzip streamed, never fully decompressed in memory; the same applies to every loader in this doc), so 13-, 14- and 15-column files all load. The 2016 FEC state file and the PA county files have 14 columns: `boundary_set` and no `method`.

| # | Column | Observed in `data-v3/results/` | v3 rule | Maps to |
|---|---|---|---|---|
| 1 | `state` | `PA`, `AL` (USPS) | 2-letter USPS (+ `DC`); `US` for national rows | `contest.state_abbr` |
| 2 | `year` | `2016`, `2020`, `2024` | any 4-digit year, so **any number of years** works (2016 ready) | `contest.year` |
| 3 | `office` | `president` | office key; raw spellings via lookup | `office.office_key` |
| 4 | `district` | `statewide` | `statewide` (or empty) means the contest has no district; otherwise the seat code (`101`, `01`) | `contest.district_code` (null for statewide) |
| 5 | `unit_id` | county **FIPS** `42001`; state FIPS `01` | Census GEOID where one exists (state 2, county 5, CD 4, SLD 5, school 7 digits); precinct keys as the bot defines them | `unit.unit_key` (= GEOID), fallback lookup on `unit.legacy_key` |
| 6 | `unit_type` | `county`, `state` | `state, county, county_subdivision, place, precinct, ushouse, sldu, sldl, school_unified, school_elementary, school_secondary, ward` (aliases `senate`→`sldu`, `statehouse`→`sldl`; generic `school`/`schools` → resolved to the right school type from the unit's GEOID via `schools.csv` `tiger_set`, Q-G4) | `unit.unit_type` |
| 7 | `candidate_id` | `biden-joseph-robinette-jr`, `trump-donald-j`, `clinton-hillary`, `jorgensen-jo`, `all-others` | stable slug; `all-others` = aggregate remainder row | `candidate.candidate_key` |
| 8 | `answer` | the **ballot label**: `BIDEN, JOSEPH ROBINETTE JR`, `Donald J. Trump`, `All others` | display label as printed by the source (not a key) | `answer.label`; `answer_key` derived (below) |
| 9 | `party` | `DEM`, `REP`, `LIB`, `CON`, `OTH` | party code | `party` (via `party.aliases`) |
| 10 | `votes` | integers | number ≥ 0 (decimals allowed for re-tabulated rows) | `result.votes` |
| 11 | `weight` | `1` | number in (0, 1]; empty → 1. The 2016 README: "exact reported totals (weight = 1)"; ≈ only for area-weighted rows | `result.weight` |
| 12 | `source_url` | a URL, sometimes **followed by a note**: `https://www.fec.gov/…/federalelections2016.xlsx (sheet "Table 2. Electoral &  Pop Vote")` | split on the first whitespace: URL → `source.url`, rest → `source.notes` | `source` |
| 13 | `retrieved_at` | `2026-10-18T09:39:46Z` | ISO 8601 with zone | `source.retrieved_at`, `result.retrieved_at` |
| 15 (opt) | `method` | `official` (state rows), `retabulated`, `area_weighted` (2022 Senate) | as listed in §1 note | `result.method`; `is_estimate = (method = 'area_weighted')`; `official` and `retabulated` are exact |
| 14 (opt) | `boundary_set` | `v2-2024` in every results file on `data/election` 50f5f5a | lowercase-hyphen slug: `v2-2024` (2022/2024 Senate rows, 2016 presidential district rows), later e.g. `tiger-2020`; **if missing**, derived from the layer (`unit_type` + file → default set, `boundary_set_default`) | `boundary_set.slug`; geometry joins on it, **not on year** |

**Deriving `answer_key`** (stable across years, so deltas compare like with like):
- Partisan offices (president, us_house, state legislature): `party=DEM` → `dem_nominee`, `REP` → `rep_nominee` (one per contest, else reject R10); `candidate_id=all-others` → `other` (`is_aggregate`); any other candidate → `cand:<candidate_id>`.
- The v2 view ("D, R and total of all candidates") is then `dem_nominee`, `rep_nominee` and `total = sum of all answers`. `other` is computed as `total − D − R` when only an aggregate exists. Third-party candidates (Jorgensen, Stein, Castle …) stay individual answers, available for N-answer views, and sum into "other" for the v2 view.
- Measures: `answer` `Yes`/`No` → `yes`/`no`. Multi-choice → `choice:<n>` by ballot order. Nonpartisan races → `cand:<candidate_id>`.

The **natural key** of a row is `(year, office, stage, boundary_set, unit_type, unit_id, candidate_id)` (Q-E12; `state` and `district` are implied: `district` is always `statewide` for Senate and President, Q-E5). One row per key per batch. Below the state level, `unit_id` is the boundary set's own ID: precincts `ST|v2county|v2precinct[|#n]` (the `#n` suffix splits repeated v2 names) and districts the 2024 GEOIDs from `data-v3/geo` (`0101` CD, `01001` SLD, `0100190` school). Precinct IDs are stable **only within a boundary set** (Q-E6). `stage` is derived from the office token: `*_special` → special, `*_runoff` → runoff, else general.

`method` (estimate flag) is now column 15 where present (D6 is settled by the lane's files). Without it, `is_estimate = weight < 1`, and `method = official` when weight = 1.

## 2. Pipeline
```
CSV file ──► load_batch (sha256; same file twice = no-op)
         ──► COPY into stg_result_row (all text, line_no)
         ──► validate (SQL rules → stg_reject)
         ──► resolve keys (contest / answer / candidate / party / unit / source), creating missing dimension rows
         ──► upsert result (+ result_history for changed values)
         ──► refresh aggregates for touched contests, bump contest.data_version and global dv
         ──► rebuild packs (and tiles if geometry changed) ──► manifest
```
It runs offline (on the box or in CI) with a writer role, never from the web API.

## 3. Staging
- `load_batch`: `file_sha256` is unique, so re-submitting an identical file does nothing. `git_commit` records the data-lane commit the file came from.
- `stg_result_row`: an unlogged table, all columns `text`, loaded with `COPY … FROM STDIN (FORMAT csv, HEADER true)`. Nothing is cast at load time, so every bad value becomes a reportable reject instead of a failed COPY.
- `stg_reject(load_batch_id, line_no, rule, detail)`.

## 4. Validation rules (each is one SQL statement inserting into `stg_reject`)
| Rule | Check | On failure |
|---|---|---|
| R01 header | the 13 base column names present (any order), plus optional `method` / `boundary_set`; files with other headers (audits, mismatch lists) are skipped and listed, not loaded | reject / skip whole file |
| R02 required | `state, year, office, unit_id, unit_type, votes, source_url, retrieved_at, candidate_id` non-empty (measures: `answer` instead of `candidate_id`) | reject row |
| R03 votes | numeric, ≥ 0 | reject row |
| R04 weight | empty or numeric in (0, 1] | reject row |
| R05 year/state | year 4 digits within 1789..current; state in the 50 + DC + `US` list | reject row |
| R06 unit_type | in the allowed list (after aliasing) | reject row |
| R07 unit resolves | `(unit_type, year)` → `boundary_set_default` → `unit_key` exists | reject row and log it to the gap report (never invent a unit) |
| R08 timestamps / URLs | `retrieved_at` parses as timestamptz and is not in the future; `source_url` **starts with** `http(s)://` (trailing note allowed, split off into `source.notes`) | reject row |
| R09 duplicates | natural key repeated within the batch | reject all copies, report |
| R10 answer consistency | one `answer_key` per (contest, candidate_id); one candidate per partisan slot per contest | reject row |
| R11 party | maps to a `party` (via aliases) or creates a new party flagged `needs_review` | warn |
| R12 totals QC | per (contest, county): sum of precinct rows vs the official county row within 90–110 % (v2 rule, HANDOFF §4 item 5) | warn and report; do not drop |
| R13 weights | for each source unit, the sum of weights across target units is ≤ 1 + 1e-6 | reject batch section |
| R14 regressions | an existing row from a newer `retrieved_at` would be overwritten by an older one | skip row (older never overwrites newer) |

The batch is applied only if hard rejects are ≤ 0.5 % of rows and no batch-level rule failed. Otherwise status becomes `rejected` and the report goes back to the Election Data lane. Gaps are reported, never filled (REPO-RULES rule 4).

## 5. Idempotent upsert
```sql
-- after resolving keys into a temp table `r` (contest_id, unit_id, answer_id, votes, weight, is_estimate, method, source_id, retrieved_at)
insert into result_history (contest_id, unit_id, answer_id, votes, weight, source_id, retrieved_at)
select x.contest_id, x.unit_id, x.answer_id, x.votes, x.weight, x.source_id, x.retrieved_at
from result x join r using (contest_id, unit_id, answer_id)
where r.retrieved_at >= x.retrieved_at
  and (x.votes, x.weight, x.source_id) is distinct from (r.votes, r.weight, r.source_id);

insert into result as x (contest_id, unit_id, answer_id, votes, weight, is_estimate, method, source_id, retrieved_at, load_batch_id)
select contest_id, unit_id, answer_id, votes, weight, is_estimate, method, source_id, retrieved_at, :batch
from r
on conflict (contest_id, unit_id, answer_id) do update
  set votes = excluded.votes, weight = excluded.weight, is_estimate = excluded.is_estimate,
      method = excluded.method, source_id = excluded.source_id, retrieved_at = excluded.retrieved_at,
      load_batch_id = excluded.load_batch_id, updated_at = now()
  where excluded.retrieved_at >= x.retrieved_at
    and (x.votes, x.weight, x.source_id, x.method) is distinct from
        (excluded.votes, excluded.weight, excluded.source_id, excluded.method);
```
- Running the same batch again changes 0 rows. A newer batch changes only rows whose values differ. Rows absent from a newer batch are **not** deleted; withdrawals need an explicit `retract` list (D7).
- Dimension rows (`contest`, `answer`, `candidate`, `party`, `source`) are upserted on their natural keys (`contest_key`, `(contest_id, answer_key)`, `candidate_key`, `party_key`, `source_id`) before facts. Election rows carry no `source_id`, so the loader mints one per distinct (url, retrieved_at) in the same `<slug>-<sha8>` form the inst lane uses; `source` is unique on `source_id` only.
- Everything for one batch runs in one transaction. Aggregates are refreshed with `refresh materialized view concurrently` after commit, so readers never see a half-loaded contest.

## 6. After load
1. `refresh materialized view concurrently unit_contest_agg; … answer_share;` (both have the unique indexes CONCURRENTLY needs). Per-contest partial refresh can come later if the full refresh grows beyond 60 s.
2. Bump `contest.data_version` for touched contests and the global `dv`.
3. Export packs for touched contests (`/packs/{dv}/…`) and upload them. Write the manifest last (atomic switch).
4. Run the parity checks: totals per state and county equal v2's for 2020 and 2024 (§8).

## 7. Importing v2's existing data via the flat export (alternative path)
v2's data is the inline `PACK`/`XREF` plus JS-wrapped files (`v2/data/*.js`; the root `data/` files are v1 and out of scope, see §0. Original list: `data/<State>.js`, `data/precincts2020|2024/*.js`, `data/election2020|2024.js`; spec §4.1). A **flat export** of all v2 results and boundaries already exists on the box at `/workspace/db/export/` (HANDOFF §5). It is convenient (CSV and GeoJSON), but it is a derived copy that was not regenerated since Oct 17 06:14. The **legacy importer in §8 reads the v2 files directly and is the recommended path**. The export is a cross-check.

| Export file | Rows | Becomes |
|---|---|---|
| `candidates.csv` | 6 (pres2020/2024 × dem/rep/other) | `candidate`, `answer` (`dem_nominee`, `rep_nominee`, `other` with `is_aggregate`) |
| `geo_states.csv`, `geo_districts.csv` (20,467 districts: schools 13,208, senate 1,942, statehouse 4,882, ushouse 435; some keys contain commas, e.g. `schools:CA:Igo, Ono, Platina Union Elementary School District`, so CSV quoting is required) | | `unit` + `entity` + `entity_unit` |
| `boundaries/*.geojson.gz` (states 50, counties 3,143, districts, precincts 2020 163,570, 2024 163,819) | | `unit_geom` lod 0, then lods 1–3 via `ST_SimplifyPreserveTopology` |
| `results/county.csv` (6,284 rows; dem, rep, total, estimate, source) | | bot-format rows, `unit_type=county` |
| `results/district.csv` (40,689; with `estimate`, `flag`) | | rows, `unit_type ∈ ushouse/sldu/sldl/school_*`, `method=retabulated` |
| `results/precinct_2020.csv`, `precinct_2024.csv` (≈163.6k / 163.8k) | | rows, `unit_type=precinct` |
| `results/precinct_2024_est2020.csv` (159,451; area-weighted 2020 on 2024 precincts) | | rows for the 2020 contest on 2024 precincts, `is_estimate=true`, `method=area_weighted` |
| `sources.csv` (105 state × year × layer entries; some are per-county JSON maps) | | `source` + `license` (one source per county credit) |
| `_localities.json` (state, county, town, school district tuples) | | `county_subdivision` units, `entity_unit` links |

Steps:
1. **Regenerate the export from current `main` first.** The files on the box are dated Oct 17, 2026 06:14, before builds 1549–1566 (for example DC wards, build 1559). Who runs the exporter is the orchestrator's or data lanes' call; v3 does not edit `v2/` or `data/`.
2. Converter `v3/ingest/v2_to_rows.py` (Phase 2) turns the wide `dem,rep,total` rows into long bot-format rows: `dem → answer dem_nominee, candidate biden-joseph-r / harris-kamala-d`; `rep → rep_nominee, trump-donald-j`; `other = total − dem − rep` (only if ≥ 0, otherwise reject and report). `source_url` comes from `sources.csv`. `retrieved_at` is the export timestamp, because v2 does not record retrieval times per row; the original credit text is kept in `source.attribution`. `method=v2_import` plus `is_estimate` from the export's `estimate`/`flag` columns.
3. Load geometry first (units and lods), then results through the same staging pipeline, so v2 data passes the same validation as new data.
4. **Parity gate:** for 2020 and 2024, per state, county and district, v3 aggregates must equal the v2 export exactly (integers) and match ≈ flags one-to-one. The coverage counts must reproduce spec §9.2 (for example US House 435 / 435, state senate 1,942 / 1,942 for 2024).
5. Candidate keys: v2 uses short keys (`biden`, `trump`, `harris`). The Election Data bot's directory decides the canonical `candidate_key`. The importer maps v2 keys to it through a small lookup table and never invents IDs (D8).

## 8. Legacy v2 importer (design; `v3/ingest/legacy_v2.py`, Phase 2)
Reads the v2 global-loader JS files **directly** from a pinned `main` commit, so no orchestrator action is needed. It emits bot-format rows (§1, plus the optional `method` column) and GeoJSON features, which then go through the **same** staging and validation as `data-v3/`.

**Parsing.** Each file is `<loader>(<json>)` or `window.X=<json>;`. Strip the wrapper (first `[`/`{` to last `]`/`}`) and `json.loads`. Do not `eval`. Comment-only provenance (`dc.js` header, `countries.js` header) is captured as text.

**Geometry decoding** (matches `decodePolys` / `dec()` in v2 and `tools/build_vest2016.py`): each ring is `[x0, y0, dx1, dy1, …]` integer deltas of lng/lat.
- National layers (`v2/data/us*.js`, `dc.js`, `parts/`): **÷ 1000** (`add_tiger_schools.py`: "coordinates x1000 as integer deltas").
- Precinct files `v2/data/precincts20XX/*.js` and `v2/data/precincts20XX-DC.js`: **÷ 10000** (SPEC §4.1 `SCALE=1e4`; `build_vest2016.py` `S=10000`).
- Polygon nesting `[[ring, hole…], …]` → MultiPolygon. Then `ST_MakeValid`, then lod 1–3 via `ST_SimplifyPreserveTopology`. Precision is about 100 m (÷1000) or 10 m (÷10000), so **for production geometry, prefer TIGER/precinct sources from `data-v3/geo/`** and use v2 geometry only as the fallback (Q-G3).

**Deriving the missing row fields** (the v2 files have no candidate_id, office, weight, source_url or retrieved_at):
| Field | Derivation |
|---|---|
| `state` | row `state` name → USPS via `geo_states` (v2 uses full names: `"Alabama"`) |
| `year` | 2020 / 2024 from the row slot (`a2024`, `a2020`) of the shared layer files, `ELECTION2020/2024`, `precincts2020/2024`, `x20` → 2020. **2016 is never in a row slot**: it comes only from the separate lazy-loaded 2016 files (`election2016.js`, `ds2016-*.js`, `precincts2016/`), so the year is the file's year (Q-E9, resolved) |
| `office` | always `president` (every v2 result is presidential; the layer is the *reporting unit*, not the office) |
| `district` | `statewide` (the contest is the statewide presidential race; the district layer is the unit) |
| `unit_type` | from the loader: `__usst` → state, `__uscty`/`ELECTION20XX` → county, `__ds2016("states"|"ushouse"|"senate"|"statehouse"|"schools")` → state/ushouse/sldu/sldl/school_* (school type from `schools.csv`), `__uscd` → ushouse, `__usdist("senate")` → sldu, `__usdist("statehouse")` → sldl, `__usdist("schools")` → `school_unified|school_elementary|school_secondary` by the row's `tiger_set` in `data-v3/geo/schools.csv` (matched on `(layer, row)` or `state|name`), `__prec` → precinct, `dc.js` wards → ward (linked to both chambers), `ak.js hd*` → sldl (AK House), `ak.js boro*` → county (borough) |
| `unit_id` | GEOID from the name → GEOID crosswalk (geo lane, Q-G1); if unmatched, `legacy:<state>|<name>` plus a gap-report entry. Precincts: `<ST>|<county>|<precinct>` as in the export |
| `candidate_id` | synthetic, per year: `dem` → **`clinton-hillary` (2016)** / `biden-joseph-robinette-jr` (2020) / `harris-kamala-d` (2024), all as answer `dem_nominee` so the 3-point slider compares the same slot; `rep` → `trump-donald-j` (all three years); remainder → `all-others`. Slugs follow the Election Data lane's directory as seen in `PA/pa_president_county_official.csv` (Harris's slug is not in a committed file yet: Q-E2) |
| `answer` / `party` | `dem_nominee`/DEM, `rep_nominee`/REP, `other`/OTH |
| `votes` | `d`, `r`, and `other = tot − d − r` (reject the row and report if negative) |
| `weight` / `is_estimate` / `method` | `weight = 1` always (v2 stores already-weighted totals, not shares). Flag → `is_estimate`: `est` = both years ≈; `e24` = only 2024 ≈; `e20` = only 2020 ≈ (as read by `v2/index.html`: `ef==="e24"&&ym()!=="2020"`); `null` = exact; `cty` = **unclear** (Q-E1; treated as exact `method=whole_county` until answered). `method = v2_import` plus the flag kept in `meta` |
| `source_url` / `retrieved_at` | National layer files carry **no** source text. Precinct files carry a per-county credit dict as the 2nd loader argument (`__prec("Delaware",[…],{"New Castle County":"The New York Times, …"})`). `ak.js` has `src`/`boroNote`; `dc.js` a header comment. Map these to `source` rows (one per distinct credit text, with `license` from the text: NYT C-UDA, CC BY 4.0, CC0, public record). Use `source_url` = the URL inside the credit text if present, else `https://github.com/ge0r9b/us-districts/blob/<sha>/<path>`. `retrieved_at` = commit time of the file at `<sha>` (v2 records no download times) |
| `result_total` | `tot` (all presidential candidates incl. write-ins where reported); `coverage` unknown → null; `null` result slot = gray (no row) |

**Duplicates and the crosswalk.** The Geo lane renamed the 132 duplicate school rows to `Name (County)` (on `origin/data/geo` a0c2262 and in `cfef4cc`; not yet on main 9ac59a9, which still has 58 duplicate keys / 132 rows, Ohio 49). With the rename, **`state|name` is unique in every national v2 layer** (`usstates`, `uscounties`, `uscd`, `ussldu`, `ussldl`, `ussch`: 0 duplicate keys, verified), and the 2016 `ds2016-*` keys match those rows exactly (0 orphans). The importer therefore uses `state|name` (`state|district` for CD/SLD) as `unit.legacy_key`, **unique per boundary set**, and the crosswalk to TIGER GEOIDs is a plain 1:1 table `legacy_key → geoid` (Q-G1). Geometry matching (≥ 90 % IoU) is only a cross-check, and for rows the table does not cover.
Root `data/<State>.js` (v1, out of scope) still has the old school names and some duplicate place and town names. ~~Q-G8~~ is resolved: the v1 files get no renames, and v3 does not read them.

**2016 (resolved Q-E9; files on `origin/data/election` cfef4cc, README `data-v3/results/2016/README.md`):**
| File (v2/data/) | Global | Shape (verified) | v3 |
|---|---|---|---|
| `election2016.js` | `window.ELECTION2016={"State|County":[d,r,t]}` | 3,144 keys incl. Alaska boroughs and DC; all 3-element (exact) | county results, 2016 contest |
| `ds2016-states.js` | `__ds2016("states",{...})` | 51 keys `"State"`, all exact (FEC) | state results |
| `ds2016-cd.js` | `__ds2016("ushouse",{"State|01":[d,r,t(,1)]})` | 434 keys (404 with 4th element `1`); 1 of 435 missing → gray | ushouse |
| `ds2016-sldu.js` | `__ds2016("senate",…)` keys `State|009` | 1,935 keys (1,832 ≈); 7 missing → gray | sldu |
| `ds2016-sldl.js` | `__ds2016("statehouse",…)` keys `State|055` | 4,860 keys (4,611 ≈); 22 missing → gray | sldl |
| `ds2016-sch.js` | `__ds2016("schools",…)` keys `State|Name` with the `Name (County)` renames | 13,239 keys (12,142 ≈); 65 of 13,304 missing → gray | school |
| `precincts2016/<State>.js` (50) + `precincts2016-DC.js` | **superseded by `data/election` 026b55f (see §9.4):** `__prec16(state,[[county,precinct,d,r,t(,1)] or [county,precinct]],meta)`, values only, row *i* = row *i* of `precincts2024/<State>.js` | VEST 2016 placed onto the 2024 polygons, CC BY 4.0 | results on the **`v2-2024` precinct units** (no `precincts-2016` set) |
Rules: 4th element `1` → `is_estimate = true`, `method = area_weighted` (the README: 2016 precincts weighted into 2024 lines); 3 elements → exact; **missing key → no row (gray)**, never zero. `[d, r, t]` → `dem_nominee` = Clinton (`clinton-hillary`), `rep_nominee` = Trump, `other = t − d − r`. Source: the VEST 2016 / FEC 2016 citations in the README (`source_url` doi:10.7910/DVN/NH5S2I and the FEC xlsx URL).

**County tables:** the corrected 2020/2024 county tables are `v2/data/election2020.js` / `v2/data/election2024.js` (on `origin/data/election` a63e17e; county-table fixes for OR 2024, KS/RI/NY/ME 2020 in 5a563d7). v2 will stop reading `../data/`. The importer reads **only** `v2/data/`. Root `data/` is v1 and out of scope: there is no fallback, even though main 9ac59a9 still loads `../data/election20XX.js` until the branches merge.

## 9. v2 intake alignment: every current and in-flight artifact → v3
Verified against the files at `main` 509d31d (build 202610181567), `origin/data/election` 7faa12d, `origin/data/geo` 28a7426, and the uncommitted files in the lane clones on the box (read-only), Oct 18, 2026 about 05:55 EDT.

### 9.1 Current v2 artifacts (main)
| Path | Loader / format | Fields (verified) | v3 target | Loader |
|---|---|---|---|---|
| `v2/data/usstates.js` | `window.__usst([...])` | `[state, polys(÷1000)]` | `unit`(state) + `unit_geom` | legacy |
| `v2/data/uscounties.js` | `window.__uscty([...])` | `[state, county, polys]` (3,143 rows; **no results in the file**) | `unit`(county) + geom | legacy |
| `v2/data/election2020.js`, `v2/data/election2024.js` (corrected; on `data/election` a63e17e, merging to main with upcoming builds) | `window.ELECTION20XX={...}` | `"State|County": [d, r, tot]` (no source in file) | `result` + `result_total` (county) | legacy; superseded per state by official `data-v3/results` rows (PA already; official wins, Q-E8) |
| `v2/data/election2016.js`, `ds2016-{states,cd,sldu,sldl,sch}.js`, `precincts2016/*.js`, `precincts2016-DC.js` (on `data/election` cfef4cc) | `ELECTION2016`, `__ds2016(layer,{key:[d,r,t(,1)]})`, `__prec` | see §8 "2016" | 2016 contest results + `precincts-2016` units | legacy (lazy per-year files) |
| `v2/data/uscd.js` | `window.__uscd([...])` | `[state, "01", polys, a24, a20, "est"?]` (435; 73 `est`) | unit(ushouse) + results | legacy |
| `v2/data/ussldu.js` | `window.__usdist("senate",[...])` | `[state, "002", polys, a24, a20, flag?]` (1,942; flags est 509, e24 30, e20 32, cty 4) | unit(sldu) + results | legacy |
| `v2/data/ussldl.js` | `window.__usdist("statehouse",[...])` | same (4,882; est 1,187, e20 109, e24 54) | unit(sldl) + results | legacy |
| `v2/data/ussch.js` | `window.__usdist("schools",[...])` | same (main 9ac59a9: 13,208 rows, est 4,719, e24 160, e20 90, cty 54, explicit null 104; `a24` null 84, `a20` null 26 = gray; 58 duplicate keys. `origin/data/geo`: **13,304 rows** (+96 OK elementary), duplicates renamed `Name (County)`, **0 duplicate keys**) | unit(school) + results | legacy + `legacy_key → geoid` table |
| ~~`data/<State>.js` (50)~~ (root, **v1, out of scope**); byte-for-byte copies at `v2/data/states/<State>.js` (on `data/geo` 6d8b443, sha256 verified; main L742 still loads `../data/` until the orchestrator repoints it) | `__geo("State",{schools,ushouse,senate,statehouse,places,towns,counties})` | `[state, name, polys÷10000]` (towns `[state, county, name, polys]`) | not used for v3 geometry: towns/places come from `data-v3/geo/towns_2024.geojson` / `places_2024.geojson` (TIGER, by GEOID; Q-G5); `v2/data/states/` only as the parity reference for names | parity check only |
| `v2/data/parts/<State>.js` | `__parts("State",[...])` | `[county, town, polys|null]`: the **county part of a town split across counties** (geometry or null), **not results** (`window.__parts` in `v2/index.html`) | `unit`(county_subdivision part) with `parent_unit_id` = county; `unit_crosswalk` town↔county | legacy |
| `v2/data/precincts2024/*.js` (verbatim copy, `data/election` be5168d; main 9ac59a9 still loads root `../data/precincts2024/` L991) + `v2/data/precincts2024-DC.js` | `__prec("State",[...],{credits})` | `[county, precinct, d, r, tot, polys(÷10000)]` + per-county credit dict | unit(precinct, set `precincts-2024`) + results + `source` per county | legacy. Keys: `County|Precinct` is **not unique** (2024: NC 7, PA 1 repeated) → use the per-year `precinct_id` (`<USPS>-<year>-<county FIPS>-<row ordinal>`, Q-G7) |
| `v2/data/precincts2020/*.js` (verbatim copy, be5168d; main still loads root L1510) + `v2/data/precincts2020-DC.js` | same | same | unit(precinct, set `precincts-2020`) + results | legacy; repeated `County|Precinct` keys in 2020: MA 1,918, OK 556, PA 51, AZ 4, NC 2, GA 1, NM 1 → per-year `precinct_id` |
| `v2/data/x20/<State>.js` | `window.__x20("State",{"County|precinct":[d,r,tot]})` | 2020 votes **estimated on 2024 precincts** | `result` for the 2020 contest on `precincts-2024` units, `is_estimate=true`, `method=area_weighted` (some exact same-shape: Q-E3) | legacy |
| `v2/data/dc.js` | IIFE with header comment | 8 wards: geometry + `[d,r,tot]` 2024 (2022 plan) and 2020 (2012 plan) | unit(ward) + `entity_unit(seat_district)` for **both** DC "chambers" + DCPS school unit | legacy |
| `v2/data/ak.js` | `window.__ak={...}` | `hd2024`/`hd2020` (40 House districts `[d,r,tot]`), `state2024/2020`, `boro2024/2020` (30) + `src`, `boroNote*` | results for sldl (AK) and county (boroughs, ≈) | legacy |
| `v2/data/zcta2024.js` (byte-for-byte copy on `data/geo` 6d8b443; main L1309 still loads root) | `window.ZCTA2024={"zip":[lat,lng]}` | **lat first** | **not used by v3**: v3 loads `data-v3/geo/zcta2024.csv` (ZCTA, internal point lat/lon, land area; TIGER 2024 Gazetteer; Q-G9) into a `zcta` lookup | v2 parity only |
| `v2/data/countries.js`, `ctryshape.js`, `canada.js` | `window.COUNTRIES/CTRYSHAPE/CANADA` | Natural Earth bbox / silhouettes / provinces (`[name, code, S, W, N, E, rings]`) | `entity`(country/province) + icons; Canada parked | legacy (context only) |
| Inline `PACK`, `XREF`, `STATE_FILES`, `OFFICES`, `PHOTO` in `v2/index.html` | JS constants | lists, cross-refs, office list (`[{id:"president",label:"President",letter:"Pr",scope:"us"}]`), candidate photos | `entity`, `entity_alias`, `office`, `candidate.photo_path` | one-off extraction (read-only) |
| `v2/img/flags`, `stateflags`, candidate photos | PNG | | `entity_image` (`role = flag`), `candidate.photo_path` + credit | copy |
| `v2/data/COVERAGE.md` | Markdown | gap inventory, sources, licences | `source`/`license` seed; gap list = expected gray (parity gate) | manual + checks |
| `/workspace/db/export/` (box only) | CSV + GeoJSON | §7 | cross-check only | export path |

### 9.2 In-flight artifacts (not on main yet)
| Where | Artifact | Format | v3 target | Note |
|---|---|---|---|---|
| `origin/data/election` | `data-v3/results/PA/pa_president_county_official.csv` | bot rows; PA 2020 + 2024, county FIPS, all ballot candidates | primary intake | first real `data-v3` file |
| `origin/data/election` | `data-v3/results/PA/pa_president_county_official_2016.csv` | bot rows; 67 counties × 5 candidates | 2016 contest | the 2016 contest is created automatically (any year) |
| `origin/data/election` | `data-v3/results/2016/us_president_2016_state_fec.csv` | bot rows; 51 states × 3 (Trump, Clinton, all-others); `unit_type=state`, `unit_id` state FIPS | 2016 state results | `source_url` has a trailing sheet note (R08 handles it) |
| `origin/data/election` | `PA/pa_v2_vs_official_mismatches.csv`, `states/v2_state_totals_vs_official.csv`, `*/AUDIT.md`, `GAPS.md`, `SOURCES.md` | audit tables | not loaded; parity/diff reports reference them | header ≠ bot format → skipped by R01 |
| `origin/data/election` | `raw/*.json`, `raw/*.xlsx` | untouched downloads | `source.sha256` | never parsed by v3 |
| election-data clone, uncommitted | `data-v3/results/2016/precincts2016/<State>.js` (12 states so far) + `report/<st>.json` + `tools/build_vest2016.py` | **v2 `__prec` format** `[county, precinct, d, r, tot, polys(÷10000)]` from VEST 2016 (CC BY 4.0), county = v2 county name | precinct units (`precincts-2016`) + 2016 results via the legacy parser | uses the legacy format, not bot rows (Q-E4) |
| `origin/data/election` cfef4cc / a63e17e | 2016 lazy-load files and corrected county tables in `v2/data/` (listed in §9.1) | v2 wide JS | 2016 contest; county results | legacy; main 9ac59a9 has the 3-point slider and Clinton thumbnail (Build 1569, `tests/y2016.py`) but shows 2016 as gray until the files are wired |
| `origin/data/geo` | `tools/coverage_audit.py`, COVERAGE.md audit matrix (layer × year × state vs TIGER 2024 Gazetteer) | Markdown + optional CSV | parity gate expectations | read-only |
| geo-data clone, uncommitted | `tools/add_tiger_schools.py` (adds TIGER 2024 **elementary** districts, Oklahoma first, into `ussch.js` row format with flags `e24`/`e20`/`est`) | v2 `__usdist("schools")` rows | school units (elementary) | v3 needs `unit_type` school_elementary vs unified (Q-G4) |
| Planned (coordinator) | `data-v3/geo/` with stable TIGER GEOIDs; IA townships | not committed | `unit.unit_key = geoid`, crosswalk to `legacy_key` | format to be agreed (Q-G2) |
| `qa/bugs` | `BUGS.md` | not on any remote branch; the local clone has no BUGS.md yet | MIGRATION_CHECKLIST re-check | — |

### 9.3 Drift check, Oct 18, 2026 08:00 EDT (main 58d815e, Build 1570)
**On main now (Build 1570):** 2016 is wired. `election2016.js`, `ds2016-*.js` and `precincts2016/` lazy-load only when 2016 is picked (test `y2016-data`). County tables and 2020/2024 precincts now load from `v2/data/` (`election2020/2024.js` corrected copies, `precincts2020/`, `precincts2024/`; test `prec-paths`). The legacy importer reads exactly these paths. **Only two root `../data/` loads remain in `v2/index.html`:** L742 (the 50 state geography files, `STATE_FILES`) and L1311 (`zcta2024.js`). Both have `v2/data/` copies on `data/geo` and switch with the geo merge build (readiness item 3).

**New intake on lanes (not on main yet):**
| Where | Artifact | Format | v3 target | Note |
|---|---|---|---|---|
| `origin/data/election` 258dd04 | `data-v3/results/2024/senate/` state, county, `precincts/<ST>.csv.gz` (33), ushouse, sldu, sldl, school (gz) | **bot rows, 13 cols + `method`** | office `us_senate`; contests per state, stage `general` / `special` | First non-president contest. `office` tokens `us_senate` / `us_senate_special` map to one `office` row (`us_senate`) plus `contest.stage`. Below state level, 3 rows per unit (d slot, r slot, `all-others`). The d slot can be an independent (ME King, VT Sanders, NE Osborn), so v3 must not assume d = Democrat; the colour follows `party`. States with no race have no rows and show gray. |
| `origin/data/election` e2332f6 / 66ec3f5 | `data-v3/results/2022/senate/` (same files; GA `us_senate_runoff`, CA/OK specials; ID/IN official replacements) | same | **first midterm year**; stage `runoff` | **2022 values sit on v2's 2024 precinct polygons** (bridged, ≈ where lines differ). So contest year ≠ boundary vintage: the loader must attach 2022 rows to boundary set `precincts-2024`, never create a `precincts-2022` set. AK values are first-round RCV. |
| `origin/data/inst-officeholders` | `data-v3/inst/officeholders_house_{current,2024,2020}.csv`, `officeholders_stateleg_{current,2024}.csv` (+ official roster diffs) | CSV keyed `unit_geoid, unit_vintage`, `entity_id`, `person_id` (bioguide / OpenStates ocd-person), term dates, source + sha256 + licence | new `officeholder` table (SCHEMA.sql, proposed) | Joined to `data-v3/geo` by GEOID. 2020 House sits on `cd116`, so officeholders are vintage-aware like results. |
| `origin/data/inst-officeholders` | `data-v3/inst/county_government.csv` (CoG 2022; 3,031 yes / 113 no) | CSV keyed `county_geoid, vintage` | `entity` attribute `has_own_government` (ENTITIES_SCHEMA on `data/inst-audit`) | 3 TIGER disagreements listed; CoG wins. |
| `origin/data/inst-fixes`, `data/inst-gray2` | `v2/data/ussch.js` value fixes (population-weighted ≈ from Census 2020 blocks; AK, OR/WY/MO, KY, deferred districts) | v2 wide JS | legacy importer, same paths | new ≈ method `population_weighted`; add to the `method` vocabulary (Q-E3). Some commits are marked droppable, so the parity gate must read whatever lands on main. |
| `origin/data/geo` c996a7d | `towns_2024.geojson.gz` (35,482 cousub, 28.7 MB gz) and `places_2024.geojson.gz` (32,041, 15.9 MB gz) | GeoJSON keyed by GEOID | `unit` + `unit_geom` (towns, places) | **No longer in git** (orchestrator ruling). Regenerated deterministically into `../geo-data-raw/v3/` by `tools/v3_geojson_2024.py`, sha256 in `data-v3/geo/README.md`. The v3 build must run or fetch that step and verify the sha256 before loading. Counts supersede Q-G5's 20,935 / 19,477. |
| `origin/data/geo` 0698944..1b2c5a7 | self-contained v2 town files (all 50 states, TIGER 2024 geometry per parts row) + lazy `places/<State>.js` | v2 wide JS | legacy importer: towns/places from `v2/data/parts`, `v2/data/places` | the legacy parser must read the new per-state places files. |
| `origin/qa/bugs` 1ddc397 | QA pass 4: QA-034..QA-037, `qa/restore.py`, `qa/sweep.py`, `qa/monkey.py`, `qa/popcmp.py` | Python Playwright | MIGRATION_CHECKLIST (restore, layout sweep, throttled slider) | Restore excludes map vs list (QA-034), a known v2 gap. |

## 10. Questions for the data lanes (answers change the loader, not the schema)
**Election Data**
- **Q-E1** `ussch.js` / `ussldu.js` flag `cty` (54 schools, 4 senate): what does it mean? Is it "district = whole county(ies), official county totals" (exact) or a county-level estimate (≈)? `v2/index.html` treats only `est`/`e24`/`e20` as ≈.
- **Q-E2** Canonical candidate slugs: the committed files use `biden-joseph-robinette-jr`, `trump-donald-j`, `clinton-hillary`, `all-others`. What is Harris's slug (`harris-kamala-d`?) and is there a committed candidate directory file v3 should treat as the source of truth?
- **Q-E3** Can the bot add an optional `method` column (`official|area_weighted|allocated|votes_in_split|town_apportioned|retabulated`)? Without it, ≈ can only be inferred from `weight < 1`, and re-tabulated district totals (weight 1 but estimated) lose their ≈. For `x20` rows: which are exact same-shape and which are area-weighted?
- ~~**Q-E9**~~ **Resolved (orchestrator, Oct 18, 2026; verified against cfef4cc):** 2016 is not stored in row positions; it lives in separate lazy-loaded `v2/data/` files (`election2016.js`, `ds2016-*.js` with a 4th element `1` = ≈ and missing key = gray, `precincts2016/` in `__prec` format). See §8. Small README mismatch: it also mentions an `e16` flag, but no `e16` occurs in any of the files (Q-E10). Original question: where does the 2016 `[d, r, tot]` triple sit in each file (a new slot after `a2020` in `__usdist`/`__uscd` rows? `ELECTION2016` in `data/election2016.js`? `precincts2016/`?), and which estimate flags cover 2016 (an `e16` flag, or a new meaning for `est` across three years)? v3 needs the exact layout before the importer's slot map is final.
- **Q-E4** (answered for the JS side by `data/election` 026b55f: 2016 precincts ship as values-only `__prec16` files aligned to the 2024 precinct rows, §9.4; still open whether bot-row CSVs will also exist) (earlier note, largely answered by Q-E9: 2016 precincts ship as `v2/data/precincts2016/` in `__prec` format and are read by the legacy parser; still open whether bot-row CSVs will also exist) 2016 precincts are being built in the v2 `__prec` JS format. Will they also be emitted as bot rows (CSV) under `data-v3/results/2016/`, or should v3 read the JS through the legacy parser?
- ~~**Q-E5**~~ **Resolved:** `district` is always `statewide` for these contests, and district layers use GEOIDs. Original: `district` = `statewide` for statewide contests: confirm the token (vs empty), and the format for seats (`01` vs `1` vs `PA-01`).
- ~~**Q-E6**~~ **Resolved:** precinct `unit_id`s are v2-2024 polygon keys `ST|v2county|v2precinct[|#n]`, stable only within a boundary set. Original: `unit_id` for precincts: what key will bot rows use (v2 `County|Precinct` name, VEST GEOID, state precinct code)? Is it stable across years?
- **Q-E7** "All others" vs individual minor candidates: the FEC files use one `all-others` row, while PA DOS lists each ballot candidate but no write-ins (2016 PA total 6,115,402 vs FEC 6,165,478). Which should v3 show as "total of all candidates" when both exist for the same unit and year?
- ~~**Q-E8**~~ **Resolved (orchestrator, Oct 18, 2026): official values win and v2's are kept in history.** Original question: when `data-v3` official totals differ from v2 (e.g. PA 2020 Allegheny, `PA/GAPS.md`), confirm v3 should show the official value and keep v2's in history (the planned precedence).

- ~~**Q-E11**~~ **Resolved:** `data/election` be5168d copies `data/precincts2020/` and `data/precincts2024/` unchanged into `v2/data/` (101 files, +114.3 MB). Main still loads the 50 state geography files (`index.html` L742) and `zcta2024.js` (L1309) from `../data/`; the orchestrator repoints them once the `v2/data/` copies are on main.
- **Q-E10** (open; likely answered by `data/election` 68791bd "2016 README: drop stale e16 flag; ≈ = 4th element 1", awaiting confirmation) The 2016 README says ≈ is "`e16`, or a 4th element `1` in `ds2016.js`", but only the 4th element occurs in the committed files. Confirm `e16` is unused (or where it will appear).

**New from the Oct 18 08:00 EDT check**
- Q-E5 and Q-E6 are answered in practice by the Senate READMEs: `district=statewide`; precinct `unit_id` = `<ST>|<v2 county>|<v2 precinct name>` with `|#<row>` only for repeats, keyed to the v2 2024 file. Q-E7: Senate rows use one `all-others` row below state level and every candidate at state level. Awaiting the Election lane's confirmation that this is the rule for all future contests.
- ~~**Q-E12**~~ Resolved; see the Q-E12 entry below.
- ~~**Q-E13**~~ Resolved; see the Q-E13 entry below and §12.
- ~~**Q-I1**~~ **Resolved (Oct 18, 2026):** `person_id = scheme:id`, priority bioguide > ocd-person > state-leg, with a `persons.csv` crosswalk; tables `person`, `person_alias`, `officeholder` (unit + date range). See §13.

- ~~**Q-E12**~~ **Resolved (Oct 18, 2026):** rows are keyed by contest year + `unit_id`; below state level `unit_id` is the boundary set's own ID. The lane adds a `boundary_set` column (after `retrieved_at`) = `v2-2024` for the 2022/2024 Senate rows and 2016 presidential district rows; future values use the same lowercase-hyphen form (`tiger-2020`). v3 keys results on `(year, office, stage, boundary_set, unit_type, unit_id)` and joins geometry on `boundary_set`; a missing column is derived from the layer. **Note:** the committed Senate files already use column 14 for `method`, so `boundary_set` will be column 15, and the loader reads by header name.
- ~~**Q-E13**~~ **Resolved (Oct 18, 2026):** Senate office tokens are `us_senate` (regular) and `us_senate_special` (unexpired terms: CA and NE 2024, CA and OK 2022). The **GA 2022 runoff token is `us_senate_runoff`** (read from `data-v3/results/2022/senate/us_senate_2022_*.csv` on `data/election` 66ec3f5). `district` is always `statewide`. The d/r rule is in §12.

- ~~**Q-I2**~~ **Resolved (data/inst-officeholders 9d25f25):** every person_id is `scheme:id`: `bioguide:`, then `ocd-person:<uuid>`, then `<st>-leg:<id>`. 12 ids were mapped to OpenStates (`person_id_matches.csv`) and 12 kept as state-leg (VT 9, TX, OK, LA). `persons.csv` is committed (8,185 rows, 957 aliases). See §13.

**Geo & Institution Data**
- ~~**Q-G1**~~ **Resolved (done, bbc8854 / 9ff4c00):** `data-v3/geo/<layer>.csv`, one line per v2 row with `geoid`; every row matched, no GEOID reused within a layer. The 58 duplicate school keys were renamed `<name> (<county>)`; `v2_name_collisions.csv` maps `old_name → new_name → geoid` (use `old_name` for pre-rename main commits). The importer keys on `state|name` (post-rename) or `(layer, row)`, and the ≥ 90 % IoU fallback is dropped. Not covered yet: v1 towns/places → `v1_towns.csv` + places crosswalk (in progress). Note: the app's `normT()` hides same-named towns (IL 473, NY 197, IA 173, KS 154 …), so `state|county|name` is not unique for towns; use GEOID.
- ~~**Q-G8**~~ **Resolved (orchestrator, Oct 18, 2026; the loader repoint and the Ohio / Union County "Washington township" duplicate key are queued with the geo merge build):** root `data/<State>.js` is v1. It gets no renames and is out of scope for v3. The lane also renamed 8 `v2/data/parts/` place rows `Name (County)` (OH Oakwood; TX Reno ×3, Oak Ridge ×2, Lakeside ×2; fd0f171), now listed in `v2_name_collisions.csv`. **Left for the orchestrator:** one duplicate v1 town key, Ohio / Union County / "Washington township" (GEOIDs 3915981662 and 3915981242), which can only be fixed when v2 moves off v1. v3 is unaffected because it keys towns by GEOID.
- ~~**Q-G2**~~ **Resolved (orchestrator, Oct 18, 06:08 EDT):** GeoJSON, one file per layer × vintage (`data-v3/geo/<layer>_<vintage>.geojson`), gzipped above ~5 MB or regenerated by a `tools/` script; attribute tables are UTF-8 CSV. Current v2 geometry is lon/lat in EPSG:4269 (NAD83; < 1 m from EPSG:4326, not reprojected), and the planned GeoJSON is EPSG:4326, 6 decimals, properties `geoid, name, state_fips, tiger_set`.
- ~~**Q-G3**~~ **Resolved:** full-resolution TIGER stays out of git. v3 fetches TIGER/Line 2024 from `https://www2.census.gov/geo/tiger/TIGER2024/<LAYER>/` at build time and joins on `geoid` (the lane offers `tools/fetch_tiger.py` + `tiger_manifest.csv` on request). This becomes `unit_geom` lod 0 for point-in-polygon. v2 geometry is used only for display parity.
- ~~**Q-G4**~~ **Resolved (orchestrator, Oct 18, 2026):** three school unit types `school_unified` / `school_elementary` / `school_secondary` (TIGER UNSD / ELSD / SCSD) under a shared parent category `school_district` (SCHEMA.sql `unit_type_def`), so the UI still shows one list. Background: The lane recommends three unit types `school_unified` / `school_elementary` / `school_secondary` from `tiger_set` (unsd 10,872, elsd 1,952, scsd 481), allowing several school units per point (elsd and scsd overlap in CA, IL, AZ, MT; the OK elementary districts do not overlap unified ones). The v3 schema already has these types; the UI keeps v2's single "School districts" layer (D13).
- ~~**Q-G9**~~ **Resolved:** v3 uses `data-v3/geo/zcta2024.csv` (ZCTA, internal point lat/lon, land area; TIGER 2024 Gazetteer, script in `tools/`; not committed yet). v2 gets a byte-for-byte `v2/data/zcta2024.js` (on `data/geo` 6d8b443).
- ~~**Q-G5**~~ **Resolved:** the canonical town layer is TIGER county subdivisions (`cousub`, GEOID SSCCCMMMMM) in `data-v3/geo/towns_2024.geojson` (20,935 rows, ~2.48 MB gz); places are a separate layer, `places_2024.geojson` (TIGER places, SSPPPPP, 19,477 rows, ~4.01 MB gz). Both are keyed by GEOID, with full-resolution geometry from census.gov at build time. Name crosswalks: `v1_towns.csv` plus a places crosswalk (in progress). Both GeoJSON files are decided but **not committed yet** (checked on `data/geo` 6d8b443). The Iowa townships live in `parts/Iowa.js` (1,598) with GEOIDs in `towns.csv`.
- ~~**Q-G6**~~ **Resolved (decided, not built):** `data-v3/geo/entities.csv` (`entity_id, kind, state, name, alias, label, unit_layer, geoid`: state governments, chambers, school boards, counties, towns, `sovereign`/`incorporated` labels), built from `PACK`/`XREF` and checked against TIGER and Census of Governments. Until it is committed, v3 derives entities from `PACK`/`XREF`.
- ~~**Q-G7**~~ **Superseded (Oct 18, 2026 10:00 EDT check):** the user rule "only the current 2024 precinct polygons are kept; past votes are placed onto them" (`data/election` 026b55f, e18b233) replaces per-year precinct sets and the 2020→2024 area crosswalk; see §9.4. Original: **Resolved (decided, not built):** per-year `data-v3/geo/precincts_<year>.csv` with `precinct_id = <USPS>-<year>-<county FIPS>-<row ordinal>` plus `county, v2_name, source_id`, centroid, and a 2020→2024 area crosswalk (→ `unit_crosswalk`). Precinct IDs are per year, not shared across years. Precinct geometry stays in the v2 `__prec` files.

## 11. Re-runs and restore
- Every load is reproducible from (data-lane commit, file sha256). A `data-YYYYMMDD` tag (ARCHITECTURE.md §6) records the `dv` and the Neon branch or snapshot.
- Rebuild from scratch: new Neon branch → apply migrations → replay batches in `load_batch` order → compare aggregates with the tagged snapshot.

## 12. v2-parity display rule: the "d" and "r" columns (Q-E13)
v2 shows two answers plus the total. For v3 this is **a view, not the data**: v3 keeps every answer (all candidates, plus `all-others` where the source only has an aggregate), and the mapping lives in `contest_display_slot` (SCHEMA.sql).
- **d** = the Democratic nominee. If an independent beat the Democrat statewide, or there was no Democrat, **d** is that independent instead.
- **r** = the Republican.
- **total** = all candidates.
- **Colour still follows party** (`answer.party_id`), so an independent in the d slot is not coloured Democratic.

| Case | d | r | Note |
|---|---|---|---|
| ME 2024 | King (I) | Republican | Costello (D) goes to all-others in the v2 view |
| VT (Sanders races) | Sanders (I) | Republican | |
| NE 2024 regular | Osborn (I) | Republican | no Democrat |
| UT 2022 | McMullin (I) | Republican | no Democrat |
| AK 2022 | Chesbro (D) | Murkowski (R) | first-round votes; Tshibaka (R) goes to all-others |
| LA 2022 | Chambers (D) | Republican | |
| ND 2022 | Christiansen (D) | Republican | |

The loader fills `contest_display_slot` from the lane's race config (`data-v3/results/{2022,2024}/senate/tools/races22.py` / `races.py`, "d-slot rule"), records `rule` (`dem_nominee`, `independent_beat_dem`, `no_dem`) per contest, and the parity gate compares the v3 d/r/total with v2's numbers.

## 13. Officeholders and persons (Q-I1, Q-I2 resolved; `data-v3/inst/` on `data/inst-officeholders` 9d25f25, officeholder key format 4a08453)

| File | Rows (verified at 9d25f25) | person_id | Notes |
|---|---|---|---|
| `persons.csv` | **8,185** (601 `bioguide:`, 7,572 `ocd-person:`, 12 `<st>-leg:`), **957 aliases** | canonical | columns `person_id, bioguide, ocd_person, official_ids, name, sources, aliases` → `person` + `person_alias` |
| `person_id_matches.csv` | 24 (12 mapped to an OpenStates id, 12 kept as `<st>-leg`) | log | columns `file, state, chamber, district, official_id, official_name, ocd_person, openstates_name, openstates_file, rule` |
| `officeholders_house_{2020,2024,current}.csv` | 441 each (439 / 440 / 439 `bioguide:`; 2 / 1 / 2 vacant) | `bioguide:<ID>` | `unit_geoid` + `unit_vintage` `cd116` / `cd119` |
| `officeholders_stateleg_2024.csv` | 7,384 (7,348 `ocd-person:`, 36 vacant) | OpenStates | `sldl2024` / `sldu2024`; OpenStates commit in `source` |
| `officeholders_stateleg_current.csv` | 7,361 (7,290 `ocd-person:`, 12 `<st>-leg:` = VT 9, TX 1, OK 1, LA 1; 59 vacant) | | |

- **person_id = `scheme:id`**, one canonical ID per person, in priority order `bioguide:` > `ocd-person:<uuid>` (prefix normalized to `ocd-person:`) > `<st>-leg:<id>` (e.g. `vt-leg:vt-41827`, `la-leg:la-l-64`). No state legislator is bioguide-canonical, and there is no cross-level name matching. `person.scheme` accepts `bioguide`, `ocd-person` or `^[a-z]{2}-leg$`.
- `person_alias` loads from `persons.csv` `aliases` (former canonical IDs, including the MN/NH ids that were mapped to OpenStates).
- **New `date_flags` column** in the officeholder files (`term_end_open`, `term_start_missing`, `;`-combined) → `officeholder.date_flags`. Missing dates stay null; they are never guessed.
- **Provenance (f1d64f6):** each officeholder row carries `source_id` (a `;`-list allowed) → `officeholder_source` link rows → `source.source_id` (`sources.csv`, 48 rows on this branch, all identical to the 70-row file on `data/inst-entities` 348f410). The upstream commit comes from `source.commit`; `officeholder.source_commit` is dropped. The record's id inside its source is `source_record_id` (e.g. `AK00`) → `officeholder.source_record_id`. `boundary_set` and `join_status` are stored as given.
- **Officeholder key (4a08453):** chamber `entity_id` + `unit_layer` + `unit_geoid` + `unit_vintage` + `seat`. The files also carry `unit_plan` (`cd116`, `cd119`, `sldl2024`, `sldu2024`) and `entity_id_legacy` (`al-house` → alias). `valid_from = term_start`, `valid_to = term_end`. A vacancy has a null `person_id` and `status = vacant`. `seat` is filled on 70 of the 7,361 current state-legislature rows (multi-member seats, Idaho House A/B).
- **Unit resolution** (`unit_layer` + `unit_geoid` + `unit_vintage` → `boundary_set` / `unit_type` / `unit_id`):

  | File values (verified) | `unit_type` | `boundary_set` | `unit_id` |
  |---|---|---|---|
  | `cd` / `2020` / `cd116` (house_2020, 441) | `ushouse` | **`tiger-2020-cd116`** (agreed with Institutions; loaded from data-v3/geo `ushouse_2020.csv`) | `unit_geoid` (`0200`) |
  | `sldu` / `sldl` 2020 (2018 plans; no 2020 stateleg file yet) | `sldu` / `sldl` | **`tiger-2020-sldu`** / **`tiger-2020-sldl`** | `unit_geoid` |
  | `cd` / `2024` / `cd119` (house_2024, house_current) | `ushouse` | `v2-2024` (= the 2024 GEOID set the results use) | `unit_geoid` |
  | `sldu` / `2024` / `sldu2024` (1,973 rows in each stateleg file) | `sldu` | `v2-2024` | `unit_geoid` (`01001`) |
  | `sldl` / `2024` / `sldl2024` (5,388 current, 5,411 in 2024) | `sldl` | `v2-2024` | `unit_geoid` |

  **The files carry `boundary_set` themselves (c830581).** The loader uses it with `unit_type` and `unit_geoid` to find the unit.
  - **Seats with no TIGER district** (`join_status` `no_v3_unit`, `no_v3_unit_floterial`, `no_v3_unit_tribal`; empty `unit_geoid` and `boundary_set`) get registered **`seat` units** with no geometry, so `officeholder.unit_id` stays NOT NULL.
  - **Unit key pattern:** `seat:<chamber slug>:<district label, lowercased, spaces to '-'>`, for example:
    - `seat:nh-lower:belknap-8`
    - `seat:me-lower:passamaquoddy-tribe`, `seat:me-lower:houlton-band-of-maliseet-indians`
    - House delegates use the `statedistrict` code: `seat:us-house:PR00`, `GU00`, `VI00`, `MP00`, `AQ00` (AQ00 is American Samoa in the Clerk file).
  - **Which boundary set:** the set named by the file's `unit_plan`, so `cd116` → `tiger-2020-cd116` and `cd119` / `sldl2024` → `v2-2024`.
  - **Counts at f1d64f6:** 124 rows have no TIGER unit (5 in each House file, 59 in stateleg 2024, 50 in stateleg current). They cover **46 distinct seats** (5 delegates, 39 NH floterial districts, 2 ME tribal seats), which makes **51 seat units** because the House delegates appear in both cd116 and cd119.
  - **Member units (ffdf738):** `seat_member_units.csv` (`seat_unit_key, boundary_set, member_unit_layer, member_unit_key, member_boundary_set, member_label, towns, source_id`) → `seat_member_unit`.
    - `seat_unit_key` + `boundary_set` give the seat unit. `member_unit_layer` (`sldl`) + `member_unit_key` (GEOID, e.g. `33003`) + `member_boundary_set` (`v2-2024`) give the member unit.
    - `member_label` and `towns` go to the load report only.
    - 109 links cover all 39 NH floterials, from NH RSA 662:5. `seat_member_unit_gaps.csv` is empty.
  - **Seat keys in the files (ffdf738):** the officeholder files now carry a `unit_key` column. Seat rows have `unit_layer = seat`, `unit_key` = the seat key (`seat:us-house:AQ00`, `seat:nh-lower:belknap-8`) and `boundary_set` set (`tiger-2020-cd116` / `v2-2024`). This matches the pattern above.
  - Any other row whose unit doesn't resolve is rejected and reported, and is never attached to a different vintage. Without the column: `unit_type = unit_type_def` where `tiger_set = unit_layer`, and `boundary_set` from `boundary_set_default (unit_type, unit_vintage)`,

### 13a. Column-order check (Election Data, verified Oct 18, 2026)
At `06421a6` every results CSV has `boundary_set` as column 14, and the Senate files have `method` as column 15. Rows: 728,885 precinct rows (`.csv.gz`) + 43,514 Senate county/district/state rows + 153 (2016 FEC states) + 335 (PA 2016 county) = **772,887**, which matches the lane's figure. At that commit `PA/pa_president_county_official.csv` (469 rows) still had 13 columns. At the current head **50f5f5a** it has 14 (`boundary_set`), so the "PA 2020/2024 county files next" step has landed.

## 14. Process
Since Oct 18, 2026 the v3 lane asks the data bots directly (Election Data, Geo, Institutions, and from now on Companies 7e7bba2a and Governments a901cced) and copies the orchestrator. The geo merge build will remove the last two `../data/` loads from v2 (state geography files, `zcta2024.js`), together with the Ohio / Union County "Washington township" key fix.

## 15. Institutions: entity registry, scraped lists, refresh and user submissions
### 15.1 Inputs
| Producer | Path | Format | Status |
|---|---|---|---|
| Institutions lane | `data-v3/inst/entities.csv` (**54,359** at d332210: the 54,144 US rows + 215 world rows), `entity_geoid_xwalk.csv` (**58,663**), `entity_images.csv` (2,024), `entity_feed_map.csv` (93,278), `source_urls.csv` (126), `entity_v2_rows.csv`, `entity_gaps.csv` on `data/inst-entities` **d332210** | one row per entity, no vintage; xwalk one row per entity × `unit_layer` × vintage | **built** |
| Governments bot (a901cced) | `data-v3/institutions/governments/` on `data/governments` **bc02908** (`states.csv`, `local/<ST>.csv`, `federal_agencies.csv`, `tribes.csv`, `governments_geoid_xwalk.csv`, `id_registry.csv`, `sources.csv`, `county_government_check.csv`) | ids `state:<FIPS>`, `cog:<PID6>`, `fr:<id>`, `bia:<slug>`, frozen in `id_registry.csv`; registry rows win, the rest become `government_other` (mapping in §9.4) | CoG 2022 92,150 units, 473 FR agencies, 577 BIA lines; GEOID rulings from Geo applied |
| Companies bot (7e7bba2a) | `data-v3/institutions/companies/` on `data/companies` **30b1777** (loader files `brands.csv`, `brand_relationships.csv`, `company_locations.csv.gz`, `retracted_locations.csv`, `sources.csv`; `locations/<brand>.csv` = store detail; mapping update in §9.4; the 5faf8aa mapping below still describes the detail files) | **v3 scope (user decision, Oct 18, 2026): public-facing brands, establishments and organizations from Wikidata**, keyed `wikidata:Q<id>`, plus store/site locations. The first pull (0be48d0: SEC/GLEIF `companies.csv.gz`, `relationships.csv.gz`) is **out of scope and not loaded** | first Wikidata pull landed (5faf8aa) |
| Users (phase 3+) | `submission` table via form / CSV upload | moderated | needs auth (D18) |

**Registry rules (agreed with Institutions):**
- `entity_id` is opaque and frozen at first-seen kind + GEOID (`county:01001`, `muni:place:0107000`, `town:cousub:0911001080`, `school:0100003`, `state:01`, `nation:us`). Chambers and national bodies use slugs (`chamber:al-upper`, `us-house`, `chamber:dc-council`). The same id carries across boundary vintages. A new id is minted only when the government itself changes (merger, dissolution, incorporation, CT planning regions), linked through `predecessor_id` / `successor_id` (`;`-lists → `entity_succession`).
- Kinds: `nation, territory, province, state, county, municipality, township, school_unified, school_elementary, school_secondary, chamber, dc_council`, plus `government_other`, `company`, `nonprofit` and `fund` for the bots. School kinds follow Q-G4 under the `school_district` category.
- **World geography (non-US):**
  - Nations are `nation:<iso2>`, ISO 3166-1 alpha-2 in lowercase (`nation:ca`, `nation:fr`). The existing US row on `data/inst-entities` 348f410 is already `nation:us` and is kept as is.
  - Territory ids (kind `territory`, confirmed with Institutions):

    | Pattern | Use | `parent_id` |
    |---|---|---|
    | `territory:<2-digit US FIPS>` | US territories (`territory:60`, `66`, `69`, `72`, `78`, as on 348f410) | `nation:us` |
    | `territory:<iso2>` (lowercase) | foreign dependencies (Greenland `territory:gl`) | the sovereign nation (`nation:dk`) |
    | `territory:ca-<code>` | Canada's territories: `territory:ca-nt`, `ca-nu`, `ca-yt` | `nation:ca` |

    US territories are not loaded as nations, even where ISO gives them a code (`pr`, `gu`, ...).
  - Canadian provinces are kind `province`, `province:ca-<code>` (lowercase ISO 3166-2 code, e.g. `province:ca-on`), with `parent_id = nation:ca`.
  - **Units exist for any country with a registered boundary set (Canada first, below).** Other non-US places stay entity-only. They have no `entity_geoid` / `entity_unit` rows, `entity_location.unit_id` / `boundary_set` stay null, and their outline is the v2 Natural Earth shape.
  - The SCHEMA.sql checks enforce these id patterns and parents (`nation:<iso2>`; the three territory forms with `nation:us` / `nation:ca` parents where fixed; `province:ca-<code>` under `nation:ca`).
- **Canada (data/inst-canada b4dc491, `data-v3/inst/ca/`; D23 resolved: loads in v3.1, v3-only, no v2 JSON):**
  - **Units are allowed for any country with a registered boundary set.** Canada is the first. This replaces the old "no non-US units" rule. Other non-US places stay entity-only.
  - **Unit types** (prefixed in v3): the files say `fed`, `poll`, `ped`, `ppoll`, `cd` and `csd`, and the loader maps them to `ca_fed`, `ca_poll`, `ca_ped`, `ca_ppoll`, `ca_cd` and `ca_csd`. New categories are `federal_district` and `provincial_district`. Polls fall under `precinct`, CDs under `county` and CSDs under `town`.
  - **Boundary sets:** the slug pattern is `<agency>-<boundary year>-<set>`. All 24 slugs in the files are registered in the SCHEMA.sql seed, with `country = 'ca'` and `province` on the provincial ones:

    | Agency | Sets (units at b4dc491) |
    |---|---|
    | Elections Canada | `ec-2023-fed` (343, current), `ec-2013-fed` (338), `ec-2025-pd` (71,217, current), `ec-2021-pd` (69,797), `ec-2019-pd` (66,064) |
    | ON | `eo-2022-ed` (124) |
    | QC | `eq-2026-ced` (127), `eq-2026-sv` (16,756) |
    | BC | `ebc-2023-ed` (93), `ebc-2024-va` (5,778) |
    | AB | `ea-2019-ed` (87), `ea-2026-va` (4,904) |
    | MB | `em-2018-ed` (57), `em-2023-va` (2,371) |
    | SK | `esk-2022-ed` (61), `esk-2024-va` (783) |
    | NB | `enb-2024-ed` (49), `enb-2024-pd` (1,753) |
    | PE | `epei-2017-ed` (27), `epei-2017-poll` (241; vintage not stated by the source) |
    | NL | `enl-2015-ed` (40), `enl-2019-poll` (1,438; not current, maybe superseded) |
    | Statistics Canada | `statcan-2021-cd` (293), `statcan-2021-csd` (5,161) |

    That is 247,902 units in total, with no duplicate keys. The current-set index is unique per (tenant, `unit_type`, `country`, `province`).
  - **Units:** `units_ca_*.csv` (`boundary_set, unit_type, unit_key, name, name_fr, alias, country, province, parent_boundary_set, parent_unit_key, entity_id, attrs, source_id, source_record_id, geometry_ref, flags`) → `unit`:
    - `name_fr` → `labels.fr`. `province` → `unit.province`. `source_record_id` (`FED_NUM=10001`) → `external_id`.
    - `parent_boundary_set` + `parent_unit_key` → `parent_unit_id`, which may cross sets (`ec-2025-pd` → `ec-2023-fed`). `parent_boundary_set` is also kept on the unit.
    - `entity_id` (the chamber) → `entity_unit`. `attrs`, `alias`, `geometry_ref` and `flags` → `meta`.
  - **Entities:** `entities_ca_federal.csv` (2) and `entities_ca_provincial.csv` (13) add `country`, `province`, `name_fr` and `external_id`. These go to `entity.country`, `entity.province`, `entity.labels.fr` and `entity.external_id` (`seats=343(2023_rep_order)`).
    - Chambers: `chamber:ca-house` (lower_chamber, parent `nation:ca`), `chamber:ca-senate` (upper_chamber, appointed, no units) and `chamber:ca-<iso>-legislature` for the 13 unicameral legislatures. Each legislature's parent is its province or territory entity.
    - All rows have `feed = inst-lane` → `origin = inst`.
  - **People and officeholders:**
    - `persons_ca.csv` (337) → `person` with `scheme = ca-mp`, `person_id = ca-mp:<House of Commons PersonId>`. Provincial members come later as `ca-<iso>-leg:<id>`.
    - `officeholders_ca_house_current.csv` (343: 337 serving, 6 vacant) → `officeholder`. `unit_id` is resolved from the Canadian unit key: (`boundary_set` `ec-2023-fed`, `unit_type` `ca_fed`, `unit_key` = FED_NUM). All 343 resolve. `unit_plan` = `rep-order-2023`.
  - **Licences:** the `license` seed adds `OGL-CA`, `OGL-NB`, `StatCan-OL`, `EO-OUDPL`, `DGEQ-OD`, `EBC-OD`, `PEI-OD`, `not-stated` (AB, MB, SK, NL), `HoC-website`, `ca-public-record` (legislature sites) and `ca-federal-law`.
    - `source.non_commercial` and `source.attribution_required` (and the same flags on `license`) are set from these.
    - **Élections Québec data (DGEQ, non-commercial) is excluded from paid features.** Any paid tier filters out sources and boundary sets whose licence has `non_commercial = true`.
  - **Tiles:** Canadian ridings and polls get PMTiles built from the source layers (Elections Canada, provincial agency and StatCan shapefiles named in `geometry_ref`). This is part of the **v3.1 tile build**, one archive per boundary set.
  - **Gaps at b4dc491:**
    - The StatCan boundary download answers HTTP 403, so `ca_cd` / `ca_csd` have no geometry yet, and CSD/CD types are unknown.
    - Senators and provincial members are not built.
    - NS has no provincial district or poll set.
- **District seats are units, not entities.** Officeholders = chamber `entity_id` + unit + `seat` number.
- Column mapping: `feed` is stored raw in `entity.feed` and **mapped to `entity.origin` on load**:

  | `feed` | `origin` |
  |---|---|
  | `tiger/cog` (54,042), `inst-lane` (102) | `inst` |
  | `governments-bot` | `governments_bot` |
  | `companies-bot` | `companies_bot` |
  | `user-upload` | `user` |

  Any other value is rejected and reported. `alias` (`;`, with `\;` escaped) → `entity_alias` rows. `label` → `entity.label`. `gov_status` → `entity.gov_status`. `v2_layer` / `v2_row` / `v2_key` → arrays. `source_id` (`;`-list; 51,800 of 54,144 rows cite several) → `entity_source` (`ord` keeps the order). Extras `level`, `type`, `cog_pid6` and `flags` → columns. Xwalk (348f410: `entity_id, unit_layer, geoid, vintage, boundary_set, relation, source_id, overlap, share_of_geoid_in_entity, share_of_entity_in_geoid`): `unit_layer` = `unit_type_def.tiger_set`, and `boundary_set`, `relation`, `overlap`, `share_of_geoid_in_entity` and `share_of_entity_in_geoid` (same names, numeric 0–1) → `entity_geoid`. `source_id` (72 rows cite several) → `entity_geoid_source`. Each row is then then resolved to `entity_unit` (`primary` / `coextensive` → `same_as` for schools and municipalities, `jurisdiction` for states and counties; everything else → `jurisdiction`).
- **Kinds present in d332210 (54,359):** municipality 19,525; township 18,076; school_unified 10,872; county 3,080; school_elementary 1,952; school_secondary 481; **nation 194** (`nation:us` + 193 world nations); chamber 100 (`us-house` + 98 `chamber:<st>-lower|upper` + unicameral `chamber:ne-upper`); state 51; **territory 17** (5 US by FIPS, 9 foreign dependencies `territory:<iso2>`: aw, ax, cw, gg, gl, hk, je, mo, sx; 3 Canadian `territory:ca-nt|nu|yt`); **province 10** (`province:ca-*`); dc_council 1 (`chamber:dc-council`).
  - The 215 new world rows (193 nations, 12 territories, 10 provinces) have no unit: no xwalk rows, flag `outside_v2_scope:no_unit_no_boundary_set`, `feed = inst-lane` (317 inst-lane rows in total).
  - **`wikidata`** (new column, 38,835 rows, no duplicates) → `entity.wikidata`. The file gives a bare `Q228`, and the loader prefixes it to `wikidata:Q228` to satisfy the CHECK. All of them are in the `entity.kind` CHECK, which also allows `government_other` and `company` for the bots. Xwalk `unit_layer`s are cousub, place, unsd, county, elsd, scsd and state. Relations: primary 54,042, coextensive 4,219, also_cousub 306, independent_city_county_equivalent 42, consolidated_city_county 30, consolidated_town_city 23, federal_district_city 1.
- **Sources:** `sources.csv` (348f410: 70 rows; `source_id, source, source_url, license, retrieved_at, commit, sha256`) → `source`:
  - `source_id` is the **text primary key**; uniqueness is on `source_id` only.
  - `source` → `title`. `commit` → `commit`. `publisher` stays null unless a file gives it.
  - **`source_urls.csv`** (d332210: `source_id, ord, url, label`, 126 rows for all 97 sources; 27 sources have 2 URLs and 1 has 3; labels such as `house`, `senate`, `repo file (pinned commit)`) → **`source_url`**, column for column. `ord = 1` is also `source.url`. The loader no longer splits `sources.csv` `source_url` on ` ; `; that column is only cross-checked.
  - Rows that cite several sources use link tables: `entity_source`, `entity_geoid_source`, `officeholder_source`, `person_source`, `county_government_source` and `entity_location_source`.
  - Every id must exist in `sources.csv` (0 unknown across the inst files).
- **Entity gaps (`entity_gaps.csv`, 254 rows):** **28 `orphan_v2_row`**, all `v2:parts` slivers (e.g. `Ida County|Cushing city`, `Ramsey County|Birchwood Village city`). Each is a v2 simplification sliver of a place that doesn't reach that county in TIGER 2024. These stay unlinked, so the v2 row has no entity and gets no fabricated link. Every other v2 row resolves (131,282 of 131,310 in `entity_v2_rows.csv`). The rest of the file is review flags, not missing entities: `gov_status_unknown` 63, `cog2022_unit_not_linked_by_code` 57, `excluded_not_defined` 49, `officeholder_unit_without_tiger_geoid` 49, `consolidated_county_cog_code_not_in_tiger` 6 and `same_code_place_cousub_overlap_unmeasured` 2. They load into `entity.flags` and the load report.
- Governments link to geography through `entity_geoid` (the xwalk). Companies link through `entity_location` (HQ, sites, by GEOID and/or point).
- **Xwalk `boundary_set` (348f410):** `v2-2024` on 58,655 rows, and **`tiger-2020-county`** on 8 rows (the old CT counties `county:09001`…`09015`, vintage 2020). The registered boundary sets (SCHEMA.sql seed, unique on `(slug, unit_type)`) are `v2-2024` (every v2 layer plus `seat`), `tiger-2020-cd116` (`ushouse`, `seat`), `tiger-2020-sldu`, `tiger-2020-sldl` (2018 plans) and `tiger-2020-county`.
- **`county_government.csv` (f1d64f6, 3,152 rows: 3,144 for 2024 + 8 for 2020 CT)** → `county_government`:
  - Columns as in the file: `county_geoid, vintage, county_name, has_own_government, gov_status, government_kind, cog_pid6, govbot_entity_id, cog_unit_name, cog_unit_type, tiger_funcstat, agrees_with_tiger, government_note`.
  - Added on load: `entity_id = county:<county_geoid>`, which exists for all 3,152 rows; `boundary_set` (`v2-2024`, or `tiger-2020-county` for 2020); and `source_id` (`;`-list) → `county_government_source`.
  - `gov_status` (government 3,105, area_only 47) is also written to `entity.gov_status`. `govbot_entity_id` (`cog:100001`) → `entity_alias` (`external_id`).
- **`source_record_id`** (the record's id inside its source) exists on `entity`, `entity_geoid`, `entity_relation`, `entity_location`, `person`, `officeholder` and `county_government`. It is filled where a file gives one: the officeholder files, and `entities.csv` since d332210 (54,257 of 54,359 rows).

**Companies, brands and organizations (Companies bot; plan change Oct 18, 2026, user via orchestrator):**
- **Scope:** v3 carries only **public-facing brands, establishments and organizations** from Wikidata, plus their locations. **SEC / GLEIF / LEI ingest is dropped from v3 entirely.** The user keeps a corporate database on their own server, and the bridge to it comes in v5/v6 (ARCHITECTURE roadmap). It stays off the public v3 surface.
- **IDs:** the canonical company `entity_id` is **`wikidata:Q<id>`** (bare `scheme:id`, like `bioguide:` and `cog:`). The rest:
  - Former QIDs (Wikidata merges and redirects) → `entity_alias` (`kind = former_qid`), so they keep resolving.
  - **Scraped brands with no QID get no `entity_id` and are excluded** (counted in the load report).
  - **User adds** (moderated form or CSV, phase 3+) get a minted **`usd:<uuid>`** once approved. When a QID appears later, the entity is re-keyed to `wikidata:Q…` (`entity_merge`, rule `usd_to_qid`), and `usd:` stays as an `entity_alias`.
  - `lei:` / `cik:` are **reserved `entity_alias` schemes only** (`kind = reserved`). There is no v3 loader for them, and they are never served by the public API.
- **Kind / name:** `entity.kind` is one of `brand`, `organization`, `company`, `nonprofit` or `fund`. `brand_name` / `name` hold the Wikidata label (public-facing brand). `legal_form_code` / `legal_form` are optional, filled only when Wikidata states a legal form.
- **Files (verified at `data/companies` 67c8cef):**
  - `brands.csv`: 45 rows, 34 `brand` and 11 `company`.
  - `brand_cleanliness.csv`: a ranking, not loaded.
  - `sources.csv`: 11 rows, with the same columns as the inst lane's: `source_id, source, source_url, license, retrieved_at, commit, sha256`.
  - `locations/<brand>.csv`: `cvs.csv` 9,001, `marriott.csv` 6,261, `mcdonalds.csv` 13,486, `walgreens.csv` 7,991, `wawa.csv` 1,320.
  - `company_locations.csv.gz`: 38,059 rows, all of the above. These are plain `.csv`; the loader also streams `.csv.gz` when a file is larger than about 5 MB. All files are read by header name.
- **`brands.csv` → `entity`:**
  - `entity_id` → `entity_id`. `name` → `name` and `brand_name`.
  - `kind` (`brand` / `organization`) → `entity.kind`.
  - `instance_of` (P31 labels, `;`) → `type` (first label) plus `meta.instance_of`. `website` (`;`) → `meta.website`.
  - `source_id` (a sources.csv id) → `entity_source`. `source_url` (the Wikidata page) → `meta.wikidata_url`. `retrieved_at` → the source's `retrieved_at`. `flags` → `flags`. `parent_brand_name` is ignored. The `logo_*` columns → `entity_logo` (below).
  - (Column names verified at 67c8cef. Earlier drafts said `source` / `source_date`, which `brands.csv` does not use.)
  - `location_files` / `location_count` are only checked against the loaded rows (they matched for all 40 brands).
- **`brands.csv` `parent_brand_id` → `entity_relation`**, with `child_id = entity_id`, `parent_id` = each QID in the `;`-list, and `relation = parent_org` (Wikidata P749; P127 is not used).
  - **Multi-parent links are kept**, one row per parent: 28 links in total, 2 of them multi-parent (`wikidata:Q634831` and `wikidata:Q30715430` → Starwood `Q552363` + `Q1141173`). Every parent is itself a row in `brands.csv`. `parent_brand_name` is ignored, since the label comes from the parent's own row.
  - `valid_from` / `valid_to` come from the P749 start time (P580) / end time (P582) qualifiers. **Since 30b1777 they come from `brand_relationships.csv`** (one row per P749 statement, §9.4); `brands.csv` `parent_brand_id` (current parents only) is then just a cross-check.
  - `locations/*.csv` `parent_brand_qid` is a copy of the same P749 value. It matched `brands.csv` on every row, so it is not loaded again.
- **`locations/<brand>.csv` → `entity_location`, one row per store/property:**

  | Column | → | Rule |
  |---|---|---|
  | file stem + `store_id` | `location_key` (also `source_record_id = store_id`) | `walgreens:15196`; `store_id` is unique only within a file. A row with an empty `store_id` is rejected and reported |
  | (constant) | `role` | `establishment_at` (no HQ rows in these files) |
  | `brand_qid` | `entity_id` | an empty `brand_qid` means no entity, so the row is excluded |
  | `sub_brand_qid` | `sub_entity_id` | `sub_brand` text → `meta.sub_brand` |
  | `name` (else `brand`) | `name` | |
  | `address`, `city`, `state`, `zip` | `address` | `address, city, state zip` as published |
  | `lat`, `lon` | `geom` | `ST_SetSRID(ST_MakePoint(lon, lat), 4326)`; empty → null |
  | `county_geoid` | `geoid` | county FIPS (5 digits) |
  | (constant) | `boundary_set` | `v2-2024` when `geoid` is in v2's county layer; `unit_id` = that county unit, then refined by PostGIS point-in-polygon. PR (72) and VI (78) GEOIDs are not in v2's county layer, so `boundary_set` and `unit_id` stay null and the point is kept |
  | `source` (`;`) | `entity_location_source` rows | every id must exist in `sources.csv` |
  | `source_date` | `retrieved_at` | |
  | `flags` (`;`) | `flags` | |
  | `phone`, `status`, `store_type`, `country_code`, `source_url` | `meta` | |
  | `county` (name), `parent_brand_qid`, `brand` | — | derivable, not stored |

  **Scope filter:** only US rows load, meaning `country_code` in US/PR/VI/GU/AS/MP, or empty with a US state code. Marriott's non-US properties (3,781 with another `country_code`, plus empty-country rows with no US state) are skipped and counted in the load report. A row with neither `geom` nor `geoid` fails the `entity_location` check and is reported.
- **Retractions:** a store missing from a newer file is set `retracted = true` only through the retract list (§15.3), never deleted.

- **Superseded:** the earlier notes about the SEC/GLEIF pull (`cik:` rows that had an LEI, missing `company_locations.csv` and LEI side file, GLEIF relationship columns, `type = other`) **no longer apply**; that data is not loaded in v3.

- **Release scope (D21, resolved by the user): the complete set.** v3.0 ships the brand/location schema. The v3.1 list ingest then loads **every brand and every location** from `data/companies` (b583b2c: 45 brands, 38,092 locations in `company_locations.csv.gz`).
  - Size estimate: about 1.4 MB gzipped as a file, and roughly 10–20 MB in Postgres with the GIST index. This is an estimate, not a measurement.
- **Points with no unit:** a location whose point falls in no unit (for example Wawa 9598 and 9599, both "260 W. Baltimore Pike, Media PA" at 36.000282, −45.406712, in the Atlantic) still loads. It gets `unit_id`, `geoid` and `boundary_set` null and the loader adds the flag `no_unit_resolved`. The row is listed in the load report, and the map shows it only if its point is inside the map extent. The user's Wawa list is loaded as-is, so the coordinates are not corrected.
- **Images: seals, flags and logos → `entity_image`** (this replaces the old `icon_flag` column and `entity_logo` table):
  - **Rule:** only freely licensed images are served publicly in v3. Rows with `fair_use = true` load with `public = false` (a CHECK enforces it), and showing them is DECISIONS D22.
  - **`entity_images.csv`** (d332210, 2,024 rows: 1,967 seals and 57 flags; 821 fair use):

    | file column | `entity_image` | Rule |
    |---|---|---|
    | `entity_id` | `entity_id` | empty on 6 rows: tribes known only to the Governments bot (`bia:*`), kept via `feed_entity_id` |
    | `feed_entity_id` | `feed_entity_id` | |
    | `image_kind` (`seal` / `flag`) | `role` | |
    | `commons_file` | `file` | |
    | `commons_url` | `file_url` | |
    | `license` | `license` | verbatim (`LicenseRef-PublicDomain` 1,065, `fair-use` 821, `CC-BY-SA-4.0` 77, ...) |
    | `fair_use` (`yes` / `no`) | `fair_use` | `public = not fair_use` |
    | `usage_basis` | `usage_basis` | `identification icon, small size` on all fair-use rows |
    | `attribution`, `source_url` | same | |
    | `wikidata_qid` | `wikidata` | prefixed `wikidata:` |
    | `retrieved_at` | `retrieved_at` | |
    | `source_id` (`;`) | `entity_image_source` | every id exists in `sources.csv` |

  - **`brands.csv` logo columns** (b583b2c; 29 of 45 brands have a logo, all public domain):

    | `brands.csv` | `entity_image` | Rule |
    |---|---|---|
    | (constant) | `role` | `logo` |
    | `logo_file` | `file` | a blank means no row |
    | `logo_license` | `license` | verbatim; `is_trademark = true` when it contains `trademarked` |
    | `logo_attribution` | `attribution` | |
    | `logo_source_url` | `source_url` | Commons file page |
    | `logo_flags` | `flags` | `logo_no_p154` (15 brands, incl. Wawa) and `logo_multiple_p154_no_rank_or_dates_review` (CVS) have no logo; a `logo_not_free_or_unknown_licence:*` flag means the row is not loaded |
    | (constant) | `fair_use` / `public` | false / true |
    | — | `entity_image_source` | `wikidata-commons-logos-<date>` |

  - **Serving as static assets:**
    - A build step (not the request path) downloads each public file from Commons. SVGs are sanitised (scripts and external refs stripped) and optimised. Raster files are resized to 128 px PNG/WebP.
    - The result is written to `public/img/<role>/<entity_id with ':' → '-'>.<ext>`, and `served_path` and `sha256` are recorded.
    - Vercel's CDN serves it with `Cache-Control: public, max-age=31536000, immutable`. A changed file gets a new `?v=<sha8>`.
    - Rows with `public = false` are never fetched into `public/`.
    - The API returns `images: [{role, url, license, attribution, source_url}]` for public rows only. The UI shows the attribution and source link in the institution panel and the credits page. Images are never recoloured or cropped, and trademarked logos carry a short trademark notice.

### 15.2 Pipeline: staging → validation → dedupe/merge → upsert
1. **Stage:** each file → `load_batch` + `stg_entity_row` (raw row as JSON, by header name).
2. **Validate:** required columns; known `kind`; `entity_id` prefix matches `kind`; `parent_id`, `predecessor_id`, `successor_id` and `entity_relation` endpoints resolve (in the batch or the DB); no relation cycles; company entity_ids match `wikidata:Q[0-9]+` (else excluded) or `usd:<uuid>`; locations have a point or a GEOID; GEOID exists in `data-v3/geo` for that vintage; scraped sources have `robots_ok` and a recorded `license`.
3. **Dedupe/merge:** the match order is the same `entity_id`, then a strong external id (GEOID + layer, CoG `cog_pid6`, Wikidata QID including former QIDs, stored as `entity_alias` rows with `kind = external_id` / `former_qid`), then name + state + kind fuzzy match (`pg_trgm` similarity). From the score:
   - **match_confidence ≥ 0.95:** auto-merge.
   - **0.80–0.95:** `review` queue.
   - **below 0.80:** new entity.
   The registry (`data-v3/inst`) wins over bot rows for governments; bots add fields only where the registry is empty. A merge writes `entity_merge` (from_id → into_id, confidence, rule, decided_by) and an `entity_alias` row of `kind = merged_id`, so **old ids keep resolving**. IDs are never reused.
4. **Upsert:** `insert … on conflict (entity_id) do update` only when values changed; every change writes `entity_history` (before/after JSON).

### 15.3 Refresh jobs (v3.2)
- Later versions refresh automatically: scheduled scrapes run as server cron (**Vercel Cron**, or a worker if runs exceed function limits), with a separate writer role, never the API's read-only role.
- Each run is a new `load_batch`. Diffs are applied **with history**: changed rows close the old relation/location (`valid_to`) and open a new one (`valid_from`). A row **missing** from a newer scrape is **not deleted**; it is closed only through an explicit **retract list** (`retraction`, D7). `entity_history` records every op.
- Scraped-data policy: public sources only; honour robots.txt and terms of service; identify the crawler; rate-limit; no logins or paywalls; license recorded per source (`source.license`, `license_verified`, `robots_ok`).

### 15.4 User add/upload with moderation (phase 3+, needs auth: D18)
- Single **add form** and **CSV upload** (same columns as the bots' files) → `submission` rows. On approval, a new organization gets `usd:<uuid>` (re-keyed to `wikidata:Q…` when a QID appears) (`pending`) with the submitter (`app_user`) and a required public `evidence_url`. Each row runs the same validation and dedupe as §15.2, and the `match_confidence` is shown to the moderator.
- **Moderation queue** (`status = pending`, oldest first). Approve applies the row through the normal upsert with `entity.origin = 'user'`; reject keeps the row with a note. Every action → `moderation_log` (audit log).
- **Rate limits** per user and per IP hash (`rate_limit_bucket`): e.g. 20 single adds/day, 2 uploads/day, max 500 rows per upload (defaults to confirm).
- API: `POST /v1/submissions`, `GET /v1/submissions?status=`, `POST /v1/submissions/{id}/approve|reject` (API.md, **phase 3+**).

### 9.4 Drift check, Oct 18, 2026 10:00 EDT (main 7a23208 Build 1575; data/election e18b233, data/geo fd003ab, data/companies 30b1777, data/governments bc02908, data/inst-officeholders f1d64f6)

**Precincts: one polygon set, past years' votes placed onto it (user rule; `data/election` 026b55f, e18b233).**
- `v2/data/precincts2016/<State>.js` + `precincts2016-DC.js` now call `window.__prec16(state, rows, meta)` and `v2/data/precincts2020/*` + `precincts2020-DC.js` call `window.__prec20(...)`. **No geometry.** `ROW = [county, precinct, d, r, t]` exact, `[county, precinct, d, r, t, 1]` ≈ (split or merged precinct), `[county, precinct]` gray (nothing placed). Row *i* belongs to row *i* of `precincts2024/<State>.js` (`precincts2024-DC.js` for DC); the lane verified 173,276 rows, 0 mismatches.
- **Loader change:** there is **one** precinct `boundary_set`, `v2-2024` (unit_type `precinct`, vintage 2024). The `precincts-2016` and `precincts-2020` sets, the per-year `precinct_id`, and the repeated-`County|Precinct`-key handling for 2020 (MA 1,918, OK 556, …) are **dropped**. 2016 and 2020 president results attach to the 2024 precinct units: 6th element `1` → `is_estimate = true`, `method = area_weighted`; 5 elements → exact (`method = placed_whole`: name match ≥ 50 % area, or one whole unsplit precinct); length 2 → **no result row** (gray), never zero.
- **Validation:** per state, the 2016/2020 file must have the same length as the 2024 file and identical `[county, precinct]` at every index; any mismatch rejects that state's batch (no partial loads).
- **Totals:** about 1 % of votes are unplaced (areas without a 2024 polygon, e.g. 8 South Dakota counties). They stay in the county, state and district tables only, so **precinct sums are never used to derive county/state totals** (same rule as QA-017/029/039). The load report records placed vs source totals per state from `prec16_on24_report.json` / `prec20_on24_report.json`.
- Old 2020 precinct polygons survive only in git history and `/workspace/prec20_orig/` on the box. v3 does not import them.
- **Merge risk (for the orchestrator):** main's `v2/index.html` (7a23208) knows only `__prec`. Once `data/election` merges, the 2016 and 2020 precinct files no longer carry polygons and use new globals, so the merge needs the same build to read `__prec16` / `__prec20` against the 2024 polygons, or 2016/2020 precincts go blank.
- Also on `data/election`: QA-003 corrected county tables in `v2/data/election2020/2024.js` to certified figures (50f5f5a: PA Allegheny 2020, CA, WI, AL, IN 2020, MA 2024). The legacy importer reads them as-is; the earlier v2 values go to history (Q-E8). Q-E12 `boundary_set` is column 14 in every Senate CSV and the 2016 rows (06421a6, a7cb1df), as planned.

**Geo lane: points, ZIP cross-reference, search index (`data/geo` aea8231..fd003ab).**
| v2 artifact | Format | v3 target |
|---|---|---|
| `v2/data/points/<State>.js` (51 files, 82,052 points) | `__points(state,{county,town,place,sch,cd,sldu,sldl:{key:[lon,lat]}})`, keys = row keys without `State|` (86 duplicate v1 rows keyed by GEOID) | new `unit.label_point geometry(Point,4326)` (the state-icon star, always inside the shape); `centroid` stays the geometric centroid. Two zero-area sliver rows (IL Hecker village, KS Willard city) have no point: `label_point` null, flagged |
| `v2/data/zcta_xref/<3-digit>.js` (891 files, 33,642 ZCTAs) | `__zxref(prefix,{zcta:{st, place:[[key,share(,st)]], town:[…], county:[…]}})`, share of ZCTA land, 2 decimals, < 1 % dropped | new `zcta_unit_share (zcta, unit_id, share, source_id)`; keys resolve through `legacy_key`; the 137 cross-state entries use the 3rd element's state |
| `v2/data/geo_index/<a-z|0>.js` (115,745 rows) | `__geoIndex([[name,type,stateAbbr,key],…])`, labels as the app shows them ("District 1", "OH Senate 2") | parity source for the v3 search box: `GET /v1/search` must return the same rows (served from `unit` + `unit_name_trgm`, plus ZCTA rows); see GEOCODER.md |

**Companies (30b1777, "Full Stack fixes").** The loader now reads the ready-made files:
- `company_locations.csv.gz` (36,675 at 30b1777; 38,092 at b583b2c, incl. Wawa and the 33 restored Marriott rows; for Wawa `source_id` keeps only the coordinate source, while `wawa.csv` `source` lists 3 ids) → `entity_location`: `location_id` (`<file stem>:<store_id>`) → `location_key`; `entity_id`, `sub_entity_id`, `role` (`establishment_at`), `name`, `address`, `lat`/`lon` → `geom`, `geoid` + `boundary_set` (`v2-2024`, set only when the county is in v2's layer; PR/VI keep the point, `geoid` empty, flag `county_not_in_v2-2024:<geoid>`), `source_id`, `retrieved_at`; extras `brand_name`, `geoid_method`, `flags`. `locations/<brand>.csv` are joined by `location_id` only for `meta` (phone, status, store type).
- `brand_relationships.csv` (34 P749 statements) → `entity_relation` (`relation = parent_org`, `valid_from`/`valid_to` from P580/P582, `current`, `wikidata_rank` → meta, `flags`). Sheraton and St. Regis keep both current parents with `multiple_current_parents_no_dates_review`.
- `retracted_locations.csv` (`location_id, retracted_at, reason, source_id`; header only today) → `retraction` with target `entity_location`.
- `brands.csv` (b583b2c: 45 rows, 34 `brand` and 11 `company`; `organization` is still accepted) → `entity`. `kind_review` → `flags`.
- Marriott is US and territories only. At b583b2c it has **6,294 rows**: 5,797 with All The Places coordinates, 464 from Marriott's first-party pacsys feed, and 33 with `v5_user_approved`.
  - **D20 (resolved by user decision):** all ~400 locations that earlier had coordinates only from the user's v5 list are kept, unless they are duplicates.
    - 367 of them are re-sourced from the pacsys feed and stay as they are.
    - The other 33 are restored after dedupe (Companies' rule: the same MARSHA code, or the same normalized name and address **within 100 m**; a duplicate would be dropped as `duplicate_of:<store_id>`). None were duplicates.
    - They use first-party or ATP coordinates where available. Otherwise they use the v5 values with the flag `v5_user_approved` and `source_id = marriott-v5-user-approved-2026-10-18`.
  - `marriott_dropped_us.csv` now has 36 rows (23 with no coordinates and no address, 12 with no QID, 1 with no store_id). They stay out under the existing rules.

**Governments (bc02908) → `entity`.**
- IDs: `state:<FIPS>` equals the registry id (same row). `cog:<PID6>` units dedupe against registry rows by `cog_pid6` first, then GEOID + layer (§15.2); school districts by `nces_leaid` = school GEOID. `fr:<id>`, `bia:<slug>` are new entities. `id_registry.csv` (`entity_id, source_key, first_seen`) → `entity_alias` (`kind = external_id`), so a refresh never re-mints an id.
- `type` → `entity.kind`: `county`, `municipality`, `township` as-is; `school_district` + subtype `unified`/`elementary`/`secondary` → `school_unified`/`school_elementary`/`school_secondary`; other school subtypes, `special_district`, `federal_agency`, `tribe` → `government_other` with `type` = the bot's type and `meta.subtype`.
- `gov_status` (bot vocabulary `independent` / `dependent` / `federally_recognized`) → `entity.gov_status` `government` / `dependent` / `government` (+ `meta.recognition = 'federal'`).
- `parent_id` (`state:..`, `fr:..`, `nation:us`), `valid_from`/`valid_to`, `flags` (`owner_unknown`, `qid_by_*`), `wikidata_qid` and `nces_leaid` (→ `entity_alias` external ids), `tiger_status`, `geoid_match` → columns / meta.
- `governments_geoid_xwalk.csv` → `entity_geoid`. Its `relation` vocabulary is wider than the registry's (`balance_place`, `consolidated_city` on layer `concity`, `county_part`, `prior_vintage_code`, `predecessor_code`, `trust_land`, a `;shared_area` suffix), so `entity_geoid.relation` stays open text. Rows with `vintage` 2022/2020 (`tiger_status = absent_2024`) resolve to no current unit and are kept for history. `aiannh` GEOIDs have no v3 boundary set yet: kept in `entity_geoid`, no `entity_unit` until a tribal-areas set exists (v3.x).

**Feed map (d332210) → `entity_feed_map`.**
- `entity_feed_map.csv` (`feed, feed_entity_id, feed_type, entity_id, match, note, source_id`; 93,278 rows, all `governments-bot`) maps to `feed`, `feed_id`, `feed_type`, `entity_id`, `match`, `note` and `source_id`.
- `status` is derived:

  | `status` | Rule | Rows |
  |---|---|---|
  | `mapped` | `entity_id` filled | 51,695 |
  | `feed_only` | note `feed_only:special_district` / `tribe` / `federal_agency` (39,555 / 577 / 473) | 40,605 |
  | `unmapped` | note `no_geoid_or_cog_link` (973), plus the 5 `conflict(see entity_gaps)` rows before the consolidated rule below | 978 |

- **Consolidated city-counties** are two entities: the county (`county:<GEOID>`) and the place (`muni:place:<GEOID>`, the "balance" place). They are linked by `entity_relation` with `relation = 'consolidated_with'` (parent = county, child = place).
  - The CoG id maps to the **county** entity, with `status = mapped` and `note = consolidated`.
  - The five CoG ids that `entity_feed_map.csv` still leaves unmapped as `conflict(see entity_gaps)` at d332210, and the loader maps this way:

    | CoG id | Government | County entity | Place entity |
    |---|---|---|---|
    | `cog:161834` | Athens-Clarke County unified government, GA | `county:13059` | `muni:place:1303440` |
    | `cog:164742` | Unified Government of Greeley County, KS | `county:20071` | `muni:place:2028412` |
    | `cog:165866` | Louisville-Jefferson County metro government, KY | `county:21111` | `muni:place:2148006` |
    | `cog:108124` | Butte-Silver Bow, MT | `county:30093` | `muni:place:3011397` |
    | `cog:175728` | Nashville-Davidson metropolitan government, TN | `county:47037` | `muni:place:4752006` |

  - Honolulu (`cog:183701`) is already mapped to `county:15003` in the file. Its only place entity is the Urban Honolulu CDP (`muni:place:1571550`, unincorporated). That is not a consolidated government, so it gets no `consolidated_with` row unless Institutions decides otherwise.

### 9.7 Companies organizations (data/companies 7022011)

`organizations/` adds one `entity` per organization plus `<stem>_locations.csv`, loaded only with `--include=companies` and the live size gate:

- `colleges_us`: 5,731 Title IV institutions (nonprofit 3,591, company 2,140) and 5,731 `establishment_at` campuses. 2,450 entity ids are `ipeds:<UNITID>` (six digits). The UNITID is also `entity_alias` scheme `ipeds`. A later QID match records `entity_merge` rule `ipeds_to_qid` and keeps the old id.
- `airlines_world`: 5,888 companies and 3,911 `hq_in` rows.
- `telecoms_world`: 2,954 entries (1,982 company, 972 brand) and 2,098 `hq_in` rows.

`hq_in` outside the US keeps `boundary_set` null and still stores the point. US rows keep `v2-2024` when the file says so. Source-specific columns go to `entity.meta`, except `inception` (`entity.inception`, source `wikidata:P571`; a year is kept, including years before 2016), `dissolved` (`valid_to`), `corporate_qid` / `ultimate_parent_qid` / `system_entity_id` / `main_campus_entity_id` / airline `parent_entity_id` (`entity_relation` `parent_org`, and only when that entity exists), and logos (`entity_image` under the public/attribution rules). `*_dropped.csv` and `*_summary.json` are not loaded.

Institution history, separate from these company dates, is cut at 2016-01-01: `valid_from` and `inception` before that day are stored null. A row missing from a later institution feed is marked `feed_absent`. Its id is not deleted and not reused.

**Officeholders (c830581, f1d64f6).** Rows now carry `boundary_set` (`tiger-2020-cd116` / `v2-2024`): the loader resolves `unit_id` through that slug (replaces the `unit_vintage` guess). `county_government.csv` is now derived from the Governments check, with `gov_status` `government` / `dependent` / `area_only` (matches the `entity.gov_status` CHECK) and `govbot_entity_id` → `entity_alias` (`external_id`) linking `county:<GEOID>` to `cog:<PID6>`.
