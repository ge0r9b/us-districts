# data-v3/institutions/companies: schema (draft, first pull Oct 18, 2026)

Status: **draft for review** by the Institution filter / v3 Full Stack lane. Built by `scripts/build.py` on branch `data/companies`.
UTF-8 CSV, one header row, read by header name. Files above ~5 MB are committed gzipped (`*.csv.gz`), as in `data-v3/geo`.
Columns after `source_date` (companies) are additive extras that readers may ignore.
Nothing is estimated or matched by name: every value comes from the cited source; unknown = empty.

Target in `docs/v3/SCHEMA.sql` (origin/v3/plan): `entity` with `kind in ('company','brand','subsidiary','other')`,
`gov_kind = 'private'`, `has_region = false`, `parent_id` → entity. See "Open questions" at the end.

## companies.csv(.gz): one row per legal entity

| # | column | example | meaning |
|---|---|---|---|
| 1 | `entity_id` | `cik:320193`, `lei:549300B47NZODRMG3D47` | `scheme:id`. SEC ticker-list filers get `cik:<CIK without leading zeros>` (even when an LEI is known); every other entity gets `lei:<LEI>`. Minted once and frozen (same rule as `data-v3/inst/ENTITIES_SCHEMA.md`); later passes add cross-IDs, they never re-key a row |
| 2 | `name` | `Apple Inc.` | SEC conformed name for `cik:` rows, GLEIF `Entity.LegalName` otherwise |
| 3 | `type` | `company` / `nonprofit` / `other` | `nonprofit` only when the GLEIF ELF legal form says so (nonprofit, not-for-profit, nonstock, religious corporation) and SEC does not list the entity as an operating issuer (conflict is flagged). `company`: SEC `entityType=operating`, or GLEIF category GENERAL/BRANCH/SOLE_PROPRIETOR. `other`: funds, government entities, SEC non-operating filers. Empty = no source record |
| 4 | `legal_form` | `Business Corporation` | ISO 20275 ELF name for GLEIF `EntityLegalFormCode` (GLEIF ELF list), else GLEIF `OtherLegalForm` |
| 5 | `jurisdiction` | `US-DE`, `GB`, `KY` | ISO 3166 (sub)division of incorporation. SEC `stateOfIncorporation` when it is a US state/territory code, else GLEIF `LegalJurisdiction` |
| 6 | `state_of_incorporation` | `DE`, `E9` | raw SEC EDGAR code (US USPS code or EDGAR foreign code), or the state part of a GLEIF `US-xx` jurisdiction |
| 7 | `hq_address` | `ONE APPLE PARK WAY, CUPERTINO, CA, 95014` | SEC business address (cik rows) else GLEIF headquarters address; `, `-joined |
| 8 | `hq_state` | `CA` | USPS code of a US HQ; empty when HQ is outside the US |
| 9-10 | `lat`, `lon` | | **empty in this pull** (no geocoding yet; see open questions) |
| 11 | `parent_id` | `lei:...` / `cik:...` | GLEIF level 2 direct accounting-consolidation parent (`IS_DIRECTLY_CONSOLIDATED_BY`, ACTIVE) |
| 12 | `ultimate_parent_id` | | GLEIF level 2 ultimate parent (`IS_ULTIMATELY_CONSOLIDATED_BY`, ACTIVE) |
| 13 | `lei` | `HWUPKR0MPOU8FGXBT394` | ISO 17442 LEI |
| 14 | `cik` | `320193` | SEC Central Index Key |
| 15 | `wikidata_qid` | `Q312` | `;`-list if Wikidata has several items (flagged) |
| 16 | `state_registry_id` | `RA000602:2927442` | GLEIF `RegistrationAuthorityID:RegistrationAuthorityEntityID` for US-jurisdiction entities (RA000602 = Delaware Division of Corporations; codes per the GLEIF Registration Authorities list) |
| 17 | `source` | `sec:submissions;gleif:lei-cdf;gleif:rr-cdf;wikidata` | `;`-list of source codes (table below) |
| 18 | `source_url` | `https://data.sec.gov/submissions/CIK0000320193.json;https://api.gleif.org/api/v1/lei-records/...` | `;`-list, per-record URL for each source |
| 19 | `source_date` | `2026-10-18` | newest retrieval / publish date among the row's sources |
| 20+ | `ticker`, `exchange`, `sic`, `sec_entity_type`, `gleif_category`, `legal_form_code`, `entity_status`, `lei_registration_status`, `cik_lei_link`, `flags` | | extras. `cik_lei_link` = `sec` (SEC submissions `lei` field) or `wikidata` (one item carrying both P5531 and P1278). `flags` = `;`-list of review items (below) |

## relationships.csv(.gz): one row per GLEIF level-2 relationship

| column | meaning |
|---|---|
| `child_id`, `parent_id` | `entity_id`s in companies.csv (always present there) |
| `relationship` | `direct_parent` / `ultimate_parent` (GLEIF RR `IS_DIRECTLY_` / `IS_ULTIMATELY_CONSOLIDATED_BY`). Exhibit 21 rows will be `ex21_subsidiary` |
| `child_lei`, `parent_lei` | raw node ids |
| `start_date` | RR `RELATIONSHIP_PERIOD` start date, if reported |
| `relationship_status`, `registration_status` | RR status (all ACTIVE in this pull) and RR registration status (PUBLISHED / LAPSED) |
| `accounting_standard` | RR qualifier category (e.g. `US_GAAP`, `IFRS`) when reported |
| `source`, `source_url`, `source_date` | `gleif:rr-cdf`, GLEIF API relationship URL for the child, golden-copy publish date |

## Sources

| code | source | licence |
|---|---|---|
| `sec:company_tickers` | https://www.sec.gov/files/company_tickers.json, `company_tickers_exchange.json` | US government work |
| `sec:submissions` | https://data.sec.gov/submissions/CIK##########.json (name, entityType, SIC, stateOfIncorporation, business address, lei) | US government work |
| `gleif:lei-cdf` | GLEIF Golden Copy LEI-CDF 3.1 full file (URL + publish time in `summary.json` / `raw/gleif.meta.json`); per row `https://api.gleif.org/api/v1/lei-records/<LEI>` | CC0 1.0 |
| `gleif:rr-cdf` | GLEIF Golden Copy RR-CDF 2.1 (level 2 relationships) | CC0 1.0 |
| (ELF names) | https://api.gleif.org/api/v1/entity-legal-forms (ISO 20275) | CC0 1.0 |
| `wikidata` | Wikidata Query Service, items with P5531 (CIK) and/or P1278 (LEI) | CC0 1.0 |

SEC requests send `User-Agent: us-districts-data <contact email>` (override with `SEC_USER_AGENT`) at ≤ 8 req/s, per SEC fair-access rules.

## Scope of this pull
- every CIK on the SEC ticker list (`company_tickers_exchange.json`): operating companies and other filers with a current ticker;
- every GLEIF entity on either side of an ACTIVE `IS_DIRECTLY_/IS_ULTIMATELY_CONSOLIDATED_BY` relationship where at least one
  side is a US entity (legal jurisdiction `US*`, or legal / HQ address country US). Foreign parents and foreign subsidiaries of US entities are included so every `parent_id` resolves.
- Not included: US LEIs with no level-2 relationship (~330k), fund relationships (`IS_FUND-MANAGED_BY`, `IS_SUBFUND_OF`, `IS_FEEDER_TO`),
  branch relationships, GLEIF reporting exceptions (no-parent reasons), SEC filers without a ticker, Exhibit 21 (next pass).

## Flags
`wikidata_lei_differs:<lei>`, `wikidata_multiple_lei:<a|b>`, `wikidata_lei_rejected_jurisdiction:<lei>:<sec>|<gleif>` (Wikidata-only CIK-LEI link dropped because SEC and GLEIF disagree on state of incorporation; usually the item merges a holding company with its bank/subsidiary), `gleif_legal_form_nonprofit_vs_sec_operating`, `lei_shared_by_ciks:<lei>:<cik|cik>` (link not used), `lei_not_in_gleif:<lei>` (link not used),
`sec_foreign_incorporation_code:<EDGAR code>`, `jurisdiction_sec_vs_gleif:<sec>|<gleif>`, `multiple_wikidata_items`, `no_submissions_record`.

## Rebuild
```
cd data-v3/institutions/companies/scripts
python3 fetch_sec.py && python3 fetch_gleif.py && python3 fetch_elf.py && python3 fetch_wikidata.py && python3 build.py
```
Raw files go to `raw/` (gitignored, ~0.7 GB). `CONTACT_EMAIL` / `SEC_USER_AGENT` / `COMPANIES_RAW` env vars override defaults.
