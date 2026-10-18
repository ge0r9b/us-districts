# Sources (all official, retrieved 2026-10-18; times in RETRIEVED_AT are UTC)
| election | file(s) | licence | check source |
|---|---|---|---|
| Federal GE45 2025-04-28 | https://www.elections.ca/res/rep/off/ovrGE45/62/data_donnees/pollresults_resultatsbureauCanada.zip (Format 2) | OGL - Canada (Elections Canada) | `.../ovrGE45/62/data_donnees/table_tableau12.csv` (candidate votes per riding) |
| Federal GE44 2021-09-20 | https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureauCanada.zip | same | `.../ovr2021app/53/data_donnees/table_tableau12.csv` |
| Federal GE43 2019-10-21 | https://www.elections.ca/res/rep/off/ovr2019app/51/data_donnees/pollresults_resultatsbureauCanada.zip | same | `.../ovr2019app/51/data_donnees/table_tableau12.csv` |
| Quebec GE 2026-10-05 | https://donnees.electionsquebec.qc.ca/production/provincial/resultats/resultats.json (isResultatsFinaux=true, updated 2026-10-08) | Élections Québec open-data licence | `circonscriptions.csv` (valid votes) |
| Quebec GE 2022-10-03 | https://donnees.electionsquebec.qc.ca/production/provincial/resultats/archives/gen2022-10-03/resultats-bureau-vote.zip | same | `.../gen2022-10-03/candidats.csv` |
| Ontario GE 2025-02-27 | https://results.elections.on.ca/api/report-groups/48/report-outputs/1095/csv (Official Return from the Records) | Elections Ontario | report 1096 (Valid Votes Cast for Each Candidate). Report 1089 (Statistical Summary) also downloaded. |
| BC GE 2024-10-19 | DataBC `provincial_voting_results_by_voting_place.csv` (https://catalogue.data.gov.bc.ca/dataset/provincial-voting-results) | Elections BC Open Data Licence | Statement of Votes PDF, https://elections.bc.ca/docs/rpt/statement-of-votes-2024-provincial-election.pdf, "Summary of results by electoral district" -> `provincial/bc2024_official_riding_totals_sov.csv` |
| Alberta GE 2023-05-29 | https://officialresults.elections.ab.ca/orResultsED.cfm?MODE=exED&ED=01..87&EventId=101 (87 xlsx) | Elections Alberta | each workbook's "Total (All Voting Locations)" row |
Raw copies with SHA-256: `/workspace/ca_raw/*/SHA256SUMS` (box). BC `provincial_voting_results_by_va.csv` (2005-2020 by VA) was also downloaded, not loaded.

Units: Institutions lane `data/inst-canada` @ `3bbb54a` (QC 2022 `eq-2022-sv`/`eq-2022-ced`; `ca_*` unit types from 945e1a7).
