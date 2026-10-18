# data-v3/people: candidate and officeholder directory (schema, plan only)

Status: **plan only until v3.** This file defines the schema. No people data is committed on this branch yet.
Snapshot convention: dates are ISO `YYYY-MM-DD`. Unknown values are left blank and never guessed.

## Layout (sharded by state)
```
data-v3/people/<ST>/people.csv   one row per person (USPS code; national executives -> US/)
data-v3/people/<ST>/roles.csv    one row per office held or candidacy
```
A person is stored in the shard of their most recent role, with officeholder roles ranked above candidacies. Roles are stored in the shard of the state the role belongs to, so a `person_id` can show up in roles.csv files for several states. Always join on `person_id`.

## Stable ids (`person_id`)
Use the first one that exists:
1. Wikidata QID (`Q22686`)
2. `bioguide:<id>` (Congress Bioguide)
3. `ocd-person:<uuid>` (OpenStates)
4. `fec:<candidate id>`
5. `cid:<surname-first slug>` (the Historic Election Data `candidate_id`, reused as-is)
6. `name:<ST>:<slug>` (last resort)

If a better id turns up later, the old id goes into `other_ids` and stays there, so old keys still resolve.

## people.csv
| column | meaning |
|---|---|
| person_id | stable id (see above) |
| name | display name as the primary source gives it |
| party | repo party_key (`dem`, `rep`, `ind`, `lib`, `grn`, `prog`, `fwd`, `np`, `oth`, `unk`), the same keys as Seating Charts parties.csv |
| wikidata | QID, or blank |
| bioguide | Bioguide id, or blank |
| fec_ids | FEC candidate ids separated by `;` |
| other_ids | other `scheme:id` values separated by `;` (cid, ocd-person, bp, superseded ids) |
| home_state | the shard this row is stored in |
| source_url | the page the identity comes from |

## roles.csv
| column | meaning |
|---|---|
| person_id | links to people.csv |
| name | name as the role's source gives it |
| kind | `officeholder` or `candidate` |
| office | `president`, `vice_president`, `us_senate`, `us_senate_special`, `us_house`, `us_house_delegate`, `governor` (later: `state_senate`, `state_house`, ...), using the same tokens as the results `office` field |
| inst_key | institution entity key: `us-executive`, `us-senate`, `us-house`, `us-<st>-governor`, and for state chambers `chamber:<st>-upper` / `chamber:<st>-lower` (the inst lane's entity_id) |
| state | USPS code (`US` for national roles) |
| district | district label: House = 2-digit `01` (`00` = at-large); state legislature = the 3-character TIGER SLDUST/SLDLST code |
| seat | Senate class (`class 1/2/3`) or the seat label inside a multi-member district |
| unit_layer | `nation`, `state`, `cd`, `sldu`, `sldl`, `seat` |
| geoid | app geo key: state FIPS (`42`), CD `SSDD`, SLDU/SLDL `SS`+3, or `seat:<chamber>:<label>` when there is no TIGER unit (data-v3/geo, inst seat units). Blank when the district's vintage is not one of the app's layers |
| vintage | district plan vintage for candidacies (`cd2012`, `cd2022`, `cd2024`, `state`) |
| contest_key | results contest key `{year}\|{st}\|{office}\|{district}` (+ `\|{stage}`), so roles can join to results |
| party | party for this role |
| term_start, term_end | dates; term_end blank = still serving or not known |
| election_year, stage | for candidacies (`general`, `runoff`, `special`, ...) |
| votes, won, incumbent | from the results source; blank = not reported |
| source_url | citation for this row |

## Key-matching rules
- The CD `geoid` must exist in `data-v3/geo/ushouse.csv`, which covers the 119th Congress plus the DC delegate (`1198`).
- The state `geoid` is the 2-digit FIPS code. The app's natural state key is the full state name; map it with ushouse.csv's `state` column.
- A 2016–2020 House candidacy uses an older plan, so its geoid stays blank and `vintage` + `district` keep the label. Pair it to current units with `data-v3/geo/ushouse_2020.csv`.
- Territorial delegates use `seat:us-house:<ST>00`, the same as the inst lane.
