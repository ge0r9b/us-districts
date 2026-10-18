# Gaps (plan stage)

Scope: the user put people work on **plan only until v3**. No scraping, downloading or building happens until then. Nothing below has been filled yet.

1. **Governors**: no local current-holder data and no 2016–2024 governor results anywhere in the repo or Seating. Plan: NGA roster plus state SOS canvasses or MEDSL. Wikidata P6 is stale for several states (seen in a spot check), so it must not be the source.
2. **President/VP**: not in local data except as presidential candidates (v3/plan candidates.csv, 10 rows). Plan: congress-legislators executive.yaml.
3. **Candidate completeness**: Seating stores only the top n_up+1 finishers for House 2016–2024 and Senate 2016–2020. The full field is known only for Senate 2022/2024 (data/election state files). Minor candidates need MEDSL or Clerk statistics.
4. **QIDs**: the local data has no Wikidata ids. The bioguide → QID mapping needs congress-legislators. Non-incumbent candidates (FEC/cid/bp keys) will mostly have no QID.
5. **District keys for old plans**: House candidacies before cd2022/cd2024 have no current geoid. They stay label + vintage and are paired through `ushouse_2020.csv`. The PA 2018 and NC/FL/VA mid-decade plans have no geo table.
6. **Identity reconciliation**: the same person can appear under bioguide, fec, cid, bp and os keys across Seating, inst and Election Data. A crosswalk is needed (inst `person_id_matches.csv` is a start).
7. **Current House vacancies** and special-election changes after the snapshot need a refresh step.
8. Party labels: fusion lines (NY/CT WF, CON) are merged into the candidate in the Election files. The original lines are lost.
