"""Geocode US rows that have an address but no coordinates with the U.S. Census Bureau geocoder (public domain).

https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?benchmark=Public_AR_Current&format=json
Reads locations/<file>.csv(.gz) for the files named on the command line, queries each address with no lat/lon once,
and caches every answer (matched or not) in raw/census_geocode.json keyed by the query string.
Usage: python fetch_census_geocode.py hy_vee grocery_outlet meijer brookshires shoprite
"""
import glob
import json
import sys

import pandas as pd

from common import RAW, ROOT, get, today, write_meta

URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"


def query_of(r):
    parts = [r["address"], r["city"], r["state"], r["zip"]]
    return ", ".join(p for p in parts if p)


def main(files):
    cache_p = RAW / "census_geocode.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    n = 0
    for f in files:
        p = glob.glob(str(ROOT / "locations" / f"{f}.csv*"))[0]
        d = pd.read_csv(p, dtype=str, keep_default_na=False)
        for _, r in d[(d.lat == "") & (d.address != "") & (d.country_code == "US")].iterrows():
            q = query_of(r)
            if q in cache:
                continue
            j = get(URL, min_interval=0.3, params={"address": q, "benchmark": "Public_AR_Current", "format": "json"}).json()
            m = j.get("result", {}).get("addressMatches", [])
            cache[q] = {"matches": len(m), "matched_address": m[0]["matchedAddress"] if m else "",
                        "lat": m[0]["coordinates"]["y"] if m else None, "lon": m[0]["coordinates"]["x"] if m else None}
            n += 1
    cache_p.write_text(json.dumps(cache, indent=1))
    write_meta("census_geocode", {"retrieved_at": today(), "url": URL, "benchmark": "Public_AR_Current", "queries": len(cache)})
    print(n, "new queries;", sum(1 for v in cache.values() if v["matches"]), "matched of", len(cache), file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
