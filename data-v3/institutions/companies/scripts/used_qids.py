"""Print every brand_qid / sub_brand_qid used in locations/*.csv(.gz), for fetch_wikidata_brands.py."""
import glob

import pandas as pd

from common import ROOT

q = set()
for p in glob.glob(str(ROOT / "locations" / "*.csv*")):
    if "dropped" in p:
        continue
    d = pd.read_csv(p, dtype=str, keep_default_na=False, usecols=lambda c: c in ("brand_qid", "sub_brand_qid"))
    for c in d.columns:
        q |= {v.split(":", 1)[1] for v in d[c] if v}
print(" ".join(sorted(q, key=lambda t: int(t[1:]))))
