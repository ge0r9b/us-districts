#!/usr/bin/env python3
"""Canadian boundaries for v3 (data-v3/geo), from Statistics Canada 2021 Census cartographic boundary files (CBF) and the
Elections Canada 2023 Representation Order FED file. Licences: Statistics Canada Open Licence (StatCan files); Open Government
Licence - Canada (Elections Canada file, via open.canada.ca).
Inputs (tools/statcan2021_fetch.py <raw> PR:attr CD:attr FED CSD, then --gen10 CSD and --gen10 FED, and
FederalElectoralDistricts_SHP.zip unzipped to <raw>/fed2023):
  CSD.jsonl.gz, FED.jsonl.gz (Esri JSON, EPSG:3347), CSD_gen10/FED_gen10, PR_attr.jsonl.gz, CD_attr.jsonl.gz, fed2023/ED_CF.shp.
Geometry is processed in NAD83 / Statistics Canada Lambert (EPSG:3347, metres).
  - Coverages are validated per province and repaired with shapely.coverage_clean where needed (see simp()).
  - CSD: the CBF CSD coverage, simplified as a whole with shapely.coverage_simplify at --tol metres (default 50 m, about the
    0.0005 deg used for towns_2024 / places_2024). CD and PR are the unions of the simplified CSDs (CSDUID[:4] / [:2]), so the
    three layers nest exactly and share identical edges.
  - FED 2013 (CBF, clipped to the shoreline like the CSDs) and FED 2023 (Elections Canada; it extends into water, so it is
    clipped here to the CBF land, the union of the full-resolution CSDs it touches) are each simplified as their own coverage.
  Output coordinates: WGS84 lon/lat (pyproj EPSG:3347 -> EPSG:4326; NAD83 ~ WGS84 at this scale), snapped to 5 decimals with
  shapely.set_precision. Every .geojson is gzipped with mtime 0 (byte-for-byte reproducible from the same inputs).
Runs in resumable stages (each caches its geometry as pickles in <out>/cache, so an interrupted build resumes at the next stage):
  load     parse inputs, rebuild/patch the features the REST service could not return, clip FED 2023 -> cache/load.pkl
  csd      coverage-simplify the CSDs -> cache/csd_simpl.pkl, ca_csd_2021.geojson.gz, data-v3/geo/ca_csd.csv
  pr, cd   dissolve the simplified CSDs -> ca_pr_2021 / ca_cd_2021 .geojson.gz, ca_pr.csv / ca_cd.csv
  fed2013, fed2023  simplify -> ca_fed2013 / ca_fed2023 .geojson.gz, ca_fed2013.csv / ca_fed2023.csv
  csv      rewrite the five attribute CSVs from cache/load.pkl only
  xref     full-resolution overlaps -> ca_csd_fed.csv (CSD -> FED 2013/2023 shares), ca_fed2013_2023.csv
Each stage merges its numbers into <out>/report.json.
usage: canada2021_geojson.py <repo> <raw_dir> --out DIR [--tol 50] --stage load|csd|pr|cd|fed2013|fed2023|xref|all"""
import sys, os, json, gzip, csv, collections, time, pickle
import shapely, shapefile, pyproj
from shapely.geometry import Polygon, MultiPolygon, LinearRing, shape, mapping
from shapely.strtree import STRtree
from shapely.ops import transform
a = sys.argv[1:]; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
repo, raw = [x for x in a if not x.startswith("--") and x not in (opt("--out"), opt("--tol"), opt("--stage"))][:2]
OUT = opt("--out"); TOL = float(opt("--tol", "50")); STAGE = opt("--stage", "all"); t0 = time.time()
CACHE = os.path.join(OUT, "cache"); os.makedirs(CACHE, exist_ok=True)
log = lambda *x: print("%5.0fs" % (time.time() - t0), *x, flush=True)
RP = os.path.join(OUT, "report.json"); R = json.load(open(RP)) if os.path.exists(RP) else {}
def save_report(): json.dump(R, open(RP, "w"), indent=1, sort_keys=True)
def cput(n, obj): pickle.dump(obj, open(os.path.join(CACHE, n + ".pkl.tmp"), "wb"), protocol=5); os.replace(os.path.join(CACHE, n + ".pkl.tmp"), os.path.join(CACHE, n + ".pkl"))
def cget(n): return pickle.load(open(os.path.join(CACHE, n + ".pkl"), "rb"))
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
def stage_load():
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
    R0 = {"fed2013_generalized_10m": [f["attributes"]["FEDUID"] for f in FED_GEN], "csd_generalized_10m": GEN, "csd_full_on_retry": GEN_RETRIED, "fed2013_rebuilt_from_csd": FED_DERIVED, "tol_m": TOL, "counts": {"PR": len(PRa), "CD": len(CDa), "CSD": len(CSD), "FED2013": len(F13), "FED2023": len(F23)}}

    cput("load", {"PRa": PRa, "CDa": CDa, "CSD": CSD, "F13": F13, "F23": F23})
    R.update(R0); save_report(); log("load cached")

def simp(G, name, grp):
    """Coverage simplification of the whole national coverage G (grp[i] = province of G[i]). Validity is checked per province
    (a national coverage_is_valid on the full-resolution data does not finish in reasonable time); a province whose coverage is
    not valid (edges not exactly matched next to the features patched from 10 m generalized geometry) is first repaired with
    shapely.coverage_clean (GEOS CoverageCleaner, automatic snapping distance, gap_width 0, so gaps are kept and only overlaps and
    unmatched edges are fixed). Then the whole coverage is simplified at once, so edges shared across provinces stay identical."""
    G = list(G); idx = collections.defaultdict(list); cleaned = {}
    for i, k in enumerate(grp): idx[k].append(i)
    for k, ii in sorted(idx.items()):
        sub = [G[i] for i in ii]
        if not shapely.coverage_is_valid(sub):
            bad = int(sum(not e.is_empty for e in shapely.coverage_invalid_edges(sub))); K = list(shapely.coverage_clean(sub))
            cleaned[k] = {"features_with_invalid_edges": bad, "area_moved_m2": round(sum(x.symmetric_difference(y).area for x, y in zip(sub, K)), 1),
                          "valid_after": bool(shapely.coverage_is_valid(K))}
            for i, g in zip(ii, K): G[i] = g
            log(name, "cleaned", k, cleaned[k])
    t = time.time(); S = list(shapely.coverage_simplify(G, TOL)); log(name, "simplified", round(time.time() - t))
    S = [s if not s.is_empty else g.simplify(TOL / 4) for s, g in zip(S, G)]
    sd = sum(s.symmetric_difference(g).area for s, g in zip(S, G)); ar = sum(g.area for g in G)
    # Hausdorff is quadratic in vertices; measured only on features under 20,000 input vertices (others: area error only)
    H = sorted(s.hausdorff_distance(g) for s, g in zip(S, G) if shapely.get_num_coordinates(g) < 20000) or [0]
    outv = {k: bool(shapely.coverage_is_valid([S[i] for i in ii])) for k, ii in sorted(idx.items())}
    R[name] = {"tol_m": TOL, "cleaned_before_simplify": cleaned, "output_valid_coverage_per_province": all(outv.values()),
               "output_invalid_provinces": [k for k, v in outv.items() if not v], "all_valid_geometry": bool(all(s.is_valid for s in S)),
               "area_error_pct": round(100 * sd / ar, 4), "hausdorff_m_median": round(H[len(H) // 2], 1), "hausdorff_m_max": round(H[-1], 1),
               "vertices_in": int(sum(shapely.get_num_coordinates(G))), "vertices_out": int(sum(shapely.get_num_coordinates(S)))}
    log(name, R[name]); return S
gd = lambda p: os.path.join(repo, "data-v3", "geo", p)
def W(name, head, rows):
    with open(gd(name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(head); w.writerows(rows)
    R.setdefault("csv", {})[name] = len(rows)
TR = pyproj.Transformer.from_crs(3347, 4326, always_xy=True).transform
def polys(g):  # polygonal part of a make_valid result
    if g.geom_type == "GeometryCollection": g = MultiPolygon([p for q in g.geoms for p in getattr(q, "geoms", [q]) if p.geom_type == "Polygon"])
    return g
def gj(g):
    g = transform(TR, g)
    if not g.is_valid: g = polys(shapely.make_valid(g))  # reprojection can make a ring self-touch; repair before snapping
    g = polys(shapely.set_precision(g, 1e-5))
    m = mapping(g); rd = lambda c: [round(c[0], 5), round(c[1], 5)]
    if m["type"] == "Polygon": return {"type": "Polygon", "coordinates": [[rd(c) for c in r] for r in m["coordinates"]]}
    return {"type": "MultiPolygon", "coordinates": [[[rd(c) for c in r] for r in p] for p in m["coordinates"]]}
def write(name, feats):
    p = os.path.join(OUT, name + ".geojson.gz"); b = ('{"type":"FeatureCollection","features":[\n' + ",\n".join(
        json.dumps({"type": "Feature", "id": i, "properties": pp, "geometry": gj(g)}, separators=(",", ":"), ensure_ascii=False)
        for i, pp, g in feats) + "\n]}\n").encode()
    with open(p + ".tmp", "wb") as fo:
        with gzip.GzipFile(filename="", fileobj=fo, mode="wb", mtime=0, compresslevel=9) as o: o.write(b)
    os.replace(p + ".tmp", p)
    R.setdefault("files", {})[os.path.basename(p)] = {"bytes": os.path.getsize(p), "features": len(feats), "geojson_bytes": len(b)}
    log(name, R["files"][os.path.basename(p)])
la = lambda d: round(d["LANDAREA"], 4)  # CBF LANDAREA (km2, 4 decimals in the source)
TERR = {"60", "61", "62"}

def stage_csd():
    L = cget("load"); CSD, CDa = L["CSD"], L["CDa"]
    S = simp([g for _, g in CSD], "CSD", [d["PRUID"] for d, _ in CSD]); cput("csd_simpl", S)
    write("ca_csd_2021", sorted([(d["CSDUID"], {"csduid": d["CSDUID"], "dguid": d["DGUID"], "name": d["CSDNAME"], "type": d["CSDTYPE"],
          "landarea_km2": la(d), "pruid": d["PRUID"], "cduid": d["CSDUID"][:4], "cdname": CDa[d["CSDUID"][:4]]["CDNAME"]}, s)
          for (d, g), s in zip(CSD, S)], key=lambda x: x[0]))
    W("ca_csd.csv", ["csduid", "dguid", "name", "type", "pruid", "cduid", "landarea_km2"],
      sorted([[d["CSDUID"], d["DGUID"], d["CSDNAME"], d["CSDTYPE"], d["PRUID"], d["CSDUID"][:4], la(d)] for d, _ in CSD]))
def dissolve(n):
    L = cget("load"); S = cget("csd_simpl"); grp, full = collections.defaultdict(list), collections.defaultdict(list)
    for (d, g), s in zip(L["CSD"], S): grp[d["CSDUID"][:n]].append(s); full[d["CSDUID"][:n]].append(g)
    A = L["PRa"] if n == 2 else L["CDa"]; nm = "PR" if n == 2 else "CD"
    D, FB = {}, []
    for k, v in sorted(grp.items()):
        # GEOS CoverageUnion needs exactly noded inputs and can refuse a coverage that coverage_is_valid accepts (a TopologyException
        # on PR 62); such groups fall back to the general unary_union (same result, slower) and are listed in the report.
        try: D[k] = shapely.coverage_union_all(v)
        except shapely.errors.GEOSException: D[k] = shapely.make_valid(shapely.unary_union(v)); FB.append(k)
    R[nm + "_union_fallback"] = FB
    # CoverageUnion does not guarantee a valid result (self-touching rings in the Arctic archipelago): repair those with make_valid
    BAD = sorted(k for k, g in D.items() if not g.is_valid)
    for k in BAD: D[k] = polys(shapely.make_valid(D[k]))
    R[nm + "_made_valid"] = BAD
    # check: the summed area of the full-resolution CSDs (a coverage, no overlaps) against the CBF SHAPE_Area of the published PR / CD
    err = {k: abs(sum(g.area for g in full[k]) - A[k]["SHAPE_Area"]) / A[k]["SHAPE_Area"] for k in A if k in full}
    R[nm + "_vs_CBF_shape_area_pct_max"] = round(100 * max(err.values()), 4)
    R[nm + "_vs_CBF_shape_area_worst"] = max(err, key=err.get)
    R[nm + "_missing"] = sorted(set(A) - set(D)); R[nm + "_extra"] = sorted(set(D) - set(A))
    log(nm, "dissolved", R[nm + "_vs_CBF_shape_area_pct_max"], R[nm + "_missing"]); return L, D
def stage_pr():
    L, D = dissolve(2); P = L["PRa"]
    t = lambda k: "territory" if k in TERR else "province"
    write("ca_pr_2021", [(k, {"pruid": k, "dguid": d["DGUID"], "name_en": d["PRENAME"], "name_fr": d["PRFNAME"], "abbr_en": d["PREABBR"],
          "abbr_fr": d["PRFABBR"], "type": t(k), "landarea_km2": la(d)}, D[k]) for k, d in sorted(P.items())])
    W("ca_pr.csv", ["pruid", "dguid", "name_en", "name_fr", "abbr_en", "abbr_fr", "type", "parent", "landarea_km2"],
      [[k, d["DGUID"], d["PRENAME"], d["PRFNAME"], d["PREABBR"], d["PRFABBR"], t(k), "CA", la(d)] for k, d in sorted(P.items())])
def stage_cd():
    L, D = dissolve(4); P, C = L["PRa"], L["CDa"]
    write("ca_cd_2021", [(k, {"cduid": k, "dguid": d["DGUID"], "name": d["CDNAME"], "type": d["CDTYPE"], "landarea_km2": la(d),
          "pruid": d["PRUID"], "prname_en": P[d["PRUID"]]["PRENAME"], "prname_fr": P[d["PRUID"]]["PRFNAME"]}, D[k]) for k, d in sorted(C.items())])
    W("ca_cd.csv", ["cduid", "dguid", "name", "type", "pruid", "landarea_km2"],
      [[k, d["DGUID"], d["CDNAME"], d["CDTYPE"], d["PRUID"], la(d)] for k, d in sorted(C.items())])
def stage_fed2013():
    F = cget("load")["F13"]; S = simp([g for _, g in F], "FED2013", [d["PRUID"] for d, _ in F])
    write("ca_fed2013", sorted([(d["FEDUID"], {"feduid": d["FEDUID"], "dguid": d["DGUID"], "name": d["FEDNAME"], "name_en": d["FEDENAME"],
          "name_fr": d["FEDFNAME"], "landarea_km2": la(d), "pruid": d["PRUID"], "rep_order": "2013"}, s) for (d, g), s in zip(F, S)], key=lambda x: x[0]))
    W("ca_fed2013.csv", ["feduid", "dguid", "name", "name_en", "name_fr", "pruid", "landarea_km2"],
      sorted([[d["FEDUID"], d["DGUID"], d["FEDNAME"], d["FEDENAME"], d["FEDFNAME"], d["PRUID"], la(d)] for d, _ in F]))
def stage_fed2023():
    F = cget("load")["F23"]; S = simp([g for _, g in F], "FED2023", [str(d["ED_CF_NUM"])[:2] for d, _ in F])
    write("ca_fed2023", sorted([(str(d["ED_CF_NUM"]), {"fed_num": str(d["ED_CF_NUM"]), "name_en": d["ED_NAMEE"], "name_fr": d["CF_NOMF"],
          "pruid": str(d["ED_CF_NUM"])[:2], "land_km2_cbf_clip": round(g.area / 1e6, 4), "rep_order": "2023"}, s) for (d, g), s in zip(F, S)], key=lambda x: x[0]))
    W("ca_fed2023.csv", ["fed_num", "name_en", "name_fr", "pruid", "land_km2_cbf_clip"],
      sorted([[str(d["ED_CF_NUM"]), d["ED_NAMEE"], d["CF_NOMF"], str(d["ED_CF_NUM"])[:2], round(g.area / 1e6, 4)] for d, g in F]))
def stage_xref():
    L = cget("load"); CSD, F13, F23 = L["CSD"], L["F13"], L["F23"]
    def pairs(A, B):
        T = STRtree([g for _, g in B]); out = collections.defaultdict(list)
        for i, (_, g) in enumerate(A):
            for j in T.query(g, predicate="intersects"):
                x = g.intersection(B[j][1]).area
                if x > 0: out[i].append((x, j))
        return out
    P13 = pairs(CSD, F13); log("csd x fed2013"); P23 = pairs(CSD, F23); log("csd x fed2023"); PF = pairs(F13, F23); log("fed x fed")
    def top(lst, F, key, k=3):
        tot = sum(x for x, _ in lst) or 1
        return ";".join("%s:%.1f" % (key(F[j][0]), 100 * x / tot) for x, j in sorted(lst, reverse=True)[:k])
    k13 = lambda d: d["FEDUID"]; k23 = lambda d: str(d["ED_CF_NUM"])
    W("ca_csd_fed.csv", ["csduid", "fed2013_share_pct (FEDUID:% of CSD area, top 3)", "fed2023_share_pct (FED number:% of CSD area, top 3)"],
      sorted([[d["CSDUID"], top(P13[i], F13, k13), top(P23[i], F23, k23)] for i, (d, g) in enumerate(CSD)]))
    pr = []
    for i, lst in sorted(PF.items()):
        for x, j in sorted(lst, key=lambda t: t[1]):
            a13, a23 = F13[i][1].area, F23[j][1].area
            if x / a13 >= 0.001 or x / a23 >= 0.001:
                pr.append([F13[i][0]["FEDUID"], F13[i][0]["FEDENAME"], str(F23[j][0]["ED_CF_NUM"]), F23[j][0]["ED_NAMEE"],
                           round(100 * x / a13, 3), round(100 * x / a23, 3), int(F13[i][0]["FEDUID"] == str(F23[j][0]["ED_CF_NUM"]))])
    W("ca_fed2013_2023.csv", ["feduid_2013", "name_2013", "fed_num_2023", "name_2023", "pct_of_2013", "pct_of_2023", "same_number"], pr)
    R["fed_pairs"] = len(pr); R["fed_essentially_same_ge99"] = sum(1 for p in pr if p[4] >= 99 and p[5] >= 99); R["fed_same_number"] = sum(p[6] for p in pr)

def stage_csv():  # rewrite the five attribute CSVs only (no geometry work)
    L = cget("load"); P, C = L["PRa"], L["CDa"]; t = lambda k: "territory" if k in TERR else "province"
    W("ca_pr.csv", ["pruid", "dguid", "name_en", "name_fr", "abbr_en", "abbr_fr", "type", "parent", "landarea_km2"],
      [[k, d["DGUID"], d["PRENAME"], d["PRFNAME"], d["PREABBR"], d["PRFABBR"], t(k), "CA", la(d)] for k, d in sorted(P.items())])
    W("ca_cd.csv", ["cduid", "dguid", "name", "type", "pruid", "landarea_km2"],
      [[k, d["DGUID"], d["CDNAME"], d["CDTYPE"], d["PRUID"], la(d)] for k, d in sorted(C.items())])
    W("ca_csd.csv", ["csduid", "dguid", "name", "type", "pruid", "cduid", "landarea_km2"],
      sorted([[d["CSDUID"], d["DGUID"], d["CSDNAME"], d["CSDTYPE"], d["PRUID"], d["CSDUID"][:4], la(d)] for d, _ in L["CSD"]]))
    W("ca_fed2013.csv", ["feduid", "dguid", "name", "name_en", "name_fr", "pruid", "landarea_km2"],
      sorted([[d["FEDUID"], d["DGUID"], d["FEDNAME"], d["FEDENAME"], d["FEDFNAME"], d["PRUID"], la(d)] for d, _ in L["F13"]]))
    W("ca_fed2023.csv", ["fed_num", "name_en", "name_fr", "pruid", "land_km2_cbf_clip"],
      sorted([[str(d["ED_CF_NUM"]), d["ED_NAMEE"], d["CF_NOMF"], str(d["ED_CF_NUM"])[:2], round(g.area / 1e6, 4)] for d, g in L["F23"]]))
ST = {"csv": stage_csv, "load": stage_load, "csd": stage_csd, "pr": stage_pr, "cd": stage_cd, "fed2013": stage_fed2013, "fed2023": stage_fed2023, "xref": stage_xref}
for s in ([k for k in ST if k != "csv"] if STAGE == "all" else STAGE.split(",")):
    log("stage", s); ST[s](); save_report(); log("stage", s, "done")
