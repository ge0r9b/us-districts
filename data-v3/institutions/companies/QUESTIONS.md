# data-v3/institutions/companies: open questions (brands + locations)

1. ~~kind for brands~~ resolved (5029c30/8639fe1): `brand`, `organization`/`company`.
2. ~~company_locations~~ resolved: built (`company_locations.csv.gz`).
3. **Sheraton / St. Regis parents.** Both P749 statements (Starwood, Marriott International) have no dates on Wikidata; kept and flagged for review. Add P580/P582 upstream on Wikidata?
4. **Walgreens / Sycamore.** Wikidata still gives Walgreens → Walgreens Boots Alliance and WBA has no P749/P127, so nothing shows the 2025 Sycamore Partners take-private. Leave as Wikidata says, or edit Wikidata upstream first?
5. **Marriott v5 provenance.** ATP now wins wherever it has a value; 400 US rows still rely on v5-only coordinates/addresses (`v5_unknown_license`). Keep them flagged, or drop them?
6. **Marriott brands without a Wikidata item:** in the US file only MGM Collection (12 rows, dropped and listed). Per §15 these are excluded until a QID exists.
7. **More brands from All The Places.** Which chains next? ATP has ~5,600 spiders, most with `brand:wikidata`.
