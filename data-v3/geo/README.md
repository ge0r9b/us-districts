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

## Germany, BKG VG250 01.01.2026 (`tools/foreign_geojson.py … de`)

Source and licence:
- Bundesamt für Kartographie und Geodäsie (BKG), **VG250 Verwaltungsgebiete 1:250 000, Ebenen, Stand 01.01.2026**
  (`vg250_01-01.utm32s.gpkg.ebenen.zip`, published 21 Jul 2026, `DE_VG250.gpkg`, ETRS89 / UTM 32N, EPSG:25832),
  https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/2026/. Edition: the 01.01. one (Gebietsstand 1 January 2026,
  `dokumentation/aktualitaet.txt` = 01.01.2026); the 31.12.2025 edition is the earlier of the two. Licence **Datenlizenz
  Deutschland – Namensnennung – Version 2.0** (https://www.govdata.de/dl-de/by-2-0).
- Required attribution (BKG `nutzungsbedingungen_vg250.pdf`, Quellenvermerk; on a web page link "BKG" to https://www.bkg.bund.de
  and "dl-de/by-2-0" to https://www.govdata.de/dl-de/by-2-0), plus a change note:
  `© BKG (2026) dl-de/by-2-0, Datenquellen: https://sgx.geodatenzentrum.de/web_public/gdz/datenquellen/datenquellen_vg_nuts.pdf`
  — `Geometrie vereinfacht (10 m) und nach WGS84 umprojiziert` (geometry simplified at 10 m and reprojected to WGS84).

| layer | features (official total) | CSV in git (key) | GeoJSON (not in git) | .gz bytes | .gz sha256 |
|---|---|---|---|---|---|
| Länder | 16 (16) | `de_lan.csv` (`code` = ARS, 2) | `de_lan_2026.geojson.gz` | 790,807 | `8a1312e4de9eac9c782419342a50fd295c3c379e602bfba6b8c65fd712fcdebf` |
| Kreise | 401 (294 Landkreise + 107 kreisfreie Städte) | `de_krs.csv` (ARS, 5) | `de_krs_2026.geojson.gz` | 2,780,431 | `7f9c6f5d3a94b9e21e20a971d11916f496b75f4752244ad0b2992c13071ff2c0` |
| Gemeindeverbände (VWG) | 4,580 (see below) | `de_vwg.csv` (ARS, 9) | `de_vwg_2026.geojson.gz` | 7,112,190 | `2e8e621f484b49c38a714321e8256f4d1561078ef84e1feb8b27c764d375a37d` |
| Gemeinden | 10,939 = 10,747 Gemeinden (10,747) + 192 gemeindefreie Gebiete | `de_gem.csv` (ARS, 12; `ags` 8) | `de_gem_2026.geojson.gz` | 9,476,294 | `371d70d44a54199f13cf61e77bd8779a233ff61159c10b2be42c41af5fd71f1f` |

CSV columns: `de_gem`: `code` (ARS), `ags`, `name` (GEN), `type` (BEZ: Stadt / Gemeinde / Gemeindefreies Gebiet), `parent_vwg`
(ARS[:9]), `krs`, `lan`, `area_km2`. `de_vwg` / `de_krs` / `de_lan`: `code`, `ags` (blank for VWG; the source has `--------`), `name`,
`type` (BEZ), `parent` (KRS for VWG, Land for KRS, `DE`), `n_gem`, `area_km2`.

Counts checked: Gemeinden 10,747 = 2,057 Städte + 8,690 Gemeinden at 1 Jan 2026 (de.wikipedia "Gemeinde (Deutschland)", citing
Destatis; our BEZ split is the same 2,057 / 8,690); Kreise 294 Landkreise + 107 kreisfreie Städte (de.wikipedia lists of
Landkreise and kreisfreie Städte, Stand 2026; ours 252 Landkreis + 42 Kreis = 294, 98 Kreisfreie Stadt + 9 Stadtkreis = 107);
16 Länder. Destatis' own Verwaltungsgliederung tables (31.12.2025 and 2026 quarters) were not reachable from the build box (TLS
reset) or the fetch tool (timeout), so these totals are verified against secondary sources that cite Destatis, not against the
Destatis file itself. VWG: VG250 carries every Gemeinde in a VWG unit, so the 4,580 are 1,202 Gemeindeverbände proper (Verwaltungs-
gemeinschaft 573, Amt 209, Verbandsgemeinde 149, Verwaltungsverband 120, Samtgemeinde 114, Erfüllende Gemeinde 37) plus 3,378
verband-free units (Einheitsgemeinde 2,084, Gemeinschaftsfreie Gemeinde 987, Amtsfreie Gemeinde 266, Verbandsfreie Gemeinde 41);
a published national total for Gemeindeverbände was not verified. Gemeindefreie Gebiete: VG250 has 192; de.wikipedia
"Gemeindefreies Gebiet" counts 194 at 1 Jan 2026 (difference not resolved).

Geometry: land parts only (GF = 4; the 155 GEM / 93 VWG / 33 KRS water parts, GF = 2, of the North Sea, Baltic and Bodensee are
dropped). Base coverage = the 10,939 Gemeinden, validated per Land (all valid, nothing cleaned), coverage_simplify at **10 m**
(VG250 is already a 1:250,000 product: 1,908,596 → 1,747,829 vertices, area error 0.0013 %, Hausdorff median 1.1 m, max 6.9 m). The whole national
coverage is valid after simplification (checked with coverage_is_valid on all 10,939).
VWG / KRS / LAN are unions of the simplified Gemeinden by ARS prefix (9 / 5 / 2), so all four layers nest exactly; the
full-resolution unions equal BKG's own VWG / KRS / LAN polygons (symmetric difference 0.0000 % for every unit, no code missing or
extra). `area_km2` = geodesic area of the full-resolution GF = 4 polygon (sum of Länder 357,184.67 km²; Destatis' official area
includes water). Output WGS84, 5 decimals, gzip mtime 0; a rerun of `--stage lan` from the same cache gave the same sha256.

Regenerate (input 64 MB zip, sha256 `6b096eb4862b4eafda9294e425fb5a6d0e7773eb5815a4d4edc78b639ec2728f`, BKG md5
`912ebecfc58bade695cf31271f4e0e85`):

```
mkdir -p ../geo-data-raw/vg250 && cd ../geo-data-raw/vg250 && \
  curl -O https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/2026/vg250_01-01.utm32s.gpkg.ebenen.zip && \
  unzip -o vg250_01-01.utm32s.gpkg.ebenen.zip -d x && cd -
for s in load base vwg krs lan; do
  python3 -W ignore tools/foreign_geojson.py . ../geo-data-raw de --out ../geo-data-raw/v3de --stage $s; done
```

Uncompressed GeoJSON bytes: LAN 2,573,446; KRS 9,195,565; VWG 25,970,089; GEM 36,540,967. Libraries: shapely 2.2.0 / GEOS 3.14.1,
pyproj 3.8.0, pyogrio 0.13.0 / GDAL 3.12.4. Per-stage numbers in `../geo-data-raw/v3de/report.json`.

## France, IGN ADMIN EXPRESS COG 2026 (`tools/foreign_geojson.py … fr`)

Source and licence:
- Institut national de l'information géographique et forestière (IGN), **ADMIN EXPRESS COG 4.0, édition 2026-01-01**
  (INSEE Code officiel géographique **2026**, i.e. 1 January 2026; delivery `1_DONNEES_LIVRAISON_2026-06-00493`, feed updated
  2026-07-01), the full-precision edition (not COG CARTO), from https://data.geopf.fr/telechargement/resource/ADMIN-EXPRESS-COG.
  GeoPackages per territory: `ADMIN-EXPRESS-COG_4-0__GPKG_LAMB93_FXX_2026-01-01` (metropolitan France, EPSG:2154) and
  `…_RGAF09UTM20_GLP`, `…_RGAF09UTM20_MTQ`, `…_UTM22RGFG95_GUF`, `…_RGR92UTM40S_REU`, `…_RGM04UTM38S_MYT` (the five DROM, each in
  its local UTM CRS), plus `…_RGAF09UTM20_BLM`, `…_RGAF09UTM20_MAF`, `…_RGSPM06U21_SPM` (overseas collectivités).
  Licence **Licence Ouverte / Open Licence 2.0** (Etalab, https://www.etalab.gouv.fr/licence-ouverte-open-licence).
- Required attribution (Licence Ouverte: source and date of last update), plus a change note:
  `Source : IGN – ADMIN EXPRESS COG, édition 2026-01-01 (COG 2026, mise à jour juillet 2026), Licence Ouverte 2.0 — données
  modifiées (géométrie simplifiée à 20 m, reprojetée en WGS84)`.

| layer | features (official total) | CSV in git (key) | GeoJSON (not in git) | .gz bytes | .gz sha256 |
|---|---|---|---|---|---|
| régions | 18 (13 + 5) | `fr_reg.csv` (`code` = INSEE, `siren`) | `fr_reg_2026.geojson.gz` | 1,728,368 | `17b9ba105c4db011213d1a5ff407be49b88ad14ac33cf67a641c1d881bc38a66` |
| départements | 101 (96 + 5) | `fr_dep.csv` (INSEE, `siren`) | `fr_dep_2026.geojson.gz` | 3,455,906 | `f518230ab22ff341daff96a2befe1801caf0986e36e366d7bf2ecf853535f8de` |
| EPCI | 1,264 = 1,252 EPCI à fiscalité propre (1,252) + Métropole de Lyon + 11 EPT | `fr_epci.csv` (`code` = SIREN) | `fr_epci_2026.geojson.gz` | 9,804,733 | `40a5f838f44c0ef537589c56075ed44b8c5ef72d9be717a1d48cf38e8126147c` |
| communes | 34,875 (34,875) | `fr_com.csv` (INSEE, `siren`) | `fr_com_2026.geojson.gz` | 37,567,192 | `2b6a1e18dd8a3a62456acfb149a6f779b6fa50315dc8048b9d32eb0d39e39547` |
| overseas collectivités BLM, MAF, SPM | 3 | `fr_com_om.csv` (INSEE 977, 978, 975) | `fr_com_om_2026.geojson.gz` | 29,098 | `4c283b1b40d12637ece01ee804521b9e50127e9d4b87cd220d0d6656cf960eba` |
| communes associées (COMA) / déléguées (COMD) | 2,566 = 468 + 2,098 (COG 2026: 2,576 = 471 + 2,105; 10 missing, see below) | `fr_cad.csv` (`code` = INSEE + `type`) | `fr_cad_2026.geojson.gz` | 2,662,820 | `c0e32b8809f1108d7971fd8fc0898109058c19cfd58c2816694f1cb5c962476a` |

CSV columns: `fr_com`: `code` (INSEE), `siren`, `name`, `type` (IGN `statut`), `parent_dep`, `reg`, `epci_siren` (`/`-separated
when a commune is in both the Métropole du Grand Paris and an EPT; `NR` for the 4 isolated communes), `zone` (FXX/GLP/MTQ/GUF/REU/MYT),
`area_km2`. `fr_dep`: `code`, `siren`, `name`, `type`, `parent_reg`, `n_com`, `zone`, `area_km2`. `fr_reg`: same with `parent` = FR.
`fr_epci`: `code` (SIREN), `name`, `type` (IGN `nature`), `deps` (member départements), `n_com`, `zone`, `area_km2`.

Counts checked: communes 34,875 at 1 Jan 2026 (INSEE, COG 2026 announcement: "34 875 communes" in metropolitan France and the
DROM; ours 34,746 FXX + 129 DROM); régions 18 and départements 101 (COG 2026); EPCI à fiscalité propre 1,252 (DGCL, BIS n° 206,
January 2026: 21 métropoles, 14 CU, 230 CA, 987 CC; 4 isolated communes). IGN's EPCI layer has 1,264 rows: 22 "Métropole"
(21 + the Métropole de Lyon, a collectivité with EPCI powers), 14 CU, 229 CA, 988 CC and 11 "Etablissement public territorial"
(the Grand Paris EPTs); 1,264 − 12 = 1,252. CA 229 / CC 988 vs DGCL 230 / 987: IGN still types 243100781 Le Grand Ouest
Toulousain as a CC; DGCL says it became a CA in 2025. The 4 isolated communes (Île-de-Bréhat, Île-de-Sein, Ouessant,
L'Île-d'Yeu) carry `epci_siren` = `NR`, matching DGCL's 4. The 3 overseas collectivités (Saint-Barthélemy, Saint-Martin,
Saint-Pierre-et-Miquelon) are outside the 34,875 and are a separate layer; SPM's 2 communes are not in `fr_com`.

Geometry: base coverage = the 34,875 communes, each territory simplified in its own projected CRS, validated per département
(all valid, nothing cleaned), coverage_simplify at **20 m**: FXX 27,180,904 → 6,234,511 vertices, area error 0.13 %, Hausdorff
median 13.3 m (max 441 m, a single outlier; DROM medians 18–41 m, max 58–137 m). Each territory's whole coverage is valid after
simplification. Départements and régions are unions of the
simplified communes by their INSEE codes; EPCI are unions of the member communes listed in IGN's EPCI layer
(`codes_insee_des_communes_membres`; every listed code found). The full-resolution unions equal IGN's own région, département and
EPCI polygons (symmetric difference 0.0000 % for every unit; no code missing or extra). `area_km2` = geodesic area of the
full-resolution polygon. Output WGS84, 5 decimals, gzip mtime 0.

Communes associées / déléguées (stage `cad`, added Oct 18, 2026): IGN publishes them in the same ADMIN EXPRESS COG 2026 FXX
GeoPackage, layer `commune_associee_ou_deleguee` (none in the DROM packages). `fr_cad.csv`: `code` (INSEE), `siren` (mostly empty),
`name`, `type` (commune associée / commune déléguée), `parent_com` (`code_insee_de_la_commune_de_rattach`, all 934 found in
`fr_com`), `zone`, `area_km2`. **Join on (code, type)**: 582 rows share the INSEE code of their parent commune nouvelle (e.g. the
chef-lieu déléguée), so `code` alone collides with `fr_com`. Geometry: per parent commune the units are coverage-simplified together
at 20 m (2,000,181 → 451,612 vertices, area error 0.15 %, Hausdorff median 14 m), then clipped to the parent's simplified polygon,
so they nest exactly in `fr_com`; no unit became empty. They do not always fill the parent: COMA cover only the associated part
(578 of 934 parents ≥ 99 % covered). Check against INSEE `v_commune_2026.csv` (COG 2026, sha256
`7be1153de3a63df48fa0ca77f8490c8a0c5c9c4eb12f5cec1ca7f70b0237b1d3`): no extra rows; 10 COG rows missing from IGN, all under 3 parents:
COMD 25303 Hauterive-la-Fresse, 25347 La Longeville, 25390 Montbenoît, 25398 Montflovin, 25620 Ville-du-Pont (parent 25390);
COMA 55294 Liouville, 55319 Marbotte, 55451 Saint-Agnant-sous-les-Côtes (parent 55012); COMD 69144 Nuelles, 69208
Saint-Germain-sur-l'Arbresle (parent 69208). No other IGN product carries them (ADMIN EXPRESS COG CARTO is a generalization of the
same data; BD TOPO's commune_associee_ou_deleguee is the same IGN source). Their area is inside the parent's `fr_com` polygon.

Regenerate (inputs about 247 MB of .7z; sha256 of each, also in `../geo-data-raw/adminexpress/SHA256SUMS`):
FXX `688eb44505d9b4a8e422ded2f4afaac799f10783de563132ca1a60e9491c6278`, GLP `53f6340c0143c17dd554fd3c191046dd2af288e255ca11d6cf8b480340c91e6e`,
MTQ `3d04005ffad90eb82a4e53663d53a04940c4a5fad64e1f41e8e4abd568841327`, GUF `267721af2a6dd3e50990e8c6bd337392c7ebfeec10e5c79abf36ac2fb09ce098`,
REU `6e9e6aeea31352df75d59128eaf14247460481ed2d8690032481440515a1de62`, MYT `86d5e7463c7ce1b96afaef93d423596f1a682b818b723efd1c7145cf27e347d0`,
BLM `bddc87d6e3b604d3d1efbb310a640515ba7c0c6b38571d26eeaa10345c545169`, MAF `08fa723dbfe2061d14bc20ef28055374dc1fc02398e68543a1023bebeef5be96`,
SPM `75bad941a664eab3ae8a35ed535c055221ff3c7abf23bc5e48ac29188410a435`.

```
mkdir -p ../geo-data-raw/adminexpress && cd ../geo-data-raw/adminexpress
for z in LAMB93_FXX RGAF09UTM20_GLP RGAF09UTM20_MTQ UTM22RGFG95_GUF RGR92UTM40S_REU RGM04UTM38S_MYT RGAF09UTM20_BLM RGAF09UTM20_MAF RGSPM06U21_SPM; do
  n=ADMIN-EXPRESS-COG_4-0__GPKG_${z}_2026-01-01
  curl -O https://data.geopf.fr/telechargement/download/ADMIN-EXPRESS-COG/$n/$n.7z; done
python3 -c "import py7zr,glob; [py7zr.SevenZipFile(f).extractall('x') for f in sorted(glob.glob('*.7z'))]"; cd -
for s in load base dep reg epci om cad; do
  python3 -W ignore tools/foreign_geojson.py . ../geo-data-raw fr --out ../geo-data-raw/v3fr --stage $s; done
```

Uncompressed GeoJSON bytes: REG 5,914,434; DEP 11,549,042; EPCI 32,743,757; COM 129,454,005; COM_OM 108,018; CAD 9,344,367. Per-stage
numbers in `../geo-data-raw/v3fr/report.json`.

## United Kingdom, ONS Open Geography Portal BFC (`tools/ons_fetch.py`, `tools/foreign_geojson.py … gb`)

Source and licence:
- Office for National Statistics, Open Geography Portal, **BFC** layers (full resolution, clipped to the coastline at Mean High
  Water), fetched from ONS's ArcGIS feature services `services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/<service>/FeatureServer`
  in British National Grid (EPSG:27700), full resolution (no server generalization, mm precision), Oct 18, 2026:
  `Local_Authority_Districts_May_2026_Boundaries_UK_BFC` (LAD_MAY_2026_UK_BFC), `Counties_and_Unitary_Authorities_December_2025_Boundaries_UK_BFC`
  (CTYUA_DEC_2025_UK_BFC), `Combined_Authorities_December_2025_Boundaries_EN_BFC` (CAUTH_DEC_2025_EN_BFC, layer 1),
  `PARNCP_MAY_2026_EW_BFC` (Parishes and Non-Civil Parished Areas (May 2026) Boundaries EW BFC). BFC was available for all four.
  Latest editions on Oct 18, 2026: LAD and PARNCP May 2026; CTYUA and CAUTH December 2025 (no May 2026 edition exists). LAD codes
  are identical in LAD Dec 2025 and May 2026 (361 each), so CTYUA Dec 2025 aligns with LAD May 2026. ONS stopped issuing a
  parish-only layer after May 2024; PARNCP is the full England and Wales coverage.
  Licence **Open Government Licence v3.0** (https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
- Required attribution (ONS geography licences page, "Digital boundaries and reference maps"), plus a change note:
  `Source: Office for National Statistics licensed under the Open Government Licence v.3.0. Contains OS data © Crown copyright
  and database right 2026.` — geometry simplified at 20 m and reprojected to WGS84. (The NI LGDs in the LAD layer are LPS-derived;
  ONS publishes them under the same OGL statement.)

| layer | features (official total) | CSV in git (key) | GeoJSON (not in git) | .gz bytes | .gz sha256 |
|---|---|---|---|---|---|
| Local Authority Districts, May 2026 | 361 (E 296, S 32, W 22, N 11) | `gb_lad.csv` (`code` = LAD26CD) | `gb_lad_2026.geojson.gz` | 4,456,105 | `4f63d0ff28d0636594c6f075dae3e64a388de1cd5f1aa3544be68d9b9b9a782c` |
| Counties and unitary authorities, Dec 2025 | 218 (21 counties + 197 unitary) | `gb_ctyua.csv` (CTYUA25CD) | `gb_ctyua_2025.geojson.gz` | 3,877,281 | `3556609a318bc823dc883c82b9c44c2cc5a306aba0335963b33a4c5d6d06ad6e` |
| Combined authorities, Dec 2025 | 15 (15) | `gb_cauth.csv` (CAUTH25CD) | `gb_cauth_2025.geojson.gz` | 445,484 | `97bfbe35bd7fc315bdee5a02e7eb0b8b86a95ecf2ab5c3f742abc8c311264d6f` |
| Parishes / communities / NCP areas, May 2026 | 11,542 (10,464 + 878 + 200) | `gb_par.csv` (PARNCP26CD) | `gb_par_2026.geojson.gz` | 11,902,782 | `68b0aa8ac759d5f3a2e906158be6f6082ac9cafb7a684bc6f13990a1de5da203` |

CSV columns: `gb_lad`: `code`, `name`, `name_cy` (Welsh name, Wales only), `type` (E06 unitary authority, E07 non-metropolitan district,
E08 metropolitan district, E09 London borough, S12 council area, W06 principal area, N09 local government district), `parent_ctyua`,
`cauth` (E47 code or blank), `area_km2`. `gb_ctyua` / `gb_cauth`: `code`, `name`, `name_cy`, `type`, `parent` (GSS country code;
E92000001 for CAs), `area_km2`, `n_lad`, `lads` (member LAD codes). `gb_par`: `code`, `name`, `name_cy`, `type` (E04 parish,
W04 community, E43 non-civil parished area), `parent_lad`, `area_km2`.

Counts checked: LAD 361 by prefix (E06 63, E07 164, E08 36, E09 33 = England 296; S12 32 Scottish council areas; W06 22 Welsh principal
areas; N09 11 NI LGDs: the statutory totals). CTYUA 218 = 21 counties (ONS `CTY_DEC_2025_EN_NC` names-and-codes list: 21) + 63 E06
+ 36 E08 + 33 E09 + 32 + 22 + 11. CAUTH 15 (Greater Manchester, South Yorkshire, West Yorkshire, Liverpool City Region, Tees Valley,
West Midlands, Cambridgeshire and Peterborough, West of England, York and North Yorkshire, North East, and the combined county
authorities East Midlands, Devon and Torbay, Hull and East Yorkshire, Greater Lincolnshire, Lancashire; the Greater London
Authority is not a CA). Parishes: every code equals ONS's separate names-and-codes lists `PAR_APR_2026_EW_NC` (11,342 = 10,464
E04 + 878 W04) and `NCP_APR_2026_EN_NC` (200 E43), no code missing or extra (`../geo-data-raw/ons/nc_check.json`).

Geometry: base coverage = the 11,542 PARNCP units (England and Wales) + the 43 Scottish and NI LADs, validated per CTYUA (the
England–Scotland border units E06000057, E06000063, S12000006, S12000026 as one group, where parish edges meet the Scottish LAD
edges: 5 features with unmatched edges, repaired by coverage_clean, 0.7 m² moved), coverage_simplify at **20 m**: 21,394,514 →
2,440,369 vertices, area error 0.15 %, Hausdorff median 16.6 m (max 517 m, isolated outliers on the coast); the whole national
coverage is valid after simplification. LAD = union of its PARNCP units (PARNCP26 carries LAD26CD) or the LAD itself (S, N);
CTYUA and CAUTH = unions of LADs, membership from the full-resolution overlap with ONS's CTYUA / CAUTH polygons (every LAD ≥ 99.94 %
inside one CTYUA; 106 LADs in a CA, all ≥ 99 % inside). Check against the published polygons (full-resolution union vs ONS
polygon, symmetric difference): LAD max 0.027 % (E06000058 BCP; next 0.001 %); CAUTH max 0.017 %; CTYUA max 0.148 % (E06000023
Bristol), 0.104 % (E06000044 Portsmouth), all others ≤ 0.043 %: those are coastline/estuary differences between the December 2025
CTYUA and the May 2026 LAD/PARNCP editions, and our CTYUA follows the May 2026 lines. No code missing or extra in any layer.
`area_km2` = geodesic area of the full-resolution ONS polygon (BFC, so land to Mean High Water; LAD total 244,438 km²).
Output WGS84 (pyproj EPSG:27700 → 4326), 5 decimals, gzip mtime 0.

Regenerate (raw ONS pulls, Esri JSON, sha256: LAD `855aef10143e9343c070e349d0462bddbd5506976844aecc8ea04a4795dfec26`, CTYUA
`87ba6aa10b103faf7eb1a57c57b567b87c9e705df85a727ed40f2ee4a3097984`, CAUTH `7bb5e1aae7929cd41c7dcc3d9dd8ae4031d1221f55697aa75ade4ddd392cb450`,
PAR `d973ac2872a06e3a1ff5a08ce6caf9f1792585f6037e15a02258a6ae6dbf124e`; ONS can republish a layer in place, so a fresh pull can
differ):

```
python3 tools/ons_fetch.py ../geo-data-raw/ons LAD CAUTH CTYUA PAR
for s in load base lad ctyua cauth; do
  python3 -W ignore tools/foreign_geojson.py . ../geo-data-raw gb --out ../geo-data-raw/v3gb --stage $s; done
```

Uncompressed GeoJSON bytes: LAD 15,598,700; CTYUA 13,589,679; CAUTH 1,519,994; PAR 44,310,467. Per-stage numbers in
`../geo-data-raw/v3gb/report.json`.
