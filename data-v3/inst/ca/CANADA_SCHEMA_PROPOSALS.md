# Canada: schema proposals for Full Stack (institutions lane, data/inst-canada). NOT accepted yet.

Against docs/v3/SCHEMA.sql on origin/v3/plan (365c8a1; Canada rules from 62cb622 / 3c1e42d).

1. **Units for Canada.** SCHEMA 62cb622 says non-US places carry no unit or boundary_set. Going down to polls needs Canadian
   units. Proposal: allow `unit` / `boundary_set` rows for `country = 'ca'` (they never mix with the US sets, since every slug is
   distinct and every row has `country`).
2. **New unit types** (`unit_type_def`):

   | unit_type | category | label | key |
   |---|---|---|---|
   | `fed` | new `federal_district` ("Federal electoral districts") | Federal electoral district (Canada) | Elections Canada FED_NUM, e.g. `35075` |
   | `poll` | `precinct` | Federal polling division (Canada) | `<FED_NUM>:<PD_NUM>-<SFX>`, e.g. `10001:78-0` |
   | `ped` | new `provincial_district` ("Provincial electoral districts") | Provincial / territorial electoral district | the agency's code (ON ED_ID, QC CO_CEP, BC abbreviation `ABM`, AB/MB/SK/NB/PE/NL district number) |
   | `ppoll` | `precinct` | Provincial polling division / voting area / section de vote | `<district key>:<poll code>` (QC `199:106`, BC `ABM:049`, SK `1:ATH01`) |
   | `cd` | `county` | Census division (Canada) | StatCan CDUID |
   | `csd` | `town` | Census subdivision (Canada) | StatCan CSDUID |
3. **New boundary sets** (slug, unit_type, vintage_year, is_current):
   `ec-2023-fed` fed 2023 current; `ec-2013-fed` fed 2013; `ec-2025-pd` poll 2025 current; `ec-2021-pd` poll 2021; `ec-2019-pd` poll 2019;
   `eo-2022-ed` ped 2022 current; `eq-2026-ced` ped 2026 current; `eq-2026-sv` ppoll 2026 current; `ebc-2023-ed` ped 2023 current;
   `ebc-2024-va` ppoll 2024 current; `ea-2019-ed` ped 2019 current; `ea-2026-va` ppoll 2026 current; `em-2018-ed` ped 2018 current;
   `em-2023-va` ppoll 2023 current; `esk-2022-ed` ped 2022 current; `esk-2024-va` ppoll 2024 current; `enb-2024-ed` ped 2024 current;
   `enb-2024-pd` ppoll 2024 current; `epei-2017-ed` ped 2017 current; `epei-2017-poll` ppoll 2017 current (vintage not stated by the
   source); `enl-2015-ed` ped 2015 current; `enl-2019-poll` ppoll 2019 (maybe superseded); `statcan-2021-cd` cd 2021 current;
   `statcan-2021-csd` csd 2021 current. Pattern: `<agency>-<boundary year>-<set>`. `boundary_set_one_current` is per
   (owner_tenant_id, unit_type), so `ped` / `ppoll` need a province in that unique index (13 current `ped` sets), e.g.
   `(owner_tenant_id, unit_type, coalesce(meta->>'province',''))`.
4. **unit.parent_unit_id across sets.** A poll's parent is the FED of a *different* slug (`ec-2025-pd` → `ec-2023-fed`); the files
   carry `parent_boundary_set` + `parent_unit_key`. Proposal: allow cross-set parents (the comment now says "same vintage").
5. **unit country / province.** `unit.state_fips`/`state_abbr` are US. Proposal: `unit.country char(2)` (default 'us') and put the
   ISO 3166-2 province code (`ON`, `QC` ...) in `state_abbr` only together with `country='ca'`; no Canadian code collides with a US
   postal code, but the pair must be read together. Same for `entity`: rows here leave `state_fips`/`state` empty and add
   `country`, `province`, `name_fr`, `external_id` columns (proposed; could go to `meta` instead).
6. **Chamber ids.** `chamber:ca-house` (House of Commons, type lower_chamber), `chamber:ca-senate` (type upper_chamber, appointed,
   no units), `chamber:ca-<iso>-legislature` for the 13 unicameral provincial / territorial legislatures (type unicameral; parent =
   province / territory entity). Kind stays `chamber`.
7. **Person scheme `ca-mp`.** `person.scheme` check allows `bioguide`, `ocd-person`, `^[a-z]{2}-leg$`. Proposal: add `ca-mp`
   (`ca-mp:<House of Commons PersonId>`, permanent across parliaments, e.g. `ca-mp:89156`). Provincial members later as
   `ca-<iso>-leg:<agency id>` (e.g. `ca-on-leg:...`), which needs `^ca-[a-z]{2}-leg$` too.
8. **officeholder.unit_geoid.** Canadian codes are not GEOIDs. The file uses `unit_key` (FED_NUM) + `boundary_set`; proposal:
   resolve officeholder → unit by (`boundary_set`, `unit_key`), `unit_layer = 'fed'`, `unit_plan = 'rep-order-2023'`.
9. **Licence rows** to add to `license`: OGL - Canada; OGL - New Brunswick; Statistics Canada Open Licence; Elections Ontario
   Open Use Data Product Licence; DGEQ open-data licence (attribution; the QC file metadata adds a **non-commercial** clause: decide
   before any paid tier shows QC sections); Elections BC Open Data Licence; PEI open data; "not stated" (AB, MB, SK, NL);
   House of Commons website (no reuse grant; factual fields only).
10. **Feed / origin.** All rows `feed = inst-lane` (→ origin `inst`), within the DATA_LOADING §15.1 set.
