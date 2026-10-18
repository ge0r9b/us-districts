# County government (v3; institutions lane)

`county_government.csv` is built by `tools/inst_county_government.py`. It answers ENTITIES_SCHEMA Q1 (`has_own_government`) and is keyed by county GEOID plus vintage. It is v3 only: nothing in v2 loads it.

- **Source (official):** U.S. Census Bureau, *2022 Census of Governments: Organization*, Government Units Listing (`govt_units_2022.ZIP` → `Govt_Units_2022_Final.xlsx`, tab General Purpose). Public domain. Retrieved Oct 18, 2026. The sha256 of the ZIP is in every row and in `inst-raw/cog2022/SHA256SUMS`.
- **Rule:** `has_own_government=yes` if and only if the listing has a `1 - COUNTY` unit with that state and county FIPS. That gives **3,031 yes and 113 no** over the 3,144 county equivalents of 2024. Every CoG county unit maps to a data-v3 county GEOID, and none is left over.
- **`government_kind`:** one of four values:
  - `county`: 3,031.
  - `municipal`: 74. There is no county unit, but TIGER says C/B/F, or says A. The CoG general-purpose unit in that county area with the largest population is cited in `cog_unit_*`, e.g. CITY AND COUNTY OF SAN FRANCISCO. That is a citation of the listing, not a claim about who performs county functions.
  - `none in this county area`: 4. These are the NYC boroughs; CoG files the City of New York under 36061.
  - `none`: 35. These are TIGER N/S/G: CT's planning regions, MA, RI, Alaska census areas and Kalawao.
- **Cross-check against TIGER 2024 FUNCSTAT** (`data-v3/geo/county_funcstat.csv`): `agrees_with_tiger` is yes when (FUNCSTAT = A) matches (a CoG county unit exists). The counts are 3,032 A vs 3,031 CoG county units. **3 disagreements**, listed and not resolved:

| GEOID | County | TIGER | CoG 2022 |
|---|---|---|---|
| 13101 | Echols County, GA | C (consolidated) | `COUNTY OF ECHOLS`, a county unit |
| 15003 | Honolulu County, HI | A (active) | no county unit; `CITY AND COUNTY OF HONOLULU` is municipal |
| 22109 | Terrebonne Parish, LA | A (active) | no county unit; `CONSOLIDATED GOVERNMENT OF TERREBONNE` is municipal |

So 3,032 − 2 + 1 = 3,031, which accounts for the whole difference. The consolidated city-counties geo mentioned (San Francisco, Denver, Philadelphia, Nashville, Anchorage, the NYC boroughs) agree: TIGER marks them C, and CoG has no county unit for them.

- **Connecticut:** the 2024 rows are the 9 planning regions (09110–09190). CoG 2022 already assigns CT towns to these region codes. 8 extra `vintage=2020` rows cover the old counties 09001–09015 from the TIGER 2020 Gazetteer, with `has_own_government=no`, because CoG lists no county government in CT. 2020-vintage joins go town → planning region (`data-v3/geo/ALIGNMENT.md` §2). No other county differs between the 2020 and 2024 sets for the 50 states and DC. Puerto Rico is outside `counties.csv` in both years.
- Summary: `county_government_summary.json`.
