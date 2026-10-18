# v3 hosting and cost plan (Phase 1)

> **Accounts (Oct 18, 2026):** the user has created a **Neon account** (signed in with GitHub). The Neon project is **`ultrevote`** (database `neondb`, PostGIS 3.6), created after builds were approved on 2026-10-18; its connection string is only a box secret (`DATABASE_URL`). **Hosting decision (D3, 2026-10-18): Cloudflare free plan (Pages + a Worker for `/api/v1` + R2 for PMTiles) with Neon; Vercel is superseded.** No Cloudflare account exists yet; the user creates it later, and the first v3 preview goes live there, not on the us-districts site (ARCHITECTURE §5c). No Geocodio or other accounts exist, and this lane creates none. Prices were read from the vendors' public pages on **Oct 18, 2026**; check again before signing up. All prices are USD before tax.

## Sources (read Oct 18, 2026)
- Cloudflare Workers limits: https://developers.cloudflare.com/workers/platform/limits/ (updated Oct 12, 2026); pricing: https://developers.cloudflare.com/workers/platform/pricing/ (Oct 2, 2026)
- Cloudflare Pages limits: https://developers.cloudflare.com/pages/platform/limits/ (Sep 5, 2026); Range behaviour: https://developers.cloudflare.com/pages/configuration/serving-pages/
- Cloudflare KV limits: https://developers.cloudflare.com/kv/platform/limits/ (Oct 8, 2026)
- Vercel pricing (superseded by D3, kept for the record): https://vercel.com/pricing
- Neon pricing: https://neon.com/pricing (plan details: https://neon.com/docs/introduction/plans)
- Supabase pricing (alternative, D2): https://supabase.com/pricing
- Cloudflare R2 pricing (tiles and packs option): https://developers.cloudflare.com/r2/pricing/ (page "last updated Oct 1, 2026")
- Geocodio pricing: https://www.geocod.io/pricing/; Census Geocoder: free (https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html)

## Cloudflare (chosen, D3)
| | Free ($0) | Workers Paid ($5/month per account) |
|---|---|---|
| Worker requests (`/api/v1`) | 100,000 / day (resets 00:00 UTC) | 10M / month included, then $0.30 per 1M |
| Worker CPU | 10 ms per request | 30M CPU-ms / month included, then $0.02 per 1M CPU-ms; up to 5 min per request |
| Pages static asset requests | free and unlimited | free and unlimited |
| Pages files | 20,000 per site, 25 MiB per file, 500 builds / month | 100,000 files on paid Cloudflare plans |
| Pages Range requests | answered with `200` (no `206`): PMTiles cannot be served from Pages | same |
| R2 | 10 GB-month, 1M Class A + 10M Class B ops / month, egress free | $0.015 / GB-month, $4.50 / $0.36 per 1M ops |
| KV | 100,000 reads / 1,000 writes per day, 1 GB | 10M reads / 1M writes per month included |
| Cache API in a Worker | free; works only on a custom domain (not `*.workers.dev`) | same |
| Over the limit | Worker returns error 1027 (or fails open); no surprise bill | Pay-as-you-go |

## Vercel (superseded by D3; kept for the record)
| | Hobby ($0) | Pro ($20/month per developer seat) |
|---|---|---|
| **Use allowed** | "Hobby plan is for personal, non-commercial use" (pricing FAQ) | Commercial |
| CDN requests | 1M / month | 10M / month, then from $2 per 1M |
| Fast Data Transfer | 100 GB / month | 1 TB / month, then from $0.15/GB |
| Function invocations | 1M / month | then from $0.60 per 1M |
| Fluid active CPU / memory | 4 h / 360 GB-h per month | then from $0.128/h, $0.0106/GB-h |
| Fast Origin Transfer | 10 GB / month | then from $0.06/GB |
| ISR reads / writes | 1M / 200k | then $0.40 / $4 per 1M |
| Blob storage / transfer | 1 GB / 10 GB per month | $0.023/GB-month |
| Over the limit | Hobby **cannot buy extra usage**; limits are caps | Pay-as-you-go; default $200 on-demand budget with alerts and an optional hard pause |

## Neon (Postgres + PostGIS)
| | Free ($0, no card) | Launch (pay-as-you-go) | Scale |
|---|---|---|---|
| Compute | 100 CU-hours / project / month, autoscale ≤ 2 CU | $0.106 / CU-hour, ≤ 16 CU | $0.222 / CU-hour |
| Scale to zero | after 5 min, **cannot be disabled** | after 5 min, can be disabled | configurable |
| Storage | **1 GB / project**, 20 GB per account | $0.35 / GB-month | $0.35 / GB-month |
| Egress | 5 GB / project | 500 GB, then $0.10/GB | same |
| Branches | 10 / project | 10, extra $1.50/branch-month | 25 |
| History (restore window) | 6 h | up to 7 days ($0.20/GB-month) | up to 30 days |
| Over the limit | CU-hours or egress used up: compute suspends until next month; > 1 GB: writes blocked (no data deleted) | billed | billed |
| PostGIS, pg_trgm | included on all plans | | |

## Static tiles and packs: where they live
Map tiles are many small requests (a pan or zoom session easily fetches 100–300 tile ranges). **Decision (D3): packs and the app on Cloudflare Pages, PMTiles on R2.** Pages cannot serve PMTiles because it does not answer Range requests with `206`. Through a custom domain the edge cache absorbs most tile reads; served through a Worker instead, every tile range would count against the 100,000/day Worker limit. Options considered:
| Option | Free allowance | Paid | Note |
|---|---|---|---|
| Vercel static deploy / Blob (superseded by D3) | 1M requests, 100 GB transfer (Hobby); Blob 1 GB store | Pro overage per request/GB | Was the dev-time default; request cap was the trigger |
| **Cloudflare R2** + custom domain cache | 10 GB-month storage, 10M Class B reads/month, **egress free** | $0.015/GB-month, $0.36 per 1M reads | Best fit for PMTiles range reads; needs a Cloudflare account (D3) |
| Cloudflare Pages (packs, app, images) | static requests free and unlimited; 25 MiB per file; 20,000 files | — | **Chosen for everything except PMTiles** |
| GitHub Pages (where v2 lives) | 1 GB site limit (spec §2); 100 MB per file; serves Range | — | Not used for v3: v2 stays here, and the v3 preview goes on Cloudflare (ARCHITECTURE §5c) |

Expected sizes: PMTiles for all current sets plus 2020/2024 precincts at about 200–600 MB (estimated from the 390 MB of uncompressed simplified GeoJSON in the v2 export; tippecanoe output is usually smaller). Result packs under 100 MB per `dv`.

## Expected usage and cost
| Phase | Assumption | Hosting (Cloudflare; the Vercel column is superseded) | Neon | Tiles | Total / month |
|---|---|---|---|---|---|
| Phase 2 dev and preview (now → parity) | Only the user and bots; < 50 sessions/day | Local only, then Cloudflare Free $0 | Free $0 if the DB fits 1 GB, else Launch: ~1.5 GB × $0.35 = $0.53 + ~20 CU-h × $0.106 = $2.12 | local, then R2 free | **$0 – $3** |
| Public non-commercial launch (personal project) | ~1,000 sessions/day; packs and tiles are CDN hits; DB only for geocode and search | Cloudflare Free $0 while the API stays under 100,000 requests/day (tiles and packs are not Worker requests) | Launch ~$3–8 (storage ~$0.50–1, compute 0.25–0.5 CU, ~30–60 CU-h) | R2 free (< 10M reads) | **≈ $3 – $8** |
| Commercial (paid custom boundary sets, any revenue) | Same traffic | Free plan is allowed; Workers Paid $5 only if the API passes 100,000/day or needs more than 10 ms CPU | Launch ~$5–15 | R2 ~$0–5 | **≈ $5 – $25** |

Neon cold start: scale-to-zero after 5 minutes means the first geocode or search after idle waits for compute to wake. Static packs and tiles do not touch Neon, so the map and list stay instant. On Launch you can disable scale-to-zero (about 0.25 CU × 730 h = 182 CU-h ≈ $19/month) if cold geocodes become a problem (D4).

## What triggers paid
1. **Any commercial use** (selling custom boundary sets, ads, client work): NYT C-UDA-derived data must be replaced first (spec §9.3). The Cloudflare free plan has no Hobby-style non-commercial term (that was the Vercel blocker, now superseded).
2. **Database > 1 GB** (likely once 2016 or more offices are added; the v2 export already estimates 0.6–0.9 GB): Neon Launch.
3. **> 100 CU-hours / month** on Neon Free (roughly 400 h of 0.25 CU), or **> 5 GB egress**: Launch.
4. **> 100,000 Worker requests/day or > 10 ms CPU per API request**: Workers Paid ($5/month). **> 10 GB in R2 or > 10M Class B reads/month**: R2 pay-as-you-go ($0.015/GB-month, $0.36 per 1M reads). A custom domain with edge caching keeps tile reads off both.
5. **> 2,500 geocodes/day** on Geocodio (if enabled): $1 per 1,000.
6. **Neon restore window > 6 h** (for example 7-day point-in-time restore for safety): Launch ($0.20/GB-month of history).

## Guardrails (once accounts exist; user decision)
Cloudflare Free cannot overspend: over a limit, requests fail, so the Worker route's fail-open/closed mode is a deliberate choice. On Workers Paid, set a `limits.cpu_ms` cap. Neon Launch spending notifications at 80/100 %. Neon autoscaling cap of 1 CU. Geocodio daily limit (it supports one, up to 50,000/day). R2 needs no egress guard (egress is free).
