# Canada: schema proposals and Full Stack's rulings (institutions lane, data/inst-canada)

Status 2026-10-18: Full Stack ruled on the first proposals (relayed by the orchestrator). The branch stays separate: Canada loads
after v3.0 parity. Against docs/v3/SCHEMA.sql on origin/v3/plan (365c8a1; Canada rules from 62cb622 / 3c1e42d).

## Accepted (applied on this branch)

| # | ruling | how it is applied here |
|---|---|---|
| R1 | Unit types are `ca_fed`, `ca_poll`, `ca_ped`, `ca_ppoll`, `ca_cd`, `ca_csd` | `unit_type` of every `units_ca_*.csv` and `boundary_sets_ca.csv`; officeholder `unit_layer = ca_fed` |
| R2 | Slugs stay `<agency>-<year>-<set>`; `boundary_sets_ca.csv` with `boundary_set, country, province, unit_type, vintage, is_current, source_id`; `is_current` per (country, province, unit_type) | `boundary_sets_ca.csv`, 24 sets; `province` empty for Canada-wide sets (Elections Canada, StatCan); the build asserts one current set per (country, province, unit_type); not current: `ec-2013-fed`, `ec-2021-pd`, `ec-2019-pd`; `source_id` = every source the set's units cite in first place (`;`) |
| R3 | `parent_boundary_set` wherever a parent sits in another set | units carry `parent_boundary_set` + `parent_unit_key` (`ca_poll` → `ec-2023-fed` / `ec-2013-fed`; `ca_ppoll` → its province's `ca_ped` set; `ca_csd` → `statcan-2021-cd`) |
| R4 | `country` (iso2), `province`, `external_id` on unit and entity files; `name_fr` replaced by `labels` JSON keyed by language | `labels` = `{"fr":"..."}` (compact, sorted keys; empty when there is no other-language name); unit `external_id` = `<agency>:<type>:<unit_key>` (`ec:fed:35075`, `statcan:csd:3520005`, `eq:ppoll:199:106`); entity `external_id` empty for now (chamber seat counts moved to the `seats:<n>` flag) |
| R5 | Officeholders: `unit_id` holds the Canadian unit key | `officeholders_ca_house_current.csv` `unit_id` = FED_NUM, `boundary_set = ec-2023-fed`, `country = ca` |
| R6 | `non_commercial`, `attribution_required` on `sources_ca.csv`; Élections Québec = true / true; others only from each licence's text | table below; empty = the licence text does not say, or there is no licence |

R6 values (licence texts read 2026-10-18):

| sources | non_commercial | attribution_required | basis |
|---|---|---|---|
| Elections Canada (`ec-*`) | false | true | OGL - Canada 2.0: "including for commercial purposes"; "Acknowledge the source" |
| Statistics Canada (`statcan-*`) | false | true | Statistics Canada Open Licence: "use, reproduce, publish, freely distribute, or sell"; acknowledgment of source |
| GeoNB (`geonb-*`) | false | true | OGL - New Brunswick: "including for commercial purposes"; "acknowledge the source" |
| Elections BC (`ebc-*`) | false | true | Elections BC Open Data Licence v1.0: commercial use allowed; attribution statement required |
| Elections Ontario (`eo-*`) | false | false | Open Use Data Product Licence: commercial use allowed; no attribution clause (non-endorsement only) |
| Élections Québec (`eq-*`) | true | true | ruling; the file metadata excludes commercial use and requires citing the source |
| Constitution Act (`ca-constitution-*`) | false | false | Reproduction of Federal Law Order SI/97-5: "without charge or request for permission" |
| Elections Alberta, Manitoba, Saskatchewan, NL, PEI GIS, House of Commons member list, legislature websites | (empty) | (empty) | no licence text found on the download pages |

## Still open (not ruled yet)

1. Units for non-US places at all (62cb622 said none); implied accepted by R1-R5, to be written into SCHEMA.sql.
2. Categories for the new types: `ca_fed` → new `federal_district`, `ca_ped` → new `provincial_district`, `ca_poll` / `ca_ppoll` → `precinct`, `ca_cd` → `county`, `ca_csd` → `town`.
3. The `boundary_set_one_current` index needs a province dimension (R2 is per country + province + unit_type).
4. Person scheme `ca-mp` (`ca-mp:<House of Commons PersonId>`) in the `person.scheme` check; later `ca-<iso>-leg`.
5. Chamber ids `chamber:ca-house`, `chamber:ca-senate`, `chamber:ca-<iso>-legislature` (kind `chamber`).
6. Licence rows for the `license` table (list above); `feed = inst-lane` → origin `inst`.
7. First Nations governments: a new kind (e.g. `first_nation`) for band / First Nation governments. Not minted: StatCan's eight
   First Nations CSD types (IRI 992, S-É 21, TC 9, IGD 2, TK 1, NL 1, TWL 1, TAL 1 = 1,028 CSDs) are land units, and one band can
   hold many reserves, so the entity should come from the band list (CIRNAC First Nation profiles, band number), linked to its
   reserve CSDs through the xwalk. Yukon SG / TL and QC VC / VK / TI are related but logged as gaps.
8. RULED (Full Stack, after 3bbb54a): ids `municipality:ca-<CSDUID>` and `county:ca-<CDUID>` (first freeze, applied); xwalk
   `relation=part`, `overlap=split` with both shares ≈ population-weighted for Flin Flon / Lloydminster (docs/v3 5e561f6, applied).
9. RULED: kind `indigenous_government`, ids `first_nation:ca-<band number>`, reserve / settlement / land `ca_csd` units linked by
   `entity_unit` role `reserve_of`, from an official band list + official reserve-to-band relation only. NOT BUILT YET: the ISC
   open-data hosts refuse TLS from the box (see CANADA_PLAN.md).
