#!/usr/bin/env python3
"""ZIP (ZCTA) -> geo-list rows, for the address/ZIP search.

Writes v2/data/zcta_xref/<first 3 ZIP digits>.js:
  __zxref("194",{"19405":{st:"PA",place:[[key,share],...],town:[[key,share],...],county:[[key,share],...]},...});
  key    = the exact row key the geo lists / points files use, within state st:
           place  -> v2/data/places/<State>.js row name ("Bridgeport borough")
           town   -> "County|Name" of v2/data/parts/<State>.js (the townsIn() rows)
           county -> v2/data/uscounties.js row name ("Montgomery County"; Connecticut: 2022 planning regions)
           An entry in a different state than st (ZCTAs crossing a state line) carries the state as a third element:
           [key, share, "NJ"].
  share  = share of the ZCTA's land area (ALAND of the part / ALAND of the ZCTA; total area if the ZCTA has no land),
           2 decimals; each list sorted by share, largest first. Parts under 1 % are left out unless the list would
           otherwise be empty (then the largest is kept, possibly 0.0).
Source: Census 2020 ZCTA relationship files (tab20_zcta520_{place20,cousub20,county20}_natl.txt, public domain).
2020 -> v2 key: place and county subdivision GEOIDs through data-v3 places_2024 / towns_2024 GeoJSON (v2_places /
v2_parts), falling back to data-v3/geo/v1_towns.csv and then to a unique (state, county, NAMELSAD) / (state, NAMELSAD)
match; county GEOIDs through the 2024 county Gazetteer. Connecticut's 2020 counties no longer exist in v2 (planning
regions since 2022), so CT county shares are summed from the CT town parts by the 2024 planning region of each town.
County subdivisions that are not v2 town rows (e.g. statistical CCDs / unorganized territories without a row) are not
listed. ZCTA shapes, ZIP digits and shares are not invented: a ZCTA appears only with rows from the files.
usage: build_zcta_xref.py <repo> <rel2020_dir> <v3_raw_dir> <gaz_dir> [--report OUT.json]
"""
import sys, os, json, gzip, re, csv, collections, argparse
ap = argparse.ArgumentParser(); ap.add_argument("repo"); ap.add_argument("rel"); ap.add_argument("v3raw"); ap.add_argument("gaz"); ap.add_argument("--report")
a = ap.parse_args()
D = os.path.join(a.repo, "v2", "data")
FIPS2ST = {"01":"Alabama","02":"Alaska","04":"Arizona","05":"Arkansas","06":"California","08":"Colorado","09":"Connecticut","10":"Delaware",
"11":"District of Columbia","12":"Florida","13":"Georgia","15":"Hawaii","16":"Idaho","17":"Illinois","18":"Indiana","19":"Iowa","20":"Kansas",
"21":"Kentucky","22":"Louisiana","23":"Maine","24":"Maryland","25":"Massachusetts","26":"Michigan","27":"Minnesota","28":"Mississippi",
"29":"Missouri","30":"Montana","31":"Nebraska","32":"Nevada","33":"New Hampshire","34":"New Jersey","35":"New Mexico","36":"New York",
"37":"North Carolina","38":"North Dakota","39":"Ohio","40":"Oklahoma","41":"Oregon","42":"Pennsylvania","44":"Rhode Island",
"45":"South Carolina","46":"South Dakota","47":"Tennessee","48":"Texas","49":"Utah","50":"Vermont","51":"Virginia","53":"Washington",
"54":"West Virginia","55":"Wisconsin","56":"Wyoming"}
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
def sf(st): return st.replace(" ", "-") + ".js"

# ---- v2 row keys ----
PLACEROWS = {}; PARTROWS = {}; COUNTYROWS = collections.defaultdict(set)
for r in jscall(os.path.join(D, "uscounties.js"), "window.__uscty")[0]: COUNTYROWS[r[0]].add(r[1])
COUNTYROWS["District of Columbia"].add("District of Columbia")    # dc.js
for st in FIPS2ST.values():
    if st == "District of Columbia": PLACEROWS[st] = set(); PARTROWS[st] = set(); continue
    PLACEROWS[st] = {r[1] for r in jscall(os.path.join(D, "places", sf(st)), "__places")[1]}
    PARTROWS[st] = {r[0] + "|" + r[1] for r in jscall(os.path.join(D, "parts", sf(st)), "__parts")[1]}

def v3feat(fn):
    with gzip.open(os.path.join(a.v3raw, fn), "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip().rstrip(",")
            if line.startswith('{"type":"Feature"'):
                yield json.loads(re.search(r'"properties":(\{.*?\}),"geometry"', line).group(1))
PL_G = {}; TW_G = {}; TW_N = collections.defaultdict(list); TW_CTY = {}
for p in v3feat("places_2024.geojson.gz"):
    if p.get("v2_places"): PL_G[p["geoid"]] = p["v2_places"]
for p in v3feat("towns_2024.geojson.gz"):
    parts = [k for k in (p.get("v2_parts") or []) if k in PARTROWS.get(p["state"], ())]
    if parts:
        TW_G[p["geoid"]] = parts[0]; TW_CTY[parts[0]] = p["county"]
        TW_N[(p["state"], p["namelsad"])].append(parts[0])
        TW_N[(p["state"], p["county"], p["namelsad"])].append(parts[0])
V1 = {}
with open(os.path.join(a.repo, "data-v3", "geo", "v1_towns.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if not r["geoid"]: continue
        k = r["v1_name"] if r["layer"] == "places" else r["county"] + "|" + r["v1_name"]
        V1.setdefault((r["layer"], r["geoid"]), (r["state"], k))
CTYNAME = {}
with open(os.path.join(a.gaz, "2024_Gaz_counties_national.txt"), encoding="utf-8", errors="replace") as f:
    f.readline()
    for line in f:
        v = [x.strip() for x in line.split("\t")]; CTYNAME[v[1]] = v[3]

def rel(fn):
    with open(os.path.join(a.rel, fn), encoding="utf-8-sig") as f:
        hdr = f.readline().rstrip("\n").split("|")
        for line in f:
            r = dict(zip(hdr, line.rstrip("\n").split("|")))
            if r["GEOID_ZCTA5_20"]: yield r

how = collections.Counter(); unmapped = collections.Counter(); UNM = collections.defaultdict(list)
ZL = {}   # zcta -> (land, total)
X = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(float)))  # X[z][layer][(st,key)] = land part
def zarea(r):
    z = r["GEOID_ZCTA5_20"]; ZL[z] = (int(r["AREALAND_ZCTA5_20"]), int(r["AREALAND_ZCTA5_20"]) + int(r["AREAWATER_ZCTA5_20"]))
    return z
def part(r, land_only=True): return (int(r["AREALAND_PART"]), int(r["AREALAND_PART"]) + int(r["AREAWATER_PART"]))

for r in rel("tab20_zcta520_place20_natl.txt"):
    z = zarea(r); g = r["GEOID_PLACE_20"]; st = FIPS2ST.get(g[:2])
    if not st: continue
    k = None
    if g in PL_G and PL_G[g] in PLACEROWS[st]: k = PL_G[g]; how["place:geoid"] += 1
    elif ("places", g) in V1 and V1[("places", g)][1] in PLACEROWS[st]: k = V1[("places", g)][1]; how["place:v1_towns"] += 1
    elif r["NAMELSAD_PLACE_20"] in PLACEROWS[st]: k = r["NAMELSAD_PLACE_20"]; how["place:name"] += 1
    if k is None: unmapped["place " + r["CLASSFP_PLACE_20"]] += 1; UNM["place"].append((st, r["NAMELSAD_PLACE_20"], g, r["CLASSFP_PLACE_20"])); continue
    X[z]["place"][(st, k)] += part(r)[0]; X[z]["place_t"][(st, k)] += part(r)[1]
CT_T = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
for r in rel("tab20_zcta520_cousub20_natl.txt"):
    z = zarea(r); g = r["GEOID_COUSUB_20"]; st = FIPS2ST.get(g[:2])
    if not st: continue
    k = None
    if g in TW_G: k = TW_G[g]; how["town:geoid"] += 1
    elif ("towns", g) in V1 and V1[("towns", g)][1] in PARTROWS[st]: k = V1[("towns", g)][1]; how["town:v1_towns"] += 1
    else:
        c = CTYNAME.get(g[:5], "")
        for nk in ((st, c, r["NAMELSAD_COUSUB_20"]), (st, r["NAMELSAD_COUSUB_20"])):
            if len(set(TW_N.get(nk, []))) == 1: k = TW_N[nk][0]; how["town:name"] += 1; break
    if k is None: unmapped["town " + r["CLASSFP_COUSUB_20"]] += 1; UNM["town"].append((st, r["NAMELSAD_COUSUB_20"], g, r["CLASSFP_COUSUB_20"])); continue
    X[z]["town"][(st, k)] += part(r)[0]; X[z]["town_t"][(st, k)] += part(r)[1]
    if st == "Connecticut":
        cty = k.split("|")[0]; CT_T[z][cty][0] += part(r)[0]; CT_T[z][cty][1] += part(r)[1]
for r in rel("tab20_zcta520_county20_natl.txt"):
    z = zarea(r); g = r["GEOID_COUNTY_20"]; st = FIPS2ST.get(g[:2])
    if not st or st == "Connecticut": continue
    k = CTYNAME.get(g) if g != "11001" else "District of Columbia"
    if k not in COUNTYROWS[st]: unmapped["county"] += 1; UNM["county"].append((st, r["NAMELSAD_COUNTY_20"], g)); continue
    how["county:geoid"] += 1
    X[z]["county"][(st, k)] += part(r)[0]; X[z]["county_t"][(st, k)] += part(r)[1]
for z, d in CT_T.items():
    for cty, (l, t) in d.items():
        if cty in COUNTYROWS["Connecticut"]:
            X[z]["county"][("Connecticut", cty)] += l; X[z]["county_t"][("Connecticut", cty)] += t; how["county:CT via towns"] += 1

OUT = collections.defaultdict(dict); stats = collections.Counter()
for z in sorted(X):
    land, tot = ZL[z]; use_t = land == 0
    # primary state: most area over the county parts (else town/place)
    sta = collections.Counter()
    for L in ("county", "town", "place"):
        for (st, k), v in X[z][L + "_t" if use_t else L].items(): sta[st] += v
        if sta: break
    pst = sta.most_common(1)[0][0]
    rec = {"st": AB[pst]}
    for L in ("place", "town", "county"):
        d = X[z][L + "_t" if use_t else L]; den = tot if use_t else land
        if not d or not den: continue
        items = sorted(((v / den, st, k) for (st, k), v in d.items()), key=lambda x: (-x[0], x[2]))
        keep = [x for x in items if x[0] >= 0.01] or items[:1]
        stats[L + " dropped<1%"] += len(items) - len(keep)
        rec[L] = [[k, round(s, 2)] + ([AB[st]] if st != pst else []) for s, st, k in keep]
        stats[L + " entries"] += len(keep); stats[L + " zctas"] += 1
    if len(sta) > 1: stats["cross-state zctas"] += 1
    OUT[z[:3]][z] = rec
os.makedirs(os.path.join(D, "zcta_xref"), exist_ok=True)
sizes = {}
def enc(v): return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
for pre in sorted(OUT):
    body = ",".join(json.dumps(z) + ":{" + ",".join((L if L != "st" else "st") + ":" + enc(v) for L, v in rec.items()) + "}" for z, rec in OUT[pre].items())
    js = "__zxref(" + json.dumps(pre) + ",{" + body + "});\n"
    open(os.path.join(D, "zcta_xref", pre + ".js"), "w", encoding="utf-8").write(js)
    sizes[pre] = (len(js.encode()), len(gzip.compress(js.encode(), 6)))
rep = {"zctas": len(X), "files": len(OUT), "how": how, "unmapped": unmapped, "stats": stats, "sizes": sizes,
       "unmapped_examples": {k: v[:40] for k, v in UNM.items()}, "unmapped_incorporated": sorted(set(tuple(x) for k, v in UNM.items() for x in v if x[-1] in ("C1", "C5", "T1", "C2", "C7", "C8")))}
print(json.dumps({k: v for k, v in rep.items() if k not in ("sizes", "unmapped_examples")}, indent=1))
if a.report: json.dump(rep, open(a.report, "w"), indent=1, ensure_ascii=False)
