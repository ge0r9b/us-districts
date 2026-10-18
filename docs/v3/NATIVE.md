# Native clients (macOS and iOS)

Around v4/v5 the app is built in Cursor as cross-platform native macOS and iOS apps. v3 does not ship a native client. It stays API-first so that client can reuse this server.

- **`/api/v1` is the contract.** JSON, versioned in the path, documented in [API.md](API.md) and [openapi.yaml](openapi.yaml). Additive fields stay in v1. A native app pins `?dv=` from `/manifest`.
- **Business rules live on the server or in `v3/packages/core`.** The d/r slot rule, answer keys, sort (high to low, no-data last), filter matching, and `%` / `#` shaping are not inside web components. The API returns rows already sorted. `packages/core` is plain TypeScript with no DOM and no framework.
- **Tiles stay PMTiles / vector.** [styles/map.json](../../v3/styles/map.json) is a MapLibre style document. MapLibre Native on iOS and macOS can read the same archive and the same style. The alpha.1 shell falls back to GeoJSON states only when the archive is not published yet.
- **Auth will be token-friendly.** Responses send `Access-Control-Allow-Origin: *` and allow an `Authorization` header. Nothing in v3 assumes a cookie session. When accounts arrive (D18), clients send a bearer token.
- **Visual rules are data.** [design/tokens.json](../../v3/design/tokens.json) holds light mode, Liquid Glass, colours, and spacing a SwiftUI app can read. It is not a stylesheet.
- **Safe area.** `safeArea.top/right/bottom/left` are the CSS `env(safe-area-inset-*)` values. The shell copies them onto `--sat`, `--sar`, `--sab`, and `--sal`. A native client reads the same keys and applies the platform safe-area insets.
- **Layout mode.** `layoutMode` is `map` or `list`. The shell sets `data-layout` on the document from that token. Map keeps the sheet at the bottom. List hides the map and gives the sheet the rest of the screen, under the top band.
- **Two filters.** Institution (office) and geography (states, counties, precincts) are separate controls. They do not share matching code: institution uses `packages/core` `matchesInstitution`, geography uses `geographyLevel` and `matchesState`.
- **Icons.** Flags, seals, and logos render as they are inside the fixed thumbnail: `object-fit: contain` on a transparent background (native: scaled to fit, clear background). A non-rectangular flag such as Nepal's keeps its true shape. Thumbnail size and transparency are design tokens.
- **Precincts.** Geometry is PMTiles at `/tiles/precinct-2024/{ST}.pmtiles` (zoom 8, layer `precincts`, properties `id`, `name`, `parent`). Results are content-hashed packs. `/api/v1/results?unit_type=precinct` reads the pack. `/api/v1/packs/precinct/{state}/{year}/{office}` redirects to the immutable file. Postgres keeps membership and `precinct_rollup`, not precinct facts.
