"""Rewrite the '## Files' table in SCHEMA.md from the files on disk (row counts only)."""
import glob
import os
import re

import pandas as pd

from common import ROOT


def n(p):
    return len(pd.read_csv(p, dtype=str, keep_default_na=False))


b = pd.read_csv(ROOT / "brands.csv", dtype=str, keep_default_na=False)
kinds = ", ".join(f"{v} {k}" for k, v in b.kind.replace("", "review").value_counts().items())
L = pd.read_csv(ROOT / "company_locations.csv.gz", dtype=str, keep_default_na=False)
locs = []
for p in sorted(glob.glob(str(ROOT / "locations" / "*.csv*"))):
    name = os.path.basename(p)
    if "dropped" in name:
        continue
    locs.append(f"{name.split('.')[0]} {n(p):,}" + (" (`.csv.gz`)" if p.endswith(".gz") else ""))
orgs = ""
for p in sorted(glob.glob(str(ROOT / "organizations" / "*.csv*"))):
    name = os.path.basename(p)
    if "_locations." in name or "_sources." in name or "_dropped." in name:
        continue
    orgs += f"| `organizations/{name}` | {n(p):,} | `entity` (one row per organization; loader rows in `organizations/{name.split('.')[0]}_locations.csv`) |\n"
table = f"""| file | rows (this build) | loads into |
|---|---|---|
| `brands.csv` | {len(b)} ({kinds}) | `entity` |
| `brand_relationships.csv` | {n(ROOT / 'brand_relationships.csv')} | `entity_relation` |
| `company_locations.csv.gz` | {len(L):,} ({(L.geoid != '').sum():,} with a v2-2024 county geoid; {(L.country_code != 'US').sum():,} outside the US) | `entity_location` |
| `retracted_locations.csv` | {n(ROOT / 'retracted_locations.csv')} (header only) | `retraction` (target `entity_location`) |
| `locations/<brand>.csv` | {'; '.join(locs)} | source tables for company_locations (full store detail) |
{orgs}| `locations/marriott_dropped.csv` | {n(ROOT / 'locations' / 'marriott_dropped.csv')} | not loaded: Marriott rows that could not be kept, with reason |
| `brand_cleanliness.csv` | {n(ROOT / 'brand_cleanliness.csv')} | not loaded: brands with locations ranked by cleanliness (`scripts/rank_brands.py`; measurements only) |
| `sources.csv` | {n(ROOT / 'sources.csv')} | `source` |
"""
s = (ROOT / "SCHEMA.md").read_text()
s = re.sub(r"\| file \| rows \(this build\) \| loads into \|\n(\|.*\|\n)+", table, s, count=1)
(ROOT / "SCHEMA.md").write_text(s)
print(table)
