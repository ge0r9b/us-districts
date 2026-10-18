# Canada in the v3 institution registry: plan and status (institutions lane, data/inst-canada)

Goal (user, 2026-10-18): "now go further down to the precinct level in canada". Parents agreed with Full Stack (SCHEMA 62cb622 / 3c1e42d):
`nation:ca`, `province:ca-<ab|bc|mb|nb|nl|ns|on|pe|qc|sk>`, `territory:ca-<nt|nu|yt>`. Those rows are built on data/inst-entities;
this branch only references them as parents. Districts and polls are **units**, not entities; chambers are entities.
Geometry stays out of the CSVs: raw files are kept on the box under `/workspace/w/inst-raw/ca/` (with `SHA256SUMS` and sha256 in
`sources_ca.csv`); each unit row has a `geometry_ref` (file + layer + key) only. Boundary_set slugs and the `ca_*` unit types follow
Full Stack's rulings R1-R6 (CANADA_SCHEMA_PROPOSALS.md).

Status: **built** = rows in this directory; **gap** = logged in `gaps_ca_*.csv` with the reason.

| level | official source (URL) | licence | count | vintage | geometry | status |
|---|---|---|---|---|---|---|
| House of Commons (chamber) | Constitution Act, 1867 | federal law | 1 entity `chamber:ca-house` | - | - | built |
| Senate (chamber) | Constitution Act, 1867 | federal law | 1 entity `chamber:ca-senate` (appointed, 105 seats) | - | none (no electoral units) | entity built; senators = gap |
| Federal electoral districts, 2023 Representation Order (GE45 2025 and now) | Elections Canada https://www.elections.ca/res/cir/mapsCorner/edb/FederalElectoralDistricts_SHP.zip (names after Bill C-25, 2026) + https://www.elections.ca/res/cir/mapsCorner/vector/FederalElectoralDistricts_2025_SHP.zip | OGL - Canada | 343 (17 renamed by Bill C-25; old name in `alias`) | 2023 order | yes (SHP) | built `ec-2023-fed` |
| Federal electoral districts, 2013 Representation Order (GE42 2015, GE43 2019, GE44 2021) | Elections Canada FED_CA_2021_EN.zip, federal_electoral_districts_boundaries_2019.shp.zip (ftp.maps.canada.ca) | OGL - Canada | 338 | 2013 order | yes | built `ec-2013-fed` |
| Federal polling divisions GE45 2025 | https://www.elections.ca/res/cir/mapsCorner/vector/PollingDivisionBoundaries_2025_SHP.zip | OGL - Canada | 71,217 PDs (71,687 shapefile parts); N 63,426 / S 2,427 / M 5,834 parts | at the GE45 writ (2025) | yes | built `ec-2025-pd` |
| Federal polling divisions GE44 2021 | ftp.maps.canada.ca .../Elections_Canada_2021/PD_CA_2021_EN.zip | OGL - Canada | 69,797 (69,997 parts) | 2021 | yes | built `ec-2021-pd` |
| Federal polling divisions GE43 2019 | ftp.maps.canada.ca .../Elections_Canada_2019/polling_divisions_boundaries_2019.shp.zip | OGL - Canada | 66,064 (69,538 parts) | 2019 | yes | built `ec-2019-pd` |
| Advance polling districts 2019/2021/2025 | same Elections Canada pages (ADVPD files) | OGL - Canada | - | - | yes | not built (each PD carries `adv_poll=` instead) |
| Poll names | Elections Canada poll-by-poll results, Format 2 (GE43/44/45), only the polling-division name column is read | OGL - Canada | 71,217 / 69,794 / 66,058 named | - | - | built (name column only) |
| Current MPs | House of Commons, https://www.ourcommons.ca/Members/en/search/xml | HoC website content (no reuse grant found; factual fields only) | 337 serving + 6 vacant = 343 seats | 2026-10-18 | - | built |
| Provincial / territorial legislatures (chambers) | the 13 legislature websites | - | 13 entities `chamber:ca-<iso>-legislature` | - | - | built |
| ON electoral districts | Elections Ontario, Electoral District Shapefile - 2022 General Election | EO Open Use Data Product Licence | 124 | Representation Act 2015 (2017 amend.), GE 2018/2022/2025 | yes | built `eo-2022-ed` |
| ON polling divisions | Elections Ontario PD shapefiles | **Limited Use** licence (no redistribution / derived products) | - | - | yes | gap (licence) |
| QC circonscriptions | Élections Québec, circonscriptions_electorales_2026_shapefile.zip + liste_circonscriptions2026.csv | DGEQ open-data licence (attribution); file metadata says **non-commercial** | 127 | Loi 2026 c. 15 | yes | built `eq-2026-ced` |
| QC sections de vote | Élections Québec, sections_vote_2026_shapefile.zip (tracé du 2026-07-15) | as above | 16,756 (49 without electors, 30 span municipalities) | 2026-07-15 (may change until the decree) | yes | built `eq-2026-sv` |
| QC circonscriptions + sections de vote, 2022 GE (3 Oct 2022) | Élections Québec, circonscriptions_electorales_2022_shapefile.zip + sections_vote_2022_shapefile.zip (délimitation du 28 août 2022) | as above (non-commercial, attribution) | 125 / 17,745 (46 without electors) | G.O. 22 June 2022 | yes | built `eq-2022-ced`, `eq-2022-sv` (not current; 2026 renumbered every CO_CEP) |
| BC electoral districts | BC Geographic Warehouse layer 74 (EBC_ELECTORAL_DISTS_BS11_SVW) | Elections BC Open Data Licence | 93 | 2023 redistribution | yes | built `ebc-2023-ed` |
| BC voting areas | BC Geographic Warehouse layer 73 (EBC_VOTING_AREAS_BS11_POLY_SVW, gazetted 2024-09-19) | Elections BC Open Data Licence | 5,778 | 2024 | yes | built `ebc-2024-va` |
| AB electoral divisions | Elections Alberta 2019Boundaries_ED-Shapefiles.zip (Bill 33, 2017) | not stated | 87 (1 renamed: Calgary-Bhullar-McCall) | 2017 act, GE 2019/2023 | yes | built `ea-2019-ed`; the proposed 89 = gap |
| AB voting areas | Elections Alberta EA_Voting_Area_Boundaries_2026.zip | not stated | 4,904 | 2026 | yes | built `ea-2026-va` |
| MB electoral divisions | Elections Manitoba 2018_Final_ED_*_Public_Urban.zip | not stated | 57 | 2018 | yes | built `em-2018-ed` |
| MB voting areas | Elections Manitoba VA_MB2023_public.zip | not stated | 2,371 | GE 2023 | yes | built `em-2023-va`; by-election sets = gap |
| SK constituencies | Elections Saskatchewan ESK_KML_Shape_Files_Mar2024.zip | not stated | 61 | 2022 commission, GE30 2024 | yes | built `esk-2022-ed` |
| SK voting areas | same zip (VotingAreas_30thGE) | not stated | 783 | GE30 2024 | yes | built `esk-2024-va` |
| NB electoral districts + polling divisions | GeoNB Polling Divisions - Provincial, Current (2024), https://gnb.socrata.com/api/views/s8s4-3dia/rows.csv | OGL - New Brunswick | 49 EDs (derived from the PD file) / 1,753 PDs | 2024 | yes | built `enb-2024-ed`, `enb-2024-pd` |
| PE electoral districts + polls | Government of PEI GIS, Provincial_Electoral_Wards_and_Polls layer 0 | PEI open data (reuse permitted) | 27 / 241 | not stated (2017 districts) | yes | built `epei-2017-ed`, `epei-2017-poll` |
| NL electoral districts + polls | Elections NL, NL-Polls-2019.zip | not stated | 40 / 1,438 | April 2019 | yes | built `enl-2015-ed`, `enl-2019-poll` (older than GE 2021/2025: gap) |
| NS electoral districts + polls | Elections Nova Scotia (PDF maps, online lookup) | - | 55 districts (per ENS map) | 2026 map | no open file found | gap |
| YT / NT / NU districts + polls | Elections Yukon / Elections NWT / Elections Nunavut | - | not verified | - | no open file found | gap |
| Provincial members (MLAs, MNAs, MPPs, MHAs) | each legislature's member list | - | - | - | - | gap (not built in this batch) |
| Census divisions (counties, regional municipalities, MRCs, regional districts ...) | StatCan 2021 Geographic Attribute File 92-151-X (CDTYPE) + SGC 2021 | Statistics Canada Open Licence | 293 | 2021 | lcd file not downloaded | built: units `statcan-2021-cd`; 139 CD governments `county:ca-<CDUID>` (MRC 81, RD 28, ON CTY 20, RM 6, UC 3, DM 1); 68 CDs of ambiguous types = gap |
| Census subdivisions (municipalities, reserves, unorganized) | StatCan 92-151-X (CSDTYPE, DB population) + lcsd000b21a_e boundary file + SGC 2021 | Statistics Canada Open Licence | 5,161 | 2021 | yes (lcsd000b21a_e) | built: units `statcan-2021-csd`; 3,406 municipalities `municipality:ca-<CSDUID>`; 1,028 First Nations-type CSDs = kind proposal; 442 CSDs of 18 ambiguous types = gap |
| School boards | no national list; provincial lists (ON Ministry of Education school board list, BC school districts, AB school authorities, QC centres de services scolaires ...) | provincial OGLs | - | - | partly | gap (not started) |

## Municipal and county governments (StatCan 2021 types)

Inputs: `2021_92-151_X.zip` (one row per dissemination block, collapsed by the builder to one row per CSD / CD; every DB of a CSD
agrees on name and type, asserted), `lcsd000b21a_e.zip` (CSDUID, name, type agree with 92-151-X for all 5,161), SGC 2021 structure
file. Classification uses only StatCan's own definitions (Census Dictionary 2021 geo012 / geo008 and Tables 1.5 / 1.4; SGC 2021
Appendix A / B titles); `statcan_types_ca.csv` lists every type with its class, count, provinces and the quoted basis.

- CSD -> `municipality` (parent = province / territory; joined to its `ca_csd` unit in `entity_geoid_xwalk_ca.csv`) when the type's
  official title is a municipality / city / town / village / township / parish municipality (26 types, 3,408 CSDs, 3,406
  entities: Flin Flon and Lloydminster are one municipality with a CSD in each province, keyed on the larger part, logged).
- First Nations types (geo012's eight on-reserve types: IRI, S-É, IGD, TC, TK, NL, TWL, TAL; 1,028 CSDs): not minted; open kind proposal.
- NO, SNO, SC (unorganized / statistical equivalents) and SET, SÉ (settlements): units only.
- 18 types StatCan's text does not settle (NB parishes P, hamlets, NT chartered communities / community governments, LGD, RCR,
  AB ID / SA, PE fire districts, BC regional district electoral areas, CN, GR, QC villages cris / naskapi, terres inuites,
  YT self-government / Teslin lands): units only, one gap row per type.
- CD governments: MRC, RD, RM, UC, DM and Ontario CTY (geo008: legislated "group of neighbouring municipalities joined together for
  ... regional planning and managing common services"). CDR / TER are StatCan creations; NB CT, NS / PE CTY, ON DIS, REG and QC TÉ = gap.

## First Nations governments (ruled; reserve_of links by equal-area overlay)

Full Stack ruled kind `indigenous_government`, ids `first_nation:ca-<band number>`, links `entity_unit` role `reserve_of` from the
reserve / settlement / land `ca_csd` units. Built from ISC "First Nations Location" (OGL-Canada, open.canada.ca
b6567c5c-8339-4055-99fa-63f92114d9e4; browser download 2026-10-18, data.sac-isc.gc.ca refuses TLS from the box):
- `entities_ca_indigenous.csv`: 638 bands. Parent = province / territory of the StatCan 2021 CSD polygon containing the ISC band
  location point (all 638 fall in exactly one; flag `parent_from:isc_location_in_statcan_csd_2021`), else `nation:ca`.
- `first_nation_reserves_ca.csv`: the ISC First Nation - reserve relation, 3,543 band x reserve rows (3,329 ISC reserves, 56 shared).
- `entity_unit_ca.csv`: 1,162 `reserve_of` rows, all ≈ (`method=overlay`, `is_estimate=true`). Full Stack ruling: (a) an official
  StatCan 2021 reserve number -> CSDUID file was searched for and not found (StatCan 2021 correspondence files cover dissemination
  blocks / areas only; ISC's CWB thematic data is keyed by CSDUID with names only), so (b): NRCan CLSS Aboriginal Lands polygons
  (AL_TA_CA_SHP_DCM_eng.zip edition 2.189, CONFIRMED + MODIFIED + ADDED; ALCODE = ISC reserve number; source `nrcan-al-ta-ca`)
  overlaid on the 1,028 StatCan 2021 CSDs of the eight First Nations types (IRI, S-É, IGD, TC, TK, NL, TWL, TAL), areas in Canada
  Albers Equal Area (ESRI:102001). A reserve is linked to a CSD iff intersection / CSD area >= 0.5 ("the CSD is at least 50% inside
  the reserve") or intersection / reserve area >= 0.5 ("the reserve is at least 50% in the CSD"). One row per band x CSD x reserve
  (Full Stack: never merged; the 50% rule is applied to each reserve on its own; a shared reserve gives one row per band; flag
  `several_reserves_in_csd` when a band has more than one reserve linked to the same CSD; a reserve passing only as part of a group
  would be a `below_threshold_individually_was_merged` gap, 0 occur); `share_of_geoid_in_entity` = share of the CSD inside the reserve,
  `share_of_entity_in_geoid` = share of the reserve inside the CSD; `source_record_id` = `isc_reserve_no=<ALCODE>`. Bands without a reserve get no rows; names are never matched.
- `gaps_ca_reserve_overlay.csv`: 361 below-threshold overlaps (not linked) + 2,270 reserves flagged `no_csd` (no 2021 First
  Nations-type CSD overlaps >= 50%; mostly uninhabited reserves StatCan does not delineate as CSDs). They are never mapped to a parent
  CSD. `first_nation_reserves_ca.csv` carries the linked CSDUID(s) in `csd_unit_key` (semicolon-joined if several) with `csd_link_count` and one status flag: `csd_linked` / `below_threshold` / `no_csd` (see README_CA.md). 1,059 distinct reserves linked; 996 of the 1,028 First Nations CSDs are
  linked to at least one band (32 not, gap `fn_csd_without_band`: S-É 17, IRI 13, TWL 1, TAL 1).
