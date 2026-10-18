# Canada: official election results (data-v3, results lane)

Official counts only. No row is estimated, apportioned or area-weighted (`weight` = 1 everywhere, no ≈). Units come from the
Institutions lane (branch `data/inst-canada` @ `b4dc491`, `data-v3/inst/ca/units_ca_*.csv`), read with `git show`, not merged.
Raw downloads (untouched, with `SHA256SUMS` and `RETRIEVED_AT`) are kept on the box under `/workspace/ca_raw/{fed,qc,on,bc,ab}`.

## Files
| file | rows | ridings checked | unit_types | on a polygon |
|---|---|---|---|---|
| `federal/ca_house_of_commons_2025_poll.csv.gz` | 462,634 | 343/343 = Table 12 | poll, advance_area, advance, special | 93.81% of votes (polls 55.81% + advance areas 38.00%) |
| `federal/ca_house_of_commons_2021_poll.csv.gz` | 463,862 | 338/338 = Table 12 | poll, advance_area, advance, special | 93.93% (59.57% + 34.36%) |
| `federal/ca_house_of_commons_2019_poll.csv.gz` | 465,434 | 338/338 = Table 12 | poll, advance_area, special | 96.46% (69.82% + 26.64%) |
| `federal/advance_areas_<year>.csv.gz` | 7,762 / 6,425 / 6,172 | lookup: each advance_area's member PD unit_ids | | |
| `provincial/qc_national_assembly_2026.csv.gz` | 908 | 127/127 | riding | riding only (poll file not yet published) |
| `provincial/qc_national_assembly_2022.csv.gz` | 153,838 | 125/125 | poll, advance, special | 0% (2022 sections: no units yet) |
| `provincial/on_legislature_2025.csv.gz` | 50,595 | 124/124 | poll, advance | 0% (no ON PD units: licence) |
| `provincial/bc_legislature_2024.csv.gz` | 7,399 | 93/93 | poll (= voting place), advance, special | 0% (2024 reported by voting place, not VA) |
| `provincial/ab_legislature_2023.csv.gz` | 7,987 | 87/87 | poll (= voting location), advance, special | 0% single polygon; see `vas=` |
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
- `poll`: `<FED>:<PD_NUM>-<SFX>` = the `ec-<year>-pd` unit. Stations of one PD are summed into it exactly (78A+78B -> 78-0,
  174-1A -> 174-1; listed in `method` as `stations=`). Mobile polls (5xx) are PDs and have polygons.
- `advance_area`: `<FED>:6xx`, the advance poll's votes as one unit (never split). Its shape is the exact union of the PDs whose
  units attr `adv_poll` = that number: `advance_areas_<year>.csv.gz` columns `year, district, unit_id, unit_type, boundary_set,
  advance_poll, n_members, member_unit_ids` (`|`-separated `ec-<year>-pd` unit_ids), `has_results`, `combined_from`,
  `combined_member_unit_ids`. When advance poll 602 was counted with 603 (602 `combined_with=603`, reports 0), 603's row lists
  602 in `combined_from` and 602's PDs in `combined_member_unit_ids`: draw 603 as members + combined members. `boundary_set` =
  `ec-<year>-pd`. advance_area overlaps the poll layer (same PDs); it is a second layer, not added on top of polls.
- `advance`: `<FED>:6xx` with no member PD in the units (`no_member_pds`; 2025 8 polls / 0 votes, 2021 7 polls / 42 votes, 2019
  none). `special`: `<FED>:S/R n`. No polygon; `boundary_set` = the riding set (`ec-2023-fed` for 2025, `ec-2013-fed` for
  2021/2019), so they count in the riding total.
- `method`: `official`, plus per-station notes `<station>:combined_with=<n>` (that station's ballots were counted with poll n,
  so its own row is 0), `:void`, `:no_poll_held`, `:no_pd_polygon`.

## Provincial unit_id
- QC 2022: `<CEP>:<S.V.>` (election-day ballots only, `election_day_only`), `<CEP>:BVAn` advance (sections listed in `method`),
  `<CEP>:<slug>` special (BDS, établissements, hors circonscription, hors Québec, détenus, itinérant...). `boundary_set=eq-2022-ced`.
- QC 2026: one row per candidate per riding; `method` carries `of_which_advance=`.
- ON 2025: `<ED>:<PollNumber>` (standard) / `<ED>:ADVnnn`; `combined_with=`, `no_poll_taken`.
- BC 2024: `<ED>:<voting opportunity>:<address id>`; voting place name in `method`.
- AB 2023: `<ED>:<type>-<n>` (election-day / advance / mobile / special-ballot); the VAs it served in `method` as `vas=026+027+...`.
