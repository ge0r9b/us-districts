# data-v3/institutions/companies: open questions (for the Institution filter / v3 Full Stack lane)

1. **Location of this folder.** Institutions data so far lives in `data-v3/inst/` (branch `data/inst-entities`); this lane was assigned
   `data-v3/institutions/companies/`. Keep it here, or move to `data-v3/inst/companies/`?
2. **entity_id style.** Here `cik:<n>` for SEC ticker filers and `lei:<LEI>` for the rest, frozen once minted (an SEC company keeps `cik:` after an LEI is
   found). `data-v3/inst` uses kind prefixes (`county:01001`) and SCHEMA.sql examples use `us-pa-...`. OK to keep scheme:id for companies, or prefix `company:`?
3. **kind mapping.** SCHEMA.sql `entity.kind` allows `company`, `brand`, `subsidiary`, `other`. Should GLEIF-only children be `subsidiary`
   (they all have a parent) and SEC filers `company`? Where do `nonprofit` and funds (`type=other`) go: `other`, or a new kind?
4. **gov_kind / has_region.** Assume `gov_kind='private'`, `has_region=false` for every row here. Should an HQ point (lat/lon) be an `entity_unit`
   link to the county/place containing it, or just entity attributes?
5. **lat/lon.** Empty in this pull. OK to geocode US HQ addresses with the Census Geocoder batch API (public, US government work), storing
   match quality + source per row? Foreign HQs would stay empty.
6. **Scope / size.** This pull = SEC ticker list (8,030) + GLEIF entities in active consolidation relationships touching the US (~38k). All ~364k active US LEIs
   would be ~60 MB uncompressed. Do you want the full US LEI set (as a separate gz file), or only entities reachable from a company the filter shows?
   "Full EDGAR company list" was read as the ticker list; EDGAR's `cik-lookup-data.txt` (~1M names incl. individuals and funds) was left out.
7. **CIK↔LEI coverage.** Only 1,161 of 8,030 SEC companies have an LEI link (26 from the SEC `lei` field, the rest from Wikidata). No name matching was
   done. Is a reviewed candidate file (exact normalized name + same state of incorporation, not merged into companies.csv) acceptable as a next step?
8. **Relationship model.** `parent_id` = GLEIF direct consolidation parent, `ultimate_parent_id` = ultimate. Exhibit 21 subsidiaries (next pass) are
   name-only (no LEI/CIK): mint `ex21:<parent cik>:<n>` ids and keep them in relationships.csv only, or add them to companies.csv?
9. **Committed format.** Outputs are `*.csv.gz` (3.9 MB + 1.5 MB). OK for the v3 loader, or do you want plain CSV split by state / letter?
10. **Alias / search names.** Should tickers and SEC `formerNames` go into an alias column (`;`-list, as in entities.csv) for the institution search?
