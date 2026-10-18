#!/usr/bin/env python3
"""data-v3/geo/towns_2024.geojson and places_2024.geojson: every Census TIGER 2024 county subdivision and place (public domain)
of the 50 states and DC, one feature per GEOID (the feature id), for v3.
Geometry: per state and layer, the TIGER coverage (cousubs tile the state; places do not overlap) is simplified as a whole
with shapely.coverage_simplify at --tol degrees (default 0.0005, finer than v2's 0.002), so neighbours keep identical
shared edges; coordinates are snapped to 5 decimals (about 1 m) with
shapely.set_precision, which keeps every geometry valid. A state layer whose input is not a valid coverage falls back
to per-feature topology-preserving simplification (reported).
Properties: TIGER fields (statefp, countyfp, name, namelsad, lsad, classfp, funcstat, aland, awater), state and county names,
and the v2 rows that carry the feature, from the tools/build_town_files.py reports:
  towns:  v2_parts = ["<county>|<parts row name>", ...]
  places: v2_places = places/<State>.js row name or null; v2_parts = county-clipped parts rows of the place.
Files over --gzip-mb (default 5) are written gzipped (.geojson.gz) instead.
usage: v3_geojson_2024.py <repo> <tiger_st_dir> <tl_2024_us_county.zip> <reports_dir> [--tol 0.0005] [--gzip-mb 5] [--states A,B (test only)] [--out DIR]"""
import sys, os, json, gzip, collections, shapely
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shapely.geometry import mapping
from town_gaps import recs, FIPS
FIPS = dict(FIPS, **{"11": "District of Columbia"})
a = sys.argv[1:]; opt = lambda k, d: a[a.index(k) + 1] if k in a else d
repo, td, cz, rd = [x for x in a if not x.startswith("--") and x not in (opt("--tol", ""), opt("--gzip-mb", ""), opt("--states", ""), opt("--out", ""))][:4]
TOL = float(opt("--tol", "0.0005")); GZ = float(opt("--gzip-mb", "5")) * 1e6
CN = {(d["STATEFP"], d["COUNTYFP"]): d["NAMELSAD"] for d, g in recs(cz)}
rnd = lambda c: [round(c[0], 5), round(c[1], 5)]
def geom(g):
    g = shapely.set_precision(g, 1e-5)  # snap to the 5-decimal grid with a valid result (plain rounding can self-touch)
    if g.geom_type == "GeometryCollection": g = shapely.MultiPolygon([p for p in g.geoms if p.geom_type == "Polygon"])
    m = mapping(g)
    if m["type"] == "Polygon": return {"type": "Polygon", "coordinates": [[rnd(c) for c in r] for r in m["coordinates"]]}
    return {"type": "MultiPolygon", "coordinates": [[[rnd(c) for c in r] for r in p] for p in m["coordinates"]]}
stats = collections.Counter(); fb = []
outs = {k: open(os.path.join(opt("--out", os.path.join(repo, "data-v3/geo")), "%s_2024.geojson" % k), "w") for k in ("towns", "places")}
for f in outs.values(): f.write('{"type":"FeatureCollection","features":[\n')
first = {"towns": True, "places": True}
ONLY = opt("--states", None); ONLY = set(ONLY.split(",")) if ONLY else None
for sf, st in sorted(FIPS.items()):
    if ONLY and st not in ONLY: continue
    rp = os.path.join(rd, st.replace(" ", "_") + ".json"); V = collections.defaultdict(list); VP = {}
    if os.path.exists(rp):
        R = json.load(open(rp))
        for r in R["rows"]:
            if r.get("geoid"): V[r["geoid"]].append(r["county"] + "|" + r["name"])
        for r in R["place_rows"]:
            if r.get("geoid"): VP[r["geoid"]] = r["name"]
    for z, k in (("cousub", "towns"), ("place", "places")):
        F = list(recs(os.path.join(td, "tl_2024_%s_%s.zip" % (sf, z))))
        G = [g for d, g in F]
        if shapely.coverage_is_valid(G): S = list(shapely.coverage_simplify(G, TOL))
        else: S = [g.simplify(TOL, preserve_topology=True) for g in G]; fb.append((st, z))
        for (d, g0), g in zip(F, S):
            if g.is_empty: g = g0.simplify(TOL / 4, preserve_topology=True); stats["empty_resimplified"] += 1
            p = {"geoid": d["GEOID"], "state": st, "statefp": sf}
            if k == "towns": p.update(countyfp=d["COUNTYFP"], county=CN.get((sf, d["COUNTYFP"])))
            p.update(name=d["NAME"], namelsad=d["NAMELSAD"], lsad=d["LSAD"], classfp=d["CLASSFP"], funcstat=d["FUNCSTAT"],
                     aland=d["ALAND"], awater=d["AWATER"])
            if k == "places": p["incorporated"] = d["CLASSFP"].startswith("C"); p["v2_places"] = VP.get(d["GEOID"])
            p["v2_parts"] = V.get(d["GEOID"], [])
            ft = {"type": "Feature", "id": d["GEOID"], "properties": p, "geometry": geom(g)}
            outs[k].write(("" if first[k] else ",\n") + json.dumps(ft, separators=(",", ":"), ensure_ascii=False)); first[k] = False
            stats[k] += 1; stats[k + "_v2"] += bool(p["v2_parts"] or p.get("v2_places"))
    print(st, dict(stats), flush=True)
for k, f in outs.items():
    f.write("\n]}\n"); f.close(); pth = f.name
    if os.path.getsize(pth) > GZ:
        with open(pth, "rb") as i, gzip.GzipFile(pth + ".gz", "wb", mtime=0) as o: o.write(i.read())
        os.remove(pth); pth += ".gz"
    print(k, pth, os.path.getsize(pth))
print("fallback", fb, dict(stats))
