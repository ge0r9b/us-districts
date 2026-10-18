# v3 (scaffold placeholder)

No application code yet. Phase 1 is planning only. See [`docs/v3/`](../docs/v3/README.md).

Planned layout (Phase 2): `app/` (Vite SPA + MapLibre), `api/` (Vercel functions), `db/` (migrations from `docs/v3/SCHEMA.sql`), `ingest/` (bot-row loader, legacy v2 importer, pack and tile builders), `tests/` (Playwright ports of `tests/*.py`).

Rules: the v3 lane edits only `v3/` and `docs/v3/`. No deploy or merge to main until v2.0 is tagged and the user approves (REPO-RULES rule 5). Local ports 8860–8899.

Roadmap (details in `docs/v3/ARCHITECTURE.md` §9):
- **v3.0:** parity with v2. The brand/location schema ships empty; its data loads in v3.1 (D21).
- **v3.1:** list ingest: Wikidata brands and locations (Companies bot) plus governments, plus Canada (D23; v3-only, with PMTiles for ridings and polls built from the source layers in the v3.1 tile build). This loads the complete brand/location set from `data/companies`: all brands and all ~38,000 locations (38,092 at b583b2c). That is about 1.4 MB gz and roughly 10–20 MB in Postgres with the GIST index (estimate; D21).
- **v3.2:** scheduled refresh.
- **v3.3:** auth and moderated add/upload.
- **v4+:** live voting and custom boundary sets.
- **v5/v6:** bridge to the user's private corporate database (LEI/CIK crosswalk via `entity_alias`). This stays off the public v3 surface.
