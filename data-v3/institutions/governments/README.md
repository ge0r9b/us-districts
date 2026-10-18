# data-v3/institutions/governments: US government entities (first pull, Oct 18, 2026)

Every US government we can list from open federal sources, one row per government, with stable IDs, TIGER 2024
GEOIDs where an exact rule finds one, and per-row provenance. The column definitions and type list are in
[SCHEMA.md](SCHEMA.md). Nothing in `v2/` or elsewhere in the repo is changed.

## Files
| file | rows | content |
|---|---|---|
| `states.csv` | 50 | state governments (`state:SS`) |
| `local/<USPS>.csv` | 92,178 total in 51 files (50 states + DC) | every unit in the 2022 Census of Governments individual-unit file (92,150) plus 28 units created since: 3,031 county, 19,491 municipality, 16,214 township, 12,546 independent school districts + 1,313 dependent school systems, 39,555 special districts |
| `federal_agencies.csv` | 473 | Federal Register agencies and sub-agencies with `parent_id` (includes abolished agencies; the API has no active flag) |
| `tribes.csv` | 577 | every line of the latest BIA list (FR 2026-01899, 91 FR 4102, Jan 30, 2026: 348 contiguous-48 lines + 229 Alaska lines; 4 of them are "(See …)" cross-references). The notice text says 575 entities. |
| `governments_geoid_xwalk.csv` | 56,529 | every (entity, TIGER GEOID) pair, primary included |
| `county_government_check.csv` | 3,222 | each TIGER 2024 county (incl. 78 PR municipios) and whether CoG 2022 lists a county government there |
| `id_registry.csv` | 93,278 | frozen entity IDs (see SCHEMA.md); committed and appended by every build |
| `sources.csv` | 19 | stable source codes used in `source` columns |
| `changes_since_cog2022.csv` | 131 | incorporations, dissolutions, mergers, consolidations, reclassifications after the CoG 2022 snapshot (see below) |
| `images.csv` | 2,024 | seal (1,967) and flag (57) image records: Commons/Wikipedia file, license, attribution, QID (no binaries) |
| `images_gaps.csv` | 37,896 | in-scope entities without an image, with the reason |
| `changes_curated.csv` | 26 | hand-entered input for the changes cited to state sources |
| `summary.json` | | row counts, match counts, source URLs/dates (written by the build) |
| `scripts/` | | Python 3 stdlib + `openpyxl` (to read the CoG .xlsx) |

Exact current counts are always in `summary.json`.

## Sources (open public records: U.S. Government works, plus the state records listed under Changes)
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
| `census_gcn` | Census Geographic Change Notes (BAS), national files 2021-2025 | https://www2.census.gov/geo/docs/reference/bndrychange/ | retrieved 2026-10-18 |
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

## Changes since the 2022 Census of Governments
`changes_since_cog2022.csv`, applied to the entity rows: ceased units get `is_active=false`, `valid_to` and the flag
`ceased` (never deleted); new units are added with `valid_from` and the flag `not_in_cog2022`.

Sources:
- `census_gcn`: Census Bureau Geographic Change Notes (Boundary and Annexation Survey), national files for
  effective years 2021-2025 (https://www2.census.gov/geo/docs/reference/bndrychange/). These are the federal record of
  incorporations, disincorporations, mergers and legal-description changes reported by state and local governments,
  so they cover every state in one pass. A GCN record is used only when its state + code (or ANSI code) is the CoG
  unit's code, its core name equals the CoG core name and its kind (city/village/borough vs township) agrees. Records
  that only follow redistricting (voting-district cousubs in AR, NE, VA, WV), CDPs, UTs and Census spelling
  corrections ("Corrected ...") are skipped. New units must be a governmental kind and not already in CoG; new
  townships only in states whose CoG has township governments. A 2024-2025 incorporation whose code TIGER 2024 still
  shows as a CDP gets no GEOID (note says so). Where GCN's ANSI code disagrees with TIGER 2024, TIGER's is kept and the
  note says so (GCN gives Gluckstadt MS and Hochatown OK the same ANSI code).
- State sources (`changes_curated.csv`): South Carolina Legislature acts 104, 105, 106 of 2021 and 256 of 2022 (Bamberg,
  Barnwell, Clarendon and Florence school consolidations, July 1, 2022) and Act 183 of 2020 (S. 975: Clarendon County
  School Districts 1 and 3 abolished July 1, 2021 and consolidated as Clarendon County School District No. 4, which
  Act 106 then merged with No. 2 on July 1, 2022; No. 4 is kept as a ceased `sc_act:2020-183:clarendon_4` row) plus the SC Department of Education letter for
  the Florence 4 date; Nebraska official 2020 Kearney County results + Neb. Rev. Stat. 23-295 (14 townships
  discontinued, January 2023; the statute fixes only the month); Maine P&SL 2017 ch. 11 + Maine Revenue Services
  deorganization list (Codyville, July 1, 2019); Florida CS/HB 1215 = Laws of Florida 2020-196 (Weeki Wachee,
  June 9, 2020); Wisconsin DOA Municipal Data System (Village of French Island, May 21, 2026).
- Texas special districts (`changes_tceq_wdd.csv`, generated by `scripts/tceq_wdd.py` + `scripts/tx_wdd_changes.py`
  from the TCEQ Water Districts Database, every row citing its WDD detail page): 9 dissolutions (CoG units whose name,
  abbreviations expanded, is unique in CoG TX special districts and in the WDD, same primary county, WDD status
  DELETED/DISSOLVED or MERGED/ANNEXED dated 2021 or later; the date is the WDD activity date) and 305 `creation` rows
  (WDD districts created 2022-01-01 or later, status ACTIVE, no CoG name match; entity_id `tceq_wdd:<WDD ID>`, subtype =
  the TCEQ district type). Counted, not added: 333 created since 2022 but INACTIVE (not operating, which CoG does not
  count), 1 PROPOSED, 19 CoG units the WDD shows dissolved before 2021. The Texas Comptroller Special Purpose District
  Public Information Database (https://spdpid.comptroller.texas.gov/) was checked: it is self-reported financial and
  contact data with no creation or dissolution dates, so it gives no dated change and is not used.

Counts by change type and source: consolidation_abolished / sc_legislature 9, consolidation_new_entity / sc_legislature 4, creation / tceq_wdd 305, dissolution / census_gcn 42, dissolution / fl_legislature 1, dissolution / me_legislature 1, dissolution / ne_kearney_election 14, dissolution / tceq_wdd 9, incorporation / census_gcn 18, incorporation / wi_mds 1, new_township / census_gcn 6, reclassification / census_gcn 39.

Not recorded (could not be confirmed from an official source in this pass, or out of scope): Rib Mountain WI, where GCN gives
2023-07-11 and WI MDS gives 2023-07-21 (GCN date kept); California special districts (blocker: the State
Controller's public lists on bythenumbers.sco.ca.gov, "FY 2021-22 / 2022-23 / 2023-24 California Independent Special
Districts" (1,704 / 1,702 / 1,924 names), carry a number and a name only, no formation or dissolution date, and SCO itself
says the list "may not be the most reliable source" while its alignment with GC 56044/56036 is evaluated, so a name
missing or added between years is not an official change; the SCO inactive list gives no dissolution date either;
LAFCO dissolutions are per-county resolutions with no statewide official list; none are recorded); Texas special districts outside the WDD (e.g. emergency services, hospital,
housing districts) are not covered; CoG 2022 omissions that are not changes (Howard KS,
Keene KY, St. Mary KY, Plantersville TX, Poetry TX existed before 2022) are not added.

## Wikidata QIDs and images
**Fair-use basis (stated by the user for the app).** The app uses governments' logos and seals only as shorthand to
identify and discuss the entities in relation to votes and public opinion. It does not represent or speak for them; an
entity can speak for itself only by claiming its page on the app and posting there. Only small identification icons are
used. Rows with `license=fair-use` carry `usage_basis=identification icon, small size` and the `source_url` of the file;
no image files are stored in this repo.

QIDs come only from exact identifier links (rules in SCHEMA.md): qid_by_p5087 50, qid_by_p590 16,194, qid_by_p774 19,390, qid_by_p882 3,030. Unassigned: item_shared 10, multiple_items 5, no_item 68, p774_p590_disagree 64.
`images.csv`: 6,119 seals, 57 flags and 141 logos (4,574 rows are `fair-use`: files hosted on English Wikipedia, and the Federal
Register agency logos, used as identification icons, usage_basis `identification icon, small size`). By kind and entity type: flag / dc 1, flag / nation 1, flag / state 50, flag / territory 5, logo / federal_agency / fr_logo 141, seal / county 250, seal / county / enwiki_fair_use 831, seal / county / enwiki_free 72, seal / dc 1, seal / federal_agency 69, seal / federal_agency / enwiki_free 14, seal / municipality 648, seal / municipality / enwiki_fair_use 2484, seal / municipality / enwiki_free 239, seal / nation 1, seal / state 50, seal / territory 1, seal / territory / enwiki_free 1, seal / township 119, seal / township / enwiki_fair_use 1115, seal / township / enwiki_free 218, seal / tribe 1, seal / tribe / enwiki_fair_use 3, seal / tribe / enwiki_free 2.
By license: CC-BY-3.0 3, CC-BY-4.0 15, CC-BY-SA-3.0 31, CC-BY-SA-4.0 115, CC0-1.0 40, GFDL-1.2-or-later 1, LicenseRef-Attribution 2, LicenseRef-Copyrighted-free-use 4, LicenseRef-GPL 1, LicenseRef-PublicDomain 1531, fair-use 4574. Queries: Wikidata SPARQL in batches of at most 400 VALUES, Commons/Wikipedia API at 50 titles per
request, one request per second, User-Agent naming this repo; all responses are cached in `cache/` (gitignored), so a
rerun with a full cache makes no requests. Not covered: special districts (no identifier property) and school districts
(skipped by rule).
Federal agencies: Wikidata has no Federal Register agency-ID property, and P1813 (short name) is a name, so the exact
link is the official website: the FR API `agency_url` must equal an item's P856 after normalisation (scheme, leading
`www.`, trailing slash, query dropped; host + path compared exactly), the item must be an organisation (P31/P279*
Q43229; this drops P856 on offices, positions and CFR titles, e.g. defense.gov on "Assistant Secretary of Defense for
Public Affairs") and the usual uniqueness rule holds. One reviewed reject: fr:334 National Counterintelligence Center,
whose FR `agency_url` is nctc.gov (the Counterterrorism Center). Result: 144 of 473 agencies get a QID; none: no
agency_url 206, no item 104, several items 11, URL shared by several agencies 7, rejected 1. Seals: P158, then the
enwiki fallback, then the agency logo the Federal Register shows (`image_kind=logo`, `fair-use`, `source_url` =
agency-logos.federalregister.gov), for agencies with or without a QID.
The enwiki seal fallback covers municipalities and townships too (same single-file and uniqueness rules as counties,
plus: a file named only for a state, e.g. `Seal utah.png`, is never taken for a city).

## Foreign governments (`foreign/`, `scripts/build_foreign.py`)
Built in the same run as everything else (`scripts/build_all.py`); every row cites its sources (`source`, `source_url`,
`retrieved_at`, `license`), IDs are frozen in `id_registry.csv` (keys `iso3166-1:XX`, `iso3166-2:XX-YYY`).

| file | rows | what |
|---|---|---|
| `foreign/nations.csv` | 196 | `nation:<iso2>`, `type=sovereign`: the 193 UN members (un.org Member States page, with date of admission) minus the US (already `nation:us`), the 2 UN observer States (Holy See `nation:va`, State of Palestine `nation:ps`), and 2 ISO 3166-1 entries with no single UN-member sovereign: Taiwan `nation:tw` and Western Sahara `nation:eh` (`subtype=non_un_state`, `gov_status=disputed_or_unrecognized`, flag `review_status`) |
| `foreign/dependencies.csv` | 44 | `territory:<iso2>`, `type=foreign`, parent = sovereign `nation:<iso2>`: every other ISO 3166-1 entry with a government; sovereign from Wikidata P17 (also P131/P361 for the realm items Kingdom of Denmark, Kingdom of the Netherlands, Realm of New Zealand, which carry no P297), Isle of Man reviewed (Crown Dependency, like Jersey/Guernsey). `subtype` = the ISO 3166-2 type where the sovereign's ISO 3166-2 list has the place (e.g. `special administrative region`, `overseas collectivity`), else `dependency`. U.S. Minor Outlying Islands = `territory:74` (FIPS, like the other U.S. territories), parent `nation:us` |
| `foreign/subdivisions.csv` | 3515 | first-level ISO 3166-2 subdivisions (iso-codes entries without `parent`) of 199 countries/dependencies, `type=foreign`, `subtype` = ISO type lowercased (province 762, region 465, municipality 397, district 294, state 229, ...). Canada: `province:ca-<code>` / `territory:ca-<code>` with `external_ids=statcan_sgc:<2-digit SGC 2021 code>` (Statistics Canada SGC 2021 structure CSV, joined on the exact province name, all 13 match); every other country `subdivision:<iso 3166-2 lowercased>` (proposal, see SCHEMA.md) |
| `foreign/iso_domestic_crosswalk.csv` | | ISO codes that are not built here: the US and its 57 ISO 3166-2 entries map to the domestic rows (`nation:us`, `state:SS`, DC `cog:124214`, `territory:60/66/69/72/78/74`); 17 ISO 3166-2 codes that are the same Wikidata item as an ISO 3166-1 entry (e.g. CN-HK, FR-971, NL-AW) map to that `territory:` row; CN-TW (ISO lists Taiwan as a province of China) maps to `nation:tw` and is not built twice |

Not built: Antarctica (AQ, no government), Bouvet Island (BV) and Heard and McDonald Islands (HM) (uninhabited, no own
government); second-level ISO 3166-2 entries (1456).
QIDs only by exact code: P297 = alpha-2 for nations/dependencies (one live item per code, not dissolved; Cyprus has two
items, the one with UN membership P463 is taken: `qid_by_p297_and_p463`), P300 = ISO 3166-2 code for subdivisions
(3408 `qid_by_p300`; none: no item 77, several items 29, item with several codes 1). UN membership: un.org names
matched to iso-codes `name` / `official_name` / `common_name`; 7 UN short forms (Bahamas (The), China (the People's
Republic of), Democratic Republic of the Congo, Gambia (Republic of The), Naoero, Netherlands (Kingdom of the), Republic of
Korea) are a reviewed list that the build only accepts when the Wikidata P297 item has UN membership (P463 Q1065);
192 of 193 also carry P463 on the P297 item (Denmark's is on the Kingdom of Denmark item). Columns from Wikidata on the
matched item: `capital_qid`/`capital` (P36), `head_of_government_office_qid`/`head_of_government_office` (P1313).
Images (in `images.csv`, same rules as domestic): flag = P41; seal = P158, else P94 coat of arms (stored as
`image_kind=seal` with `usage_basis=coat of arms (P94) used as the seal`); most open license first. 3529 rows
(1726 flags, 1803 seals); gaps in `images_gaps.csv`: no P41 1922, no P158/P94 1845, no QID 107 (per kind).
Sovereign items: the nation row's `wikidata_qid` is the sovereign-state item (P31 Q3624078). If the P297 item is not one
but is part of exactly one live sovereign state (its P361, or the state's P150/P527), that state is taken and the P297
item goes to `constituent_qid`; if the P297 item is the sovereign state and has exactly one part that is a constituent
country (P31/P279? Q1763527) without its own P297, that part is `constituent_qid`. Checked on Wikidata (2026-10-18): Denmark
Q35 (not a sovereign state) -> Kingdom of Denmark Q756617, constituent Q35; P297 NL is already on Kingdom of the
Netherlands Q29999 (sovereign state), constituent the Netherlands Q55; New Zealand Q664 and the United Kingdom Q145 are the
sovereign-state items themselves (Realm of New Zealand Q889033 and "realm of the United Kingdom" Q124653007 are not
sovereign states; the UK's four countries are subdivisions here, so no constituent). Images stay on the item they are on:
the sovereign item first, then the constituent item (`images.csv` `wikidata_qid` says which); nation:dk's flag and coat
of arms are the same files on Q756617, so only their `wikidata_qid` changed (Q35 -> Q756617).
`valid_from`: Wikidata P571 with a P248/P854 reference only (174 rows: 21 nations, 5 dependencies, 148 subdivisions;
7 with disagreeing referenced values left blank); `valid_to` blank. ISO changes go forward with frozen IDs: a code
dropped by a later iso-codes release keeps its row (`is_active=N`, `iso_code_withdrawn`).
Not done in this pass: CIA World Factbook government type (no column yet), INEGI (MX) and ONS (UK) codes as
`external_ids`, local-language labels, an enwiki fair-use fallback for foreign seals.

## UK, Germany, France: every government level (`foreign/gb/`, `foreign/de/`, `foreign/fr/`)
One builder per country (`scripts/build_foreign_<cc>.py`, shared helpers in `scripts/foreign_local.py`), run by
`build_all.py` (or alone: `python3 scripts/build_foreign_<cc>.py`; the FR one saves the registry only with `--save`). Columns, ID proposals and crosswalks: SCHEMA.md.
The existing `nation:` and ISO first-level `subdivision:` rows are reused, never duplicated (`code_xwalk.csv`).

### UK (`foreign/gb/`)
Source: ONS Register of Geographic Codes (RGC) June 2026 (all live codes with name, Welsh name, operative date,
statutory instrument and parent code), ONS ward lookup WD26_LAD26_CTYUA26_RGN26_CTRY26_UK_LU (Scottish council areas,
which the RGC workbook has no sheets for; it also confirms the live LAD set: no difference), ONS LAD25_CAUTH25_EN_LU
(combined authority membership, May 2025; all 15 live combined authorities are covered). OGL v3.0.

| level | GSS | rows | parent |
|---|---|---|---|
| UK Government | K02 | existing `nation:gb` | |
| devolved governments | S92/W92/N92 | existing `subdivision:gb-sct/wls/nir` | `nation:gb` |
| Greater London Authority | E61 | 1 | `nation:gb` |
| combined (county) authorities | E47 | 15 | `nation:gb` |
| county councils | E10 | 21 | combined authority if all its districts are in one (Cambridgeshire etc.), else `nation:gb` |
| unitary authorities | E06 | 63 | combined authority or `nation:gb` |
| non-metropolitan districts | E07 | 164 | county (`member_of` = combined authority) |
| metropolitan boroughs | E08 | 36 | combined authority |
| London boroughs + City of London | E09 | 33 | GLA |
| Welsh principal councils | W06 | 22 | `subdivision:gb-wls` |
| Scottish council areas | S12 | 32 | `subdivision:gb-sct` |
| NI district councils | N09 | 11 | `subdivision:gb-nir` |
| civil parishes (England) | E04 | 10,463 | local authority |
| communities (Wales) | W04 | 878 | principal council |

England (E92000001) maps to `subdivision:gb-eng` as an area only; it has no devolved government, so English councils
sit under `nation:gb`. Not every parish/community has a council (some have only a parish meeting) and no ONS product
says which, so all carry `council_status_unknown`. Wikidata QIDs and ISO 3166-2 codes only through the exact GSS code
(P836) on a single item (QIDs for 10,619 rows; ISO 3166-2 for 180 councils). `boundary_xwalk.csv`: every unit's code was
found in its BGC/BUC product (LAD May 2025: 361/361; parishes PARNCP May 2026 BGC: 11,341/11,341; counties Dec 2025,
CAUTH May 2025, Regions Dec 2025 for the GLA, Countries Dec 2025). `gaps.csv` lists mismatches (none). The RGC lists
parish E04013473 Westbury twice (two community-governance orders); it is one row.
Not covered: Scottish Gaelic names (not in the RGC), community councils in Scotland and NI (not statutory local
government, no GSS codes), parish council existence, abolished councils (only live codes).

### Germany (`foreign/de/`)
Sources: Destatis Regionalschlüssel code list 2026-09-30 (every Gemeinde by ARS, as in GV-ISys; Destatis publishes it on
XRepository) and BKG VG250 Stand 01.01.2026 attribute tables via WFS (Länder, Regierungsbezirke, Kreise, Gemeindeverbände,
Gemeinden with designation `BEZ` and `WSK`), both dl-de/by-2-0. **Blocker:** www.destatis.de (GV100AD / GV-ISys Excel)
refuses TLS connections from the build host, so the GV100AD file itself was not used; the XRepository list is Destatis's
own key list and carries Gemeinden only, so the upper levels come from VG250 (BKG, built on the same ARS).

| level | rows | parent |
|---|---|---|
| Bund | existing `nation:de` | |
| Länder | existing `subdivision:de-xx` (16; ARS Land code → ISO checked by name) | `nation:de` |
| Regierungsbezirke (`gov_status=administrative`) | 19 | Land |
| Landkreise / Kreise | 252 + 42 | Regierungsbezirk or Land |
| kreisfreie Städte / Stadtkreise | 96 + 9 (+ Berlin, Hamburg = their Land rows) | Regierungsbezirk or Land |
| Gemeindeverbände: Verwaltungsgemeinschaft 573, Amt 209, Verbandsgemeinde 149, Verwaltungsverband 120, Samtgemeinde 114, erfüllende Gemeinde 38 | 1,203 | Kreis |
| Gemeinden (Gemeinde 8,690, Stadt 1,950) | 10,640 | Gemeindeverband or Kreis |

All 10,747 Gemeinden of the Destatis list are covered (10,640 + 105 kreisfreie Städte + Berlin + Hamburg); 197
areas without a municipal government (gemeindefreie Gebiete, coastal waters, the German-Luxembourg condominium, Verband key
9999) are left out. Changes between VG250 (Jan 2026) and Destatis (Sep 2026) are in `gaps.csv`: Hanau kreisfrei
(06415, flag `kreisfrei_from_ars_structure`), Schmölln's erfüllende Gemeinde without members, a few Gemeinden with a new
Verband key. QIDs by exact ARS (P1388) or Kreisschlüssel (P440), 1:1 only. `boundary_xwalk.csv`: VG250 (all levels) and
VG1000 (Staat, Länder, RBZ, Kreise), only codes present in the layer.
Not covered: GV100AD-only fields (Destatis host blocked), official English names (none published), dissolved units.

### France (`foreign/fr/`; units split in `units_upper.csv` and `units_communes_<région>.csv` for the 10 MB limit)
Sources: INSEE COG au 1er janvier 2026, INSEE Base des EPCI à fiscalité propre et des EPT au 1er janvier 2026, IGN ADMIN
EXPRESS COG CARTO (attribute tables via WFS, latest edition = COG 2026), all Licence Ouverte 2.0.

| level | rows | parent |
|---|---|---|
| État | existing `nation:fr` | |
| régions | 12 metropolitan → existing `subdivision:fr-*` (Wikidata item with INSEE code P2585 and ISO P300), Corse → `subdivision:fr-20r`, Martinique/Guyane/Mayotte → their single collectivity's `territory:` row; new: Guadeloupe, La Réunion (`fr-cog:reg:01/04`) | `nation:fr` |
| département-level collectivities (CTCD) | 91 conseils départementaux (`fr-cog:dep:XX`), Métropole de Lyon, Collectivité européenne d'Alsace (`fr-cog:ctcd:69M/6AE`), Ville de Paris (= commune 75056); existing: Corse, Martinique, Guyane, Mayotte, and the départements of Guadeloupe and La Réunion (= `territory:gp/re`, ISO FR-971/974 "overseas departmental collectivity") | région |
| collectivités d'outre-mer | existing `territory:pm/bl/mf/tf/wf/pf/nc`, `subdivision:fr-cp` (code_xwalk) | |
| EPCI à fiscalité propre (SIREN) | 21 métropoles, 14 CU, 230 CA, 987 CC (+ Métropole de Lyon) | région or `nation:fr` |
| EPT (Grand Paris) | 11 | Métropole du Grand Paris |
| communes | 34,875 (incl. Paris) + 85 in the COM | CTCD / `territory:` row; `member_of` EPCI (+ EPT) |
| communes déléguées / associées, arrondissements municipaux | 2,105 / 471 / 45 | commune |

Départements as territorial units are not separate rows: `code_xwalk.csv` maps each INSEE département code (and the
ISO 3166-2 FR-XX code) to the collectivity that governs it (`same_government`, or `governs_departement` for 2A/2B, 67/68, 75,
972, 973, 976; `governs_part` for Rhône 69, split between its conseil départemental and the Métropole de Lyon).
The Guadeloupe and La Réunion région rows carry no QID (Wikidata's P2585 item is the area item already on `territory:gp/re`,
flag `qid_is_shared_area_item`). `valid_from` for 1,508 communes from the INSEE movement file. Not covered: provinces of
New Caledonia and the Wallis-et-Futuna circonscriptions/chefferies (not in the COG as communes), syndicats (SIVU, SIVOM,
syndicats mixtes), Île des Faisans (condominium, no own government), SIREN for EPT/EPCI beyond the INSEE code
(they are the SIREN), commune SIREN missing where IGN has none. `gaps.csv`: 10 communes déléguées/associées absent from
the ADMIN EXPRESS layer.

## Tribal GEOIDs vs the Geography bot's areas
`scripts/check_aiannh_join.py` reads `data-v3/geo/aiannh_2024.csv`, `anrc_2024.csv` and `aitsn_2024.csv` from data/geo
@ ed866a4 (read-only, via `git show`) and writes `aiannh_join_check.csv`: every tribe GEOID in `tribes.csv` and the
crosswalk (376 entity-GEOID pairs, 304 tribes, 374 distinct GEOIDs) joins to a Geo feature; none fail.

## Rerun
```
cd data-v3/institutions/governments
pip install openpyxl                         # only non-stdlib dependency
python3 scripts/fetch_sources.py             # downloads into cache/ (gitignored); skips cached files
python3 scripts/fetch_sources.py --refresh   # re-download everything (new retrieved_at)
python3 scripts/build_all.py                 # rewrites all CSVs + summary.json (first run also fetches Wikidata/Commons/enwiki metadata into cache/)
```
The build is deterministic: with the same `cache/` it reproduces byte-identical files. `fetch_sources.py` always
picks the newest BIA list notice from the Federal Register search, so a refresh after a new notice picks it up.
`cache/manifest.json` records URL, Last-Modified and retrieval time per file. Raw downloads are never committed.

Scripts: `common.py` (download/cache, readers, column lists), `build_states.py`, `build_cog.py`,
`build_federal_agencies.py`, `build_tribes.py`, `build_changes.py`, `wikidata.py` (QIDs, Commons/enwiki metadata), `build_images.py`, `build_foreign.py`, `foreign_local.py`, `build_foreign_gb.py`, `build_foreign_de.py`, `build_foreign_fr.py`, `build_all.py`.
