# data-v3/institutions/companies: brands and their locations (schema)

Branch `data/companies`. Built by `scripts/build_locations.py`. UTF-8 CSV, header row, read by header name; a file above ~5 MB is committed as `.csv.gz`.
Nothing is estimated or invented: a value no source gives stays empty and the row is flagged.

**Scope (user directive, Oct 18, 2026):** public-facing brands, establishments and organizations as people know them, keyed by Wikidata.
No SEC / GLEIF / LEI data and no operator or corporate-parent fields; the earlier SEC/GLEIF pull was removed in 1d99a24.

## IDs (final)
Bare `scheme:id`, no extra prefix: brands and organizations are `wikidata:Q<n>` (e.g. `wikidata:Q38076` McDonald's).
An id is never reused; if an item is merged on Wikidata the old id stays resolvable as an alias.
Store / property ids are the brand's own number or code (`store_id`), unique within a brand file (Starbucks: `<namespace>-<ref>`, see below).

## Files
| file | rows (this build) | loads into |
|---|---|---|
| `brands.csv` | 213 (179 brand, 34 company) | `entity` |
| `brand_relationships.csv` | 136 | `entity_relation` |
| `company_locations.csv.gz` | 212,439 (110,000 with a v2-2024 county geoid; 102,410 outside the US) | `entity_location` |
| `retracted_locations.csv` | 0 (header only) | `retraction` (target `entity_location`) |
| `locations/<brand>.csv` | ahold_delhaize 2,068; albertsons 2,230; aldi 2,750; bashas 98; best_buy 1,204; bjs 261; brookshires 107; bucees 50; choice 5,612; circle_k 8,196; costco 660; cvs 9,001; fareway 143; festival_foods 42; food_city 154; giant_eagle 231; grocery_outlet 568; heb 346; hilton 6,929; home_depot 2,212; hy_vee 272; ihg 6,828; ingles 188; kroger 2,374; lidl 203; lowes 1,763; lunds_byerlys 28; market_basket 92; marriott 10,056; mcdonalds 36,378 (`.csv.gz`); meijer 205; piggly_wiggly 486; publix 1,451; raleys 98; sams_club 602; save_a_lot 604; schnucks 112; seven_eleven 54,167 (`.csv.gz`); shoprite 316; smart_and_final 253; spartannash 97; sprouts 519; starbucks 35,075 (`.csv.gz`); target 2,026; tops 146; trader_joes 666; walgreens 7,991; walmart 4,904; wawa 1,320; wegmans 114; whole_foods 535; winn_dixie 254 | source tables for company_locations (full store detail) |
| `locations/marriott_dropped.csv` | 361 | not loaded: Marriott rows that could not be kept, with reason |
| `brand_cleanliness.csv` | 172 | not loaded: brands with locations ranked by cleanliness (`scripts/rank_brands.py`; measurements only) |
| `sources.csv` | 136 | `source` |

## brands.csv: one row per brand or parent organization
| column | meaning |
|---|---|
| `entity_id` | `wikidata:Q…` |
| `name` | Wikidata English label |
| `kind` | `brand` (has locations here, or a Wikidata chain/brand item) / `company` (a parent whose P31 says company, business, enterprise, airline, plc …). `organization` is also accepted by the loader. Empty + `kind_review` flag when P31 gives no evidence |
| `brand_name` | Wikidata label, for `kind=brand` |
| `instance_of` | Wikidata P31 labels, `;`-list |
| `parent_brand_id`, `parent_brand_name` | **current** Wikidata P749 (parent organization) parents: statements without a P582 end date, `;`-list (e.g. Sheraton: Starwood; Marriott International). Full history is in brand_relationships.csv. P127 is not used. Empty = Wikidata states none |
| `website` | P856 |
| `location_files`, `location_count` | where this QID is used as `brand_qid` / `sub_brand_qid` |
| `flags` | `kind_review` |
| `source_id`, `source_url`, `retrieved_at` | sources.csv id; the Wikidata item page; retrieval date |
| `logo_file` | Wikimedia Commons file name from Wikidata P154 (logo image). One value is chosen: the preferred-rank statement, else the only statement without an end date (P582); otherwise blank with `logo_multiple_p154_no_rank_or_dates_review`. Filled **only** when Commons gives a free licence (PD, CC0, CC-BY, CC-BY-SA); otherwise blank, and the app falls back to a building icon |
| `logo_license` | what Commons says: `LicenseShortName` (PD/CC basis category), plus `restrictions: …` (e.g. `trademarked`). Most are `Public domain (PD textlogo), restrictions: trademarked`: free of copyright, still a trademark |
| `logo_attribution` | Commons `Artist` field (HTML stripped), else `Credit` |
| `logo_source_url` | the Commons file description page |
| `logo_flags` | `logo_no_p154`, `logo_multiple_p154_no_rank_or_dates_review`, `logo_not_free_or_unknown_licence:<what Commons says>`. Source: `wikidata-commons-logos-<date>` in sources.csv (raw: `raw/logos.json`, `scripts/fetch_logos.py`) |

Scope: every brand used by a location row, plus every ancestor reachable through P749 statements (current or historical), so all relationship endpoints resolve.

## brand_relationships.csv: one row per Wikidata P749 statement
| column | meaning |
|---|---|
| `parent_id`, `child_id` | `wikidata:Q…`, both rows in brands.csv |
| `relation` | `parent_org` (P749) |
| `valid_from`, `valid_to` | P580 start time / P582 end time qualifiers (date part). Empty = Wikidata gives none. No end date = current |
| `current` | `yes` when `valid_to` is empty |
| `wikidata_rank` | `preferred` / `normal` (deprecated statements are skipped) |
| `flags` | `multiple_current_parents_no_dates_review`: the child has more than one current parent and this statement has no dates. Set for Sheraton (Q634831) and St. Regis (Q30715430) → Starwood (Q552363) and Marriott International (Q1141173): Wikidata has no P580/P582 on either statement (checked Oct 18, 2026). Starwood itself → Marriott International from 2016-09-23 |
| `source_id`, `source_url`, `retrieved_at` | Wikidata; `source_url` = the child's P749 section |

## company_locations.csv.gz: one row per establishment (loader file)
| column | meaning |
|---|---|
| `location_id` | `<file stem>:<store_id>` (`walgreens:15196`, `marriott:NYCMQ`, `starbucks:us-1040242`) = `entity_location.location_key`; rows without a store_id are excluded |
| `entity_id` | `brand_qid` of the location row (`wikidata:Q…`) |
| `sub_entity_id` | `sub_brand_qid` when given (Duane Reade, CVS Pharmacy y más) |
| `role` | `establishment_at` (no `hq_in` rows yet: no HQ addresses in scope) |
| `name`, `address` | store name; published business address `street, city, state, zip` |
| `geoid`, `boundary_set` | county GEOID from point-in-polygon on Census 2024 counties, set only when the GEOID is in the agreed `v2-2024` county set (`data-v3/geo/counties.csv`); `boundary_set = v2-2024` then. PR/VI points keep lat/lon with geoid empty and flag `county_not_in_v2-2024:<geoid>`. Non-US rows (Starbucks outside the US) have `geoid` and `boundary_set` empty |
| `lat`, `lon` | WGS84 point (every row has one; rows with neither a point nor a geoid are excluded: 47 Starbucks rows in BR/AU) |
| `source_id`, `retrieved_at` | source of the location's coordinates (ATP id when ATP supplied them, `marriott-pacsys-*` when Marriott's own feed did) and its date |
| extras | `brand_name`, `geoid_method` (`point_in_polygon_cb2024` / `nearest_county_within_2km`), `flags` (copied from the location row), `country_code` (ISO 3166-1 alpha-2 from the location row) |

## retracted_locations.csv
`location_id, retracted_at, reason, source_id`. Only known permanent closures; none are known in this build (the inputs carry temporary statuses only, kept as `status_*` flags), so the file is the header.

## locations/<brand>.csv: one row per store / property
| column | meaning |
|---|---|
| `store_id` | brand store number (Walgreens, CVS, McDonald's) or Marriott MARSHA code |
| `brand`, `brand_qid` | brand as shown to the public and its `wikidata:Q…` (Marriott: the hotel brand, e.g. Courtyard) |
| `parent_brand_qid` | P749 of `brand_qid` (from brands.csv) |
| `address`, `city`, `state`, `zip` | as the source gives them (Marriott non-US rows keep their own region form) |
| `county` | Census 2024 county name from point-in-polygon on lat/lon (`county_geoid` = its GEOID) |
| `lat`, `lon` | WGS84 |
| `phone` | US numbers normalized to `(AAA) BBB-CCCC`; others as given |
| `sub_brand` | store variant (`Duane Reade`, `CVS Pharmacy at Target`, `Four Points Express`, an independent pharmacy name, …) |
| `flags` | `;`-list of review items (below) |
| `source` | `;`-list of `source_id`s (sources.csv) used for the row |
| `source_url` | the store's / property's own page where known |
| `source_date` | newest retrieval date among the row's location sources |
| extras | `name` (store/hotel name), `sub_brand_qid`, `county_geoid`, `country_code` (ISO 3166-1), `status`, `store_type` |

## sources.csv
`source_id, source, source_url, license, retrieved_at, commit, sha256` (sha256 of the raw file used). Same layout as `data-v3/inst` officeholders.

## Per-brand notes
- **walgreens.csv**: walgreens.com locator API (Oct 12, 2026), US + PR + VI. Phones reformatted from `(787) 8828044` to `(787) 882-8044`.
  Independent pharmacies under the Walgreens name are kept, flagged, and no operator is assumed:
  `independent_walgreens_affiliate_operator_unknown` (the 3 "…, a Walgreens Rx" stores plus "Jim, Myers, A Walgreens Pharmacy") and `powered_by_walgreens_affiliate_operator_unknown` (9 "…, Powered by Walgreens").
  Duane Reade rows keep `brand=Walgreens` and `sub_brand_qid=wikidata:Q5310380`.
- **cvs.csv**: cvs.com locator city pages (Oct 17, 2026), US. `CVS Pharmacy y más` rows carry `sub_brand_qid=wikidata:Q136695801`.
- **mcdonalds.csv.gz**: global, 36,378 rows in 68 countries. All The Places (CC0), run 2026-10-10.
  - **US rows** (13,486): from the `mcdonalds` spider, with `store_id` = the bare ATP ref, unchanged since 5faf8aa.
  - **Other countries:** from the rest of `mcdonalds` plus every `mcdonalds_<cc>` spider, with `store_id` = `<country>-<ref>`.
  - **Older runs:** `mcdonalds_cy`, `_it` and `_ph` were empty in the latest run, so they come from run 2026-10-03; `_rs`, `_si` and `_za` from run 2026-07-25 (`atp_older_run_<date>`).
  - **Excluded:** McCafé points (Q3114287; 6,155 coffee bars inside restaurants) and 87 points with no ref (all of Morocco, plus 1 in Malaysia). No spider returned anything for the other countries McDonald's operates in.
  - Israel's spider tags McDonald's Israel (Q12061542), which is kept as `sub_brand_qid`. 426 rows have no coordinates.
- **marriott.csv**: global (user, 2026-10-18): 10,056 rows in about 160 countries (US 6,270). Rows with no country (211) are dropped. The v5 property list (Oct 4, 2026) supplies the MARSHA code, hotel name, brand name and marriott.com URL; it is joined on the MARSHA code to
  1. All The Places `marriott_hotels` + `ritz_carlton` (CC0): wins for coordinates and the address block (`coordinates_from_atp`, `address_from_atp`; `v5_vs_atp_coordinates_<d>km` when > 1 km apart);
  2. Marriott's own property feeds `pacsys.marriott.com/data/marriott_properties_<BRAND>_en-US.json` (first-party, the JSON marriott.com's brand pages load; ATP reads only some brand codes) for rows ATP lacks: `coordinates_from_marriott_feed`, `address_from_marriott_feed`. Fetched with `scripts/fetch_marriott_pacsys.py`.
  **v5-only values (user decision 2026-10-18):** a row with no ATP or Marriott-feed point keeps its v5 coordinates (and v5 address), flagged `v5_user_approved`, with source `marriott-v5-user-approved-2026-10-18`, unless it duplicates another row (same MARSHA code, or the same normalized name and address within 100 m), in which case it is dropped as `duplicate_of:<store_id>`. 33 rows are kept this way and none were duplicates. The other 367 of the original 400 v5-only rows now take their point and address from Marriott's feed.
  `locations/marriott_dropped.csv` (renamed from `marriott_dropped_us.csv`) lists every row not kept, with its reason: 211 `no_country`, 100 `no_coordinates_no_address`, 24 `non_us_v5_only_coordinates`, 14 `no_store_id`, 12 `no_brand_qid` (MGM Collection).
  **Non-US licence rule:** the user's approval of v5-only values covers the US/territory hotels only. A non-US row whose only point is v5's is dropped (`non_us_v5_only_coordinates`). All 3,762 non-US rows kept take their point and address from ATP (3,095) or Marriott's feed (667).
  **brand_qid** order: exact normalized-name match to a Wikidata item parented/owned by Marriott or Starwood (`brand_qid_from_wikidata_name_match`),
  else the matched ATP item's `brand:wikidata`, else a v5-brand → QID map learned from ≥ 5 MARSHA-matched rows with ≥ 90 % agreement (`brand_qid_from_brand_name`).
  **Provenance caveat:** v5 addresses were partly filled from OpenStreetMap/Photon (ODbL) and the ArcGIS World Geocoder (Esri terms restrict storing results); v5 does not record which rows, so v5 addresses and points are used only where ATP and Marriott's feed have none, and those 33 rows carry `v5_user_approved`. Full provenance of v5: `PROVENANCE-marriott-v5.md`.
- **wawa.csv**: the user's own Wawa list (Apple Numbers file uploaded 2026-10-18, copied untouched to `raw/inputs/wawa-stores-user-2026-10-18.numbers`; its About sheet says it was collected 2026-09-16 from order.wawa.com's store API). The user checked it, so values are copied as-is: no validation, phone reformatting or geocoding. `source` is `wawa-user-list-2026-10-18` alone, the same id `company_locations` carries.
  Column map: Store ID → `store_id`, Name → `name`, Street → `address`, City, State, ZIP → `zip`, Phone, Latitude/Longitude → `lat`/`lon`, URL → `source_url`. Timezone and Schedule Type have no schema column and are not carried.
  Added: `brand_qid` = wikidata:Q5936320 (Wawa; no P749 parent on Wikidata, so `parent_brand_qid` is blank), `location_id` = `wawa:<store id>`, county by point-in-polygon on cb_2024 (1,318 of 1,320). Stores 9598 and 9599 (260 W. Baltimore Pike, Media PA; 36.000282, -45.406712, in the Atlantic) get the flag `no_county`; their values are unchanged.
- **starbucks.csv.gz**: all countries, from every All The Places `starbucks_*` spider with features in run 2026-10-10 (CC0): ae, ar_cl, au, br, ca, cn, eu, hk_mo, jp, mena, pe, sg, th, tw, us, za (`starbucks_in` returned 0 features). `brand_qid` = wikidata:Q37158; Wikidata has no P749 for it, so `parent_brand_qid` is blank.
  **store_id** = `<namespace>-<ATP ref>`: ATP refs are numbered per licensee system, so one number can be two different stores in two spiders (e.g. starbucks_th 14091 and starbucks_us 14091). The namespace is the country domain for refs of the form `locations.starbucks.<tld>/#<n>` (starbucks_ae and starbucks_mena publish the same stores that way, so they dedupe to one id), else the spider suffix without `_` (`us`, `cn`, `eu`, `arcl`, `hkmo`, ...). Duplicate store_ids keep the first spider in name order: 255 dropped (all ae/mena, same point and address).
  Not loaded: `starbucks_reserve` (6 Roasteries, brand Starbucks Reserve Q71150001, no ref).
  `name` = ATP `name` (or `name:en`); when it is just "Starbucks" and ATP gives a `branch`, `Starbucks <branch>`. 178 hkmo rows have no name in ATP. `address` = `addr:street_address`, else `addr:full` (flag `address_is_addr_full`). US phones are normalized like the other files; others are as given.
  County geoid only for `country_code = US` (16,708 of 16,708); 34 PR rows from starbucks_eu keep it empty. 47 rows (BR 45, AU 2) have no coordinates in ATP (`missing_coordinates`) and are not in company_locations.

- **Other All The Places chains** (`CHAINS` in build_locations.py; one file each, all countries the brand's spiders cover). Every file has the full column set: `name`, `country_code`, `state`, `county` + `county_geoid` (US rows only), `city`, `address`, `lat`, `lon`.
  `store_id` = `<namespace>-<ATP ref>` (namespace = the spider's country, e.g. `us-1234`, `ca-3019`; a URL ref keeps only its trailing store number). The latest ATP run (2026-10-10) is read first. When a spider's latest output is empty or clearly partial, an older complete ATP run fills only the store ids the latest run lacks. Those rows are flagged `atp_older_run_<date>` and cite that run's own `sources.csv` entry (`scripts/fetch_atp_older.py`). `store_type` = the ATP `name` (store format).
  - **walmart.csv**: wikidata:Q483551 (Wikidata has no P749 parent).
    - Spiders: `walmart_us` latest (1,484 features, partial) + `walmart_ca` latest (385) + `walmart_us` run 2026-01-24 (4,476, the last complete run) for the 3,037 store ids missing from the latest run.
    - Rows named "Walmart Neighborhood Market" carry `sub_brand_qid` wikidata:Q7963529.
    - Excluded: 2 "Walmart Pharmacy" points (not stores); Sam's Club (`sams_club`, `sams_club_mx`; brand Q1972120, not tagged Walmart); Lider (`lider_cl`) and Asda (`asda_gb`): other brands.

  - **home_depot.csv**: wikidata:Q864407 The Home Depot (no P749 parent). Spiders `home_depot` (US; ATP reads storelocators.com's list, and the ref is an address slug, not a store number) + `home_depot_ca` (CA). 4 US points have no coordinates in ATP (`missing_coordinates`).

  - **lowes.csv**: wikidata:Q1373493 Lowe's (no P749 parent). `lowes_us` returned 0 features in the latest run (and only 0–38 in every run since 2026-07-18), so the file uses run 2026-07-11 (1,763 features, the last complete run); every row is flagged `atp_older_run_2026-07-11`. Not included: Lowes Foods (`lowes_foods`, Q6693991) and Lowe's Market (`lowes_market_us`, Q6693107), which are unrelated grocery chains.

  - **best_buy.csv**: wikidata:Q533415 (no P749 parent). Spiders `best_buy` (US + PR) and `best_buy_ca`. Excluded: 4 "Best Buy Distribution Center" points (not stores) and 165 "Best Buy Express" points in Canada (brand Q3212934, formerly The Source, tagged as a separate brand). Best Buy Warehouse and Outlet stores are kept; see `store_type`.

  - **target.csv**: wikidata:Q1046951 Target Corporation (no P749 parent). Spider `target_us`. Excluded: `target_au` (Target Australia, Q7685854, a different company owned by Wesfarmers).

  - **seven_eleven.csv(.gz)**: wikidata:Q259340 7-Eleven. Spiders `seven_eleven_ca_us` (US + CA), `_au`, `_dk`, `_jp`, `_mx`, `_ph`, `_se`, `_th`, `_tw`. The CA/US ref suffix `_SHOP` is stripped, leaving the store number. Excluded from `seven_eleven_ca_us`: 6,019 fuel-station points with no brand tag (the forecourt of a store already listed), 2,205 Speedway (Q7575683) and 137 Stripes (Q7624135) stores, which are separate brands. No ATP spider covers 7-Eleven in other countries (e.g. South Korea, Malaysia, Hong Kong, China, Singapore, Norway).

  - **circle_k.csv**: wikidata:Q3268010 Circle K. Spiders `circle_k` (US + CA), `_dk`, `_ireland` (IE + GB), `_no`, `_pl`, `_se`, `_vn`. URL refs keep their last path segment (station slug). Excluded: 607 Couche-Tard-branded stores in Quebec (brand Q2836957, Alimentation Couche-Tard). `circle_k_vn` refs are list positions (`vn-0`, `vn-1`, ...), so those ids may not be stable between runs.

  - **bucees.csv**: wikidata:Q4982335 Buc-ee's. `bucees_us` returned 0 features in the latest run, so the file uses run 2026-10-03 (50 features); every row is flagged `atp_older_run_2026-10-03`.

  - **hilton.csv**: Hilton hotels worldwide. `brand_qid` = the brand ATP tags on each hotel (Hampton, Hilton Garden Inn, Home2, DoubleTree, Homewood, Tru, Embassy Suites, Curio, Tapestry, Conrad, Waldorf Astoria, Canopy, LXR, Motto, Tempo, Signia, Graduate, Hilton Grand Vacations, Hilton), parent from Wikidata P749. `store_id` = Hilton's property code (ATP ref). `hilton` returned 0 features in every run since 2026-09-05, so the file uses run 2026-08-29 (7,722 features; `atp_older_run_2026-08-29`). Excluded, because there is no brand QID to key on: 522 Small Luxury Hotels of the World (a partner network, not a Hilton brand), 241 Spark by Hilton, 5 AutoCamp, 1 NoMad and 24 untagged.

  - **ihg.csv**: IHG hotels worldwide, from `ihg_hotels` (latest run). `brand_qid` = the brand ATP tags (Holiday Inn Express, Holiday Inn, Holiday Inn Resort, Holiday Inn Club Vacations, Candlewood, Crowne Plaza, Staybridge, InterContinental, Hotel Indigo, voco, Garner, avid, Kimpton, Army Hotels, Vignette Collection, EVEN, Regent), parent from P749. `store_id` = IHG's 5-character hotel code taken from the ref URL (`.../<code>/hoteldetail`), upper-cased. Excluded: 154 hotels with no brand tag. 8 have no coordinates.

  - **choice.csv**: Choice Hotels properties worldwide. `brand_qid` = the brand ATP tags (Quality Inn, Comfort Inn, Comfort Suites, Econo Lodge, Sleep Inn, Rodeway Inn, Ascend, Clarion, MainStay, Suburban, Cambria, WoodSpring, plus the Radisson Americas brands Choice franchises: Radisson, Radisson Blu, Radisson RED, Park Inn, Park Plaza), parent from P749 (the Radisson brands' Wikidata parent is Radisson Hotel Group, not Choice). `store_id` = Choice's property code. `choice_hotels` returned 0 features in the latest run, so the file uses run 2026-09-19 (6,209 features; `atp_older_run_2026-09-19`). Excluded, because there is no brand QID: 366 Country Inn & Suites ("Country"), 58 RocketFuel, 44 SSAW, 37 "Home", 32 Everhome, 20 Penn, 19 Westgate, 13 Radisson Individuals, 7 El Cid, 1 Stopover.


### US grocery chains (ATP, CC0; added 2026-10-18)
One file per parent group or standalone chain: kroger, albertsons, ahold_delhaize, publix, heb, aldi, lidl, trader_joes, whole_foods, costco, sams_club, bjs, meijer, hy_vee, wegmans, shoprite, winn_dixie, save_a_lot, sprouts, giant_eagle, ingles, food_city, schnucks, raleys, smart_and_final, grocery_outlet, fareway, brookshires, tops, market_basket, piggly_wiggly, festival_foods, lunds_byerlys, bashas, spartannash.
- US rows only (`addr:country` US/PR/territories). `brand` is the banner name ATP gives; `brand_qid` is the feature's `brand:wikidata`; `parent_brand_qid` is that banner's Wikidata P749 (blank when Wikidata has none, e.g. Kroger banners Pick 'n Save, Mariano's, JayC; Albertsons banners Tom Thumb, Randalls, Pavilions, Star Market, Kings, Haggen, Carrs, Andronico's).
- Store points only: features typed `shop=supermarket|wholesale|convenience|department_store`. Pharmacies, fuel stations, liquor stores, clinics and offices inside the same spiders are left out (counted as `excluded_type:*` in summary.json).
- Market Basket's spider tags its 5 MB Spirits liquor stores as supermarkets; they are dropped by name (`^MB Spirits`). Its spider gives no street address, and the store named "Market Basket #96 (Coming Soon!)" is kept as ATP lists it. Sprouts and Tops have no city/zip field in ATP, Hy-Vee gives only `addr:full`, and 1,341 Food Lion rows have no city; those fields are left blank, not parsed or guessed.
- Features without `brand:wikidata` are skipped and listed: Metro Market (Kroger, 23), Nob Hill Foods (Raley's, 17).
- ATP's Gerbes features carry Dillons' QID and Foods Co features carry Food 4 Less's QID; ATP's banner name is kept in `brand`.
- store_id: the ATP ref; files mixing spiders namespace it (`safeway-`, `foodlion-`, `giantco-`, `giantfood-`, `martins-`, `hannaford-`, `stopshop-`, `bashas-`, `foodcityaz-`, `familyfare-`, `dw-`). Sprouts uses the store URL slug.
- Stop & Shop and BJ's come from the 2026-10-03 run (latest run empty) and carry `atp_older_run_2026-10-03`.
- Hy-Vee's spider has no geometry in any run, and a few Grocery Outlet, Meijer and Brookshire's features also lack it. Those rows are geocoded from their ATP address with the U.S. Census Bureau geocoder (public domain; answers cached in raw/census_geocode.json by scripts/fetch_census_geocode.py) and flagged `coordinates_from_census_geocoder`. Addresses the geocoder can't match stay without coordinates.
- No ATP data, so not built: Harris Teeter, WinCo, Weis, Harps, Price Chopper/Market 32 (NY; `price_chopper_kc_us` is a different Kansas City chain), Hornbacher's, Harveys, Central Market (not in the H-E-B spider), Stater Bros (0 features in every recent run).
## Flags
`missing_coordinates`, `coordinates_from_atp`, `coordinates_from_marriott_feed`, `address_from_marriott_feed`, `v5_user_approved` (v5 coordinates/address kept by user decision 2026-10-18), `county_not_in_v2-2024:<geoid>`, `address_from_atp`, `v5_vs_atp_coordinates_<d>km` (> 1 km apart; ATP kept), `no_marsha_code`, `duplicate_marsha_in_v5`,
`brand_qid_from_wikidata_name_match`, `brand_qid_from_brand_name`, `atp_brand_qid_differs:<Q>`, `county_nearest_within_2km` (point just outside the 1:500k shoreline, e.g. Navy Pier),
`point_outside_us_counties`, `point_state_<XX>_vs_address_<YY>`, `phone_unparsed`, `status_<status>`, `independent_walgreens_affiliate_operator_unknown`, `powered_by_walgreens_affiliate_operator_unknown`, `address_is_addr_full`, `duplicate_in_<spider>_<d>km`, `no_county` (Wawa), `atp_older_run_<date>`, `coordinates_from_census_geocoder`.

## Rebuild
```
cd data-v3/institutions/companies/scripts
python3 fetch_atp.py mcdonalds marriott_hotels ritz_carlton starbucks_ae starbucks_ar_cl starbucks_au starbucks_br starbucks_ca starbucks_cn starbucks_eu starbucks_hk_mo starbucks_in starbucks_jp starbucks_mena starbucks_pe starbucks_reserve starbucks_sg starbucks_th starbucks_tw starbucks_us starbucks_za
python3 fetch_marriott_pacsys.py AK WI TX JW WH LC MV SV WV PR XR RZ BR MD EB DE EL OX GE ER BG FI CY RI MC TS SH FP SI AR DS AL XE
python3 fetch_wikidata_brands.py <brand QIDs…>      # list in summary.json / brands.csv
python3 rank_brands.py                              # after build_locations.py -> brand_cleanliness.csv
python3 fetch_atp_older.py 2026-01-24-13-32-35 walmart_us   # older complete runs where the latest is partial
python3 fetch_logos.py                              # P154 + Commons licences for the entities in brands.csv
# copy inputs to raw/inputs/: all_stores.csv, marriott-properties-v5.csv, cb_2024_us_county_500k.*
python3 build_locations.py
```
`raw/` is gitignored. `CONTACT_EMAIL` / `HTTP_USER_AGENT` override the crawler identity.
