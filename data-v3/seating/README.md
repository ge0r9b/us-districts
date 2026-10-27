# v3data – seat structure and office holders (snapshot 2026-10-18)

Run `python3 tools/build_v3data.py && python3 tools/build_pack.py` (inputs in `../src`). The build makes no
graphics and does not write to the repo. See SCHEMA.md for the format.

Sources (retrieved Oct 2026):
- Congress: unitedstates/congress-legislators (current + historical), cross-checked against senate.gov
  senators XML (2026-10-08) and the House Clerk MemberData XML (2026-10-01).
- State chambers: Ballotpedia chamber member tables and infoboxes, plus the "<chamber> elections, 2026" pages
  (seats up, candidates). Cross-checked against Open States people (commit 15d0336, 2026-10-15, scraped from
  official legislature sites), openstates-metadata seat counts, and Wikipedia "Political party strength in U.S. states".
- Courts: Ballotpedia court pages (selection method, justices, appointing governor), cross-checked against the
  Wikipedia court pages (seat/district, term end, appointer).
- District IDs: github.com/ge0r9b/us-districts data-v3/geo/*.csv (read only).

## Election results (2016–2024, plus odd-year and special contests 2015–2025)
Pipeline (re-runnable; re-run to refresh current holders):
`python3 tools/build_v3data.py` -> `tools/results/congress_parse.py` -> `tools/results/bp_district_parse.py` -> `tools/build_results.py` -> `tools/build_pack.py`.
Raw caches are in ../src/ (FEC xlsx, Clerk 2024 PDF text, MEDSL Senate, Klarner SLERs, Ballotpedia HTML).
Sources: results_sources.csv. No NYT data. US Senate 2022/2024 are the Election Data lane's rows (read only).

Shared candidate ids (fix 2026-10-26): Election Data `candidate_id` slugs are surname-first and repeat across states (252 slugs, e.g. `rogers-mike` = AL-03 House and MI 2024 Senate). They are now linked only by (slug, state) plus office and year (`cid_links.csv`); a slug used in several states is state-qualified in `people.cid`, and the old slug-only collisions are listed in `cid_collisions.csv`. Former members of Congress running again in the same state link to their bioguide id (MI 2024 Senate Mike Rogers = R000572). An FEC id that resolves to a member who never served from that state is not linked. Source: `tools/fetch/upstream_cids.py` (read-only Election Data checkout) -> `src/results/upstream_cids.json`.

Exclusions (user request): CA, KS and WV supreme courts are removed entirely, and no court contests before 2017 are kept.
These are build-time filters (`DROP_COURTS` in build_v3data.py, `COURT_MIN_YEAR` in build_results.py), so every rebuild stays consistent.
Orphaned people are pruned on every build. Always run the full pipeline in order.

## City councils and mayors (30 most populous cities)

Ranking: Census Bureau Vintage 2025 city/town population estimates (sub-est2025.csv, SUMLEV 162, https://www2.census.gov/programs-surveys/popest/datasets/2020-2025/cities/totals/). Members and mayors: Ballotpedia city pages and the Ballotpedia list of current mayors of the top 100 cities (fetched 2026-10-18), with Charlotte's mayor and Denver's at-large vacancy confirmed on the official city sites.

All 30 of the most populous cities are included. Five have a consolidated or district legislature that is not called a city council; they use the same schema (`office` = city_council, plus a `…-mayor` body) with a body-specific key slug: Indianapolis City-County Council (Unigov), San Francisco Board of Supervisors (City and County), Nashville Metro Council (Metropolitan Government; the vice mayor presides and votes only to break ties, seat VM), Louisville Metro Council, and the Council of the District of Columbia (`us-dc-washington-council` = repo entity `chamber:dc-council`; DC mayor `us-dc-washington-mayor` = repo `state:11`). Their b ids (188–197) were appended, so the first 25 cities' keys and ids are unchanged.

| Census rank | city | council key | seats (voting) | districts / at-large / mayor seat | election | mayor's council role | next council election | official council site |
|---|---|---|---|---|---|---|---|---|
| 1 | New York, NY | `us-ny-new-york-city-council` | 51 | 51 / 0 / 0 | partisan | none (veto) | 2026-11-03 | https://council.nyc.gov/ |
| 2 | Los Angeles, CA | `us-ca-los-angeles-city-council` | 15 | 15 / 0 / 0 | nonpartisan | none (veto) | 2026-11-03 | https://clerk.lacity.gov/ |
| 3 | Chicago, IL | `us-il-chicago-city-council` | 50 | 50 / 0 / 0 | nonpartisan | tie (veto) | 2027-02-23 | https://www.chicago.gov/city/en/about/wards.html |
| 4 | Houston, TX | `us-tx-houston-city-council` | 17 | 11 / 5 / 1 | nonpartisan | member | 2027-11-02 | https://www.houstontx.gov/council/ |
| 5 | Phoenix, AZ | `us-az-phoenix-city-council` | 9 | 8 / 0 / 1 | nonpartisan | member | 2026-11-03 | https://www.phoenix.gov/administration/mayorcouncil.html |
| 6 | Philadelphia, PA | `us-pa-philadelphia-city-council` | 17 | 10 / 7 / 0 | partisan | none (veto) | 2027-11-02 | https://phlcouncil.com/ |
| 7 | San Antonio, TX | `us-tx-san-antonio-city-council` | 11 | 10 / 0 / 1 | nonpartisan | member | 2029-05 | https://www.sa.gov/Directory/Departments/Mayor-Council |
| 8 | San Diego, CA | `us-ca-san-diego-city-council` | 9 | 9 / 0 / 0 | nonpartisan | none (veto) | 2026-11-03 | https://www.sandiego.gov/citycouncil |
| 9 | Dallas, TX | `us-tx-dallas-city-council` | 15 | 14 / 0 / 1 | nonpartisan | member | 2027-05-01 | https://dallascityhall.com/government/citycouncil/Pages/default.aspx |
| 10 | Fort Worth, TX | `us-tx-fort-worth-city-council` | 11 | 10 / 0 / 1 | nonpartisan | member | 2027-05-01 | https://www.fortworthtexas.gov/government/city-council |
| 11 | Jacksonville, FL | `us-fl-jacksonville-city-council` | 19 | 14 / 5 / 0 | partisan | none (veto) | 2027-03 | https://www.jacksonville.gov/city-council |
| 12 | Austin, TX | `us-tx-austin-city-council` | 11 | 10 / 0 / 1 | nonpartisan | member | 2026-11-03 | https://www.austintexas.gov/council |
| 13 | San Jose, CA | `us-ca-san-jose-city-council` | 11 | 10 / 0 / 1 | nonpartisan | member | 2026-11-03 | https://www.sanjoseca.gov/your-government/departments-offices/mayor-and-city-council |
| 14 | Charlotte, NC | `us-nc-charlotte-city-council` | 11 | 7 / 4 / 0 | partisan | tie (veto) | 2027-11-02 | https://www.charlottenc.gov/City-Government/City-Council |
| 15 | Columbus, OH | `us-oh-columbus-city-council` | 9 | 9 / 0 / 0 | nonpartisan | none (veto) | 2027-11-02 | https://www.columbus.gov/City-Council |
| 16 | Indianapolis, IN (City-County Council) | `us-in-indianapolis-city-county-council` | 25 | 25 / 0 / 0 | partisan | none (veto) | 2027-11-02 | https://www.indy.gov/activity/city-county-council-members |
| 17 | San Francisco, CA (Board of Supervisors) | `us-ca-san-francisco-board-of-supervisors` | 11 | 11 / 0 / 0 | nonpartisan | none (veto) | 2026-11-03 | https://www.sf.gov/departments--board-supervisors |
| 18 | Seattle, WA | `us-wa-seattle-city-council` | 9 | 7 / 2 / 0 | nonpartisan | none (veto) | 2026-11-03 | https://www.seattle.gov/council |
| 19 | Denver, CO | `us-co-denver-city-council` | 13 | 11 / 2 / 0 | nonpartisan | none (veto) | 2026-11-03 | https://www.denvergov.org/Government/Agencies-Departments-Offices/Agencies-Departments-Offices-Directory/Denver-City-Council |
| 20 | Nashville-Davidson, TN (Metro Council) | `us-tn-nashville-davidson-metro-council` | 41 | 35 / 6 / 0 | nonpartisan | none (veto) | 2027-08 | https://www.nashville.gov/departments/council/metro-council-members |
| 21 | Oklahoma City, OK | `us-ok-oklahoma-city-city-council` | 9 | 8 / 0 / 1 | nonpartisan | member | 2027-02 | https://www.okc.gov/government/city-council |
| 22 | Washington, DC (Council of the District of Columbia) | `us-dc-washington-council` | 13 | 8 / 5 / 0 | partisan | none (veto) | 2026-11-03 | https://dccouncil.gov/councilmembers/ |
| 23 | El Paso, TX | `us-tx-el-paso-city-council` | 8 | 8 / 0 / 0 | nonpartisan | tie (veto) | 2026-11-03 | https://www.elpasotexas.gov/government |
| 24 | Las Vegas, NV | `us-nv-las-vegas-city-council` | 7 | 6 / 0 / 1 | nonpartisan | member | 2026-11-03 | https://www.lasvegasnevada.gov/Government/Mayor-City-Council |
| 25 | Boston, MA | `us-ma-boston-city-council` | 13 | 9 / 4 / 0 | nonpartisan | none (veto) | 2027-11-02 | https://www.boston.gov/departments/city-council |
| 26 | Detroit, MI | `us-mi-detroit-city-council` | 9 | 7 / 2 / 0 | nonpartisan | none (veto) | 2029-11-06 | https://detroitmi.gov/government/city-council |
| 27 | Louisville/Jefferson County, KY (Metro Council) | `us-ky-louisville-jefferson-county-metro-council` | 26 | 26 / 0 / 0 | partisan | none (veto) | 2026-11-03 | https://louisvilleky.gov/government/metro-council/districts-1-26 |
| 28 | Portland, OR | `us-or-portland-city-council` | 12 | 12 / 0 / 0 | nonpartisan | tie | 2026-11-03 | https://www.portland.gov/council |
| 29 | Memphis, TN | `us-tn-memphis-city-council` | 13 | 13 / 0 / 0 | nonpartisan | none (veto) | 2027-10 | https://www.memphiscitycouncil.com/ |
| 30 | Baltimore, MD | `us-md-baltimore-city-council` | 15 | 14 / 1 / 0 | partisan | none (veto) | 2028-11-07 | https://baltimorecitycouncil.com/ |

Official-site verification of the five added bodies (2026-10-18): San Francisco (sf.gov Board of Supervisors) and DC (dccouncil.gov) match Ballotpedia for every member; Nashville: all 40 council members match nashville.gov (the vice mayor is not on that page; Ballotpedia used). Indianapolis: indy.gov lists District 10 Shaila Mulholland (D, Democratic caucus pick, WFYI 2026-10-05) and District 21 Josh Masquelier (R, Republican caucus pick, Mirror Indy 2026-09-03), shown vacant on Ballotpedia, and District 11 as Crista Lee Wells (Ballotpedia: Crista Carlino); the official values are kept. Louisville: louisvilleky.gov blocks automated fetches (HTTP 403), so the roster was checked against indexed official council pages and Metro budget/agenda PDFs; District 7 Paula McCraney is listed as Independent (I-7) on the 2026-06-25 council agenda (Ballotpedia: Democratic). Every override is recorded in `city_bodies.corrections` and as `official site vs Ballotpedia` rows in `crosscheck.csv`.


## Layout in the repo (branch data/seating)
`data-v3/seating/`: the tables and packs above (`holders.pack.json` is published gzipped only), `SCHEMA.md`, this README,
`tools/` (build pipeline), `tools/fetch/` (source fetch/parse scripts), `config/city/cities.json` (curated city structure).
Raw source snapshots (Ballotpedia/Wikipedia HTML, FEC/Clerk/MEDSL/Klarner/Census files; ~hundreds of MB) are not committed;
the tools expect them under /workspace/seating/src on the build box. `openstates_metadata` is the pip package.
