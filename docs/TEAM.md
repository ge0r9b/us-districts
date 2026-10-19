# Bot team structure (handoff Oct 19 2026)

Replicate this team for v3. All bots share one computer (/workspace) and the repo github.com/ge0r9b/us-districts; v3 lives in private ge0r9b/v3 (Neon + Cloudflare Worker).

| Bot | Role | Reports / hands off to |
|---|---|---|
| Grok Bot (lead) | Orchestrator. Owns v2 builder (only one allowed to edit v2/index.html), rules QA bugs, hourly watchdog of v2/v3/box health, relays to user. Never sends build links. | User |
| Full Stack | v3 trajectory lead: owns ge0r9b/v3 (v3/plan, v3/build), Neon, Worker, V2_PARITY_CHECKLIST, architecture (per-country silos). | Grok Bot; receives every v2 fix to mirror |
| Bug Tester | Hourly QA passes on live v2 (WebKit + Chromium, 5 sizes), files QA-### in BUGS.md on qa/bugs branch, verifies fixes. | Grok Bot rules severity |
| Status | Project-wide status reports; sends build links to user. | User |
| Success | Progress timeline; relays user reports. | Grok Bot |
| Speed | Performance budgets (first load, pan fps, tap latency, iPhone last 2 years). | Grok Bot / Full Stack |
| Trailblazer | Explores new approaches/prototypes for the map. | Grok Bot |
| Geo | Geography/boundaries (states, counties, towns, districts, precincts; Canada). | Full Stack |
| Historic Election Data | Certified results 2016-2024 (+Senate, House, state leg); official sources, certified totals win. | Full Stack |
| Topic | Topics feature. | Full Stack |
| Institution filter | Institutions list/filter. | Full Stack |
| Companies | Company scraper (brand name, parent, customer-facing locations). | Full Stack |
| Governments | Governments scraper. | Full Stack |
| People | People data. | Full Stack |
| Seating Charts | Seating-chart project. | User |
| convenience store pharma or gas | Store-location scraping for those chains. | Companies |
| 0-5 | Numbered helper bots; "0" is also a group chat. | Grok Bot |

## Standing rules
- v2 frozen: fixes only; every shared-behavior fix mirrored to v3 build by build.
- Official sources first, never fabricate, mark estimates with ≈. Certified state totals win; gaps <10k votes OK.
- Speed first: zero latency; historic results precomputed and frozen.
- Never delete scraped data meeting US rules (incl. foreign). /workspace/countries is the only copy.
- v3: national boundaries for all countries; foreign sub-national waits for user approval except Canada.
- Company schema: public brand name, parent (country + address), locations with country/state/county/town/address/coords. No legal entities, EINs, LEIs.
- Per-country silos: own DB/host/repo; one shared UI fetching from each country's server.
- Tag v2.0 only when BUGS.md is clear and the full suite passes.
- GitHub sign-in only by Google/Apple/passkey; merges of iOS PR #2 need the user.
- Downtime extras paused until user approves resuming (asked Sun Oct 25, 2 PM ET).
