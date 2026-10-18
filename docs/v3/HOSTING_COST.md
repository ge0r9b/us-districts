# v3 hosting and cost plan (Phase 1)

> **Accounts (Oct 18, 2026):** the user has created a **Neon account** (signed in with GitHub). **No Neon project exists yet.** The plan is a `dev` branch in Neon first, and the connection string reaches v3 only as a secret, once builds are approved. No Vercel, Cloudflare, Geocodio or other accounts exist, and this lane creates none. Prices were read from the vendors' public pages on **Oct 18, 2026**; check again before signing up. All prices are USD before tax.

## Sources (read Oct 18, 2026)
- Vercel pricing: https://vercel.com/pricing
- Neon pricing: https://neon.com/pricing (plan details: https://neon.com/docs/introduction/plans)
- Supabase pricing (alternative, D2): https://supabase.com/pricing
- Cloudflare R2 pricing (tiles and packs option): https://developers.cloudflare.com/r2/pricing/ (page "last updated Oct 1, 2026")
- Geocodio pricing: https://www.geocod.io/pricing/; Census Geocoder: free (https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html)

## Vercel
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
Map tiles are many small requests (a pan or zoom session easily fetches 100–300 tile ranges). On Vercel Hobby that uses up the **1M CDN requests/month at a few thousand sessions**. Options:
| Option | Free allowance | Paid | Note |
|---|---|---|---|
| Vercel static deploy / Blob | 1M requests, 100 GB transfer (Hobby); Blob 1 GB store | Pro overage per request/GB | Simplest; request cap is the trigger |
| **Cloudflare R2** + custom domain cache | 10 GB-month storage, 10M Class B reads/month, **egress free** | $0.015/GB-month, $0.36 per 1M reads | Best fit for PMTiles range reads; needs a Cloudflare account (D3) |
| GitHub Pages (where v2 lives) | 1 GB site limit (spec §2) | — | Not for v3: size limit, and v3 must not deploy to Pages before approval |

Expected sizes: PMTiles for all current sets plus 2020/2024 precincts at about 200–600 MB (estimated from the 390 MB of uncompressed simplified GeoJSON in the v2 export; tippecanoe output is usually smaller). Result packs under 100 MB per `dv`.

## Expected usage and cost
| Phase | Assumption | Vercel | Neon | Tiles | Total / month |
|---|---|---|---|---|---|
| Phase 2 dev and preview (now → parity) | Only the user and bots; < 50 sessions/day | Hobby $0 | Free $0 if the DB fits 1 GB, else Launch: ~1.5 GB × $0.35 = $0.53 + ~20 CU-h × $0.106 = $2.12 | Vercel static or R2 free | **$0 – $3** |
| Public non-commercial launch (personal project) | ~1,000 sessions/day; packs and tiles are CDN hits; DB only for geocode and search | Hobby $0 if under 1M requests (tiles on R2 keep it there) | Launch ~$3–8 (storage ~$0.50–1, compute 0.25–0.5 CU, ~30–60 CU-h) | R2 free (< 10M reads) | **≈ $3 – $8** |
| Commercial (paid custom boundary sets, any revenue) | Same traffic | **Pro required: $20/seat** | Launch ~$5–15 | R2 ~$0–5 | **≈ $25 – $40** |

Neon cold start: scale-to-zero after 5 minutes means the first geocode or search after idle waits for compute to wake. Static packs and tiles do not touch Neon, so the map and list stay instant. On Launch you can disable scale-to-zero (about 0.25 CU × 730 h = 182 CU-h ≈ $19/month) if cold geocodes become a problem (D4).

## What triggers paid
1. **Any commercial use** (selling custom boundary sets, ads, client work): Vercel Pro is mandatory under Hobby's non-commercial term. Separately, NYT C-UDA-derived data must be replaced first (spec §9.3).
2. **Database > 1 GB** (likely once 2016 or more offices are added; the v2 export already estimates 0.6–0.9 GB): Neon Launch.
3. **> 100 CU-hours / month** on Neon Free (roughly 400 h of 0.25 CU), or **> 5 GB egress**: Launch.
4. **> 1M CDN requests or > 100 GB transfer / month on Vercel**: Hobby cannot pay overage, so Pro, or move tiles to R2.
5. **> 2,500 geocodes/day** on Geocodio (if enabled): $1 per 1,000.
6. **Neon restore window > 6 h** (for example 7-day point-in-time restore for safety): Launch ($0.20/GB-month of history).

## Guardrails (once accounts exist; user decision)
Vercel spend-management hard limit set low (for example $25). Neon Launch spending notifications at 80/100 %. Neon autoscaling cap of 1 CU. Geocodio daily limit (it supports one, up to 50,000/day). R2 needs no egress guard (egress is free).
