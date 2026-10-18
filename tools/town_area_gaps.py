#!/usr/bin/env python3
"""Area check of the v2 town layer against TIGER 2024 (companion of town_gaps.py): per county, the land of the expected
town entities (incorporated places + governmental county subdivisions, as in town_gaps.py), clipped to the county, that no
shown app town polygon covers; and the shown polygons' area outside every TIGER place/county subdivision of the county.
Shown polygons = townsIn() rows (v1 towns, parts rows with geometry, parts rows borrowing the v1 place polygon).
usage: town_area_gaps.py <repo> <tiger_dir> <tl_2024_us_county.zip> --json OUT [--states A,B]
"""
import sys, os, json, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely.geometry import Polygon, MultiPolygon
import coverage_audit as A
from town_gaps import recs, normT, FIPS

def dec(enc, S=10000):
    ps = []
    for poly in enc or []:
        rings = []
        for fl in poly:
            x = y = 0; pts = []
            for k in range(0, len(fl) - 1, 2): x += fl[k]; y += fl[k + 1]; pts.append((x / S, y / S))
            if len(pts) >= 3: rings.append(pts)
        if rings:
            try: ps.append(Polygon(rings[0], rings[1:]).buffer(0))
            except Exception: pass
    return unary_union(ps) if ps else None

def main():
    a = sys.argv[1:]; opt = lambda k: a[a.index(k) + 1] if k in a else None
    repo, td, cz = [x for x in a if not x.startswith("--") and x not in (opt("--json"), opt("--states"))][:3]
    st2f = {v: k for k, v in FIPS.items()}
    states = opt("--states").split(",") if opt("--states") else sorted(st2f)
    C = collections.defaultdict(dict)
    for d, g in recs(cz): C[d["STATEFP"]][d["NAMELSAD"]] = g
    out = {}
    for st in states:
        sf = st2f[st]; fn = st.replace(" ", "-") + ".js"
        if not os.path.exists(os.path.join(repo, "data", fn)): continue
        geo = A.jsargs(os.path.join(repo, "data", fn), r"__geo\(")[1]
        pp = os.path.join(repo, "v2", "data", "parts", fn); parts = []
        if os.path.exists(pp): s = open(pp).read(); parts = json.loads(s[s.index("[", s.index("(")):s.rindex("]") + 1])
        PV = {p[1]: p[-1] for p in geo.get("places") or []}
        PL = list(recs(os.path.join(td, "tl_2024_%s_place.zip" % sf)))
        CS = [x for x in recs(os.path.join(td, "tl_2024_%s_cousub.zip" % sf)) if not x[0]["GEOID"].endswith("00000")]
        ALLG = [g for _, g in PL] + [g for _, g in CS]
        EXPG = [g for d, g in PL if d["CLASSFP"].startswith("C")] + [g for d, g in CS if d["FUNCSTAT"] in ("A", "B", "C", "G")]
        Tall = STRtree(ALLG); Texp = STRtree(EXPG)
        tot = collections.Counter(); per = {}
        for cn, cg in C[sf].items():
            shown = []; have = set()
            for t in geo.get("towns") or []:
                if t[1] == cn: shown.append(t[-1]); have.add(normT(t[2]))
            for p in parts:
                if p[0] != cn or normT(p[1]) in have: continue
                e = p[2] if p[2] else PV.get(p[1])
                if e is None: continue
                shown.append(e); have.add(normT(p[1]))
            S = unary_union([g for g in (dec(e) for e in shown) if g is not None]) if shown else None
            E = [EXPG[i].intersection(cg) for i in Texp.query(cg)]
            E = unary_union([g for g in E if not g.is_empty and g.area > 0]) if E else None
            if E is None or E.is_empty: continue
            ea = E.area; miss = E.difference(S).area if S is not None else ea
            extra = 0.0
            if S is not None:
                Al = unary_union([ALLG[i] for i in Tall.query(cg)] or [Polygon()])
                extra = S.intersection(cg).difference(Al).area
            tot["exp_area"] += ea; tot["miss_area"] += miss; tot["extra_area"] += extra
            per[cn] = [round(ea, 6), round(miss, 6), round(extra, 6)]
        k2 = 111.0 * 111.0 * 0.75
        r = {"exp_km2": round(tot["exp_area"] * k2), "miss_km2": round(tot["miss_area"] * k2), "miss_share": round(tot["miss_area"] / max(tot["exp_area"], 1e-12), 4),
             "shown_outside_tiger_km2": round(tot["extra_area"] * k2), "counties": per}
        out[st] = r; print(st, {k: v for k, v in r.items() if k != "counties"}, flush=True)
    json.dump(out, open(opt("--json"), "w"))

if __name__ == "__main__":
    main()
