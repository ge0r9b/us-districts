# Foreign boundary vintages (UK, DE, FR), for the Governments crosswalk

Written Oct 18, 2026 (EDT) by Geo, before the geometry builds, so `boundary_xwalk.csv` can key to these exact datasets.
Use the `boundary_dataset` and `vintage` strings below verbatim. The key field is the join key; the CSV index in
`data-v3/geo/` carries it as the `code` column. Counts are the feature counts in the source; checks against the
publishers' official totals are in README.md and COVERAGE.md once each layer is built.

## UK: ONS Open Geography Portal, Open Government Licence v3.0

All are BFC (full resolution, clipped to the coastline), served by ONS's ArcGIS service
`services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/<service>/FeatureServer`, British National Grid (EPSG:27700).

| layer | csv | boundary_dataset | vintage | key field (GSS) | source count |
|---|---|---|---|---|---|
| Local Authority Districts (England LADs, Scottish council areas, Welsh principal areas, NI LGDs) | `gb_lad.csv` | `ONS LAD_MAY_2026_UK_BFC` (Local Authority Districts (May 2026) Boundaries UK BFC) | 2026-05 | `LAD26CD` (E06/E07/E08/E09, S12, W06, N09) | 361 |
| Counties and unitary authorities | `gb_ctyua.csv` | `ONS CTYUA_DEC_2025_UK_BFC` (Counties and Unitary Authorities (December 2025) Boundaries UK BFC) | 2025-12 | `CTYUA25CD` (E10 counties; E06/E08/E09, S12, W06, N09 unitaries) | 218 |
| Combined authorities (England) | `gb_cauth.csv` | `ONS CAUTH_DEC_2025_EN_BFC` (Combined Authorities (December 2025) Boundaries EN BFC) | 2025-12 | `CAUTH25CD` (E47) | 15 |
| Parishes (England) and communities (Wales) | `gb_par.csv` | `ONS PARNCP_MAY_2026_EW_BFC` (Parishes and Non-Civil Parished Areas (May 2026) Boundaries EW BFC) | 2026-05 | `PARNCP26CD` (E04 parish, W04 community, E43 non-civil-parished area) | 11,542 |

Notes:
- CTYUA and CAUTH: December 2025 is the latest ONS edition on Oct 18, 2026 (no May 2026 edition is published). The LAD
  codes did not change between LAD December 2025 and LAD May 2026 (checked: identical 361 codes), so CTYUA Dec 2025 lines up
  with LAD May 2026.
- ONS no longer issues a parish-only layer after May 2024; the PARNCP layer is the full England and Wales coverage. Rows with
  E43 codes are the unparished remainder (no parish council); the `type` column marks them, so key institutions only to E04/W04
  rows.

## DE: BKG VG250, Datenlizenz Deutschland – Namensnennung – Version 2.0 (dl-de/by-2-0)

`VG250 Verwaltungsgebiete 1:250 000, Ebenen, Stand 01.01.2026` (`vg250_01-01.utm32s.gpkg.ebenen.zip`, file `DE_VG250.gpkg`,
EPSG:25832), from https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/2026/ (published 21 Jul 2026). Edition:
**01.01.2026** (Gebietsstand 1 January 2026; `aktualitaet.txt` = 01.01.2026). The 31.12.2025 edition also exists; 01.01.2026
is the later one. Only the land parts (GF = 4) are used; the coastal and lake water parts (GF = 2) are dropped.

| layer | csv | boundary_dataset | vintage | key field | source count (GF = 4) |
|---|---|---|---|---|---|
| Länder | `de_lan.csv` | `BKG VG250 VG250_LAN` | 2026-01-01 | `ARS` (2 digits) | 16 |
| Kreise | `de_krs.csv` | `BKG VG250 VG250_KRS` | 2026-01-01 | `ARS` (5 digits) | 401 |
| Verwaltungsgemeinschaften / Gemeindeverbände | `de_vwg.csv` | `BKG VG250 VG250_VWG` | 2026-01-01 | `ARS` (9 digits) | 4,580 |
| Gemeinden | `de_gem.csv` | `BKG VG250 VG250_GEM` | 2026-01-01 | `ARS` (12 digits); `AGS` (8 digits) also in the CSV | 10,939 |

For Gemeinden the ARS is the primary key (unique; it includes the Gemeindeverband). AGS is carried as a second column for
joins to sources that only have AGS. VG250 VWG covers the whole country: it also contains Einheitsgemeinden and
verbandsfreie Gemeinden as their own units (the `type` column carries BKG's `BEZ`).

## FR: IGN ADMIN EXPRESS COG, Licence Ouverte / Open Licence 2.0 (Etalab)

`ADMIN EXPRESS COG 4.0, édition 2026-01-01` (COG **2026**, INSEE Code officiel géographique at 1 January 2026), the
full-precision edition (not COG CARTO). GeoPackages per territory from https://data.geopf.fr/telechargement/resource/ADMIN-EXPRESS-COG:
`ADMIN-EXPRESS-COG_4-0__GPKG_LAMB93_FXX_2026-01-01` (metropolitan France) and the GLP, MTQ, GUF, REU, MYT packages (the five
overseas départements/régions), plus BLM, MAF, SPM (overseas collectivités, kept in a separate flagged layer if present).

| layer | csv | boundary_dataset | vintage | key field | source count (FXX + 5 DROM) |
|---|---|---|---|---|---|
| Régions | `fr_reg.csv` | `IGN ADMIN-EXPRESS-COG region` | COG 2026 | `code_insee` (2 digits); `code_siren` also given | 13 + 5 = 18 |
| Départements | `fr_dep.csv` | `IGN ADMIN-EXPRESS-COG departement` | COG 2026 | `code_insee` (2A/2B, 971–976); `code_siren` also given | 96 + 5 = 101 |
| EPCI | `fr_epci.csv` | `IGN ADMIN-EXPRESS-COG epci` | COG 2026 | `code_siren` (9 digits) | 1,241 + 23 = 1,264 |
| Communes | `fr_com.csv` | `IGN ADMIN-EXPRESS-COG commune` | COG 2026 | `code_insee` (5 chars); `code_siren` also given | 34,746 + 129 = 34,875 |

EPCI: the IGN layer can include the Métropole de Lyon and the Grand Paris établissements publics territoriaux alongside the
EPCI à fiscalité propre (DGCL total at 1 Jan 2026: 1,252). The `type` column carries IGN's `nature` so the two can be told
apart. Built: 1,264 = 22 Métropole (21 + Métropole de Lyon) + 14 CU + 229 CA + 988 CC + 11 Etablissement public
territorial; minus Lyon and the 11 EPT = 1,252. IGN still types 243100781 Le Grand Ouest Toulousain as a CC (DGCL: a CA since
2025), hence CA 229 / CC 988 vs DGCL 230 / 987. The 4 communes in no EPCI carry `epci_siren` = `NR`.
Overseas collectivités Saint-Barthélemy (977), Saint-Martin (978), Saint-Pierre-et-Miquelon (975) are in `fr_com_om.csv`, keyed
by INSEE code, outside the 34,875 communes.

## Status (Oct 18, 2026, after the builds)

All layers above are built and pushed on `data/geo`: CSV indexes in `data-v3/geo/` (column `code` = the key field above), GeoJSON
regenerated into `../geo-data-raw/v3gb`, `v3de`, `v3fr` (sha256 in README.md). Every source count equals the official total
listed in README.md, except where noted there (Gemeindeverbände: no national total verified; gemeindefreie Gebiete 192 vs 194 on
de.wikipedia). Within each country the layers nest exactly (coarser layers are unions of the simplified finest layer).
