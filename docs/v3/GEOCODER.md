# v3 geocoder plan (Phase 1)

## What v2 does today (from `v2/index.html` and HANDOFF §4, build 1548)
- Address search runs **in the browser**: Census Geocoder one-line (`geocoding.geo.census.gov/geocoder/locations/onelineaddress`, JSONP), then Census components (`…/locations/address` with street/city/state/zip), then OSM Nominatim. There is also a ZIP row from local ZCTA 2024 centroids (`data/zcta2024.js`), and address rows in universal search. Address-like text triggers suggestions after 650 ms (spec §5.2).
- The point is then matched to a precinct or county **client-side** (`aggFor`, point-in-polygon in JS).

## v3 design
1. **Server-side** `/api/v1/geocode?q=` normalizes the address (uppercase, collapse spaces, expand common suffixes) and computes `sha256` → `geocode_cache`. On a hit, it returns the cached point (no provider call).
2. On a miss, it calls providers in order, with a 2.5 s total budget:
   1. **Census Geocoder** `geographies/onelineaddress` (benchmark `Public_AR_Current`)
   2. Census `geographies/address` (components), if the one-line attempt had no match and the query parses into parts
   3. **Fallback provider** (D5: Geocodio recommended once the user approves an account; until then Nominatim through the server proxy with an identifying User-Agent, results cached, ≤ 1 request/s)
3. **Point-in-polygon in PostGIS** on our own boundaries (`/locate`). Census returns its own districts, but **our** boundary sets decide: v2 counts results in 2024 boundaries. A live probe on Oct 18, 2026 (about 05:48 EDT) of the `Current_Current` vintage returned "120th Congressional Districts" and "2026 State Legislative Districts - Upper", which are not v2's 119th Congress / 2024 layers. Census also has no precincts.
   ```sql
   with p as (select st_setsrid(st_makepoint($1, $2), 4326) g)
   select u.unit_type, u.unit_key, u.name
   from p
   join unit_geom ug on ug.lod = 0 and st_covers(ug.geom, p.g)   -- covers: a point on a border still matches
   join unit u on u.id = ug.unit_id
   join boundary_set b on b.id = u.boundary_set_id and b.is_current and b.visibility = 'public';
   ```
   This uses the partial GiST index `unit_geom_gist_lod0`, about 8 bbox candidates per point and then an exact test. The expected time is a few ms warm.
4. **ZIPs and place names never call a provider.** ZIP comes from a ZCTA centroid table, places from `unit`/`entity`/`alias` (pg_trgm). Only street addresses go to Census.
5. Privacy: raw addresses are not logged or stored, only the hash and point. Responses are `Cache-Control: private`.

## Provider options (checked Oct 18, 2026)
| Provider | Cost | Limits / terms | Pros | Cons |
|---|---|---|---|---|
| **US Census Geocoder** ([API docs](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html), [FAQ](https://www2.census.gov/geo/pdfs/maps-data/data/Census_Geocoder_FAQ.pdf)) | Free, no key | Batch ≤ 10,000 records / 5 MB; no published per-second limit; US + PR only | Public domain; returns state, county, county subdivision, place, tract/block, CD, SLD-upper, unified school district; already used by v2 | TIGER address ranges are interpolated; slow (1.31 s for one request in our probe); the FAQ notes match rates vary under load; no autocomplete |
| **Geocodio** ([pricing](https://www.geocod.io/pricing/)) | 2,500 lookups/day free, then $1 / 1,000 (pay-as-you-go) | 1,000 lookups/min; results **may be stored** | Fast, rooftop where available; district appends (CD, SLD) | Needs an account and card above the free tier; each append costs 1 extra credit |
| **Mapbox Geocoding** ([pricing](https://www.mapbox.com/pricing), [temporary vs permanent](https://docs.mapbox.com/help/dive-deeper/understand-temporary-vs-permanent-geocoding/)) | Temporary: 100k/month free, then $0.75 / 1k; Permanent: $5 / 1k | Temporary results **may not be stored/cached**; the docs say responses may only be used with a Mapbox map | Good autocomplete | Conflicts with our cache and with a MapLibre + Esri/OSM map |
| **OSM Nominatim (public)** ([usage policy](https://operations.osmfoundation.org/policies/nominatim/)) | Free | Max 1 req/s for the whole app; identifying User-Agent; **no autocomplete**; ODbL attribution; must be switchable without an app update | Already a v2 fallback; worldwide (future Canada) | Not for production volume; v2 calls it from the browser, so v3 should proxy and cache it or drop it |
| Self-hosted Nominatim / Pelias | Server cost (tens of GB of RAM/disk for a US import) | Own terms (ODbL data) | No limits, private | Operations burden; overkill for now |
| Google Geocoding | Paid per request | Terms require Google map display; storage restricted | Best match quality | Licence conflicts |

## Recommendation
- **Default:** Census (server-side, cached) as primary, plus PostGIS `/locate` on our boundaries. Keep Nominatim only as a proxied, cached last resort, honouring its 1 req/s policy. This costs $0 and needs no accounts.
- **When the user approves an account (D5):** add Geocodio as the second provider (its 2,500/day free tier probably covers all real use), and keep Census first for cost.
- **Autocomplete:** suggestions come from our own place index (states, counties, towns, ZIPs). Street-address autocomplete would need a paid provider. It stays out of v1, matching v2, which only fires address lookups after 650 ms.
- Latency: Census at about 1.3 s dominates. v2 has the same wait. The UI shows the place or ZIP result instantly and adds the address row when Census answers, without moving rows that are already shown (no layout jumps).
