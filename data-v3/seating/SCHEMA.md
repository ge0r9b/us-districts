# Seats / office-holders data, v3 (spec)

Snapshot date is 2026-10-18. Every table is a plain CSV keyed by small integers. `holders.pack.json.gz` is the
one-file client bundle built from them; `holders.lite.json.gz` is the same bundle without people.

## Tables (canonical, CSV)

| file | key | columns |
|---|---|---|
| `bodies.csv` | `b` | `key` (stable string id, see *Body keys*), `st`, `kind` (L = legislature, C = court, M = municipal: city council or mayor), `office` (us_senate, us_house, state_senate, state_house, state_legislature, state_supreme_court, state_court_criminal_appeals, city_council, mayor), `name`, `seats` (voting seats in force today), `majority` (floor(n/2)+1), `unit_type` (state, cd, sldu, sldl, none, council_district, place), `term` (years; `2-4-4` = IL/TX-style senate cycle), `stagger` (all/partial/none_2026/thirds/staggered/none), `last_el`, `next_el`, `sel` (selection_methods code), `complete_from` (holders are complete from this date onward), `src`, `note`, `geoid` (Census place GEOID SSPPPPP for city bodies), `entity` (repo entity id, city bodies only: `muni:place:SSPPPPP`; DC Council `chamber:dc-council`, DC mayor `state:11`) |
| `seats.csv` | (`b`,`s`) | `s` (0-based seat index inside the body; this is the "seat slot" a chart draws), `dist` (district label normalised to the repo's tiger_name/v2_name), `geoid` (repo GEOID: CD `SSDD`, SLDU/SLDL `SS`+3 chars, state FIPS for the Senate, empty for courts and NH floterials), `pos` (1..k inside a multi-member district; Senate = class), `label`, `valid_from`/`valid_to` (only for House slots that exist in a single apportionment), `up26` (1 = seat on the 2026 ballot), `role` ('' / at-large / super-district / president / chair / vice-mayor / mayor) |
| `people.csv` | `p` (contiguous; renumbered each build) | `key` (`bioguide:X` / `fec:ID` / `cid:<Election-Data slug>` / `os:<openstates uuid>` / `bp:<ballotpedia slug>` / `kl:<Klarner candid>` / `name:ST:slug`), `name`, `cid` (surname-first slug, unique in this file; = the Election Data `candidate_id` when that slug is used in one state only, `{slug}-{st}` when the Election Data uses the same slug in several states, e.g. `rogers-mike-al` / `rogers-mike-mi`; join Election Data rows through `cid_links.csv` on (`cid`, `st`), never on the slug alone) |
| `cid_links.csv` | (`cid`,`st`,`year`,`office`) | Election Data `candidate_id` -> `p`/`key`. Linked only within the same state, office family and year, by surname + first initial (district breaks ties); never across states. `cid_in_people` = that person's people.cid; `method` = `ambiguous: …` rows list every candidate `p` and are not attached |
| `cid_collisions.csv` | row | audit of shared-name collisions (same slug, different state or person key): `slug`, `st`, `p`, `key`, `name`, `person_states`, `slug_states`, `kind`, `old_cid` (build 06a2cc3), `new_cid`, `old_slug_holder` (who the slug resolved to before), `action` (fixed: … / ambiguous: …) |
| `terms.csv` | (`b`,`s`,`start`) | `end` (empty = serving), `p`, `party` (code), `caucus` (code, empty = same as party), `how` (E = elected, S = special, A = appointed, R = retained), `appt` (party code of the appointing governor), `approx` (1 = start/end inferred from election date, not a sworn-in date), `src` (snapshot / results contest id) |
| `court_detail.csv` | (`b`,`s`) | `p`, `appointer`, `appt_party`, `chief`, `term_ends`, `wiki_party` |
| `contests_2026.csv` | row | `b`, `year`, `geoid`, `district`, `n_up` (seats elected in that district), `slot` (Ballotpedia ballot column: Democratic/Republican/Other/Candidates), `party`, `incumbent`, `name`, `bp` (slug) |
| `parties.csv` | `code` | 0 vac, 1 dem, 2 rep, 3 ind, 4 np, 5 prog (VT), 6 fwd, 7 lib, 8 grn, 9 unk, 10 oth. `key` = repo party_key; `bot` = the Election Data bot's party code |
| `selection_methods.csv` | `code` | 0 none (legislature), 1 partisan, 2 partisan_retention, 3 party_nominated_nonpartisan (MI), 4 nonpartisan, 5 retention |
| `composition.csv` | row | `b`, `date`, `basis` (party/caucus), `party`, `n`: replay results used as a regression test |
| `crosscheck.csv` | row | `body`, `check`, `ok` (1/0), `detail` |

Integrity rules: a seat has at most one open term at a time. An unoccupied seat is a vacancy (party 0).
`sum(seats active at date) == bodies.seats`. Body ids are 0 = US Senate, 1 = US House, 2–100 = the 99 state
chambers (alphabetical by state, upper before lower; NE unicameral), 101–137 = courts (37), 138–197 = city council / mayor pairs
(council b even, its mayor b+1): 138–187 = the first 25 cities in Census population order, 188–197 = Indianapolis,
San Francisco, Nashville, DC, Louisville (appended 2026-10-18 so earlier ids did not shift). Integer `b` ids may shift when bodies are added or removed; pin to `key`.

## Body keys (stable; pin to these, not to `b`)

Keys are derived deterministically from source identifiers and never from row order, so a rebuild yields the same strings
(verified: a second full build reproduced `bodies.csv` keys and base tables byte-for-byte).

| body | key grammar | example |
|---|---|---|
| US Senate / House | `us-senate`, `us-house` | |
| state chamber | `us-{st}-{senate\|house\|legislature}` (NE = `us-ne-legislature`) | `us-pa-house` |
| state high court | `us-{st}-supreme-court`, `us-{st}-court-of-criminal-appeals` | `us-tx-court-of-criminal-appeals` |
| city council | `us-{st}-{place-slug}-{body-slug}`; `{body-slug}` = `city-council` unless the body has another name | `us-ny-new-york-city-council` |
| consolidated city-county / metro council | same grammar, `{body-slug}` = `city-county-council`, `board-of-supervisors`, `metro-council` | `us-in-indianapolis-city-county-council`, `us-ca-san-francisco-board-of-supervisors`, `us-tn-nashville-davidson-metro-council`, `us-ky-louisville-jefferson-county-metro-council` |
| Council of the District of Columbia | `us-dc-washington-council` (`{st}` = dc, place = "Washington city", `{body-slug}` = `council`) | repo entity `chamber:dc-council` (kind dc_council) |
| mayor | `us-{st}-{place-slug}-mayor` | `us-ok-oklahoma-city-mayor`, `us-dc-washington-mayor` (repo entity `state:11`) |

`{st}` = lowercase USPS code. `{place-slug}` = Census place NAME with the trailing LSAD word and "(balance)" removed ("Oklahoma City city" ->
"Oklahoma City"; "Nashville-Davidson metropolitan government (balance)" -> "Nashville-Davidson";
"Louisville/Jefferson County metro government (balance)" -> "Louisville/Jefferson County"), NFKD-ascii, lowercased, runs of non-alphanumerics -> `-`. Seats are addressed by (`key`, `dist`, `pos`).

## City councils and mayors (`city_bodies.csv`, `city_detail.csv`)

* Scope: the 30 most populous US cities, ranked by Census Vintage 2025 place estimates (`sub-est2025.csv`, SUMLEV 162).
  `office` = city_council for every local legislature, including the consolidated city-county / metro councils
  (Indianapolis City-County Council, San Francisco Board of Supervisors, Nashville Metro Council, Louisville Metro Council)
  and the Council of the District of Columbia; `city_bodies.consolidated` describes the consolidation. No city is skipped
  (`build_meta.json:skipped_cities` = {}).
* Nashville: the vice mayor (elected countywide) presides over the Metro Council and votes only to break ties; the seat is
  kept (`dist` VM, `role` vice-mayor) and counted in `seats` = 41 (majority 21, the same as for 40). DC: the chair is
  elected at-large and is a full voting member (`dist` CHAIR, `role` chair).
* Each city has two bodies: `…-city-council` (seats = voting members) and `…-mayor` (1 seat). Where the mayor is a full voting
  council member (`mayor_role` = member: Houston, Phoenix, San Antonio, Dallas, Fort Worth, Austin, San Jose, Oklahoma City, Las Vegas)
  the council also has an ex officio seat `dist`=`MAYOR`, `role`=mayor, held by the same person; `seats`/`majority` count it.
  `tie` = presides and votes only to break ties (Chicago, Charlotte, El Paso, Portland); `none` = not a member.
* `city_bodies.csv` (`b` council, `mayor_b`, `geoid`, `entity`, `place`, `pop2025`, `census_rank`, `n_district`, `n_atlarge`,
  `n_mayor_seat`, `seat_mix` district/mixed/at-large, `partisan` 1/0, `mayor_role`, `mayor_veto`, `council_url` (official site), `bp_page`, `consolidated` (consolidated government, if any), `corrections` (where the
  official site overrides Ballotpedia: seat: Ballotpedia value -> kept value (source))).
* `city_detail.csv` (`b`,`s`): `p`, `party_label` (as listed: Democratic, Working Families, For All of Us, Nonpartisan …), `affil`
  (`ballot` = partisan election; `nonpartisan office`; `known affiliation (Ballotpedia)` for mayors in nonpartisan races), `assumed`,
  `term_ends`, `office`. `terms.party` uses the code of that label (Working Families / For All of Us -> 10 oth; unknown -> 9).
* `next_el` = next scheduled council (or mayoral) election; ISO date, or `YYYY-MM` when the day is not fixed yet; vacancy/special
  elections count (NYC D3, Seattle D5, Denver At-large B on 2026-11-03). `note` says which seats are up.
* Council-district geography is not in the repo (data-v3/geo has no place or council layers), so `seats.geoid` is empty;
  the mayor seat carries the place GEOID.
* `topics.json:city_councils` lists the council bodies and, under `mayors`, the mayor bodies.

## Exclusions (user request, 2026-10-18)

* The California, Kansas and West Virginia supreme courts are removed entirely: no body, seats, terms, court_detail,
  people, results, topics, coverage or pack records (`DROP_COURTS` in `tools/build_v3data.py`; listed in
  `build_meta.json:dropped_courts`). Court body ids were renumbered (37 courts, b 101–137).
* No court contest or result before 2017 is kept, for any court (`COURT_MIN_YEAR = 2017` in `tools/build_results.py`;
  `build_meta.json:court_min_year`). The court holder back-fill therefore starts from the 2017+ contests.
* People not referenced by any term, stored candidate row or court_detail row are dropped, and `p` is renumbered
  contiguously on every build (`people.csv` ids are not stable across rebuilds; join through `key`).

## Election results 2015–2025 (`results_*.csv`)

| file | key | columns |
|---|---|---|
| `results_contests.csv` | `c` | `key` = `{year}\|{st}\|{office}\|{district}` (repo contest_key; '' = statewide) + `\|{stage}` when stage≠general + `\|{date}` for specials; `b` body, `year`, `date`, `stage` (general, runoff, special, special_runoff, retention, primary_decided = primary decided seat/general cancelled, unopposed = cancelled, won without ballot), `kind` (candidate/retention), `office` (us_senate, us_senate_special, us_house, state_senate, state_house, state_legislature, state_supreme_court, state_court_criminal_appeals), `st`, `vintage` (map vintage of the district, e.g. cd2012/cd2016fl/cd2018pa/cd2020nc/cd2022/cd2024; leg 2012/2022/2023/2024), `district` (label in that vintage), `geoid` (only when that vintage == the repo's current geo layer), `n_up` (seats elected), `seats` (seat slots filled, `;`-separated), `link` (geo/label/class/person/surname/'' = unlinked), `total` votes, `ncand`, `src` (see results_sources.csv), `note` |
| `results_candidates.csv` | (`c`,`rank`) | `p` (people.csv), `party` code, `votes` (empty = not reported/unopposed), `pct`, `win`, `inc`, `ans` (yes/no for retention). Stored: top `n_up+1` finishers (top two in single-member races; all winners + first loser in multi-member) |
| `results_sources.csv` | `code` | source citation |
| `results_crosscheck.csv` | row | `check`, `key`, `ok`, `detail` (FEC vs Election Data, MEDSL vs FEC, winners vs congress-legislators terms, Ballotpedia vs Klarner) |
| `results_coverage.csv`, `results_coverage_body.csv` | | per year × body type × stage, and per body × year |
| `topics.json` | | app topic groups: `senate` = US Senate (b 0, primary) + all state senates + NE; offices us_senate, us_senate_special, state_senate. Also `house`, `courts` |

Senate topic join: filter `results_contests` by `office in topics.senate.offices` (or `b in topics.senate.bodies`).
US Senate seats link by (st, class); contest key matches the Election Data `data-v3/results/{year}/senate` rows.

Retention: two candidate rows `ans`=yes/no with pct; the judge is `p` on both. Winner = yes row win=1.

Back-fill (`terms.src` != snapshot): from 2016-01-01 each linked contest winner opens a term on Jan 1 after the
election (specials: election date; approx=1); an incumbent winning the first contest holds from 2016-01-01;
terms are clipped at the snapshot holder's assumed-office date. `bodies.complete_from` = first date at which every
seat has a known holder.

## Pack (client) – `holders.pack.json.gz`

```
{v, epoch:"2000-01-01", parties:[key...], sel:[key...], people:[[key,name],...],   // person id p -> people[p-1]
 bodies:[{key, st, kind, office, n, maj, unit, term, sel, t0,
          dist:[...], geoid:[...],           // indexed by seat slot
          valid:{slot:[fromDay,toDay]},      // sparse; slot active when from<=d<to
          up26:"1101-...",                   // one char per slot
          role:[...], place, entity,         // only on city bodies (role per slot; place GEOID)
          ev:[dday,seat,person,party,caucus, dday,...]}]}  // delta-coded event stream
```

`ev` is sorted by date. `dday` is the number of days since the previous event (the first is days since the epoch).
Each event *sets* the seat's state: person 0 with party 0 means vacant, and caucus 0 means "same as party". The
state at day `d` comes from replaying events while the running day is <= d. This is O(events) and needs no
index. To scrub a timeline fast, keep one cursor per body and step forward or back. Before `t0` the state is
unknown (party 9).

Results: each body also carries `res:[[dday, stage, slot|[slots]|-1, n_up, total|-1, label_if_unlinked,
[p,party,votes|-1,flags, ...]], ...]` (dday delta-coded like ev; stage 0 general,1 runoff,2 special,3 special_runoff,
4 retention,5 primary_decided,6 unopposed; flags = win + 2*inc; retention: yes row first, p = judge).
`comp` holds state compositions on Feb 1 of 2017/2019/2021/2023/2025 (only on/after complete_from).

The lite pack drops `people` and person ids: `ev` becomes 4-tuples `[dday,seat,party,caucus]`, `res` candidate tuples drop p.

## Joins with ge0r9b/us-districts (data-v3, docs/v3/SCHEMA.md)

* `bodies.key` == repo `entity_key`; `bodies.office` == repo office key (`us_house`, `state_senate`, `state_house`, …).
* `seats.geoid` == `data-v3/geo/{ushouse,senate,statehouse}.csv:geoid` == results `unit_id` with `unit_type`
  ushouse/sldu/sldl (CD = cd119 `SSDD`; at-large `SS00`). NE legislature rows use the SLDU GEOID, as the repo does.
* Contest join: `contest_key = {year}|{st}|{office}|{dist}`. Multi-member districts: rows with the same
  (`b`,`geoid`) share one contest; the top `n_up` finishers fill the slots with `pos` 1..k (`up26`=1).
* `party` codes map to the repo `party_key` and the bot's `DEM/REP/LIB/OTH` through `parties.csv`.
* House people `bioguide:X` match the inst-officeholders lane (`person_id`).

## How it plugs into the time series and the forecast

1. **History / scrub**: for date `d`, replay `ev` to get the per-seat party, then colour the seat chart. The
   majority line is `maj`. Congress is complete from 2017-01-03, which covers the 2016/2020/2024 results years.
   State chambers and courts: see `bodies.complete_from` (back-filled from 2016 results); `terms.start` keeps the date each
   current member took office.
2. **Results → seats**: after an election is certified, for each contest winner append a term (seat = slot of
   that geoid/pos, `start` = the body's swearing-in date). The previous holder's term ends the same day. Seats
   whose `up26`=0 carry over unchanged.
3. **Forecast**: projected composition = carry-over seats (up26=0) + per-contest P(win) for up26=1 seats.
   Sum the probabilities, or simulate, to get P(majority) against `maj`. Courts: retention seats (sel 5) carry
   the incumbent's `appt` party.
