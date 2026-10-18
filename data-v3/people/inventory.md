# Inventory: existing local data reusable for people (no new downloads)

## /workspace/seating/v3data (Seating Charts, snapshot 2026-10-18; see its SCHEMA.md)
- `people.csv` (34,088 rows): `p,key,name,cid`. Key schemes: bp 22.1k, os (OpenStates) 8.7k, fec 1.5k, bioguide 926, name 438, kl 240, cid 60. `p` is renumbered on every build, so join on `key`.
- `terms.csv` (19,290): `b,s,start,end,p,party,caucus,how,appt,approx,src`. Holders by seat for 138 bodies (US Senate/House, 99 state chambers, 37 courts).
- `seats.csv` (8,184): seat slots with `geoid` in the repo's form (CD SSDD, SLD SS+3, state FIPS for the Senate).
- `bodies.csv`: body `key` = entity key (`us-senate`, `us-house`, `us-pa-house`, ...).
- `results_contests.csv` + `results_candidates.csv` (58k candidate rows), 2015–2025: us_house about 2.2k contests, us_senate 170 + 10 special, state legislature about 30k, courts. Only the **top n_up+1 finishers** are stored; `ncand` gives the full field size. `geoid` is set only when the vintage is the current layer.
- `contests_2026.csv`: 2026 ballot candidates (Ballotpedia slugs). `parties.csv`: party codes mapped to repo party_key.
- Governors: **not covered**. There is no governor body and there are no governor results.

## Branch data/inst-officeholders (data-v3/inst, institutions lane)
- `officeholders_house_current/2024/2020.csv`, `officeholders_stateleg_current/2024.csv`: key = `entity_id` + `unit_layer` + `unit_geoid`/`unit_key` + `seat`. `person_id` = bioguide > ocd-person > `<st>-leg`.
- `persons.csv`, `person_id_matches.csv`: cross-ids. `sources.csv`: pinned commits (OpenStates, congress-legislators).
- Seat units: `seat:<chamber>:<label>` for NH floterials, ME tribal seats and House delegates.
- `data-v3/geo/*.csv`: TIGER GEOIDs for every v2 row (ushouse 436, senate 1,950, statehouse 4,890, ...), plus the 2020-plan pairings.

## Historic Election Data (branches data/election, v3/plan)
- `data-v3/results/2022|2024/senate/us_senate_<y>_state.csv`: **every** Senate candidate (Clerk official), with columns `candidate_id` (surname-first slug), `answer` (name), `party`, `votes`, `source_url`. District/county/precinct files use d/r/all-others slots only.
- `v3/plan:data-v3/results/candidates.csv`: 10 presidential candidates, `candidate_id,name,party,years,source_names`.
- `data-v3/results/2016/`: FEC federalelections2016.xlsx (raw).

## Repo key conventions (/workspace/data-inventory.md)
- State = full name. County = `<State>|<County NAMELSAD>`. District = (state, layer, code): House `01`/`00`, SLD 3-char TIGER codes.
- Party triplets are dem/rep/total. `null` = no data, never zero.
