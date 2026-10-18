# v3 open decisions (need the user's call)

Each item has a **recommended default**. If the user says nothing, Phase 2 proceeds with the default. Data-format questions for the data lanes are listed separately in DATA_LOADING.md §10 (Q-E1…Q-E8, Q-G1…Q-G7).

**Resolved Oct 18, 2026 (orchestrator):** D11 (2016 in v2, 3-point slider) and Q-E8 (official values win over v2's, and v2's are kept in history). **Pending:** D10 (orchestrator triage).

| # | Decision | Options | Recommended default | Why |
|---|---|---|---|---|
| D1 | Front-end framework | (a) Vite + TypeScript SPA (Preact/React) + Hono functions; (b) Next.js App Router on Vercel | **(a) Vite SPA** | One interactive screen; a static shell gives the lowest TTFB and no SSR cold start. Choose (b) only if SEO pages per place matter. |
| D2 | Database host | (a) Neon Postgres + PostGIS; (b) Supabase (spec's earlier pick: Auth, Storage, Realtime included) | **(a) Neon** for Phase 2; revisit Supabase when live votes and Auth start | Neon: branching per preview, scale-to-zero, PostGIS on every plan; Free 1 GB vs Supabase Free 500 MB and pausing after 1 week idle. |
| D3 | Where tiles and packs live | (a) Vercel static / Blob; (b) Cloudflare R2 + custom domain | **(b) R2** once traffic is real; (a) during dev | Hobby's 1M CDN requests/month is used up quickly by tiles; R2 egress is free. Needs a Cloudflare account (none created). |
| D4 | Neon plan | Free → Launch | **Free during dev; Launch when the DB passes 1 GB or before any public launch** | The estimated DB of 0.6–0.9 GB is close to the 1 GB cap; Launch is about $3–8/month here. |
| D5 | Geocoder fallback | Census only; + Geocodio (account); + proxied Nominatim | **Census primary + proxied Nominatim now; add Geocodio when an account is approved** | $0 now; Geocodio's 2,500/day free tier allows stored results. |
| D6 | Estimate flag in bot rows | infer `is_estimate` from `weight<1`; ask the bot for an optional `method` column | **Ask for `method`** (Q-E3); infer until then | Without it, re-tabulated weight-1 district totals lose their ≈. |
| D7 | Rows missing from a newer batch | keep; delete; explicit retract list | **Keep; deletes only via an explicit retract file** | Idempotent, no silent data loss. |
| D8 | Candidate IDs | v2 short keys (`biden`, `trump`); bot slugs (`biden-joseph-robinette-jr`) | **Bot slugs are canonical**; v2 keys kept as aliases | Matches `data-v3/results` already committed on `data/election`. |
| D9 | Basemap | Esri World Street Map (as v2); Protomaps/OSM PMTiles self-hosted | **Esri for parity in alpha; decide before any commercial use** | Esri commercial terms unverified (spec §9.3). |
| D10 | "pts" in # mode (spec §11.3 known gap) | keep v2 behaviour; strict rule (no % or pts in # mode) | **PENDING: the orchestrator is triaging this in v2 (Oct 18, 2026).** v3 follows whatever v2 ships | Parity first: the outcome in v2 becomes the v3 rule. |
| D11 | Years in the time slider | — | **RESOLVED (orchestrator, Oct 18, 2026): 2016 presidential is in v2 as a 3-point slider 2016 / 2020 / 2024, with Clinton as the Democratic answer aligned with Biden / Harris (`dem_nominee`). 2016 is the last vote data set for v2.** v3 schema and API already take N years | More years and offices after that are v3 work (ARCHITECTURE.md §9). |
| D12 | District-type outlines | near-black (v2 today) vs white (rule "white with data") | **Follow v2 as shipped** (`boundary-color` test) and confirm | Spec §11.7 marks it "Decision needed". |
| D13 | School district granularity | one `school` layer (v2) vs unified/elementary/secondary (TIGER) | **Keep the v2 single layer in the UI; store TIGER types in `unit_type`** | Parity first; the geo lane is adding OK elementary districts (Q-G4). |
| D14 | Old v2 links (`#s=` hash, `v:1`) | break; map to v3 | **Map v1 hashes to v3 state** | No broken shared links. |
| D15 | Tags | as ARCHITECTURE.md §6 | **Adopt; the orchestrator creates them** (REPO-RULES: releases/tags are orchestrator-owned) | First needed: `v2.0` (prerequisite for any v3 deploy) and `v3.0-plan`. |
| D16 | Custom/paid boundary sets | design only (now); build in v3.0; later | **Design only now (schema ready); build after v3.0** | Also requires commercial licensing work (NYT data replaced) and Vercel Pro. |
| D17 | Accounts | none (now) | **Create nothing until the user approves D2–D5**; then the user (or the orchestrator with approval) creates Vercel, Neon and optionally Cloudflare/Geocodio | Task rule: no accounts. |
