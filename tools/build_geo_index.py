#!/usr/bin/env python3
"""Geo search index over every v2 geo-list row, for the bottom geography field.

Rows: [name, type, stateAbbr, key]
  type  state | county | town | place | sch | cd | sldu | sldl | zcta
  key   the exact row key used by v2/data/points/<State>.js (= the list key without "State|"); state: the state name;
        zcta: the 5-digit ZCTA. The 86 duplicate v1 rows that points keys by TIGER GEOID appear here with that GEOID
        key and their (shared) name, exactly as in points.
  name  what to match / show: county, place, school rows: the row name; town: the town name (key carries the county);
        cd: "District N" ("District at-large" for code 00), as the app labels it; sldu / sldl: "<AB> Senate <code>" /
        "<AB> House <code>" (leading zeros dropped), as the app's areaLabel does; zcta: the ZIP; state: the state name.
Sorted by lower-case name (then type, state, key). Rows come from v2/data/points/*.js (all list rows) and
v2/data/zcta_xref/*.js (ZCTAs, with their primary state), so the index, the points and the ZIP files share one key space.
Output: v2/data/geo_index.js as __geoIndex([...]) if <= ~400 KB gzip, else split by the first character of the
lower-case name into v2/data/geo_index/<a-z>.js plus v2/data/geo_index/0.js for names starting with anything else
(ZIP digits, quotes, ...); each file calls __geoIndex([...]) with its rows.
usage: build_geo_index.py <repo> <points_report.json>"""
import sys, os, json, glob, gzip, re, collections
repo = sys.argv[1]; D = os.path.join(repo, "v2", "data")
rep = json.load(open(sys.argv[2], encoding="utf-8"))
AB = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO","Connecticut":"CT","Delaware":"DE",
"District of Columbia":"DC","Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS",
"Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS",
"Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY",
"North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI",
"South Carolina":"SC","South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA","Washington":"WA",
"West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY"}
def jscall(path, name):
    s = open(path, encoding="utf-8").read(); i = s.index(name + "(") + len(name) + 1; j = s.rindex(")")
    return json.loads("[" + s[i:j] + "]")
def code(c): return re.sub(r"^0+(?=\w)", "", c)
GK = {}   # (state, layer, geoid) -> v1 name
for st, v in rep.items():
    for layer, k, g in v.get("geoid_keys", []): GK[(st, layer, g)] = k.split("|")[-1]
rows = []; cnt = collections.Counter()
for pf in sorted(glob.glob(os.path.join(D, "points", "*.js"))):
    st, P = jscall(pf, "__points"); ab = AB[st]
    rows.append([st, "state", ab, st]); cnt["state"] += 1
    for layer, d in P.items():
        for k in d:
            if (st, layer, k) in GK: nm = GK[(st, layer, k)]
            elif layer == "town": nm = k.split("|", 1)[1]
            elif layer == "cd": nm = "District at-large" if k == "00" else "District " + code(k)
            elif layer == "sldu": nm = ab + " Senate " + code(k)
            elif layer == "sldl": nm = ab + " House " + code(k)
            else: nm = k
            rows.append([nm, layer, ab, k]); cnt[layer] += 1
for zf in sorted(glob.glob(os.path.join(D, "zcta_xref", "*.js"))):
    s = open(zf, encoding="utf-8").read()
    for z, ab in re.findall(r'"(\d{5})":\{st:"([A-Z]{2})"', s):
        rows.append([z, "zcta", ab, z]); cnt["zcta"] += 1
TORD = {t: i for i, t in enumerate(["state", "county", "town", "place", "sch", "cd", "sldu", "sldl", "zcta"])}
rows.sort(key=lambda r: (r[0].lower(), TORD[r[1]], r[2], r[3]))
enc = lambda rs: "__geoIndex([" + ",".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rs) + "]);\n"
js = enc(rows); gz = len(gzip.compress(js.encode(), 6))
sizes = {}
if gz <= 400000:
    open(os.path.join(D, "geo_index.js"), "w", encoding="utf-8").write(js); sizes["geo_index.js"] = (len(js.encode()), gz)
else:
    os.makedirs(os.path.join(D, "geo_index"), exist_ok=True)
    B = collections.defaultdict(list)
    for r in rows:
        c = r[0][:1].lower(); B[c if "a" <= c <= "z" else "0"].append(r)
    for b, rs in sorted(B.items()):
        t = enc(rs); open(os.path.join(D, "geo_index", b + ".js"), "w", encoding="utf-8").write(t)
        sizes[b + ".js"] = (len(t.encode()), len(gzip.compress(t.encode(), 6)))
print(json.dumps({"rows": len(rows), "per_type": cnt, "single_file_gzip6": gz, "single_file_raw": len(js.encode()), "files": sizes}))
