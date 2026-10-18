# US Districts v3 (alpha.3)

Local only. Nothing here is deployed. The app listens on port **8860** and the API on **8861**. Do not use port 8765.

Business rules (the d/r slot, sort, `%` / `#`) live in `packages/core` and behind `/api/v1`, so a later native macOS/iOS client can reuse them. See `docs/v3/NATIVE.md`.

## What you need

- Node 20.19 or newer (Vite 7's floor; Node 22 is not required)
- PostgreSQL 16 with PostGIS 3 (CI uses 3.4; the Neon project is on 3.6)
- A superuser-capable role for a local dev database (the local example is `usd` / `usd`)
- `DATABASE_URL` in the environment, or in a gitignored `v3/.env` for migrate and seed

The loader reads `v2/data` from this checkout and the election, geo, companies, and institution files from `origin/data/election`, `origin/data/geo`, `origin/data/companies`, and `origin/data/inst-entities` (git archive into `v3/.cache`, which is gitignored). A cache refills when that branch's commit differs from the `.commit` stamp in the cache directory. The same commit is stored on `load_batch.git_commit`. When a later batch for a file is applied, older rejected batches of that file are marked `superseded`.

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

The default load is core (states, counties, congressional districts, and the official result files from alpha.1), state legislative districts, the 2022 and 2024 US House Senate files (1,023 rows each), and schools. It then assigns each US company location to its county, state, and US House district, in slices of about 10,000 ids. Each slice commits on its own and prints a progress line. A dropped connection retries that slice once; run `db:load` again to resume, and a second pass changes nothing when the hits are unchanged. `entity_location.unit_id` is the county. Points that hit nothing are flagged `no_unit_resolved`. Non-US rows stay unit-less. Institutions are a later command, after locations. Precinct facts, precinct units, and `unit_crosswalk` stay out of Postgres. `npm run precincts` writes per-state PMTiles under `app/public/tiles/precinct-2024/`, content-hashed packs under `app/public/packs/precinct/`, and `precinct_rollup` only. Those directories are generated and gitignored. `precincts --dry-run` prices the rollup and reports unit and crosswalk counts at 0 database bytes. It writes nothing. Companies and institutions stay behind flags. The 350 MB check is the live database size plus the institution projection when that load is requested. Companies, when loaded, also write clustered PMTiles at `app/public/tiles/companies.pmtiles`. Institutions load entities, relations, image metadata, and `body_entity` from `origin/data/inst-entities` at run time, with no image files. v2 keys and image attribution go to `app/public/packs/inst/`. `npm run db:size` prints heap, index, toast, and dead tuples. Migration `014` adds `entity.nid` and vacuums after the DDL commits. Read the institution dry-run before that load. Governments, seating, and people still print a gap and do not insert. A rejected file's gap lists each rule with its count. Migration `013` marks a rejected `load_batch` superseded when a later applied batch for the same file already exists.

```bash
cd v3
npm run db:size
npm run db:migrate
npm run db:load -- --include=institutions
npm run db:vacuum
npm run db:size
npm run precincts -- --dry-run
```

`db:size` only reads. `db:migrate` applies `014_shrink.sql`, then `VACUUM FULL` on `entity` and `entity_location_unit` after the DDL commits. The institution load writes the pack first, then deletes `entity_extra`, `entity_image_text`, and `entity_image_source`. `db:vacuum` rewrites those emptied tables so the space shows up in `pg_database_size`. The precinct dry-run prices `precinct_rollup` only. It does not write. Run `npm run precincts` only after that dry-run looks right. Governments are still not inserted. Re-running these commands is safe. Nothing here deploys.

```bash
# one state while you check the rollup:
npm run precincts -- --state=Vermont
# companies are not in the default load:
npm run db:load -- --include=companies
# add the flag only if pg_database_size is already over 350 MB:
npm run db:load -- --include=companies --allow-over-budget=companies
npm run db:load -- --include=institutions --allow-over-budget=institutions
```

`db:load` prints `database`, which is `pg_database_size`, and one line per location slice. The institution dry-run prints a Postgres projection that includes indexes, page overhead, and toast. Use `--allow-over-budget=institutions` only when that projection is still over 350 MB.

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
