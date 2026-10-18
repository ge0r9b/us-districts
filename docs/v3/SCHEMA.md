# v3 schema: explanation

> Phase 1 plan, branch `v3/plan`. The DDL is in [`SCHEMA.sql`](SCHEMA.sql). It has been syntax-checked with the Postgres parser (`pglast` 8.6, 60 statements) but **has not been applied to any database**. No database account exists yet.

## Where it comes from
- The spec's Supabase proposal (`docs/us-districts-spec.md` §4.2): entity, entity_alias, versioned boundary, topic/election/answer/candidate, result with `is_estimate`, `method` and `coverage`, plus source with `commercial_ok`. v3 keeps those ideas and their meaning, and changes four things:
  1. **Institution and geography are separate tables** (`entity` and `unit`), joined by `entity_unit`. This mirrors v2's two filters, which are "separate by design" (spec §5): the top filter searches institutions and the bottom filter searches places.
  2. **Boundary sets** are first-class, so one unit type can have several vintages, and so paid or custom sets can exist later.
  3. **`result.weight`** stores the Election Data bot's `weight` column as-is. `weighted_votes` is a generated column.
  4. **Answers belong to a contest** instead of a topic. Any number of answers is allowed, including ballot-measure Yes/No and multi-choice. A stable `answer_key` per slot (`dem_nominee`) keeps year-to-year deltas comparable.

## Tables at a glance
| Group | Table | Purpose |
|---|---|---|
| Tenancy / provenance | `tenant` | Owner of data. `public` (id 1) owns everything shipped today; customer tenants come later. |
| | `license` | `commercial_ok` (null means unverified) and attribution/share-alike flags. This tracks the spec §9.3 commercial-readiness work (for example NYT C-UDA is non-commercial). |
| | `source` | One row per (url, retrieved_at), filled from the bot rows' `source_url` and `retrieved_at`. |
| Geography | `boundary_set` | A vintage of one unit type (`tiger-2024-sldl`, `precincts-2024`). It holds `owner_tenant_id`, `visibility` (public/shared/private), `license_id`, `price_tier`, `tiles_url` and `is_current`. |
| | `boundary_set_grant` | Lets other tenants read a `shared` set. |
| | `boundary_set_default` | Maps a bot row's (unit_type, year) to the boundary set it lands on. |
| | `unit` | One polygon in one set. `unit_key` is the bot's `unit_id`, unique per set. Holds `parent_unit_id` (precinct → county → state), centroid and bbox. |
| | `unit_geom` | Geometry per level of detail: lod 0 is full detail, used for point-in-polygon and weighting; lods 1–3 are simplified for low zooms and the dynamic-tile fallback. |
| | `unit_crosswalk` | Overlap weights between units: precinct → district, and 2020 precinct → 2024 precinct (the `x20` files in v2). |
| Institutions | `entity` | Governments, chambers, school districts, and later companies or brands. `gov_kind`: sovereign / incorporated / body / private. `has_region=false` is allowed. |
| | `entity_unit` | `jurisdiction` (PA → PA polygon), `seat_district` (PA House → each sldl unit), `same_as` (school district ↔ its polygon). |
| | `alias` | Shared names for both filters (PA = Pennsylvania, USA = United States), per spec §5.3. |
| Contests | `party`, `candidate`, `office`, `contest`, `answer` | See below. |
| Results | `result`, `result_total`, `result_history` | Facts, totals and coverage, plus an audit trail of overwritten values. |
| Aggregates | `unit_contest_agg`, `answer_share` (materialized) | Instant reads: one row per unit with all answers, and presorted bar-list rows. |
| Staging | `load_batch`, `stg_result_row`, `stg_reject` | Ingest in the bot's exact row format (DATA_LOADING.md). |
| Geocoder | `geocode_cache` | Stores a hash of the address and the point only. Raw addresses are never stored. |

## Institution vs geography (the top and bottom filters)
- A **unit** is a polygon: a precinct, county, county subdivision (town/township), place, state, US House, state senate (`sldu`), state house (`sldl`), school district, or DC ward (v2 build 1559).
- An **entity** is something the institution filter can select: a country or state (sovereign); a county, city, town, township or borough (incorporated); a legislature or chamber, a school district or an office (body); later a company (private).
- Most governments are both. The `Pennsylvania` entity points at the `PA` state unit through `entity_unit(role='jurisdiction')`. This is the spec's "two rows" unisearch rule (an institution row and a Place row), linked by shared names, not shared code.
- **Legislatures:** the entity `us-pa-house` (chamber) has one `seat_district` link per `sldl` unit. A contest `2024|PA|state_house|101` points at that chamber's office and at its district unit.
- **School districts:** the entity (kind `school_district`) is `same_as` its polygon unit. In v2 a district spanning counties is listed under each county it touches, marked ≈. In v3 that comes from `unit_crosswalk`/geometry overlap with counties at query time, not from duplicated rows.
- **Precincts** are geography only (no entity). They are reporting units.

## Contests, answers, candidates
- `office` is the topic (President, US House, State house, ballot measure, later polls). `scope_entity_id` implements the v2 rule "topics are scoped to their entity" (President → United States).
- `contest` is one race or question at one time. `contest_key = year|state|office|district` is built from the bot columns, so the same row always maps to the same contest (idempotent).
- `answer`: any number per contest. For candidate races, `answer_key` is `dem_nominee` / `rep_nominee` / `other` for partisan slots that must compare across years (v2 deltas), or `cand:<candidate_key>` for nonpartisan or multi-candidate races. Ballot measures use `yes` / `no`; multi-choice uses `choice:<n>`. `is_aggregate` marks "All other candidates and write-ins" (v2 `other = total − dem − rep`, `candidates.csv`).
- `candidate.candidate_key` is the stable ID from the Election Data bot's candidate directory. It is never re-keyed; renames update `full_name` only.
- `party` holds raw spellings in `aliases`, so `Democratic`, `DEM` and `D` resolve to `dem`.

## Results and weight
- `result(contest, unit, answer)` stores `votes` and `weight`. `weighted_votes = votes × weight` is what every aggregate uses.
- `weight = 1` means the whole unit belongs to the contest/target. `weight < 1` means a split or area-weighted share. Example: a precinct split by a district line, apportioned by the votes cast in each part (`tools/dist_from_returns.py` in v2).
- `is_estimate` drives the ≈ mark. v2 flags estimates explicitly (`est`, `e20`, `e24`). The bot format has no such column, so `is_estimate` is derived (`weight < 1`, or `method` ≠ official) until the bot adds `method`. See DECISIONS.md D6.
- `numeric` is used rather than `int` because re-tabulation produces fractions. This is the same reasoning as spec §4.2.
- `result_total.coverage` keeps v2's rule that districts with < 50 % vote coverage stay gray.
- Deltas are computed, never stored: margin(2024) − margin(2020) for the same unit and `answer_key`.

## Boundary sets and paid custom sets later
- Every unit belongs to exactly one `boundary_set`. Today's public sets are owned by tenant 1, `visibility='public'`.
- A customer upload later becomes a new `boundary_set` with `owner_tenant_id=<customer>`, `visibility='private'` (or `shared` with grants), `license='proprietary'` and a `price_tier`. Results are re-tabulated into it with `unit_crosswalk` (precinct → custom polygon, area or vote weighted). No other table changes.
- `boundary_set_one_current` makes sure each tenant has at most one current set per unit type. "Results always in today's boundaries" is `is_current = true`.

## Indexes for instant queries
| Query | Index |
|---|---|
| Point → all units (geocode) | `unit_geom_gist_lod0` (partial GiST, lod 0 only) |
| Low-zoom bbox (dynamic MVT fallback) | `unit_geom_gist_lod2` |
| List children of a unit (drill-down) | `unit_parent`, `unit_contest_agg_parent` |
| All counties/districts of a state for a contest | `unit_contest_agg_list (contest_id, unit_type, state_abbr)` |
| Bar list sorted high → low | `answer_share_sorted (..., share desc nulls last)`: an index range scan, no sort step |
| Results for one unit across contests (pop-up, time slider) | `result_unit (unit_id, contest_id)` |
| Name search in both filters | `unit_name_trgm`, `entity_name_trgm` (pg_trgm), `alias_alias` (prefix) |
| Contest picker | `contest_year_office`, `contest_state_year` |

Past contests are also exported as static packs (ARCHITECTURE.md §4), so most reads never reach Postgres. The indexes cover the dynamic paths: geocode, search, custom sets, and anything not pre-built.

## Size estimate (from the v2 flat export on the box, `/workspace/db/export`, Oct 17, 2026)
| Item | Count | Size (uncompressed GeoJSON, ~40 m simplified) |
|---|---|---|
| Precincts 2024 / 2020 | 163,819 / 163,570 rows | 197 MB / 162 MB |
| School / state house / state senate / US House districts | 13,208 / 4,882 / 1,942 / 435 | 13.6 / 5.9 / 3.5 / 1.7 MB |
| Counties / states | 3,143 / 50 | 3.0 / 0.3 MB |
| Result rows (long format, about 3 answers per unit) | about 1.1 M | — |

Expected Postgres size is about **0.6–0.9 GB**: geometry plus lods, plus about 1.1 M result rows, plus indexes. That is close to Neon Free's 1 GB per project (HOSTING_COST.md). It is an estimate, not a measurement; measure it at the first load.
