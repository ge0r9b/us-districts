# Provenance of `marriott-properties-v5.csv`

Researched 2026-10-18 from files on the shared box (`/workspace`). Facts only; each claim names its evidence.

## The file
- `/workspace/marriott-properties-v5.csv`, 10,417 rows, sha256 `abfa55bd3f529286329f7d0a007913ef3ca6bc94dcd8c30bacc2543e60b99832`
  (identical to the copy in `raw/inputs/`, which this lane uses).
- Every Marriott file in `/workspace` has mtime 2026-10-17 05:38 EDT. That is when they were copied onto the box in bulk, not when they were made.
- `/workspace` is not a git repository; there is no git history for these files.

## Who made it
- An agent, not a person and not Marriott. The scripts and notes that produced it sit next to it on the box:
  `geo-cache/build_v3.py`, `geo-cache/nominatim_run.py`, `geo-cache/fill_canada.py`, `geo-cache/bound_400.py`, `geo-cache/bound_1500.py`,
  `fill_marriott_v5.py` (reads `marriott-properties-v4.csv`, writes `-v5.csv` and `-v5-notes.txt`), and `fill_usca_600*.py` / `fill_usca_next600.py`
  (ArcGIS passes; logs `marriott-v5-usca-run.log`, `usca*.log`).
- `marriott-properties-notes.txt`: "Built 2026-10-03 from public pages. Not an official Marriott data extract."
- The user's later app-building session (`cloud-agent-transcripts/bc-ebd8729f-…jsonl`) did not create the list. In it the user attached
  `marriott-properties-v4.csv` (transcript line 404) and then their own copy of v5, from `/Users/b/Downloads/marriott-properties-v5.csv`
  (lines 905–927, 2026-10-04 about 09:2x UTC), calling it "the updated list with the urls added". The transcript of the session that ran the build scripts is not on the box.

## When
| Version | Date (from its notes) | Made by |
|---|---|---|
| `marriott-properties.csv` | 2026-10-03 | sitemap build (10,434 rows) |
| `-clean.csv` | 2026-10-03 16:53 EDT | 17 duplicates removed (10,417 rows); geodata from Wikidata P10595/P625 and Nominatim reverse geocoding |
| `-v3.csv` | not recorded (no v3 notes file; between clean and v5) | `geo-cache/build_v3.py`: existing cells, Wikidata (P10595, operator/brand links), OpenStreetMap via Sophox, Nominatim cache |
| `-v4.csv` | not recorded (no v4 notes file; before v5's 2026-10-04 03:29 EDT) | `geo-cache/fill_canada.py` (writes v4: fills blank Canadian street addresses from Photon and Nominatim) |
| `-v5.csv` | 2026-10-04 03:29 EDT, then ArcGIS passes to about 03:55 EDT | `fill_marriott_v5.py` + `fill_usca_600*.py` |

## Sources (from the notes and scripts)
- **Property list and URLs**: marriott.com robots.txt, sitemap index, `sitemap-hotel-sitemaps.xml` (195 regional pages), HWS sitemaps `us-sitemap-hws-1..7`;
  ritzcarlton.com sitemaps; brands.mi; Marriott SEC 10-K (count check, 9,805 properties); Wikipedia Bulgari table; Wikidata P10595/P6375/P1619; Sonder termination news.
  marriott.com hotel overview pages answered "Access Denied" / 403.
- **Addresses and coordinates** (v3–v5): Wikidata P625/P6375 (CC0); OpenStreetMap via Sophox, local OSM brand extracts (124) and Photon (5), all ODbL;
  Nominatim (OSM, ODbL); cached Wikidata streets (4); **ArcGIS World Geocoder** (132 + 411 + 108 + 108 rows; Esri terms restrict storing results).
  Overpass failed and WDQS returned 429 during the v5 run.
- v5 does not record which source filled which row.

## Consequence for this lane
Licence per row is unknown, so v5 coordinates and addresses are not published (rule set 2026-10-18). v5 still supplies MARSHA code, name, brand name and URL;
every published point and address comes from All The Places (CC0) or Marriott's own pacsys feed. See SCHEMA.md → marriott.csv.
