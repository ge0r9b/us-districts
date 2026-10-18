# data-v3/institutions/governments: US government entities (first pull, Oct 18, 2026)

Every US government we can list from open federal sources, one row per government, with stable IDs, TIGER 2024
GEOIDs where an exact rule finds one, and per-row provenance. The column definitions and type list are in
[SCHEMA.md](SCHEMA.md). Nothing in `v2/` or elsewhere in the repo is changed.

## Files
| file | rows | content |
|---|---|---|
| `states.csv` | 50 | state governments (`state:SS`) |
| `local/<USPS>.csv` | 92,150 total in 51 files (50 states + DC) | every unit in the 2022 Census of Governments individual-unit file: 3,031 county, 19,491 municipality, 16,214 township, 12,546 independent school districts + 1,313 dependent school systems, 39,555 special districts |
| `federal_agencies.csv` | 473 | Federal Register agencies and sub-agencies with `parent_id` (includes abolished agencies; the API has no active flag) |
| `tribes.csv` | 577 | every line of the latest BIA list (FR 2026-01899, 91 FR 4102, Jan 30, 2026: 348 contiguous-48 lines + 229 Alaska lines; 4 of them are "(See …)" cross-references). The notice text says 575 entities. |
| `governments_geoid_xwalk.csv` | 52,904 | every (entity, TIGER GEOID) pair, primary included |
| `county_government_check.csv` | 3,222 | each TIGER 2024 county (incl. 78 PR municipios) and whether CoG 2022 lists a county government there |
| `summary.json` | | row counts, match counts, source URLs/dates (written by the build) |
| `scripts/` | | Python 3 stdlib + `openpyxl` (to read the CoG .xlsx) |

Exact current counts are always in `summary.json`.

## Sources (open, public domain U.S. Government works)
| code | source | URL | date |
|---|---|---|---|
| `cog2022` | U.S. Census Bureau, 2022 Census of Governments: Organization, Government Units Listing (`Govt_Units_2022_Final.xlsx`, tabs General Purpose / Special District / School District / DEP School Dist) | https://www2.census.gov/programs-surveys/gus/datasets/2022/govt_units_2022.ZIP | published 2023-08-24 |
| `gaz2024` | Census TIGER 2024 Gazetteer national files: counties, cousubs, place, unsd, elsd, scsd | https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/ | 2024 vintage |
| `tiger2024_aiannh` | TIGER/Line 2024 AIANNH shapefile (attribute table only; the Gazetteer AIANNH file has no ANVSAs or R/T parts) | https://www2.census.gov/geo/tiger/TIGER2024/AIANNH/tl_2024_us_aiannh.zip | 2025-06-27 |
| `census_state_codes` | Census 2020 FIPS state codes | https://www2.census.gov/geo/docs/reference/codes2020/national_state2020.txt | 2023-02-13 |
| `fr_agencies` | Federal Register API v1 agencies | https://www.federalregister.gov/api/v1/agencies | retrieved 2026-10-18 |
| `bia:2026-01899` | BIA, "Indian Entities Recognized by and Eligible To Receive Services From the United States Bureau of Indian Affairs", 91 FR 4102 | https://www.federalregister.gov/documents/2026/01/30/2026-01899/ | published 2026-01-30 |

Every entity row carries `source`, `source_url`, `source_date`, `retrieved_at` and `license`.
No paid data, no NYT data.

## How GEOIDs are assigned (`geoid_match`)
Only exact rules; anything else stays blank and is counted. Vintage is TIGER 2024 everywhere.

| type | rule | codes |
|---|---|---|
| state | 2-digit FIPS | `fips` |
| county | CoG `FIPS_STATE+FIPS_COUNTY`, if present in the 2024 county Gazetteer | `fips` (all 3,031) |
| municipality | `FIPS_STATE+FIPS_PLACE` in the 2024 place Gazetteer. If a 2024 cousub with the same code exists in the CoG county, it is added to the crosswalk as `coextensive_cousub`; if the CoG county is a TIGER county-equivalent named "<same name> city", it is added as `independent_city_county_equivalent` (VA, MD, MO, NV) | `fips`, `not_in_tiger_2024` (26) |
| township | `FIPS_STATE+FIPS_COUNTY+FIPS_PLACE` in the 2024 cousub Gazetteer (other county parts of the same cousub code → `county_part`); if not in that county but the code exists exactly once elsewhere in the state → `fips_other_county` | `fips`, `fips_other_county` (1), `not_in_tiger_2024` (37) |
| school_district | name match within the state against the TIGER layer for the CoG level (unified→unsd, elementary→elsd, secondary→scsd, non-operating→any), unique candidate only, tiers in order: `name_exact` (after expanding CoG abbreviations like SCH DIST, IND, CTL, TWP), `name_core` (generic words SCHOOL/DISTRICT/PUBLIC/INDEPENDENT… dropped), `name_core_no_number` (CoG trailing district number dropped, only against TIGER names without a number). A GEOID claimed by two units goes to the stronger tier; ties are dropped. Post-secondary and vocational units: `no_tiger_layer` | `name_exact` 6,084, `name_core` 1,079, `name_core_no_number` 2,283, `no_name_match` 3,526, `ambiguous` 133, `no_tiger_layer` 754 |
| special_district | TIGER has no special-district layer | `no_tiger_layer` |
| tribe | contiguous 48: a federal AIANNH reservation part's legal name (e.g. "Agua Caliente Indian Reservation", "Acoma Pueblo" / "Pueblo of Acoma") appears verbatim in the BIA name (word INDIAN ignored) → `legal_name_in_tribe_name` (133). Alaska: village core of the name equals exactly one ANVSA name → `name_core_anvsa` (171). R and T parts both go to the crosswalk; `geoid` holds the R part. Others blank: `no_name_match` (269; many tribes have no land area, or a name that does not contain the area's name), `cross_reference` (4) | |

`parent_id`: local units → their state (`state:SS`); DC units have no parent (no state government). The CoG file
does not say which government a dependent school system belongs to (only its type, kept in `note`), and it gives no
county → municipality containment, so no such parents are set. `county_geoid` is the CoG county area, not a parent.
FR agencies use the API's `parent_id`. States and tribes have no parent.

## Rerun
```
cd data-v3/institutions/governments
pip install openpyxl                         # only non-stdlib dependency
python3 scripts/fetch_sources.py             # downloads into cache/ (gitignored); skips cached files
python3 scripts/fetch_sources.py --refresh   # re-download everything (new retrieved_at)
python3 scripts/build_all.py                 # rewrites all CSVs + summary.json
```
The build is deterministic: with the same `cache/` it reproduces byte-identical files. `fetch_sources.py` always
picks the newest BIA list notice from the Federal Register search, so a refresh after a new notice picks it up.
`cache/manifest.json` records URL, Last-Modified and retrieval time per file. Raw downloads are never committed.

Scripts: `common.py` (download/cache, readers, column lists), `build_states.py`, `build_cog.py`,
`build_federal_agencies.py`, `build_tribes.py`, `build_all.py`.
