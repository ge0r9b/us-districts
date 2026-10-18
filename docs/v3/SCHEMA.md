# v3 schema: explanation

> Phase 1 plan, branch `v3/plan`. The DDL is in [`SCHEMA.sql`](SCHEMA.sql). It has been syntax-checked with the Postgres parser (`pglast` 8.6, 122 statements; re-checked after the source / seat / county_government update) but **has not been applied to any database**. No database account exists yet.

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
| | `source`, `source_url` | `source_id` is a text primary key (`sources.csv` `<slug>-<sha8>`; election rows mint one per url + retrieved_at). Uniqueness is on `source_id` only. Nullable `title`, `publisher` and `commit`; `source_url` holds every URL of a multi-URL source. Rows citing several sources use link tables: `entity_source`, `entity_geoid_source`, `entity_location_source`, `officeholder_source`, `person_source`, `county_government_source`. |
| Geography | `boundary_set` | A vintage of one unit type (`tiger-2024-sldl`, `precincts-2024`). It holds `owner_tenant_id`, `visibility` (public/shared/private), `license_id`, `price_tier`, `tiles_url` and `is_current`. |
| | `boundary_set_grant` | Lets other tenants read a `shared` set. |
| | `boundary_set_default` | Maps a bot row's (unit_type, year) to the boundary set it lands on. |
| | `unit_type_def`, `unit_category` | Unit types and their parent category. The three school types `school_unified` / `school_elementary` / `school_secondary` (TIGER UNSD / ELSD / SCSD) share the category `school_district`, which is the one "School districts" list in the UI (Q-G4). |
| | `unit` | One polygon in one set. `unit_key` is the bot's `unit_id`, unique per set. Holds `parent_unit_id` (precinct → county → state), centroid and bbox. |
| | `unit_geom` | Geometry per level of detail: lod 0 is full detail, used for point-in-polygon and weighting; lods 1–3 are simplified for low zooms and the dynamic-tile fallback. |
| | `unit_crosswalk` | Overlap weights between units: precinct → district, and 2020 precinct → 2024 precinct (the `x20` files in v2). |
| Institutions | `entity` | Governments, chambers, school districts, and later companies or brands. `gov_kind`: sovereign / incorporated / body / private. `has_region=false` is allowed. |
| | `entity_unit` | `jurisdiction` (PA → PA polygon), `seat_district` (PA House → each sldl unit), `same_as` (school district ↔ its polygon). |
| | `entity_alias` | Shared names for both filters (plus external ids, former QIDs, `usd:` ids re-keyed to a QID, and the reserved `lei:`/`cik:` schemes kept only for the v5/v6 bridge) (PA = Pennsylvania, USA = United States), per spec §5.3. |
| Contests | `party`, `candidate`, `office`, `contest`, `answer` | See below. |
| Results | `result`, `result_total`, `result_history` | Facts, totals and coverage, plus an audit trail of overwritten values. A result is identified by `(year, office, stage, boundary_set, unit_type, unit_id)` + answer (Q-E12): contest = year + office token (stage derived from `_special` / `_runoff`), unit = `unit_key` within its `boundary_set` (`slug` = the rows' `boundary_set`, e.g. `v2-2024`). Geometry joins on the set, not the year. |
| | `contest_display_slot` | v2-parity view: which answer fills v2's **d** and **r** columns (Q-E13: the Democratic nominee, or an independent who beat the Democrat or ran with no Democrat; the Republican). Every answer is still stored; colour follows party. |
| Images | `entity_image`, `entity_image_source` | Seals, flags and logos (`role`), from inst `entity_images.csv` and Companies `brands.csv` `logo_*`. Each row keeps the file, licence, `fair_use`, `usage_basis`, attribution, source URL, served path and checksum. Only freely licensed images are public in v3; `fair_use` rows load with `public = false` (D22). Images are static assets (`/img/<role>/<entity_id>.<ext>`) with an immutable CDN cache. Replaces `icon_flag` and `entity_logo`. |
| Entity dates and ids | `entity.inception`, `inception_precision`, `inception_source`, `valid_from`, `valid_from_source`, `constituent_qid` | `inception` = earliest sourced founding date (Wikidata P571, day or year precision). `valid_from` = start of the current form of government, only when sourced. `constituent_qid` for states with a separate constituent-country item (dk Q35, nl Q55). Kind `special_district`: `special_district:<st>-<source>-<source_id>`, frozen, parent = state. |
| Relation method | `entity_relation.method`, relation `in_county` | `method` ∈ sourced / overlay / point_in_polygon / manual. `in_county` links a special district to its primary county. |
| Bodies | `body_entity` | A seat- or office-holding body (`council`, `mayor`, `chamber`, `court`, `board`) → its entity. Several bodies can share one entity (NYC council and mayor → the city). `officeholder.body_key` and `entity_unit.body_key` (seat links) point here. Courts are kind `court`, `court:<state>-<slug>`, parent = the state. The US Senate is `us-senate`. |
| Feed map | `entity_feed_map` | Bot feed id → registry entity, with `status` `mapped` / `feed_only` / `unmapped` (inst `entity_feed_map.csv`). Consolidated city-counties: the CoG id maps to the county entity (`note = consolidated`), and county and place are linked by `entity_relation` `consolidated_with`. |
| Seats | `unit` with `unit_type = 'seat'`, `seat_member_unit` | Seats with no TIGER district (NH floterials, ME tribal seats, House delegates of territories) are units with null geometry, key `seat:<chamber slug>:<district>`, so `officeholder.unit_id` stays NOT NULL. They can optionally link to the member units they overlay. |
| People | `person` | One canonical `person_id` = `scheme:id` per person, priority `bioguide:` > `ocd-person:` > `<st>-leg:` (Q-I1, Q-I2). Holds `bioguide`, `ocd_person`, `official_ids`, `name`, optional link to `candidate`. |
| | `person_alias` | Former canonical IDs (OpenStates duplicate merges, resolved session-scoped IDs) → current person, with the OpenStates commit. |
| | `officeholder` | Who held a seat: `unit_id` + date range (`valid_from`, `valid_to`), `person_id` (null + `status = 'vacant'` for vacancies), party, source commit. Indexed on (unit, dates) for "who represented this district on date X". |
| Aggregates | `unit_contest_agg`, `answer_share` (materialized) | Instant reads: one row per unit with all answers, and presorted bar-list rows. |
| Staging | `load_batch`, `stg_result_row`, `stg_reject` | Ingest in the bot's exact row format (DATA_LOADING.md). |
| Institutions (registry) | `entity` (text `entity_id`, no vintage; `feed` raw + `origin` mapped; nullable unique `wikidata` = `wikidata:Q…`), `entity_succession`, `entity_geoid` (with `boundary_set` and the xwalk `share_of_geoid_in_entity` / `share_of_entity_in_geoid`), `entity_unit`, `county_government` | Registry agreed with Institutions (`data-v3/inst/entities.csv` + `entity_geoid_xwalk.csv`, ENTITIES_SCHEMA.md 7250e8b): an opaque `entity_id` frozen at first-seen kind + GEOID (`county:01001`, `muni:place:0107000`, `school:0100003`, `chamber:al-lower`, `chamber:ne-upper` (unicameral), `chamber:dc-council`, `us-house`). Kinds `nation … dc_council`, plus `government_other`, `brand`, `organization`, `company`, `nonprofit` and `fund`. Bot ids are bare `scheme:id`: `wikidata:Q…` for brands/organizations (`usd:<uuid>` for approved user adds), `cog:` / `fr:` for governments. The same id carries across vintages; a government change mints a new id linked by `entity_succession`. District seats are units. |
| Institutions (lists) | `entity_relation`, `entity_location`, `entity_merge`, `entity_alias.match_confidence` | Brands/organizations keyed `wikidata:Q<id>` (kinds `brand`, `organization`, `company`, `nonprofit`, `fund`; `brand_name`). Brand → parent QID links with dates (no ownership %). `entity_location` = one row per HQ (`hq_in`) or establishment (`establishment_at`) with name, address, Point 4326 (GIST), optional GEOID, source and a `retracted` flag. Brands with no QID are excluded; approved user adds get `usd:<uuid>`. No SEC/GLEIF/LEI data in v3. |
| Refresh / moderation | `stg_entity_row`, `entity_history`, `retraction`, `app_user`, `submission`, `moderation_log`, `rate_limit_bucket` | Staging → validate → dedupe → upsert; history on every change, deletes only via the retract list; user submissions (phase 3+, auth D18). |
| Geocoder | `geocode_cache` | Stores a hash of the address and the point only. Raw addresses are never stored. |

## Institution vs geography (the top and bottom filters)
- A **unit** is a polygon: a precinct, county, county subdivision (town/township), place, state, US House, state senate (`sldu`), state house (`sldl`), school district, or DC ward (v2 build 1559).
- **School districts (Q-G4, decided Oct 18, 2026):** three unit types `school_unified`, `school_elementary` and `school_secondary`, mapped 1:1 from TIGER UNSD / ELSD / SCSD (`schools.csv` `tiger_set`: unsd 10,872, elsd 1,952, scsd 481). All three belong to the parent category `school_district` (`unit_type_def.category`). Lists and aggregates group by category, so the UI keeps v2's single "School districts" list. Point-in-polygon may return one unified district, or one elementary plus one secondary district, for the same address.
- An **entity** is something the institution filter can select: a country (`nation:<iso2>`, lowercase; the US row is `nation:us`), a territory (kind `territory`: `territory:<2-digit US FIPS>` with parent `nation:us`, `territory:<iso2>` for a foreign dependency with its sovereign nation as parent, or `territory:ca-nt` / `ca-nu` / `ca-yt` with parent `nation:ca`), a Canadian province (`province:ca-<code>`, parent `nation:ca`) or a state (sovereign); a county, city, town, township or borough (incorporated); a legislature or chamber, a school district or an office (body); later a company (private). Units exist for any country with a registered boundary set, Canada first: `ca_fed`, `ca_poll`, `ca_ped`, `ca_ppoll`, `ca_cd` and `ca_csd`, with slugs `<agency>-<year>-<set>`. `boundary_set`, `unit` and `entity` carry `country`, `province`, `external_id` and `labels` (jsonb by language, no `name_fr`), and `unit.parent_boundary_set` allows parents in another set. Other non-US places stay entity-only. Canadian chambers are `chamber:ca-house`, `chamber:ca-senate` and `chamber:ca-<iso>-legislature`. Person schemes are `ca-mp:<PersonId>` and `ca-<iso>-leg:<id>`. Non-commercial sources (Élections Québec) are excluded from paid features via `source.non_commercial`.
- Most governments are both. The `Pennsylvania` entity points at the `PA` state unit through `entity_unit(role='jurisdiction')`. This is the spec's "two rows" unisearch rule (an institution row and a Place row), linked by shared names, not shared code.
- **Legislatures:** the entity `chamber:pa-lower` (chamber) has one `seat_district` link per `sldl` unit. A contest `2024|PA|state_house|101` points at that chamber's office and at its district unit.
- **School districts:** the entity (kind `school_unified` / `school_elementary` / `school_secondary`, e.g. `school:4218990`) is `same_as` its polygon unit. In v2 a district spanning counties is listed under each county it touches, marked ≈. In v3 that comes from `unit_crosswalk`/geometry overlap with counties at query time, not from duplicated rows.
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
- **Any number of years**: every year is just another `contest` row (`2016|US|president|`, `2020|…`, `2024|…`) with the same `answer_key`s. v2's 3-point slider (2016 / 2020 / 2024, decided Oct 18, 2026) needs no schema change: the 2016 `[d, r, tot]` triple becomes three `result` rows (`dem_nominee` = Clinton, `rep_nominee` = Trump, `other` = tot − d − r) plus `result_total`.
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
| All counties/districts of a state for a contest | `unit_contest_agg_list (contest_id, unit_type, state_abbr)`; one list across the three school types: `unit_contest_agg_cat (contest_id, category, state_abbr)` |
| Bar list sorted high → low (per category, so the three school types rank together) | `answer_share_sorted (contest_id, category, state_abbr, answer_key, share desc nulls last)`: an index range scan, no sort step |
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
