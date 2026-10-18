# File family: Canada (data-v3/inst/ca, institutions lane, branch data/inst-canada)

Builder: `tools/inst_ca_build.py [OUT] [--stability-test]` (runs `inst_ca_federal.py`, `inst_ca_provincial.py`,
`inst_ca_municipal.py`; helpers in `inst_ca_common.py`; source ids from the shared `inst_sources.py`). Raw inputs (read only):
`/workspace/w/inst-raw/ca/` (+ `prov/`, `statcan/`), hashes in `SHA256SUMS` and `sources_ca.csv`. Deterministic: the stability
test builds twice (second run in reverse builder order) and requires byte-identical files. Plan and status: CANADA_PLAN.md.
Schema proposals: CANADA_SCHEMA_PROPOSALS.md. Result files for the Election bot: RESULTS_SOURCES_CA.md.

| file | rows | what |
|---|---|---|
| `entities_ca_federal.csv` | 2 | `chamber:ca-house`, `chamber:ca-senate` (parent `nation:ca`) |
| `entities_ca_provincial.csv` | 13 | `chamber:ca-<iso>-legislature` (parent `province:ca-*` / `territory:ca-*`) |
| `units_ca_fed.csv` | 681 | FEDs: `ec-2023-fed` 343, `ec-2013-fed` 338 |
| `units_ca_pd_2025.csv` / `_2021` / `_2019` | 71,217 / 69,797 / 66,064 | Elections Canada polling divisions, parent = FED |
| `units_ca_ped.csv` | 665 | provincial electoral districts (ON, QC, BC, AB, MB, SK, NB, PE, NL) |
| `units_ca_ppoll.csv` | 34,024 | provincial polling divisions / voting areas / sections de vote (QC, BC, AB, MB, SK, NB, PE, NL) |
| `units_ca_cd.csv` / `units_ca_csd.csv` | 293 / 5,161 | StatCan 2021 census divisions / subdivisions (units only; types blocked, see plan) |
| `officeholders_ca_house_current.csv` | 343 | current MPs (337) + vacancies (6) |
| `persons_ca.csv` | 337 | `ca-mp:<PersonId>` |
| `gaps_ca_federal.csv`, `gaps_ca_provincial.csv`, `gaps_ca_municipal.csv` | 4 / 12 / 4 | every gap with its reason |
| `sources_ca.csv` | 38 | same columns and id scheme as `data-v3/inst/sources.csv` (merge as a union) |
| `summary_ca_*.json` | - | counts |

Entity columns = `entities.csv` columns + `country`, `province`, `name_fr`, `external_id` (proposed). `state_fips` / `state` are empty.

Unit columns: `boundary_set`, `unit_type` (`fed`, `poll`, `ped`, `ppoll`, `cd`, `csd`), `unit_key` (official code; polls
`<district>:<poll>`), `name`, `name_fr`, `alias` (former / other name), `country` (`ca`), `province` (ISO 3166-2), `parent_boundary_set`
+ `parent_unit_key`, `entity_id` (the chamber the district or poll elects to; empty for cd/csd), `attrs` (`k=v;` list: rep_order,
pd_type normal/single_building/mobile, adv_poll, va_type, QC muni_code/muni_design/ind_off ...), `source_id`, `source_record_id`
(the record's own key in the source), `geometry_ref` (raw file + layer; geometry is never copied), `flags`.

Flags: `renamed_after_ge45:bill_c25_2026`, `renamed_since_2017_act`, `poll_name_ignores_mobile_station` (a PD whose stations are
`78A` = place name and `78B` = "Mobile poll/Bureau itinérant": the place name is used), `poll_name_ambiguous_in_results`,
`adv_poll_empty_on_some_shapefile_parts`, `no_electors:ind_off_N` (QC section that can hold no electors), `spans_municipalities`,
`ed_list_derived_from_polling_division_file` / `..._poll_layer` / `..._poll_file` (NB, PE, NL: district list = the districts of the
poll file), `district_name_variants_in_poll_layer`, `vintage_2019:check_against_ge2025_polls`, `name_not_in_2018_boundary_file`,
`incorporated_unknown:csd_type_not_retrieved`, `gov_status_unknown:cd_type_not_retrieved`, `gov_status_na:legislative_chamber`,
`appointed_no_electoral_units`, `no_electoral_units_loaded`, `consensus_government_no_parties`.

Officeholder columns follow `officeholders_house_*.csv` with `unit_key` instead of `unit_geoid` and `province` / `district` instead
of `statedistrict`; `term_start` = House of Commons `FromDateTime`; `elected_date` is not in the source (`elected_date_missing`).
No estimates (≈) are used anywhere in this family.
