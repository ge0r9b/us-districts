# Canada in the v3 institution registry: plan and status (institutions lane, data/inst-canada)

Goal (user, 2026-10-18): "now go further down to the precinct level in canada". Parents agreed with Full Stack (SCHEMA 62cb622 / 3c1e42d):
`nation:ca`, `province:ca-<ab|bc|mb|nb|nl|ns|on|pe|qc|sk>`, `territory:ca-<nt|nu|yt>`. Those rows are built on data/inst-entities;
this branch only references them as parents. Districts and polls are **units**, not entities; chambers are entities.
Geometry stays out of the CSVs: raw files are kept on the box under `/workspace/w/inst-raw/ca/` (with `SHA256SUMS` and sha256 in
`sources_ca.csv`); each unit row has a `geometry_ref` (file + layer + key) only. Every boundary_set / unit_type name below is a
**proposal** (CANADA_SCHEMA_PROPOSALS.md), not yet accepted by Full Stack.

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
| Census divisions (counties, regional municipalities, MRCs, regional districts ...) | StatCan SGC 2021 structure file https://www.statcan.gc.ca/en/statistical-programs/document/sgc-cgt-2021-structure-eng.csv | Statistics Canada Open Licence | 293 | 2021 | boundary file on www12 (blocked) | built as **units** `statcan-2021-cd`; government entities = gap (CD type blocked) |
| Census subdivisions (municipalities, reserves, unorganized) | same SGC 2021 file | Statistics Canada Open Licence | 5,161 | 2021 | boundary file on www12 (blocked) | built as **units** `statcan-2021-csd`; entities + incorporated flag = gap (CSD type blocked) |
| School boards | no national list; provincial lists (ON Ministry of Education school board list, BC school districts, AB school authorities, QC centres de services scolaires ...) | provincial OGLs | - | - | partly | gap (not started) |

## Why municipalities are units only, for now

Which CSDs are municipal governments (city, town, village, RM, MD, municipalité ...) and which are not (Indian reserves,
settlements, unorganized territories) comes from the 2021 CSD type, and for CDs the CD type (Ontario counties and regional
municipalities, Quebec MRCs, BC regional districts are governments; NB/PEI/NS counties and Ontario districts are not). The
official 2021 type tables are on www12.statcan.gc.ca (HTTP 403 "Security Check" bot challenge) and www150.statcan.gc.ca (TLS
refused from this box). Both are logged; nothing was bypassed. Because entity ids are frozen at first sight, no municipal entity
is minted on a guess. Unblock options: (a) the user downloads `98100002-eng.zip` (table 98-10-0002) or `lcsd000b21a_e.zip` in a
normal browser and drops it on the box; (b) the ftp.maps.canada.ca mirror has only the 2016 CSD/CD files (GDB), usable for a
2016-typed cross-check but not for 2021. Quebec has a second official route: Élections Québec's sections carry the MAMH
municipality code and its legal designation (`muni_code`, `muni_design` in `units_ca_ppoll.csv`), and CSDUID = `24` + that code.
