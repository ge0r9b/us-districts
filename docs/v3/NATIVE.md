# Native clients (macOS and iOS)

Around v4/v5 the app is built in Cursor as cross-platform native macOS and iOS apps. v3 does not ship a native client. It stays API-first so that client can reuse this server.

- **`/api/v1` is the contract.** JSON, versioned in the path, documented in [API.md](API.md) and [openapi.yaml](openapi.yaml). Additive fields stay in v1. A native app pins `?dv=` from `/manifest`.
- **Business rules live on the server or in `v3/packages/core`.** The d/r slot rule, answer keys, sort (high to low, no-data last), filter matching, and `%` / `#` shaping are not inside web components. The API returns rows already sorted. `packages/core` is plain TypeScript with no DOM and no framework.
- **Tiles stay PMTiles / vector.** [styles/map.json](../../v3/styles/map.json) is a MapLibre style document. MapLibre Native on iOS and macOS can read the same archive and the same style. The alpha.1 shell falls back to GeoJSON states only when the archive is not published yet.
- **Auth will be token-friendly.** Responses send `Access-Control-Allow-Origin: *` and allow an `Authorization` header. Nothing in v3 assumes a cookie session. When accounts arrive (D18), clients send a bearer token.
- **Visual rules are data.** [design/tokens.json](../../v3/design/tokens.json) holds light mode, Liquid Glass, colours, and spacing a SwiftUI app can read. It is not a stylesheet.
