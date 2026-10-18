# v3 officeholder data plan (institutions lane)

Status: **plan only**. Nothing is built. No officeholder data exists in v2 today: 0 matches in every `v2/data/*.js` file (see `AUDIT.md` §1).
Scope, in order: US House, then state senates and houses (plus Nebraska's unicameral legislature), then the DC Council. Counties, towns and school boards come later; I found no national official roster for them, so their coverage is *unknown*.

## 1. Sources (official first)
| Chamber | Primary source (official) | Format / licence | Fallback |
|---|---|---|---|
| US House (435 seats + DC delegate) | House Clerk `https://clerk.house.gov/xml/lists/MemberData.xml` | XML, US government work (public domain). Has `statedistrict` (e.g. `AK00`, `AL01`, `DC00`), name, party, caucus, `bioguideID`, `elected-date`, `sworn-date`; vacant seats have an empty name. The Oct 1, 2026 file has 441 member rows: 435 state seats (2 vacant: FL-20, TX-23) and 6 delegates/commissioner (DC, PR, GU, VI, AS, MP). | `unitedstates/congress-legislators` (CC0 1.0, checked Oct 18, 2026) for past terms. The Clerk file only describes the current Congress. |
| State legislatures (99 chambers) | Each legislature's own member roster (official site, CSV/XML/API where offered, else the HTML roster page). URLs are not collected yet. They will be listed per chamber in `data-v3/inst/roster_sources.csv` (`state, chamber, url, format, terms_of_use, checked_at`) before anything is fetched. None are guessed here. | Varies; terms are recorded per site | **OpenStates `openstates/people`** (CC0 1.0, LICENSE checked Oct 18, 2026). Use it only where the official roster is missing, unparseable or not reusable, and flag every such row with `source=openstates`. The OpenStates API has separate terms and is not used. |
| DC Council (8 ward members + at-large + chair) | DC Council official member pages (dccouncil.gov) | HTML; public record | none |

Rules: raw downloads are kept untouched outside git (`/workspace/w/inst-raw/<source>/<date>/`) with a sha256 manifest. No name or party is ever typed in by hand. Every row cites its source.

## 2. Schema (joined to the data-v3 stable IDs)
`data-v3/inst/officeholders_<vintage>.csv`, UTF-8, one row per **seat × term**:

| column | meaning |
|---|---|
| `unit_geoid` | data-v3 stable district ID: TIGER GEOID from `data-v3/geo/<layer>.csv` (CD `SSDD`, SLDU/SLDL `SS`+code, DC wards `11001-11008`) |
| `unit_vintage` | line set the seat was elected on: `cd116`, `cd118`, `cd119`, `sld2018`, `sld2022`, `sld2024`, `dcward2012`, `dcward2022` |
| `entity_id` | chamber entity from `entities.csv` (e.g. `us-house`, `ak-state-house`) |
| `seat` | seat label inside a multi-member district (`A`/`B`, position number), or empty |
| `person_id` | `bioguide:<id>` (House); `ocd-person/<uuid>` (OpenStates); `<usps>-<chamber>-<source id>` (official roster) |
| `name`, `party`, `caucus` | exactly as the source gives them |
| `status` | `serving`, `vacant`, `former` |
| `term_start`, `term_end`, `elected_date` | ISO dates from the source, empty if the source has none |
| `source`, `source_url`, `source_id`, `retrieved_at`, `sha256`, `license` | provenance |

Join rules:
- **US House:** `statedistrict` → state FIPS + 2-digit district → `unit_geoid`. `AK00` → `0200` (at-large is `00` in TIGER and v2 alike); `DC00` → `1198` (TIGER delegate code `98`).
- **Legislatures:** the source district label → TIGER SLD code, via a per-state crosswalk `data-v3/inst/sld_label_crosswalk.csv`. Labels are not plain numbers in NH ("Belknap 1"), VT ("Addison-1"), MA (names), MN/ND/SD/ID/WA (sub-districts "1A", "26A", "Position 1"). Rows that don't match are reported, never guessed.
- Never join on `state|name`. The v2 rows carry no GEOIDs (orchestrator ruling); for v2 display, the app would map `(layer, row)` → `geoid` through `data-v3/geo/<layer>.csv`.

## 3. Vintages (2020 and 2024)
- **2020 vintage** = the people elected in Nov 2020, on the lines that election used:
  - US House: the 117th Congress elected on the 116th-Congress lines (`cd116`, TIGER 2020).
  - State legislatures: the 2018 SLD plans (`sld2018`, TIGER 2020). Senators in staggered chambers who were not up in 2020 are included with their own `elected_date`.
  - Source: congress-legislators terms for 2021-01-03 to 2023-01-03; OpenStates retired/role history for legislatures, unless the legislature publishes an official archive.
  - These rows **cannot** join to the v2 rows: v2 draws only 2024 lines. That needs the 2020-vintage GEOID tables asked of the geo lane (AUDIT.md §5 Q6).
- **2024 vintage** = elected in Nov 2024, on the current lines (`cd119`, `sld2024`); joins directly to `data-v3/geo/*.csv`.
- **current** = a dated snapshot (`officeholders_current.csv`) that reflects vacancies, special elections and party switches. It is separate from the election vintages, so history is not overwritten.
- Count check per chamber: rows = seats in the official roster. TIGER counts districts, not seats, so multi-member chambers are checked against the roster's own count. Any shortfall is logged, never filled.

## 4. Update cadence
| Source | Cadence | Trigger |
|---|---|---|
| Clerk MemberData.xml | weekly check of `publish-date` and sha256; rebuild only on change | special elections, resignations, swearing-in (Jan 3 of odd years) |
| Official legislature rosters | monthly while in session, quarterly otherwise | session start, special elections |
| OpenStates fallback | with the monthly roster run, only for chambers flagged fallback | |
| Election vintages (2020, 2024) | frozen once built; rebuilt only to correct an error, with the reason logged | |
| Full re-check | after each general election is certified (vintage 2026 added then) | |

## 5. Size and load (for v3; v2 only on the orchestrator's decision)
Measured on the Oct 1, 2026 Clerk file: a minimal `[statedistrict, name, party, bioguide]` table for 441 rows is 17,742 B raw / 7,010 B gzip. State legislatures are about 15× the rows (seat totals unknown until the rosters are fetched), so roughly 100 KB gzip projected for the nation. It should be lazy-loaded per state (about 2 KB gz per state) and **never** be part of the eager `index.html`. Any v2 use needs an app change, which is orchestrator only.

## 6. Open items
- `roster_sources.csv`: collect and check the 99 official roster URLs and their terms of use (not done).
- 2020-vintage GEOID tables from the geo lane.
- School boards, county commissions and town councils: no national official source found. Coverage is unknown and out of scope until the orchestrator decides.
