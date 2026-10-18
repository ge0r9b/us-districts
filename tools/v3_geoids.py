#!/usr/bin/env python3
"""Write stable Census TIGER 2024 GEOIDs for every v2 boundary row to data-v3/geo/ (v2 files are not changed).

Matching per v2 row (state, name):
  ushouse/senate/statehouse: GEOID = state FIPS + v2 name (v2 names are the TIGER district codes, e.g. "01", "002", "BEN");
  counties, schools: TIGER NAME equal to the v2 name within the state;
  every candidate is then verified with the Gazetteer internal point (INTPTLAT/INTPTLONG) inside the v2 polygon.
  When several TIGER features share a name, the one whose internal point is inside the row's polygon is taken.
  match = "code+point" | "name+point" | "name" (point outside the simplified polygon, single candidate) |
          "point" (no name match, exactly one internal point inside) | "" (no match; geoid empty).
DC rows (wards, DCPS, delegate, county) come from v2/data/dc.js as the app shows them.
Towns: rows of v2/data/parts/<State>.js that came from TIGER county subdivisions (Iowa townships) get their GEOID
from the build report given with --towns-report (state abbreviation:path), e.g. IA:/path/ia_townships.json.
usage: v3_geoids.py <repo> --gaz <dir with 2024_Gaz_*_national.txt> [--towns-report IA:path ...]
"""
import sys, os, csv, json, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coverage_audit as A
from shapely.geometry import Point, Polygon, MultiPolygon

FIPS = {}
def gaz(d, k):
    out = collections.defaultdict(list)
    with open(os.path.join(d, "2024_Gaz_%s_national.txt" % k), encoding="utf-8", errors="replace") as f:
        h = [x.strip() for x in f.readline().split("\t")]
        for line in f:
            r = dict(zip(h, [x.strip() for x in line.split("\t")]))
            r.setdefault("NAME", "Congressional District " + r["GEOID"][2:])  # the CD Gazetteer has no NAME column
            if "not defined" in r["NAME"].lower() or r["GEOID"].endswith("ZZ") or r["GEOID"].endswith("ZZZ"): continue
            r["_type"] = k; out[r["USPS"]].append(r); FIPS[r["USPS"]] = r["GEOID"][:2]
    return out

def poly(enc, S=1000):
    ps = []
    for rg in enc:
        rings = []
        for fl in rg:
            o = []; x = y = 0
            for k in range(0, len(fl) - 1, 2): x += fl[k]; y += fl[k + 1]; o.append((x / S, y / S))
            if len(o) >= 3: rings.append(o)
        if rings:
            try: ps.append(Polygon(rings[0], rings[1:]))
            except Exception: pass
    if not ps: return None
    g = MultiPolygon(ps); return g if g.is_valid else g.buffer(0)

def inside(g, r):
    return g is not None and g.buffer(0.002).contains(Point(float(r["INTPTLONG"]), float(r["INTPTLAT"])))

def match_rows(layer, rows, G, coded):
    out = []
    used = set()
    for idx, r in enumerate(rows):
        st, nm = r[0], str(r[1]); ab = A.ABBR[st]; g = poly(r[2])
        cands = G.get(ab, [])
        byname = [c for c in cands if c["GEOID"] == FIPS.get(ab, "") + nm] if coded else []
        if not byname: byname = [c for c in cands if c["NAME"] == nm]; coded_hit = False
        else: coded_hit = True
        pick = None; how = ""
        if len(byname) == 1:
            pick = byname[0]; how = ("code" if coded_hit else "name") + ("+point" if inside(g, pick) else "")
        elif len(byname) > 1:
            pin = [c for c in byname if inside(g, c) and c["GEOID"] not in used]
            if len(pin) == 1: pick = pin[0]; how = "name+point"
        else:
            pin = [c for c in cands if inside(g, c) and c["GEOID"] not in used]
            if len(pin) == 1: pick = pin[0]; how = "point"
        if pick: used.add(pick["GEOID"])
        out.append([layer, st, idx, nm, pick["GEOID"] if pick else "", pick["NAME"] if pick else "", pick["_type"] if pick else "", how])
    return out

def main():
    a = sys.argv[1:]; repo = a[0]; gd = a[a.index("--gaz") + 1]
    trep = [x for i, x in enumerate(a) if i > 0 and a[i - 1] == "--towns-report"]
    V = os.path.join(repo, "v2", "data"); O = os.path.join(repo, "data-v3", "geo"); os.makedirs(O, exist_ok=True)
    GZ = {k: gaz(gd, k) for k in ["counties", "119CDs", "sldu", "sldl", "unsd", "elsd", "scsd"]}
    SCH = collections.defaultdict(list)
    for k in ("unsd", "elsd", "scsd"):
        for s, l in GZ[k].items(): SCH[s] += l
    dcsrc = open(os.path.join(V, "dc.js"), encoding="utf-8").read()
    lit = lambda n: A.DEC.raw_decode(dcsrc, re.search(r"\b%s=" % n, dcsrc).end())[0]
    W, P = lit("W"), lit("P")
    L = {
      "ushouse": ("uscd.js", r"__uscd\(", GZ["119CDs"], True, [["District of Columbia", "98", P]]),
      "senate": ("ussldu.js", r"__usdist\(\"senate\",", GZ["sldu"], True, W),
      "statehouse": ("ussldl.js", r"__usdist\(\"statehouse\",", GZ["sldl"], True, W),
      "schools": ("ussch.js", r"__usdist\(\"schools\",", SCH, False, [["District of Columbia", "District of Columbia Public Schools", P]]),
      "counties": ("uscounties.js", r"__uscty\(", GZ["counties"], False, [["District of Columbia", "District of Columbia", P]]),
    }
    summary = {}
    for layer, (fn, pat, G, coded, dcrows) in L.items():
        rows = A.jsargs(os.path.join(V, fn), pat)[0]
        keep = [k for k, r in enumerate(rows) if r[0] != "District of Columbia"]
        base = [rows[k] for k in keep]
        if layer in ("senate", "statehouse"):
            # DC wards are TIGER SLDU 11001-11008 under both types; Nebraska (unicameral) shows its LDs as state house too
            G = dict(G); G["DC"] = GZ["sldu"]["DC"]
            if layer == "statehouse": G["NE"] = GZ["sldu"]["NE"]
        res = match_rows(layer, base + dcrows, G, coded)
        src = [str(k) for k in keep] + ["dc.js"] * len(dcrows)  # row = index in the v2 file ("dc.js" = row added by v2/data/dc.js)
        for x, k in zip(res, src): x[2] = k
        if layer == "ushouse":  # DC delegate district: v2 name "00" in the app, TIGER code 98
            for x in res:
                if x[1] == "District of Columbia": x[3] = "00"
        with open(os.path.join(O, layer + ".csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(["layer", "state", "row", "v2_name", "geoid", "tiger_name", "tiger_set", "match"]); w.writerows(res)
        summary[layer] = dict(collections.Counter(x[7] or "unmatched" for x in res)); summary[layer]["rows"] = len(res)
    towns = []
    for t in trep:
        ab, path = t.split(":", 1)
        st = [s for s, b in A.ABBR.items() if b == ab][0]
        for r in json.load(open(path)):
            if r.get("vertices"): towns.append(["towns", st, r["county"], r["name"], r["geoid"], r["funcstat"], "tiger-cousub-build-report"])
    if towns:
        with open(os.path.join(O, "towns.csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(["layer", "state", "county", "v2_name", "geoid", "funcstat", "match"]); w.writerows(towns)
        summary["towns"] = {"rows": len(towns)}
    json.dump(summary, open(os.path.join(O, "summary.json"), "w"), indent=1)
    print(json.dumps(summary, indent=1))

if __name__ == "__main__":
    main()
