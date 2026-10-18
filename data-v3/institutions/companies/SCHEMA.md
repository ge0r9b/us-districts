# data-v3/institutions/companies: brands and their locations (schema)

Branch `data/companies`. Built by `scripts/build_locations.py`. UTF-8 CSV, header row, read by header name; a file above ~5 MB is committed as `.csv.gz`.
Nothing is estimated or invented: a value no source gives stays empty and the row is flagged.

**Scope (user directive, Oct 18, 2026):** public-facing brands, establishments and organizations as people know them, keyed by Wikidata.
No SEC / GLEIF / LEI data and no operator or corporate-parent fields; the earlier SEC/GLEIF pull was removed in 1d99a24.

## IDs (final)
Bare `scheme:id`, no extra prefix: brands and organizations are `wikidata:Q<n>` (e.g. `wikidata:Q38076` McDonald's).
An id is never reused; if an item is merged on Wikidata the old id stays resolvable as an alias.
Store / property ids are the brand's own number or code (`store_id`), unique within a brand file.

## Files
| file | rows (this build) | loads into |
|---|---|---|
| `brands.csv` | 44 (33 brand, 11 company) | `entity` |
| `brand_relationships.csv` | 34 | `entity_relation` |
| `company_locations.csv.gz` | 36,675 | `entity_location` |
| `retracted_locations.csv` | 0 (header only) | `retraction` (target `entity_location`) |
| `locations/<brand>.csv` | walgreens 7,991; cvs 9,001; mcdonalds 13,486; marriott 6,197 | source tables for company_locations (full store detail) |
| `locations/marriott_dropped_us.csv` | 132 | not loaded: US/PR/VI Marriott rows that could not be kept, with reason |
| `sources.csv` | 8 | `source` |

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
| `location_id` | `<file stem>:<store_id>` (`walgreens:15196`, `marriott:NYCMQ`) = `entity_location.location_key`; rows without a store_id are excluded |
| `entity_id` | `brand_qid` of the location row (`wikidata:Q…`) |
| `sub_entity_id` | `sub_brand_qid` when given (Duane Reade, CVS Pharmacy y más) |
| `role` | `establishment_at` (no `hq_in` rows yet: no HQ addresses in scope) |
| `name`, `address` | store name; published business address `street, city, state, zip` |
| `geoid`, `boundary_set` | county GEOID from point-in-polygon on Census 2024 counties, set only when the GEOID is in the agreed `v2-2024` county set (`data-v3/geo/counties.csv`); `boundary_set = v2-2024` then. PR/VI points keep lat/lon with geoid empty and flag `county_not_in_v2-2024:<geoid>` |
| `lat`, `lon` | WGS84 point (every row has one) |
| `source_id`, `retrieved_at` | source of the location's coordinates (ATP id when ATP supplied them) and its date |
| extras | `brand_name`, `geoid_method` (`point_in_polygon_cb2024` / `nearest_county_within_2km`), `flags` (copied from the location row) |

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
- **mcdonalds.csv**: All The Places `mcdonalds` spider, run 2026-10-10 (CC0), `addr:country = US` only (no PR rows in that spider).
- **marriott.csv**: US + PR/VI only (6,197 of 10,417 v5 rows; 3,781 non-US and 307 no-country rows dropped). The v5 property list (Oct 4, 2026) is joined to All The Places `marriott_hotels` + `ritz_carlton` (CC0) on the MARSHA code.
  **Licence rule:** wherever ATP has a value it wins over v5 for coordinates and the address block (`coordinates_from_atp`, `address_from_atp`; `v5_vs_atp_coordinates_<d>km` when they were > 1 km apart).
  Values that only v5 supplies carry `v5_unknown_license:coordinates` / `v5_unknown_license:address` (400 rows: 400 coordinates, 396 addresses).
  US rows that could not be kept are listed in `locations/marriott_dropped_us.csv`: 119 with neither coordinates nor a street address (no ATP match, so the Census geocoder had nothing to geocode), 12 MGM Collection rows (no Wikidata item for that brand), 1 without a MARSHA code.
  `brand_qid`: exact Wikidata name match among items whose P749/P127 is Marriott International or Starwood (`brand_qid_from_wikidata_name_match`),
  else the matched ATP item's `brand:wikidata`, else a v5-brand → QID map learned from ≥ 5 MARSHA-matched rows with ≥ 90 % agreement (`brand_qid_from_brand_name`).
  **Provenance caveat:** v5 addresses were partly filled from OpenStreetMap/Photon (ODbL) and the ArcGIS World Geocoder (Esri terms restrict storing results); v5 does not record which rows, hence the `v5_unknown_license` flags.

## Flags
`missing_coordinates`, `coordinates_from_atp`, `v5_unknown_license:coordinates|address`, `county_not_in_v2-2024:<geoid>`, `address_from_atp`, `v5_vs_atp_coordinates_<d>km` (> 1 km apart; ATP kept), `no_marsha_code`, `duplicate_marsha_in_v5`,
`brand_qid_from_wikidata_name_match`, `brand_qid_from_brand_name`, `atp_brand_qid_differs:<Q>`, `county_nearest_within_2km` (point just outside the 1:500k shoreline, e.g. Navy Pier),
`point_outside_us_counties`, `point_state_<XX>_vs_address_<YY>`, `phone_unparsed`, `status_<status>`, `independent_walgreens_affiliate_operator_unknown`, `powered_by_walgreens_affiliate_operator_unknown`.

## Rebuild
```
cd data-v3/institutions/companies/scripts
python3 fetch_atp.py mcdonalds marriott_hotels ritz_carlton
python3 fetch_wikidata_brands.py <brand QIDs…>      # list in summary.json / brands.csv
# copy inputs to raw/inputs/: all_stores.csv, marriott-properties-v5.csv, cb_2024_us_county_500k.*
python3 build_locations.py
```
`raw/` is gitignored. `CONTACT_EMAIL` / `HTTP_USER_AGENT` override the crawler identity.
