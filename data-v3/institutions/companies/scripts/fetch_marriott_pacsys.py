"""Download Marriott's own public property feeds (first-party, marriott.com).

https://pacsys.marriott.com/data/marriott_properties_<BRAND>_en-US.json is the JSON
that marriott.com's brand "find a hotel" pages load. It is the same feed All The
Places' marriott_hotels spider reads, but ATP only reads some brand codes; this
script reads the brand codes ATP skips (Autograph AK, Westin WI, Tribute TX, JW,
W WH, Luxury Collection LC, Vacation Club MV, ...). Each property has marsha_code,
name, address, city, state, postal_code, country_code, phone, latitude, longitude.

Writes raw/marriott_pacsys/<BRAND>.json untouched plus raw/marriott_pacsys.meta.json.
Usage: python fetch_marriott_pacsys.py AK WI TX JW WH LC MV ...
"""
import json
import sys

from common import RAW, get, today, write_meta

URL = "https://pacsys.marriott.com/data/marriott_properties_{}_en-US.json"


def count(d):
    return sum(len(c["city_properties"]) for r in d["regions"] for k in r["region_countries"]
               for s in k["country_states"] for c in s["state_cities"])


def main(codes):
    out = RAW / "marriott_pacsys"
    out.mkdir(parents=True, exist_ok=True)
    meta = {"retrieved_at": today(), "license": "marriott.com terms of use (first-party public feed; facts only)", "files": {}}
    for c in codes:
        url = URL.format(c)
        r = get(url, min_interval=1.0, allow_redirects=False)
        if r.status_code != 200:
            print(c, r.status_code, "skipped", file=sys.stderr)
            continue
        (out / f"{c}.json").write_bytes(r.content)
        n = count(r.json())
        meta["files"][c] = {"url": url, "properties": n}
        print(c, n, file=sys.stderr)
    write_meta("marriott_pacsys", meta)


if __name__ == "__main__":
    main(sys.argv[1:])
