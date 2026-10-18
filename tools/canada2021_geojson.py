#!/usr/bin/env python3
"""Canadian boundaries for v3 (data-v3/geo), from Statistics Canada 2021 Census cartographic boundary files (CBF) and the
Elections Canada 2023 Representation Order FED file. Licences: Statistics Canada Open Licence (StatCan files); Open Government
Licence - Canada (Elections Canada file, via open.canada.ca).
Inputs (tools/statcan2021_fetch.py <raw> PR:attr CD:attr FED CSD, and FederalElectoralDistricts_SHP.zip unzipped to <raw>/fed2023):
  CSD.jsonl.gz, FED.jsonl.gz (Esri JSON, EPSG:3347), PR_attr.jsonl.gz, CD_attr.jsonl.gz, fed2023/ED_CF.shp (EPSG:3347 too).
Geometry: done in NAD83 / Statistics Canada Lambert (metres).
  - CSD: the CBF CSD coverage, simplified as a whole with shapely.coverage_simplify at --tol metres (default 50 m, about the
    0.0005 deg used for towns_2024 / places_2024). CD and PR are the unions of the simplified CSDs (CSDUID[:4] / [:2]), so the
    three layers nest exactly and share identical edges.
  - FED 2013 (CBF, clipped to the shoreline like the CSDs) and FED 2023 (Elections Canada; not clipped, it extends into water,
    so it is clipped here to the CBF land, i.e. the union of the full-resolution CSDs) are each simplified as their own coverage.
  Output coordinates: WGS84 lon/lat (pyproj EPSG:3347 -> EPSG:4326; NAD83 ~ WGS84 at this scale), snapped to 5 decimals with
  shapely.set_precision (valid geometry).
Outputs (--out, not in git): ca_pr_2021, ca_cd_2021, ca_csd_2021, ca_fed2013, ca_fed2023 .geojson (gzipped, mtime 0, when
over 5 MB); feature id = PRUID / CDUID / CSDUID / FEDUID / FED number.
Small tables (data-v3/geo, in git): ca_pr_2021.csv, ca_cd_2021.csv, ca_csd_2021.csv (attributes and full-resolution FED
overlaps), ca_fed2013.csv, ca_fed2023.csv, ca_fed2013_2023.csv (pairs by full-resolution land overlap).
usage: canada2021_geojson.py <repo> <raw_dir> --out DIR [--tol 50] [--report R.json]"""
import sys, os, json, gzip, csv, collections, time
import shapely, shapefile, pyproj
from shapely.geometry import Polygon, MultiPolygon, LinearRing, shape, mapping
from shapely.strtree import STRtree
from shapely.ops import transform
a = sys.argv[1:]; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
repo, raw = [x for x in a if not x.startswith("--") and x not in (opt("--out"), opt("--tol"), opt("--report"))][:2]
OUT = opt("--out"); TOL = float(opt("--tol", "50")); os.makedirs(OUT, exist_ok=True); t0 = time.time()
log = lambda *x: print("%5.0fs" % (time.time() - t0), *x, flush=True)

def esri(rings):
    """Esri polygon rings (outer rings clockwise, holes counter-clockwise) -> valid shapely (Multi)Polygon."""
    outs, holes = [], []
    for r in rings:
        if len(r) < 4: continue
        lr = LinearRing(r); (holes if lr.is_ccw else outs).append(lr)
    P = [[Polygon(o), []] for o in outs]
    for h in holes:
        hp = Polygon(h).representative_point(); c = [p for p in P if p[0].contains(hp)]
        if c: min(c, key=lambda p: p[0].area)[1].append(h)
    g = MultiPolygon([Polygon(o.exterior, hs) for o, hs in P]) if len(P) > 1 else Polygon(P[0][0].exterior, P[0][1])
    return g if g.is_valid else shapely.make_valid(g).buffer(0)
def jl(n): return [json.loads(l) for l in gzip.open(os.path.join(raw, n + ".jsonl.gz"))]
def jg(n):  # stream: parse geometry line by line so the raw Esri JSON is never held in memory all at once
    for l in gzip.open(os.path.join(raw, n + ".jsonl.gz")):
        f = json.loads(l); yield (f["attributes"], esri(f["geometry"]["rings"]))
PRa = {f["attributes"]["PRUID"]: f["attributes"] for f in jl("PR_attr")}
CDa = {f["attributes"]["CDUID"]: f["attributes"] for f in jl("CD_attr")}
CSD = list(jg("CSD"))
# CSDs the service returned only with 10 m server-side generalization (see statcan2021_fetch.py --gen10): overlaps with their
# full-resolution neighbours are removed (the neighbours win), leaving gaps of at most about 10 m along the shared edges.
GEN = []
gp = os.path.join(raw, "CSD_gen10.jsonl.gz")
if os.path.exists(gp):
    T0 = STRtree([g for _, g in CSD])
    for f in jl("CSD_gen10"):
        g = esri(f["geometry"]["rings"])
        if not f["generalized_m"]: CSD.append((f["attributes"], g)); continue
        nb = [CSD[j][1] for j in T0.query(g, predicate="intersects")]
        g2 = g.difference(shapely.unary_union(nb)) if nb else g
        CSD.append((f["attributes"], shapely.make_valid(g2).buffer(0))); GEN.append(f["attributes"]["CSDUID"])
GEN_RETRIED = [f["attributes"]["CSDUID"] for f in (jl("CSD_gen10") if os.path.exists(gp) else []) if not f["generalized_m"]]
fc = os.path.join(raw, "CSD_failed.json")
if os.path.exists(fc): assert {f["attributes"]["CSDUID"] for f in json.load(open(fc))} <= set(GEN), "CSD geometry missing"
CSD.sort(key=lambda x: x[0]["CSDUID"])
F13 = list(jg("FED"))
# FEDs the REST service cannot return (FED 62001 Nunavut: an HTTP 500 on every request) are rebuilt from the CSDs when the FED is a
# whole territory (the three territories are one FED each, so FED = PR = union of its CSDs); anything else stops the build.
fp = os.path.join(raw, "FED_failed.json"); FED_DERIVED = []; FED_GEN = []
FG = {f["attributes"]["FEDUID"]: f for f in (jl("FED_gen10") if os.path.exists(os.path.join(raw, "FED_gen10.jsonl.gz")) else [])}
for f in (json.load(open(fp)) if os.path.exists(fp) else []):
    if f["attributes"]["FEDUID"] in FG and FG[f["attributes"]["FEDUID"]]["generalized_m"] == 0:  # full resolution on retry
        g = FG[f["attributes"]["FEDUID"]]; F13.append((g["attributes"], esri(g["geometry"]["rings"]))); continue
    if f["attributes"]["FEDUID"] in FG and f["attributes"]["FEDUID"][:2] not in ("60", "61", "62"):  # 10 m generalized: fixed below
        FED_GEN.append(FG[f["attributes"]["FEDUID"]]); continue
    d = f["attributes"]; assert d["FEDUID"][:2] in ("60", "61", "62"), ("FED geometry missing", d["FEDUID"])
    F13.append((d, shapely.unary_union([g for c, g in CSD if c["PRUID"] == d["PRUID"]]))); FED_DERIVED.append(d["FEDUID"])
F13.sort(key=lambda x: x[0]["FEDUID"])
r = shapefile.Reader(os.path.join(raw, "fed2023", "ED_CF.shp"), encoding="utf-8")
F23 = [(rec.as_dict(), shape(r.shape(i).__geo_interface__).buffer(0)) for i, rec in enumerate(r.iterRecords())]
log("loaded", len(CSD), len(F13), len(F23), "CD", len(CDa), "PR", len(PRa))
# CBF land = union of the full-resolution CSDs; clipped per feature against only the CSDs it touches (a single national union
# of the CSDs needs more memory than the build box has).
TL = STRtree([g for _, g in CSD])
def clip_land(g):
    nb = [CSD[j][1] for j in TL.query(g, predicate="intersects")]
    return shapely.make_valid(g.intersection(shapely.unary_union(nb))) if nb else shapely.Polygon()
def polys(g):
    if g.geom_type == "GeometryCollection": g = shapely.MultiPolygon([p for q in g.geoms for p in getattr(q, "geoms", [q]) if p.geom_type == "Polygon"])
    return g
F23 = [(d, polys(clip_land(g))) for d, g in F23]; log("fed2023 clipped")
# FED 2013 returned only with 10 m server-side generalization (59028 Skeena--Bulkley Valley): clipped to the CBF land and with
# the overlaps with its full-resolution neighbours removed (the neighbours win).
T1 = STRtree([g for _, g in F13])
for f in FED_GEN:
    g = polys(clip_land(esri(f["geometry"]["rings"]))); nb = [F13[j][1] for j in T1.query(g, predicate="intersects")]
    F13.append((f["attributes"], shapely.make_valid(g.difference(shapely.unary_union(nb))).buffer(0)))
F13.sort(key=lambda x: x[0]["FEDUID"])
R = {"fed2013_generalized_10m": [f["attributes"]["FEDUID"] for f in FED_GEN], "csd_generalized_10m": GEN, "csd_full_on_retry": GEN_RETRIED, "fed2013_rebuilt_from_csd": FED_DERIVED, "tol_m": TOL, "counts": {"PR": len(PRa), "CD": len(CDa), "CSD": len(CSD), "FED2013": len(F13), "FED2023": len(F23)}}

def simp(G, name):
    v = bool(shapely.coverage_is_valid(G)); S = list(shapely.coverage_simplify(G, TOL)) if v else [g.simplify(TOL) for g in G]
    S = [s if not s.is_empty else g.simplify(TOL / 4) for s, g in zip(S, G)]
    sd = sum(s.symmetric_difference(g).area for s, g in zip(S, G)); ar = sum(g.area for g in G)
    # Hausdorff is quadratic in vertices; measured only on features under 20,000 input vertices (others: area error only)
    H = sorted(s.hausdorff_distance(g) for s, g in zip(S, G) if shapely.get_num_coordinates(g) < 20000) or [0]
    R[name] = {"input_valid_coverage": v, "output_valid_coverage": bool(shapely.coverage_is_valid(S)),
               "area_error_pct": round(100 * sd / ar, 4), "hausdorff_m_median": round(H[len(H) // 2], 1), "hausdorff_m_max": round(H[-1], 1),
               "vertices_in": int(sum(shapely.get_num_coordinates(G))), "vertices_out": int(sum(shapely.get_num_coordinates(S)))}
    log(name, R[name]); return S
Scsd = simp([g for _, g in CSD], "CSD")
S13 = simp([g for _, g in F13], "FED2013"); S23 = simp([g for _, g in F23], "FED2023")
by = lambda k: collections.defaultdict(list)
cdg, prg, cdf, prf = by(0), by(0), by(0), by(0)
for (d, g), s in zip(CSD, Scsd):
    u = d["CSDUID"]; cdg[u[:4]].append(s); prg[u[:2]].append(s); cdf[u[:4]].append(g); prf[u[:2]].append(g)
CDs = {k: shapely.coverage_union_all(v) for k, v in cdg.items()}; PRs = {k: shapely.coverage_union_all(v) for k, v in prg.items()}
CDfull = {k: shapely.coverage_union_all(v) for k, v in cdf.items()}; PRfull = {k: shapely.coverage_union_all(v) for k, v in prf.items()}
R["CD_vs_CBF_shape_area_pct"] = round(100 * max(abs(CDfull[k].area - CDa[k]["SHAPE_Area"]) / CDa[k]["SHAPE_Area"] for k in CDa), 4)
R["PR_vs_CBF_shape_area_pct"] = round(100 * max(abs(PRfull[k].area - PRa[k]["SHAPE_Area"]) / PRa[k]["SHAPE_Area"] for k in PRa), 4)
R["CD_missing"] = sorted(set(CDa) - set(CDs)); R["PR_missing"] = sorted(set(PRa) - set(PRs))
log("dissolved", R["CD_vs_CBF_shape_area_pct"], R["PR_vs_CBF_shape_area_pct"])

# full-resolution alignment tables
def pairs(A, B):
    T = STRtree([g for _, g in B]); out = collections.defaultdict(float)
    for i, (_, g) in enumerate(A):
        for j in T.query(g, predicate="intersects"):
            x = g.intersection(B[j][1]).area
            if x > 0: out[(i, j)] += x
    return out
P13 = pairs(CSD, F13); P23 = pairs(CSD, F23); PF = pairs(F13, F23); log("pairs")
best = lambda P, i: max(((x, j) for (ii, j), x in P.items() if ii == i), default=(0, None))
idx13 = collections.defaultdict(list); idx23 = collections.defaultdict(list); idxF = collections.defaultdict(list)
for (i, j), x in P13.items(): idx13[i].append((x, j))
for (i, j), x in P23.items(): idx23[i].append((x, j))
for (i, j), x in PF.items(): idxF[i].append((x, j))
gd = lambda p: os.path.join(repo, "data-v3", "geo", p)
def W(name, head, rows):
    with open(gd(name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(head); w.writerows(rows)
W("ca_pr_2021.csv", ["pruid", "dguid", "name_en", "name_fr", "abbr_en", "abbr_fr", "landarea_km2"],
  [[k, d["DGUID"], d["PRENAME"], d["PRFNAME"], d["PREABBR"], d["PRFABBR"], d["LANDAREA"]] for k, d in sorted(PRa.items())])
W("ca_cd_2021.csv", ["cduid", "dguid", "name", "type", "landarea_km2", "pruid"],
  [[k, d["DGUID"], d["CDNAME"], d["CDTYPE"], d["LANDAREA"], d["PRUID"]] for k, d in sorted(CDa.items())])
def top(lst, F, key, k=3):
    tot = sum(x for x, _ in lst) or 1; s = sorted(lst, reverse=True)[:k]
    return ";".join("%s:%.1f" % (key(F[j][0]), 100 * x / tot) for x, j in s)
k13 = lambda d: d["FEDUID"]; k23 = lambda d: str(d["ED_CF_NUM"])
rows = []
for i, (d, g) in enumerate(CSD):
    rows.append([d["CSDUID"], d["DGUID"], d["CSDNAME"], d["CSDTYPE"], d["LANDAREA"], d["PRUID"], d["CSDUID"][:4],
                 top(idx13[i], F13, k13), top(idx23[i], F23, k23)])
rows.sort(); W("ca_csd_2021.csv", ["csduid", "dguid", "name", "type", "landarea_km2", "pruid", "cduid",
               "fed2013_share_pct (FEDUID:% of CSD area, top 3)", "fed2023_share_pct (FED number:% of CSD area, top 3)"], rows)
W("ca_fed2013.csv", ["feduid", "dguid", "name", "name_en", "name_fr", "landarea_km2", "pruid", "fed2023_share_pct (top 3)"],
  sorted([[d["FEDUID"], d["DGUID"], d["FEDNAME"], d["FEDENAME"], d["FEDFNAME"], d["LANDAREA"], d["PRUID"], top(idxF[i], F23, k23)] for i, (d, g) in enumerate(F13)]))
W("ca_fed2023.csv", ["fed_num", "name_en", "name_fr", "pruid", "land_km2_cbf_clip"],
  sorted([[str(d["ED_CF_NUM"]), d["ED_NAMEE"], d["CF_NOMF"], str(d["ED_CF_NUM"])[:2], round(g.area / 1e6, 4)] for d, g in F23]))
pr = []
for (i, j), x in sorted(PF.items()):
    a13, a23 = F13[i][1].area, F23[j][1].area
    if x / a13 >= 0.001 or x / a23 >= 0.001:
        pr.append([F13[i][0]["FEDUID"], F13[i][0]["FEDENAME"], str(F23[j][0]["ED_CF_NUM"]), F23[j][0]["ED_NAMEE"],
                   round(100 * x / a13, 3), round(100 * x / a23, 3), int(F13[i][0]["FEDUID"] == str(F23[j][0]["ED_CF_NUM"]))])
W("ca_fed2013_2023.csv", ["feduid_2013", "name_2013", "fed_num_2023", "name_2023", "pct_of_2013", "pct_of_2023", "same_number"], pr)
R["fed_pairs"] = len(pr)
same = [p for p in pr if p[4] >= 99 and p[5] >= 99]; R["fed_essentially_same_ge99"] = len(same)
R["fed_same_number"] = sum(p[6] for p in pr); log("csv")

TR = pyproj.Transformer.from_crs(3347, 4326, always_xy=True).transform
def gj(g):
    g = shapely.set_precision(transform(TR, g), 1e-5)
    if g.geom_type == "GeometryCollection": g = MultiPolygon([p for p in g.geoms if p.geom_type == "Polygon"])
    m = mapping(g); rd = lambda c: [round(c[0], 5), round(c[1], 5)]
    if m["type"] == "Polygon": return {"type": "Polygon", "coordinates": [[rd(c) for c in r] for r in m["coordinates"]]}
    return {"type": "MultiPolygon", "coordinates": [[[rd(c) for c in r] for r in p] for p in m["coordinates"]]}
def write(name, feats):
    p = os.path.join(OUT, name + ".geojson"); s = '{"type":"FeatureCollection","features":[\n' + ",\n".join(
        json.dumps({"type": "Feature", "id": i, "properties": pp, "geometry": gj(g)}, separators=(",", ":"), ensure_ascii=False)
        for i, pp, g in feats) + "\n]}\n"
    b = s.encode()
    if len(b) > 5e6:
        with gzip.GzipFile(p + ".gz", "wb", mtime=0) as o: o.write(b)
        if os.path.exists(p): os.remove(p)
        p += ".gz"
    R.setdefault("files", {})[os.path.basename(p)] = {"bytes": os.path.getsize(p), "features": len(feats), "geojson_bytes": len(b)}
    log(name, R["files"][os.path.basename(p)])
prn = lambda u: (PRa[u]["PRENAME"], PRa[u]["PRFNAME"])
write("ca_pr_2021", [(k, {"pruid": k, "dguid": d["DGUID"], "name_en": d["PRENAME"], "name_fr": d["PRFNAME"], "abbr_en": d["PREABBR"],
       "abbr_fr": d["PRFABBR"], "landarea_km2": d["LANDAREA"]}, PRs[k]) for k, d in sorted(PRa.items())])
write("ca_cd_2021", [(k, {"cduid": k, "dguid": d["DGUID"], "name": d["CDNAME"], "type": d["CDTYPE"], "landarea_km2": d["LANDAREA"],
       "pruid": d["PRUID"], "prname_en": prn(d["PRUID"])[0], "prname_fr": prn(d["PRUID"])[1]}, CDs[k]) for k, d in sorted(CDa.items())])
cs = []
for (d, g), s, row in zip(CSD, Scsd, [None] * len(CSD)):
    u = d["CSDUID"]
    cs.append((u, {"csduid": u, "dguid": d["DGUID"], "name": d["CSDNAME"], "type": d["CSDTYPE"], "landarea_km2": d["LANDAREA"],
                   "pruid": d["PRUID"], "cduid": u[:4], "cdname": CDa[u[:4]]["CDNAME"], "cdtype": CDa[u[:4]]["CDTYPE"]}, s))
write("ca_csd_2021", sorted(cs, key=lambda x: x[0]))
write("ca_fed2013", sorted([(d["FEDUID"], {"feduid": d["FEDUID"], "dguid": d["DGUID"], "name": d["FEDNAME"], "name_en": d["FEDENAME"],
       "name_fr": d["FEDFNAME"], "landarea_km2": d["LANDAREA"], "pruid": d["PRUID"], "rep_order": "2013"}, s)
       for (d, g), s in zip(F13, S13)], key=lambda x: x[0]))
write("ca_fed2023", sorted([(str(d["ED_CF_NUM"]), {"fed_num": str(d["ED_CF_NUM"]), "name_en": d["ED_NAMEE"], "name_fr": d["CF_NOMF"],
       "pruid": str(d["ED_CF_NUM"])[:2], "rep_order": "2023"}, s) for (d, g), s in zip(F23, S23)], key=lambda x: x[0]))
if opt("--report"): json.dump(R, open(opt("--report"), "w"), indent=1)
log("done")
