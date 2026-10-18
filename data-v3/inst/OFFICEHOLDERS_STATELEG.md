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

**Start dates:** a role with no start date in OpenStates is kept and flagged as `start date not recorded`. That applies mostly to SC (32) and AL (13).

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
