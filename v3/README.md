# US Districts v3 (alpha.2)

Local only. Nothing here is deployed. The app listens on port **8860** and the API on **8861**. Do not use port 8765.

Business rules (the d/r slot, sort, `%` / `#`) live in `packages/core` and behind `/api/v1`, so a later native macOS/iOS client can reuse them. See `docs/v3/NATIVE.md`.

## What you need

- Node 22 or newer
- PostgreSQL 16 with PostGIS 3 (CI uses 3.4; the Neon project is on 3.6)
- A superuser-capable role for a local dev database (the local example is `usd` / `usd`)
- `DATABASE_URL` in the environment, or in a gitignored `v3/.env` for migrate and seed

The loader reads `v2/data` from this checkout and the election and geo files from `origin/data/election` and `origin/data/geo` (git archive into `v3/.cache`, which is gitignored).

## Run

```bash
cd v3
npm install
createdb usd_v3   # once; or any empty database named in DATABASE_URL
export DATABASE_URL=postgresql://usd:usd@127.0.0.1:5432/usd_v3
npm run db:migrate
npm run db:seed
npm run db:load
npm run dev
```

`db:migrate` and `db:seed` read `DATABASE_URL` when they start. They also load `v3/.env` if that file exists, and a variable already set in the environment wins. Nothing in the repo contains a connection string.

A host ending in `neon.tech` is opened with `@neondatabase/serverless` over WebSocket, so port 5432 is not required. Any other host, including this local example, uses `pg` over TCP. Both paths run `db/migrations/*.sql` and then `db/seed.sql`.

`db:load` uses the same host switch. A `neon.tech` host goes through `@neondatabase/serverless` over WebSocket. Any other host uses `pg`. It reads `v3/.env` when that file exists. Inserts are chunked multi-row statements (the WebSocket driver has no COPY). Each source file is its own transaction: an applied or rejected sha is skipped on the next run, and `data_version` moves when a file changes rows. `result.source_record_id` is the CSV line number. `unit.source_record_id` is the geo `row`, or the precinct key.

The default load is core (states, counties, congressional districts, and the official result files from alpha.1), state legislative districts, schools, and precincts. Precinct result files are about 530 MB of table space. They are skipped when they would push the database past 350 MB (the free Neon cap is 0.5 GB). There is no precinct polygon file in `data/geo`. Companies, institutions, governments, seating, and people stay behind flags. Companies are global (the size check uses 193,000 locations) and, when loaded, also write clustered PMTiles at `app/public/tiles/companies.pmtiles`.

```bash
cd v3
npm run db:migrate
npm run db:seed
npm run db:load
# precincts print a size line and stay out until you accept it:
npm run db:load -- --allow-over-budget=precincts
# companies are not in the default load:
npm run db:load -- --include=companies
# add the flag only if the script says the live database size plus ~100 MB would pass 350 MB:
npm run db:load -- --include=companies --allow-over-budget=companies
```

Institutions, governments, seating, and people print an estimate and do not insert. Their column maps are not reviewed, so `--allow-over-budget` does not load them either. Re-running `db:load` is safe. It does not deploy.

Open http://127.0.0.1:8860 . The map starts on 2016 president by state. 2020 and 2024 show Pennsylvania counties. `%` / `#` re-sorts the list locally.

`npm test` refuses a `neon.tech` host. It creates `usd_v3_test` from the same server (it swaps the database name), migrates, seeds, loads, and runs the schema, loader, API, and latency checks. `npm run build` then `npm run check:bundle` checks the gzipped JS budget.

## Layout

| Path | Role |
|---|---|
| `app/` | Vite + TypeScript + MapLibre shell |
| `api/` | Hono router, `/api/v1` |
| `packages/core` | Framework-free slot, sort, and filter rules |
| `db/migrations/` | Ordered idempotent DDL, checksummed in `usd.schema_migration` |
| `db/seed.sql` | Reference rows (tenant, licences, unit types, boundary sets, data_version) |
| `ingest/` | TCP migration helper and loaders |
| `design/tokens.json` | Light mode and Liquid Glass tokens |
| `styles/map.json` | MapLibre style (PMTiles, GeoJSON fallback) |

`docs/v3/SCHEMA.sql` is the design document those SQL files were derived from. The HTTP contract is `docs/v3/API.md` and `docs/v3/openapi.yaml`.
