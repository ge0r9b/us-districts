# Canada: official election results (data-v3, results lane)

Official counts only. No row is estimated, apportioned or area-weighted (`weight` = 1 everywhere, no ≈). Units come from the
Institutions lane (branch `data/inst-canada` @ `3bbb54a`, `data-v3/inst/ca/units_ca_*.csv`, `boundary_sets_ca.csv`), read with
`git show`, not merged. `unit_type` values follow their `ca_*` naming (945e1a7).
Raw downloads (untouched, with `SHA256SUMS` and `RETRIEVED_AT`) are kept on the box under `/workspace/ca_raw/{fed,qc,on,bc,ab}`.

## Files
| file | rows | ridings checked | unit_types | on a polygon |
|---|---|---|---|---|
| `federal/ca_house_of_commons_2025_poll.csv.gz` | 462,634 | 343/343 = Table 12 | ca_poll, ca_advance_area, ca_advance, ca_special | 93.81% of votes (polls 55.81% + advance areas 38.00%) |
| `federal/ca_house_of_commons_2021_poll.csv.gz` | 463,862 | 338/338 = Table 12 | ca_poll, ca_advance_area, ca_advance, ca_special | 93.93% (59.57% + 34.36%) |
| `federal/ca_house_of_commons_2019_poll.csv.gz` | 465,434 | 338/338 = Table 12 | ca_poll, ca_advance_area, ca_special | 96.46% (69.82% + 26.64%) |
| `federal/advance_areas_<year>.csv.gz` | 7,762 / 6,425 / 6,172 | lookup: each ca_advance_area's member PD unit_ids | | |
| `provincial/qc_national_assembly_2026.csv.gz` | 908 | 127/127 | ca_ped | riding only (poll file not yet published) |
| `provincial/qc_national_assembly_2022.csv.gz` | 150,919 | 125/125 | ca_ppoll, ca_advance, ca_special | 62.44% of votes (100% of election-day section votes, eq-2022-sv) |
| `provincial/on_legislature_2025.csv.gz` | 50,595 | 124/124 | ca_ppoll_unmapped, ca_advance | 0% (no ON PD units: licence) |
| `provincial/bc_legislature_2024.csv.gz` | 7,399 | 93/93 | ca_voting_place, ca_advance, ca_special | 0% (2024 reported by voting place, not VA) |
| `provincial/ab_legislature_2023.csv.gz` | 349 | 87/87 | ca_ped | electoral-division level only (ea-2019-ed) |
| `*/check_*_riding_vs_official.csv` | | per riding: our sum vs official total | | |
| `*/summary_*.json` | | rows, votes by join class, mismatches | | |
| `tools/ca_federal.py`, `tools/ca_provincial.py` | | builders (`python3 tools/ca_federal.py ge45 /workspace/ca_raw/fed <units_dir> federal`) | | |

## Columns
The v3 columns `state, year, office, district, unit_id, unit_type, candidate_id, answer, party, votes, weight, source_url,
retrieved_at, boundary_set, method`.
- `state` = `CA-<province ISO>` (federal: from the FED number prefix, 10 NL ... 62 NU).
- `office` = `ca_house_of_commons`, `qc_national_assembly`, `on_legislature`, `bc_legislature`, `ab_legislature`.
- `district` = riding number (federal FED_NUM `10001`; QC CEP code `689`; ON ED number `36`; AB ED number `1`), BC = ED abbreviation
  (`ABM`). These are the `unit_key`s of `units_ca_fed.csv` / `units_ca_ped.csv` (names there).
- Every candidate is kept (multi-party; no d/r slots). `candidate_id` = surname-first slug, made unique within a riding by
  appending the party where two candidates share a name (2019 Beauce: Maxime Bernier PPC and Maxime Bernier Rhinoceros).
  `party` = the party name as published (federal English name, QC abbreviation for 2022 / full name for 2026, ON political
  interest code, BC affiliation, AB abbreviation). Blank party = no affiliation as published (BC).
- Rejected/spoiled/declined ballots are not candidate votes and are not rows.

## Federal unit_id / boundary_set
- `ca_poll`: `<FED>:<PD_NUM>-<SFX>` = the `ec-<year>-pd` unit. Stations of one PD are summed into it exactly (78A+78B -> 78-0,
  174-1A -> 174-1; listed in `method` as `stations=`). Mobile polls (5xx) are PDs and have polygons.
- `ca_advance_area`: `<FED>:6xx`, the advance poll's votes as one unit (never split). Its shape is the exact union of the PDs whose
  units attr `adv_poll` = that number: `advance_areas_<year>.csv.gz` columns `year, district, unit_id, unit_type, boundary_set,
  advance_poll, n_members, member_unit_ids` (`|`-separated `ec-<year>-pd` unit_ids), `has_results`, `combined_from`,
  `combined_member_unit_ids`. When advance poll 602 was counted with 603 (602 `combined_with=603`, reports 0), 603's row lists
  602 in `combined_from` and 602's PDs in `combined_member_unit_ids`: draw 603 as members + combined members. `boundary_set` =
  `ec-<year>-pd`. ca_advance_area overlaps the ca_poll layer (same PDs); it is a second layer, not added on top of polls.
- `ca_advance`: `<FED>:6xx` with no member PD in the units (`no_member_pds`; 2025 8 polls / 0 votes, 2021 7 polls / 42 votes, 2019
  none). `ca_special`: `<FED>:S/R n`. `ca_poll_unmapped`: a station with no PD unit (all 0 votes). No polygon; `boundary_set` = the riding set (`ec-2023-fed` for 2025, `ec-2013-fed` for
  2021/2019), so they count in the riding total.
- `method`: `official`, plus per-station notes `<station>:combined_with=<n>` (that station's ballots were counted with poll n,
  so its own row is 0), `:void`, `:no_poll_held`, `:no_pd_polygon`.

## Provincial unit_id
- QC 2022: `ca_ppoll` `<CEP>:<S.V.>` on `eq-2022-sv` (election-day ballots only, `election_day_only`; split sections 28A+28B are
  summed exactly into section 28, `sections=` in `method`); `ca_advance` `<CEP>:BVAn` (sections listed in `method`) and
  `ca_special` `<CEP>:<slug>` (BDS, établissements, hors circonscription, hors Québec, détenus, itinérant...) on `eq-2022-ced`.
- QC 2026: `ca_ped`, one row per candidate per riding; `method` carries `of_which_advance=`.
- ON 2025: `ca_ppoll_unmapped` `<ED>:<PollNumber>` (standard, no polygon) / `ca_advance` `<ED>:ADVnnn`; `combined_with=`, `no_poll_taken`.
- BC 2024: `ca_voting_place` / `ca_advance` / `ca_special` `<ED>:<voting opportunity>:<address id>`; voting place name in `method`.
- AB 2023: `ca_ped` `<ED>`, one row per candidate per electoral division, summed exactly from the 87 workbooks' location rows
  (`of_which_election-day=`, `of_which_advance=`, `of_which_mobile=`, `of_which_special-ballot=` in `method`). Not joined to
  voting areas: gap `not_the_2023_ge_voting_areas`.

## unit_type values (aligned with Institutions `ca_*`)
| unit_type | meaning | boundary_set |
|---|---|---|
| `ca_poll` | federal polling division (has polygon) | `ec-<year>-pd` |
| `ca_advance_area` | federal advance poll = union of member PDs (lookup file) | `ec-<year>-pd` |
| `ca_advance` | advance poll with no polygon | riding set |
| `ca_special` | special-voting-rule / mail / other non-geographic votes | riding set |
| `ca_poll_unmapped` / `ca_ppoll_unmapped` | federal / provincial poll with no polygon unit | riding set |
| `ca_ppoll` | provincial polling division / section de vote (has polygon) | e.g. `eq-2022-sv` |
| `ca_voting_place` | BC 2024 voting place (serves many VAs, not a polygon) | riding set |
| `ca_ped` | provincial electoral district (riding-level rows) | e.g. `eq-2026-ced`, `ea-2019-ed` |
