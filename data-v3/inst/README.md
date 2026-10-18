# data-v3/inst (institutions lane)

| family | files | README |
|---|---|---|
| officeholders + persons | `officeholders_*.csv`, `persons.csv`, `person_id_matches.csv`, `stateleg_official_diffs.csv` | README_OFFICEHOLDERS.md |
| sources | `sources.csv` | README_SOURCES.md |
| county government | `county_government.csv`, `county_government_govbot_diffs.csv` | COUNTY_GOVERNMENT.md (columns, sources, licence) |
| institution registry | `entities.csv`, `entity_geoid_xwalk.csv`, `entity_v2_rows.csv`, `entity_gaps.csv` (branch `data/inst-entities`) | README_ENTITIES.md, ENTITIES_SCHEMA.md |

All files: UTF-8, one header row, stable column names; every row carries `source_id` into `sources.csv` (source name, full
URL(s), licence, `retrieved_at`, upstream `commit`, `sha256`; README_SOURCES.md). A row keeps `source_url` only when it is
row-specific. Open public sources only.
