# data-v3/inst (institutions lane)

| family | files | README |
|---|---|---|
| officeholders + persons | `officeholders_*.csv`, `persons.csv`, `person_id_matches.csv`, `stateleg_official_diffs.csv` | README_OFFICEHOLDERS.md |
| county government | `county_government.csv` | COUNTY_GOVERNMENT.md (columns, sources, licence) |
| institution registry | `entities.csv`, `entity_geoid_xwalk.csv`, `entity_v2_rows.csv`, `entity_gaps.csv` (branch `data/inst-entities`) | README_ENTITIES.md, ENTITIES_SCHEMA.md |

All files: UTF-8, one header row, stable column names; every row carries `source_url` + `retrieved_at` (+ `source_commit`
where an upstream git repo is used). Open public sources only.
