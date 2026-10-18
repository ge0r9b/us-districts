#!/usr/bin/env python3
"""Step 2 of the town pass: self-contained v2 town and place files per state, from Census TIGER 2024 (public domain).
  v2/data/parts/<State>.js   __parts("State",[[county, name, enc], ...])   every row with its own geometry
  v2/data/places/<State>.js  __places("State",[["State", name, enc], ...]) the v1 'places' rows (same row style as
                             data/<State>.js places, i.e. GEOM.places items), lazily loaded
enc = polygons of rings of x10000 integer deltas (decodePolys format), as before.
Rows:
  parts  = the v1 town rows of data/<State>.js, then the existing parts rows, then the TIGER gap fills (incorporated places
           with >= 2 % or >= 0.5 km2 of their land in the county, county subdivisions with FUNCSTAT A/B/C/G), one row per
           exact (county, name); a place row is the place clipped to the county. Names are the existing row names / TIGER
           NAMELSAD. Two different TIGER features with one (county, name) (Ohio, Union County, Washington township) keep the
           name on the first and get " (<GEOID>)" on the second, so keys stay unique.
  places = the v1 places rows, then TIGER incorporated places missing from them. A name used twice in a state gets
           "<name> (<county>)" (county holding most of the place, " County" dropped), like the renamed school rows.
Rows that cannot be resolved to TIGER 2024 keep their existing geometry unchanged (reported).
Geometry: shared-edge simplification. The boundaries of every TIGER feature used and of the state's counties are noded
(unary_union) and polygonized at full resolution into faces, an exact coverage; each face goes to every feature (and the
county) containing its representative point. The face coverage is then simplified as a whole with GEOS coverage
simplification (shapely.coverage_simplify, Visvalingam-Whyatt with shared edges kept identical and no gaps or overlaps
created); the tolerance is in degrees (about the square root of the removed triangle areas). A row is the union of its
simplified faces, so neighbours share identical vertices. The tolerance is the smallest of --tols that keeps each file <= --max bytes (chosen
per file). Tiling check: overlap and interior gaps among county-subdivision rows, place rows outside their county,
Hausdorff distance to TIGER.
usage: build_town_files.py <repo> <State> <tiger_dir> <tl_2024_us_county.zip> --report OUT.json [--tols 0.0002,...] [--max 300000] [--dry]
"""
import sys, os, json, re, collections, statistics, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shapely.ops import unary_union, linemerge, polygonize
from shapely.strtree import STRtree
from shapely.prepared import prep
from shapely.geometry import Polygon
import coverage_audit as A
from town_gaps import recs, FIPS
from town_area_gaps import dec
from resimplify_towns import enc_geom

TOLS = [0.0002, 0.0003, 0.0004, 0.0005, 0.0006, 0.0008, 0.001, 0.0012, 0.0015, 0.002, 0.0025, 0.003, 0.004]
K2 = 111.0 * 111.0 * 0.75

def jsrows(path):
    s = open(path).read(); i = s.index("[", s.index("(")); j = s.rindex("]") + 1
    return s, i, j, json.loads(s[i:j])

def nbytes(rows): return len(json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode())

def main():
    a = sys.argv[1:]; opt = lambda k: a[a.index(k) + 1] if k in a else None; dry = "--dry" in a
    repo, st, td, cz = [x for x in a if not x.startswith("--") and x not in (opt("--report"), opt("--tols"), opt("--max"), opt("--force-tol"))][:4]
    tols = [float(x) for x in opt("--tols").split(",")] if opt("--tols") else TOLS; MAX = int(opt("--max") or 300000)
    t0 = time.time(); sf = {v: k for k, v in FIPS.items()}[st]; fn = st.replace(" ", "-") + ".js"
    geo = A.jsargs(os.path.join(repo, "data", fn), r"__geo\(")[1]
    pp = os.path.join(repo, "v2", "data", "parts", fn)
    ps, pi, pj, parts = jsrows(pp) if os.path.exists(pp) else ('__parts(%s,[]);\n' % json.dumps(st), 0, 0, [])
    if not os.path.exists(pp): pi = ps.index("["); pj = pi + 2
    CTY = {d["NAMELSAD"]: (d["COUNTYFP"], g) for d, g in recs(cz, lambda d: d["STATEFP"] == sf)}
    CS = [(d, g) for d, g in recs(os.path.join(td, "tl_2024_%s_cousub.zip" % sf)) if not d["GEOID"].endswith("00000")]
    PL = list(recs(os.path.join(td, "tl_2024_%s_place.zip" % sf)))
    cs_by = collections.defaultdict(list); pl_by = collections.defaultdict(list)
    for k, (d, g) in enumerate(CS): cs_by[(d["COUNTYFP"], d["NAMELSAD"])].append(k)
    for k, (d, g) in enumerate(PL): pl_by[d["NAMELSAD"]].append(k)
    PLT = STRtree([g for _, g in PL])
    def best(cands, geoms, ref):
        if len(cands) == 1 or ref is None: return cands[0]
        return max(cands, key=lambda k: geoms[k].intersection(ref).area)
    def resolve(cn, name, ref):
        if cn not in CTY: return None
        cf, cg = CTY[cn]; nm = re.sub(r" \((?:%s|\d{7,10})\)$" % re.escape(cn[:-7] if cn.endswith(" County") else cn), "", name)
        if (cf, nm) in cs_by: k = best(cs_by[(cf, nm)], [g for _, g in CS], ref); return ("cs", k)
        c = [k for k in pl_by.get(nm, []) if PL[k][1].intersects(cg) and PL[k][1].intersection(cg).area > 0]
        if c: return ("pl", best(c, [g for _, g in PL], ref if ref is not None else cg))
        return None
    # ---- parts rows
    rows = []; keys = {}; rep = collections.Counter(); kept = []; dropped = []
    def add(cn, name, ref, enc_old, src):
        r = resolve(cn, name, ref)
        key = (cn, name)
        if key in keys:
            if r is None or keys[key] == r: rep["dup_identical_dropped"] += 1; return
            gid = (CS if r[0] == "cs" else PL)[r[1]][0]["GEOID"]; name = "%s (%s)" % (name, gid); key = (cn, name); rep["dup_renamed_geoid"] += 1
        if r is None and src == "parts-borrowed":  # a no-geometry parts row whose place does not touch this county in TIGER 2024
            rep["dropped_place_not_in_county"] += 1; dropped.append((cn, name)); return
        keys[key] = r; rows.append({"county": cn, "name": name, "res": r, "old": enc_old, "src": src})
        if r is None: kept.append((cn, name, src))
    for t in geo.get("towns") or []: add(t[1], t[2], dec(t[-1]), t[-1], "v1-town")
    PV = collections.defaultdict(list)
    for p in geo.get("places") or []: PV[p[1]].append(p[-1])
    for p in parts:
        enc = p[2] if p[2] else (PV[p[1]][0] if p[1] in PV else None)
        add(p[0], p[1], dec(enc) if enc else None, enc, "parts" if p[2] else "parts-borrowed")
    n_before = len(rows)
    have = {(r["county"], r["name"]) for r in rows}; haveres = {(r["county"], r["res"]) for r in rows if r["res"]}
    fills = []
    for cn, (cf, cg) in sorted(CTY.items()):
        for k in PLT.query(cg):
            d, g = PL[k]
            if not d["CLASSFP"].startswith("C"): continue
            x = g.intersection(cg).area
            if x <= 0 or not (x / g.area >= 0.02 or x * K2 >= 0.5): continue
            if (cn, d["NAMELSAD"]) in have or (cn, ("pl", k)) in haveres: continue
            fills.append((cn, d["NAMELSAD"], ("pl", k)))
    for k, (d, g) in enumerate(CS):
        if d["FUNCSTAT"] not in ("A", "B", "C", "G"): continue
        cn = next((n for n, (cf, _) in CTY.items() if cf == d["COUNTYFP"]), None)
        if cn is None or (cn, d["NAMELSAD"]) in have or (cn, ("cs", k)) in haveres: continue
        fills.append((cn, d["NAMELSAD"], ("cs", k)))
    for cn, nm, r in sorted(set(fills)):
        if (cn, nm) in keys: nm = "%s (%s)" % (nm, (CS if r[0] == "cs" else PL)[r[1]][0]["GEOID"])
        keys[(cn, nm)] = r; rows.append({"county": cn, "name": nm, "res": r, "old": None, "src": "tiger-fill"}); have.add((cn, nm))
    # ---- places rows
    v1p = geo.get("places") or []; cnt = collections.Counter(p[1] for p in v1p); prow = []; used = set(); pkept = []
    def cty_of(g): return max(CTY.items(), key=lambda kv: kv[1][1].intersection(g).area if kv[1][1].intersects(g) else 0)[0]
    for p in v1p:
        ref = dec(p[-1]); c = pl_by.get(p[1], [])
        k = best(c, [g for _, g in PL], ref) if c else None
        nm = p[1]
        if cnt[nm] > 1:
            cn = cty_of(PL[k][1] if k is not None else ref); nm = "%s (%s)" % (nm, cn[:-7] if cn.endswith(" County") else cn)
        if k is not None: used.add(k)
        else: pkept.append(nm)
        prow.append({"name": nm, "res": k, "old": p[-1], "src": "v1-place", "v1name": p[1]})
    nmset = collections.Counter(r["name"] for r in prow)
    for k, (d, g) in enumerate(PL):
        if d["CLASSFP"].startswith("C") and k not in used:
            nm = d["NAMELSAD"]
            if nmset[nm] or cnt[nm]: cn = cty_of(g); nm = "%s (%s)" % (nm, cn[:-7] if cn.endswith(" County") else cn)
            prow.append({"name": nm, "res": k, "old": None, "src": "tiger-fill"}); nmset[nm] += 1
    assert max(collections.Counter(r["name"] for r in prow).values()) == 1, "duplicate place names"
    assert max(collections.Counter((r["county"], r["name"]) for r in rows).values()) == 1, "duplicate parts keys"
    # ---- arrangement
    F = {}  # feature id -> geometry
    for r in rows:
        if r["res"]: F[r["res"]] = (CS if r["res"][0] == "cs" else PL)[r["res"][1]][1]
    for r in prow:
        if r["res"] is not None: F[("pl", r["res"])] = PL[r["res"]][1]
    for cn, (cf, cg) in CTY.items(): F[("cty", cn)] = cg
    fids = list(F); FG = [F[f] for f in fids]; FP = [prep(g) for g in FG]; FT = STRtree(FG)
    t1 = time.time()
    arcs = linemerge(unary_union([g.boundary for g in FG])); arcs = list(getattr(arcs, "geoms", [arcs]))
    print(st, "rows", len(rows), "places", len(prow), "features", len(fids), "arcs", len(arcs), "noding %.0fs" % (time.time() - t1), flush=True)
    res_by_tol = {}; KEEP = {float(opt("--force-tol"))} if opt("--force-tol") else set()
    faces0 = [f for f in polygonize(arcs) if f.area > 0]
    own0 = collections.defaultdict(list)  # feature -> [(county, face index)]
    for n, f in enumerate(faces0):
        p = f.representative_point()
        hit = [k for k in FT.query(p) if FP[k].contains(p)]
        ct = [fids[k] for k in hit if fids[k][0] == "cty"]
        for k in hit:
            if fids[k][0] != "cty": own0[fids[k]].append((ct[0][1] if ct else None, n))
    print(st, "faces", len(faces0), "assigned %.0fs" % (time.time() - t1), flush=True)
    import shapely
    def build(tol):
        SF = list(shapely.coverage_simplify(faces0, tol)) if tol > 0 else faces0
        own = {k: [(c, SF[n]) for c, n in v if SF[n] is not None and not SF[n].is_empty] for k, v in own0.items()}
        out_parts = []; out_pl = []; geoms_parts = []; geoms_pl = []; empty = []
        for r in rows:
            if r["res"] is None: enc = r["old"]; g = dec(enc) if enc else None
            else:
                fs = [f for c, f in own.get(r["res"], []) if r["res"][0] == "cs" or c == r["county"]]
                g = unary_union(fs) if fs else None; enc = enc_geom(g) if g is not None and not g.is_empty else []
                if not enc:
                    tg = F[r["res"]].intersection(CTY[r["county"]][1]) if r["res"][0] == "pl" else F[r["res"]]
                    g = tg.simplify(tol, preserve_topology=True); enc = enc_geom(g); empty.append(r["name"])
            out_parts.append([r["county"], r["name"], enc]); geoms_parts.append(g)
        for r in prow:
            if r["res"] is None: enc = r["old"]; g = dec(enc)
            else:
                fs = [f for c, f in own.get(("pl", r["res"]), [])]
                g = unary_union(fs) if fs else PL[r["res"]][1].simplify(tol, preserve_topology=True); enc = enc_geom(g)
            out_pl.append([st, r["name"], enc]); geoms_pl.append(g)
        return out_parts, out_pl, geoms_parts, geoms_pl, empty
    choice = {}; table = []; import gzip
    for tol in tols:
        t2 = time.time(); R = build(tol); bp, bl = nbytes(R[0]), nbytes(R[1]); res_by_tol[tol] = R
        gp = len(gzip.compress(json.dumps(R[0], separators=(",", ":"), ensure_ascii=False).encode(), 9)); gl = len(gzip.compress(json.dumps(R[1], separators=(",", ":"), ensure_ascii=False).encode(), 9))
        table.append([tol, bp, gp, bl, gl])
        print(" tol", tol, "parts", bp, "gz", gp, "places", bl, "gz", gl, "%.0fs" % (time.time() - t2), flush=True)
        if "parts" not in choice and bp <= MAX: choice["parts"] = tol
        if "places" not in choice and bl <= MAX: choice["places"] = tol
        if len(choice) == 2 and "--table" not in a: break
        for t in list(res_by_tol):
            if t not in choice.values() and t != tol and t not in KEEP: del res_by_tol[t]
    tp, tl = (float(opt("--force-tol")),) * 2 if opt("--force-tol") else (choice.get("parts", tols[-1]), choice.get("places", tols[-1]))
    if opt("--force-tol"): tl = choice.get("places", tl) if choice.get("places", 9) < tp else tp
    P, _, GP, _, emp = res_by_tol[tp]; _, Lr, _, GL, _ = res_by_tol[tl]
    # ---- tiling metrics (parts, county-subdivision rows)
    csi = [n for n, r in enumerate(rows) if r["res"] and r["res"][0] == "cs" and GP[n] is not None]
    L = [GP[n] for n in csi]; T = STRtree(L); ov = 0.0
    for i, g in enumerate(L):
        for j in T.query(g):
            if j > i:
                try: ov += g.intersection(L[j]).area
                except Exception: pass
    m = {}
    if csi:
        ref = unary_union([F[rows[n]["res"]] for n in csi]); inner = ref.buffer(-0.003)
        gap = ref.difference(unary_union(L)).intersection(inner).area
        m.update({"cousub_rows": len(csi), "cousub_overlap_pct": round(100 * ov / ref.area, 4), "cousub_interior_gap_pct": round(100 * gap / ref.area, 4)})
    pli = [n for n, r in enumerate(rows) if r["res"] and r["res"][0] == "pl" and GP[n] is not None]
    if pli:
        out = sum(GP[n].difference(CTY[rows[n]["county"]][1]).area for n in pli); tot = sum(GP[n].area for n in pli)
        m.update({"place_part_rows": len(pli), "place_parts_outside_county_pct": round(100 * out / max(tot, 1e-12), 4)})
    hd = []
    for n, r in enumerate(rows):
        if r["res"] and GP[n] is not None and not GP[n].is_empty:
            ref = F[r["res"]] if r["res"][0] == "cs" else F[r["res"]].intersection(CTY[r["county"]][1])
            hd.append((GP[n].hausdorff_distance(ref), r["name"], r["county"]))
    ae = [0.0, 0.0]
    for n, r in enumerate(rows):
        if r["res"] and GP[n] is not None and not GP[n].is_empty:
            ref = F[r["res"]] if r["res"][0] == "cs" else F[r["res"]].intersection(CTY[r["county"]][1])
            try: ae[0] += GP[n].symmetric_difference(ref).area; ae[1] += ref.area
            except Exception: pass
    if ae[1]: m["parts_area_error_pct"] = round(100 * ae[0] / ae[1], 3)
    hl = [(GL[n].hausdorff_distance(PL[r["res"]][1]), r["name"]) for n, r in enumerate(prow) if r["res"] is not None and GL[n] is not None and not GL[n].is_empty]
    if hd: m.update({"parts_hausdorff_deg_median": round(statistics.median(x[0] for x in hd), 5), "parts_hausdorff_deg_max": round(max(hd)[0], 5), "parts_worst": max(hd)[1:]})
    if hl: m.update({"places_hausdorff_deg_median": round(statistics.median(x[0] for x in hl), 5), "places_hausdorff_deg_max": round(max(hl)[0], 5), "places_worst": max(hl)[1]})
    # ---- counts against TIGER
    exp_pl = sum(1 for d, g in PL if d["CLASSFP"].startswith("C")); exp_cs = sum(1 for d, g in CS if d["FUNCSTAT"] in ("A", "B", "C", "G"))
    got_cs = len({r["res"] for r in rows if r["res"] and r["res"][0] == "cs" and CS[r["res"][1]][0]["FUNCSTAT"] in ("A", "B", "C", "G")})
    got_pl_parts = len({r["res"] for r in rows if r["res"] and r["res"][0] == "pl" and PL[r["res"][1]][0]["CLASSFP"].startswith("C")})
    got_pl = len({r["res"] for r in prow if r["res"] is not None and PL[r["res"]][0]["CLASSFP"].startswith("C")})
    old_parts_bytes = len(ps.encode()); pl_path = os.path.join(repo, "v2", "data", "places", fn)
    out_p = ps[:pi] + json.dumps(P, separators=(",", ":"), ensure_ascii=False) + ps[pj:]
    out_l = "__places(%s,%s);\n" % (json.dumps(st), json.dumps(Lr, separators=(",", ":"), ensure_ascii=False))
    v1_tp = len(json.dumps(geo.get("towns") or [], separators=(",", ":"))); v1_pl = len(json.dumps(v1p, separators=(",", ":")))
    rpt = {"state": st, "size_table_tol_parts_gz_places_gz": table, "dropped_parts_rows_place_not_in_county": dropped, "tol_parts": tp, "tol_places": tl, "fits": {"parts": "parts" in choice, "places": "places" in choice},
           "parts_bytes_before": old_parts_bytes, "parts_bytes_after": len(out_p.encode()), "places_bytes_after": len(out_l.encode()),
           "v1_towns_json_bytes": v1_tp, "v1_places_json_bytes": v1_pl,
           "parts_rows_before": len(parts), "v1_town_rows": len(geo.get("towns") or []), "parts_rows_after": len(P), "parts_rows_from_v1_and_parts": n_before,
           "tiger_fills": sum(1 for r in rows if r["src"] == "tiger-fill"), "fills": [(r["county"], r["name"]) for r in rows if r["src"] == "tiger-fill"][:200],
           "dup_identical_dropped": rep["dup_identical_dropped"], "dup_renamed_geoid": rep["dup_renamed_geoid"],
           "parts_rows_kept_old_geometry": kept, "places_rows": len(Lr), "places_v1_rows": len(v1p), "places_fills": sum(1 for r in prow if r["src"] == "tiger-fill"),
           "places_kept_old_geometry": pkept, "places_renamed": [r["name"] for r in prow if r.get("v1name") and r["name"] != r["v1name"]] + [r["name"] for r in prow if r["src"] == "tiger-fill" and r["name"].endswith(")")],
           "tiger_incorporated_places": exp_pl, "places_file_incorporated": got_pl, "parts_incorporated_places": got_pl_parts,
           "tiger_gov_cousubs": exp_cs, "parts_gov_cousubs": got_cs, "rows_geometry_fallback": emp, "seconds": round(time.time() - t0),
           "rows": [{"county": r["county"], "name": r["name"], "geoid": ((CS if r["res"][0] == "cs" else PL)[r["res"][1]][0]["GEOID"] if r["res"] else ""), "kind": (r["res"][0] if r["res"] else ""), "src": r["src"]} for r in rows],
           "place_rows": [{"name": r["name"], "geoid": PL[r["res"]][0]["GEOID"] if r["res"] is not None else "", "src": r["src"]} for r in prow]}
    rpt.update(m)
    json.dump(rpt, open(opt("--report"), "w"), ensure_ascii=False, indent=0)
    print(json.dumps({k: v for k, v in rpt.items() if k not in ("rows", "place_rows", "fills")}, ensure_ascii=False)[:2500])
    if not dry:
        open(pp, "w").write(out_p); os.makedirs(os.path.dirname(pl_path), exist_ok=True); open(pl_path, "w").write(out_l)

if __name__ == "__main__":
    main()
