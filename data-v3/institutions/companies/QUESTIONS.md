# data-v3/institutions/companies: open questions (brands + locations)

1. ~~kind for brands~~ resolved (5029c30/8639fe1): `brand`, `organization`/`company`.
2. ~~company_locations~~ resolved: built (`company_locations.csv.gz`).
3. **Sheraton / St. Regis parents.** Both P749 statements (Starwood, Marriott International) have no dates on Wikidata; kept and flagged for review. Add P580/P582 upstream on Wikidata?
4. **Walgreens / Sycamore.** Wikidata still gives Walgreens → Walgreens Boots Alliance and WBA has no P749/P127, so nothing shows the 2025 Sycamore Partners take-private. Leave as Wikidata says, or edit Wikidata upstream first?
5. **Marriott v5 provenance.** Resolved 2026-10-18: 367 rows re-sourced from Marriott's feed, and 33 kept on user-approved v5 values (`v5_user_approved`).
6. **Marriott brands without a Wikidata item:** in the US file only MGM Collection (12 rows, dropped and listed). Per §15 these are excluded until a QID exists.
7. **More brands from All The Places.** Which chains next? ATP has ~5,600 spiders, most with `brand:wikidata`.

## Added 2026-10-18
- **33 Marriott hotels on v5 values** (`v5_user_approved`, restored 2026-10-18 per the user). Possible same building under two codes: CLEBR Renaissance Cleveland Hotel and CLEDK Hotel Cleveland, Autograph Collection are within 100 m but have different names, so the dedupe rule keeps both.
- **CVS Pharmacy logo blank**: Wikidata has two normal-rank P154 values with no dates (CVS Logo 2016.svg, CVS Health heart.png). Picking one, or setting a preferred rank on Wikidata, would fill it.
- **Wawa stores 9598 and 9599** (both "260 W. BALTIMORE PIKE, MEDIA PA") have coordinates 36.000282, -45.406712, in the Atlantic. They're kept as-is and flagged `no_county`.
- **Brand logos**: 29 of 45 are filled (15 have no P154, 1 is ambiguous). Nearly all are "Public domain (PD textlogo)" on Commons with "restrictions: trademarked", so there is no copyright but a trademark still applies.
- **Starbucks gaps**: India (`starbucks_in` returned 0 features); 47 BR/AU rows with no coordinates; 178 Hong Kong/Macau rows with no name; 6 Reserve Roasteries not loaded (separate brand Q71150001, no store id). ATP covers 58 countries; countries with no ATP spider (e.g. South Korea, Mexico) are absent.
- **Wikidata parent gaps (hotels)**: Comfort Inn (1,254 rows) and Comfort Suites (532) have no P749 on Wikidata, so `parent_brand_qid` is blank, not Choice. The Radisson brands in Choice's spider have Radisson Hotel Group or Carlson as parent, or none (Park Inn, Radisson RED, Park Plaza). IHG Army Hotels (61) has no parent. Graduate by Hilton lists AJ Capital Partners plus Hilton, and Regent lists Silks Hotel Group plus IHG, both undated. Adding P749 statements on Wikidata would fill these.
- **ATP gaps**: the latest-run spiders for Walmart US (partial), Lowe's, Buc-ee's, Hilton and Choice were empty or partial. Older complete ATP runs are used and flagged `atp_older_run_<date>`. Walmart US mixes the latest run with the 2026-01-24 run for the 3,037 stores missing from the latest one.
