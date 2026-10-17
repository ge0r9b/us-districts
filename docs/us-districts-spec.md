# US Districts: product specification (handoff for a full-stack rebuild)

| | |
|---|---|
| **App** | US Districts, a map and results viewer for US elections |
| **Live** | https://ge0r9b.github.io/us-districts/v2/ (build 202610141498 at the time of writing) |
| **Source** | github.com/ge0r9b/us-districts. Main file `v2/index.html`. Coverage and licenses in `v2/data/COVERAGE.md` |
| **Spec date** | Oct 14, 2026 |
| **Purpose** | A handoff spec that a coding assistant (Cursor / Grok Build) can use to rebuild the app as a full-stack app on Supabase |

**How to read this document**

- **Current** means the behavior is in the code that is live now (commit `5753b6d`, build 1498).
- **In progress** means the code exists only in the uncommitted working copy (build 1499) and is not live yet. As of this spec that covers "List all…", sort, Canadian provinces, and the shared name/alias table for the institution search.
- **Rule** means an approved product rule. A rule may not be fully implemented yet. Gaps are listed in section 11.
- **(unverified)** means I read it in the code but did not test it in a browser.

---

## 1. Overview and goals

US Districts shows US presidential results (2020 and 2024) on a map, in a list and in charts, across many boundary layers: country, states, counties, towns, precincts, US House districts, state senate districts, state house districts and school districts. Every result is counted within **today's** boundaries.

**Goals**

1. Answer "how did this place vote, and how did that change?" for any US geography, down to the precinct.
2. Mobile first (iOS Safari), and it also works on desktop.
3. Never fabricate data. Estimates are marked, and gaps stay gray.
4. Lay the groundwork for a commercial product: live user votes (polls), and later institutions with no map region (companies, brands, subsidiaries) and international governments.

**Non-goals for the static app:** user accounts, live voting, property-location directories, and commercial licensing of the current data.

## 2. Users and platforms

| Item | Current | Future |
|---|---|---|
| Users | Public, anonymous | First, fewer than 10 test users for live votes and institutions |
| Primary device | iPhone, iOS Safari (portrait) | Same |
| Secondary | Desktop browsers (wide layouts, full-width charts) | Same |
| Hosting | GitHub Pages (static, 1 GB site limit) | Supabase (Postgres + PostGIS + Storage + Auth) plus a front end |
| Stack | One HTML file, Leaflet 1.x (`lib/leaflet.js`), canvas rendering, data files loaded as JS (`window.__x(...)` script tags) | Split app (section 12) |
| External services | Esri World Street Map tiles; US Census Geocoder (JSONP) and OpenStreetMap Nominatim for addresses | Same, or replacements that allow commercial use (section 11) |

iOS details that must survive the rebuild: inputs use `font-size ≥ 16px` so the page does not zoom; one focusable field at a time, so the form accessory bar does not appear; the field is focused inside `touchend` so the keyboard opens; the page stays pinned against visual-viewport scroll; and double-tap is detected by hand, because Safari does not deliver `dblclick` reliably.

## 3. Concept glossary

| Term | Meaning |
|---|---|
| **Entity** | Anything that can be selected: country, state/province, county, town (town, township, city, borough, village), precinct, district. Later also a company, brand or subsidiary. |
| **Institution** | A sovereign or incorporated entity: a sovereign government (country, state/province) or an incorporated one (county, city, town, township, borough), or later an organization. It may have **no region** on the map. |
| **Geography / boundary** | A polygon. Many entities are both a geographic area and a government: sovereign (country, state/province) or incorporated (county, city, town, township, borough). |
| **District type / layer type** | US House, State senate, State house, School districts. Selected with the Layers button. "None" is the default county/precinct view. |
| **Topic** | What the numbers are about, such as "President". It comes from a generic list (`OFFICES` now, the server later). |
| **Answer** | One option in a topic, such as a nominee. It is keyed by `answerId` (`dem_nominee`, `rep_nominee`), and the candidate is a separate `candidateId`, so deltas compare the same slot across years. |
| **Year mode** | 2020, 2024, or **delta** (2020→2024 change). |
| **Format mode** | **%** (shares only) or **#** (vote counts only). |
| **Re-tabulation** | Precinct results re-counted into current district boundaries, area-weighted where precincts are split. |
| **Estimate (≈)** | A value produced by area weighting or allocation. Data rows carry the flag `est`. |
| **Coverage** | The share of districts with results. Low-coverage districts stay gray. |
| **Institution filter** | The top filter (breadcrumb bar and full-screen menu). |
| **Geo filter** | The bottom filter (the "ZIP, place, county or address" field). |

## 4. Entity model and proposed Supabase schema

### 4.1 Today (static)

| Data | File(s) | Shape |
|---|---|---|
| Lists, local geometry, cross-references | inlined in `index.html` (`PACK`, `XREF`, about 5.2 MB) | towns/places/schools/districts per state |
| State boundaries (towns, places, counties, districts) | `data/<State>.js` (50 files) | delta-encoded polygons, `SCALE=1e4` |
| County results | `data/election2024.js`, `data/election2020.js` | `{"State|County":[dem,rep,total]}` |
| Precincts 2024 / 2020 | `data/precincts2024/*.js` (51), `data/precincts2020/*.js` (40) | `[county, precinctId, dem, rep, total, polys]` plus a per-county credit |
| National layers | `v2/data/uscounties.js`, `usstates.js`, `uscd.js`, `ussldu.js`, `ussldl.js`, `ussch.js` | `[state, name, polys, a2024, a2020, "est"?]` with `a=[dem,rep,total]` |
| Town parts | `v2/data/parts/<State>.js` | county subdivisions |
| World | `countries.js` (Natural Earth bbox), `ctryshape.js` (silhouettes), `canada.js` (in progress) | |
| Alaska | `v2/data/ak.js` | official House-district totals and borough estimates |
| ZIP centroids | `data/zcta2024.js` | |

Total site size is about 176 MB without `.git`. Precincts 2024 are 59 MB and precincts 2020 are 24 MB.

### 4.2 Proposed schema (Postgres + PostGIS)

```sql
-- Everything selectable. Institutions without regions simply have no boundary row.
create table entity (
  id            uuid primary key default gen_random_uuid(),
  kind          text not null,      -- country|state|province|county|town|precinct|ushouse|senate|statehouse|school|company|brand|subsidiary
  subtype       text,               -- town|township|city|borough|village|parish|census_area...
  name          text not null,      -- canonical display name ("Pennsylvania")
  code          text,               -- ISO / FIPS / district number / precinct id
  parent_id     uuid references entity(id),   -- institution hierarchy (US > PA > county > town)
  gov_kind text not null default 'incorporated' check (gov_kind in ('sovereign','incorporated')), -- country, state, province = sovereign; county, city, town, township, borough = incorporated
  has_region    boolean not null default true,
  meta          jsonb default '{}'
);
create index on entity(parent_id); create index on entity(kind);

-- Shared names: both filters resolve through this one table (PA = Pennsylvania, USA = United States).
create table entity_alias (
  entity_id uuid references entity(id) on delete cascade,
  alias     text not null,           -- stored lowercased
  kind      text default 'abbr',     -- abbr|alt|historic
  primary key (entity_id, alias)
);
create index on entity_alias(alias);

-- Boundaries are versioned. Results always use the current version.
create table boundary (
  id         uuid primary key default gen_random_uuid(),
  entity_id  uuid references entity(id) on delete cascade,
  vintage    text not null,          -- "2024" (current), "2020"...
  is_current boolean not null default false,
  geom       geometry(MultiPolygon, 4326) not null,
  geom_simple geometry(MultiPolygon, 4326),   -- for low zoom / vector tiles
  source_id  uuid references source(id)
);
create index on boundary using gist(geom);

create table icon (
  entity_id uuid references entity(id) on delete cascade,
  style     text not null,           -- flag (institution filter) | silhouette (geo filter)
  storage_path text,                 -- Supabase Storage, or generated from geom
  primary key (entity_id, style)
);

-- Topics and answers (generic: elections now, polls later)
create table topic (
  id uuid primary key default gen_random_uuid(),
  slug text unique, label text not null,      -- "President"
  scope_entity_id uuid references entity(id), -- President -> United States (and descendants)
  kind text not null default 'election'       -- election|poll
);
create table election (                       -- one topic at one time point
  id uuid primary key default gen_random_uuid(),
  topic_id uuid references topic(id), year int, held_on date, is_static boolean default true
);
create table answer (
  id uuid primary key default gen_random_uuid(),
  topic_id uuid references topic(id),
  answer_key text not null,            -- dem_nominee | rep_nominee | other (stable across years)
  color text
);
create table candidate (
  id uuid primary key default gen_random_uuid(),
  election_id uuid references election(id), answer_id uuid references answer(id),
  full_name text, short_name text, photo_path text, photo_credit text
);

-- Results by geography and year, already re-tabulated into CURRENT boundaries
create table result (
  election_id uuid references election(id),
  entity_id   uuid references entity(id),
  answer_id   uuid references answer(id),
  votes       numeric not null,        -- numeric because area weighting gives fractions
  is_estimate boolean not null default false,  -- drives the ≈ mark
  method      text,                    -- official|whole_county|area_weighted|allocated|town_apportioned
  coverage    real,                    -- 0..1 share of votes covered
  source_id   uuid references source(id),
  primary key (election_id, entity_id, answer_id)
);
create table result_total (election_id uuid, entity_id uuid, total numeric, primary key(election_id, entity_id));

create table source (
  id uuid primary key default gen_random_uuid(),
  name text, url text, license text,   -- 'NYT C-UDA (non-commercial)', 'CC BY 4.0', 'public record'...
  commercial_ok boolean, attribution text
);

-- Next major version: live votes
create table vote (
  id uuid primary key default gen_random_uuid(),
  topic_id uuid references topic(id), answer_id uuid references answer(id),
  user_id uuid references auth.users(id), cast_at timestamptz default now(),
  entity_id uuid references entity(id)   -- resolved precinct/location, or the institution
);
```

Notes:

- Hierarchy (`parent_id`) and geography are separate on purpose: a company has a parent but no boundary, and a precinct has a boundary and a county parent.
- Delta values are computed, not stored: `margin(2024) − margin(2020)` for the same `entity_id` and `answer_key`.
- Past elections stay static. Export them as pre-built tiles or JSON in Storage/CDN; there is no need to query them live.
- Row Level Security: public read on everything except `vote`. Users insert their own votes only.

## 5. Filters

There are two filters, **separate by design**. They agree on names (section 5.3) and share no code.

### 5.1 Institution filter (top)

**What it is:** a picker for sovereign and incorporated entities. Today that means countries and states (sovereign; provinces in progress, Canada parked) and, via the geography link, counties and towns (incorporated). Later it will add companies, brands and subsidiaries, which may have no region on the map.

**Hierarchy:** All › All countries › United States › states › counties (and towns/townships/cities/boroughs, precincts). Canada › provinces and territories (in progress).

| Element | Behavior (current unless marked) |
|---|---|
| Collapsed bar | Flag icon (US flag, or a state-flag PNG) plus the breadcrumb path, kept to 32 characters or fewer (leading crumbs collapse to "…"). |
| Open (full-screen menu) | The **field** shows the selected entity with its icon. The **crumb** above it shows only the parent. The **list** shows the children. Typing filters the list (fuzzy, then exact). |
| US level | Children are the states, plus district-type rows: US House districts, State senate districts, State house districts, School districts. |
| State level | Children are the counties. Picking a county closes the menu. With a district type selected, children are that state's districts; tapping a district drills into its precincts. |
| All countries | The US plus about 200 countries (Natural Earth). Non-US countries show a plain map with no results. Canada drills into provinces (in progress). |
| Tapping **All** | Collapses the menu and shows the whole world. |
| Empty field + Enter | Goes back to the United States. Backspace in an empty field goes up a level. |
| **List all…** (in progress) | The first row at each level: List all countries / states / provinces / counties / townships (towns, cities and boroughs included) / precincts / <district type>. It lists every child in the list view with results per the other filters (topic, year, answers, format). The bar graph shows in the list. In delta mode each row shows a change-direction bar. The map shows the **total** of the listed set, one combined color, until the selection changes. Any filter change exits list-all. |
| Sort (in progress) | A mini raw sort symbol (↑↓) next to the list, with a tiny-text bubble: "High to low" / "Low to high". Default is high to low. It sorts by the selected answer's share or count; in delta mode, by the change. Rows with no data go last, in alphabetical order. |
| Search (in progress) | Ranks countries, states and provinces through the shared alias table (PA, USA, UK). |

### 5.2 Geo filter (bottom)

**What it is:** the primary geographic-boundary filter and a quick jump-to-place tool. It accepts ZIP codes, places, counties, towns, countries, provinces (in progress) and street addresses.

| Element | Behavior (current) |
|---|---|
| Collapsed field | The placeholder names what is in view ("Erie County, PA", "Near ZIP 16501"). It updates on map move. A double-tap on an area locks its name in the field. |
| Icon | Its own icon set: an off-black silhouette of the country or state, with a tiny yellow star at the county/town (or map center). A globe for All. |
| Full-screen version | The field and the globe button stay fixed at the **bottom right**, rising above the iOS keyboard (`--kb` from `visualViewport`). Results stack **upward**, like Safari's address bar (`column-reverse`). There is **no breadcrumb**. The current level appears as one row just above the field; tap it to go up. |
| Browsing (empty field) | Country › State › County › Town, with an "All of <parent>" row on top. |
| Typing | Fuzzy-ranks states, countries, counties (weighted by votes) and towns. Address-like text adds Census Geocoder suggestions after 650 ms. |
| Enter | An exact name wins, otherwise the top match. A state goes to **the state itself**. A town sets state and county first, then moves the map. An address pins the point and opens its precinct (or county). A ZIP centers on it. |
| Clearing the field | Zooms back to the institution selection (the whole US when none). |

### 5.3 How the filters correspond (rule)

- Countries, states/provinces, counties and towns correspond between the two filters because they are both a geographic area and a government (sovereign for countries/states/provinces; incorporated for counties, cities, towns, townships and boroughs). Unisearch shows two rows for each such entity: the institution row (flag for countries/states/provinces, entity icon for incorporated ones, with a type label: Country, State, County, Town, Township, Borough, City) and a Place row (territorial silhouette, tiny star for county/town, label Place). The institution row sets the institution filter; the Place row sets the geo filter. The link is **shared names** (canonical names plus one alias table), **not shared code**. Each filter keeps its own search code and icons.
- Aliases: PA = Pennsylvania, USA/US/America = United States, UK/Britain = United Kingdom, and so on.
- Typing a state abbreviation or name puts **the state first, in both filters** (current; test `tests/state_abbr_search.py`).
- Test scripts: `tests/filters-correspond.py` and `tests/institution-search.py` (Playwright, untracked, in progress).

### 5.4 Topic (title field)

| Rule | Current behavior |
|---|---|
| Topics are scoped to their entity | President applies only to the US and places inside it. Choosing another country or All clears the topic. Returning to the US restores it. |
| Generic field | Type to get suggestions from the topic list (now the `OFFICES` constant, one entry: President). Later the list comes from the server (polls). |
| Clearing | Empty + Enter shows plain boundaries with **name-only popups**. Candidates, charts and the legend are hidden. |

## 6. Map behavior

| Situation | What shows |
|---|---|
| Whole lower 48 fits on screen | Solid **statewide** shading, and statewide popups on tap |
| Zoomed in | County shading nationwide; Alaska uses borough estimates and statewide totals |
| A single county fills the screen (≥ 35% of the view, or view width < 1.6°) with a state selected; or no state selected and one county ≥ 50% of the view | That county's precincts, with the county outline on top |
| District type selected | That district layer fills nationwide (outlines 1.6 px for US House, 1.1 px for the others); no auto precincts. Drilling into a district shows its precincts. |
| State/county selected | Context county outlines; precinct detail as above (see section 11: "always show precincts" is only partial) |
| State lacks precinct data for the year | Falls back to county shading |
| Map moves off the selected state (after a 4 s grace period) | The state selection clears |
| Non-US country | Plain map, no results layers |

**Lines and colors**

- Boundary lines are **white**. County lines are 0.5 px and state lines are 1.2 px, slightly thicker.
- Shading follows the selected answers. Both answers on: a red/blue margin scale (D+60…R+60, or D+20…R+20 in delta mode). One answer on: a **single hue**, light → that answer's color (red only or blue only). None on: no fill.
- No data: gray (`#a8a29e` / `#d6d3d1`). Districts with < 50% vote coverage are gray.
- Legend: colors plus tiny labels only. Tap to magnify.

**Interaction:** tap shows a tiny popup with the area name, one line per selected answer (in the current format), "≈ estimate" where flagged, and the change line in delta mode. Double-tap zooms to the area and puts its name in the geo field.

## 7. Views

The globe button switches between **map** and **list**. Picking a chart type opens the list view with the chart.

### 7.1 Map view

As in section 6. Candidate thumbnails (photo squares the size of the flag icon) sit at the upper left with a tiny % or count badge. Tapping a thumbnail turns that answer on or off, which changes the shading.

### 7.2 List view

- **Current:** candidate rows only, with totals for the current scope (tapped area › drilled district › county › state › US). Each row shows name, share or count, and the change versus 2020 in delta mode. Two year columns appear only when the time row is open and both years are selected.
- **In progress (list-all):** one row per child entity, plus a total on the map (section 5.1).

### 7.3 Chart view

| Chart | Rule | Current |
|---|---|---|
| One type at a time | Only the selected chart shows (bar, line or pie) | Yes |
| Valid types depend on the time selection | **Single point:** bar and pie only. **Range (two or more points):** bar and line only. The chart-type button cycles only through the types valid for the current selection | Yes (build 1528) |
| Auto-switch and restore | Crossing between a point and a range switches an invalid type to bar (line → bar at a single point, pie → bar in a range) and restores the previous choice when returning, if it is valid again. Choosing a type by hand cancels the pending restore | Yes (build 1528) |
| Line | Range only. Labels the numbers, so no table. In delta mode the change value sits directly under each line, centred between the 2020 and 2024 points, never under the thumbnails | Yes |
| Pie | Single point only. No table. Thumbnails act as the legend. Updates live while the slider moves. The concentric 2020/2024 delta ring is **removed** | Yes (build 1528) |
| Scatter plot | **Not wanted** (user rule): do not build | n/a |
| Chart button in the full-screen map | No chart is displayed there, so the button shows the inactive style (not dark). It is dark only while a chart is displayed in list view | Yes (build 1528) |
| Delta sort rule | In delta mode the default sort is by the **magnitude of the net change as displayed** (largest first): % mode = change of the margin in points (`R +13.6`), # mode = change of the vote-count margin. Party side is ignored; the sort button reverses it. Applies at every list level (states, counties, towns, districts, precincts) | Yes (build 1530) |
| Single-year # bars | In # mode a bar's total length is proportional to the row's total votes on one common scale for the whole list (largest = longest, capped left of the floating buttons); the red/blue/gray split stays inside. % mode keeps full-width shares | Yes (build 1530) |
| District-type lists | US House: one nationwide list (435), a state's list is flat. School districts, state house and state senate: states -> counties -> districts. A district spanning counties is listed under each county it touches with its whole-district numbers and the ≈ mark (identical to the map pop-up) | Yes (build 1530) |
| Rows without a 2020 side | Show the real 2024 value with `'20 n/a`, never an empty "no data" row | Yes (build 1530) |
| List-all rows | Per-row charts follow the same rule: bar and line for a range (line = two-point lines with thumbnails at the endpoints), bar and pie for a single point | Yes (build 1528) |
| Bar | Bars plus a table (candidate, share or votes, total). In delta mode, change bars that diverge from zero | Yes |
| Desktop | Full width (≥ 600 px wide layout) | Yes |

### 7.4 Other controls

- **Time button (clock):** opens the year row, a tick slider. One knob selects a single year; two knobs (range, black fill) select delta mode.
- **% / # button:** one button, default %. Tap it to reveal the other option.
- **Search button (top right):** full-screen universal search over candidates, types, states, counties, towns, schools, US House districts, precincts (in the selected state), ZIPs and topics.
- **Layers button:** see section 8.

## 8. Layout and visual rules

| Rule | Status |
|---|---|
| Left-side icons share one centered vertical axis at **x = 27**, with text at **x = 52**, at every screen size (30×22 icon slot at x = 12) | Current (CSS "one shared icon slot") |
| Field at a fixed distance from the top; button at a fixed distance from the right; only the width stretches | Current |
| Candidate thumbnails anchored at the upper left, in the same position in map, list and chart views (sized from the rendered flag box via `--thx`/`--thw`) | Current |
| No fades and no layout jumps | Partial: see section 11 |
| Circles (buttons) in a row are all the same size (48 px, 8 px gap) | Current |
| All text is 32 characters or fewer per line (cut with "…" or wrapped in popups) | Current |
| Layers button: light outline dome by default; dark with the type icon when a district type is selected | Current |
| Layers menu closes instantly, with no animation | Current |
| Tapping the selected type again deselects it and restores the defaults (country, state, county, town and precinct boundaries) | Current |
| **Format modes:** # mode shows no percentages anywhere; % mode shows no vote counts anywhere (list, map, table, totals, popups) | Mostly. Gaps in section 11 |
| No "No data yet" bubble anywhere | Current (no such string in the code). List rows may say "no data" |
| No instructional text on the map | Current |

## 9. Data pipeline, coverage and licensing

### 9.1 Method (all years in today's boundaries)

1. **Boundaries:** current (2024) Census TIGER/Line districts, counties and places; VEST and NYT precinct shapes; Natural Earth for the world.
2. **2020:** VEST 2020 precincts, area-weighted into current districts. County results from tonmcg. The 2020 precinct display layer comes from MEDSL (CC0) joined to Census 2020 VTDs.
3. **2024:** official county totals for districts made of whole counties. Elsewhere, precincts are area-weighted. QC per county: precinct sums must be 70–100% of the official total and cover at least 70% of the county's area. Precincts are scaled per party to the official county total.
4. **Special cases:** Alaska uses official Division of Elections results, with absentee and early ballots allocated by House district (estimates). Maine House and Senate use official SOS town results. South Dakota legislative districts use OpenElections precinct results. Texas uses the Texas Legislative Council VTD returns (CC BY 4.0), and North Carolina uses official NC SBE precinct results. Since build 1534: Oklahoma, Vermont, Wyoming, Arkansas, Georgia, Missouri and Tennessee 2024 legislative districts come from official precinct returns (MEDSL 2024-elections-official, CC0; Oklahoma joined to State Election Board precinct boundaries); split precincts are apportioned by the votes cast in each part's legislative race (≈, only when ≤ 30 % of the district). The Wisconsin 2024 precinct layer is the LTSB ward file (official results disaggregated to wards, exact county totals) and California's is the Statewide Database SOV by SR precinct. The TX/NC change is in the latest local commit `3fdc690`, which is not pushed yet.
5. **Flags:** rows produced by area weighting or allocation carry `est`, shown as ≈ (an approximately-equal sign).
6. **Validation:** against 18,827 districts with known results, median total error is 0.71% and median Republican-share error is 0.06 points. For the fill rules, against 2,280 districts, median R-share error is 0.05 points and p90 is 0.41 points.
7. **Never fabricate.** A district that fails QC stays gray. Examples: VA SD25, LA SD2/19, TN HD21/23, OR SD29, and 28 SD school districts.

### 9.2 Coverage (computed from the data files on Oct 17, 2026, build 1534)

| Layer | Districts | 2024 with results | 2020 with results | Rows flagged estimate |
|---|---|---|---|---|
| US House | 435 | 435 (100%) | 435 (100%) | 73 |
| State senate | 1,942 | 1,941 (99.9%) | 1,942 (100%) | 570 |
| State house | 4,882 | 4,876 (99.9%) | 4,882 (100%) | 1,349 |
| School districts | 13,208 | 13,118 (99.3%) | 13,182 (99.8%) | 4,933 |

### 9.3 Sources and licenses

| Source | Used for | License / terms | Commercial use |
|---|---|---|---|
| The New York Times 2024 presidential precinct map (github.com/nytimes/presidential-precinct-map-2024) | Most 2024 precincts, and the district re-tabulation derived from them (18 states are NYT-only in the precinct layer) | **NYT C-UDA, non-commercial only**, credit required | **No.** Replace state by state with official state/county results before commercial use. Remove the NYT credit only after no NYT-derived data remains |
| VEST (Voting and Election Science Team) | 2020 precinct boundaries and results | CC BY 4.0, credit required | Yes, with credit |
| US Census TIGER/Line, 2020 VTDs | Boundaries | Public domain | Yes |
| MIT Election Data + Science Lab | 2020 precinct returns; some 2024 counties (with Census VTD shapes) | CC0 (per file credit) | Yes |
| tonmcg US_County_Level_Election_Results_08-24 | County results | **(unverified: check the repo license)** | Check |
| OpenElections (South Dakota; some PA counties) | 2024 precinct results | **Needs checking** | Check |
| Texas Legislative Council (Capitol Data Portal) | TX 2024 precincts | CC BY 4.0 | Yes, with credit |
| NC State Board of Elections | NC 2024 precincts (67 of 100 counties) | Public record | Yes |
| MEDSL 2024-elections-official (github.com/MEDSL/2024-elections-official) | OK, VT, WY, AR, GA, MO, TN 2024 legislative districts | CC0 | Yes |
| Oklahoma State Election Board precinct boundaries (CSA/INCOG ArcGIS) | OK 2024 precinct shapes (Oklahoma and Tulsa counties) | Public government data | Yes |
| Wisconsin LTSB 2024 Election Data with 2025 Wards | WI 2024 precincts | Open public data | Yes |
| Statewide Database, UC Berkeley Law (G24 SOV by SR precinct + shapes) | CA 2024 precincts | Public download, credit required; terms page offline (404) on Oct 17, 2026 | Confirm terms |
| Alaska Division of Elections; Maine SOS | AK precincts and districts; ME legislative districts | Public record | Yes |
| Natural Earth | Countries, Canadian provinces | Public domain | Yes |
| Wikimedia Commons official portraits | Candidate photos | Public domain (US government works) | Yes |
| Esri World Street Map | Basemap tiles | Esri terms **(commercial use likely needs an ArcGIS license; unverified)** | Check |
| US Census Geocoder; OSM Nominatim | Address lookup | Public / Nominatim usage policy (1 request/s, no bulk use) | Check limits |
| Leaflet | Map library | BSD-2 | Yes |

The commercial-readiness tracker lives in `COVERAGE.md` ("Sources and licenses"). It does not yet list TX and NC. Update it with the next data commit.

## 10. Future (approved direction)

1. **Move to Supabase and a full-stack app** when data reaches **700–800 MB**. GitHub Pages allows 1 GB; the site is about 176 MB today.
2. **Past elections remain static** (pre-built files or tiles on a CDN).
3. **Next major version collects live user votes** (the `vote` table, Auth, one vote per user per topic, results aggregated by the voter's precinct or institution).
4. **Expand** to businesses, brands and international governments, with a map directory of locations. Property locations belong to a **separate directory**, not this static app. Start with fewer than 10 test users.
5. **Pie of most gains for many candidates** (future option, only for races with many candidates; not built, not planned for the current two-party views).
6. **Groundwork for a commercial product.** This first requires the license work in section 9.3.

## 11. Known issues and open questions

| # | Item | Type |
|---|---|---|
| 1 | List-all, sort, drill-down (states → counties → towns → precincts) and the shared alias table are committed and live (builds 1517–1518) | Done |
| 2 | List-all rows in # mode print counts only, inside the bar segments (`tests/list-all-values.py`, `list-all-districts.py`, live build 1525) | Done |
| 3 | Popups and the legend in # mode still show margins in points ("Trump +4.2 pts", "D+60") in some paths (`aBlock`, `precHtml`, legend) | Bug / decision |
| 4 | The ≈ mark: district rows keep their `est` flag, and the map popup shows "≈ estimate" exactly for flagged districts (`tests/est-popup.py`, Alabama senate, desktop and phone, build 1525). List rows do not show ≈ yet | Done in popups; list rows open |
| 5 | "No fades / no layout jumps": the long-press label bubble fades over 0.3 s; the menu list slides (0.2 s `slideL/slideR`); the crumb animates in | Conflict with a rule |
| 6 | "Precincts always show when a state/county is selected" is only partial. A selected state shows counties until you zoom in (< 1.6° wide) or a county fills 35% of the view | Gap |
| 7 | District-type outlines are near-black (`#1c1917`), not white | Decision needed |
| 8 | Unisearch now gives every government-and-place entity two rows: an institution row (flag or entity icon with a type label) and a Place row (silhouette, "Place"). The geo filter uses silhouettes only, including countries and provinces (builds 1521, 1524) | Done |
| 9 | Tapping the title may open both the topic editor and the universal search (two click handlers) (unverified) | Possible bug |
| 10 | Towns, townships and boroughs are a drill-down level in list-all (tap a county row, then a town row for its precincts). The institution menu itself still closes on picking a county | Partly done |
| 11 | No results for non-US countries; the topic clears there by design | By design |
| 12 | Delta at the precinct level only works where the 2020 and 2024 precinct have the same name and shape; elsewhere it is gray | Data limit |
| 13 | 2020 precinct display files exist for 40 states only | Data gap |
| 14 | Licenses to confirm: OpenElections, tonmcg, Esri tiles, Nominatim | Open |
| 15 | Single 5.5 MB `index.html` (about 0.35 MB of code, the rest inlined data) built from many layered overrides (`const _x=f; f=function(){…}`) and `setInterval` polling (200–1500 ms) for layout and sync | Tech debt |
| 16 | The legacy v1 app (`/index.html`, `US-districts.html`, `test/`) is still in the repo | Clean-up |
| 17 | Texas precinct switching timing is not yet measured or tuned | Not started |
| 18 | 2024 gray legislative districts down to 7 (AR SD 006; WY 054, MO 156, LA 057, MS 115, VA 089, AL 004); 90 gray school districts (SD 26, ME 14 …); reasons in COVERAGE.md | Partly done (1534) |
| 19 | NYT-to-official source replacement is not done. The NYT credit stays until it is. OpenElections South Dakota license is unconfirmed | Not started |
| 20 | 2016 presidential data: prepared offline only (not live, not in the time filter). Canada is parked | Parked / low priority |
| 21 | Safari/WebKit behavior (list jumping, bar values, menu header) is untested here; all checks run in Chromium (desktop and phone sizes) | Unverified |
| 22 | District menu rows use the state flag instead of checkboxes; selection still toggles on tap (dimmed flag when off) | Decision to confirm |
| 23 | Chart redesign leftovers (see t183–t199 items) are only partly verified on Safari | Open |

## 12. Migration notes

**Split the single `index.html` into data, logic and UI**

| Layer | Contents today | Target |
|---|---|---|
| Data | `PACK`, `XREF`, `STATE_FILES` inlined; JS-wrapped data files | Postgres/PostGIS tables (section 4). Static exports to Storage: vector tiles (PMTiles/MVT) per layer and year, plus per-entity JSON results |
| Logic | Aggregation (`aggFor`, point-in-polygon), coloring (`heatC`, `shareColor`, `deltaColor`), search (`fuzzyRank`, `__NAMES`), selection state (`state`/`county` selects, `ltype`, `years`, `candOn`, `numMode`, `chartMode`) | Pure TS modules: `colors`, `format` (one formatter that honors %/#), `search`, `selection-store` (one state object instead of hidden `<select>`s and globals), `results` |
| UI | Leaflet plus DOM built in strings; CSS with heavy `!important` overrides | Components: InstitutionFilter, GeoFilter, TopicField, LayersButton, TimeRow, FormatToggle, MapView, ListView, ChartView, CandidateThumbs. One layout grid that holds the x = 27 / x = 52 invariants |

**Practical order**

1. Freeze the static v2 as the reference. Write Playwright tests from sections 5–8 (extend `tests/`).
2. Load the entity/boundary/result tables from the existing files (they already hold re-tabulated current-boundary results). Keep `est`, `coverage` and the per-county `source`.
3. Serve geometry as tiles. Do not ship 59 MB of precinct JS. Query results by `entity_id` and `election_id`.
4. Replace polling with reactive state; remove the override stack.
5. Add Auth and `vote` for the next major version; keep 2020/2024 static.
6. Before any commercial launch, replace NYT-derived rows state by state (`source.commercial_ok = false` makes them easy to track), then remove the NYT credit.

## 13. Changelog

| Date | Change |
|---|---|
| Oct 17, 2026 | Build 1534: 2024 gray legislative districts filled from official precinct returns (MEDSL CC0: OK, VT, WY, AR, GA, MO, TN; all OK and VT districts now exact); Oklahoma and Tulsa County precincts from the State Election Board; Wisconsin 2024 precincts from LTSB wards and California 2024 precincts from the Statewide Database; 84 gray school districts filled (CA 46, WI 23, OK 11, VT 4); still gray: senate 1, house 6, schools 90 (COVERAGE.md) |
| Oct 17, 2026 | Build 1533: 2020 complete for all counties (Connecticut added) and precinct files within 90-110 % of official everywhere (VEST 2020, CC BY 4.0); Alaska 2020 boroughs/House/Senate (≈); ≈ 2020 for re-drawn 2024 precincts (area-weighted, `v2/data/x20/`); gray districts filled with ≈ (`e20`/`e24`/`est`); Idaho 2024 Owyhee and Idaho County from the Idaho SOS; remaining gaps in COVERAGE.md |
| Oct 15, 2026 | Build 1531: 2020 precinct coverage completed for 40 states from VEST 2020 (CC BY 4.0), QC against official county totals; remaining gaps in COVERAGE.md |
| Oct 15, 2026 | Build 1530: delta sort by net magnitude; # bars to scale; county tier for school/state-house/state-senate lists; Arizona 2020 precincts (VEST, CC BY 4.0); `'20 n/a` rows; readable line rows (1529) |
| Oct 15, 2026 | Chart rules (build 1528): pie only at a single point, line only for a range, button cycles valid types, auto-switch and restore, delta pie ring removed, no scatter, chart button inactive in the full-screen map, line delta labels under the line; list-all line rows |
| Oct 15, 2026 | Gap section refreshed at build 1525: unisearch two-row rule, sovereign vs incorporated wording, ≈ popup verified, district list-all data, editable scope row, silhouettes in the geo filter. |
| Oct 14, 2026 | First version, written from the code at build 1498 (live) and 1499 (working copy), `COVERAGE.md`, and the approved rules. |

*This document is refreshed periodically as the app changes. Check the date above, and the build number in `v2/index.html`, before you rely on it.*
