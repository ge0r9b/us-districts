# State legislature officeholders (v3; institutions lane)

These files are built by `tools/inst_officeholders_stateleg.py`, following OFFICEHOLDERS_PLAN.md step 2. They are v3 only: nothing in v2 loads them.

| File | Rows | Content |
|---|---|---|
| `officeholders_stateleg_current.csv` | 7323 | Members serving on Oct 18, 2026 (retrieval date). 7266 are joined and 57 have `no_v3_unit`. |
| `officeholders_stateleg_2024.csv` | 7348 | 2024 vintage: the chambers serving on 2025-04-01, after the Nov 2024 elections. LA, MS, NJ and VA hold odd-year elections, so their rows are the 2023-elected members who were serving then. 7289 are joined and 59 have `no_v3_unit`. |

**Source:** OpenStates people (github.com/openstates/people, commit `15d033692387`, 2026-10-15T16:23:44-05:00), CC0 1.0. Every row cites its YAML file at that commit (`source_url`) and the file's sha256. It also gives the official legislature URL that OpenStates lists for the person (`upstream_url`), when there is one.

The plan names the official legislature rosters first. Those rosters (50 different formats) were **not fetched this round**, so every row is OpenStates fallback and says so in `note`. Swapping each state over to its official roster is the open item.

**Join:** by district label to `data-v3/geo/senate.csv` and `statehouse.csv` (TIGER 2024 SLDU/SLDL, `unit_vintage` sldu2024/sldl2024). Names of people are never used. Both vintages use the 2024 plans.
- Labels are normalized: case, punctuation, words like "District", "Senatorial" and "and", and leading zeros.
- **Idaho:** House seats A/B go into `seat`, e.g. 10A means district 10, seat A.
- **Massachusetts:** "Barnstable, Dukes and Nantucket" = TIGER "Cape and Islands District" (25D40). It is the only Senate district containing Dukes and Nantucket counties.
- **Nebraska:** the unicameral joins to `senate.csv`.

**Why April 1, 2025 for the 2024 snapshot:** OpenStates closes many outgoing members' roles on 2025-02-03, the date its scrapers saw the change. A February date would double-count seats, as it did for 17 Nebraska districts and 3 Missouri duplicate person records. On Apr 1, no single-member unit has two members.

**Start dates:** a role with no start date in OpenStates is kept and flagged as `start date not recorded`. That applies to 87 rows in the 2024 file, mostly SC (33) and AL (13).

**`no_v3_unit`:**
- **Maine:** the tribal representatives (Passamaquoddy Tribe, Houlton Band of Maliseet Indians) have no district.
- **New Hampshire:** the labels that aren't among the 164 TIGER 2024 SLDL districts: Belknap 8, Carroll 7–8, Cheshire 15–18, Coos 7 and others. Those are the NH House's overlay (floterial) districts. TIGER's 164 units don't include them.

**Units with no member:** the current file reflects vacancies, or gaps in OpenStates. The 2024 snapshot reflects vacancies on Apr 1, 2025, or OpenStates history gaps (a member's role missing in `retired/`). These are listed per state below and not filled.

## Coverage per state

| State | Chamber | Units (TIGER 2024) | Current: members / units filled | 2024 (Apr 1, 2025): members / units filled | Labels with no v3 unit | Units with no member (current; 2024) |
|---|---|---|---|---|---|---|
| Alabama | upper | 35 | 35 / 35 | 34 / 34 |  | none; 01005 |
| Alabama | lower | 105 | 105 / 105 | 103 / 103 |  | none; 01011, 01013 |
| Alaska | upper | 20 | 20 / 20 | 20 / 20 |  | none; none |
| Alaska | lower | 40 | 40 / 40 | 38 / 38 |  | none; 02026, 02029 |
| Arizona | upper | 30 | 30 / 30 | 30 / 30 |  | none; none |
| Arizona | lower | 30 | 60 / 30 | 60 / 30 |  | none; none |
| Arkansas | upper | 35 | 33 / 33 | 35 / 35 |  | 05001, 05018; none |
| Arkansas | lower | 100 | 99 / 99 | 100 / 100 |  | 05008; none |
| California | upper | 40 | 39 / 39 | 40 / 40 |  | 06010; none |
| California | lower | 80 | 79 / 79 | 80 / 80 |  | 06003; none |
| Colorado | upper | 35 | 35 / 35 | 35 / 35 |  | none; none |
| Colorado | lower | 65 | 64 / 64 | 64 / 64 |  | 08032; 08033 |
| Connecticut | upper | 36 | 36 / 36 | 36 / 36 |  | none; none |
| Connecticut | lower | 151 | 151 / 151 | 150 / 150 |  | none; 09113 |
| Delaware | upper | 21 | 21 / 21 | 21 / 21 |  | none; none |
| Delaware | lower | 41 | 41 / 41 | 41 / 41 |  | none; none |
| Florida | upper | 40 | 39 / 39 | 38 / 38 |  | 12039; 12014, 12015 |
| Florida | lower | 120 | 116 / 116 | 118 / 118 |  | 12055, 12078, 12113, 12116; 12003, 12032 |
| Georgia | upper | 56 | 55 / 55 | 56 / 56 |  | 13012; none |
| Georgia | lower | 180 | 180 / 180 | 180 / 180 |  | none; none |
| Hawaii | upper | 25 | 25 / 25 | 25 / 25 |  | none; none |
| Hawaii | lower | 51 | 51 / 51 | 50 / 50 |  | none; 15036 |
| Idaho | upper | 35 | 35 / 35 | 35 / 35 |  | none; none |
| Idaho | lower | 35 | 70 / 35 | 70 / 35 |  | none; none |
| Illinois | upper | 59 | 59 / 59 | 59 / 59 |  | none; none |
| Illinois | lower | 118 | 118 / 118 | 117 / 117 |  | none; 17118 |
| Indiana | upper | 50 | 50 / 50 | 50 / 50 |  | none; none |
| Indiana | lower | 100 | 100 / 100 | 100 / 100 |  | none; none |
| Iowa | upper | 50 | 49 / 49 | 50 / 50 |  | 19011; none |
| Iowa | lower | 100 | 99 / 99 | 100 / 100 |  | 19038; none |
| Kansas | upper | 40 | 40 / 40 | 40 / 40 |  | none; none |
| Kansas | lower | 125 | 125 / 125 | 124 / 124 |  | none; 20070 |
| Kentucky | upper | 38 | 38 / 38 | 37 / 37 |  | none; 21018 |
| Kentucky | lower | 100 | 100 / 100 | 100 / 100 |  | none; none |
| Louisiana | upper | 39 | 38 / 38 | 39 / 39 |  | 22014; none |
| Louisiana | lower | 105 | 103 / 103 | 103 / 103 |  | 22077, 22092; 22045, 22067 |
| Maine | upper | 35 | 35 / 35 | 35 / 35 |  | none; none |
| Maine | lower | 151 | 153 / 151 | 152 / 151 | Houlton Band of Maliseet Indians, Passamaquoddy Tribe | none; none |
| Maryland | upper | 47 | 47 / 47 | 47 / 47 |  | none; none |
| Maryland | lower | 71 | 141 / 71 | 140 / 70 |  | none; 2427A |
| Massachusetts | upper | 40 | 40 / 40 | 40 / 40 |  | none; none |
| Massachusetts | lower | 160 | 157 / 157 | 157 / 157 |  | 25042, 25074, 25075; 25012, 25029, 25075 |
| Michigan | upper | 38 | 38 / 38 | 37 / 37 |  | none; 26035 |
| Michigan | lower | 110 | 110 / 110 | 110 / 110 |  | none; none |
| Minnesota | upper | 67 | 67 / 67 | 66 / 66 |  | none; 27006 |
| Minnesota | lower | 134 | 133 / 133 | 134 / 134 |  | 2721A; none |
| Mississippi | upper | 52 | 51 / 51 | 50 / 50 |  | 28034; 28018, 28045 |
| Mississippi | lower | 122 | 120 / 120 | 120 / 120 |  | 28070, 28077; 28023, 28082 |
| Missouri | upper | 34 | 33 / 33 | 34 / 34 |  | 29010; none |
| Missouri | lower | 163 | 155 / 155 | 162 / 162 |  | 29029, 29095, 29099, 29110, 29114, 29149, 29159, 29160; 29095 |
| Montana | upper | 50 | 50 / 50 | 50 / 50 |  | none; none |
| Montana | lower | 100 | 100 / 100 | 100 / 100 |  | none; none |
| Nebraska | legislature | 49 | 49 / 49 | 49 / 49 |  | none; none |
| Nevada | upper | 21 | 21 / 21 | 21 / 21 |  | none; none |
| Nevada | lower | 42 | 42 / 42 | 42 / 42 |  | none; none |
| New Hampshire | upper | 24 | 24 / 24 | 24 / 24 |  | none; none |
| New Hampshire | lower | 164 | 382 / 160 | 398 / 164 | Belknap 8, Carroll 7, Carroll 8, Cheshire 15, Cheshire 16, Cheshire 17, Cheshire 18, Coos 7 … (39) | 33201, 33306, 33409, 33722; none |
| New Jersey | upper | 40 | 40 / 40 | 40 / 40 |  | none; none |
| New Jersey | lower | 40 | 80 / 40 | 80 / 40 |  | none; none |
| New Mexico | upper | 42 | 42 / 42 | 42 / 42 |  | none; none |
| New Mexico | lower | 70 | 68 / 68 | 70 / 70 |  | 35037, 35041; none |
| New York | upper | 63 | 62 / 62 | 63 / 63 |  | 36012; none |
| New York | lower | 150 | 150 / 150 | 150 / 150 |  | none; none |
| North Carolina | upper | 50 | 50 / 50 | 50 / 50 |  | none; none |
| North Carolina | lower | 120 | 120 / 120 | 120 / 120 |  | none; none |
| North Dakota | upper | 47 | 47 / 47 | 47 / 47 |  | none; none |
| North Dakota | lower | 48 | 94 / 48 | 94 / 48 |  | none; none |
| Ohio | upper | 33 | 32 / 32 | 33 / 33 |  | 39013; none |
| Ohio | lower | 99 | 99 / 99 | 99 / 99 |  | none; none |
| Oklahoma | upper | 48 | 47 / 47 | 47 / 47 |  | 40024; 40008 |
| Oklahoma | lower | 101 | 99 / 99 | 99 / 99 |  | 40077, 40099; 40071, 40074 |
| Oregon | upper | 30 | 30 / 30 | 30 / 30 |  | none; none |
| Oregon | lower | 60 | 60 / 60 | 59 / 59 |  | none; 41026 |
| Pennsylvania | upper | 50 | 50 / 50 | 49 / 49 |  | none; 42036 |
| Pennsylvania | lower | 203 | 203 / 203 | 202 / 202 |  | none; 42035 |
| Rhode Island | upper | 38 | 38 / 38 | 38 / 38 |  | none; none |
| Rhode Island | lower | 75 | 74 / 74 | 75 / 75 |  | 44031; none |
| South Carolina | upper | 46 | 46 / 46 | 46 / 46 |  | none; none |
| South Carolina | lower | 124 | 124 / 124 | 123 / 123 |  | none; 45050 |
| South Dakota | upper | 35 | 35 / 35 | 35 / 35 |  | none; none |
| South Dakota | lower | 37 | 70 / 37 | 70 / 37 |  | none; none |
| Tennessee | upper | 33 | 33 / 33 | 33 / 33 |  | none; none |
| Tennessee | lower | 99 | 98 / 98 | 99 / 99 |  | 47084; none |
| Texas | upper | 31 | 30 / 30 | 31 / 31 |  | 48022; none |
| Texas | lower | 150 | 148 / 148 | 150 / 150 |  | 48001, 48093; none |
| Utah | upper | 29 | 29 / 29 | 29 / 29 |  | none; none |
| Utah | lower | 75 | 74 / 74 | 75 / 75 |  | 49016; none |
| Vermont | upper | 16 | 30 / 16 | 30 / 16 |  | none; none |
| Vermont | lower | 109 | 150 / 109 | 150 / 109 |  | none; none |
| Virginia | upper | 40 | 40 / 40 | 39 / 39 |  | none; 51015 |
| Virginia | lower | 100 | 99 / 99 | 100 / 100 |  | 51020; none |
| Washington | upper | 49 | 49 / 49 | 49 / 49 |  | none; none |
| Washington | lower | 49 | 98 / 49 | 97 / 49 |  | none; none |
| West Virginia | upper | 17 | 34 / 17 | 34 / 17 |  | none; none |
| West Virginia | lower | 100 | 100 / 100 | 100 / 100 |  | none; none |
| Wisconsin | upper | 33 | 33 / 33 | 33 / 33 |  | none; none |
| Wisconsin | lower | 99 | 99 / 99 | 99 / 99 |  | none; none |
| Wyoming | upper | 31 | 31 / 31 | 31 / 31 |  | none; none |
| Wyoming | lower | 62 | 62 / 62 | 62 / 62 |  | none; none |

## Official rosters (pass of 2026-10-18), via `tools/inst_stateleg_official.py`

These states' chambers now come from official legislature rosters in `officeholders_stateleg_current.csv`, which replace the OpenStates rows. The raw files are in `inst-raw/rosters/`, and `SOURCES.txt` gives each file's URL and sha256. `person_id` keeps the OpenStates id when the same last name sits in the same unit. Where the official page lists no party (TX, NY Assembly), the party and term_start come from that OpenStates person, as the row's note says. The `official_check` column is `official` on these rows and `openstates_fallback` on all others.

| State | Chambers | Official serving | OpenStates current | Joined | Diffs | Notes |
|---|---|---|---|---|---|---|
| Texas | H+S | 178 | 178 | 178 | 2 | 89th Legislature member pages. 6 pages show no district: 5 members left during the 89th, plus the Lt. Gov. |
| New Hampshire | H+S | 390 | 406 | 342 | 23 | 48 floterial seats are `no_v3_unit_floterial` |
| Pennsylvania | H+S | 253 | 253 | 253 | 0 | |
| Massachusetts | H+S | 196 | 197 | 196 | 2 | 194th General Court, checked against the current member pages |
| Minnesota | H+S | 203 | 200 | 203 | 3 | Unit 2721A is filled. OpenStates left it empty |
| Vermont | H+S | 180 | 180 | 180 | 25 | Mostly the party label order and Independent vs R |
| Missouri | House | 155 | 155 | 155 | 0 | 8 official vacancies |
| New York | Assembly | 150 | 150 | 150 | 0 | The source page lists no party |
| California | Assembly | 79 | 79 | 79 | 0 | District 03 is vacant |

These chambers stay on the OpenStates fallback:
- **NY Senate:** nysenate.gov returns 403 (a Cloudflare challenge).
- **CA Senate:** senate.ca.gov builds its member list client-side, so there is no machine-readable list.
- **MO Senate:** the senator listing URL returned 404.
- **All other states:** they were not attempted this round, so they stay on OpenStates (CC0).

Join counts for the current file:
- Before: 7,323 rows, 7,266 joined.
- After: 7,309 rows, 7,259 joined, 48 `no_v3_unit_floterial` (NH) and 2 `no_v3_unit_tribal` (ME).
- Why the counts went down: official vacancies (MO 8, CA 1) and NH former members are no longer counted as serving.

The 2024 file is unchanged in its rows: 7,348 rows, 7,289 joined, 58 floterial and 1 tribal. The official rosters are undated, so they cannot assign 2025-04-01 membership. Because of that, no empty 2024 units were filled. The rows are cross-checked instead:
- 957 `confirmed_session_roster`;
- 822 `confirmed_current_roster`;
- 5 `confirmed_session_roster_name_only` (TX departed members);
- 39 `not_in_official_roster`.

All 73 diffs are in `stateleg_official_diffs.csv`:
- 32 OpenStates members are not in the official roster;
- 18 2024 OpenStates members are not in the session roster;
- 14 official members are not in the OpenStates unit;
- 8 party differences;
- 1 official member sits in a unit that OpenStates leaves empty.

Special cases, which are never joined:
- **NH House floterials:** labels that are not among the 164 TIGER 2024 SLDL base districts (RSA 662:5).
- **Maine tribal representatives:** non-voting seats with no district. They appear as `no_v3_unit_tribal` in both files.

## Official rosters, batch 2 (2026-10-18): ME, MD, CT, MS, NC, SC, KS, FL Senate, CA Senate

Parsers are in `tools/inst_stateleg_parsers2.py`, which `inst_stateleg_official.py` imports. They use the same method, cross-check and diffs file as batch 1.

| State | Source | Official serving | OpenStates current | Joined | Diffs |
|---|---|---|---|---|---|
| ME | House district listing (deceased/resigned marked) + 132nd Senate list | 188 | 188 | 186 | 4 |
| MD | MGA member index, 2026 session | 187 | 188 | 187 | 2 |
| CT | CGA `LegislatorDatabase.csv` | 187 | 187 | 187 | 0 |
| MS | billstatus member XML, term 2024-2027 | 172 | 171 | 172 | 15 |
| NC | NCGA member tables (resigned/appointed marked) | 170 | 170 | 170 | 2 |
| SC | scstatehouse member lists | 170 | 170 | 170 | 0 |
| KS | KLISS API v13 | 165 | 165 | 165 | 0 |
| FL Senate | flsenate.gov senator list | 39 | 39 | 39 | 1 |
| CA Senate | senate.ca.gov roster | 40 | 40 | 40 | 0 |

ME notes:
- The two ME tribal seats appear only as seat numbers in the official list. They take the tribe label OpenStates gives the same person, and their join status is `no_v3_unit_tribal`.

MS notes:
- MS member XML carries no in-office dates.
- Senate District 44 lists two members, Polk and Johnson, both shown as "present". The tool keeps the one OpenStates lists as current (Johnson), and the row note records this.
- MS units that OpenStates leaves empty and the official list fills: House 70 and 77, Senate 34.

Correction to batch 1: senate.ca.gov/senators is rendered on the server, so the CA Senate has switched to its official list.

How the official sources were reached:
- ilga.gov, cga.ct.gov and billstatus.ls.state.ms.us send an incomplete TLS chain. Each was fetched with the system CA store plus the Mozilla CCADB public intermediate list (`inst-raw/rosters/ca_bundle_plus_aia.pem`). Verification stayed on throughout.

Party comparison:
- Party labels are normalized before comparing: U, Unenrolled, NPA and "No Party Affiliation" all count as Independent, and DFL counts as Democratic.

Still on the OpenStates fallback, with reasons (also in `stateleg_official_summary.json` under `fallback_reasons`):
- **GA, both chambers:** legis.ga.gov is an Angular app. Its member API returns 401 without the app's session token, and no CSV, XML or PDF roster was found.
- **FL House:** myfloridahouse.gov returns a WAF "Request Rejected" page. That is a block, and it was not routed around.
- **IL, both chambers:** ilga.gov returned 503 to every member-list request this round.
- **NY Senate:** 403 (Cloudflare). The official Open Legislation API needs an API key, which requires an account sign-up, and that was not done.
- **MO Senate:** the listing returns 404.

Join counts for the current file, from the official-roster step (before the vacant-row pass below):
- After batch 1: 7,309 rows, 7,259 joined.
- After batch 2: 7,318 rows, 7,268 joined.
- The vacant-row pass below then brings the rows to 7,361.

Diffs: 88 in total. 41 are OpenStates members missing from the official roster, 18 are official members sitting in a different unit from OpenStates, 18 are people in the 2024 file missing from the session roster, 7 are party differences and 4 are official members in units OpenStates leaves empty.

## Person IDs (v3 spec, 2026-10-18), via `tools/inst_persons.py`

This step runs last, after the house, stateleg and official tools. It edits all five officeholder files in place and is idempotent. Each row's `person_id` is `scheme:id`, with one canonical ID per person, chosen in this order:

1. `bioguide:<ID>`;
2. `ocd-person:<uuid>` (the old `ocd-person/<uuid>` form is normalized to this);
3. `<st>-leg:<official id>`.

Rules:
- **Bioguide comes only from OpenStates' own person records,** from `other_identifiers` with scheme `bioguide`, on the same ocd-person ID or on an ID OpenStates merged into it. There is no name matching across levels.
  - Result: 0 state legislators are bioguide-canonical. In this OpenStates commit, no state-legislature person record carries a bioguide ID. Only 1 ocd-person ID appears in both `data/us` and a state directory, and that person is not in our state-legislature files.
- **Bare official IDs** are the official-only members. Each one is matched to an OpenStates person only when exactly one OpenStates person has a role (of any date) in the same state, chamber and district label, with the same last name and the same first initial. Every match is logged in `person_id_matches.csv`.
  - 12 were matched: MN 3, MS 7, NH 2.
  - 10 were kept as `<st>-leg:`: VT 9, TX 1. Each of these had 0 candidates.
- **`persons.csv`** has the columns person_id, bioguide, ocd_person, official_ids, name, sources and aliases.
  - It has 8,186 rows: 601 bioguide, 7,575 ocd-person, 9 vt-leg and 1 tx-leg.
  - `aliases` holds 957 former or alternate IDs, spread over 947 persons. These are mostly IDs that OpenStates merged (scheme `openstates`), plus the 12 matched `<st>-leg` IDs. No previously published ID is orphaned.
  - Every `person_id` in all five files is in `persons.csv`.
- **Vacancies:** `person_id` is empty and status is `vacant`.
  - Official-roster vacancies (MO House 8, CA Assembly 1, FL Senate 1) are written as vacant rows.
  - Every data-v3 geo unit with no member row gets a vacant row: 43 in the current file and 36 in the 2024 file.
  - A multi-member unit that is only partly vacant is marked only where the official roster says so, because the v3 geo files carry no seat counts.
- **Dates:** a `date_flags` column is now in every officeholder file. `term_start_missing` means a non-vacant row has no start date. `term_end_open` means there is no end date in the source, which is normal for serving members.
  - State legislature, current file: 105 `term_start_missing` and 7,302 `term_end_open`.
  - State legislature, 2024 file: 87 `term_start_missing` and 7,076 `term_end_open`.
  - Official rows now carry the matched OpenStates role's `term_end` where OpenStates has one.

## Official rosters, batch 3 (2026-10-18): IA, MI, WA, OK House, LA, ND

| State | Source | Official serving | OpenStates current | Diffs |
|---|---|---|---|---|
| IA | legis.iowa.gov lists, 91st GA | 148 | 148 | 0 |
| MI | house.mi.gov AllRepresentatives + senate.michigan.gov all-senators | 147 | 148 | 1 |
| WA | WSL web services `GetSponsors`, 2025-26 | 147 | 147 | 0 |
| OK House | okhouse.gov representatives | 99 + 2 vacant | 99 | 2 |
| LA | house.louisiana.gov + senate.la.gov full-info lists | 141 + 3 vacant | 141 | 2 |
| ND | ndlegis.gov 69th Assembly, members by district | 141 | 141 | 0 |

Source notes:
- **IA:** members who have left show their service dates on the list. Their start and end dates are used: Dunwell in House 38 left on 2026-10-05, and Garrett in Senate 11 left on 2026-06-08. Both seats are now vacant rows.
- **IA, WA, ND:** these lists carry no in-office status. Where a unit lists more people than it has seats (the seat count comes from OpenStates' current rows for that unit), the tool keeps the person OpenStates lists as current, and the row note says so.
- **MI Senate:** the member list is a JSON array embedded in the page's HTML.

Still on the OpenStates fallback, with reasons (also in `fallback_reasons`):
- **IN, both chambers:** iga.in.gov is built in the browser. Its data API needs a registered key, and there is no other export.
- **MT, both chambers:** the api.legmt.gov legislators endpoint answers, but its records don't give a consistent current roster. The 69th and 70th legislature tags are mixed with start/end dates, only 119 of 150 seats fall under the 69th tag, and there is a placeholder district 999.
- **OK Senate:** Sucuri/Cloudproxy challenge, a block.
- **AL, both chambers:** ALISON is built in the browser and has no roster export.
- **VA, both chambers:** the new LIS is built in the browser, and legacy LIS says the 2026 member pages don't exist.

Totals for the current file after batch 3:
- 7,361 rows: 7,307 serving and 54 vacant.
- 7,257 serving rows are joined, plus 48 NH floterial and 2 ME tribal rows.
- 3,938 rows come from official rosters and 3,384 from the OpenStates fallback. The other 39 are vacant rows that the persons step added for units with no member in either source.
- 94 diffs.
- `persons.csv` has 8,188 rows and 957 aliases. 12 official IDs were matched to an OpenStates person and 12 were kept as `<st>-leg:` (VT 9, TX 1, OK 1, LA 1). The OK and LA cases are name changes: Alonso → Alonso Sandoval and Hennessy → Hennessy Dickerson. They are logged in `person_id_matches.csv`.

## Official rosters, batch 4 (2026-10-18): KY, WV, AR, WI, OH, NJ, NM, ID, SD

| State | Source | Official serving | Diffs |
|---|---|---|---|
| KY | apps.legislature.ky.gov members by district | 138 | 0 |
| WV | wvlegislature.gov House + Senate rosters | 134 | 0 |
| AR | arkleg.state.ar.us 2025 member lists (no party, no status) | 132 | 3 not asserted |
| WI | docs.legis.wisconsin.gov 2025 Assembly + Senate | 132 | 0 |
| OH | legislature.ohio.gov directories | 130 + 2 vacant | 1 |
| NJ | njleg roster (JSON embedded in the page) | 120 | 0 |
| NM | nmlegis.gov legislator lists | 110 | 0 |
| ID | legislature.idaho.gov 2026 membership | 105 | 0 |
| SD | sdlegislature.gov API, SessionMembers session 71 (InactiveDate used for status) | 105 | 0 |

**New rule, applied to every undated session roster (AR, IA, MS, ND, TX, WA):** a member listed in a unit where OpenStates has nobody current is no longer asserted as serving. Such people may have left, and filling those units would be a guess. The row is not written, and the case is logged as diff kind `session_roster_member_not_asserted_unit_empty_in_openstates`. There are 6 such cases:
- AR: McCollum (House 8), Dismang (Senate 18), Gilmore (Senate 1).
- MS: Brown (House 70), Wallace (House 77), Barnett (Senate 34).

This replaces the batch 2 MS fills, which were made under the older rule.

Totals for the current file after batch 4:
- 7,361 rows: 7,303 serving and 58 vacant. 41 of the vacant rows are for units with no member in either source.
- 7,253 serving rows are joined, plus 48 NH floterial and 2 ME tribal rows.
- 5,043 rows come from official rosters and 2,277 from the OpenStates fallback.
- 98 diffs.
- `persons.csv` has 8,188 rows and 954 aliases.

## Official rosters, batch 5 (2026-10-18): TN, UT, CO, AZ, OR, NV, AK, NE, MO Senate, IL

| State | Source | Official serving | Diffs |
|---|---|---|---|
| TN | wapp.capitol.tn.gov LegislatorInfo directory, 114th GA | 130 | 1 |
| UT | le.utah.gov roster | 103 | 7 (3 seats with different people; 1 not asserted) |
| CO | leg.colorado.gov legislators | 99 | 2 not asserted (HD 32) |
| AZ | azleg.gov member rosters, 57th Legislature | 90 | 0 |
| OR | Oregon Legislature OData API, session 2026R1 | 90 | 0 |
| NV | leg.state.nv.us current Assembly + Senate | 63 | 0 |
| AK | akleg.gov House + Senate pages | 60 | 0 |
| NE | nebraskalegislature.gov senator list (nonpartisan) | 49 | 0 |
| MO Senate | senate.mo.gov senators | 33 | 0 |
| IL | ilga.gov House + Senate member lists, 104th GA | 177 | 0 |

Source notes:
- **IL:** ilga.gov answered on retry. Its list includes former members, so it is handled as an undated session list. For example, Paul Jacobs is listed under both House 118 and Senate 59, and the tool keeps the person OpenStates lists as current.
- **Undated session lists:** UT, CO and AZ are handled the same way.
- **Name parsing:** "Last, Jr., First" is now parsed correctly.
- **Party comparison:** "Not Affiliated" counts as Independent.

### Final state of the swap

Switched to official rosters: 41 states, 78 chambers (37 states with both chambers, plus NE and one chamber each in FL, NY and OK). Both chambers in:

AK, AR, AZ, CA, CO, CT, IA, ID, IL, KS, KY, LA, MA, MD, ME, MI, MN, MO, MS, NC, ND, NH, NJ, NM, NV, OH, OR, PA, SC, SD, TN, TX, UT, VT, WA, WI and WV.

Also switched:
- NE, its single chamber;
- one chamber each in FL (Senate), NY (Assembly) and OK (House).

Still on the OpenStates fallback, with reasons (`fallback_reasons` in `stateleg_official_summary.json`):
- **AL, DE, GA, IN, MT, RI, VA, WY:** both chambers. There is no official machine-readable roster that can be fetched without the sites' internal app endpoints, keys or session tokens. MT is the exception: its API answers but is internally inconsistent.
- **HI:** Cloudflare challenge.
- **FL House:** WAF block.
- **OK Senate:** Sucuri block.
- **NY Senate:** Cloudflare, and the Open Legislation API needs a key.
- None of these blocks was worked around.

Current file, before and after:
- **Before the swap (OpenStates only):** 7,323 rows, all serving, of which 7,266 joined.
- **After:** 7,361 rows. 7,302 are serving, and 7,252 of those are joined, plus 48 NH floterial and 2 ME tribal rows. The other 59 rows are vacant.
- **Official rows:** 5,937 now come from official rosters, 1,382 stay on the OpenStates fallback, and 42 are vacant rows the persons step added for units with no member in either source.

The 2024 file has 7,384 rows: 7,348 serving at 2025-04-01 and 36 vacant. Its cross-check against the official rosters:
- 3,387 confirmed in the current roster;
- 2,431 confirmed in the session roster;
- 5 confirmed by name only;
- 142 not in the official roster, mostly people who have since left;
- 1,383 still on the OpenStates fallback.

`stateleg_official_diffs.csv` has 120 diffs:
- 49 OpenStates members not in the official roster;
- 31 people in the 2024 file not in the session roster;
- 23 official members sitting in a different unit from OpenStates;
- 9 not asserted (an undated session roster lists someone in a unit where OpenStates has nobody current);
- 7 party differences;
- 1 official member in a unit OpenStates leaves empty.

`persons.csv` has 8,185 rows:
- 601 bioguide, 7,572 ocd-person, 9 vt-leg, 1 tx-leg, 1 ok-leg and 1 la-leg;
- 957 aliases, spread over 947 persons;
- 0 state legislators are bioguide-canonical.

## v3 format (step 4, `tools/inst_v3format.py`)

Rows are keyed **chamber entity + unit + seat**: `entity_id` is now the chamber entity of `entities.csv` (`us-house`,
`chamber:<ab>-upper|lower`; old slug in `entity_id_legacy`), the unit is `unit_layer` + `unit_geoid` + `unit_vintage`
(TIGER year; the old `cd119`/`sldl2024` token is in `unit_plan`), and `seat` carries the source's seat label (Idaho House A/B).
Step 5 (`tools/inst_oh_sources.py`) normalizes provenance into `sources.csv`: rows carry `source_id`; `source`, `license`,
`retrieved_at`, `source_commit` moved there, the old record-id column `source_id` is now `source_record_id`. Columns and flags: README_OFFICEHOLDERS.md.
