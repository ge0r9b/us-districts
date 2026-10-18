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
- `towns_2024.geojson.gz` and `places_2024.geojson.gz` (`tools/v3_geojson_2024.py`, gzipped because they are over 5 MB): every
  Census TIGER 2024 county subdivision (35,482, 10-digit GEOID) and place (32,041, 7-digit GEOID, incorporated places and CDPs)
  of the 50 states and DC, one feature per GEOID (`id` = GEOID). Properties: `geoid`, `state`, `statefp`, `countyfp` and
  `county` (towns), `name`, `namelsad`, `lsad`, `classfp`, `funcstat` (filter A/B/C/G for governmental towns, CLASSFP C* /
  `incorporated` for incorporated places), `aland`, `awater`, and the v2 rows carrying the feature: `v2_parts`
  (`"<county>|<name>"` keys of `v2/data/parts/`) and, for places, `v2_places` (the `v2/data/places/` row name, or null).
  Every one of the 58,127 v2 town and place rows with a GEOID is a feature. Geometry: per state, the whole TIGER coverage is
  simplified with shapely.coverage_simplify at 0.0005° (finer than v2's 0.002°; shared edges stay identical), coordinates
  snapped to 5 decimals with every geometry valid. Rebuild from the TIGER zips with the script for full resolution.
