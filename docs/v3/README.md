# docs/v3: Phase 1 plan for US Districts v3

Branch `v3/plan` (v3 lane, REPO-RULES). Plan only: no deploy, no accounts, v2 untouched.

| Doc | Contents |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Stack, diagram, geometry/caching strategy, tags and restore |
| [SCHEMA.sql](SCHEMA.sql) / [SCHEMA.md](SCHEMA.md) | Postgres + PostGIS schema and its rationale |
| [API.md](API.md) | Endpoints, response shapes, caching, versioning |
| [DATA_LOADING.md](DATA_LOADING.md) | Bot-row ingest, validation, upserts, legacy v2 importer, **v2 intake alignment**, questions for the data lanes |
| [GEOCODER.md](GEOCODER.md) | Address → point → units |
| [HOSTING_COST.md](HOSTING_COST.md) | Vercel / Neon / R2 pricing (read Oct 18, 2026), triggers for paid tiers |
| [PERFORMANCE.md](PERFORMANCE.md) | Budget (instant response first) and how to meet it |
| [MIGRATION_CHECKLIST.md](MIGRATION_CHECKLIST.md) | v2 → v3 parity checklist, UI rules, the 78 Playwright tests, **v2 intake alignment** |
| [DECISIONS.md](DECISIONS.md) | Open decisions with recommended defaults |
