# US Districts v3 (alpha.1)

Local only. Nothing here is deployed. The app listens on port **8860** and the API on **8861**. Do not use port 8765.

Business rules (the d/r slot, sort, `%` / `#`) live in `packages/core` and behind `/api/v1`, so a later native macOS/iOS client can reuse them. See `docs/v3/NATIVE.md`.

## What you need

- Node 22 or newer
- PostgreSQL 16 with PostGIS 3.4
- A superuser-capable role for this dev database (the checked-in default is `usd` / `usd`)
- `DATABASE_URL`, for example `postgresql://usd:usd@127.0.0.1:5432/usd_v3`

The loader reads `v2/data` from this checkout and the election and geo files from `origin/data/election` and `origin/data/geo` (git archive into `v3/.cache`, which is gitignored).

## Run

```bash
cd v3
npm install
createdb usd_v3   # once; or any empty database named in DATABASE_URL
export DATABASE_URL=postgresql://usd:usd@127.0.0.1:5432/usd_v3
npm run db:migrate
npm run db:load
npm run dev
```

Open http://127.0.0.1:8860 . The map starts on 2016 president by state. 2020 and 2024 show Pennsylvania counties. `%` / `#` re-sorts the list locally.

`npm test` creates `usd_v3_test` from the same host (it swaps the database name), migrates, loads, and runs the schema, loader, API, and latency checks. `npm run build` then `npm run check:bundle` checks the gzipped JS budget.

## Layout

| Path | Role |
|---|---|
| `app/` | Vite + TypeScript + MapLibre shell |
| `api/` | Hono router, `/api/v1` |
| `packages/core` | Framework-free slot, sort, and filter rules |
| `ingest/` | Migration runner and loaders |
| `design/tokens.json` | Light mode and Liquid Glass tokens |
| `styles/map.json` | MapLibre style (PMTiles, GeoJSON fallback) |

The schema is `docs/v3/SCHEMA.sql`. The HTTP contract is `docs/v3/API.md` and `docs/v3/openapi.yaml`.
