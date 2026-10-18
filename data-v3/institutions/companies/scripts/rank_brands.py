"""Rank brands with locations by cleanliness -> brand_cleanliness.csv (measurements only, no new data).

Per brand (entity_id with establishments in company_locations.csv.gz):
  locations, states_covered (of 50 + DC, from county geoid), pct_with_geoid,
  pct_coords_cc0 (coordinate source licence CC0, i.e. All The Places),
  pct_coords_cc0_or_first_party (CC0 or the brand's own locator / feed),
  has_qid, has_parent (current P749 in brands.csv), has_free_logo.
Rank order: has_parent desc, pct_coords_cc0_or_first_party desc, pct_coords_cc0 desc,
states_covered desc, pct_with_geoid desc, locations desc.
"""
import pandas as pd

from common import ROOT

L = pd.read_csv(ROOT / "company_locations.csv.gz", dtype=str, keep_default_na=False)
L = L[~L.location_id.str.split(":").str[0].isin([p.stem.removesuffix("_locations") for p in (ROOT / "organizations").glob("*_locations.csv")])]  # brands only
B = pd.read_csv(ROOT / "brands.csv", dtype=str, keep_default_na=False).set_index("entity_id")
S = pd.read_csv(ROOT / "sources.csv", dtype=str, keep_default_na=False).set_index("source_id")
FIRST_PARTY = ("walgreens-locator", "cvs-store-locator", "marriott-pacsys")
STATES = {f"{i:02d}" for i in range(1, 57)} - {"03", "07", "14", "43", "52"}  # 50 states + DC
L["cc0"] = L.source_id.map(lambda s: S.loc[s, "license"].startswith("CC0"))
L["fp"] = L.source_id.str.startswith(FIRST_PARTY) | L["cc0"]
rows = []
for e, d in L.groupby("entity_id"):
    b = B.loc[e] if e in B.index else None
    rows.append(dict(entity_id=e, name=b["name"] if b is not None else "", locations=len(d),
                     states_covered=len(set(d.geoid.str[:2]) & STATES),
                     pct_with_geoid=round(100 * (d.geoid != "").mean(), 1),
                     pct_coords_cc0=round(100 * d.cc0.mean(), 1),
                     pct_coords_cc0_or_first_party=round(100 * d.fp.mean(), 1),
                     has_qid=e.startswith("wikidata:Q"), has_parent=bool(b is not None and b["parent_brand_id"]),
                     parent=b["parent_brand_name"] if b is not None else "",
                     has_free_logo=bool(b is not None and b["logo_file"]),
                     coordinate_sources=";".join(sorted(set(d.source_id)))))
R = pd.DataFrame(rows).sort_values(["has_parent", "pct_coords_cc0_or_first_party", "pct_coords_cc0", "states_covered",
                                    "pct_with_geoid", "locations"], ascending=False)
R.insert(0, "rank", range(1, len(R) + 1))
R.to_csv(ROOT / "brand_cleanliness.csv", index=False, lineterminator="\n")
print(R.drop(columns=["coordinate_sources"]).to_string(index=False))
