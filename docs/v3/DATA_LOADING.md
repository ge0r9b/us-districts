# v3 data loading plan (Phase 1)

> Plan only. Nothing has been loaded and no database exists yet. Data files belong to the data lanes (REPO-RULES: Election Data owns `data-v3/results/`, Geo & Institution Data owns `data-v3/geo/`). v3 only reads them.

## 0. Intake paths (priority order)
1. **Primary: `data-v3/`** at the repo root (read-only for v3).
   - `data-v3/results/**.csv`: long rows in the Election Data bot format (§1). In flight on `origin/data/election` (7faa12d): `PA/pa_president_county_official.csv` (2020 + 2024), `PA/pa_president_county_official_2016.csv`, `2016/us_president_2016_state_fec.csv`, plus audit CSVs that are **not** result rows (`*_mismatches.csv`, `states/v2_state_totals_vs_official.csv`; skipped by header check R01).
   - `data-v3/geo/` (on `origin/data/geo` 6d8b443; answers in its `QUESTIONS.md`): **committed today:** GEOID tables for every v2 layer (`ushouse.csv` 436, `senate.csv` 1,950, `statehouse.csv` 4,890, `schools.csv` 13,305 with `tiger_set` unsd/elsd/scsd, `counties.csv` 3,144, `towns.csv` 1,598 Iowa townships; columns `layer, state, row, v2_name, geoid, tiger_name, tiger_set, match`), `v2_name_collisions.csv` (old → new names + GEOID), `summary.json`, `README.md`. **Decided, not yet committed:** `towns_2024.geojson` (TIGER county subdivisions, 20,935 rows, ~2.48 MB gz) and `places_2024.geojson` (TIGER places, 19,477 rows, ~4.01 MB gz), keyed by GEOID, gzipped above ~5 MB; `zcta2024.csv` (ZCTA, internal-point lat/lon, land area, from the TIGER 2024 Gazetteer, built by a script in `tools/`); `v1_towns.csv` + a places crosswalk (in progress); `entities.csv`; per-year `precincts_<year>.csv` + a 2020→2024 area crosswalk. Full-resolution TIGER is fetched from census.gov at build time, joined on `geoid` (never committed).
2. **Legacy fallback: `v2/data/*.js` only** (global-loader JS, wide `[dem, rep, total]`), read by the legacy v2 importer (§8). It is used for everything `data-v3/` does not cover yet, and as the **only parity source**. The root `data/` folder (`data/<State>.js`, `data/election20XX.js`, `data/precincts20XX/`, `data/zcta2024.js`) is **v1 and out of scope** (orchestrator, Oct 18, 2026): v2 is moving off it, it will not be renamed, and v3 never reads it.
3. **Precedence (confirmed by the orchestrator, Oct 18, 2026, Q-E8): official values win over v2's, and v2's are kept in history.** When both exist for the same (contest, unit, answer), the official `data-v3/` row is current, whatever its `retrieved_at`: the loader ranks `method = official` above `v2_import` before comparing timestamps. The legacy row is kept in `result_history`, and differences are written to a diff report for the data lanes (they already publish such audits, e.g. `PA/pa_v2_vs_official_mismatches.csv`).

## 1. Input: the Election Data bot's row format (exact)
One CSV (UTF-8, header row, RFC 4180 quoting) per batch, with exactly these 13 columns in this order. The "Observed" column is what the committed files on `origin/data/election` (7faa12d) actually contain. v3 follows the files, not the column names.

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

**Deriving `answer_key`** (stable across years, so deltas compare like with like):
- Partisan offices (president, us_house, state legislature): `party=DEM` → `dem_nominee`, `REP` → `rep_nominee` (one per contest, else reject R10); `candidate_id=all-others` → `other` (`is_aggregate`); any other candidate → `cand:<candidate_id>`.
- The v2 view ("D, R and total of all candidates") is then `dem_nominee`, `rep_nominee` and `total = sum of all answers`. `other` is computed as `total − D − R` when only an aggregate exists. Third-party candidates (Jorgensen, Stein, Castle …) stay individual answers, available for N-answer views, and sum into "other" for the v2 view.
- Measures: `answer` `Yes`/`No` → `yes`/`no`. Multi-choice → `choice:<n>` by ballot order. Nonpartisan races → `cand:<candidate_id>`.

The **natural key** of a row is `(state, year, office, district, unit_type, unit_id, candidate_id)`. One row per key per batch.

`method` (estimate flag) is **not** in the bot format. Until decided (DECISIONS.md D6): `is_estimate = weight < 1`; `method = official` when weight = 1. Proposed: an optional 14th column `method`. The staging table has room for it, and the loader accepts 13 or 14 columns.

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
| R01 header | exactly the 13 (or 14 with `method`) column names, in order; files with other headers (audits, mismatch lists) are skipped and listed, not loaded | reject / skip whole file |
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
- Dimension rows (`contest`, `answer`, `candidate`, `party`, `source`) are upserted on their natural keys (`contest_key`, `(contest_id, answer_key)`, `candidate_key`, `party_key`, `(url, retrieved_at)`) before facts.
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
| `precincts2016/<State>.js` (50) + `precincts2016-DC.js` | `__prec(state,[[county,precinct,d,r,t,polys÷10000]],credit)` | same as `precincts2020`; VEST 2016, CC BY 4.0 | precinct units (`precincts-2016` set) + results |
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
| Inline `PACK`, `XREF`, `STATE_FILES`, `OFFICES`, `PHOTO` in `v2/index.html` | JS constants | lists, cross-refs, office list (`[{id:"president",label:"President",letter:"Pr",scope:"us"}]`), candidate photos | `entity`, `alias`, `office`, `candidate.photo_path` | one-off extraction (read-only) |
| `v2/img/flags`, `stateflags`, candidate photos | PNG | | `entity.icon_flag`, `candidate.photo_path` + credit | copy |
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
- **Q-E4** (largely answered by Q-E9: 2016 precincts ship as `v2/data/precincts2016/` in `__prec` format and are read by the legacy parser; still open whether bot-row CSVs will also exist) 2016 precincts are being built in the v2 `__prec` JS format. Will they also be emitted as bot rows (CSV) under `data-v3/results/2016/`, or should v3 read the JS through the legacy parser?
- **Q-E5** `district` = `statewide` for statewide contests: confirm the token (vs empty), and the format for seats (`01` vs `1` vs `PA-01`).
- **Q-E6** `unit_id` for precincts: what key will bot rows use (v2 `County|Precinct` name, VEST GEOID, state precinct code)? Is it stable across years?
- **Q-E7** "All others" vs individual minor candidates: the FEC files use one `all-others` row, while PA DOS lists each ballot candidate but no write-ins (2016 PA total 6,115,402 vs FEC 6,165,478). Which should v3 show as "total of all candidates" when both exist for the same unit and year?
- ~~**Q-E8**~~ **Resolved (orchestrator, Oct 18, 2026): official values win and v2's are kept in history.** Original question: when `data-v3` official totals differ from v2 (e.g. PA 2020 Allegheny, `PA/GAPS.md`), confirm v3 should show the official value and keep v2's in history (the planned precedence).

- ~~**Q-E11**~~ **Resolved:** `data/election` be5168d copies `data/precincts2020/` and `data/precincts2024/` unchanged into `v2/data/` (101 files, +114.3 MB). Main still loads the 50 state geography files (`index.html` L742) and `zcta2024.js` (L1309) from `../data/`; the orchestrator repoints them once the `v2/data/` copies are on main.
- **Q-E10** (open; likely answered by `data/election` 68791bd "2016 README: drop stale e16 flag; ≈ = 4th element 1", awaiting confirmation) The 2016 README says ≈ is "`e16`, or a 4th element `1` in `ds2016.js`", but only the 4th element occurs in the committed files. Confirm `e16` is unused (or where it will appear).

**New from the Oct 18 08:00 EDT check**
- Q-E5 and Q-E6 are answered in practice by the Senate READMEs: `district=statewide`; precinct `unit_id` = `<ST>|<v2 county>|<v2 precinct name>` with `|#<row>` only for repeats, keyed to the v2 2024 file. Q-E7: Senate rows use one `all-others` row below state level and every candidate at state level. Awaiting the Election lane's confirmation that this is the rule for all future contests.
- **Q-E12** (open) Cross-vintage results: confirm that 2022 (and any future off-year) rows are always keyed to the 2024 precinct polygons, so v3 attaches them to `precincts-2024`. If a lane later ships real 2022 polygons, the loader needs a new boundary set and a crosswalk.
- **Q-E13** (open) Office tokens: confirm `us_senate_special` / `us_senate_runoff` are stage variants of `us_senate` (v3 stores one office and `contest.stage`), and that the d-slot rule (an independent can take the d slot) holds for every contest.
- **Q-I1** (open) Officeholders: will `person_id` stay bioguide (House) / OpenStates ocd-person (state legislatures)? v3 stores these as an `officeholder` table keyed by unit plus a date range.

**Geo & Institution Data**
- ~~**Q-G1**~~ **Resolved (done, bbc8854 / 9ff4c00):** `data-v3/geo/<layer>.csv`, one line per v2 row with `geoid`; every row matched, no GEOID reused within a layer. The 58 duplicate school keys were renamed `<name> (<county>)`; `v2_name_collisions.csv` maps `old_name → new_name → geoid` (use `old_name` for pre-rename main commits). The importer keys on `state|name` (post-rename) or `(layer, row)`, and the ≥ 90 % IoU fallback is dropped. Not covered yet: v1 towns/places → `v1_towns.csv` + places crosswalk (in progress). Note: the app's `normT()` hides same-named towns (IL 473, NY 197, IA 173, KS 154 …), so `state|county|name` is not unique for towns; use GEOID.
- ~~**Q-G8**~~ **Resolved (orchestrator, Oct 18, 2026; the loader repoint and the Ohio / Union County "Washington township" duplicate key are queued with the geo merge build):** root `data/<State>.js` is v1. It gets no renames and is out of scope for v3. The lane also renamed 8 `v2/data/parts/` place rows `Name (County)` (OH Oakwood; TX Reno ×3, Oak Ridge ×2, Lakeside ×2; fd0f171), now listed in `v2_name_collisions.csv`. **Left for the orchestrator:** one duplicate v1 town key, Ohio / Union County / "Washington township" (GEOIDs 3915981662 and 3915981242), which can only be fixed when v2 moves off v1. v3 is unaffected because it keys towns by GEOID.
- ~~**Q-G2**~~ **Resolved (orchestrator, Oct 18, 06:08 EDT):** GeoJSON, one file per layer × vintage (`data-v3/geo/<layer>_<vintage>.geojson`), gzipped above ~5 MB or regenerated by a `tools/` script; attribute tables are UTF-8 CSV. Current v2 geometry is lon/lat in EPSG:4269 (NAD83; < 1 m from EPSG:4326, not reprojected), and the planned GeoJSON is EPSG:4326, 6 decimals, properties `geoid, name, state_fips, tiger_set`.
- ~~**Q-G3**~~ **Resolved:** full-resolution TIGER stays out of git. v3 fetches TIGER/Line 2024 from `https://www2.census.gov/geo/tiger/TIGER2024/<LAYER>/` at build time and joins on `geoid` (the lane offers `tools/fetch_tiger.py` + `tiger_manifest.csv` on request). This becomes `unit_geom` lod 0 for point-in-polygon. v2 geometry is used only for display parity.
- ~~**Q-G4**~~ **Resolved (orchestrator, Oct 18, 2026):** three school unit types `school_unified` / `school_elementary` / `school_secondary` (TIGER UNSD / ELSD / SCSD) under a shared parent category `school_district` (SCHEMA.sql `unit_type_def`), so the UI still shows one list. Background: The lane recommends three unit types `school_unified` / `school_elementary` / `school_secondary` from `tiger_set` (unsd 10,872, elsd 1,952, scsd 481), allowing several school units per point (elsd and scsd overlap in CA, IL, AZ, MT; the OK elementary districts do not overlap unified ones). The v3 schema already has these types; the UI keeps v2's single "School districts" layer (D13).
- ~~**Q-G9**~~ **Resolved:** v3 uses `data-v3/geo/zcta2024.csv` (ZCTA, internal point lat/lon, land area; TIGER 2024 Gazetteer, script in `tools/`; not committed yet). v2 gets a byte-for-byte `v2/data/zcta2024.js` (on `data/geo` 6d8b443).
- ~~**Q-G5**~~ **Resolved:** the canonical town layer is TIGER county subdivisions (`cousub`, GEOID SSCCCMMMMM) in `data-v3/geo/towns_2024.geojson` (20,935 rows, ~2.48 MB gz); places are a separate layer, `places_2024.geojson` (TIGER places, SSPPPPP, 19,477 rows, ~4.01 MB gz). Both are keyed by GEOID, with full-resolution geometry from census.gov at build time. Name crosswalks: `v1_towns.csv` plus a places crosswalk (in progress). Both GeoJSON files are decided but **not committed yet** (checked on `data/geo` 6d8b443). The Iowa townships live in `parts/Iowa.js` (1,598) with GEOIDs in `towns.csv`.
- ~~**Q-G6**~~ **Resolved (decided, not built):** `data-v3/geo/entities.csv` (`entity_id, kind, state, name, alias, label, unit_layer, geoid`: state governments, chambers, school boards, counties, towns, `sovereign`/`incorporated` labels), built from `PACK`/`XREF` and checked against TIGER and Census of Governments. Until it is committed, v3 derives entities from `PACK`/`XREF`.
- ~~**Q-G7**~~ **Resolved (decided, not built):** per-year `data-v3/geo/precincts_<year>.csv` with `precinct_id = <USPS>-<year>-<county FIPS>-<row ordinal>` plus `county, v2_name, source_id`, centroid, and a 2020→2024 area crosswalk (→ `unit_crosswalk`). Precinct IDs are per year, not shared across years. Precinct geometry stays in the v2 `__prec` files.

## 11. Re-runs and restore
- Every load is reproducible from (data-lane commit, file sha256). A `data-YYYYMMDD` tag (ARCHITECTURE.md §6) records the `dv` and the Neon branch or snapshot.
- Rebuild from scratch: new Neon branch → apply migrations → replay batches in `load_batch` order → compare aggregates with the tagged snapshot.
