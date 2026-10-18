# data-v3/inst/entities.csv + entity_geoid_xwalk.csv: final column list

Status: **settled Oct 18, 2026 (v3 Full Stack design)**, built by `tools/inst_entities.py` on branch `data/inst-entities`.
All files are UTF-8 CSV with one header row. v3 reads columns by header name: the names below are stable.
Column numbers 17+ in the table below keep their historical numbering (two columns moved out on 04227d3). Columns after `source_set` (entities: `feed` onward) and after `source_id` (xwalk: `overlap` onward) are additive extras that v3 may ignore.
Provenance (Oct 18, 2026): `source`, `source_url`, `retrieved_at`, `license` were replaced by `source_id` into `sources.csv` (README_SOURCES.md).

## entities.csv: one row per institution, no vintage

| # | column | example | meaning |
|---|---|---|---|
| 1 | `entity_id` | `nation:fr`, `territory:gl`, `province:ca-on`, `territory:ca-yt`, `county:01001`, `muni:place:1714000`, `town:cousub:0911001080`, `school:0100003`, `chamber:al-lower`, `us-house`, `state:01`, `nation:us`, `chamber:dc-council` | stable, opaque. Minted once from the kind prefix + the GEOID the entity was **first seen** with, then frozen: never re-derived when a boundary or GEOID changes. A new id is minted only when the government itself changes (merger, dissolution, new incorporation, CT counties → planning regions) |
| 2 | `kind` (open vocabulary; company kinds will be added by external feeds) | `nation`, `state`, `territory`, `province` (**new**, Canadian provinces, parent `nation:ca`; confirmed by Full Stack, SCHEMA 62cb622), `county`, `municipality`, `township`, `school_unified`, `school_elementary`, `school_secondary`, `chamber`, `dc_council` | district seats are **units, not entities** (no `district_seat` kind) |
| 3 | `state_fips` | `01` | jurisdiction (empty for nation / us-house / us-senate) |
| 4 | `state` | `Alabama` | |
| 5 | `name` | `Autauga County` | TIGER NAMELSAD (Census) or the official body name |
| 6 | `alias` | `Hartford town;Hartford` | `;`-list; a `;` inside a name is escaped as `\;` |
| 7 | `label` | `incorporated` / `unincorporated` / `sovereign` | v2 wording: states sovereign; TIGER CLASSFP for places |
| 8 | `gov_status` | `government` / `area_only` / `dependent` / `unknown` / empty | CoG 2022 by FIPS code, county_government.csv for counties, TIGER FUNCSTAT G = dependent; `unknown` = not determinable from the sources (ruling on 04227d3; was empty), the reason in a `gov_status_unknown:<reason>` flag; empty = not applicable (`gov_status_na:*`: chambers, courts) —  formerly: empty = unknown (see `flags`) or not applicable (chambers) |
| 9 | `parent_id` | `state:01` | generic containment / ownership link (a corporate parent works the same way). School district → state, county → state, town/municipality → county (if ≥ 98 % inside one county, else state), chamber → state, us-house → nation:us, state → nation:us |
| 10 | `valid_from` | `2023-05-02` | date the **current form of government** began, only when a source states it explicitly (Census GCN incorporation date, TCEQ WDD creation date of a district); empty otherwise. Not an inception: Wikidata P571 goes to `inception` (column 27) |
| 11 | `valid_to` | | empty = still exists |
| 12 | `predecessor_id` | | `;`-list of entity_ids this one replaced |
| 13 | `successor_id` | `county:09110;county:09130` | `;`-list of entity_ids that replaced it |
| 14 | `v2_layer` | `v2:counties;v2:parts` | `;`-list of v2 (and v1) layers that show this entity |
| – | ~~`v2_row`~~ | | **moved** (ruling on 04227d3) to `entity_v2_rows.csv` only: the entity's v2_row list = that table's (`v2_layer`, `v2_row`) rows with this `entity_id` |
| – | ~~`v2_key`~~ | | **moved**: derivable from `entity_v2_rows.csv`: `state\|v2_name` (`state\|v2_row` for `v2:parts` / `v2:towns(IA townships)`) of its `v2:` rows not `@2020` |
| 15 | `source_set` | `3f9a1c07` | (was `source_id`, ruling on 04227d3) 8-hex key into `source_sets.csv` = the row's ordered list of source ids (keys of `sources.csv`); key = first 8 hex of sha256 of the `;`-joined id list, so it depends only on the sources' deterministic ids |
| 16 | `feed` | `1` | smallint code into `enum_feed.csv`: 1 `tiger/cog`, 2 `inst-lane`, 3 `governments-bot`, 4 `companies-bot`, 5 `user-upload` (fixed codes) |
| 19+ | `level`, `type`, `cog_pid6`, `flags` | `local`, `city`, `162236`, `gov_status_unknown:...` | extras: government tier (federal/state/county/local; world rows national/subnational), finer type (TIGER LSAD text; sovereign_state / dependency / province / territory), CoG 2022 unit id, `;`-list of flags for unknowns and review items |
| 23 | `source_record_id` | `01001`, `Q228` | SCHEMA `entity.source_record_id`: the id inside the row's first cited source (GEOID / FIPS for Census rows, QID for Wikidata rows) |
| 24 | `wikidata` | `wikidata:Q156168` | Wikidata QID (world rows: from P297/P300; US rows: the Governments bot's wikidata_qid; nation:us Q30) → `entity_alias` (kind external_id, scheme wikidata) |
| 25 | `iso_3166_2` | `MX-JAL`, `CA-ON` | ISO 3166-2 code as given by the Governments bot foreign layer (subdivisions, Canadian provinces/territories, dependencies listed in their sovereign's ISO 3166-2). An attribute only: the entity_id does not follow it |
| 26 | `constituent_qid` | `Q35` (nation:dk) | nations only, from the Governments bot foreign layer: the constituent country's Wikidata item when it differs from the sovereign-state item in `wikidata` (nation:dk Q35 under Kingdom of Denmark Q756617; nation:nl Q55 under Kingdom of the Netherlands Q29999). Not unique-checked against `wikidata` as an identity of this row; a value that is another entity's `wikidata` is not carried (`wikidata_qid_conflict`) |
| 27 | `inception` | `1901-01-01`, `1623-01-01` | earliest sourced inception: Wikidata P571 with a P248/P854 reference, as carried by the Governments bot (foreign layer only today; no available feed has P571 for US rows, so they are empty and nothing was fetched). Stored as a full date; a year-only value is `YYYY-01-01`, a month-only value `YYYY-MM-01`. **Not** the date the current government began (Barbados 1623 is a settlement date) |
| 28 | `inception_precision` | `day`, `month`, `year` | precision of `inception`: the bot writes P571 at its Wikidata precision (`YYYY` / `YYYY-MM` / `YYYY-MM-DD`), so it is read from that string's form; empty when `inception` is empty |
| 29 | `inception_source` | `Wikidata Q244 P571, reference: …` | the bot's `valid_from_source` for that value (`Wikidata <QID> P571, reference: <P248 item or P854 URL>`) |
| 30 | `valid_from_source` | `Governments bot tceq_wdd:101792: tceq_wdd (https://www14.tceq.texas.gov/…)` | where `valid_from` came from: the bot row id, its source key(s), source URL and the row's note (TCEQ WDD creation date; Census GCN incorporation date). Filled on every row with a `valid_from` (checked by the builder) |
| 31 | `code_scheme` | `gss`, `ars`, `insee_com`, `insee_ctcd`, `insee_reg`, `siren` | country layers (gb/de/fr) only: the official code system of `code` |
| 32 | `code` | `E04000001`, `091620000000`, `75056`, `971D` | country layers only: the unit's **current** official code. The `entity_id` keeps the code it had when it was minted and does not follow a later recode; the bot's feed id (`gss:` / `de-ars:` / `fr-cog:<level>:` / `fr-siren:`) is in `entity_feed_map.csv` |
| 33 | `code_valid_from` | `2009-01-01`, `2008-12-31` | country layers only: the date the **code** (not the government) took effect: UK ONS RGC operative date (2009-01-01 = the GSS recoding), DE BKG VG250 `WSK` (Rechtsstand, date of the last legal/territorial change). Never copied to `valid_from` |
| 34 | `load_group` | `1`, `2` | smallint into `enum_load_group.csv`: 1 = US, domestic, nations / territories / provinces / ISO subdivisions (load first); 2 = the GB / DE / FR country layers (load later, behind a flag). A group-1 row never has a group-2 parent |

## entity_geoid_xwalk.csv: one row per entity × unit_layer × vintage

| # | column | example | meaning |
|---|---|---|---|
| 1 | `entity_id` | `muni:place:1714000` | |
| 2 | `unit_layer` | `state`, `county`, `cousub`, `place`, `unsd`, `elsd`, `scsd` | TIGER set token (= `unit_type_def.tiger_set` in docs/v3/SCHEMA.sql) |
| 3 | `geoid` | `1703114000` | Census GEOID |
| 4 | `vintage` | `2024` | TIGER vintage year |
| 5 | `boundary_set` | `v2-2024` | boundary-set slug of the unit (Election's Q-E12 tokens): `v2-2024` for TIGER 2024 units, `tiger-2020-county` for the CT 2020 counties |
| 6 | `relation` | `primary`, `coextensive`, `also_cousub`, `consolidated_city_county`, `independent_city_county_equivalent`, `consolidated_town_city`, `federal_district_city` | how this GEOID names the entity |
| 7 | `source_set` | | key into `source_sets.csv` (was the `;`-list `source_id`) |
| 8–10 | `overlap`, `share_of_geoid_in_entity`, `share_of_entity_in_geoid` | `equal` / `split` / `contained` | geometric relationship (mutual ≥ 0.9 = equal; GEOID ≥ 0.9 inside entity = split; entity ≥ 0.9 inside GEOID = contained), measured on the TIGER 2024 geometry in EPSG:6933 |
| 11 | `source_record_id` | `1703114000` | SCHEMA `entity_geoid.source_record_id`: the GEOID when the cited source is Census; empty for derived links |

## Officeholder rows (data-v3/inst/officeholders_*.csv)

Officeholders are keyed to **chamber entity + unit + seat**: `entity_id` = the chamber entity (`us-house`, `chamber:al-lower`),
`unit_layer` (`cd`/`sldu`/`sldl`) + `unit_geoid` + `unit_vintage` (TIGER year) name the district unit, and `seat` numbers
multi-member seats where the source gives one.

---

## Alignment with docs/v3/SCHEMA.sql (origin/v3/plan b66f889 → 365c8a1)

Full Stack ruled on all 10 earlier differences (b66f889); status here:
| # | difference | ruling | here |
|---|---|---|---|
| 1 | text `source_id`, `;`-lists | `source.source_id` text PK + link tables (`entity_source`, `entity_geoid_source`, ...) | as is |
| 2 | `source`, `commit` columns | `source` → `title`, `commit` kept | as is |
| 3 | multi-URL `source_url` | split into `source_url` (source_id, ord, url, label) | `source_urls.csv`, labels on every multi-URL source |
| 4 | `feed` vs `origin` | `feed` stored raw, mapped to `origin` (§15.1) | builder asserts feed ∈ {tiger/cog, inst-lane, governments-bot, companies-bot, user-upload} |
| 5 | xwalk `boundary_set` | column on `entity_geoid` | as is (`v2-2024`, `tiger-2020-county`) |
| 6 | xwalk shares | `share_of_geoid_in_entity`, `share_of_entity_in_geoid` numeric on `entity_geoid` | same names |
| 7 | officeholder `source_commit` | dropped (from `source.commit`) | as is |
| 8 | units without TIGER geometry | `seat` units, `seat:<chamber>:<district>` | data/inst-officeholders step 7 (`unit_key`, `seat_member_units.csv`) |
| 9 | `source_record_id` | column on entity, entity_geoid, officeholder, county_government, ... | filled (entities, xwalk, officeholders, county_government) |
| 10 | county_government.csv | own table | as is (+ `source_record_id`) |

Open with SCHEMA 365c8a1: `entities.csv` extras `source_record_id` / `wikidata` (col 23–24; `wikidata` → `entity_alias`
external_id scheme wikidata); `pack/entity_feed_map.csv` (feed id → registry id; a pack, not loaded into Postgres; SCHEMA has `entity_merge` / `entity_alias`
kind `merged_id`/`external_id` but no feed-map table) and `entity_images.csv` (no image table; `entity.icon_flag` is a single
text column). Full Stack rulings (Oct 18), applied in this build: `wikidata` nullable + unique `wikidata:Q…`; images columns role/file/license/fair_use/usage_basis/source_url/attribution; feed map feed/feed_id/entity_id/status/note; `entity_relations.csv` `consolidated_with`. Seal/flag rows carry `license`/`fair_use`/`usage_basis`. Later rulings (Oct 18) add `licence_url` (Commons LicenseUrl, else the canonical creativecommons.org deed for CC licences), `public`, `icon`, `attribution_source` (feed / issuing_body_name:* / commons_artist / commons_credit / commons_license / commons_uploader / commons_contributors) and `note` (e.g. a replaced file).

## Kind `subdivision` (agreed Oct 18; applied)

Other countries' first-level ISO 3166-2 subdivisions, from the Governments bot foreign layer (`foreign/subdivisions.csv`).
- `entity_id` `subdivision:<iso 3166-2 code lowercased>`, for example `subdivision:mx-jal`. The id is frozen when minted and
  does **not** change if ISO renames or recodes the subdivision; the current code is the `iso_3166_2` attribute (column 25).
- Canada keeps `province:ca-xx` / `territory:ca-xx`. Codes that the bot's `iso_domestic_crosswalk.csv` sends to an existing
  row (US states and territories, CN-HK → `territory:hk`, FR overseas codes → their `territory:` rows) are not minted; they
  appear only as `pack/entity_feed_map.csv` rows with `feed_id` `iso3166:<code>`.
- `kind` subdivision, `level` subnational, `type` = the ISO subdivision type (province, state, region, …), `parent_id` = the
  country's `nation:` or `territory:` row, plus a `parent` row in `entity_relations.csv`. `gov_status` is `unknown` and the row
  carries the flag `gov_status_unknown:outside_cog2022_scope`, the same as other non-US rows. `feed` `governments-bot`.
- No units, no xwalk rows, no boundary_set. The bot's `valid_from` / `valid_from_source` (Wikidata P571 with a reference)
  go to `inception` / `inception_source` / `inception_precision` (bb5e342); `valid_from` stays empty (it is not the date the
  current government began); `valid_to` is blank in the bot's files. All rows are `is_active` Y; a code later withdrawn by
  ISO keeps its frozen id on the bot side (`iso_code_withdrawn`), so ours stays too.
- Subdivisions of rows flagged review_status (Taiwan, Western Sahara) are not minted (feed_only, pending the user).

## Kind `special_district` (Full Stack, Oct 18; applied)
- id `special_district:<st>-<source>-<source_id>`, **frozen**. `<st>` = USPS code lowercased; `<source>` = short source
  key (`tceq` for the TCEQ Water Districts Database rows, feed source `tceq_wdd`; **future CoG special districts use the same
  kind with source `cog`**, e.g. `special_district:<st>-cog-<cog_id>`); `<source_id>` = the source's own id (the part after
  the feed prefix, `tceq_wdd:101792` → `101792`), lowercased, each run of characters outside `[a-z0-9]` replaced by `-`,
  leading/trailing `-` stripped, leading zeros kept (tools/inst_govfeed.py `sd_norm`).
- Minted today: the 305 Governments-bot rows of type special_district flagged `not_in_cog2022` (TCEQ WDD districts created
  2022-01-01 or later, ACTIVE). CoG 2022 special districts stay `feed_only:special_district` until minted.
- `name` = the official name verbatim (TCEQ, upper case as published); `type` = the TCEQ district type (municipal utility
  district, …); `level` local; `gov_status` government (bot `independent`); `valid_from` = the TCEQ creation date;
  `source_record_id` = the bot id (`tceq_wdd:<id>`); `parent_id` = `state:<FIPS>` plus a `parent` row in entity_relations.csv.
- County: an `in_county` row in entity_relations.csv with `method` `sourced`, `note` `tceq_wdd_primary_county` (the WDD's
  primary county as given in the bot row's `county_geoid`). No coordinates in the feed, so no `point_in_polygon` links. No
  sourced county → gap `special_district_county_unknown`. No units, no xwalk rows (TIGER has no special-district layer).

## entity_relations.csv
`entity_id, relation, related_entity_id, method, note, source_set, load_group` (approved by Full Stack, Oct 18; `source_set` / `load_group` 04227d3 ruling; load_group 2 when either end is a GB / DE / FR row). relation: `member_of` (entity → the body it is a member of: FR EPCI / EPT, UK combined authority; the Governments bot's `member_of` column, `method` sourced), `parent`
(minted courts, foreign territories / subdivisions, special districts), `consolidated_with`, `in_county` (special district →
its county), `area` (a council → the area entity it governs, when council and area are separate rows: FR région councils →
`subdivision:fr-*`, Guadeloupe / Réunion councils → `territory:gp` / `territory:re`), `predecessor` (entity → the entity it
replaced, `method` sourced; from the Governments bot's official link tables: UK ONS Code History Database `Changes`
(note `ons_chd`), FR COG mouvements (note `insee_cog_mouvements`), DE BKG VG250 editions (note `bkg_vg250_editions`). The
related entity is an ended one, except an FR commune created / re-established by splitting off a commune that still exists
(note suffix `;split_from_current`); a link between two current governments otherwise is a boundary transfer, not a
relation. A sourced `valid_from` with no link gets the flag `predecessor_none_in_source`; links the feed pruned or cleared
are never flagged `predecessor_pending`). The country layers write no `parent` rows (their `parent_id` column carries the link). `method` (how the link was made) ∈ `sourced` (a source states it) | `overlay` (area overlap of boundaries) |
`point_in_polygon` (a point inside a boundary; an estimate) | `manual`; `note` holds the detail (e.g.
`tceq_wdd_primary_county`). Every current row is `sourced` (parent, consolidated_with and in_county all come from a cited source); the builder rejects any other value.

## Country layers: UK, Germany, France (Full Stack, Oct 18; applied)

From the Governments bot `foreign/gb|de|fr/` (units*.csv + code_xwalk.csv, pinned commit, one sources.csv row per file
with sha256); tools/inst_foreign_local.py.
- **id** `<kind>:<cc>-<code at minting>`, lowercase, **frozen**: `municipality:de-091620000000`, `municipality:fr-75056`,
  `county:fr-01` (the département code; `county:fr-69m`, `county:fr-6ae` for the CTCD-coded collectivities),
  `submunicipal:fr-comd-77316` (FR sub-municipal ids carry the level: 584 communes déléguées share their commune's code),
  `intermunicipal:fr-<siren>`, `regional_authority:fr-<INSEE région code>`, `local_authority:gb-<gss>`, `parish:gb-<gss>`.
  A later recode changes `code`, never the id; a new government is a new id with a `predecessor` relation.
- **feed ids** `gss:<code>`, `de-ars:<12 digits>`, `fr-cog:<reg|dep|ctcd|com|comd|coma|arm>:<code>`, `fr-siren:<siren>` live
  only in `pack/entity_feed_map.csv` (status mapped; Regierungsbezirke and erfüllende Gemeinde rows feed_only). Crosswalk codes
  are feed-map rows too: `gss:`, `de-ars:`, `iso3166:`, `insee_dep:`, `insee_reg:`, `insee_ctcd:`, `insee_comer:`,
  `fr-siren:` (a commune's / département's SIREN = `fr-siren:` row, note `alt_code`). One code may map to two bodies
  that each govern part of the area (`insee_dep:69` → Métropole de Lyon and the Rhône council); that is the only feed id
  with two rows.
- **kinds** (new: `regional_authority`, `local_authority`, `intermunicipal`, `submunicipal`, `parish`):

  | kind | gov_status | GB | DE | FR |
  |---|---|---|---|---|
  | `regional_authority` | government | GLA, 15 combined authorities | – | région councils (13 mainland incl. Collectivité de Corse; Guadeloupe, Réunion: the bot's units, parent the territory) |
  | `county` | government | 21 county councils | Landkreise / Kreise | 91 conseils départementaux, Métropole de Lyon, CEA, Guadeloupe / Réunion département councils (bot units `fr-cog:dep:971/974`) |
  | `local_authority` | government | 361 LAs (unitary, districts, boroughs, Welsh principal councils, Scottish council areas, NI districts) | – | – |
  | `intermunicipal` | FR government (EPCI à fiscalité propre / EPT: councils); DE `unknown` + `gov_status_unknown:council_not_in_feed` + gap `intermunicipal_council_unknown` (the feed gives the designation only) | – | Ämter, Verbandsgemeinden, Samtgemeinden, Verwaltungsgemeinschaften, Verwaltungsverbände | EPCI, EPT |
  | `municipality` | government | – | Gemeinden / Städte; kreisfreie Städte and Stadtkreise with flag `county_powers` | communes; Ville de Paris (flag `county_powers`) |
  | `submunicipal` | dependent | – | – | communes déléguées / associées, arrondissements municipaux |
  | `parish` | `unknown` (the bot's flag `council_status_unknown` only restated it: dropped) | civil parishes, Welsh communities | – | – |

  `administrative` (a body without an elected council) is in the vocabulary for intermunicipal rows but unused: no feed field
  says so. Regierungsbezirke and erfüllende Gemeinde rows are not minted: Kreise get their Land as parent, Gemeinden under an
  erfüllende Gemeinde its Kreis. `level` regional_authority subnational, county county, all others local.
- **areas**: council and area are separate rows where both exist. FR région areas stay `subdivision:<iso>` (no units);
  `territory:gp` / `territory:re` stay the areas (Q17012 / Q17070) with the département and région councils as children
  (the bot's mapping is overridden in the builder and logged as `govbot_mapping_overridden`). These areas and
  `subdivision:gb-eng` are `gov_status` area_only. England's councils sit under `nation:gb`. French Guiana, Martinique and
  Mayotte (single collectivities) keep the bot's mapping to their `territory:` rows (pending a ruling).
- **dates**: FR establishment dates (INSEE mouvements) → `valid_from` + `valid_from_source` (flag
  `predecessor_none_in_source` when the COG has no predecessor); UK / DE code dates → `code_valid_from`. Dates the feed
  clears (history cutoff) are cleared here too; ids the feed prunes are never minted.
- **history** (terminated codes, `is_active` N in the feed, ended on or after the feed's HISTORY_CUTOFF 2016-01-01; UK ONS
  RGC/CHD, FR COG, DE BKG VG250 2025/2026 editions):
  - code change of the same government → not minted; the old feed id is an `entity_feed_map` row to the current entity,
    note `code_history:terminated_<date>;current=<feed id>`. UK: an official successor with the same name and subtype
    (followed through terminated successors); FR: COG mouvement 41 (département change) or 50 (chef-lieu transfer); DE:
    a single successor with the same name (name or alt_name; e.g. Hanau becoming kreisfrei);
  - a distinct government that ended → minted (same id pattern, the code it had) with `valid_to` = the code's end date (RGC
    TERM_DATE / COG end of period) and flag `is_active_false:code_terminated`; UK: successor(s) of another name or a split,
    or no link and no current unit of the same name under the same parent; FR: every other mouvement (30 suppression, 31 / 33 fusion, 32 commune nouvelle); DE: a merger or no link;
  - no link but a current same-name unit under the same parent → `feed_only`, gap `code_terminated_unresolved` (not decided);
  - an ended GB row whose parent is outside the table gets the bot's own fallback (devolved government row by the GSS
    country letter, else `nation:gb`).
- **lean rows**: empty optional fields stay empty; no `source_record_id` (the feed id is in entity_feed_map), no
  `outside_v2_scope` flag and no `parent` relation rows; `alias` = Welsh name (UK) or VG250 short name (DE) where it differs.
  Images: none (the bot has no images for these units).

## Kind `court` (approved by Full Stack, Oct 18; applied)

Minted from the Seating Charts bot's `bodies.csv` (pinned commit, see sources.csv): every kind C body becomes one entity.
- `kind` `court`; `entity_id` `court:<st>-<slug>`, lower-case and frozen. The slug is deterministic from bodies.csv `office`:
  `state_supreme_court` → `supreme`, `state_court_criminal_appeals` → `criminal-appeals` (examples: `court:pa-supreme`,
  `court:tx-criminal-appeals`). `level` state, `type` `supreme_court` / `court_of_criminal_appeals`.
- `name` is the bodies.csv `name`, copied verbatim. `source_record_id` is the bodies.csv `key`, and `source_id` cites bodies.csv.
- `parent_id` `state:<fips>`, plus a `parent` row in `entity_relations.csv` (court → state). `gov_status` is empty and the
  row carries the flag `gov_status_na:judicial_body`, the same as chambers. `feed` `inst-lane`.
- Seats, terms and holders stay in the Seating Charts files and attach to the body_key (`body_entity.csv`). Courts get no
  seat units and no GEOIDs.
- Courts the Seating Charts build excluded or dropped (build_meta.json `excluded_courts` / `dropped_courts`) are not minted.
  They are listed in `entity_gaps.csv` as gap `not_in_seating_charts`, keyed by the bot's code (for example `CA_SC`).
Still open: intermediate appellate and trial courts (not in bodies.csv; none minted).

## body_entity.csv (Full Stack, Oct 18): Seating Charts body → entity

| column | example | meaning |
|---|---|---|
| `body_key` | `us-ny-new-york-mayor` | primary key, unique: bodies.csv `key` (the join is on key only; the bot's integer `b` is never stored) |
| `entity_id` | `muni:place:3651000` | the institution entity. Several bodies may share one entity: NYC's council and mayor both point to the municipality |
| `role` | `council` | `chamber` / `court` / `council` / `mayor` / `board` (extensible) |
| `st`, `kind`, `office` | `NY`, `M`, `mayor` | copied from bodies.csv for the record |
| `match` | `file_entity_verified` | `structural` (L: st + office → chamber slot); `minted_from_body` (C); `file_entity_verified` (M: the file's `entity` exists here, is in `st`, carries the body's place GEOID in the xwalk, and city_bodies.csv lists it); `file_entity_verified_via_parent:<id>` (the GEOID is on the parent, e.g. DC council → state:11); `consolidated_government` (the file's area_only balance place → the county of its consolidated_with pair) |
| `source_record_id` | `us-ny-new-york-mayor` | the id inside the source (the bodies.csv key) |
| `source_id` | `repo-bodies-…;repo-city-bodies-…` | bodies.csv, plus city_bodies.csv for the M rows |

`entities.csv` has no body column; council and mayor entities are not created. **Officeholders and seats attach to the
`body_key`, not to the entity.** Bodies that match no entity go to `body_key_gaps.csv`
(`body_key, st, kind, office, name, reason, source_id`).

# Original proposal (kept for history; superseded where it differs from the column list above)

# Proposed schema: data-v3/inst/entities.csv (institution registry)

Approved by the orchestrator (QUESTIONS.md Q-G6). **Not built yet.** This is the proposed schema only. It lives under `data-v3/inst/` (institutions lane), not under `data-v3/geo/`.

One row per government or institution (not per place):

| column | example | meaning |
|---|---|---|
| `entity_id` | `county:01001`, `muni:place:0107000`, `town:cousub:0900104720`, `school:0100003`, `chamber:al-upper`, `us-house`, `state:01` | stable ID = kind prefix + TIGER GEOID; chambers and national bodies use fixed slugs |
| `kind` | `state`, `county`, `municipality`, `township`, `school_unified`, `school_elementary`, `school_secondary`, `chamber`, `district_seat`, `dc_council` | Q-G4: three school types, no single "school" type |
| `state_fips`, `state` | `01`, `Alabama` | |
| `name` | `Autauga County` | TIGER 2024 NAMELSAD |
| `alias` | `Autauga` | `;`-separated search aliases (v2 names, old pre-9ff4c00 school names, abbreviations) |
| `label` | `sovereign` / `incorporated` / `unincorporated` | the app's existing type labels (from PACK/XREF, read-only) |
| `gov_status` | `government` / `area_only` / `dependent` | from the 2022 Census of Governments: e.g. CT/RI counties = `area_only`; dependent school systems = `dependent` |
| `unit_layer`, `geoid`, `vintage` | `counties`, `01001`, `2024` | join to `data-v3/geo/<layer>.csv`; one row per vintage when the boundary changed |
| `geoid_alt` | `cousub:1900190000` | second GEOID when one government is both a place and a county subdivision. Geo answered Q3: such a government is **one entity carrying both GEOIDs**, and the relationship goes in the crosswalk below |
| `parent_entity_id` | `state:01` | containment for the institution search tree |
| `v2_layer`, `v2_row` | `schools`, `1` | back-link to the v2 row (from `data-v3/geo`), empty if v2 doesn't show it |
| `source`, `license` | `TIGER 2024; CoG 2022` | |

Build inputs (all read-only): `data-v3/geo/*.csv`; TIGER 2024 Gazetteer (counties, cousub, place, sld, CD, school sets); CoG 2022 Government Units Listing (government status); `PACK`/`XREF` in `v2/index.html` for labels and aliases. Expected size: about 65k rows (3,144 counties + about 22.5k cousubs + 19,465 places + 13,305 schools + 7,276 district rows (436 + 1,950 + 4,890) + chambers). That is v3 only, with no v2 load.

## Geo's answers that shape this schema (Oct 18, 2026)

- **Q3, one government with two Census GEOIDs** (place = county subdivision, consolidated city-county, independent city): this is one row in `entities.csv`. `geoid` is the primary (place) GEOID and `geoid_alt` the second. A crosswalk, `data-v3/inst/entity_geoid_xwalk.csv`, records the relationship type:

  | column | example | meaning |
  |---|---|---|
  | `entity_id` | `muni:place:1938595` | |
  | `geoid_layer`, `geoid` | `cousub`, `<10-digit state+county+cousub GEOID>` | every GEOID that names this entity, the primary one included |
  | `relation` | `coextensive` / `consolidated_city_county` / `independent_city_county_equivalent` / `primary` | how this GEOID relates to the entity |
  | `vintage` | `2024` | |
  | `source` | `TIGER 2024 place-cousub relationship file` | |

- **Q1, has its own government** is an institutions-lane attribute, not geography. It goes in `data-v3/inst/county_government.csv`, keyed by county GEOID:

  | column | example | meaning |
  |---|---|---|
  | `county_geoid` | `09001` | TIGER county GEOID (2024 vintage; a 2020-vintage row is added where the county set differs, e.g. CT planning regions) |
  | `has_own_government` | `yes` / `no` / `unknown` | `no` = an area with no county government (CT, RI, parts of MA, unorganized AK borough areas); `unknown` until a source is cited |
  | `government_note` | `county government abolished 1960; functions held by state/towns` | short free text |
  | `source` | `Census of Governments 2022, Government Units Listing` | required for every value other than `unknown` |

  `entities.csv` takes `gov_status` from this file for `kind=county`. Filling it from CoG 2022 is optional this round (geo's ruling), so the file starts as the 3,144 GEOIDs set to `unknown`. Nothing is guessed.
- **Q2, Q4, Q5** (v1 town alignment, keying to v1 towns): pending in geo's `data-v3/geo/ALIGNMENT.md` and `v1_towns.csv`. `alias` and `v2_row` will follow those once they land.
- **Q6:** geo is building the 2020-vintage GEOID tables. `vintage=2020` rows will join to them.

## Load plan and slimming (Full Stack ruling on 04227d3; applied)
- `load_manifest.csv` lists every file with its target: `db` (load into Postgres, `load_order`, `group_column`), `pack`
  (separate artifact, not loaded) or `repo` (kept in the repo, not part of this load plan).
- **DB**: `enum_feed.csv`, `enum_feed_map_status.csv`, `enum_load_group.csv`, `sources.csv`, `source_urls.csv`,
  `source_sets.csv`, then `entities.csv`, then `entity_relations.csv` and `entity_images.csv`. Load `load_group` 1 first;
  `load_group` 2 (GB / DE / FR) later behind a flag (a column, not split files: one schema per table, and the split is a
  `WHERE load_group = 1`). Group 1 also holds the 16 area rows the country layers mark `area_only` (subdivision:gb-eng, the 13
  FR région areas, territory:gp / re); their councils arrive with group 2.
- **pack**: `pack/entity_feed_map.csv`: `feed` (smallint, enum_feed), `feed_id`, `role`, `is_primary`, `entity_id`,
  `status` (smallint, enum_feed_map_status: 1 mapped, 2 feed_only, 3 unmapped), `note`, `source_set`. Key
  (`feed`, `feed_id`, `role`), unique (asserted). `role` is empty and `is_primary` 1 where a feed id has one target; a feed id
  with several targets gets each target body's role and exactly one primary, the target the feed crosswalks
  `same_government` (the others are `governs_part`). Only case: `insee_dep:69` → `county:fr-69` role `departmental_council`
  (primary: INSEE's département 69 is the Rhône) and `county:fr-69m` role `territorial_collectivity` (Métropole de Lyon,
  governs part). Boilerplate notes `minted` / `alt_code` (and a `minted;` prefix) are dropped. The DB keeps the codes as
  `code_scheme` / `code` on entities.
- **source_sets.csv** `source_set, ord, source_id`: every table's former `source_id` list (entities, relations, images, gaps,
  geoid xwalk, v2 rows, body files, pack) is a `source_set` key; `sources.csv` / `source_urls.csv` keep `source_id`.
