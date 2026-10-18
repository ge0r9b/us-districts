# Gaps and caveats
Every riding total matches its official source (0 mismatches in all 8 elections); the gaps are about polygons, not counts.

1. **Federal advance votes are on advance areas** (union of member PDs, lookup `federal/advance_areas_<year>.csv.gz`); share of
   votes on a polygon (polls + advance areas): 2025 93.81%, 2021 93.93%, 2019 96.46%. Still without a polygon: special-voting-rule
   (S/R) votes 6.2% / 6.1% / 3.5%, and advance polls with no member PD (2025 0 votes, 2021 42 votes). Provincial advance/special
   rows remain on the riding.
2. **Federal stations with no PD unit**: 2025 35 stations, 2021 269, 2019 0, all with 0 votes (void / combined mobile stations).
3. **Combined polls**: a station `combined_with=n` reports 0; its ballots are in poll n. The PD polygon of that station shows only
   its other stations (2025: 35,104 combined candidate rows at PD level). Exact as published.
4. **Quebec 2026**: Élections Québec has not published the poll-level file yet (`resultats-bureau-vote.zip` for the 2026 GE
   returns 403; archives list only up to the 2026-02-23 Chicoutimi by-election). Loaded riding-level results; rerun when posted.
   The units (`eq-2026-sv`) are the 2026 sections, so the 2026 poll file will join directly on `<CO_CEP>:<NO_SV>`.
5. **Quebec 2022**: sections are on the 2017 map (125 ridings) and the units hold only 2026 sections, so 0% joins. The 2022
   section shapefile is on dgeq.org archives ("Sections de vote (Shapefile)", 2022) -> ask the Institutions lane for `eq-2022-sv`.
6. **Ontario 2025**: no ON polling-division units (Elections Ontario PD shapes are under a limited-use licence; Institutions gap).
   Poll rows keep `no_pd_polygon:on_pd_licence`.
7. **BC 2024**: Elections BC counted by voting place ("vote anywhere"), not by voting area, so no VA join is possible for 2024.
   BC 2020 and earlier are by VA but on the 2015 map (87 EDs), not the 2024 VA units. Not loaded.
8. **Alberta 2023**: results are by voting location, each serving a listed set of VAs (`vas=` in `method`). The units are the
   2026 VA vintage (`ea-2026-va`); 93.6% of election-day votes are at locations whose VA codes all exist in it, but the 2026 VAs
   are not verified identical to 2023's, so no polygon join is claimed.
9. Not loaded: federal by-elections, other provinces (MB, SK, NB, PE, NL, NS, territories: mostly PDF), Ontario 2022, Alberta 2019.
10. Name fixes: 2021 59001 (Abbotsford) NDP candidate spelled three ways in the poll file -> folded to "Dharmasena Yakandawela";
    2019 24007 (Beauce) two Maxime Berniers -> ids `bernier-maxime-people-s-party` / `bernier-maxime-parti-rhinoceros-party`.
