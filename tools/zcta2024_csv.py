#!/usr/bin/env python3
"""data-v3/geo/zcta2024.csv from the Census 2024 ZCTA Gazetteer (2024_Gaz_zcta_national.txt, public domain).
Columns: zcta5 (GEOID), aland_m2, awater_m2, intptlat, intptlon (Gazetteer internal point, as published),
in_v2 (1 if the ZCTA is a key of v2/data/zcta2024.js), v2_point_match (1 if v2's [lat, lon] equals the Gazetteer point
rounded to 4 decimals). usage: zcta2024_csv.py <repo> <2024_Gaz_zcta_national.txt>"""
import sys, csv, json, os
repo, gaz = sys.argv[1:3]
s = open(os.path.join(repo, "v2/data/zcta2024.js")).read(); V = json.loads(s[s.index("{"):s.rindex("}") + 1])
rows = list(csv.reader(open(gaz, encoding="utf-8"), delimiter="\t")); h = [x.strip() for x in rows[0]]
out = csv.writer(open(os.path.join(repo, "data-v3/geo/zcta2024.csv"), "w", newline=""), lineterminator="\n")
out.writerow(["zcta5", "aland_m2", "awater_m2", "intptlat", "intptlon", "in_v2", "v2_point_match"])
n = m = 0; G = set()
for r in rows[1:]:
    d = dict(zip(h, [x.strip() for x in r])); z = d["GEOID"]; G.add(z); v = V.get(z)
    pm = int(bool(v) and round(float(d["INTPTLAT"]), 4) == v[0] and round(float(d["INTPTLONG"]), 4) == v[1])
    out.writerow([z, d["ALAND"], d["AWATER"], d["INTPTLAT"], d["INTPTLONG"], int(bool(v)), pm]); n += 1; m += pm
print("gazetteer", n, "v2 keys", len(V), "in both", len(G & set(V)), "v2 only", sorted(set(V) - G)[:10], len(set(V) - G), "point match", m)
