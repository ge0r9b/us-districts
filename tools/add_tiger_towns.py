#!/usr/bin/env python3
"""Add Census TIGER 2024 county subdivisions (e.g. Iowa's townships) to the v2 town layer, v2/data/parts/<State>.js,
rows [county name, NAMELSAD, enc] (the format read by __parts in v2/index.html; enc = rings of x10000 integer deltas).

Geometry convention = the v1 town rows the app already draws (data/<State>.js "towns"): buffer(0), simplify 0.0002 deg
(preserve_topology), x10000 deltas, consecutive duplicates dropped, rings < 4 points dropped. (Calibrated: at 0.0002
the vertex count of the 60 Iowa city rows matches the v1 rows, median ratio 1.00.)
Results are not stored for towns: the app computes them at runtime from the precinct files (sum of precincts whose
centroid is inside, else its area-weighted ≈ estimate), the same as for every other town row.
Only FUNCSTAT values given by --funcstat (default G = active government subordinate to another, i.e. Iowa townships)
are added; rows already in the v1 towns or the parts file are skipped. The report lists every township the app's
townsIn() name de-duplication (normT: suffix city/town/township/... stripped) will hide behind a same-named town.
usage: add_tiger_towns.py <repo> <State> <tl_2024_SS_cousub.zip> <2024_Gaz_counties_national.txt> --report OUT.json [--funcstat G] [--dry]
"""
import sys, os, json, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_tiger_schools import read_tiger, encode
import coverage_audit as A

def normT(n):  # same as v2/index.html normT()
    return re.sub(r"\s+(city|borough|town|township|village|cdp|municipality|charter township|plantation)$", "", str(n).lower()).strip()

def main():
    a = sys.argv[1:]; dry = "--dry" in a
    rep = a[a.index("--report") + 1]
    fs = set((a[a.index("--funcstat") + 1] if "--funcstat" in a else "G").split(","))
    pos = [x for x in a if not x.startswith("--") and x not in (rep,) and not (("--funcstat" in a) and x == a[a.index("--funcstat") + 1])]
    repo, st, z, gaz = pos[:4]
    ab = A.ABBR[st]
    cty = {}
    with open(gaz, encoding="utf-8") as f:
        f.readline()
        for line in f:
            c = line.rstrip("\n").split("\t")
            if c[0] == ab: cty[c[1].strip()] = c[3].strip()
    fn = st.replace(" ", "-") + ".js"
    geo = A.jsargs(os.path.join(repo, "data", fn), r"__geo\(")[1]
    pp = os.path.join(repo, "v2", "data", "parts", fn)
    s = open(pp).read(); i = s.index("[", s.index("(")); j = s.rindex("]") + 1
    parts = json.loads(s[i:j])
    assert s[:i] + json.dumps(parts, separators=(",", ":")) + s[j:] == s, "parts file does not round-trip"
    have = {(t[1], t[2]) for t in geo.get("towns") or []} | {(p[0], p[1]) for p in parts}
    seen = collections.defaultdict(set)  # what townsIn() will already show per county, in its order
    for t in geo.get("towns") or []: seen[t[1]].add(normT(t[2]))
    for p in parts: seen[p[0]].add(normT(p[1]))
    new = []; report = []
    for rec, g in read_tiger(z):
        if rec["FUNCSTAT"] not in fs: continue
        cn = cty.get(rec["STATEFP"] + rec["COUNTYFP"]); nm = rec["NAMELSAD"]
        r = {"geoid": rec["GEOID"], "county": cn, "name": nm, "funcstat": rec["FUNCSTAT"]}
        if not cn: r["skipped"] = "county not in Gazetteer"; report.append(r); continue
        if (cn, nm) in have: r["skipped"] = "already present"; report.append(r); continue
        enc = encode(g, 0.0002, 10000)
        if not enc: r["skipped"] = "empty after simplification"; report.append(r); continue
        r["vertices"] = sum(len(f) // 2 for q in enc for f in q)
        if normT(nm) in seen[cn]: r["hidden_by_normT"] = True
        seen[cn].add(normT(nm)); new.append([cn, nm, enc]); report.append(r)
    parts += sorted(new, key=lambda x: (x[0], x[1]))
    out = s[:i] + json.dumps(parts, separators=(",", ":")) + s[j:]
    json.dump(report, open(rep, "w"), indent=1)
    print("added", len(new), "hidden_by_normT", sum(1 for r in report if r.get("hidden_by_normT")), "skipped", collections.Counter(r.get("skipped") for r in report if r.get("skipped")),
          "bytes", len(s.encode()), "->", len(out.encode()))
    if not dry: open(pp, "w").write(out)

if __name__ == "__main__":
    main()
