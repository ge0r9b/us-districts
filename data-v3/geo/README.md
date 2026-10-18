# data-v3/geo: stable TIGER GEOIDs for the v2 boundary rows

Made by `tools/v3_geoids.py <repo> --gaz <dir> --towns-report IA:<report>` from the Census TIGER 2024 Gazetteer
(public domain) and the v2 data files. Nothing in `v2/data/` is changed; this is a side table for v3 and for audits.

## Files
One CSV per layer, UTF-8, header row, one line per row as the v2 app shows it:

| File | v2 source | GEOID form (TIGER 2024) |
|---|---|---|
| `ushouse.csv` | `v2/data/uscd.js` (+ DC delegate from `dc.js`) | SSDD: state FIPS + 119th Congress district (`00` at-large, `98` DC delegate) |
| `senate.csv` | `v2/data/ussldu.js` (+ DC wards from `dc.js`) | SS + SLDU code (DC wards 11001-11008) |
| `statehouse.csv` | `v2/data/ussldl.js` (+ DC wards) | SS + SLDL code; Nebraska (unicameral) and DC rows carry their SLDU GEOID |
| `schools.csv` | `v2/data/ussch.js` (+ DCPS) | SS + LEA (7 digits); `tiger_set` = unsd / elsd / scsd |
| `counties.csv` | `v2/data/uscounties.js` (+ DC) | SSCCC |
| `towns.csv` | `v2/data/parts/<State>.js` rows built from TIGER county subdivisions (Iowa townships) | SSCCCMMMMM |
| `v2_name_collisions.csv` | `v2/data/ussch.js` | report: rows whose (state, name) is shared, see below |
| `summary.json` | | match counts per layer |

Columns (layer files): `layer, state, row, v2_name, geoid, tiger_name, tiger_set, match`.
- `row` = 0-based index of the row in the v2 file's array, or `dc.js` for rows injected at runtime by `v2/data/dc.js`.
  Rows are identified by (`layer`, `row`). Since 9ff4c00 (`state`, `v2_name`) is also unique in every layer: the 58 same-name school groups (132 rows) were renamed "<name> (<county>)", see `v2_name_collisions.csv`.
- `match`: `code+point` / `name+point` (code or name matched and the TIGER internal point lies inside the v2 polygon,
  buffered 0.002°), `code` / `name` (single candidate, internal point outside the simplified polygon), `point`
  (no name match, exactly one internal point inside), empty = unmatched. Same-named TIGER features are told apart only by the point test.
- towns.csv columns: `layer, state, county, v2_name, geoid, funcstat, match`.

Coverage at commit time: every row matched, no GEOID used twice within a layer (ushouse 436, senate 1,950,
statehouse 4,890, schools 13,305, counties 3,144, towns 1,598).
Re-run after any v2 boundary change; the `row` index shifts when rows are inserted.

## 2020-vintage GEOID tables (`tools/v3_geoids_2020.py`)

`ushouse_2020.csv`, `senate_2020.csv` and `statehouse_2020.csv` pair each v2 row with a district of TIGER 2020 (public domain):
- the 116th Congress districts (`tl_2020_us_cd116`);
- the state legislative districts of TIGER 2020 (the 2018 plans, `tl_2020_SS_sldu` / `_sldl`).

v2 keeps one row per current (2024-plan) district and stores its 2020 figures on that same geometry, so a 2020 GEOID here is the 2020-plan district *of the same code*, with overlap shares. It is not a claim that the boundaries are equal.

Columns: `layer, state, row, v2_name, geoid_2024, geoid_2020, tiger_name_2020, match, v2_in_2020, 2020_in_v2`.
- `row` and `geoid_2024` are as in `ushouse.csv` / `senate.csv` / `statehouse.csv`.
- `v2_in_2020` is the share of the v2 polygon inside the 2020 district; `2020_in_v2` is the reverse.
- `match` values:
  - `code+same`: same code, and each covers ≥ 90 % of the other.
  - `code`: same code, boundary changed.
  - `overlap`: no same-code 2020 district, so the 2020 district overlapping most is given (new or renumbered districts, e.g. MA, MD).
  - `unpaired_2020`: a 2020 district no v2 row points to; `row` is empty.
- Nebraska's state house rows pair with its 2020 SLDU districts (unicameral). The DC delegate and DC wards come from `dc.js` at runtime, so their 2020 units show as unpaired. Territories are left out.
- Counts are in `summary_2020.json`.

## Other side tables
- `v1_towns.csv` (`tools/v1_towns.py`): TIGER 2024 GEOIDs for root `data/<State>.js` towns and places rows; see ALIGNMENT.md item 4.
- `county_funcstat.csv`: TIGER 2024 county FUNCSTAT; see ALIGNMENT.md item 1.
- `town_pairs.csv`: the classes behind `v2/data/town_pairs.js`.
- `town_gaps_2024*.csv`: the town-layer gap audit.
- `zcta2024.csv` (`tools/zcta2024_csv.py`): all 33,791 ZCTAs of the Census 2024 ZCTA Gazetteer, keyed by `zcta5` (the ZCTA GEOID),
  with land/water area (m²) and the internal point as published. `in_v2` and `v2_point_match` check `v2/data/zcta2024.js`:
  all 33,791 v2 keys are in the Gazetteer and every v2 [lat, lon] is the Gazetteer point rounded to 4 decimals.
- `towns_2024.geojson.gz` and `places_2024.geojson.gz` (`tools/v3_geojson_2024.py`, gzipped because they are over 5 MB; **not in git**
  (orchestrator ruling: large GeoJSON is regenerated locally into `../geo-data-raw/v3/`, see below)): every
  Census TIGER 2024 county subdivision (35,482, 10-digit GEOID) and place (32,041, 7-digit GEOID, incorporated places and CDPs)
  of the 50 states and DC, one feature per GEOID (`id` = GEOID). Properties: `geoid`, `state`, `statefp`, `countyfp` and
  `county` (towns), `name`, `namelsad`, `lsad`, `classfp`, `funcstat` (filter A/B/C/G for governmental towns, CLASSFP C* /
  `incorporated` for incorporated places), `aland`, `awater`, and the v2 rows carrying the feature: `v2_parts`
  (`"<county>|<name>"` keys of `v2/data/parts/`) and, for places, `v2_places` (the `v2/data/places/` row name, or null).
  Every one of the 58,127 v2 town and place rows with a GEOID is a feature. Geometry: per state, the whole TIGER coverage is
  simplified with shapely.coverage_simplify at 0.0005° (finer than v2's 0.002°; shared edges stay identical), coordinates
  snapped to 5 decimals with every geometry valid. Rebuild from the TIGER zips with the script for full resolution.

### Regenerating the large GeoJSON (not in git)

From the repo root, with the TIGER 2024 zips (`tl_2024_SS_cousub.zip`, `tl_2024_SS_place.zip` for the 50 states + DC from
https://www2.census.gov/geo/tiger/TIGER2024/, and `tl_2024_us_county.zip`) and the `tools/build_town_files.py` reports:

```
python3 tools/v3_geojson_2024.py . ../geo-data-raw/tiger2024/st ../geo-data-raw/tiger2024/tl_2024_us_county.zip \
    ../geo-data-raw/reports/townfiles --out ../geo-data-raw/v3
```

The build is deterministic (gzip mtime 0; verified by a second run giving identical bytes). Expected sha256, with shapely 2.2.0 /
GEOS 3.14.1 and pyshp 3.1.6 (other GEOS versions may simplify differently):

| file | bytes | sha256 |
|---|---|---|
| `towns_2024.geojson.gz` | 28,734,498 | `dc9082137847a3de24bf7a514041906fe4f9bd5d139bf2c0e7755a1087ba88f8` |
| `towns_2024.geojson` (uncompressed) | 110,043,707 | `da34684534e3e0b68bc9829c6e60dae1e9ce56fd4a236f6dd328c7a6502eab70` |
| `places_2024.geojson.gz` | 15,940,151 | `a03515169c78ffb3dc1a99897274c96ac35a6ec0633573113857d6f7d55a2182` |
| `places_2024.geojson` (uncompressed) | 61,936,814 | `4fc408a76f89fc9d9e5f303e22b0c4c03ec2b611e167ab4c352b6c4a3a4a2d96` |

The two files were committed once (b06c280) and removed in the next commit, so their blobs remain in the `data/geo` history.

## Tribal areas, TIGER 2024 (`tools/v3_aiannh_2024.py`)

Source: Census TIGER/Line 2024 (public domain), https://www2.census.gov/geo/tiger/TIGER2024/ `AIANNH/tl_2024_us_aiannh.zip`,
`ANRC/tl_2024_02_anrc.zip`, `AITSN/tl_2024_us_aitsn.zip`. ANVSAs (Alaska Native village statistical areas) are not a separate
TIGER file: they are the 221 CLASSFP `E1` features of AIANNH. ANRCs (Alaska Native regional corporations) are separate.

| layer | features | CSV in git (id = GEOID) | GeoJSON (not in git) | bytes | sha256 |
|---|---|---|---|---|---|
| AIANNH (643 reservations / trust lands / OTSA / SDTSA / TDSA / state & Hawaiian areas + 221 ANVSA) | 864 | `aiannh_2024.csv` (79,759 B) | `aiannh_2024.geojson` | 2,745,550 | `6e2379258bf6333e42a147ed7de9bbacc200c0bbf06b17a495b1a501472030f7` |
| ANRC | 12 | `anrc_2024.csv` (1,587 B) | `anrc_2024.geojson` | 488,931 | `43e311511688af49da4a45396d658a6bff7b75d2f7e9aa17f6c8bb702d61c99f` |
| AITSN (tribal subdivisions, e.g. Navajo chapters) | 484 | `aitsn_2024.csv` (39,974 B) | `aitsn_2024.geojson` | 1,605,560 | `16354fa8f04803c0a8844bcf4e933af938bf4cabcfe844314a1a260fb7e3854b` |

GEOID: AIANNH = AIANNHCE + `R` (reservation / statistical area) or `T` (off-reservation trust land), so one tribe can have two
features; ANRC = state + ANRCFP; AITSN = AIANNHCE + TRSUBCE. Properties/columns: the TIGER fields (lowercased) plus
`states` and `counties` (TIGER 2024 county GEOIDs the feature overlaps by at least 0.1% of its area or about 1 km²), the
alignment hook to state and county institutions. AIANNH features overlap one another by design (OTSA/SDTSA vs reservations),
so AIANNH and AITSN are simplified per feature (topology-preserving, 0.0005°, as towns_2024) and neighbouring edges are not
guaranteed identical; ANRC is a valid coverage and uses coverage_simplify. Coordinates snapped to 5 decimals, all valid.
Each file is under 5 MB so none is gzipped; they stay out of git anyway (`.gitignore`). Deterministic (two runs, identical sha256):

```
python3 tools/v3_aiannh_2024.py . ../geo-data-raw/tiger2024/aiannh ../geo-data-raw/tiger2024/tl_2024_us_county.zip --out ../geo-data-raw/v3
```

## Canada, Statistics Canada 2021 (`tools/statcan2021_fetch.py`, `tools/canada2021_geojson.py`)

Sources and licences:
- Statistics Canada, 2021 Census cartographic boundary files (CBF: shoreline-clipped), **Statistics Canada Open Licence**
  (https://www.statcan.gc.ca/en/reference/licence). Fetched from StatCan's official ArcGIS REST service
  `geo.statcan.gc.ca/geo_wa/rest/services/2021/Cartographic_boundary_files/MapServer` (layers 0 PR, 4 CD, 9 CSD, 3 FED 2013),
  full resolution, EPSG:3347. The equivalent `l*000b21a_e.zip` downloads on www12.statcan.gc.ca return HTTP 403 to scripts
  (re-checked Oct 18, 2026).
- Elections Canada, Federal Electoral Districts, 2023 Representation Orders (`FederalElectoralDistricts_SHP.zip`, `ED_CF.shp`,
  zip entries dated 2026-09-03), **Open Government Licence - Canada**, https://open.canada.ca/data/dataset/18bf3ea7-1940-46ec-af52-9ba3f77ed708.

| layer | features (published 2021 total) | CSV in git (id) | GeoJSON (not in git) | .gz bytes | .gz sha256 |
|---|---|---|---|---|---|
| provinces / territories | 13 (10 + 3) | `ca_pr.csv` (`pruid`) | `ca_pr_2021.geojson.gz` | 14,828,718 | `b52d4f6bbe0e96d34544ace0de64b73110283086244bdcb9ed33e5aefb53f37a` |
| census divisions | 293 (293) | `ca_cd.csv` (`cduid`) | `ca_cd_2021.geojson.gz` | 15,922,012 | `6de002a602ddcf4bc699d05575df9ce099d3c8c7016193ad2003639ed2d76c75` |
| census subdivisions | 5,161 (5,161) | `ca_csd.csv` (`csduid`) | `ca_csd_2021.geojson.gz` | 18,625,942 | `9c2e196b942d1559aa03bfc9a6bbdafeb9c64111cd6abaa3a3a1b24443cd521d` |
| FED, 2013 Representation Order | 338 (338) | `ca_fed2013.csv` (`feduid`) | `ca_fed2013.geojson.gz` | 15,740,567 | `691e05567ccd95d98209dadeec1cee71cdd45b98afeeaf480361ddffe4f8993b` |
| FED, 2023 Representation Orders | 343 (343) | `ca_fed2023.csv` (`fed_num`) | `ca_fed2023.geojson.gz` | 16,145,958 | `9c494cdc44dd1f9140aa6c926d2d96cfe645e5160b8b7e00eedfdea9407aae31` |

Cross-references (full-resolution overlaps, in git): `ca_csd_fed.csv` (each CSD → top 3 FED 2013 and FED 2023 by % of the CSD's
area) and `ca_fed2013_2023.csv` (every 2013 × 2023 FED pair overlapping by ≥ 0.1 % of either, with both shares).

Published totals checked: Census Dictionary 2021 Table 1.1 (PR 13, CD 293, CSD 5,161, FED 2013 338, all per province equal to
ours) and the 2023 Representation Order proclamation SI/2023-57 (343 seats; N.L. 7, P.E.I. 4, N.S. 11, N.B. 10, Que. 78, Ont. 122,
Man. 14, Sask. 14, Alta. 37, B.C. 43, territories 1 each, all equal to ours).

Geometry: in EPSG:3347 (metres). CSDs: the national CSD coverage, validated per province, simplified as a whole with
shapely.coverage_simplify at **50 m** (about the 0.0005° of towns_2024); area error 0.024 %, Hausdorff median 29 m. CD and PR are
unions of the simplified CSDs, so CSD/CD/PR nest exactly and share identical edges (summed CSD area vs the CBF SHAPE_Area: max
0.001 % PR, 0.002 % CD). FED 2013 and FED 2023 are each simplified as their own coverage at 50 m (FED 2023 is first clipped to
the CBF land, since the Elections Canada file extends into water). Output WGS84 lon/lat, 5 decimals, all geometry valid; gzip
mtime 0. `landarea_km2` = CBF LANDAREA; FED 2023 `land_km2_cbf_clip` is computed from the clipped shape. Per-stage numbers in
`../geo-data-raw/v3ca/report.json`.

Regenerate (raw inputs in `../geo-data-raw/statcan2021`, about 250 MB; each stage is resumable, cache in `<out>/cache`):

```
python3 tools/statcan2021_fetch.py ../geo-data-raw/statcan2021 PR:attr CD:attr FED CSD
python3 tools/statcan2021_fetch.py ../geo-data-raw/statcan2021 --gen10 CSD
python3 tools/statcan2021_fetch.py ../geo-data-raw/statcan2021 --gen10 FED
curl -o ../geo-data-raw/statcan2021/FederalElectoralDistricts_SHP.zip https://www.elections.ca/res/cir/mapsCorner/edb/FederalElectoralDistricts_SHP.zip
unzip -j ../geo-data-raw/statcan2021/FederalElectoralDistricts_SHP.zip 'FederalElectoralDistricts_SHP/ED_CF.*' -d ../geo-data-raw/statcan2021/fed2023
for s in load csd pr cd fed2013 fed2023 xref; do
  python3 tools/canada2021_geojson.py . ../geo-data-raw/statcan2021 --out ../geo-data-raw/v3ca --tol 50 --stage $s; done
```

Input sha256 used for the table above (shapely 2.2.0 / GEOS 3.14.1, pyproj 3.8.0, pyshp 3.1.6):
`CSD.jsonl.gz` ea2e861e61ef9356c632c6fed7a9153377b64b03ae906c7e42ba132f03c4a53f, `FED.jsonl.gz`
e2ff0310795caf3af88e55199b7be58170a7e63233ed77e63fb2445602cf27c3, `CSD_gen10.jsonl.gz`
70ea98cf78fbb18c7ef0615b468744cfe5c6d5abe83ab68b7e3065d1a75feeb2, `FED_gen10.jsonl.gz`
756bc8b93e6a425e661869f51cc211969c103d0d6bbda307c7f25143b3926de3, `FederalElectoralDistricts_SHP.zip`
61e7a57dfe879bfbdc5f91ff46717a8afa97462afcb1db862ad87c570c341904. The Elections Canada zip is updated in place (names change by
Act of Parliament), so a fresh download can differ.

Features the REST service could not return at full resolution (HTTP 500 on every request, retried again Oct 18, 2026) are in
`CSD_failed.json` / `FED_failed.json` and are handled as follows (listed in `report.json`):
- CSD 6204030 Qikiqtaaluk, Unorganized (NU): 10 m server-generalized geometry, overlaps with full-resolution neighbours removed.
- FED 59028 Skeena--Bulkley Valley (BC): same treatment (10 m, clipped to CBF land).
- FED 62001 Nunavut: rebuilt as the union of Nunavut's CSDs (the territory is one FED).
The 10 m generalization is a fifth of the 50 m output tolerance; coverage_clean repaired the few unmatched edges this left
(PR 62 for CSD, 204.6 m²; BC for FED 2013, 202.9 m²; SK for FED 2023, 443.9 m²).

Uncompressed GeoJSON bytes: PR 52,927,419; CD 56,263,142; CSD 67,274,405; FED 2013 55,860,647; FED 2023 58,423,075. Reproducibility
across two full runs was not re-verified for these files (the CSD file was rebuilt once after a properties change: 18,629,615 →
18,625,942 bytes, `landarea_km2` now rounded to the source's 4 decimals).
