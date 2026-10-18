# Sources (priority order)

## 1. Official sources
- Congress Bioguide, bioguide.congress.gov: federal legislators, ids
- Clerk of the House (clerk.house.gov): member list and *Statistics of the Congressional Election* (official federal results)
- Secretary of the Senate, senate.gov: senators, classes
- FEC (fec.gov): candidate ids, *Federal Elections* results volumes 2016–2022
- National Governors Association roster (nga.org/governors): current governors and term dates
- State Secretaries of State and election boards: official canvasses, governor and legislative results
- State legislature websites: current members
- unitedstates/congress-legislators (GitHub, CC0): compiled from the official sources above. Includes bioguide, FEC, Wikidata and OpenSecrets ids

## 2. Wikidata
- QIDs used as the primary `person_id`, and for cross-ids. Do not use Wikidata alone for current officeholders: the state P6 (head of government) statements were found to be stale in a spot check

## 3. OpenStates (CC0)
- State legislators, `ocd-person` ids. The inst lane already pins a commit

## 4. VEST (CC BY 4.0)
- Precinct results with candidate column codes (e.g. `G16PREDCLI`). Gives candidate names for statewide races 2016–2024

## 5. MEDSL (MIT Election Data + Science Lab)
- Precinct, county and state returns with candidate names for 2016–2024 (House, Senate, governor, state legislature)

## 6. OpenElections
- Volunteer-standardized official results by state. Use it to fill gaps when MEDSL is missing a race

Wikipedia and Ballotpedia are lookups only, used to resolve QIDs or for cross-checks. Each row cites the primary source it came from.
