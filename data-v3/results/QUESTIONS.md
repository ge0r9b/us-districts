# Election Data: answers to v3 questions (docs/v3/DATA_LOADING.md §10, branch v3/plan)

Answered from the repo at data/election 5c517c5 (= data/geo a14a9eb + election-lane commits).

**Q-E1: `cty` flag.** Exact, not ≈. It marks a district made of whole counties, whose value is the official county total (or a sum of them). Checked on every row:
- All 54 `ussch.js` rows with `cty`: the 2024 and 2020 values equal exactly one county's `ELECTION2024`/`ELECTION2020` value (e.g. Maryland Carroll County Public Schools = Maryland|Carroll County).
- All 4 `ussldu.js` rows (IN 026, KY 004, KY 014, MS 004): the values equal the sum of 2-5 counties lying wholly inside the district (e.g. KY 014 = Washington + Larue + Spencer + Marion + Nelson).
- `tools/fill_gray.py` treats `cty` as exact (`exact = flag not in ('e24','est','e20')`). The flag comes from build 202610141474 ("whole counties at official county totals"). v3 should load these as `method=official` (county sum), with no ≈.

**Q-E2: candidate IDs.** The source of truth is now `data-v3/results/candidates.csv`. Harris = `harris-kamala-d`. The full list:
- `clinton-hillary-r`, `trump-donald-j`, `johnson-gary-e`, `stein-jill`, `castle-darrell-l`
- `biden-joseph-r`, `jorgensen-jo`
- `harris-kamala-d`, `oliver-chase`
- `all-others` (FEC "All Others")

The committed PA and 2016 FEC rows were re-keyed to these IDs (commit 550bfe3). The earlier `biden-joseph-robinette-jr` and `clinton-hillary` are retired.

**Q-E3: optional `method` column.** Yes. From now on I will add it as a 14th, optional column with the values `official | area_weighted | allocated | votes_in_split | town_apportioned | retabulated`. Existing 13-column files stay valid; a missing column means `official`.
- For `v2/data/x20/<State>.js`: every row there is area-weighted (≈). By construction (`tools/build_x20.py`), x20 holds only 2024 precincts that have no same-name-and-shape 2020 precinct. The exact same-shape matches are not in x20; the app pairs them by name and geometry hash.

**Q-E4: 2016 as bot rows.** Partly.
- Ready now: 2016 state rows (`2016/us_president_2016_state_fec.csv`, 13 columns, from FEC) and PA county rows (`PA/pa_president_county_official_2016.csv`).
- Shipped as v2-format JS: the full 2016 build in `2016/precincts2016/*.js` (`__prec`), `2016/out/election2016.js` (counties) and `2016/out/ds2016.js` (states and districts, `1` = ≈).
- I can emit counties and districts as 13+1-column CSV on request (about 70k rows, roughly 10 MB uncompressed). I held back to keep bytes lean.
- Precincts: read them through the legacy `__prec` parser. A CSV copy would roughly double about 44 MB.

**Q-E5: district token.** Statewide contests use `district=statewide` (not empty). Seats use v2's keys, which are TIGER codes, as strings, without a state prefix:
- US House: 2 digits (`01`; at-large `00`).
- State senate and house: 3 characters (`009`, `055`). This includes letter codes such as MD `29A` and the AK senate `00R`.
- Schools: the full v2 name. After the Geo renames, duplicates are `Name (County)`.

The state goes in the `state` column, never `PA-01`.

**Q-E6: precinct `unit_id`.** Precinct rows use v2's `County|Precinct` key. It is **not stable across years**:
- 2016: VEST precinct names.
- 2020: MEDSL/TIGER VTD names, plus VEST fills.
- 2024: NYT GEOID-like codes in many counties (e.g. `Beaver County|420071330`), and names elsewhere.

Boundaries also change. Link precincts across years only by geometry (shape hash or areal overlap, as x20 does), never by key.

**Q-E7: which total.** Total = all presidential candidates (the user's rule). When sources overlap, take the total from the highest-precedence official source *for that unit*:
- State level: the state's certified total if it includes write-ins, otherwise FEC (whose `all-others` includes write-ins).
- County or precinct level: the state or county certified list.

Where a source leaves write-ins out (PA DOS 2016/2020/2024), the total is lower than FEC's. Flag it with the definition and don't mix sources inside one unit. For 2016 PA: county rows total 6,115,402 (DOS, no write-ins) and the state row 6,165,478 (FEC). Both are kept, each labelled with its source.

**Q-E8: precedence.** Confirmed: official certified values win, and v2's value is kept in history (REPO-RULES rule 4).
- "Official" means the **state's certified result** first, then FEC as a compilation.
- Example: Virginia 2024. FEC shows 2,333,778 / 2,074,097, but the VA Department of Elections certified 2,335,395 / 2,075,085, which is what v2 already has.
- Where two official figures disagree (PA 2020 Allegheny: county board vs DOS), keep both in history and show the state certification, with a note.
