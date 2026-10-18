# data-v3/institutions/companies: brands and their locations (schema)

Branch `data/companies`. Built by `scripts/build_locations.py`. UTF-8 CSV, header row, read by header name; a file above ~5 MB is committed as `.csv.gz`.
Nothing is estimated or invented: a value no source gives stays empty and the row is flagged.

**Scope (user directive, Oct 18, 2026):** public-facing brands, establishments and organizations as people know them, keyed by Wikidata.
No SEC / GLEIF / LEI data and no operator or corporate-parent fields; the earlier SEC/GLEIF pull was removed in 1d99a24.

## IDs (final)
Bare `scheme:id`, no extra prefix: brands and organizations are `wikidata:Q<n>` (e.g. `wikidata:Q38076` McDonald's).
An id is never reused; if an item is merged on Wikidata the old id stays resolvable as an alias.
Store / property ids are the brand's own number or code (`store_id`), unique within a brand file.

## brands.csv: one row per brand or parent organization
| column | meaning |
|---|---|
| `entity_id` | `wikidata:Q…` |
| `name` | Wikidata English label |
| `kind` | `brand` (has locations here) / `organization` (only appears as a parent) |
| `instance_of` | Wikidata P31 labels, `;`-list |
| `parent_brand_id`, `parent_brand_name` | Wikidata **P749 (parent organization)** of the item, `;`-list when Wikidata lists several (e.g. Sheraton: Starwood; Marriott International). P127 (owned by / shareholders) is not used. Empty = Wikidata states none |
| `website` | P856 |
| `location_files`, `location_count` | where this QID is used as `brand_qid` / `sub_brand_qid` |
| `source`, `source_url`, `source_date` | `source` = `source_id` in sources.csv; `source_url` = the Wikidata item page |

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
- **marriott.csv**: the v5 property list (Oct 4, 2026; global) joined to All The Places `marriott_hotels` + `ritz_carlton` (CC0) on the MARSHA code.
  ATP fills missing coordinates (`coordinates_from_atp`), missing street addresses (`address_from_atp`), zip, phone and country code; v5 values are never overwritten.
  `brand_qid`: exact Wikidata name match among items whose P749/P127 is Marriott International or Starwood (`brand_qid_from_wikidata_name_match`),
  else the matched ATP item's `brand:wikidata`, else a v5-brand → QID map learned from ≥ 5 MARSHA-matched rows with ≥ 90 % agreement (`brand_qid_from_brand_name`).
  **Provenance caveat:** v5 addresses were partly filled from OpenStreetMap/Photon (ODbL) and the ArcGIS World Geocoder (Esri terms restrict storing results); v5 does not record which rows, see `sources.csv` licence text.

## Flags
`missing_coordinates`, `coordinates_from_atp`, `address_from_atp`, `v5_vs_atp_coordinates_<d>km` (> 1 km apart; v5 kept), `no_marsha_code`, `duplicate_marsha_in_v5`,
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
