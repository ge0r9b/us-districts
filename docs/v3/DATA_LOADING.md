# v3 data loading plan (Phase 1)

> Plan only. Nothing has been loaded and no database exists yet. Data files belong to the data lanes (REPO-RULES: Election Data owns `data-v3/results/`, Geo & Institution Data owns `data-v3/geo/`). v3 only reads them.

## 0a. Scope: US only (D25, user ruling Oct 19, 2026)
v3 is US-only: the 50 states, DC and the US territories (PR, VI, GU, AS, MP). All Canada and other foreign work is **parked**: Canada 2021 geography and the 24 Canadian boundary sets, FR/DE/GB and other foreign governments (`load_group` 2, `institutions-foreign`), foreign subdivisions/nations beyond what US screens need, and brand locations with a non-US `country_code`. Loaders must not load them by default, and v3 screens must not show them. Each country gets its own repo later. Sections below that describe foreign inputs are kept for that future repo and are marked parked.

Neon audit (Oct 19, 2026, read-only): foreign rows are already loaded: about 70,800 `entity` rows (~32 MiB with indexes) and about 107,200 `entity_location` rows (~39 MiB with indexes), plus 24 Canadian `boundary_set` rows (no Canadian `unit` rows). Freeing them needs a separate go-ahead.

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
- **World geography (non-US):** **PARKED (user ruling, Oct 19, 2026: v3 is US-only; see D25).**
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
- **PARKED (user ruling, Oct 19, 2026: v3 is US-only; see D25).** **Canada (data/inst-canada b4dc491, `data-v3/inst/ca/`; D23 resolved: loads in v3.1, v3-only, no v2 JSON):**
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
  - **Courts, US Senate and bodies (rulings to Institutions, Oct 18, 2026):**
    - New kind **`court`**, id `court:<state>-<slug>`. It covers 35 state supreme courts plus the Texas and Oklahoma courts of criminal appeals. Each court's parent is its state government (`parent_id = state:<FIPS>`). Courts not covered are gaps with reason `not_in_seating_charts`.
    - **`us-senate`** is a frozen id, mirroring the registry's frozen `us-house`.
    - **`body_entity`** (`body_key` PK, `entity_id`, `role` in council / mayor / chamber / court / board, `source_record_id`):
      - Officeholders (`officeholder.body_key`) and seat links (`entity_unit.body_key` on `seat_district` rows) point at a body, not straight at an entity.
      - Several bodies can share one entity. For example, NYC's council and its mayor both point at the municipal entity.
      - Chambers get a body row with `body_key` = the chamber id and `role = chamber`. Courts get one with `role = court`.
      - There is no `entity.body_key`.
  - **Canadian governments and First Nations (3bbb54a):**
    - Ids are `municipality:ca-<CSDUID>` (kind `municipality`) and `county:ca-<CDUID>` (kind `county`, for county and regional governments). SCHEMA.sql checks both.
    - First Nations use the new kind `indigenous_government` (US tribes can move to it later), with id `first_nation:ca-<band number>` from the CIRNAC band list. These are not minted from StatCan's First Nations CSD types, because one band can hold many reserves.
    - Reserve, settlement and land CSDs stay `ca_csd` units, linked to their First Nation by `entity_unit` with `role = 'reserve_of'`.
    - **`reserve_of` (data/inst-canada 0e83355, `entity_unit_ca.csv`):**
      - **How the links are made:** NRCan reserve polygons (Aboriginal Lands, edition 2.189) are overlaid on the 2021 First Nations CSDs (the 8 First Nations CSD types), with areas computed in Albers equal-area (ESRI:102001). A reserve–CSD pair links when the overlap is at least 50% of either area.
      - **Shape of the data:** many-to-many, one row per (band, CSD, reserve).
        - `source_record_id` is a single `isc_reserve_no` (`isc_reserve_no=06000`).
        - Every link is approximate (≈): `method = overlay`, `is_estimate = true`, plus `share_of_geoid_in_entity` (share of the CSD inside the reserve) and `share_of_entity_in_geoid` (share of the reserve inside the CSD).
        - `source_id` (`;`-list) → `entity_unit_source`. `flags` (`shared_reserve`, `several_reserves_in_csd`) → `flags`.
      - **Counts:**
        - 1,162 links covering 1,059 reserves.
        - 571 of 638 bands have links.
        - 996 of the 1,028 First Nations CSDs are linked. The other 32 have no band (flag `fn_csd_without_band`).
        - `gaps_ca_reserve_overlay.csv` has 2,631 gaps: 361 below-threshold overlaps plus 2,270 reserves flagged `no_csd`.
        - `gaps_ca_indigenous.csv` has another 146 gaps.
      - **Why an overlay:** no StatCan 2021 file maps reserves to CSDUIDs. StatCan's correspondence files cover only dissemination blocks (DB) and dissemination areas (DA).
    - **`first_nation_reserves_ca.csv` (b8acf34):** one row per band × reserve, 3,543 rows.
      - New columns: `csd_unit_key` (one CSDUID, or two joined with `;`), `csd_link_count` (0 / 1 / 2) and `csd_boundary_set` (`statcan-2021-csd`). `csd_boundary_set` is filled only on linked rows (1,140) and is empty on the other 2,403.
      - Status is one of `csd_linked`, `below_threshold` or `no_csd`, optionally followed by `also_below_threshold_overlaps:N`. There is no separate status column: the status lives in `flags`, alongside `shared_reserve` (e.g. `shared_reserve;csd_linked;also_below_threshold_overlaps:2`). The loader reads it from there.
      - Counts:

        | Status | Rows | Reserves |
        |---|---|---|
        | `csd_linked`, one CSD | 1,118 | 1,051 |
        | `csd_linked`, two CSDs | 22 | 8 |
        | `below_threshold` | 157 | 151 |
        | `no_csd` | 2,246 | 2,119 |
        | **Total** | **3,543** | **3,329** |

      - Links sum to 1,162 (1,118 + 2 × 22) and match `entity_unit_ca.csv` row for row. The file is a cross-check only; `reserve_of` loads from `entity_unit_ca.csv`.
    - Xwalk relation **`part`** (with `share_of_geoid_in_entity` / `share_of_entity_in_geoid`) covers the two municipalities that span a provincial border, each with a CSD in both provinces: Flin Flon (`4621064` MB + `4718052` SK) and Lloydminster (`4810039` AB + `4717029` SK).
    - Boundary sets `eq-2022-ced` (125) and `eq-2022-sv` (17,745, key `<CO_CEP>:<NO_SV>`), from the 2022 Quebec general election, are registered as not current.
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
- **Rulings and data at data/inst-entities 4215fab:**
  - **Counts:** 58,219 entities, including **305 `tx-tceq` special districts** (parent `state:48`; 291 of them also have an `in_county` relation), and 711 gaps. `entity_relations.csv` has 4,153 rows: parent 3,857, in_county 291, consolidated_with 5.
  - **`entity_relation.method`** is one of `sourced`, `overlay`, `point_in_polygon` or `manual`. The new relation type is **`in_county`** (a special district's primary county).
  - **`valid_from`** holds the TCEQ creation date (special districts) and the Census incorporation date (municipalities and other governments), with its source in `valid_from_source`. 321 rows have one.
  - **Inception precision** is `day`, `month` or `year`. Year-only values are stored as Jan 1 (`YYYY-01-01`). At 4215fab, 139 have day precision and 34 year.
  - **Images:**
    - Free images get `source_url`, `attribution` and licence backfilled from the Commons file metadata (`extmetadata`: `LicenseShortName`, `Artist` / `Credit`, the file page).
    - Any row still missing a licence or an attribution after that becomes `public = false`.
    - **`public` means a free licence**, including `LicenseRef-Copyrighted-free-use` and attribution-only licences (`LicenseRef-Attribution`). Attribution is required whenever `public = true` (a CHECK enforces it).
- **Rulings to Institutions (Oct 18, 2026) and counts at data/inst-entities 574c290:**
  - **Counts:** 57,914 entities, 9,846 images, 3,381 icons, 1,233 gaps.
  - **Kind `special_district`:** frozen ids `special_district:<st>-<source>-<source_id>`. The first 305 are `tx-tceq` (Texas Commission on Environmental Quality). Each has a `parent` relation to its state. None are in 574c290 yet.
  - **`constituent_qid`:** the constituent country's Wikidata item where it differs from the state's own item (`nation:dk` → `Q35`, `nation:nl` → `Q55`). It is stored bare, as in the file.
  - **Founding dates:**
    - **`inception`** (+ `inception_precision`, `inception_source`) is the earliest sourced founding date, from Wikidata P571. A year-only date is stored as `YYYY-01-01` with precision `year`.
    - **`valid_from`** now means only the start of the **current form of government**, and only when a source states it. The file's `valid_from_source` → `entity.valid_from_source`.
  - **Images:**
    - Agency (`fr:*`) and BIA (`bia:*`) images stay **feed_only**: `entity_id` is null and `feed_entity_id` is set.
    - Hidden fair-use images (`public = false`) must carry licence, attribution and `source_url` (a CHECK enforces it). They may have no Commons file.
- **PARKED (user ruling, Oct 19, 2026: v3 is US-only; see D25).** **Rulings to Institutions (Oct 18, 2026, 15:22 ET): foreign local governments (DE, FR, GB, ...):**
  - **Ids** are frozen at minting as `<kind>:<cc>-<code at minting>`. Examples: `municipality:de-091620000000`, `municipality:fr-75056`, `county:fr-01`, `submunicipal:fr-comd-77316`.
    - `gss:`, `de-ars:`, `fr-cog:<level>:` and `fr-siren:` are **feed ids only**. They go to `entity_feed_map` (`feed_id`) and `entity_alias` (`external_id`), never to `entity_id` (a CHECK rejects them).
    - The **current** code goes in `entity.code_scheme` / `entity.code` (e.g. `de-ars` / `091620000000`, `fr-cog:commune` / `75056`).
    - If the code changes but it is the same government, the id stays and only `code_scheme`/`code` are updated.
    - A **new government** (merger, split, new commune) gets a new id plus an `entity_relation` `predecessor` row (`parent_id` = old, `child_id` = new). The same pair goes to `entity_succession`.
  - **Kinds:** `county`, `municipality`, `local_authority`, `regional_authority`, `intermunicipal`, `submunicipal`, `parish`. Foreign rows of these kinds must have `country`, and their id must start `<kind>:<country>-`.
    - A **kreisfreie Stadt** is a `municipality` with the flag `county_powers`.
    - The **FR régions** are councils of kind `regional_authority`. The région **areas** stay `subdivision:<iso>`.
    - **Regierungsbezirke** and **erfüllende Gemeinde** rows are feed-only: `entity_feed_map.status = 'feed_only'`, with no entity.
  - **`gov_status`:**
    - `government`: a body with a council, including indirectly elected ones.
    - `administrative`: an intermunicipal body with no council.
    - `dependent`: submunicipal.
    - `unknown`: parish, until its council status is sourced.
  - **Guadeloupe and Réunion:** `territory:gp` and `territory:re` stay the area. The département council (`county`) and the région council (`regional_authority`) are child entities (`parent_id` = the territory), and the communes sit under the département council.
  - **Coverage:** all parishes and all FR sub-municipal units are minted. There are no caps.
  - **Dates:** `valid_from` is carried with a required `valid_from_source` (a CHECK enforces it whenever `valid_from` is set). The predecessor can stay null; such rows get the flag `predecessor_pending`.
- **Counts at data/inst-entities 1fde48d:**
  - 57,914 entities, 3,557 relations (`entity_relations.csv`), 5,553 images, 2,925 icons.
  - Kinds: municipality 19,525; township 18,076; school_unified 10,872; **subdivision 3,480**; county 3,080; school_elementary 1,952; school_secondary 481; nation 196; chamber 101 (incl. `us-senate`); territory 52; state 51; court 37; province 10; dc_council 1.
  - **Kind `subdivision`:** foreign first-level subdivisions. Ids are `subdivision:<ISO 3166-2, lowercase>` (`subdivision:ad-02`) and frozen, and the new `iso_3166_2` column holds the code (`AD-02`). Subdivisions have **no units** (flag `outside_v2_scope:no_unit_no_boundary_set`); the parent is the nation.
  - **`entity_relations.csv`** (`entity_id, relation, related_entity_id, source_id`): `parent` 3,552 and `consolidated_with` 5 → `entity_relation`. `parent` is also written to `entity.parent_id`.
  - `wikidata` is now given already prefixed (`wikidata:Q…`), so the loader no longer adds the prefix.
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
  - **At 1fde48d:** `entity_images.csv` has 5,553 rows (3,770 seals, 1,783 flags). Columns were renamed: `role`, `file`, `feed_id`, plus the new **`public`** and **`icon`**.
    - `public` = yes means a free licence (4,732 rows). The 821 fair-use rows are `public = no`.
    - `icon` = yes marks **at most one icon per entity**: the nation flag, else the seal. There are 2,925 icons, all public.
    - These map to `entity_image.public` / `entity_image.icon`. A partial unique index (`entity_image_one_icon`) enforces one icon per entity, and a CHECK enforces `icon → public`.
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
    - Cloudflare Pages serves it (D3) with `Cache-Control: public, max-age=31536000, immutable` (set in `_headers`). A changed file gets a new `?v=<sha8>`.
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
- Later versions refresh automatically: scheduled scrapes run offline on a schedule (box or CI; Workers Free caps Cron Triggers at 10 ms CPU, so on Cloudflare they would need Workers Paid), with a separate writer role, never the API's read-only role.
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
- **Superseded at inst-entities 7b9a726 / b3ead97 (Oct 18, 2026):** the map is now `pack/entity_feed_map.csv` (197,797 rows; columns `feed, feed_id, role, is_primary, entity_id, status, note, source_set`, with smallint `feed` and `status`), shipped as a pack and **not loaded into Postgres** (`load_manifest.csv` target `pack`). The rules below still describe how `status` is derived inside the pack.
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

**Officeholders (c830581, f1d64f6).** Rows now carry `boundary_set` (`tiger-2020-cd116` / `v2-2024`): the loader resolves `unit_id` through that slug (replaces the `unit_vintage` guess). `county_government.csv` is now derived from the Governments check, with `gov_status` `government` / `dependent` / `area_only` (matches the `entity.gov_status` CHECK) and `govbot_entity_id` → `entity_alias` (`external_id`) linking `county:<GEOID>` to `cog:<PID6>`.

### 9.5 Drift check, Oct 18, 2026 12:00 EDT (main 615fa5a Build 1576; data/election 3edd314, data/geo 1b9f2ae, data/companies 051406b, data/governments 2dfc48f, data/inst-entities e661d9e, data/inst-officeholders ffdf738; new lanes data/seating 9783f53, data/people 3d26488, data/inst-canada b8acf34, perf/speed-baseline e6bd50c)

**Canada results (data/election 4c15ee6..3edd314, v3.1 with D23).** `data-v3/results/CA/` uses the 14-column row format with `office` = `ca_house_of_commons`, `qc_national_assembly`, `on_legislature`, `bc_legislature`, `ab_legislature` and `unit_type` values beyond the six registered ones. SCHEMA.sql now registers `ca_advance_area`, `ca_advance`, `ca_special`, `ca_voting_place` and `ca_ppoll_unmapped`.
- `ca_advance_area` (`<FED>:6xx`): votes never split; its member PDs come from `federal/advance_areas_<year>.csv.gz` → `unit_member (unit_id, member_unit_id)` and its geometry is built as the union at load. Validation: every member PD must exist in `ec-<year>-pd`.
- Polygon-less types (`ca_advance`, `ca_special`, `ca_voting_place`, `ca_ppoll_unmapped`) load as units with null geometry under the riding's set; they feed riding/province/national totals only and never draw.
- On-polygon shares to show in the load report: federal 2025 93.81 %, 2021 93.93 %, 2019 96.46 %; QC 2022 62.44 % (100 % of election-day votes); ON 2025 and BC 2024 0 %; AB 2023 and QC 2026 riding level only. Riding totals equal the official tables in every file (343/343, 338/338, 125/125, 124/124, 93/93, 87/87, 127/127).
- QC 2022 sections key on `eq-2022-sv` (inst-canada 3bbb54a), so v3 keeps two QC section sets (2022 and 2026) with no crosswalk between them.

**Geo (1b9f2ae).** Canada 2021 StatCan geometry is no longer blocked: `ca_pr`, `ca_cd`, `ca_csd` (5,161), `ca_fed2013`, `ca_fed2023` CSVs plus `ca_csd_fed` / `ca_fed2013_2023` crosswalks, with GeoJSON regenerated locally by `tools/canada2021_geojson.py` (gzipped, not all in git). This clears the "StatCan CD/CSD geometry blocked" note under D23. Tribal areas (ed866a4): AIANNH 864, ANRC 12, AITSN 484, GEOID-keyed; this is the tribal-areas boundary set the Governments `aiannh` GEOIDs were waiting for (`tiger-2024-aiannh`, `-anrc`, `-aitsn`; v3.1 with the institution lists), and Governments confirms 376/376 tribe GEOID pairs join (8e6d3bf).

**Companies (051406b): now global, about 5x the D21 size.** `company_locations.csv.gz` has **193,193 rows (6.8 MB gz)**: 90,767 with a `v2-2024` county GEOID and 102,410 outside the US (Starbucks, McDonald's in 68 countries, Hilton, IHG, Choice, 7-Eleven, Circle K, Buc-ee's, Target, Best Buy, Lowe's, Home Depot, Walmart US/CA/PR, Marriott global).
- Loader: `country_code` becomes a real `entity_location.country_code char(2)` column (not only `meta`), indexed, because the institution filter and the geography filter both need it. Non-US rows keep `geoid`/`boundary_set` null.
- Serving: the D21 estimate (1.4 MB gz file, 10–20 MB in Postgres) is out of date. Locations must not ship as one pack. They go to a clustered PMTiles point layer (per brand, built at load) plus `/api/v1/locations?bbox=` for lists; Postgres size is now roughly 60–100 MB with the GiST index (estimate, not measured). Neon free tier is 0.5 GB, so watch total size once Canada results (about 1.6 M rows) and seating results also load (HOSTING_COST.md).
- `QUESTIONS.md` (051406b) asks about hotel parent gaps and older ATP runs; those are the Companies lane's questions to the user, not loader questions.

**Governments (2dfc48f).** 2,723 municipality and 1,333 township seals from enwiki as fallback images (single-file, uniqueness and not-a-state-seal rules). They load as `entity_image` with `fair_use` as given; D22 still decides what is shown publicly.

**Seating Charts (new lane, data/seating 9783f53) → bodies, seats, terms, holders, results.** `data-v3/seating/`: `bodies.csv` (189 bodies incl. US Senate/House, 99 state chambers, 37 courts, 25 city councils), `seats.csv` (8,584), `terms.csv` (19,689), `people.csv` (34,457; `key` = `bioguide:` and other canonical ids, plus `cid` = the Election Data `candidate_id`), `composition.csv`, `contests_2026.csv`, `results_contests.csv` / `results_candidates.csv` (2016–2024 plus odd-year and specials, courts from 2017; CA, KS, WV supreme courts excluded by user request), and `holders.pack.json.gz` (1.26 MB). Mapping: `bodies.key` = `body_entity.body_key` (inst-entities e661d9e, already in SCHEMA at 9e8c8a2); `seats` → `unit` (seat units where no polygon) and `officeholder`; `terms` → `officeholder` date ranges; `people.key` → `person.person_id` (same priority scheme as §13); `people.cid` → `person_alias (kind 'candidate_id')` so results rows join to people; results rows → `contest`/`result` with `source_id` from `results_sources.csv`, and US Senate 2022/2024 stay the Election Data lane's rows (dedupe on contest key, Election Data wins). The lane writes no repo graphics and is read-only on data-v3/geo.

**People (new lane, data/people 3d26488, plan only).** Its proposed `person_id` priority (Wikidata QID first, then bioguide, ocd-person, fec, cid, name) conflicts with the scheme in SCHEMA.sql and §13 (bioguide > ocd-person > `<st>-leg`), which Officeholders and Seating already use. See DECISIONS.md D24 (proposed: keep the SCHEMA scheme, store the QID in `person.wikidata` and as an alias).

**Perf lane (perf/speed-baseline e6bd50c).** v2 Build 1575 baseline and four prototypes; what v3 takes from it is in PERFORMANCE.md "v2 measured baseline".

### 9.6 Drift check, Oct 18, 2026 14:00 EDT (main e1f9ae3 Build 1583; data/election 0e058f7, data/geo fdae0c3, data/companies c6f1cf9, data/governments bb5e342, data/inst-entities 4215fab, data/seating 06a2cc3, data/people 7dbfd95, perf/speed-baseline 1f8ae1f)
- **Senate 2022/2024 results re-cut (data/election 0e058f7).** No negative votes: "all others" is apportioned as its own component, d / r / others are rounded separately and county sums are exact by largest remainder; the writers stop on a negative. CT 2024 old-county votes are no longer dropped. NE unicameral rows are left out of `us_senate_2024_sldl` (listed in GAPS) so every sldl `unit_id` matches a unit. Loader impact: none to the schema; the §4 negative-`other` reject stays as a guard and should now fire zero times. **Any Senate rows already seeded into Neon from an earlier commit (v3/build alpha.3) must be re-upserted from 0e058f7**; the idempotent upsert (§5) replaces them in place. NE `sldl` gaps are expected, not rejects.
- **PARKED (user ruling, Oct 19, 2026: v3 is US-only; see D25).** **Canada 2021 geography (data/geo fdae0c3, Q-G11).** New CSVs `ca_pr` (13), `ca_cd` (293), `ca_fed2013` (338), `ca_fed2023` (343), plus `ca_csd_fed.csv` (CSD → FED 2013/2023 area shares) and `ca_fed2013_2023.csv` (691 overlap pairs); GeoJSON stays in `geo-data-raw/v3ca` (not in git). These line up with the §15 Canada boundary sets (`statcan-2021-cd`, `ec-2013-fed`, `ec-2023-fed`). Rules for v3.1: join provinces on code → `pruid` (NL 10 … NU 62), never on name ("Québec" vs "Quebec"); key FEDs on `fed_num` (17 names changed by Bill C-25, 2026); `ca_csd_fed` loads into `unit_crosswalk` as area-share weights; `ca_fed2013_2023` is an area overlap, not a legal "unchanged" list. Three features use 10 m server generalization (CSD 6204030, FED 59028) or a CSD union (FED 62001); rebuild them if StatCan's zips become reachable.
- **Display tier for Canada (Q-G11 point 2), recommendation:** v3 does not need separate `_lo` GeoJSON files. PR/CD stay at 50 m as the analysis and nesting layers in PostGIS; the display tier comes from the PMTiles build (zoom-dependent simplification and dropping tiny island parts at low zoom), the same as US layers. Only v2 would need a hand-made low tier, and v2 is closed to new data. Open for the orchestrator to confirm.
- **PARKED (user ruling, Oct 19, 2026: v3 is US-only; see D25).** **Governments foreign layer (bb5e342) and inst-entities 4215fab** were folded into §15 and SCHEMA in v3/plan 1bf4947, c603061, 99481d0 (subdivision kind + `iso_3166_2`, `constituent_qid`, inception vs `valid_from`, `special_district:tx-tceq-<id>`, image public/attribution rules). No further change.
- **Companies (c6f1cf9):** about 20 more grocery chains as `locations/<brand>.csv` (ATP, CC0); same row format, loads through §15 with no change. Full coverage stays the rule (no caps).
- **Seating (06a2cc3):** Indianapolis, SF, Nashville, DC and Louisville councils and mayors added (bodies 188–197); DC keys `chamber:dc-council` / `state:11` already in §15.
- **People (7dbfd95):** D24 as settled (bioguide > ocd-person > st-leg > …, QID in `person.wikidata`).

### 9.7 Drift check, Oct 18, 2026 16:00 EDT (main ae92b92 Build 1584; data/companies 7022011, data/geo a92f2b0, data/governments 310086f, data/inst-entities f0f1f6d, perf/speed-baseline 5cd2898, qa/bugs f1a097c; v3/build 20e8b3d)
- **Companies organizations (data/companies 6365949, c2967f0, 7022011).** New `organizations/` files, one `entity` row per organization plus loader rows in `<stem>_locations.csv` (same columns as `company_locations.csv.gz`): `colleges_us` (5,731 IPEDS Title IV institutions, kinds `nonprofit` 3,591 / `company` 2,140, 5,731 `establishment_at` campuses, 5,597 in `v2-2024` counties), `airlines_world` (5,888 `company`, active and defunct, 3,911 `hq_in`) and `telecoms_world` (2,954: 1,982 `company`, 972 `brand`; 2,098 `hq_in`). These are the first `hq_in` rows; most are outside the US, so `boundary_set` and `unit_id` stay null (the §15 non-US rule) and the point still renders. Source-specific columns (IPEDS `unitid`/`opeid`/`ein`/`sector`/`level`/`carnegie_*`/`hbcu`/`tribal`/`land_grant`/`system_entity_id`/`main_campus_entity_id`; telecom `service_type`/`mcc`/`mnc`; `active`, `inception`, `dissolved`, `corporate_qid`, `ultimate_parent_qid`, logo fields) go to `entity.meta`, except `inception` (→ `entity.inception`, source `wikidata:P571`), `dissolved` (→ `valid_to`), `corporate_qid` / `ultimate_parent_qid` when they differ from the row (→ `entity_relation parent_org`), `system_entity_id` / `main_campus_entity_id` (→ `entity_relation parent_org`), and logos (→ `entity_image` under the same public/attribution rules). `*_dropped.csv` and `*_summary.json` are reports, not loaded.
- **New id scheme `ipeds:<UNITID>` (2,450 of 5,731 colleges).** Used when no single Wikidata item carries that UNITID as P1771. The plan's CHECK (and `v3/db/migrations/004_entities.sql` on v3/build) only allowed `wikidata:Q…` / `usd:<uuid>` for these kinds, so the load would reject them. SCHEMA.sql now also allows `ipeds:[0-9]{6}`; the UNITID also goes to `entity_alias` (scheme `ipeds`), and a later QID match re-keys through `entity_merge` (rule `ipeds_to_qid`), the same pattern as `usd:`. **v3/build needs the same one-line CHECK change** before it loads colleges.
- **PARKED (user ruling, Oct 19, 2026: v3 is US-only; see D25).** **UK, Germany and France boundary indexes (data/geo, Q-G12).** CSV indexes for `gb_lad` (361, May 2026), `gb_ctyua` (218), `gb_cauth` (15), `gb_par` (11,542 parishes/communities/non-parished areas); `de_lan`/`de_krs`/`de_vwg`/`de_gem` (VG250 01.01.2026); `fr_reg`/`fr_dep`/`fr_com`/`fr_epci`/`fr_cad`/`fr_com_om` (ADMIN EXPRESS COG 2026); GeoJSON is built by `tools/foreign_geojson.py` outside git. Vintages and keys are in `data-v3/geo/FOREIGN_VINTAGES.md`. For v3 these become registered boundary sets (`ons-2026-lad`, `bkg-2026-gem`, `ign-cog2026-com`, … named at load from FOREIGN_VINTAGES) so foreign governments get `entity_unit` rows instead of staying entity-only; join keys are GSS, ARS and INSEE/SIREN, and `fr_cad` must be keyed on **(code, type)** because 582 communes déléguées share their parent's INSEE code. Governments' `boundary_xwalk` (re-keyed to the same editions in b198633) is the bridge, so no Governments rows change. Open in Q-G12 (lane-level, not user): which 8 of the 13 old / 3 new German 2026 codes Governments means, and 10 FR communes déléguées IGN has no polygon for (entity-only until it does).
- **PARKED (user ruling, Oct 19, 2026: v3 is US-only; see D25).** **Governments foreign history (e0ee04c, 310086f).** Terminated codes are rows with `is_active=N` and new `predecessor_id` / `successor_id` columns (GB 3,402 RGC codes, FR 1,812 communes since 1943; DE history not built). These map to `entity_succession` / the `predecessor` relation under the ed669fa ruling; the feed ids (`gss:`, `de-ars:`, `fr-cog:`, `fr-siren:`) are still mapped to frozen `<kind>:<cc>-<code>` ids at load, and GP/RE are areas with council children as already ruled. No plan change.
- **inst-entities f0f1f6d:** image licence fields (`licence_url`, Commons attribution, image-override module). Same `entity_image` columns; no change.
- **Build 1584 (main ae92b92):** speed patches D/E and idle warm-up for state senate/house/school districts. Parity items added to MIGRATION_CHECKLIST.md; the v3 shell at 20e8b3d applies 1577–1583, so 1584 is still to port.

### 9.8 Drift check, Oct 18, 2026 18:05 EDT (us-districts main 0c711df Build 1587; data/governments bd0ce1a, data/inst-entities b3ead97, perf/speed-baseline e128cf7, qa/bugs cc521df; ge0r9b/v3 v3/build c37d0d3)
- **History cutoff 2016-01-01 (data/governments bd0ce1a; user via the Governments bot).** `HISTORY_CUTOFF` in `scripts/common.py`: ended rows from before 2016 are not written (GB 2,347, FR 3,224; US, DE and other foreign 0), links to them are dropped, and `valid_from` before 2016 is cleared (170 Wikidata P571 dates on nations, dependencies and subdivisions; 459 FR communes). Pruned ids stay in `id_registry/*.csv` with a `pruned` column, so a refresh never re-mints them. DE history is limited to the 2026 VG250 change. For v3: the loader treats a `pruned` registry row as a reserved `entity_alias` with no entity, `entity_succession` / `predecessor` relations only reach back to 2016, and a null `valid_from` means "before 2016 or unknown", never "new". The same cutoff applies to every institution feed.
- **inst-entities 04227d3 → 7b9a726 → b3ead97 (the Oct 18 Full Stack rulings, now built).** 122,329 entity rows, including the GB/DE/FR country layers under frozen `<kind>:<cc>-<code>` ids; 40,554 relations (new `member_of`; the Corse intercommunal parent is the Collectivité de Corse council); 9,846 images; 58,663 crosswalk rows; 198 body rows. New files: `load_manifest.csv` (load order and target per file), `source_sets.csv`, the `enum_*` lookups, and `pack/entity_feed_map.csv` (see the feed map note in §15). `v2_row` / `v2_key` moved to `entity_v2_rows.csv` (repo only, not loaded). `gov_status` gains `unknown`. SCHEMA.md documents the new tables; v3/build loads exactly what `load_manifest.csv` marks `db` (c37d0d3), with load group 2 behind a flag (c64046d).
- **v3/build 2355ec9 → c37d0d3 (ge0r9b/v3).** The `ipeds:` CHECK is fixed (248efb4), so the 16:00 flag is closed. The API now runs as a Cloudflare Worker (`v3/worker/index.ts`, `v3/wrangler.toml` with `DATABASE_URL` as a secret and `.dev.vars` locally; it fails closed for any non-`neon.tech` host), and a static pack build (`v3/scripts/export-static.ts`) produces the Pages files. The static shell was dropped (4ab1061), which matches the user's call that the preview goes on Cloudflare, not the us-districts site; ARCHITECTURE §5c, D3, D17 and HOSTING_COST now say so. Also loaded: 2020 and 2024 Alaska, DC and state president totals (d4a569d); the API serves DC scope, same-name labels and "Georgia" search (f9a96de), which are the v3 answers to QA-072 and QA-075. Build 1584 list checks are ported (248efb4); 1585–1587 are still to port (MIGRATION_CHECKLIST).
- **Builds 1585–1587 (main 0c711df)** are UI-only (bars on thumbnail rows, pie placement, menus as overlays, sort chip position); no data or field changes. Parity items and the 14 new or changed tests in `tests/` are in MIGRATION_CHECKLIST.md. **perf/speed-baseline e128cf7:** 1585 matches 1584 within noise, so the 1584 perf bar stands. Still no `v2.0` tag.

### 9.9 Drift check, Oct 18, 2026 20:05 EDT (us-districts main 3fc48e5 Build 1592; qa/bugs 438a549, perf/speed-baseline 5e92d72, new native/ios-v2 5b74850; ge0r9b/v3 v3/build bd7e0a9)
- **Data branches unchanged** on both repos since 18:05; no us-districts `data/*` branch is ahead of ge0r9b/v3. Still no `v2.0` tag.
- **Build 1589 (CRITICAL in v2), two data rules for v3.** (1) District maps colour by the selected year's own margin: 2016 district layers must use the 2016 result, never fall through to the 2020→2024 shift colours. In v3 the fill comes from the year's pack (`results/<year>/<set>`), so the colour function must take the year as an input, with a parity test per year × level (`tests/colors-2016.py`: Philadelphia, Brooklyn and DC blue, rural PA red; US, PA, US House, state senate and state house × '16/'20/'24). (2) **DC's delegate seat (at-large 1198) takes DC's statewide presidential result** for 2016, the same as the 2020/2024 DC triples already loaded (d4a569d). The election loader must emit a 2016 DC delegate-seat row (or the pack builder must alias it to DC statewide); check before the 2016 pack is cut.
- **Build 1588, sort rule change (affects `@usd/core` `sortRows`).** High to low with every answer shown now ranks rows by **total votes cast** (all candidates plus Other), in both % and # modes, stacked and split bars, every year. Only when exactly one answer is toggled on does it rank by that answer (its share in %, its votes in #). A range keeps |net change| as displayed. v3/build's `sortRows` sorts by the selected answer's share or votes, so it needs a `total` key and the one-answer rule (MIGRATION_CHECKLIST).
- **Build 1588, district labels.** District-type lists show only the number (`1`, `4`, `17`), and seat 0 / AL reads **"At-large"** (DC, Alaska, Wyoming). This settles the 18:05 "District 00" proposal: v3 follows v2 and labels it At-large. QA-080 (low, open question): the nationwide US House list still reads `DE-00`.
- **Builds 1590–1592 (UI only).** Sort chip on its own header row (QA-044); split-bar lists share one scale (QA-078, already in v3/build 7013d5f); range bars stay on the icon rows with the time row closed (QA-077); top row flush to the safe-area top; turning the chart off returns to the view it was opened from (QA-079). Parity items in MIGRATION_CHECKLIST.
- **perf/speed-baseline 5e92d72:** 1588 within noise of 1585 (taps all under 100 ms medians, iPad pan 47.7 fps), so the 1584 bar stands and iPad pan ≥ 55 fps remains a v3 gate.
- **native/ios-v2 5b74850 (us-districts):** an unsigned SwiftUI web-view shell around the live v2 page with an offline disk cache, built by GitHub Actions for the user to sign. It's the user's small v2 native app, not v3; it changes nothing in this plan (NATIVE.md note).
- **v3/build c37d0d3 → bd7e0a9:** versioned result packs, map clicks and name search local from `bbox.json` + PMTiles + `names.json`, one Neon statement per Worker pick/search/geocode, geocode cache, `npm test` on in-memory PGlite (101 pass), table compaction under the Neon cap, Wrangler pinned 4.86.0, DC outline attached. Matches ARCHITECTURE §5c; no doc drift.

### 9.10 Drift check, Oct 18, 2026 22:00 EDT (us-districts main c34d398 Build 1595; qa/bugs 0997a90, perf/speed-baseline 1b4d427, new preview/shadows 4394663; ge0r9b/v3 v3/build 0a39df5)
- **No data or field changes.** Builds 1593–1595 are UI only, and every data/* branch is unchanged on both repos. Still no v2.0 tag.
- **Builds 1593–1595:** names at x=52 in every list mode (QA-081), `DE At-large` nationwide (QA-080), the 1590 sort-chip header band replaced by a floating chip that nudges labels aside (1594), chip fixed at rest (QA-083), clearer unselected glass buttons and opaque text fields (1594), and state outlines on top and thicker (1595). Parity items in MIGRATION_CHECKLIST.
- **v3/build 42ac077–0a39df5:** total-votes sort, per-year colours with the 2016 DC delegate seat, local pick from decoded tiles with a bbox pre-filter, a split map bundle, and a preloaded map chunk. That closes the 1588 and 1589 flags.
- **perf 1b4d427:** 1595 within noise of 1588; iPad pan 47.9 fps keeps the ≥ 55 fps gate open.
- **preview/shadows** is a preview lane, not main. It isn't parity until a v2 build adopts it.

### 9.11 Drift check, Oct 19, 2026 00:00 EDT (us-districts main f9e148f Build 1597; qa/bugs 71e0b5d; ge0r9b/v3 unchanged, v3/build 0a39df5)
- **No data or field changes.** Builds 1596–1597 are UI only, and every data/* branch is unchanged on both repos. Still no v2.0 tag.
- **Build 1596:** US House inside a county lists that county's US House districts with split ones marked ≈ (QA-005 fixed), and row taps hit-test at the finger's real point. In v3 the county list needs a county-to-district overlap with whole versus partial flags, served by `/api/v1` and baked into the static pack.
- **Build 1597:** the name bubble sits beside the photo, never over a value label or another photo (QA-076).
- **QA passes 23–24:** new QA-084 HIGH (split-bar rows draw at 30 px then 44 px) and QA-085 HIGH (year taps on PA district-type maps 150–425 ms). Both are v3 gates in MIGRATION_CHECKLIST.
- **main now has `previews/shadows/` and `previews/compact/`** (noindex, built by `tools/mkpreview.py`, loading v2 data). They're proposals until a v2 build adopts them.


### 9.12 Drift check, Oct 19, 2026 02:00 EDT (us-districts main c19f7a0 Build 1599; qa/bugs 136695c; ge0r9b/v3 v3/build 8324e6f)
- **No data or field changes.** Builds 1598–1599 touch only `v2/index.html` and tests, and every data/* branch is unchanged on both repos. Still no v2.0 tag.
- **Build 1598:** split-bar rows draw at 44 px in the first frame (QA-084, partly verified in pass 25).
- **Build 1599:** year taps recolour district maps in place and prefetch other years when the time row opens (QA-085), boundary slivers drop out of county town lists (QA-006), fuzzy search only as a fallback (QA-067), plus QA-051, QA-061, QA-068, QA-069 and QA-086 fixes. The sliver rule needs a minimum-overlap threshold in the county-to-town overlap the loader bakes into the pack.
- **v3/build 8324e6f:** year changes restyle the loaded map with feature-state (no tile reload) and split rows are locked at 44 px; perf:client now checks both. This covers the QA-084 and QA-085 gates for state, county and US House; PA state legislative maps and WebKit first visits are still to be checked.

### 9.13 Drift check, Oct 19, 2026 04:00 EDT (us-districts main 5850c12 Build 1604; qa/bugs cced02f pass 26; ge0r9b/v3 unchanged at v3/build 8324e6f)
- **No data or field changes.** Builds 1600–1604 touch only `v2/index.html` and tests, and every data/* branch is unchanged on both repos. Still no v2.0 tag.
- **Build 1600/1601:** the range-chart thumbnail bubble reads the name from `data-party` when the time row is closed (QA-086, verified fixed in pass 26). 1601 only corrects the build number (1500 was a typo).
- **Build 1602:** cached list rows are keyed by chart mode, so a bar visit's 30 px rows never show on a first split-bar visit (QA-084, verified fixed).
- **Build 1603:** in the list view, Back and drill-ins paint the list first and the map's precinct heat follows two frames later (QA-020; WebKit Back from LA County cities to CA counties 45–61 ms, was about 400–450).
- **Build 1604:** an alias hit ("America" = United States) drops typo look-alikes such as South Africa and Amelia County (QA-067; pass 26 found it still open on 1599/1601 in the real search, 1604 not yet re-verified).

### 9.14 Drift check, Oct 19, 2026 06:00 EDT (us-districts main 101924c Build 1607; qa/bugs 0551f80 passes 27–28; ge0r9b/v3 unchanged at v3/build 8324e6f)
- **No data or field changes.** Builds 1605–1607 touch only `v2/index.html` and tests (`addr-from-list.py`, `thumbs-no-drop.py`, `back-la-speed.py`, `inst-search-real.py`, `year-tap-speed.py`, `y2016-data.py`). Every data/* branch is unchanged on both repos. Still no v2.0 tag.
- **Build 1605:** an address that resolves to DC from a list view ends exactly as tapping DC in the All States list (QA-087 CRITICAL, verified fixed in pass 28). WebKit releases a field when the focused field is removed. QA-085 Chromium: county heat recoloured in place and skipped under a district fill, smaller canvas padding, empty canvases hidden.
- **Build 1606:** list thumbnails keep their place under the back chevron on every drill-in and Back (QA-089), institution search matches at word starts so "USA" no longer lists Colusa County (QA-088), and in the list view the map heat is built on idle after the rows (QA-020: Back from LA County cities shows CA rows at 158–198 ms, was 400–760).
- **Build 1607:** after a DC address search from a list view, the selected DC row is scrolled into view.

### 9.15 Drift check, Oct 19, 2026 08:00 EDT (us-districts main b3a622e Build 1610; qa/bugs 6ef3429 passes 29–30; ge0r9b/v3 v3/build 7e89357)
- **No data branch moved** on either repo, and there's still no v2.0 tag. Builds 1608–1610 touch only `v2/index.html` and tests (`addr-from-list.py`, `back-la-speed.py`, new `school-dups.py`, new draft `recheck-old.py`).
- **Build 1610 is a naming rule that touches data (QA-074):** school districts that share a name inside one state (Ohio's three "Eastern Local School District") are labelled with their county, e.g. "Eastern Local School District (Brown)". v2 computes the county at runtime from the district polygon's largest-ring centroid. v3 should do this once at load: the school-district load step computes a `county_hint` (largest-ring centroid in a county polygon, with a vertex fallback) and a `display_name` that adds the county only when (state, name) is duplicated. The names index and the API return `display_name`, so search, list rows, the bottom field and the bubble all agree. Load check: (state, display_name) is unique for every school district in every state, not only OH, TX, CA and VT.
- **v3/build 7e89357 (already reported by the build lane):** one shared `selectPlace` path for list-view address hits (QA-087), list rows painted before map heat, a detached field kept usable, timing for PA county years and list Back, "America" shown as United States, and a Neon compaction plan that refuses an over-gate load. Neon is at 316.0 MiB with almost nothing reclaimable, so about 34 MiB of headroom is left under the 350 MiB gate; the school-district `display_name` above is a few KB and fits.

### 9.16 Drift check, Oct 19, 2026 10:00 EDT (us-districts main f435ab2 Build 1611; qa/bugs 1afb5d8 passes 31–32; perf/speed-baseline 5a48ac1; data/election f940021; ge0r9b/v3 v3/build a7d0a0c)
- **Still no v2.0 tag.** data/election moved on both repos to the same f940021 (NY county NYSBOE fix); other data/* unchanged and matched. No data/* drift to flag.
- **Build 1611 (f435ab2):** QA-093 CRITICAL fixed — DC picked in All States (row tap or address) then globe → map shows DC title and DC numbers (shared DC map-side selection applied when the map opens). QA-092 fixed — All States keeps the normal zoom-4 US view (not zoom 2). `tests/list-dc-globe.py` passes WebKit and Chromium 390; title matches numbers.
- **QA passes 31–32 (new CRITICAL / HIGH still open at end of pass 32):** QA-094 CRITICAL (county city-list header shows sum of cities, not the county — Harris 56/42 vs 52/46; Miami-Dade, Maricopa); QA-095 CRITICAL (state district-list totals 0.5–3.9% below FEC — MI, NY, FL); QA-098 CRITICAL (non-DC address from All States → precinct title over county numbers, wrong winner in Phoenix); QA-103 CRITICAL (by QA-093 ruling: reload of a DC map view shows US title and US numbers over DC outline; saved `dc:1` dropped on load); QA-096 HIGH (city precinct map thumbnails lack numbers); QA-100 HIGH (NY county rows two-party only — data fix on f940021; builder merging to main). QA-097/099/102 MEDIUM, QA-101 LOW. QA-074 labels added on 1610 but still not visible through pass 32.
- **v3 rules for the new CRITICAL bugs:** one selection object drives title, numbers, outline and field (never mix units); list totals must match the unit's own result row, not a sum of children; an address from a list uses the same `selectPlace` as the place row; reload restores the exact selection including the DC flag (or, if DC is not restored, a clean US view at zoom 4 under the US title — never a mixed screen).
- **data/election f940021 (both repos):** all 62 NY county keys for 2016/2020/2024 replaced with NYSBOE official county results (`d`=Dem+WF(+WEP), `r`=Rep+Con, `total`=all candidates incl. write-ins); 2024 totals had dropped other candidates (`t=d+r`); 2016 VEST nearest-county shifts fixed; corrected CSVs in `data-v3/results/states/ny`. For v3: when election packs/load pull NY counties, use these rows; after main merge + live build, recheck Kings vs Brooklyn borough and NY state totals vs FEC.
- **v3/build 7e89357 → a7d0a0c:** c4976ed states the compact gate as 316 MiB of 350 (34 MiB headroom, unchanged); a46349b first map paint under 900 ms (WebKit preview throttle order; no double-fetch names/bbox; pick archives after paint; opening map from a focused All States row adopts that state; fresh list opens zoom-4 US — covers QA-092-style home and helps the first-paint gate); 63810fb names duplicate school districts with their county at load (`county_hint` + `display_name`; API/packs return it; colliding state refused — implements the QA-074 plan from §9.15); 37db955 saves address camera and scrolls the list once (stored view = place user picked; title stays tied to numbers; PA state-house year switch only recolours that layer — QA-091/090/093 selection integrity + QA-085 PA house path); a7d0a0c exports saved map camera helpers.
- **perf 5a48ac1 (Build 1611 vs 1595):** no regression; Back faster (27/23/27/32 ms vs 33/36/41/40); iPad pan 57.3 fps / 10 dropped (was 47.9 fps / 55 dropped) — v2 now meets ≥55 fps; keep as a v3 MapLibre gate. Phones ~59.2–59.6 fps; bytes flat.

### 9.17 Drift check, Oct 19, 2026 12:20 EDT (us-districts main 7739e72 Build 1614; qa/bugs b0ee03c passes 33–34 + hourly; perf/speed-baseline e048caa; data/election ff5f180; ge0r9b/v3 v3/build ac41801)
- **Still no v2.0 tag.** data/election moved on both repos to the same ff5f180; every other data/* branch unchanged and matched. No data/* drift to flag.
- **data/election ff5f180 — `data-v3/results/states/official_state_totals.json` (new):** certified presidential state totals for 2016, 2020 and 2024, 51 entries per year (50 states + DC), each `{d, r, total}` keyed by state name, with a per-year `source` (FEC Federal Elections 2016 and 2020 Table 2; FEC Official 2024 results). `d`/`r` fold fusion lines (Dem + WF/WEP; Rep + Con/AIP) and `total` counts every candidate and write-in. **v3 load:** ingest it as the authoritative state row for each (state, year, president) in `contest_results` (source_set `fec_certified`), and have state and national headers, thumbnails and list totals read that row, never a sum of counties, districts or precincts. Third-party share = `total − d − r` from this row. This is the data side of QA-003 under the user's standing rule (gap under 1% per precinct, under 0.1% for a large state, under 0.01% nationally; use the certified state total even when precinct sums differ; don't spend compute reconciling small gaps). Load check: every state/year header equals this file exactly; national = sum of the 51 rows.
- **Builds 1612–1614 (7beb223, 81be4c7, 7739e72):** 1612 one selection path — a searched or picked place (DC, an address's precinct) carries its selection; the map view re-applies title, numbers, outline, field and view; reload restores it from the saved `sel` (QA-103/098). A county's cities list shows the county's own result (QA-094); a state's district lists show the official state total (QA-095); a city's precinct list → globe shows the city's numbers (QA-096); school rows drop "School District"/ISD and add a short county suffix (QA-074). 1613 loads only the 62 NY county keys from f940021 into `v2/data/election2016/2020/2024.js` (QA-100) and opens the map on a DC address searched from a list (field, pin, zoom 15). 1614 makes list-view thumbnails after an address search show the searched precinct (Maricopa Precinct 242 Harris 70 / Trump 28; Leon Precinct 42 74 / 24) — the QA-098 list-view fix; QA-097 city-map reload via `children()` is WIP. New tests: `county-own-totals.py`, `ny-data.py`, `city-map-reload.py`, draft `reload-lists.py`; `list-dc-globe.py` now also asserts list view, globe and reload.
- **QA passes 33–34 + hourly (on 1612/1613):** QA-103, QA-094, QA-095 fixed in both engines; QA-100 fixed (NY state 56 / 43, Kings = NYSBOE); QA-098 fixed on the map but open in the list view on 1613 (fix shipped in 1614, not yet re-tested). New **QA-104 MEDIUM:** reload of a county map view saves `lt:none` and drops the county layer (Miami-Dade Chromium, Kings WebKit). QA-101 now LOW (Kings 27.6/70.9 vs Brooklyn 27.3/70.6; Kings list has a "New York city" row with Brooklyn's numbers — orchestrator to rule). QA-074 now about the suffix being cut by the 100 px name column. **QA-003 re-rated under the user rule:** fails are US 2024 total −0.166% (others missing), US 2020 Biden +0.0128%, NY 2020 (+0.27% Biden), PA 2020 total +0.14%, ME 2020 Biden −1.06%, and 2024 total-vote shortfalls of 0.46–1.00% in WY, ND, VT, MD, IL, WA, MA, RI, NE, NH, VA (others missing). The ff5f180 totals file above is what fixes these in v3.
- **v3/build a7d0a0c → ac41801:** 3e78429/d705566 charge school-name writes for the rows they rewrite (`IS DISTINCT FROM`), flag unit bloat and warn when a load step grows past 3× its estimate; 059285b paints the map from the HTML and gates the median; 1717c80 records Neon at 327.1 MiB of the 350 MiB gate (≈23 MiB headroom); 7969c88 loads all 62 NY counties from NYSBOE f940021 (`v3/ingest/ny-counties.ts` + test); ac41801 restores DC on reload, keeps county-city and unfocused district list titles on the parent total, titles a non-DC All States address with the place its numbers belong to, and uses the state row because district sums miss FEC by more than 0.1% (`tests/district-fec.test.ts`). It does not yet ingest ff5f180's certified totals file; the state-row rule should point at it.
- **perf e048caa (Build 1613 vs 1611):** no regression beyond noise at 4 viewports; US House pick median 75–90 ms; iPad pan 53.8 fps (was 57.3 on 1611, now just under the ≥55 fps v3 MapLibre gate — watch, don't relax the gate).

### 9.18 Drift check, Oct 19, 2026 14:00 EDT (us-districts main 9f41265 Build 1616; qa/bugs 183963c passes 35–37; perf/speed-baseline 40e4b1c; ge0r9b/v3 v3/build 9ff1c3d)
- **Still no v2.0 tag.** No data/* branch moved on either repo since 12:20; no drift to flag.
- **Build 1615 (6dfa3f1) — QA-003 under the user rule:** v2 inlines `window.__OFF` from data/election ff5f180 `official_state_totals.json` (FEC, with the NY NYSBOE and VA ELECT certified rows already in that file) and uses it for state rows, state thumbnails, state colours and the national sum; county/precinct sums are not chased. Values match ge0r9b/v3 v3/build 8bfe521 (`v3/ingest/official-states.ts`) exactly (spot-checked NY 2020, VA 2024, CA 2020). QA pass 35 verified it (orchestrator `tests/official-totals.py` 30 ok); pass 36 found all 51 rows for 2016 equal FEC exactly, national 65,853,514 / 62,984,828 / 136,669,276. Visible shift: PA '24 now 50.2 / 48.5 / 1.3 (others included), WY 2024 Trump 71.6%.
- **Build 1615 — QA-104:** the counties layer is restored on reload too (it had been skipped as the old default). v3/build 9ff1c3d does the same in `packages/core/saved-view.ts` with a test.
- **Build 1616 (9f41265):** QA-097 a city-map reload restores the city from the county's parts (verified 6 cities, both engines); QA-105 census-GEOID precinct names read "<County> Precinct <local part>" (e.g. "Dauphin Precinct 0270") and only when the id starts with the state FIPS; QA-106 the list header no longer reads "<precinct> counties". For v3: precinct `display_name` is built at load from the same rule (strip the 2-digit state + 3-digit county FIPS from a GEOID-shaped name, keep the local part, prefix the county short name); never derive the header noun from the selection.
- **perf 40e4b1c (Build 1615 vs 1613):** no regression beyond noise; iPad pan back to 57.3 fps / 10 dropped (1613 was 53.8), so v2 meets the ≥55 fps v3 gate again. First map 617–1021 ms (TTFB noise), bytes +4.5 KB gz for the totals table.
- **v3/build ac41801 → 9ff1c3d:** 8bfe521 loads the certified state totals (closes the earlier QA-003 flag), 9ff1c3d keeps the county layer on reload (QA-104). Still a draft; no deploy, no Neon load.
