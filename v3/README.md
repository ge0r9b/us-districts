# v3 (scaffold placeholder)

No application code yet. Phase 1 is planning only. See [`docs/v3/`](../docs/v3/README.md).

Planned layout (Phase 2): `app/` (Vite SPA + MapLibre), `api/` (Vercel functions), `db/` (migrations from `docs/v3/SCHEMA.sql`), `ingest/` (bot-row loader, legacy v2 importer, pack and tile builders), `tests/` (Playwright ports of `tests/*.py`).

Rules: the v3 lane edits only `v3/` and `docs/v3/`. No deploy or merge to main until v2.0 is tagged and the user approves (REPO-RULES rule 5). Local ports 8860–8899.
