#!/usr/bin/env python3
"""Add Census TIGER 2024 school districts that are missing from v2/data/ussch.js (first use: Oklahoma's 96
elementary districts, ELSD), in the existing row format [state, name, enc, a24, a20(, flag)].

Geometry: same convention as the rest of ussch.js (/workspace/w/simpsld.py): buffer(0), simplify(0.004 deg,
preserve_topology), coordinates x1000 as integer deltas, consecutive duplicates dropped, rings with < 4 points dropped.

Results per year, never invented:
 1. exact (no flag), the strict school rule (/workspace/w/sch/sch.py): every precinct of the app's precinct file
    (data/precincts<year>/<State>.js) that overlaps the district by > 3 % of its own area must lie >= 97 % inside it,
    those precincts must cover >= 97 % of the district, and every touched county's precinct total must be within
    0.5 % of the official county total (data/election<year>.js); value = plain sum of those precincts;
 2. otherwise the area-weighted estimate of tools/fill_gray.py (same code, executed from that file: precinct votes
    shared by area, scaled per county and party to official county totals, >= 90 % usable cover, < 2 % failing
    counties), flagged ≈ ('e24' / 'e20' / 'est' when both years are estimates);
 3. otherwise gray (null) with the reason in the report.
usage: add_tiger_schools.py <repo> <State> <tiger zip> [<tiger zip> ...] --report OUT.json [--dry]
"""
import sys, os, json, io, zipfile, collections
import shapefile
from shapely.geometry import shape
from shapely.strtree import STRtree

def load_fill_gray(repo, year):
    ns = {}
    src = open(os.path.join(repo, "tools", "fill_gray.py")).read().split("FL={")[0]
    argv = sys.argv; sys.argv = ["fill_gray.py", repo, year, "--dry"]
    try: exec(compile(src, "fill_gray.py", "exec"), ns)
    finally: sys.argv = argv
    return ns

def read_tiger(z):
    Z = zipfile.ZipFile(z); b = [n for n in Z.namelist() if n.endswith(".shp")][0][:-4]
    r = shapefile.Reader(shp=io.BytesIO(Z.read(b + ".shp")), dbf=io.BytesIO(Z.read(b + ".dbf")), shx=io.BytesIO(Z.read(b + ".shx")), encoding="utf-8")
    for s in r.iterShapeRecords():
        yield s.record.as_dict(), shape(s.shape.__geo_interface__).buffer(0)

def encode(g, tol=0.004, S=1000):
    g = g.buffer(0).simplify(tol, preserve_topology=True)
    geoms = [g] if g.geom_type == "Polygon" else list(getattr(g, "geoms", []))
    enc = []
    for q in geoms:
        if q.is_empty or q.geom_type != "Polygon": continue
        rings = []
        for r in [q.exterior] + list(q.interiors):
            flat = []; px = py = 0
            for x, y in r.coords:
                x, y = round(x * S), round(y * S)
                if flat and x == px and y == py: continue
                flat += [x - px, y - py]; px, py = x, y
            if len(flat) >= 8: rings.append(flat)
        if rings: enc.append(rings)
    return enc

def strict(ns, st, D, year):
    P = ns["prec"](st)
    if not P or P[0] is None: return None, "no precinct file"
    T, G, V, sc, TB, BAD = P
    E = ns["E"]; ins = []; cov = 0.0
    for i in T.query(D):
        try: a = G[i].intersection(D).area
        except Exception: continue
        if a <= 0: continue
        fr = a / V[i][4]
        if fr >= 0.97: ins.append(i); cov += a
        elif fr > 0.03 and V[i][3] > 0: return None, "precinct %s straddles the boundary (%.0f %% inside)" % (V[i][0], 100 * fr)
    if TB is not None:
        for i in TB.query(D):
            try:
                if BAD[i].intersection(D).area > 0.03 * BAD[i].area: return None, "touches a county whose precincts fail the county check"
            except Exception: pass
    if cov < 0.97 * D.area: return None, "precincts inside cover %.0f %%" % (100 * cov / D.area)
    if not ins: return None, "no precinct inside"
    # county check: precinct file total within 0.5 % of official for every touched county
    ctot = collections.Counter()
    for k in range(len(V)): ctot[V[k][0]] += V[k][3]
    for c in {V[i][0] for i in ins}:
        o = E.get(st + "|" + c)
        if not o or not o[2] or abs(ctot[c] / o[2] - 1) > 0.005: return None, "county %s precincts not within 0.5 %% of official" % c
    s = [0, 0, 0]
    for i in ins: s[0] += V[i][1]; s[1] += V[i][2]; s[2] += V[i][3]
    if s[2] < 1: return None, "no votes"
    return s, None

def main():
    a = sys.argv[1:]; dry = "--dry" in a
    rep = a[a.index("--report") + 1]
    pos = [x for x in a if not x.startswith("--") and x != rep]
    repo, st, zips = pos[0], pos[1], pos[2:]
    p = os.path.join(repo, "v2", "data", "ussch.js")
    s = open(p).read(); i = s.index("[", s.index("(")); j = s.rindex("]") + 1
    rows = json.loads(s[i:j])
    have = {(r[0], r[1]) for r in rows}
    NS = {y: load_fill_gray(repo, y) for y in ("2024", "2020")}
    new = []; report = []
    for z in zips:
        for rec, g in read_tiger(z):
            nm = rec["NAME"]
            if (st, nm) in have: report.append({"geoid": rec["GEOID"], "name": nm, "skipped": "name already in ussch.js"}); continue
            enc = encode(g)
            if not enc: report.append({"geoid": rec["GEOID"], "name": nm, "skipped": "empty after simplification"}); continue
            D = NS["2024"]["mp"](enc, 1000)  # the polygon as stored (what the app draws)
            vals = {}; how = {}; why = {}
            for y in ("2024", "2020"):
                v, w = strict(NS[y], st, D, y)
                if v: vals[y] = v; how[y] = "exact"; continue
                ev, ew = NS[y]["estimate"](st, D)
                if ev: vals[y] = ev; how[y] = "estimate"; why[y] = w
                else: vals[y] = None; how[y] = "gray"; why[y] = "exact: %s; estimate: %s" % (w, ew)
            e24, e20 = how["2024"] == "estimate", how["2020"] == "estimate"
            flag = "est" if e24 and e20 else "e24" if e24 else "e20" if e20 else None
            row = [st, nm, enc, vals["2024"], vals["2020"]] + ([flag] if flag else [])
            new.append(row)
            report.append({"geoid": rec["GEOID"], "name": nm, "tiger": os.path.basename(z), "2024": vals["2024"], "2020": vals["2020"], "method": how, "why": why, "flag": flag,
                           "vertices": sum(len(f) // 2 for q in enc for f in q)})
    # insert after the state's last row, then keep the state's rows sorted by name like the source order is not guaranteed
    last = max(k for k, r in enumerate(rows) if r[0] == st)
    rows[last + 1:last + 1] = sorted(new, key=lambda r: r[1])
    json.dump(report, open(rep, "w"), indent=1)
    c = collections.Counter((r.get("method") or {}).get("2024", "skipped") for r in report); c20 = collections.Counter((r.get("method") or {}).get("2020", "skipped") for r in report)
    print("new rows", len(new), "2024", dict(c), "2020", dict(c20))
    if not dry:
        open(p, "w").write(s[:i] + json.dumps(rows, separators=(",", ":")) + s[j:])

if __name__ == "__main__":
    main()
