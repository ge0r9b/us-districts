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
  Rows are identified by (`layer`, `row`); (`state`, `v2_name`) is **not** unique for 74 school rows.
- `match`: `code+point` / `name+point` (code or name matched and the TIGER internal point lies inside the v2 polygon,
  buffered 0.002°), `code` / `name` (single candidate, internal point outside the simplified polygon), `point`
  (no name match, exactly one internal point inside), empty = unmatched. Same-named TIGER features are told apart only by the point test.
- towns.csv columns: `layer, state, county, v2_name, geoid, funcstat, match`.

Coverage at commit time: every row matched, no GEOID used twice within a layer (ushouse 436, senate 1,950,
statehouse 4,890, schools 13,305, counties 3,144, towns 1,598).
Re-run after any v2 boundary change; the `row` index shifts when rows are inserted.
