# Pennsylvania: sources (2020 and 2024 President)

Audit only. No v2 data in `data/` was changed. All times below are UTC as recorded at download (2026-10-18 09:39-09:43 UTC = 05:39-05:43 EDT).

## Official (used as the reference)
| Item | URL | Notes |
|---|---|---|
| PA Department of State, certified 2020 General, President by county | https://www.electionreturns.pa.gov/api/ElectionReturn/GetCountyBreak?officeId=1&districtId=1&methodName=GetCountyBreak&electionid=83&electiontype=G&isactive=0 | Raw: `raw/GetCountyBreak_office1_e83.json`. Statewide: Biden 3,458,229, Trump 3,377,674, Jorgensen 79,380 (total 6,915,283; DOS lists no write-ins). Matches the certificate announced 2020-11-24. |
| PA Department of State, certified 2024 General, President by county | https://www.electionreturns.pa.gov/api/ElectionReturn/GetCountyBreak?officeId=1&districtId=1&methodName=GetCountyBreak&electionid=105&electiontype=G&isactive=0 | Raw: `raw/GetCountyBreak_office1_e105.json`. Statewide: Trump 3,543,308, Harris 3,423,042, Stein 34,538, Oliver 33,318 (total 7,034,206). |
| PA DOS election list (election ids) | https://www.electionreturns.pa.gov/api/ElectionReturn/GetAllElections?methodName=GetAllElections | Raw: `raw/GetAllElections.json` (83 = 2020 Presidential Election, 105 = 2024 Presidential Election). |
| Normalized rows | `pa_president_county_official.csv` | Columns: state, year, office, district, unit_id (county FIPS), unit_type, candidate_id, answer, party, votes, weight, source_url, retrieved_at. Both `pa_president_county_official.csv` (2020/2024) and `pa_president_county_official_2016.csv` also have column 14 `boundary_set` = `v2-2024` (Q-E12; counties on v2's county set). Built 1:1 from the two raw files above. |

## Secondary (checked, not applied; per REPO-RULES order official > VEST > MEDSL > OpenElections)
| Source | URL | Exact match to DOS (Dem and Rep) |
|---|---|---|
| VEST 2020 PA precincts (CC BY 4.0) | https://doi.org/10.7910/DVN/K7760H (box copy `/workspace/vest/pa_2020.zip`) | 55 of 67 counties. Off: Adams, Allegheny, Berks, Crawford, Delaware, Fayette, Lehigh, Monroe, Northumberland, Philadelphia, Pike, Westmoreland. |
| MEDSL 2024 PA precincts (CC0) | https://raw.githubusercontent.com/MEDSL/2024-elections-official/main/individual_states/pa24.zip | 66 of 67 counties. Off: Philadelphia (Dem -2,177, Rep -267). |
| OpenElections 2024 PA precincts | https://raw.githubusercontent.com/openelections/openelections-data-pa/master/2024/20241105__pa__general__precinct.csv | 59 of 67. Missing Clarion, Sullivan, Wayne; partial Bradford, Carbon, Fulton; Lancaster/Warren off by 1-11. |
| OpenElections 2020 PA precincts | https://raw.githubusercontent.com/openelections/openelections-data-pa/master/2020/20201103__pa__general__precinct.csv | 48 of 67. |

Large raw downloads (OpenElections, MEDSL) are kept untouched on the box in `/workspace/w/pa-audit/raw/` (not committed because of size). SHA-256:
```
68acdee2924d771b92a05cd950dec850b462c633c05563207ac7e206116e7366  2024presgeresults.xlsx
91df029d9a108e2431fe87630208fd5a49e0112e684665c4e51e38e506191fc3  GetAllElections.json
c73094edb1b46312f89facc68c561b26286caa158819fe775c00f3487942c7cc  GetCountyBreak_office1_e105.json
cccba01e4692036c60c278b25e9d6f7a47a0d3884d4d16d9e134aac7aa3e424a  GetCountyBreak_office1_e83.json
5073b6d2c76c86c941508dfb1a11cc497e8529b0068c5132aceb0f385c19352e  federalelections2020.xlsx
f134e829a9df0925209f8cad77fc2448c8c780400e2a0190de1d42866f4075ee  medsl_pa24.zip
44829ee9245f3c0af516deab4e885b02c0432c16b184a3e2cd6864c503a91964  oe_20201103__pa__general__precinct.csv
70c574bd0c441205fb81040d8b4c833ff96558992c7be0650509a7c7ce3d4308  oe_20241105__pa__general__precinct.csv
a18c914a8fa8729fdd62db544f835382abf49238a0229bd458e44d685c921546  pa24.csv
```

## What v2 uses today (from the file credits)
- `data/precincts2020/Pennsylvania.js`: MEDSL 2020 precinct returns (doi:10.7910/DVN/NT66Z3) joined to Census 2020 VTDs; 616 precincts filled from VEST.
- `data/precincts2024/Pennsylvania.js`: per county, NYT 2024 precinct map (C-UDA non-commercial), or Census VTD + MEDSL/OpenElections.
- `data/election2020.js` / `data/election2024.js`: county totals (source not stated in file; 2024 equals DOS exactly; 2020 equals county-certified figures, see GAPS.md).
