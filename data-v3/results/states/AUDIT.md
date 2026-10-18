# All states: v2 2020/2024 presidential state totals vs official

Audit only; nothing in `data/` was changed. Reference: FEC "Federal Elections 2020" (Table 2, compiled from state certified results; https://www.fec.gov/resources/cms-content/documents/federalelections2020.xlsx, retrieved 2026-10-18, box copy `/workspace/w/pa-audit/raw/`, not committed: 6 MB) and FEC "Official 2024 Presidential General Election Results" (https://www.fec.gov/resources/cms-content/documents/2024presgeresults.xlsx, `raw/`). FEC 2020 Dem/Rep include fusion-party lines (e.g. NY WFP/Conservative). Full list: `v2_state_totals_vs_official.csv`.

v2 layers checked: **county table** = sum of `data/election20xx.js` per state (+ Alaska boroughs from `v2/data/ak.js`, DC from `v2/data/dc.js`); **precinct file** = sum of `data/precincts20xx/<State>.js` (+ `v2/data/precincts20xx-DC.js`).

## County table: states whose Dem or Rep total differs from official

| Year | State | Dem v2 | Dem official | Dem diff | Rep v2 | Rep official | Rep diff |
|---|---|---|---|---|---|---|---|
| 2020 | Alabama | 849,648 | 849,624 | +24 | 1,441,168 | 1,441,170 | -2 |
| 2020 | Alaska | 153,776 | 153,778 | -2 | 189,952 | 189,951 | +1 |
| 2020 | California | 11,109,764 | 11,110,639 | -875 | 6,005,961 | 6,006,518 | -557 |
| 2020 | Idaho | 287,021 | 287,021 | +0 | 554,118 | 554,119 | -1 |
| 2020 | Indiana | 1,242,495 | 1,242,498 | -3 | 1,729,852 | 1,729,857 | -5 |
| 2020 | Kansas | 558,669 | 570,323 | -11,654 | 758,100 | 771,406 | -13,306 |
| 2020 | Maine | 430,473 | 435,072 | -4,599 | 359,899 | 360,737 | -838 |
| 2020 | New Hampshire | 424,921 | 424,937 | -16 | 365,654 | 365,660 | -6 |
| 2020 | New Jersey | 2,608,335 | 2,608,400 | -65 | 1,883,274 | 1,883,313 | -39 |
| 2020 | New York | 5,244,006 | 5,244,886 | -880 | 3,250,230 | 3,251,997 | -1,767 |
| 2020 | North Carolina | 2,684,292 | 2,684,292 | +0 | 2,758,773 | 2,758,775 | -2 |
| 2020 | North Dakota | 114,902 | 115,042 | -140 | 235,595 | 235,751 | -156 |
| 2020 | Pennsylvania | 3,459,923 | 3,458,229 | +1,694 | 3,378,263 | 3,377,674 | +589 |
| 2020 | Rhode Island | 306,210 | 307,486 | -1,276 | 199,837 | 199,922 | -85 |
| 2020 | Wisconsin | 1,630,673 | 1,630,866 | -193 | 1,610,065 | 1,610,184 | -119 |
| 2024 | Alaska | 139,688 | 140,026 | -338 | 184,409 | 184,458 | -49 |
| 2024 | Massachusetts | 2,126,545 | 2,126,518 | +27 | 1,251,308 | 1,251,303 | +5 |
| 2024 | New Hampshire | 418,496 | 418,488 | +8 | 395,578 | 395,523 | +55 |
| 2024 | Oregon | 1,228,410 | 1,240,600 | -12,190 | 910,702 | 919,480 | -8,778 |
| 2024 | Virginia | 2,335,395 | 2,333,778 | +1,617 | 2,075,085 | 2,074,097 | +988 |

All other states (of 51 incl. DC) match official Dem and Rep exactly in the county table.

## Precinct files: deviation of state sum from official (Dem / Rep)

| Year | States exact | States off (Dem %, Rep %) |
|---|---|---|
| 2020 | 20 | Arizona -0.01/-0.01; Arkansas -0.01/-0.03; California -0.21/-0.10; Delaware -0.42/-0.57; Florida -0.03/-0.02; Georgia -1.71/-1.28; Illinois -0.08/-0.09; Indiana -0.18/-0.04; Kansas -0.02/-0.06; Kentucky -0.01/-0.00; Louisiana -0.01/-0.04; Maine -0.00/+0.01; Maryland -0.06/-0.02; Massachusetts -0.05/-0.05; Michigan -0.02/-0.03; Mississippi -0.01/-0.00; Missouri -0.10/-0.04; Nebraska -0.66/-0.60; Nevada -0.03/-0.04; New Jersey -0.00/-0.00; New Mexico -0.03/-0.01; North Carolina -0.06/-0.01; Ohio -0.01/-0.02; Pennsylvania -0.02/+0.02; Rhode Island -0.55/-0.38; South Carolina -0.21/-0.28; Tennessee -0.00/-0.02; Texas -0.75/-0.53; Utah +0.00/-0.00; Virginia +0.07/-0.12; Washington -0.24/-0.14 |
| 2024 | 6 | Alabama -2.02/-2.45; Alaska -0.24/-0.03; Arizona -0.00/-0.00; Arkansas -0.84/-1.03; California -0.03/-0.07; Colorado -0.58/-0.57; Connecticut -1.58/-2.06; Delaware -0.68/-0.66; Florida -0.88/-1.02; Georgia -1.61/-1.17; Hawaii -1.04/-1.23; Idaho -0.05/-0.09; Illinois -0.28/-0.37; Indiana -0.34/-0.39; Iowa -0.21/-0.22; Kansas -0.72/-0.87; Kentucky -0.21/-0.23; Louisiana -0.26/-0.50; Maine -0.03/-0.12; Maryland -0.19/-0.12; Massachusetts -2.12/-2.13; Michigan -1.18/-0.71; Minnesota -0.11/-0.12; Mississippi -1.18/-1.08; Missouri -1.41/-1.94; Montana -0.58/-0.99; Nebraska -0.00/-0.01; Nevada -0.35/-0.35; New Jersey -1.67/-1.35; New Mexico -0.05/-0.02; New York -0.48/-0.51; North Carolina -0.41/-0.39; North Dakota -0.04/-0.16; Ohio -0.95/-1.28; Oregon -4.25/-4.95; Pennsylvania -0.66/-0.85; South Carolina -0.54/-0.44; South Dakota -18.61/-18.28; Tennessee -0.32/-0.70; Texas -0.00/-0.00; Utah -0.34/-0.43; Virginia -0.77/-0.78; Washington -0.54/-0.80; West Virginia -2.30/-1.68; Wyoming -4.73/-5.20 |

## Gaps
- **County-level official totals for states other than PA were not compared in this pass.** The usual consolidated file, MEDSL County Presidential Returns 2000-2024 (doi:10.7910/DVN/VOQCHQ), cannot be downloaded without filling in a Dataverse guestbook form (guestbook 458). I did not submit that form. Options: the user fills it in once, or the lane fetches each state's official county canvass (51 sources).
- **Largest county-table gaps vs official:** Kansas 2020 (-11,654 D / -13,306 R), Oregon 2024 (-12,190 / -8,778), Maine 2020 (-4,599 / -838), Virginia 2024 (+1,617 / +988), Pennsylvania 2020 (+1,694 / +589, Allegheny; see PA/GAPS.md), Rhode Island 2020 (-1,276 / -85). Causes not yet established. They are probably votes reported only statewide (overseas, federal-only, or provisional ballots not assigned to counties) or a stale pre-certification county source, but that is unverified.
- Alaska 2024 county table -338 D / -49 R: the 401 statewide-only votes are not allocated to boroughs (documented in COVERAGE.md).
- **Precinct files:** shortfalls are expected where precinct data is incomplete (worst: South Dakota 2024 -18.6%, Wyoming 2024 -5%, Oregon 2024 -4 to -5%, West Virginia, Massachusetts and Alabama 2024 -2%). These match the county QC lists in v2/data/COVERAGE.md.
