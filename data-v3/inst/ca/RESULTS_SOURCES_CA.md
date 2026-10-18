# Canada: official poll-by-poll result files (for the Historic Election Data bot; no results are built in this lane)

"verified" = the file link was seen / downloaded on 2026-10-18. Others are the agency's results page, not checked file by file.

| election | source | format | status |
|---|---|---|---|
| Federal GE45, 2025-04-28 | Elections Canada, https://www.elections.ca/res/rep/off/ovrGE45/62/data_donnees/pollresults_resultatsbureauCanada.zip (Format 2, long) and .../pollbypoll_bureauparbureauCanada.zip (Format 1, wide); per province `...10.zip` ... `...62.zip`; polling-day registrations `polldayregistrations_enregistjourduscrutinCanada.zip`; index https://www.elections.ca/content.aspx?dir=rep%2Foff%2F45gedata&document=bypro&lang=e&section=res | CSV in ZIP, OGL - Canada | verified (Format 2 Canada downloaded: 343 files, 82,309 distinct polling-station entries incl. advance 6xx and S/R) |
| Federal GE44, 2021-09-20 | https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureauCanada.zip (+ Format 1, per province) | CSV in ZIP | verified |
| Federal GE43, 2019-10-21 | https://www.elections.ca/res/rep/off/ovr2019app/51/data_donnees/pollresults_resultatsbureauCanada.zip (+ Format 1, per province) | CSV in ZIP | verified |
| Federal by-elections, earlier GEs | Elections Canada past elections pages | CSV | not checked |
| Quebec | Élections Québec open data: https://donnees.electionsquebec.qc.ca/production/provincial/resultats/resultats.json, candidats.csv, circonscriptions.csv, statistiques.csv; earlier elections at https://www.dgeq.org/archives.html (results by section de vote) | JSON / CSV | links verified on dgeq.org; contents not checked |
| Ontario GE 2025 | Elections Ontario "Official Return from the Records" (poll level), https://results.elections.on.ca/en/publications (CSV endpoint https://results.elections.on.ca/api/report-groups/48/report-outputs/1089/csv) | CSV / PDF | from search, not downloaded |
| British Columbia | BC Data Catalogue "Provincial Voting Results", https://catalogue.data.gov.bc.ca/dataset/provincial-voting-results (by voting area 2005-2020; 2024 only by voting place) | CSV | from search, not downloaded |
| Alberta GE 2023 | Elections Alberta official results by ED and poll, https://officialresults.elections.ab.ca/orResultsED.cfm?MODE=exED&ED=01&EventId=101 (per ED, Excel); Statement of Vote PDF | XLSX / PDF | from search, not downloaded |
| Manitoba, Saskatchewan, New Brunswick, PEI, NL, Nova Scotia, territories | each agency's Statement of Votes / results pages (electionsmanitoba.ca, elections.sk.ca, electionsnb.ca, electionspei.ca, elections.gov.nl.ca, electionsnovascotia.ca, electionsyukon.ca, electionsnwt.ca, elections.nu.ca) | mostly PDF | not checked |

Join keys from this lane: federal results rows → `ec-<year>-pd` unit `<FED_NUM>:<PD_NUM>-<SFX>` (station `78A`/`78B` → PD `78-0`;
`48-3` → `48-3`; `6xx` advance polls and `S/R n` special-voting-rule rows have no PD polygon); QC → `eq-2026-sv` `<CO_CEP>:<NO_SV>`.
