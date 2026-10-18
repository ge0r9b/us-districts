#!/usr/bin/env python3
"""v3 tribal areas from Census TIGER/Line 2024 (public domain): AIANNH (American Indian / Alaska Native / Native Hawaiian
areas: reservations and off-reservation trust land, OTSAs, SDTSAs, TDSAs, state reservations, Hawaiian home lands, and the
Alaska Native village statistical areas, ANVSA = CLASSFP E1, which TIGER ships inside the AIANNH file), ANRC (Alaska Native
regional corporations, a separate file) and AITSN (tribal subdivisions, e.g. Navajo chapters).
AIANNH features overlap by design (e.g. an OTSA or SDTSA can overlap a reservation; R and T parts share AIANNHCE), so the
layer is NOT a coverage: each feature is simplified on its own with topology-preserving simplify at --tol degrees (default
0.0005, as towns_2024); ANRC and AITSN are coverages (coverage_simplify). Coordinates snapped to 5 decimals, valid geometry.
Each feature gets `states` and `counties` (GEOIDs of TIGER 2024 counties it overlaps by >= 0.1% of its area or >= 1 km2) for
geography-to-institution alignment.
Outputs (--out, not in git, gzipped mtime 0 when over 5 MB): aiannh_2024, anrc_2024, aitsn_2024 .geojson; feature id = GEOID.
Small CSVs in git (data-v3/geo): aiannh_2024.csv, anrc_2024.csv, aitsn_2024.csv.
usage: v3_aiannh_2024.py <repo> <dir with tl_2024_us_aiannh.zip tl_2024_02_anrc.zip tl_2024_us_aitsn.zip> <tl_2024_us_county.zip> --out DIR [--tol 0.0005]"""
import sys, os, json, gzip, csv, shapely, shapefile
from shapely.geometry import shape, mapping
from shapely.strtree import STRtree
a = sys.argv[1:]; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
repo, src, cz = [x for x in a if not x.startswith("--") and x not in (opt("--out"), opt("--tol"))][:3]
OUT = opt("--out"); TOL = float(opt("--tol", "0.0005")); os.makedirs(OUT, exist_ok=True)
def recs(p):
    r = shapefile.Reader(p, encoding="utf-8")
    return [(rec.as_dict(), shapely.make_valid(shape(sh.__geo_interface__))) for rec, sh in zip(r.iterRecords(), r.iterShapes())]
C = recs(cz); CT = STRtree([g for _, g in C])
def where(g):
    hit = []
    for j in CT.query(g, predicate="intersects"):
        x = g.intersection(C[j][1]).area
        if x > 0 and (x >= 0.001 * g.area or x * 1e4 >= 1 / 12): hit.append(C[j][0]["GEOID"])  # ~1 km2 in deg2 at mid lat
    hit.sort(); return sorted({h[:2] for h in hit}), hit
rnd = lambda c: [round(c[0], 5), round(c[1], 5)]
def geom(g):
    g = shapely.set_precision(g, 1e-5)
    if g.geom_type == "GeometryCollection": g = shapely.MultiPolygon([p for p in g.geoms if p.geom_type == "Polygon"])
    m = mapping(g)
    if m["type"] == "Polygon": return {"type": "Polygon", "coordinates": [[rnd(c) for c in r] for r in m["coordinates"]]}
    return {"type": "MultiPolygon", "coordinates": [[[rnd(c) for c in r] for r in p] for p in m["coordinates"]]}
REP = {}
def build(name, f, fields, coverage):
    R = sorted(recs(os.path.join(src, f)), key=lambda x: x[0]["GEOID"]); G = [g for _, g in R]
    assert len({d["GEOID"] for d, _ in R}) == len(R), name
    cov = coverage and bool(shapely.coverage_is_valid(G))
    S = list(shapely.coverage_simplify(G, TOL)) if cov else [g.simplify(TOL, preserve_topology=True) for g in G]
    S = [s if not s.is_empty else g for s, g in zip(S, G)]
    feats, rows = [], []
    for (d, g), s in zip(R, S):
        st, co = where(g)
        p = {k.lower(): d[k] for k in fields}; p["states"] = st; p["counties"] = co
        feats.append(json.dumps({"type": "Feature", "id": d["GEOID"], "properties": p, "geometry": geom(s)}, separators=(",", ":"), ensure_ascii=False))
        rows.append([d[k] for k in fields] + [";".join(st), ";".join(co)])
    with open(os.path.join(repo, "data-v3", "geo", name + ".csv"), "w", newline="", encoding="utf-8") as o:
        w = csv.writer(o, lineterminator="\n"); w.writerow([k.lower() for k in fields] + ["states", "counties"]); w.writerows(rows)
    b = ('{"type":"FeatureCollection","features":[\n' + ",\n".join(feats) + "\n]}\n").encode(); p = os.path.join(OUT, name + ".geojson")
    if len(b) > 5e6:
        with gzip.GzipFile(p + ".gz", "wb", mtime=0) as o: o.write(b)
        p += ".gz"
    else: open(p, "wb").write(b)
    REP[name] = {"features": len(R), "coverage_simplified": cov, "bytes": os.path.getsize(p), "geojson_bytes": len(b),
                 "vertices_in": int(sum(shapely.get_num_coordinates(G))), "vertices_out": int(sum(shapely.get_num_coordinates(S)))}
    print(name, REP[name], flush=True)
base = ["GEOID", "NAME", "NAMELSAD", "LSAD", "CLASSFP", "MTFCC", "FUNCSTAT", "ALAND", "AWATER"]
build("aiannh_2024", "tl_2024_us_aiannh.zip", ["GEOID", "AIANNHCE", "NAME", "NAMELSAD", "LSAD", "CLASSFP", "COMPTYP", "AIANNHR", "MTFCC", "FUNCSTAT", "ALAND", "AWATER"], False)
build("anrc_2024", "tl_2024_02_anrc.zip", base, True)
build("aitsn_2024", "tl_2024_us_aitsn.zip", ["GEOID", "AIANNHCE", "TRSUBCE"] + base[1:], False)
json.dump(REP, open(os.path.join(OUT, "aiannh_report.json"), "w"), indent=1)
