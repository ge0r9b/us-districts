#!/usr/bin/env python3
"""UK, Germany and France boundaries for v3 (data-v3/geo), modelled on tools/canada2021_geojson.py.
  gb  ONS Open Geography Portal BFC layers (tools/ons_fetch.py -> <raw>/ons/*.jsonl.gz, EPSG:27700), Open Government Licence v3.0
      PARNCP May 2026 (England parishes + non-civil-parished areas, Welsh communities), LAD May 2026, CTYUA Dec 2025, CAUTH Dec 2025.
  de  BKG VG250 Ebenen, Stand 01.01.2026 (<raw>/vg250/x/vg250_ebenen_0101/DE_VG250.gpkg, EPSG:25832), dl-de/by-2-0
      VG250_GEM / VWG / KRS / LAN, land parts only (GF = 4).
  fr  IGN ADMIN EXPRESS COG 4.0, édition 2026-01-01 (<raw>/adminexpress/x/*/…/*.gpkg; FXX Lambert-93 + 5 DROM in their local
      UTM CRS + the BLM/MAF/SPM overseas collectivités), Licence Ouverte 2.0.
Geometry policy (v3 lead): official full-resolution geometry with only light shared-edge simplification, because the PMTiles build
simplifies per zoom. The finest layer of each country is the base coverage: validated per group and repaired with
shapely.coverage_clean where invalid, then simplified as a whole with shapely.coverage_simplify at --tol metres in the source's
projected CRS. The coarser layers are unions of the simplified base units, so all layers of a country nest exactly and share
identical edges:
  gb  base = parishes/NCP areas (England, Wales) + LADs (Scotland, Northern Ireland); LAD = union of its base units (PARNCP26 has
      LAD26CD); CTYUA and CAUTH = unions of LADs (membership from full-resolution overlap with the ONS CTYUA / CAUTH layers).
  de  base = Gemeinden; VWG / KRS / LAN = unions by ARS prefix (9 / 5 / 2 digits).
  fr  base = communes (each territory simplified in its own CRS); départements and régions by the communes' INSEE codes; EPCI by
      the IGN EPCI layer's member list (codes_insee_des_communes_membres).
Each dissolved layer is checked against the publisher's own layer: per-unit area difference (full-resolution union vs published
polygon) and missing / extra codes, in report.json.
Areas: area_km2 = geodesic area (pyproj Geod, WGS84) of the full-resolution source polygon (land: clipped to the coast / GF = 4).
Output: WGS84 lon/lat, 5 decimals, valid geometry, one FeatureCollection per layer, gzip mtime 0 -> <out>/<cc>_<layer>.geojson.gz,
and the CSV index data-v3/geo/<cc>_<layer>.csv (code, name, type, parent code, area). Stages are resumable (pickle cache).
usage: foreign_geojson.py <repo> <raw_dir> <gb|de|fr> --out DIR [--tol M] --stage load|base|<layers>|all"""
import sys, os, json, gzip, csv, collections, time, pickle, glob, sqlite3
import numpy as np, shapely, pyproj, pyogrio, pyogrio.raw
from shapely.geometry import Polygon, MultiPolygon, LinearRing, mapping
from shapely.strtree import STRtree
a = sys.argv[1:]; opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
repo, raw, CC = [x for x in a if not x.startswith("--") and x not in (opt("--out"), opt("--tol"), opt("--stage"))][:3]
DEFTOL = {"gb": 20, "de": 10, "fr": 20}
OUT = opt("--out"); TOL = float(opt("--tol", DEFTOL[CC])); STAGE = opt("--stage", "all"); t0 = time.time()
CACHE = os.path.join(OUT, "cache"); os.makedirs(CACHE, exist_ok=True)
log = lambda *x: print("%5.0fs" % (time.time() - t0), *x, flush=True)
RP = os.path.join(OUT, "report.json"); R = json.load(open(RP)) if os.path.exists(RP) else {}
def save_report(): json.dump(R, open(RP, "w"), indent=1, sort_keys=True, ensure_ascii=False)
def cput(n, obj):
    p = os.path.join(CACHE, n + ".pkl"); pickle.dump(obj, open(p + ".tmp", "wb"), protocol=5); os.replace(p + ".tmp", p)
def cget(n): return pickle.load(open(os.path.join(CACHE, n + ".pkl"), "rb"))
def polys(g):  # polygonal part of a make_valid / intersection result
    if g.geom_type == "GeometryCollection":
        g = MultiPolygon([p for q in g.geoms for p in getattr(q, "geoms", [q]) if p.geom_type == "Polygon"])
    return g
def valid(g): return g if g.is_valid else polys(shapely.make_valid(g))
def esri(rings):
    """Esri polygon rings (outer rings clockwise, holes counter-clockwise) -> valid shapely (Multi)Polygon."""
    outs, holes = [], []
    for r in rings:
        if len(r) < 4: continue
        lr = LinearRing(r); (holes if lr.is_ccw else outs).append(lr)
    P = [[Polygon(o), []] for o in outs]
    T = STRtree([p[0] for p in P]) if len(P) > 50 else None
    for h in holes:
        hp = Polygon(h).representative_point()
        c = [P[j] for j in T.query(hp, predicate="within")] if T is not None else [p for p in P if p[0].contains(hp)]
        if c: min(c, key=lambda p: p[0].area)[1].append(h)
    g = MultiPolygon([Polygon(o.exterior, hs) for o, hs in P]) if len(P) > 1 else Polygon(P[0][0].exterior, P[0][1])
    return valid(g)
_TR = {}; GEOD = pyproj.Geod(ellps="WGS84")
def tr(crs):
    if crs not in _TR: _TR[crs] = pyproj.Transformer.from_crs(crs, 4326, always_xy=True)
    return _TR[crs]
def to_ll(g, crs): T = tr(crs); return shapely.transform(g, lambda xy: np.column_stack(T.transform(xy[:, 0], xy[:, 1])))
def geod_km2(g, crs): return round(abs(GEOD.geometry_area_perimeter(to_ll(g, crs))[0]) / 1e6, 4)
def simp(G, name, grp):
    """Coverage simplification of the base coverage G (grp[i] = validation group of G[i]); see canada2021_geojson.simp."""
    G = list(G); idx = collections.defaultdict(list); cleaned = {}
    for i, k in enumerate(grp): idx[k].append(i)
    for k, ii in sorted(idx.items()):
        sub = [G[i] for i in ii]
        if not shapely.coverage_is_valid(sub):
            bad = int(sum(not e.is_empty for e in shapely.coverage_invalid_edges(sub))); K = [polys(x) for x in shapely.coverage_clean(sub)]
            cleaned[k] = {"features_with_invalid_edges": bad, "area_moved_m2": round(sum(x.symmetric_difference(y).area for x, y in zip(sub, K)), 1),
                          "valid_after": bool(shapely.coverage_is_valid(K))}
            for i, g in zip(ii, K): G[i] = g
            log(name, "cleaned", k, cleaned[k])
    t = time.time(); S = list(shapely.coverage_simplify(G, TOL)); log(name, "simplified", round(time.time() - t))
    S = [valid(s) if not s.is_empty else g.simplify(TOL / 4) for s, g in zip(S, G)]
    sd = sum(s.symmetric_difference(g).area for s, g in zip(S, G)); ar = sum(g.area for g in G)
    H = sorted(s.hausdorff_distance(g) for s, g in zip(S, G) if shapely.get_num_coordinates(g) < 20000) or [0]
    outv = {k: bool(shapely.coverage_is_valid([S[i] for i in ii])) for k, ii in sorted(idx.items())}
    R[name] = {"tol_m": TOL, "groups": len(idx), "cleaned_before_simplify": cleaned, "output_valid_coverage_per_group": all(outv.values()),
               "output_invalid_groups": [k for k, v in outv.items() if not v], "all_valid_geometry": bool(all(s.is_valid for s in S)),
               "area_error_pct": round(100 * sd / ar, 4), "hausdorff_m_median": round(H[len(H) // 2], 1), "hausdorff_m_max": round(H[-1], 1),
               "vertices_in": int(sum(shapely.get_num_coordinates(G))), "vertices_out": int(sum(shapely.get_num_coordinates(S)))}
    log(name, R[name]); return S
def dissolve(name, members, base_simpl, base_full, published=None):
    """members: {code: [base index]}. Unions of the simplified base units (exact nesting) and, for the check, of the full-resolution
    ones, compared with the publisher's polygon of the same code (published: {code: full-res geometry}, same CRS)."""
    D, FB, err = {}, [], {}
    for k, ii in sorted(members.items()):
        v = [base_simpl[i] for i in ii]
        try: D[k] = shapely.coverage_union_all(v)
        except shapely.errors.GEOSException: D[k] = shapely.unary_union(v); FB.append(k)
        D[k] = valid(D[k])
        if published is not None and k in published:
            f = shapely.unary_union([base_full[i] for i in ii]); p = published[k]
            err[k] = round(100 * f.symmetric_difference(p).area / p.area, 4)
    R[name + "_union_fallback"] = FB
    if published is not None:
        w = sorted(err, key=err.get, reverse=True)
        R[name + "_vs_published"] = {"symdiff_pct_max": err[w[0]] if w else None, "worst": [(k, err[k]) for k in w[:5]],
            "units_over_0.1pct": sum(1 for v in err.values() if v > 0.1), "missing": sorted(set(published) - set(D)), "extra": sorted(set(D) - set(published))}
        log(name, R[name + "_vs_published"])
    return D
gd = lambda p: os.path.join(repo, "data-v3", "geo", p)
def W(name, head, rows):
    with open(gd(name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(head); w.writerows(rows)
    R.setdefault("csv", {})[name] = len(rows)
def gj(g, crs):
    g = valid(to_ll(g, crs)); g = polys(shapely.set_precision(g, 1e-5))
    m = mapping(g); rd = lambda c: [round(c[0], 5), round(c[1], 5)]
    if m["type"] == "Polygon": return {"type": "Polygon", "coordinates": [[rd(c) for c in r] for r in m["coordinates"]]}
    return {"type": "MultiPolygon", "coordinates": [[[rd(c) for c in r] for r in p] for p in m["coordinates"]]}
def write(name, feats):
    """feats: [(id, properties, geometry, crs)] -> <out>/<name>.geojson.gz (sorted by id, gzip mtime 0)."""
    feats = sorted(feats, key=lambda x: x[0]); p = os.path.join(OUT, name + ".geojson.gz")
    b = ('{"type":"FeatureCollection","features":[\n' + ",\n".join(
        json.dumps({"type": "Feature", "id": i, "properties": pp, "geometry": gj(g, crs)}, separators=(",", ":"), ensure_ascii=False)
        for i, pp, g, crs in feats) + "\n]}\n").encode()
    with open(p + ".tmp", "wb") as fo:
        with gzip.GzipFile(filename="", fileobj=fo, mode="wb", mtime=0, compresslevel=9) as o: o.write(b)
    os.replace(p + ".tmp", p)
    R.setdefault("files", {})[os.path.basename(p)] = {"bytes": os.path.getsize(p), "features": len(feats), "geojson_bytes": len(b)}
    log(name, R["files"][os.path.basename(p)])
def overlap_parent(child, parent):
    """child, parent: {code: geom}. For each child, the parent with the largest overlap and its share of the child's area."""
    pk = sorted(parent); T = STRtree([parent[k] for k in pk]); out = {}
    for c, g in child.items():
        best = max(((g.intersection(parent[pk[j]]).area, pk[j]) for j in T.query(g, predicate="intersects")), default=(0, None))
        out[c] = (best[1], round(best[0] / g.area, 6))
    return out

# ---------------------------------------------------------------- gb
GBC = 27700
def gb_read(n):
    for l in gzip.open(os.path.join(raw, "ons", n + ".jsonl.gz")):
        f = json.loads(l); yield f["attributes"], esri(f["geometry"]["rings"])
def gb_load():
    PAR = list(gb_read("PAR")); LAD = list(gb_read("LAD")); CTY = list(gb_read("CTYUA")); CA = list(gb_read("CAUTH")); log("read")
    LADg = {d["LAD26CD"]: g for d, g in LAD}
    base = [("PAR", d["PARNCP26CD"], d, g) for d, g in PAR] + [("LAD", d["LAD26CD"], d, g) for d, g in LAD if d["LAD26CD"][0] in "SN"]
    lad_of = [d["LAD26CD"] if t == "PAR" else c for t, c, d, g in base]
    CTYg = {d["CTYUA25CD"]: g for d, g in CTY}; CAg = {d["CAUTH25CD"]: g for d, g in CA}
    l2c = overlap_parent(LADg, CTYg); log("lad->ctyua"); l2a = {k: v for k, v in overlap_parent({k: g for k, g in LADg.items() if k[0] == "E"}, CAg).items() if v[1] >= 0.5}
    log("lad->cauth")
    area = [geod_km2(g, GBC) for _, _, _, g in base]; lad_area = {k: geod_km2(g, GBC) for k, g in LADg.items()}
    cty_area = {k: geod_km2(g, GBC) for k, g in CTYg.items()}; ca_area = {k: geod_km2(g, GBC) for k, g in CAg.items()}; log("areas")
    R["gb_load"] = {"PAR": len(PAR), "LAD": len(LAD), "CTYUA": len(CTY), "CAUTH": len(CA), "base_units": len(base),
                    "lad_to_ctyua_min_share": min(v[1] for v in l2c.values()), "lad_to_cauth_shares_below_0.99": sorted((k, v) for k, v in l2a.items() if v[1] < 0.99),
                    "par_by_prefix": dict(collections.Counter(c[:3] for t, c, d, g in base if t == "PAR")),
                    "lad_by_prefix": dict(collections.Counter(d["LAD26CD"][:3] for d, g in LAD)), "ctyua_by_prefix": dict(collections.Counter(d["CTYUA25CD"][:3] for d, g in CTY))}
    cput("gb_load", {"base": base, "lad_of": lad_of, "area": area, "LAD": [(d, g) for d, g in LAD], "CTY": [(d, g) for d, g in CTY], "CA": [(d, g) for d, g in CA],
                     "l2c": l2c, "l2a": l2a, "lad_area": lad_area, "cty_area": cty_area, "ca_area": ca_area})
def gb_base():
    L = cget("gb_load"); base = L["base"]; c2 = {k: v[0] for k, v in L["l2c"].items()}
    S = simp([g for *_, g in base], "gb_base", [c2[l] for l in L["lad_of"]]); cput("gb_simpl", S)
    TY = {"E04": "parish", "W04": "community", "E43": "non-civil parished area"}
    feats, rows = [], []
    for (t, c, d, g), s, l, ar in zip(base, S, L["lad_of"], L["area"]):
        if t != "PAR": continue
        nm, nw = d["PARNCP26NM"], (d.get("PARNCP26NW") or "").strip()
        feats.append((c, {"code": c, "name": nm, "name_cy": nw, "type": TY[c[:3]], "lad": l, "lad_name": d["LAD26NM"], "area_km2": ar}, s, GBC))
        rows.append([c, nm, nw, TY[c[:3]], l, ar])
    write("gb_par_2026", feats); W("gb_par.csv", ["code", "name", "name_cy", "type", "parent_lad", "area_km2"], sorted(rows))
GBLT = {"E06": "unitary authority", "E07": "non-metropolitan district", "E08": "metropolitan district", "E09": "London borough",
        "S12": "council area", "W06": "principal area", "N09": "local government district", "E10": "county"}
def gb_lads():
    L = cget("gb_load"); S = cget("gb_simpl"); base = L["base"]; m = collections.defaultdict(list)
    for i, l in enumerate(L["lad_of"]): m[l].append(i)
    return L, S, base, dissolve("gb_lad", m, S, [g for *_, g in base], {d["LAD26CD"]: g for d, g in L["LAD"]})
def gb_lad():
    L, S, base, D = gb_lads(); cput("gb_lad", D)
    feats, rows = [], []
    for d, g in L["LAD"]:
        c = d["LAD26CD"]; nw = (d.get("LAD26NMW") or "").strip(); p = L["l2c"][c][0]
        feats.append((c, {"code": c, "name": d["LAD26NM"], "name_cy": nw, "type": GBLT[c[:3]], "ctyua": p, "cauth": L["l2a"].get(c, (None,))[0] or "",
                          "area_km2": L["lad_area"][c]}, D[c], GBC))
        rows.append([c, d["LAD26NM"], nw, GBLT[c[:3]], p, L["l2a"].get(c, (None,))[0] or "", L["lad_area"][c]])
    write("gb_lad_2026", feats); W("gb_lad.csv", ["code", "name", "name_cy", "type", "parent_ctyua", "cauth", "area_km2"], sorted(rows))
def gb_up(name, A, key, nmk, nwk, l2x, areas, typ, fname, parent):
    L = cget("gb_load"); D0 = cget("gb_lad"); lk = sorted(D0); m = collections.defaultdict(list)
    for i, k in enumerate(lk):
        if k in l2x: m[l2x[k][0]].append(i)
    full = {d["LAD26CD"]: g for d, g in L["LAD"]}
    D = dissolve(name, m, [D0[k] for k in lk], [full[k] for k in lk], {d[key]: g for d, g in A})
    feats, rows = [], []
    for d, g in A:
        c = d[key]; nw = (d.get(nwk) or "").strip() if nwk else ""
        mem = ";".join(lk[i] for i in m[c])
        feats.append((c, {"code": c, "name": d[nmk], "name_cy": nw, "type": typ(c), "parent": parent, "lads": mem, "area_km2": areas[c]}, D[c], GBC))
        rows.append([c, d[nmk], nw, typ(c), parent, areas[c], len(m[c]), mem])
    write(fname, feats); W(name + ".csv", ["code", "name", "name_cy", "type", "parent", "area_km2", "n_lad", "lads"], sorted(rows))
def gb_ctyua():
    L = cget("gb_load")
    gb_up("gb_ctyua", L["CTY"], "CTYUA25CD", "CTYUA25NM", "CTYUA25NMW", L["l2c"], L["cty_area"], lambda c: GBLT[c[:3]], "gb_ctyua_2025", "")
def gb_cauth():
    L = cget("gb_load")
    gb_up("gb_cauth", L["CA"], "CAUTH25CD", "CAUTH25NM", None, L["l2a"], L["ca_area"], lambda c: "combined authority", "gb_cauth_2025", "E92000001")

# ---------------------------------------------------------------- de
DEC = 25832; DEF = lambda: os.path.join(raw, "vg250", "x", "vg250_ebenen_0101", "DE_VG250.gpkg")
def de_layer(l, geom=True):
    c = sqlite3.connect(DEF()); c.row_factory = sqlite3.Row
    A = [dict(r) for r in c.execute(f"select ARS, AGS, GEN, BEZ, NUTS, SDV_ARS, IBZ from {l} where GF = 4 order by ARS")]
    if not geom: return A
    meta, _, geo, fld = pyogrio.raw.read(DEF(), layer=l, where="GF = 4", columns=["ARS"])
    G = {k: valid(shapely.from_wkb(w)) for k, w in zip(fld[0], geo)}
    return A, G
def de_load():
    GA, GG = de_layer("vg250_gem"); out = {"GA": GA, "GG": GG}
    for l in ("vwg", "krs", "lan"):
        A, G = de_layer("vg250_" + l); out[l] = (A, G); log(l, len(A))
    out["area"] = {k: geod_km2(g, DEC) for k, g in GG.items()}
    for l in ("vwg", "krs", "lan"): out[l + "_area"] = {k: geod_km2(g, DEC) for k, g in out[l][1].items()}
    R["de_load"] = {"gem": len(GA), "gem_by_bez": dict(collections.Counter(d["BEZ"] for d in GA)), "vwg": len(out["vwg"][0]), "vwg_by_bez": dict(collections.Counter(d["BEZ"] for d in out["vwg"][0])),
                    "krs": len(out["krs"][0]), "krs_by_bez": dict(collections.Counter(d["BEZ"] for d in out["krs"][0])), "lan": len(out["lan"][0])}
    cput("de_load", out); log("loaded", R["de_load"])
def de_base():
    L = cget("de_load"); A = L["GA"]; ks = [d["ARS"] for d in A]
    S = simp([L["GG"][k] for k in ks], "de_gem", [k[:2] for k in ks]); cput("de_simpl", S)
    write("de_gem_2026", [(d["ARS"], {"ars": d["ARS"], "ags": d["AGS"], "name": d["GEN"], "type": d["BEZ"], "vwg": d["ARS"][:9], "krs": d["ARS"][:5], "lan": d["ARS"][:2],
                           "area_km2": L["area"][d["ARS"]]}, s, DEC) for d, s in zip(A, S)])
    W("de_gem.csv", ["code", "ags", "name", "type", "parent_vwg", "krs", "lan", "area_km2"],
      [[d["ARS"], d["AGS"], d["GEN"], d["BEZ"], d["ARS"][:9], d["ARS"][:5], d["ARS"][:2], L["area"][d["ARS"]]] for d in A])
def de_up(l, n, parent):
    L = cget("de_load"); S = cget("de_simpl"); ks = [d["ARS"] for d in L["GA"]]; m = collections.defaultdict(list)
    for i, k in enumerate(ks): m[k[:n]].append(i)
    A, G = L[l]; D = dissolve("de_" + l, m, S, [L["GG"][k] for k in ks], G); ar = L[l + "_area"]
    write("de_%s_2026" % l, [(d["ARS"], {"ars": d["ARS"], "ags": d["AGS"], "name": d["GEN"], "type": d["BEZ"], "parent": parent(d["ARS"]), "n_gem": len(m[d["ARS"]]),
                           "area_km2": ar[d["ARS"]]}, D[d["ARS"]], DEC) for d in A])
    W("de_%s.csv" % l, ["code", "ags", "name", "type", "parent", "n_gem", "area_km2"],
      [[d["ARS"], d["AGS"], d["GEN"], d["BEZ"], parent(d["ARS"]), len(m[d["ARS"]]), ar[d["ARS"]]] for d in A])
def de_vwg(): de_up("vwg", 9, lambda k: k[:5])
def de_krs(): de_up("krs", 5, lambda k: k[:2])
def de_lan(): de_up("lan", 2, lambda k: "DE")

# ---------------------------------------------------------------- fr
def fr_gpkgs():
    out = {}
    for f in sorted(glob.glob(os.path.join(raw, "adminexpress", "x", "*", "**", "*.gpkg"), recursive=True)):
        z = os.path.basename(f).split("_")[-1].split("-")[0]; out[z] = f  # FXX GLP MTQ GUF REU MYT BLM MAF SPM
    return out
def fr_read(f, l):
    if l not in [x[0] for x in pyogrio.list_layers(f)]: return [], None
    meta, _, geo, fld = pyogrio.raw.read(f, layer=l); crs = meta["crs"]
    cols = list(meta["fields"]); conv = lambda v: v.item() if hasattr(v, "item") else v
    return [({k: conv(fld[j][i]) for j, k in enumerate(cols)}, valid(shapely.from_wkb(geo[i]))) for i in range(len(geo))], crs
def fr_load():
    out = {"com": [], "dep": [], "reg": [], "epci": [], "om": []}; ZC = {}
    for z, f in fr_gpkgs().items():
        for l, k in (("commune", "com"), ("departement", "dep"), ("region", "reg"), ("epci", "epci")):
            rows, crs = fr_read(f, l)
            if z in ("BLM", "MAF", "SPM") and k == "com": k = "om_com"
            for d, g in rows: out.setdefault(k, []).append((z, crs, d, g))
            if crs: ZC[z] = crs
        if z in ("BLM", "MAF", "SPM"):
            rows, crs = fr_read(f, "collectivite_territoriale"); out["om"] += [(z, crs, d, g) for d, g in rows]
        log(z, {k: len(v) for k, v in out.items()})
    out["ZC"] = ZC
    for k in ("com", "dep", "reg", "epci", "om"): out[k + "_area"] = [geod_km2(g, crs) for z, crs, d, g in out[k]]
    R["fr_load"] = {k: len(out[k]) for k in ("com", "dep", "reg", "epci", "om")} | {"om_com": len(out.get("om_com", [])),
        "com_by_zone": dict(collections.Counter(z for z, *_ in out["com"])), "epci_by_nature": dict(collections.Counter(d["nature"] for z, c, d, g in out["epci"])),
        "com_by_statut": dict(collections.Counter(d["statut"] for z, c, d, g in out["com"])), "crs": {z: str(c) for z, c in ZC.items()}}
    cput("fr_load", out); log("loaded", R["fr_load"])
def fr_base():
    L = cget("fr_load"); C = L["com"]; S = [None] * len(C); byz = collections.defaultdict(list)
    for i, (z, crs, d, g) in enumerate(C): byz[z].append(i)
    for z, ii in sorted(byz.items()):  # each territory in its own projected CRS
        Sz = simp([C[i][3] for i in ii], "fr_com_" + z, [C[i][2]["code_insee_du_departement"] for i in ii])
        for i, s in zip(ii, Sz): S[i] = s
    cput("fr_simpl", S)
    feats, rows = [], []
    for (z, crs, d, g), s, ar in zip(C, S, L["com_area"]):
        p = {"code": d["code_insee"], "siren": d["code_siren"], "name": d["nom_officiel"], "type": d["statut"], "dep": d["code_insee_du_departement"],
             "reg": d["code_insee_de_la_region"], "epci": d["codes_siren_des_epci"] or "", "zone": z, "area_km2": ar}
        feats.append((d["code_insee"], p, s, crs))
        rows.append([d["code_insee"], d["code_siren"], d["nom_officiel"], d["statut"], d["code_insee_du_departement"], d["code_insee_de_la_region"], d["codes_siren_des_epci"] or "", z, ar])
    write("fr_com_2026", feats); W("fr_com.csv", ["code", "siren", "name", "type", "parent_dep", "reg", "epci_siren", "zone", "area_km2"], sorted(rows))
def fr_up(k, keyf, members, name, extra):
    L = cget("fr_load"); C = L["com"]; S = cget("fr_simpl"); A = L[k]; m = collections.defaultdict(list); idx = {d["code_insee"]: i for i, (z, c, d, g) in enumerate(C)}
    for key, codes in members(C, A, idx): m[key] += codes
    crsk = {keyf(d): crs for z, crs, d, g in A}
    # unions are formed per CRS group: every unit here lies in one territory
    D = dissolve(name, m, S, [g for *_, g in C], {keyf(d): g for z, crs, d, g in A})
    feats, rows = [], []
    for (z, crs, d, g), ar in zip(A, L[k + "_area"]):
        c = keyf(d); e = extra(d)
        feats.append((c, {"code": c, **e, "n_com": len(m[c]), "zone": z, "area_km2": ar}, D[c], crs))
        rows.append([c] + list(e.values()) + [len(m[c]), z, ar])
    write(name + "_2026", feats); W(name + ".csv", ["code"] + list(extra(A[0][2]).keys()) + ["n_com", "zone", "area_km2"], sorted(rows))
def fr_dep():
    fr_up("dep", lambda d: d["code_insee"], lambda C, A, idx: [(d["code_insee_du_departement"], [i]) for i, (z, c, d, g) in enumerate(C)], "fr_dep",
          lambda d: {"siren": d["code_siren"], "name": d["nom_officiel"], "type": "département", "parent_reg": d["code_insee_de_la_region"]})
def fr_reg():
    fr_up("reg", lambda d: d["code_insee"], lambda C, A, idx: [(d["code_insee_de_la_region"], [i]) for i, (z, c, d, g) in enumerate(C)], "fr_reg",
          lambda d: {"siren": d["code_siren"], "name": d["nom_officiel"], "type": "région", "parent": "FR"})
def fr_epci():
    def mem(C, A, idx):
        miss = []
        for z, c, d, g in A:
            cc = [x for x in (d["codes_insee_des_communes_membres"] or "").replace(",", "/").replace(";", "/").split("/") if x.strip()]
            miss += [x for x in cc if x.strip() not in idx]; yield d["code_siren"], [idx[x.strip()] for x in cc if x.strip() in idx]
        R["fr_epci_member_codes_not_found"] = miss
    fr_up("epci", lambda d: d["code_siren"], mem, "fr_epci",
          lambda d: {"name": d["nom_officiel"], "type": d["nature"], "deps": d["codes_insee_des_departements_membres"] or ""})
def fr_om():  # overseas collectivités BLM, MAF, SPM: the collectivité polygon, simplified on its own (not part of the 34,875)
    L = cget("fr_load"); A = L["om"]; feats, rows = [], []
    for (z, crs, d, g), ar in zip(A, L["om_area"]):
        s = valid(shapely.coverage_simplify([g], TOL)[0]); c = d["code_insee"]
        feats.append((c, {"code": c, "siren": d["code_siren"], "name": d["nom_officiel"], "type": "collectivité d'outre-mer", "zone": z, "area_km2": ar}, s, crs))
        rows.append([c, d["code_siren"], d["nom_officiel"], "collectivité d'outre-mer", "FR", z, ar])
    write("fr_com_om_2026", feats); W("fr_com_om.csv", ["code", "siren", "name", "type", "parent", "zone", "area_km2"], sorted(rows))

ST = {"gb": {"load": gb_load, "base": gb_base, "lad": gb_lad, "ctyua": gb_ctyua, "cauth": gb_cauth},
      "de": {"load": de_load, "base": de_base, "vwg": de_vwg, "krs": de_krs, "lan": de_lan},
      "fr": {"load": fr_load, "base": fr_base, "dep": fr_dep, "reg": fr_reg, "epci": fr_epci, "om": fr_om}}[CC]
for s in (list(ST) if STAGE == "all" else STAGE.split(",")):
    log("stage", CC, s); ST[s](); save_report(); log("stage", CC, s, "done")
