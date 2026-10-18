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
| `governments_geoid_xwalk.csv` | 56,484 | every (entity, TIGER GEOID) pair, primary included |
| `county_government_check.csv` | 3,222 | each TIGER 2024 county (incl. 78 PR municipios) and whether CoG 2022 lists a county government there |
| `id_registry.csv` | 93,251 | frozen entity IDs (see SCHEMA.md); committed and appended by every build |
| `sources.csv` | 13 | stable source codes used in `source` columns |
| `summary.json` | | row counts, match counts, source URLs/dates (written by the build) |
| `scripts/` | | Python 3 stdlib + `openpyxl` (to read the CoG .xlsx) |

Exact current counts are always in `summary.json`.

## Sources (open, public domain U.S. Government works)
| code | source | URL | date |
|---|---|---|---|
| `cog2022` | U.S. Census Bureau, 2022 Census of Governments: Organization, Government Units Listing (`Govt_Units_2022_Final.xlsx`, tabs General Purpose / Special District / School District / DEP School Dist) | https://www2.census.gov/programs-surveys/gus/datasets/2022/govt_units_2022.ZIP | published 2023-08-24 |
| `gaz2024` | Census TIGER 2024 Gazetteer national files: counties, cousubs, place, unsd, elsd, scsd | https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/ | 2024 vintage |
| `tiger2024_aiannh` | TIGER/Line 2024 AIANNH shapefile (attribute table only; the Gazetteer AIANNH file has no ANVSAs or R/T parts) | https://www2.census.gov/geo/tiger/TIGER2024/AIANNH/tl_2024_us_aiannh.zip | 2025-06-27 |
| `gaz2022`, `gaz2020` | Census 2022 and 2020 Gazetteer place + cousub files, used only for units missing from TIGER 2024 | https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2022_Gazetteer/, .../2020_Gazetteer/ | 2022 / 2020 vintage |
| `concity2024` | TIGER/Line 2024 consolidated cities (attribute tables, states 09 13 18 20 21 30 47) | https://www2.census.gov/geo/tiger/TIGER2024/CONCITY/ | 2024 vintage |
| `f33` | Census Annual Survey of School System Finances (F-33) unit files `elsec24.txt`, `elsec23.txt`, `elsec22.txt` (FY2024, FY2023, FY2022): `PID6` (= CoG `CENSUS_ID_PID6`) and `NCESID` (= NCES LEAID). Current layout (FY2024 doc `school24doc.docx`) carries `PID6`, not the old 14-digit `IDCENSUS` | https://www2.census.gov/programs-surveys/school-finances/tables/2024/secondary-education-finance/elsec24.txt | FY2024 |
| `census_state_codes` | Census 2020 FIPS state codes | https://www2.census.gov/geo/docs/reference/codes2020/national_state2020.txt | 2023-02-13 |
| `fr_agencies` | Federal Register API v1 agencies | https://www.federalregister.gov/api/v1/agencies | retrieved 2026-10-18 |
| `bia:2026-01899` | BIA, "Indian Entities Recognized by and Eligible To Receive Services From the United States Bureau of Indian Affairs", 91 FR 4102 | https://www.federalregister.gov/documents/2026/01/30/2026-01899/ | published 2026-01-30 |

Every entity row carries `source` (codes from `sources.csv`), `source_date`, `retrieved_at` and `license`;
`source_url` only where it is row-specific.
No paid data, no NYT data.

## How GEOIDs are assigned (`geoid_match`)
Code joins first; name matching only as a labeled `fallback_*`; anything else blank and counted. `geoid_vintage` is
2024 unless an older GEOID had to be carried (then `tiger_status=absent_2024`).

| type | rule | codes (counts) |
|---|---|---|
| state | 2-digit FIPS | `fips` 50 |
| county | CoG `FIPS_STATE+FIPS_COUNTY` in the 2024 county Gazetteer | `fips` 3,031 |
| municipality | `FIPS_STATE+FIPS_PLACE` in the 2024 place Gazetteer (crosswalk adds `coextensive_cousub`, `independent_city_county_equivalent` for VA/MD/MO/NV cities, `consolidated_city_county` for "City and County of X" and consolidated cities, and `consolidated_city` = TIGER CONCITY GEOID) | `fips` 19,465 |
| | CoG code is a TIGER 2024 CONCITY code → the TIGER `<CONCITY NAMELSAD> (balance)` place: Athens-Clarke 1303440, Louisville/Jefferson 2148006, Nashville-Davidson 4752006, Butte-Silver Bow 3011397, Greeley County KS 2028412 (CONCITY GEOID + county in the crosswalk) | `concity_balance` 5 |
| | "CITY AND COUNTY OF X" whose place code is not in TIGER → county X (Honolulu → 15003) | `city_and_county_name` 1 |
| township | `FIPS_STATE+FIPS_COUNTY+FIPS_PLACE` in the 2024 cousub Gazetteer (other county parts → `county_part`); if the code exists exactly once elsewhere in the state → `fips_other_county` (Pomfret CT: CoG county 09180 looks like a coding slip for 09150 Northeastern CT planning region) | `fips` 16,176, `fips_other_county` 1 |
| municipality / township not in TIGER 2024 | (1) code in the 2022, then 2020 Gazetteer, followed into 2024 by the same ANSI code (MA "city known as the town of" renames, TX Pecos → "Town of Pecos city", IN DeMotte, MN Minnetonka Beach…) | `ansi_via_2022` 9, `ansi_via_2020` 1 |
| | (2) labeled fallback: unique TIGER 2024 feature with the same core name and compatible kind in the same state (cousubs: same county); predecessor code kept in the crosswalk | `fallback_name_2024` 7 |
| | (3) otherwise the old GEOID is carried: `geoid_vintage` 2022/2020, `tiger_status=absent_2024` (dissolved or merged units, e.g. 14 Nebraska 31099 townships, WI towns Madison, Rib Mountain, Greenville, Lisbon, Weeki Wachee FL) | `fips_2022` 35, `fips_2020` 1 |
| | code-only rule for the rest: CoG code equals no TIGER 2020/2022/2024 code (Bellerive MO 04240 vs TIGER Bellerive Acres 04248, Grandfather NC 27320 vs Grandfather Village 27324, North Rich twp KS 51325, Millican TX 48516), left blank with the reason in `note` | `not_in_tiger_2020_2024` 4 |
| school_district | code join: CoG `CENSUS_ID_PID6` = F-33 `PID6` → `NCESID` (`nces_leaid` column), which is the TIGER unsd/elsd/scsd GEOID. Newest F-33 file that lists the unit wins | `f33_ncesid_2024` 12,920, `f33_ncesid_2023` 8; `f33_ncesid_not_in_tiger_2024` 274 (LEAID kept in `nces_leaid`, geoid blank: mostly regional/vocational/charter-type LEAs with no TIGER polygon) |
| | units absent from F-33: name match in the state against the TIGER layer for the CoG level, unique only (abbreviations expanded; tiers exact → core) | `fallback_name_exact` 5, `fallback_name_core` 5, `no_name_match` 114 |
| | TIGER secondary areas of a unified LEA (`NAME (9-12)` / `(7-12)` scsd with a unique same-named unsd in the state, plus Washington Unified CA 0601415 → 0606018 confirmed by Geo) go to the crosswalk as `secondary_9_12` / `secondary_7_12` | 29 rows |
| | post-secondary / vocational units not in F-33 | `no_tiger_layer` 529 |
| | one NCESID claimed by several CoG units (SC: Clarendon 1/2/3 → 4503915, Bamberg 1 → 4503916, consolidated after 2022) | `ambiguous` 4 |
| special_district | TIGER has no special-district layer | `no_tiger_layer` 39,555 |
| tribe | contiguous 48: a federal AIANNH reservation part's legal name (e.g. "Agua Caliente Indian Reservation", "Acoma Pueblo" / "Pueblo of Acoma") appears verbatim in the BIA name (word INDIAN ignored) → `legal_name_in_tribe_name` 133. Alaska: village core of the name equals exactly one ANVSA name → `name_core_anvsa` 171. R and T parts both go to the crosswalk; `geoid` holds the R part. Others blank: `no_name_match` 269 (many tribes have no land area, or a name that does not contain the area's name), `cross_reference` 4 | |

Verification: all 12,938 school GEOIDs on entities are in `data-v3/geo/schools.csv` (main); F-33 agrees with the
earlier name-only matching on 9,434 of 9,435 districts (Washington Unified CA, Fresno County, CoG level secondary:
F-33 gives the unified 0601415, name matching had picked the 9-12 area 0606018). 367 `schools.csv` GEOIDs have no
CoG entity (mostly CA/AZ/VT/MA paired elementary + high districts that CoG and F-33 treat as one government).
36 units carry an absent-from-2024 GEOID; 32 of them are on the Geography bot's list of 2020 places/towns missing
from 2024 (`v2/data/COVERAGE.md` on `data/geo` @ fd003ab, list in `geo-data-raw/zcta_xref_report.json`); the other
4 (KS Victoria twp, NE Blaine and Hayes twps, WI Lisbon town) exist in 2022 but not 2024.

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
