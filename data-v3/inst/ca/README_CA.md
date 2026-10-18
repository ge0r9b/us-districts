# File family: Canada (data-v3/inst/ca, institutions lane, branch data/inst-canada)

Builder: `tools/inst_ca_build.py [OUT] [--stability-test]` (runs `inst_ca_federal.py`, `inst_ca_provincial.py`,
`inst_ca_municipal.py`; helpers in `inst_ca_common.py`; source ids from the shared `inst_sources.py`). Raw inputs (read only):
`/workspace/w/inst-raw/ca/` (+ `prov/`, `statcan/`), hashes in `SHA256SUMS` and `sources_ca.csv`. Deterministic: the stability
test builds twice (second run in reverse builder order) and requires byte-identical files. Plan and status: CANADA_PLAN.md.
Schema: CANADA_SCHEMA_PROPOSALS.md (Full Stack rulings R1-R6 accepted and applied; Canada loads after v3.0 parity). Result files for the Election bot: RESULTS_SOURCES_CA.md.

| file | rows | what |
|---|---|---|
| `entities_ca_federal.csv` | 2 | `chamber:ca-house`, `chamber:ca-senate` (parent `nation:ca`) |
| `entities_ca_municipal.csv` | 3,545 | 3,406 `municipality` (`municipality:ca-<CSDUID>`, parent province / territory) + 139 CD governments (`county:ca-<CDUID>`) |
| `entity_geoid_xwalk_ca.csv` | 3,547 | entity -> `ca_csd` / `ca_cd` unit, columns of `entity_geoid_xwalk.csv` + `is_estimate`, `share_basis`; Flin Flon / Lloydminster: 4 rows `relation=part`, `overlap=split`, both shares ≈ population-weighted (92-151-X block population); all other rows `primary` / `equal` / 1.0000 |
| `statcan_types_ca.csv` | 78 | every StatCan CSD type (57) and CD type x province, with class, count and the quoted StatCan basis |
| `entities_ca_indigenous.csv` | 638 | `first_nation:ca-<band number>`, kind `indigenous_government` (ISC band list), parent from the ISC location point (flagged) |
| `first_nation_reserves_ca.csv` | 3,543 | ISC First Nation - reserve relation (band, ISC reserve number, names, bands_sharing) + the overlay's CSD key: `csd_unit_key` = the linked 2021 CSDUID(s) (several: semicolon-joined, sorted), `csd_link_count`; exactly one status flag per row: `csd_linked` (1,140 rows / 1,059 reserves, 22 rows / 8 reserves with 2 CSDs), `below_threshold` (no link, only overlaps under 50%: 157 rows / 151 reserves), `no_csd` (no First Nations-type CSD overlap: 2,246 rows / 2,119 reserves); linked reserves that also have sub-50% overlaps carry `also_below_threshold_overlaps:N`. Sum of `csd_link_count` = 1,162 = `reserve_of` rows in `entity_unit_ca.csv` |
| `entity_unit_ca.csv` | 1,162 | `entity_id, boundary_set, unit_type, unit_key, role (reserve_of), method (overlay), share_of_geoid_in_entity, share_of_entity_in_geoid, is_estimate, share_basis, source_id, source_record_id (one isc_reserve_no= per row), flags`; all ≈, NRCan AL_TA x StatCan 2021 CSD equal-area overlay, 50% rule |
| `gaps_ca_reserve_overlay.csv` | 2,631 | 361 below-threshold reserve x CSD overlaps + 2,270 `no_csd` reserves (one row per unlinked reserve; in `first_nation_reserves_ca.csv` the 151 of them with a sub-50% overlap are `below_threshold`, the other 2,119 `no_csd`; the 361 overlap rows fall 170 on those 151 reserves and 191 on 161 linked reserves) |
| `entities_ca_provincial.csv` | 13 | `chamber:ca-<iso>-legislature` (parent `province:ca-*` / `territory:ca-*`) |
| `boundary_sets_ca.csv` | 26 | one row per boundary set: `boundary_set, country, province, unit_type, vintage, is_current, source_id` (`is_current` unique per country + province + unit_type; province empty for Canada-wide sets) |
| `units_ca_fed.csv` | 681 | FEDs: `ec-2023-fed` 343, `ec-2013-fed` 338 |
| `units_ca_pd_2025.csv` / `_2021` / `_2019` | 71,217 / 69,797 / 66,064 | Elections Canada polling divisions, parent = FED |
| `units_ca_ped.csv` | 790 | provincial electoral districts (ON, QC 2026 + 2022, BC, AB, MB, SK, NB, PE, NL) |
| `units_ca_ppoll.csv` | 51,769 | provincial polling divisions / voting areas / sections de vote (QC, BC, AB, MB, SK, NB, PE, NL) |
| `units_ca_cd.csv` / `units_ca_csd.csv` | 293 / 5,161 | StatCan 2021 census divisions / subdivisions (types from 92-151-X; `attrs` csd_type / csd_class / pop2021) |
| `officeholders_ca_house_current.csv` | 343 | current MPs (337) + vacancies (6) |
| `persons_ca.csv` | 337 | `ca-mp:<PersonId>` |
| `gaps_ca_federal.csv`, `gaps_ca_provincial.csv`, `gaps_ca_municipal.csv`, `gaps_ca_indigenous.csv` | 4 / 14 / 33 / 114 | every gap with its reason |
| `sources_ca.csv` | 45 | same columns and id scheme as `data-v3/inst/sources.csv` (merge as a union) + `non_commercial`, `attribution_required` (`true` / `false`; empty = licence silent or none) |
| `summary_ca_*.json` | - | counts |

Entity columns = `entities.csv` columns + `country` (iso2), `province` (ISO 3166-2, empty for national bodies), `labels` (JSON by language, e.g. `{"fr":"Sénat du Canada"}`), `external_id` (empty for now). `state_fips` / `state` are empty.

Unit columns: `boundary_set`, `unit_type` (`ca_fed`, `ca_poll`, `ca_ped`, `ca_ppoll`, `ca_cd`, `ca_csd`), `unit_key` (official code; polls
`<district>:<poll>`), `name`, `labels` (JSON by language), `alias` (former / other name), `country` (`ca`), `province` (ISO 3166-2), `parent_boundary_set`
+ `parent_unit_key`, `entity_id` (the chamber the district or poll elects to; empty for cd/csd), `attrs` (`k=v;` list: rep_order,
pd_type normal/single_building/mobile, adv_poll, va_type, QC muni_code/muni_design/ind_off ...), `source_id`, `source_record_id`
(the record's own key in the source), `external_id` (`<agency>:<type>:<unit_key>`, e.g. `ec:fed:35075`), `geometry_ref` (raw file + layer; geometry is never copied), `flags`.

Flags: `renamed_after_ge45:bill_c25_2026`, `renamed_since_2017_act`, `poll_name_ignores_mobile_station` (a PD whose stations are
`78A` = place name and `78B` = "Mobile poll/Bureau itinérant": the place name is used), `poll_name_ambiguous_in_results`,
`adv_poll_empty_on_some_shapefile_parts`, `no_electors:ind_off_N` (QC section that can hold no electors), `spans_municipalities`,
`ed_list_derived_from_polling_division_file` / `..._poll_layer` / `..._poll_file` (NB, PE, NL: district list = the districts of the
poll file), `district_name_variants_in_poll_layer`, `vintage_2019:check_against_ge2025_polls`, `name_not_in_2018_boundary_file`,
`first_nations_kind_proposal`, `csd_type_ambiguous`, `cd_type_ambiguous`, `zero_population_2021`, `straddles_provinces`, `statcan_csd_type:<t>` / `statcan_cd_type:<t>` (entities), `name_not_in_2026_map`, `gov_status_na:legislative_chamber`,
`appointed_no_electoral_units`, `seats:<n>` (chamber seats), `no_electoral_units_loaded`, `consensus_government_no_parties`.

Officeholder columns follow `officeholders_house_*.csv` with `unit_id` (the Canadian unit key, R5) + `country` instead of `unit_geoid`, `unit_layer = ca_fed`, and `province` / `district` instead
of `statedistrict`; `term_start` = House of Commons `FromDateTime`; `elected_date` is not in the source (`elected_date_missing`).
No estimates (≈) are used anywhere in this family.
