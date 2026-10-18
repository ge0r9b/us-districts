# File family: institution registry (data-v3/inst, institutions lane)

Files: `entities.csv`, `entity_geoid_xwalk.csv`, `entity_v2_rows.csv`, `entity_gaps.csv`, `entities_summary.json`, `sources.csv`,
`source_urls.csv`, `source_sets.csv`, `enum_*.csv`, `load_manifest.csv`, `pack/entity_feed_map.csv` (a pack, not a DB table), `entity_images.csv`, `entity_relations.csv`, `body_entity.csv`, `body_key_gaps.csv`.
Builder: `tools/inst_entities.py` (read-only inputs; deterministic). Column list and SCHEMA.sql alignment: ENTITIES_SCHEMA.md.
Format: UTF-8, one header row, stable column names (v3 reads by header). **Provenance:** every row of every file in the
family has `source_set` (a key into `source_sets.csv`, whose ordered `source_id`s are keys of `sources.csv`; until 04227d3 a `source_id` `;`-list) into `sources.csv` (source, full URL(s), licence, `retrieved_at`, pinned `commit`, `sha256`;
README_SOURCES.md); the repeated `source` / `source_url` / `retrieved_at` / `license` text columns are gone. Ids are
`<slug>-<sha8(url|commit)>`, deterministic; `--stability-test` rebuilds them a second time and compares. Open public sources only.

Build: `tools/inst_entities.py <repo> --gaz24 DIR --gaz20 DIR --cog XLSX --geojson DIR --oh-ref <data/inst-officeholders sha>
--gov-ref <data/governments sha> --world-raw DIR --foreign-ref <data/governments sha> --seating-ref <data/seating sha> [--stability-test]`. `--world-raw` is the directory `tools/inst_world.py fetch <repo> DIR`
writes (the Wikidata .rq queries + .json answers, sha256s recorded in `entities_summary.json` `world.files`). Officeholder files, county_government.csv and the Governments bot's
`data-v3/institutions/governments/local/*.csv` are read with `git show` (read only).

## What is an entity

One row per **institution** (government, governing body, later companies), no vintage. Kinds now: `nation`, `state`
(50 + DC), `territory` (US: 60/66/69/72/78 with House delegates, 74 Minor Outlying Islands; foreign dependencies; Canada's 3), `subdivision` (ISO 3166-2, non-US), `chamber` (99 state chambers + `us-house` + `us-senate`), `dc_council`, `court` (37 state high courts), `special_district` (305 TCEQ WDD districts, TX),
`county`, `municipality` (place-based government), `township` (county-subdivision government), `school_unified`,
`school_elementary`, `school_secondary`. District seats are **units** (cd / sldu / sldl GEOIDs), not entities: an officeholder
row is keyed chamber `entity_id` + `unit_layer` + `unit_geoid` + `unit_vintage` + `seat`.

`entity_id` is minted once (kind prefix + the GEOID first seen) and then frozen and opaque; it does not change when a boundary
or GEOID changes. A new id is minted only when the government itself changes, linked with `predecessor_id` / `successor_id`
(today: CT's 8 old counties → 9 planning regions, linked through the shared town FIPS codes of TIGER 2020 and 2024).

## World institutions (tools/inst_world.py; SCHEMA 62cb622 / 3c1e42d)
The **list** of which foreign institutions exist is v2's Natural Earth layers on origin/main (`v2/data/countries.js` 204 rows,
`v2/data/canada.js` 13 rows; Geo bot's files, read only, pinned by commit + sha256 in `sources.csv`). No geometry is copied: the
institution is a separate entity from the area, and **non-US places have no xwalk row, no unit and no boundary_set**.
Status and QIDs come only from Wikidata (current statements: rank not deprecated, no P582 end time):
- `nation:<iso2>` (lowercase, kind `nation`, `label` sovereign, `gov_status` government): the item holding P297 = the code is a
  sovereign state (P31 Q3624078). Not a UN member (no current P463 Q1065) → flag `not_un_member(wikidata_P463)` + gap
  (Taiwan, Vatican City), still kind `nation`, no parent. `nation:us` is unchanged (it only gets `wikidata` Q30).
- Home-part rule (Denmark): P297 DK is on Q35 Denmark, not a sovereign state; its P17 is the sovereign Kingdom of Denmark
  Q756617, which has no P297 and shares Q35's capital (P36) → `nation:dk` = Q756617 (flag + gap for review).
- `territory:<iso2>` (kind `territory`, `type` dependency): not a sovereign state; sovereign = its current P17 sovereign state,
  else P361, else the ISO 3166-2 parent code of its P300 (`NL-AW`). Parent = that sovereign's `nation:<iso2>`. No sovereign
  found → the row is **not written** (SCHEMA needs a nation parent) and is logged (`world_entity_excluded_no_sovereign`: Isle of Man).
- `nation:il` (Israel, Q801) is **added from Wikidata** (P297 IL; current sovereign state and UN member) because the Natural Earth
  list lacks it; flag `added_from_wikidata:not_in_natural_earth_list`, cites only the Wikidata source. Kosovo, Palestine, Western
  Sahara and the Faroe Islands are not in the list and are **not added**: `entity_gaps.csv` `not_in_source_list` rows, for the user to decide.
- US ISO codes (pr, gu, vi, as, mp) are never nations or `territory:<iso2>`; they stay `territory:<FIPS>` under `nation:us`
  (none are in the Natural Earth list).
- Canada: `province:ca-<code>` (kind `province`, 10) and `territory:ca-nt|nu|yt` (kind `territory`), parent `nation:ca`, QID by
  P300 `CA-<code>`; the id pattern sits in one constant (`inst_world.ca_id`).
- `name` = the Natural Earth name; the Wikidata label goes to `alias` when it differs (`Québec` / `Quebec`). `feed` = `inst-lane`.

## Governments bot foreign layer (tools/inst_foreign.py, `--foreign-ref`)
Read only from `data-v3/institutions/governments/foreign/` (nations.csv, dependencies.csv, subdivisions.csv,
iso_domestic_crosswalk.csv) plus the foreign rows of its `images.csv`, at the pinned commit. Every file has its sha256 and
the commit in sources.csv. The domestic feed is read with `--gov-ref`; both refs pin the same commit (bd0ce1a; the
nations / dependencies / subdivisions differ from bb5e342 only in `retrieved_at`; the bot's frozen-id registry is read
from `id_registry/<scope>.csv` since b198633, rows unchanged).
- **Ids already in the registry are mapped, never renamed.** That covers the 194 shared nations, the 9 foreign territories
  we had, and Canada's province/territory rows. A parent disagreement → `govbot_foreign_parent_differs`. A QID is carried
  only into an empty `wikidata`; a different QID → `wikidata_qid_conflict` (registry kept). A QID already held by another
  entity is not carried (also a conflict row).
- **`constituent_qid` and `valid_to` are carried as given; the bot's `valid_from` / `valid_from_source` become `inception` /
  `inception_source`** (empty registry value only; a different non-empty registry value is kept and logged as
  `govbot_foreign_attr_differs`). `constituent_qid` is the constituent country item under a sovereign-state QID (nation:dk
  Q35, nation:nl Q55); with it the `wikidata_qid_via_home_part_rule` gap on nation:dk is closed (the
  `wikidata_p297_item_is_home_part` flag stays as provenance). **`inception` = earliest sourced inception (Wikidata P571
  with a P248/P854 reference), not the date the current government began**: Barbados `1623-01-01` (precision year) is a
  settlement date, and UN admission dates are not used. `inception_precision` (day / month / year) is read from the form of
  the bot's string, which it writes at the Wikidata precision; year-only is stored `YYYY-01-01`. `valid_from` stays empty on
  these rows. US rows have no P571 in any available feed, so their `inception` is empty (nothing fetched).
- **Rows flagged `review_status` (nation:tw, nation:eh) are `feed_only`.** They are not minted or mapped and their gaps stay
  open, pending the user. Their subdivisions are `feed_only` too, and their images are logged as `image_entity_unmapped`
  with reason `pending_user_status_review` (not linked, not minted).
- **Every other row is minted under its own id** (`feed` governments-bot, `source_record_id` = the bot id):
  - new `nation:` rows (nation:ps; this closes the Palestine `not_in_source_list` gap);
  - new `territory:<iso2>` dependencies (including territory:fo, which closes the Faroe Islands gap, and territory:im,
    whose sovereign the bot reviewed as nation:gb, which closes the Isle of Man gaps);
  - `territory:74` (U.S. Minor Outlying Islands, level federal, parent nation:us);
  - `subdivision:<code>` rows.
  Each minted territory and subdivision gets a `parent` row in entity_relations.csv. Non-US rows get no units.
- **Kosovo stays an open `not_in_source_list` gap** (pending the user). The bot lists only Serbia's RS-KM, which is minted
  as an ordinary Serbian subdivision (`subdivision:rs-km`, parent nation:rs), as its row says.
- **Images:** the foreign flags and seals (coat-of-arms rows are role `seal`, with `usage_basis` naming P94) are merged into
  entity_images.csv. Two columns are added on every row:
  - `public` = yes only for free licences (fair-use rows stay hidden);
  - `icon` = yes on at most one public image per entity: a nation's flag, or a seal for every government below the
    sovereign level. There is no flag fallback below nation level and logos are never icons.

## Governments bot country layers: UK, Germany, France (tools/inst_foreign_local.py, `--foreign-ref`)
Read only from `foreign/gb/`, `foreign/de/`, `foreign/fr/` (units*.csv, code_xwalk.csv) at the same pinned commit;
every file has its own sources.csv row with sha256, and each row also cites the bot's upstream source ids from its
`source` column (ons_rgc, destatis_rs, bkg_vg250, insee_cog2026, insee_epci2026, ign_adminexpress, wikidata_foreign, ...).
See ENTITIES_SCHEMA.md "Country layers" for ids, kinds, gov_status and history. Feed-defect workarounds are self-checking
and logged in entities_summary.json `country_layers.workarounds`; at bd0ce1a all are no-ops: Saint-Barthélemy /
Saint-Martin communes map to `territory:bl` / `territory:mf` through the bot's own crosswalk (no QID on the commune rows);
commune SIRENs come from the DGCL table, so 215500398 / 213100068 are each on one commune; GB-ENG is area_only in the bot's
crosswalk. GP/RE:
- Guadeloupe / Réunion (ruling Oct 18): self-checking too; since 310086f the bot emits the département and région
  councils as units under the area (territory:gp / re, area_only), so the override logs `dropped`; the councils get an
  `area` relation, and the area_only crosswalk rows for codes the council also holds are dropped from the feed map.
- wikidata: carried only when no other entity holds the QID (else `wikidata_qid_conflict`); none conflicted.
- History follows the feed's HISTORY_CUTOFF (2016-01-01, read from the bot's scripts/common.py): rows ended before it are
  not in the feed and their ids are pruned in the bot's registry (`pruned` column) -> never minted here (the builder
  asserts no minted id equals one derived from a pruned id); dates the feed clears (valid_from, P571 inceptions) are
  cleared here too; communes nouvelles created on the cutoff date whose predecessors were pruned carry no flag (not
  `predecessor_pending`). DE history is limited upstream to the 2026 VG250 change; no DE row carries a `valid_from`.
- member_of (ruling on 04227d3): the bot's `member_of` column → `entity_relations.csv` relation `member_of`, method
  sourced (commune → EPCI / EPT, UK council → combined authority); a `;`-list gives one relation per body.
- Corse (ruling on 04227d3): the 360 communes' parent is the Collectivité de Corse council (`regional_authority:fr-94`, minted
  from the bot's code_xwalk insee_ctcd row, `county_powers`), which has an `area` relation to `subdivision:fr-20r`; the 19
  Corse EPCIs keep the bot's parent `subdivision:fr-20r` (like the mainland EPCIs, which sit under their région area).
- GF / MQ / YT (ruling on 04227d3): the bot's mapping is kept (the collectivité unique is the territory row).

## Governments bot feed (tools/inst_govfeed.py)
`pack/entity_feed_map.csv` (`feed, feed_id, role, is_primary, entity_id` (empty when not mapped), `status` = 1 mapped / 2 feed_only / 3 unmapped, `note`
(`match=<rule>`, `type=<bot type>`, `consolidated`, `conflict(...)`), `source_set`; feed / status are smallint codes, see ENTITIES_SCHEMA.md "Load plan") maps **every** Governments id (`state:`, `territory:`, `cog:`, `gcn:`, `fr:`, `bia:`, ...) to its registry
entity, in this order: same state/territory FIPS id (the bot's older `state:60/66/69/72/78` → `territory:<FIPS>`, logged);
school `nces_leaid` → `school:<leaid>`; GEOID (layer + geoid, TIGER 2024) → the entity holding it; CoG `cog_id` → the entity
carrying that `cog_pid6`. GEOID and CoG must agree, else a `govbot_mapping_conflict` gap and no link. Nothing is renamed on either
side; a bot id equal to a registry id that maps elsewhere would be a `govbot_frozen_id_conflict` gap (none). Unmapped ids
(special districts, federal agencies, tribes) are `feed_only:*`; the v3 loader makes them `government_other`.
Special districts (Full Stack, Oct 18): the 305 Texas districts created since CoG 2022 (`tceq_wdd:<WDD ID>`, TCEQ Water
Districts Database) are minted as kind `special_district`, id `special_district:tx-tceq-<WDD id>` (frozen; rule in
ENTITIES_SCHEMA.md), official name verbatim, parent `state:48` (+ `parent` relation), feed row status mapped
(`match=minted_special_district`), `valid_from` = the TCEQ creation date. County: `in_county` relation, method `sourced`,
note `tceq_wdd_primary_county` (291); entity `source_id` cites the bot and `tceq_wdd`; `valid_from_source` names the WDD row; 14 rows have no county in the feed → `special_district_county_unknown` gaps. CoG special
districts stay `feed_only:special_district`; when minted they use the same kind with source `cog`.
Images of ids that are feed_only by design (federal agencies `fr:`, tribes `bia:`) stay unlinked with **no**
`image_entity_unmapped` gap; Federal Register logos cite the bot's `fr_agencies` source. Unmapped feed ids that are not
feed_only by design (e.g. Mountain House CA `gcn:0649582`: incorporated 2024, TIGER 2024 has only the CDP, which is not an
entity here) keep the gap, with the feed row's reason in `detail`.
Fair-use images (`public` no, never flipped here) all carry `license`, `attribution` and `source_url`. An empty attribution is
filled with the issuing body's name, `<name> (issuing body)`, from the registry entity (else the bot row); column
`attribution_source` = `feed` / `issuing_body_name:registry_entity` / `issuing_body_name:governments_bot_row`; if no name
exists the row gets an `image_attribution_missing` gap (none today).
Free images (Full Stack, Oct 18): rows missing `source_url`, `attribution` or `license` are backfilled from the Wikimedia
Commons API (imageinfo/extmetadata; `tools/inst_commons.py fetch`, 50 titles per request, 2 s apart, maxlag 5, identifying
User-Agent), cached under `/workspace/w/inst-raw/commons/` with SHA256SUMS (the build reads only the cache, `--commons-cache`;
sources.csv row with the sha256 of SHA256SUMS): `source_url` = the Commons file page, `attribution` = Commons Artist, else
Credit (`attribution_source` commons_artist / commons_credit), `license` = LicenseShortName; never invented. A free row still
missing licence or attribution is set `public` no with an `image_free_field_missing` gap (reason in `detail`); one missing only
`source_url` keeps `public` and gets the gap. Copyrighted-free-use / attribution-only licences stay public with an attribution.
Second ruling (Full Stack, Oct 18): an attribution that is only "Unknown" ("Unknown author", "Author unknown", …) counts as
missing. A free row with no usable Artist/Credit whose Commons licence is public domain (LicenseShortName / License, from a
second cached query that also asks for License, UsageTerms, Copyrighted) gets `attribution` "Public domain, via Wikimedia
Commons", `attribution_source` commons_license, and stays public; an Unknown artist with a PD licence gets the same. The two
rows with no Commons licence (province:ca-qc arms, subdivision:jp-34 flag) were checked on their file pages (wikitext,
templates, categories, cached as v2_page_*.json): no licence template, only {{Insignia}} (a non-copyright restriction) and the
category "Files with no machine-readable license" (Quebec also has an open deletion request) → licence not determined, kept
private with that reason.
Third ruling (Full Stack, Oct 18; cache v3_*: LicenseUrl for every free file, upload histories, a Quebec search):
- free rows with no author and a Commons licence CC0 → `CC0, via Wikimedia Commons`; Copyrighted free use →
  `Copyrighted free use, via Wikimedia Commons` (both `attribution_source` commons_license);
- CC BY-SA rows with no author → TASL `<original uploader>, <file page URL>, CC BY-SA x.y` (earliest revision of
  `prop=imageinfo&iiprop=user|timestamp`; `commons_uploader`), or `Wikimedia Commons contributors, <URL>, CC BY-SA x.y` when
  the uploader is hidden (`commons_contributors`); no history → stays private;
- image overrides (`tools/inst_image_overrides.py`, explicit and logged in entities_summary.json `image_overrides`): Quebec
  arms `Coat of arms of Quebec (without crown).svg` → `Coat of arms of Quebec.svg` (the file it was extracted from;
  {{Cc-by-sa-4.0}}). An override applies only while the feed row still has the old file and the cached Commons page of the
  new file has a machine-readable free licence template, no deletion / no-licence category, a licence and an Artist; it
  drops itself (logged `dropped`) once the Governments feed already points at the new file. `note` records old, new and why.
  Nothing is edited or re-hosted. Hiroshima Prefecture flag (subdivision:jp-34): no replacement exists (search + the
  prefectural-flag category hold only this file and two flag-map stubs), so it stays private; the reason is in its gap;
- `licence_url` (after `license`): the Commons LicenseUrl, else for CC licences the canonical creativecommons.org deed;
  every CC URL is then written in the canonical form `https://creativecommons.org/licenses/<type>/<version>/[<port>/]`
  (CC0 `https://creativecommons.org/publicdomain/zero/1.0/`): https, trailing `/`, no `deed.xx`. Other licences only when
  Commons gives a URL, unchanged;
- the 7 fair-use rows credited only "Unknown" stay hidden and unchanged.
Consolidated city-counties kept as two entities (CoG code not a TIGER place: Athens-Clarke, Greeley, Louisville-Jefferson,
Butte-Silver Bow, Nashville-Davidson): the CoG id maps to the **county** entity (`status` mapped, `note` consolidated), the place
GEOID stays on the city entity, and `entity_relations.csv` (`entity_id, relation, related_entity_id, method, note, source_id`) has one
`consolidated_with` row per pair (both directions implied), cited to CoG 2022 + the Governments bot (its GEOID for the CoG unit)
+ county_government.csv. The other 72 consolidated / independent-city county GEOIDs are folded into ONE entity (xwalk relation
`consolidated_city_county` / `independent_city_county_equivalent`), so no relation row is needed; Honolulu (15003) has no
Governments-bot GEOID for CoG 183701, so no second entity and no relation (gap kept).
Builder rule (Full Stack, Oct 18): every county in a `consolidated_with` relation gets `gov_status` government and loses the
`gov_status_unknown:consolidated_government_not_linked_to_tiger_code` flag (the relation is the link); a county without a relation
(Honolulu) keeps the flag and its `gov_status_unknown` gap.
Carried onto mapped entities: `wikidata` as `wikidata:Q…` (nullable, unique: a QID on several entities is left empty on all of
them and logged as `wikidata_qid_duplicate`; only when every bot row of the entity agrees; registry value wins on a conflict),
ceased units (`valid_to` + flag `is_active_false:governments_bot_<ids>`, only when all of the entity's bot rows ceased),
new units (`valid_from` = the sourced incorporation / creation date + flag `not_in_cog2022`). `entity_images.csv`: seals and flags (institution-only attributes, never
used by the geo filter): `entity_id, role` (seal / flag / logo), `file` (Commons file name), `license`, `fair_use` (yes exactly when
the license is `fair-use`; such rows must carry `usage_basis`, checked), `usage_basis`, `source_url`, `attribution`, then extras
`licence_url, public, icon, attribution_source, feed_id, commons_url, wikidata_qid, retrieved_at, source_id, note`. `LicenseRef-Copyright` rows are fair_use = no but not free either. The bot's `sources.csv` rows are added to
ours as a union on the bot's own ids (`cog2022`, `wikidata_images`, ...); a collision with one of ours would stop the build.

## SCHEMA b66f889 alignment
- `source_urls.csv` (source_id, ord, url, label): every URL of every source; multi-URL sources get labels (house / senate,
  cousub / place, repo file / upstream, member detail).
- `source_record_id`: entities = the id inside the first cited source (GEOID / FIPS for TIGER, Gazetteer and ANSI rows; QID for
  Wikidata rows; empty for chambers and nation:us); xwalk = the GEOID where the cited source is Census. Officeholder files carry
  their own (data/inst-officeholders); county_government.csv: govbot_entity_id or cog_pid6.
- `feed` stays inside the §15.1 map (`tiger/cog`, `inst-lane`; asserted by the builder).
- Seat units for officeholder rows without a TIGER district, and NH floterial member links: data/inst-officeholders step 7
  (README_OFFICEHOLDERS.md).

## Seating Charts bodies: body_entity.csv and courts (tools/inst_bodies.py)
Input: the Seating Charts bot's committed `data-v3/seating/bodies.csv`, `build_meta.json` and `city_bodies.csv` at the pinned
`--seating-ref` commit (branch data/seating), read with `git show`. sources.csv records each file's commit and sha256.
The join is on bodies.csv `key` only. `body_entity.csv` (`body_key` PK, `entity_id`, `role`, `st`, `kind`, `office`,
`match`, `source_record_id`, `source_id`) links every body to one entity. Column rules are in ENTITIES_SCHEMA.md.
- **L (role chamber), structure only, never names:** US `us_senate` → `us-senate`, US `us_house` → `us-house`,
  `<st>` `state_senate` / `state_legislature` (sldu) → `chamber:<st>-upper`, `<st>` `state_house` (sldl) → `chamber:<st>-lower`.
  st, office and the entity's type are asserted on every match. Assemblies, the NJ General Assembly and Houses of Delegates
  (MD, VA, WV) are office `state_house`. Nebraska's `us-ne-legislature` (office state_senate) → `chamber:ne-upper` (type
  unicameral) is the only key outside the `us-<st>-senate|house` pattern, and the summary lists it under `bodies.judged`.
- **C (role court):** each court body is minted as `court:<st>-<slug>` (kind `court`, approved Oct 18). Courts the bot
  excluded or dropped are `entity_gaps.csv` `not_in_seating_charts`.
- **M (roles council / board / mayor):** the file's `entity` is a claim. It is used only after it is verified: the entity
  exists here and is in state `st`; the body's place `geoid` is a place GEOID of that entity in entity_geoid_xwalk, or of
  its parent (DC's council sits under `state:11`, which carries place 1150000 as `federal_district_city`); and
  city_bodies.csv (read-only cross-check) lists the geoid. A council and its mayor share one entity; no council or mayor
  entities are created. Role `board` applies when the key ends in `-board-of-supervisors` (San Francisco).
- **Consolidated governments** (rule applied the same way to all four): a body goes to the entity that holds the
  consolidated government.
  - San Francisco and Indianapolis: `muni:place:0667000` and `muni:place:1836003` already carry the county GEOID
    (06075 / 18097, xwalk `consolidated_city_county`) and have `gov_status` government. They are single entities, so no
    relation is needed and none is added.
  - Nashville and Louisville: bodies.csv names the balance places `muni:place:4752006` / `2148006`, which here are
    `area_only` (TIGER FUNCSTAT F). Per the Oct 18 ruling, the CoG government is mapped to the county side of their
    `consolidated_with` pair, so the metro council and mayor map to `county:47037` / `county:21111` (match
    `consolidated_government`; listed under `bodies.judged`).
- **DC:** `us-dc-washington-council` → `chamber:dc-council` (role council). `us-dc-washington-mayor` → `state:11`, the DC
  government entity (gov_status government, CoG 124214, carries place 1150000, county 11001 and cousub 1100150000).
- **Officeholders and seats attach to `body_key`, not to the entity.** An entity can carry several bodies with different roles.
- A body that fails any rule goes to `body_key_gaps.csv` with a reason.

## How the rows are built (all links by Census code, never by name)

- **Municipalities and towns.** Candidates: every incorporated place (TIGER CLASSFP C*), every county subdivision with a
  governmental FUNCSTAT (A/B/C/G) or a CoG 2022 code, plus every place or county subdivision a v1/v2 row carries.
  - A place and a county subdivision with the same state + 5-digit FIPS code are one Census-coded entity: one row, place
    GEOID primary, county subdivisions in the xwalk. Example: Chicago = place 1714000 + cousubs 1703114000 (Cook) and
    1704314000 (DuPage).
  - County-subdivision-only governments with one FIPS code across counties are one entity.
  - Geo's `town_pairs.csv` "same" pairs (mutual overlap ≥ 0.9) merge only when CoG 2022 lists just one of the two codes
    (23 pairs, e.g. Hartford city / Hartford town). When CoG lists both as governments (13 pairs, e.g. Berwyn city /
    Berwyn township) they stay two entities, flagged `coextensive_separate_government`.
- **Consolidated city-counties and independent cities** (county_government.csv: no county government, the CoG municipal
  unit's code is a TIGER place): the county GEOID joins the city entity. That covers 72 counties (VA independent cities,
  Baltimore, St. Louis, SF, Denver, Philadelphia, NYC's 5 boroughs, ...). DC is one entity, `state:11`, carrying place
  1150000, county 11001 and cousub 1100150000. In 6 cases the CoG code is not in TIGER 2024 (Athens-Clarke, Honolulu,
  Greeley, Louisville, Butte-Silver Bow, Nashville-Davidson). Those counties stay county entities with `gov_status` empty
  and a flag; the cases are listed in `entity_gaps.csv`.
- **gov_status.**
  - CoG 2022 code match → `government`.
  - TIGER FUNCSTAT G with no CoG unit → `dependent` (Iowa townships, NYC boroughs as cousubs).
  - FUNCSTAT F/I/N/S → `area_only`.
  - Counties: from county_government.csv.
  - Schools: from the Governments bot (`--gov-ref`, `local/<ST>.csv`): its `nces_leaid` is the NCES LEA ID = the TIGER
    school GEOID, joined by code; bot `independent` → `government`, `dependent` → `dependent`; `cog_pid6` = the bot's
    `cog_id`. Schools without a bot row stay empty and flagged `gov_status_unknown:no_governments_bot_row_with_this_nces_leaid`;
    bot rows disagreeing on one LEA ID would be flagged and listed as gap `school_gov_status_conflict`.
  - Chambers: not applicable.
- **parent_id.**
  - school, county and chamber → state;
  - municipality or town → county (when ≥ 98 % of it is in one county), else state;
  - state → nation:us; us-house and us-senate → nation:us; court → state (also a `parent` row in entity_relations.csv).

## entity_geoid_xwalk.csv

One row per entity × unit_layer × GEOID × vintage. `boundary_set` = the boundary-set slug of the unit (same tokens as
Election, DATA_LOADING Q-E12): `v2-2024` for every TIGER 2024 unit (the v2 lines); `tiger-2020-county` for the 8 CT county
units of TIGER 2020 (same lowercase-hyphen form; not yet a registered set). `relation`: `primary`, `coextensive` (mutual ≥ 0.9), `also_cousub`
(part of a place split across county subdivisions), `consolidated_city_county`, `independent_city_county_equivalent`,
`consolidated_town_city`, `federal_district_city`. `overlap` gives the geometry (equal / split / contained) and the two
`share_*` columns the area shares on TIGER 2024 (geo lane GeoJSON, EPSG:6933).

## entity_v2_rows.csv / entity_gaps.csv

`entity_v2_rows.csv` maps every v2 row (counties, schools, senate, statehouse, ushouse incl. the 2020 pairings, states, parts,
places, IA towns) and every v1 town/place row to its entity (district rows → chamber entity + unit). `entity_gaps.csv` lists
orphans, unknowns, excluded "not defined" TIGER records and CoG 2022 units not linked by code.

## Taking external feeds (governments-bot, companies-bot, user uploads)

Feeds live in `data-v3/institutions/` (owned by those bots; this lane does not write there). A feed row maps onto
entities.csv like this:

| feed field | entities.csv |
|---|---|
| feed's stable id | `entity_id` = `<feed prefix>:<feed id>` (e.g. `cog:<pid6>` from the Governments bot); never reused |
| user upload | moderator-approved uploads get `entity_id` = `usd:<uuid>` with `feed` = `user-upload`. When one later gets a Wikidata QID it is re-keyed to `wikidata:Q…` and the `usd:` id is kept in `alias` (and stays resolvable) |
| scraped brand without a QID | gets **no** entity_id (not written to entities.csv) |
| parent of national rows | `nation:us` (the nation row; the Governments bot uses it as `parent_id`) |
| entity type | `kind` (open vocabulary; feed kinds now: `company`, `nonprofit`, `fund`, `brand`, plus the bot's government kinds) |
| parent / owner | `parent_id` (generic: a corporate parent, or a government parent) |
| jurisdiction | `state_fips`, `state` (empty if national or foreign) |
| GEOID, if a government | an `entity_geoid_xwalk.csv` row (relation `primary`). If the GEOID already belongs to a `tiger/cog` entity, the feed row is an alias of that entity, not a new one |
| name, other names | `name`, `alias` |
| start / end, mergers | `valid_from`, `valid_to`, `predecessor_id`, `successor_id` |
| provenance | `feed` = `governments-bot` / `companies-bot` / `user-upload`; the feed row's source becomes a `sources.csv` row, referenced by `source_id` |

## Sources and licences

| source | URL | licence |
|---|---|---|
| Census 2024 / 2020 TIGER Gazetteer (counties, cousubs, places, CD119/116, SLDU/SLDL, UNSD/ELSD/SCSD) | https://www2.census.gov/geo/docs/maps-data/data/gazetteer/ | public domain |
| Census TIGER/Line 2024 county subdivisions + places (FUNCSTAT, CLASSFP, geometry; via data-v3/geo GeoJSON) | https://www2.census.gov/geo/tiger/TIGER2024/ | public domain |
| Census 2022 Census of Governments, Government Units Listing | https://www2.census.gov/programs-surveys/gus/datasets/2022/govt_units_2022.ZIP | public domain |
| ANSI/FIPS state codes | https://www.census.gov/library/reference/code-lists/ansi.html | public domain |
| Governments bot, data-v3/institutions/governments (school gov_status, nces_leaid; county check via county_government.csv) | this repo, origin/data/governments (pinned commit in sources.csv) | public domain (from CoG) |
| data-v3/geo tables (v2 row links), data-v3/inst county_government.csv and officeholder files | this repo (pinned commits in sources.csv) | as listed per file |

## Flags vocabulary (`entities.csv` `flags`; `;` separates flags, `,` separates values inside one flag)

| flag | meaning |
|---|---|
| `gov_status_unknown:tiger_funcstat_<A/B/C>_no_cog2022_code_match` | TIGER says active government, but no CoG 2022 unit has this FIPS code; `gov_status` left empty |
| `gov_status_unknown:consolidated_government_not_linked_to_tiger_code:cog_pid6=<id>` | a consolidated city-county whose CoG municipal code is not a TIGER 2024 place and that has no `consolidated_with` relation; county kept, `gov_status` empty (dropped once a relation exists) |
| `gov_status_unknown:not_in_cog2022_scope` | territory: CoG 2022 does not cover territories |
| `gov_status_unknown:no_governments_bot_row_with_this_nces_leaid` | school district with no Governments-bot row carrying its NCES LEA ID |
| `gov_status_unknown:governments_bot_rows_disagree` | several bot rows on one LEA ID with different gov_status (none in this build) |
| `gov_status_na:legislative_chamber` / `gov_status_na:legislative_body_of_state:11` / `gov_status_na:judicial_body` | not a government in the CoG sense: a chamber / the DC Council / a court |
| `tiger_funcstat:<A/B/C/F/G/I/N/S>` | county: TIGER 2024 FUNCSTAT, kept for the CoG cross-check |
| `tiger_funcstat_G:active_government_subordinate_to_another_unit` | cousub/place FUNCSTAT G with no CoG unit; `gov_status=dependent` |
| `tiger_funcstat_F:fictitious_entity`, `tiger_funcstat_I:inactive_governmental_unit`, `tiger_funcstat_N:nonfunctioning_legal_entity`, `tiger_funcstat_S:statistical_entity` | FUNCSTAT says no functioning government; `gov_status=area_only` |
| `tiger_funcstat_I_but_in_cog2022`, `tiger_funcstat_N_but_in_cog2022` | TIGER says inactive/nonfunctioning, CoG 2022 still lists a government (CoG wins: `government`) |
| `not_in_cog2022` | no CoG 2022 unit with this code |
| `cog2022_is_active_N` | the CoG unit linked by code has IS_ACTIVE = N |
| `coextensive_separate_government:<entity_id>` | geo town_pairs "same" area, but CoG lists both as governments: two entities, this is the other one |
| `consolidated_government_covers_county:<county>(primary_place_is_smaller,CoG_lists_the_place_code)` | consolidated government whose place GEOID is smaller than the county it governs (balance-of-county cases) |
| `spans_counties:<geoid>,<geoid>` | municipality/town < 98 % in one county, so `parent_id` = state; the counties it spans |
| `chamber_name_generic` | chamber name is the generic "<State> Senate / House", not the official body name |
| `outside_v2_scope:territory_with_house_delegate` | territory: included only because it sends a House delegate |
| `vintage_2020_only:replaced_by_ct_planning_regions_2022` | CT county: only in TIGER 2020 |
| `valid_to_not_recorded:last_tiger_vintage_here_2020` | end date unknown; last seen in TIGER 2020 |
| `replaced_by_planning_regions_in_tiger_2022` | see `successor_id` |
| `not_un_member(wikidata_P463)`, `not_sovereign_state(wikidata_P31)`, `sovereign_via_wikidata_<P17/P361/P300>:<QIDs>`, `wikidata_p297_item_is_home_part:<QID>(...)` | world rows: Wikidata status used (see World institutions) |
| `outside_v2_scope:no_unit_no_boundary_set` | world row: no xwalk unit, no boundary_set (SCHEMA 62cb622) |
| `gov_status_unknown:outside_cog2022_scope` | foreign territory / Canadian province or territory: no CoG-type government status source |
| ~~`council_status_unknown`~~ | dropped (04227d3 ruling): UK civil parishes / Welsh communities now carry `gov_status` `unknown`, which says the same |
| `gov_status_unknown:council_not_in_feed` | DE Gemeindeverband: the feed gives its designation only, not whether it has a council; `gov_status` `unknown`, gap `intermunicipal_council_unknown` |
| `county_powers` | a municipality that also carries county / département powers (DE kreisfreie Stadt / Stadtkreis, Ville de Paris) or a région council governing départements (Collectivité de Corse) |
| `is_active_false:code_terminated` | country layers: a distinct government that ended (terminated code, not a code change); `valid_to` = the code's end date |
| `predecessor_none_in_source` | the row has a sourced `valid_from` (FR creation / commune nouvelle) and the COG lists no predecessor (e.g. DOM communes 1946, Mayotte 2011) |
| `predecessor_pending` | reserved: a sourced `valid_from` whose predecessor the feed does not carry yet; not used (pruned / cleared links are never pending; no DE row has a `valid_from`) |
| `epci_spans_regions`, `no_epci`, `qid_is_shared_area_item:<QID>`, `cauth_from_district_lookup`, `not_in_vg250`, `verband_not_in_vg250`, `kreisfrei_from_ars_structure`, `no_member_in_destatis_<date>` | carried from the Governments bot country layers (see its SCHEMA.md) |
| `is_active_false:governments_bot_<ids>` | the Governments bot marks the unit ceased (changes_since_cog2022.csv); `valid_to` set |
| `xwalk_partial_overlap`, `county_share_unmeasured`, `multiple_cog_units`, `officeholder_entity_id_alias`, `officeholder_entity_id_missing`, `name_missing`, `no_geoid_in_gazetteer`, `no_tiger_geoid`, `county_area_governed_by_cog_municipal_unit` | defined by the builder; no row of the current build carries them |

`entity_gaps.csv` `gap` values: `orphan_v2_row`, `orphan_officeholder_unit`, `officeholder_unit_without_tiger_geoid`,
`cog2022_unit_not_linked_by_code`, `gov_status_unknown`, `excluded_not_defined` (TIGER "not defined"/water pseudo-units),
`consolidated_county_cog_code_not_in_tiger`, `consolidated_county_no_government_linked`,
`same_code_place_cousub_overlap_unmeasured`, `town_pair_same_neither_in_cog`, `school_gov_status_conflict`; world:
`wikidata_p297_several_items`, `wikidata_qid_via_home_part_rule`, `territory_sovereign_unknown`, `nation_not_un_member`,
`world_entity_excluded_no_sovereign`, `wikidata_qid_missing`, `wikidata_status_ambiguous`, `territory_sovereign_several_candidates`;
Governments feed: `govbot_mapping_conflict`, `govbot_mapping_ambiguous`, `govbot_frozen_id_conflict`, `govbot_territory_key_differs`,
`govbot_ceased_partial`, `govbot_ceased_dates_disagree`, `govbot_new_unit_not_in_registry`, `govbot_registry_id_not_in_files`,
`wikidata_qid_conflict`, `wikidata_qid_duplicate`, `image_entity_unmapped`, `image_fair_use_inconsistent`;
source list: `not_in_source_list`; Seating Charts: `not_in_seating_charts`; foreign layer: `govbot_foreign_parent_differs`, `govbot_foreign_parent_missing`, `govbot_foreign_attr_differs`; special districts: `special_district_county_unknown`; images: `image_attribution_missing`; country layers:
`intermunicipal_council_unknown`, `govbot_mapping_overridden`, `code_terminated_unresolved`; defined for the feed-defect
workarounds (none at bd0ce1a): `govbot_unit_duplicates_registry`, `siren_bad_join`, `govbot_xwalk_relation_overridden`.
`feed` values: `tiger/cog` (built here from TIGER + CoG), `inst-lane` (nation, chambers, DC Council, world nations/territories/provinces); later `governments-bot`,
`companies-bot`, `user-upload`.

Counts in the current build (122,329 entities: nation 196, state 51, territory 52, province 10, chamber 101, dc_council 1,
court 37, subdivision 3,480, county 3,496, municipality 66,245, township 18,076, school_unified 10,872, school_elementary
1,952, school_secondary 481, special_district 305, regional_authority 32, local_authority 403, intermunicipal 2,428,
submunicipal 2,621, parish 11,490; country layers GB 11,937 / DE 12,208 / FR 39,965, of them 1,215 ended
(is_active_false:code_terminated); 1,881 gap rows; 197,797 pack feed-map rows (feed_only 40,691, mapped 156,132, unmapped 974); gov_status unknown 16,614, empty (not applicable) 139; load_group 1: 58,219 entities, 2: 64,110; 9,846 images
(no|flag 1, no|logo 141, no|seal 4,433, yes|flag 1,782, yes|seal 3,489 as public|role; 3,381 icons; licence_url on 1,315 rows (all from Commons
LicenseUrl); Commons backfill: source_url 4,725; attribution: 385 commons_license (PD 381 incl. 268 Unknown, CC0 2,
Copyrighted free use 2), 25 commons_uploader, 18 Commons Credit for an Unknown author; Quebec arms: the feed now carries
Coat of arms of Quebec.svg (override dropped); 1 free row private: subdivision:jp-34 flag, no determinable licence); 40,554 relations (member_of 35,112, parent 3,857, predecessor 1,272, in_county 291, area 17, consolidated_with 5); 198 body_entity rows, 0 body_key
gaps; wikidata on 42,249 entities; valid_from on 321 entities (305 special districts:
TCEQ creation date; 16 new units: incorporation dates; valid_from_source on all 321); inception on 173 (day 139, year 34), all foreign layer; constituent_qid on 2). `flags` tokens, grouped by the text before the first `:`:
`outside_v2_scope:no_unit_no_boundary_set` 4,037; `gov_status_unknown:outside_cog2022_scope` 3,536; `tiger_funcstat:A` 3,031;
`not_in_cog2022` 1,924; `tiger_funcstat_G` 1,603; `spans_counties` 899;
`gov_status_unknown:no_governments_bot_row_with_this_nces_leaid` 375; `tiger_funcstat_F` 152; `tiger_funcstat_I` 127;
`gov_status_na:legislative_chamber` 101; `chamber_name_generic` 98; `cog2022_is_active_N` 90;
`gov_status_unknown:tiger_funcstat_A_no_cog2022_code_match` 56; `tiger_funcstat_I_but_in_cog2022` 39;
`gov_status_na:judicial_body` 37; `coextensive_separate_government` 26; `is_active_false` 24; `tiger_funcstat:N` 23;
`tiger_funcstat_N` 20; `not_un_member(wikidata_P463)` 11; `tiger_funcstat:S` 11; `not_sovereign_state(wikidata_P31)` 9;
`sovereign_via_wikidata_P17` 9; `gov_status_unknown:not_in_cog2022_scope` 6; `tiger_funcstat:C` 6;
`outside_v2_scope:territory_with_house_delegate` 5; `consolidated_government_covers_county` 4; CT flags 8 each; one each of
`added_from_wikidata`, `gov_status_na:legislative_body_of_state`,
`gov_status_unknown:consolidated_government_not_linked_to_tiger_code`,
`gov_status_unknown:tiger_funcstat_C_no_cog2022_code_match`, `multiple_cog_units`, `tiger_funcstat:G`,
`tiger_funcstat_N_but_in_cog2022`, `tiger_funcstat_S`, `un_observer(governments_bot)`, `wikidata_p297_item_is_home_part`.
Gap rows by `gap`: `gov_status_unknown` 433; `cog2022_unit_not_linked_by_code` 57; `image_free_field_missing` 1; `excluded_not_defined` 49; `image_entity_unmapped` 44;
`officeholder_unit_without_tiger_geoid` 49; `orphan_v2_row` 28; `not_in_seating_charts` 15; `special_district_county_unknown` 14; `govbot_new_unit_not_in_registry` 13;
`nation_not_un_member` 2; `not_in_source_list` 2;
`same_code_place_cousub_overlap_unmeasured` 2; one each of `consolidated_county_cog_code_not_in_tiger`,
`govbot_ceased_partial`, `wikidata_p297_several_items`.
