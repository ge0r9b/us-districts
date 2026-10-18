# 2016 President: offline staging (not used by v2)

Per HANDOFF, 2016 is prepared offline only. v2 has no 2016 data, so there is nothing to compare v2 against yet. Nothing in `data/` or `v2/` was changed.

## Estimate marker
These files contain only exact reported totals (weight = 1). The ≈ marker is reserved for area-weighted estimates, the same as 2020 and 2024. No row here is an estimate, so no row carries ≈. Any later 2016 precinct-to-district area weighting must flag those rows as estimates (`est`, ≈).

## Files
| File | Size (bytes) | Content |
|---|---|---|
| `us_president_2016_state_fec.csv` | 34,296 | 51 units (50 states + DC) x 3 rows (Trump, Clinton, all others), normalized columns |
| `raw/federalelections2016.xlsx` | 1,549,194 | FEC "Federal Elections 2016", untouched |
| `../PA/pa_president_county_official_2016.csv` | 89,003 | PA DOS certified 2016 county results, normalized (67 counties x 5 candidates) |
| `../PA/raw/GetCountyBreak_office1_e54.json` | 122,583 | PA DOS raw, untouched |

## Sources
- FEC, Federal Elections 2016, sheet "Table 2. Electoral & Pop Vote": https://www.fec.gov/resources/cms-content/documents/federalelections2016.xlsx (retrieved 2026-10-18 09:46 UTC)
- PA DOS certified 2016 General, President by county: https://www.electionreturns.pa.gov/api/ElectionReturn/GetCountyBreak?officeId=1&districtId=1&methodName=GetCountyBreak&electionid=54&electiontype=G&isactive=0

## Totals check
- National (sum of the 51 FEC state rows = FEC printed total): Trump 62,984,828; Clinton 65,853,514; others 7,830,934; total 136,669,276.
- PA DOS vs FEC PA: Trump 2,970,733 = 2,970,733; Clinton 2,926,441 = 2,926,441 (exact). Total 6,115,402 vs FEC 6,165,478 (-50,076): DOS lists only the 5 ballot candidates (adds Johnson 146,715, Stein 49,941, Castle 21,572), while FEC also counts write-ins. This is a difference in definition, not an error.

## Gaps
- No 2016 county or precinct files for other states yet. County-level for all states needs either the MEDSL county file (Dataverse guestbook form, not submitted) or each state's canvass.
