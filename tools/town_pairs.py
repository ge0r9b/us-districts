#!/usr/bin/env python3
"""v2/data/town_pairs.js for the suffix-aware duplicate check of townsIn() (orchestrator option A).
For every county, every two town-layer rows the app sees (v1 data/<State>.js towns + v2/data/parts/<State>.js rows, exact
names) whose normT() names are equal but whose names differ (e.g. "Ames city" / "Ames township") are classified with TIGER
2024 shapes clipped to the county: "same" when each covers >= 90 % of the other (mutual overlap; the place and the county
subdivision are the same ground, e.g. CT Hartford city / Hartford town), else "separate".
Rows are resolved to TIGER by exact NAMELSAD in that county (county subdivision first, then place); a row with no TIGER
match falls back to its own app polygon (clipped to the county).
Key "State|Name A|Name B" with Name A < Name B in plain code-point order (JS a<b, Python sorted). Only one order is listed.
A key whose class differs between counties is written as "separate" and listed in the flag table (conflict=yes).
Also writes the flag table data-v3/geo/town_pairs.csv (one line per county pair).
usage: town_pairs.py <repo> <tiger_dir> <tl_2024_us_county.zip> [--states A,B]
"""
import sys, os, json, collections, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shapely.strtree import STRtree
import coverage_audit as A
from town_gaps import recs, normT, FIPS
from town_area_gaps import dec

def main():
    a = sys.argv[1:]; opt = lambda k: a[a.index(k) + 1] if k in a else None
    repo, td, cz = [x for x in a if not x.startswith("--") and x != opt("--states")][:3]
    st2f = {v: k for k, v in FIPS.items()}
    states = opt("--states").split(",") if opt("--states") else sorted(st2f)
    C = collections.defaultdict(dict)
    for d, g in recs(cz): C[d["STATEFP"]][d["NAMELSAD"]] = g
    rows_out = []; keys = {}
    for st in states:
        sf = st2f[st]; fn = st.replace(" ", "-") + ".js"
        if not os.path.exists(os.path.join(repo, "data", fn)): continue
        geo = A.jsargs(os.path.join(repo, "data", fn), r"__geo\(")[1]
        pp = os.path.join(repo, "v2", "data", "parts", fn); parts = []
        if os.path.exists(pp): s = open(pp).read(); parts = json.loads(s[s.index("[", s.index("(")):s.rindex("]") + 1])
        PV = {}
        for p in geo.get("places") or []: PV.setdefault(p[1], p[-1])
        bycty = collections.defaultdict(list)
        for t in geo.get("towns") or []: bycty[t[1]].append((t[2], t[-1]))
        for p in parts: bycty[p[0]].append((p[1], p[2] if p[2] else PV.get(p[1])))
        cand = {cn: [r for r in L if sum(1 for q in L if normT(q[0]) == normT(r[0]) and q[0] != r[0])] for cn, L in bycty.items()}
        cand = {k: v for k, v in cand.items() if v}
        if not cand: continue
        need = {r[0] for v in cand.values() for r in v}
        CS = collections.defaultdict(dict); PL = collections.defaultdict(list)
        for d, g in recs(os.path.join(td, "tl_2024_%s_cousub.zip" % sf), lambda d: d["NAMELSAD"] in need): CS[d["COUNTYFP"]][d["NAMELSAD"]] = (d["GEOID"], g)
        for d, g in recs(os.path.join(td, "tl_2024_%s_place.zip" % sf), lambda d: d["NAMELSAD"] in need): PL[d["NAMELSAD"]].append((d["GEOID"], g))
        cfp = {}
        for d, g in recs(cz, lambda d: d["STATEFP"] == sf): cfp[d["NAMELSAD"]] = d["COUNTYFP"]
        n = 0
        for cn, L in cand.items():
            cg = C[sf][cn]
            def res(nm, enc):
                if nm in CS[cfp[cn]]: gid, g = CS[cfp[cn]][nm]; return gid, g.intersection(cg), "cousub"
                best = None
                for gid, g in PL.get(nm, []):
                    x = g.intersection(cg)
                    if x.area > 0 and (best is None or x.area > best[1].area): best = (gid, x)
                if best: return best[0], best[1], "place"
                g = dec(enc) if enc else None
                return "", (g.intersection(cg) if g is not None else None), "app"
            R = {nm: res(nm, enc) for nm, enc in {r[0]: r[1] for r in L}.items()}
            names = sorted(R)
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    x, y = names[i], names[j]
                    if normT(x) != normT(y): continue
                    gx, gy = R[x][1], R[y][1]
                    if gx is None or gy is None or gx.is_empty or gy.is_empty: ov = (0.0, 0.0)
                    else: inter = gx.intersection(gy).area; ov = (inter / gx.area, inter / gy.area)
                    cls = "same" if min(ov) >= 0.9 else "separate"
                    k = "%s|%s|%s" % (st, x, y)
                    rows_out.append({"state": st, "county": cn, "name_a": x, "geoid_a": R[x][0], "src_a": R[x][2], "name_b": y, "geoid_b": R[y][0], "src_b": R[y][2],
                                     "a_in_b": round(ov[0], 4), "b_in_a": round(ov[1], 4), "class": cls})
                    keys.setdefault(k, set()).add(cls); n += 1
        print(st, n, flush=True)
    conf = {k for k, v in keys.items() if len(v) > 1}
    for r in rows_out: r["conflict"] = "yes" if "%s|%s|%s" % (r["state"], r["name_a"], r["name_b"]) in conf else ""
    TP = {k: ("separate" if k in conf else next(iter(v))) for k, v in sorted(keys.items())}
    js = "/* town_pairs.js: see tools/town_pairs.py and data-v3/geo/ALIGNMENT.md. Key \"State|Name A|Name B\", Name A < Name B (code-point order); value \"same\" (mutual TIGER overlap >= 90 %) or \"separate\". */\nwindow.TOWN_PAIRS=" + json.dumps(TP, ensure_ascii=False, separators=(",", ":")) + ";\n"
    open(os.path.join(repo, "v2", "data", "town_pairs.js"), "w").write(js)
    with open(os.path.join(repo, "data-v3", "geo", "town_pairs.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0]), lineterminator="\n"); w.writeheader(); [w.writerow(r) for r in rows_out]
    c = collections.Counter(TP.values()); print("keys", len(TP), dict(c), "county pairs", len(rows_out), collections.Counter(r["class"] for r in rows_out), "conflicting keys", len(conf))

if __name__ == "__main__":
    main()
