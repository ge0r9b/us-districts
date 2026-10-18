# data-v3/institutions/companies: open questions (brands + locations)

1. **kind for brands.** `entity.kind` (docs/v3 SCHEMA.sql 1cda425) allows `company`, `nonprofit`, `fund`, `other`. Add `brand`, or load brands as `company`/`other`? Parent organizations here are `organization`.
2. **company_locations.** Should each store row also become an `entity_location` row (`role = site_in`, `geoid` = county GEOID, `boundary_set` = `v2-2024`, lat/lon), keyed by `brand_qid`? The per-brand files already carry everything needed.
3. **Parent brand.** Only Wikidata P749 is used. Where Wikidata lists two parents (Sheraton, St. Regis: Starwood; Marriott International) both are kept. OK, or keep only the current one?
4. **Walgreens / Sycamore.** Wikidata still gives Walgreens → Walgreens Boots Alliance and WBA has no P749/P127, so nothing shows the 2025 Sycamore Partners take-private. Leave as Wikidata says, or edit Wikidata upstream first?
5. **Marriott v5 provenance.** v5 mixes OSM-derived (ODbL) and ArcGIS-geocoded addresses without per-row tags. Keep, or drop v5-only address/coordinate values and keep only marriott.com + ATP (CC0) values?
6. **Marriott brands without a Wikidata item:** Series by Marriott (84), Outdoor Collection (35), StudioRes (26), MGM Collection (12), Bvlgari (9, Wikidata has "Bulgari Hotels & Resorts" but not linked to Marriott as owner). Mint an id scheme for them, or leave `brand_qid` empty?
7. **More brands from All The Places.** Which chains next? ATP has ~5,600 spiders, most with `brand:wikidata`.
