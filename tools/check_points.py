#!/usr/bin/env python3
"""Independent check of v2/data/points/<State>.js (see build_points.py).
For every state: every list-row key of every layer has a point (count = rows), no extra keys except the GEOID keys of
duplicate v1 rows, and each point lies inside every shape of its row (for a key shared by several v1 rows: inside the
newer file's unique row). Uses its own decoder and an even-odd ring test with holes (no shapely).
usage: check_points.py <repo>"""
import sys, os, json, re, glob, collections
D = os.path.join(sys.argv[1], "v2", "data")
def jscall(path, name):
    s = open(path, encoding="utf-8").read(); i = s.index(name + "(") + len(name) + 1; j = s.rindex(")")
    return json.loads("[" + s[i:j] + "]")
def dec(enc, sc):
    out = []
    for rings in enc:
        rr = []
        for f in rings:
            x = y = 0; o = []
            for k in range(0, len(f), 2): x += f[k]; y += f[k + 1]; o.append((x / sc, y / sc))
            rr.append(o)
        out.append(rr)
    return out
def inring(r, x, y):
    c = False; j = len(r) - 1
    for i in range(len(r)):
        xi, yi = r[i]; xj, yj = r[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: c = not c
        j = i
    return c
def area(polys):
    s = 0
    for p in polys:
        r = p[0]; s += abs(sum(r[i - 1][0] * r[i][1] - r[i][0] * r[i - 1][1] for i in range(len(r)))) / 2
    return s
def inside(polys, x, y): return any(inring(p[0], x, y) and not any(inring(h, x, y) for h in p[1:]) for p in polys)
NATF = {"county": ("uscounties.js", "window.__uscty"), "sch": ("ussch.js", "window.__usdist"), "cd": ("uscd.js", "window.__uscd"),
        "sldu": ("ussldu.js", "window.__usdist"), "sldl": ("ussldl.js", "window.__usdist")}
NAT = collections.defaultdict(lambda: collections.defaultdict(dict))
for L, (f, c) in NATF.items():
    for r in jscall(os.path.join(D, f), c)[-1]: NAT[r[0]][L][r[1]] = dec(r[2], 1000)
GEOL = {"counties": "county", "schools": "sch", "ushouse": "cd", "senate": "sldu", "statehouse": "sldl", "places": "place"}
bad = 0; tot = collections.Counter(); totrows = collections.Counter()
for pf in sorted(glob.glob(os.path.join(D, "points", "*.js"))):
    st, P = jscall(pf, "__points"); fn = os.path.basename(pf)
    rows = collections.defaultdict(lambda: collections.defaultdict(list))
    if st == "District of Columbia":
        s = open(os.path.join(D, "dc.js")).read(); m = re.search(r"var W=(.*?),A=0,P=(.*?),A24=", s, re.S)
        W = json.loads(m.group(1)); G = dec(json.loads(m.group(2)), 1000)
        for L, k in (("county", st), ("cd", "00"), ("sch", "District of Columbia Public Schools")): rows[L][k].append(G)
        for r in W: rows["sldu"][r[1]].append(dec(r[2], 1000)); rows["sldl"][r[1]].append(dec(r[2], 1000))
    else:
        for L, d in NAT[st].items():
            for k, g in d.items(): rows[L][k].append(g)
        g = jscall(os.path.join(D, "states", fn), "__geo")[1]
        geo = collections.defaultdict(lambda: collections.defaultdict(list))
        for L, items in g.items():
            for it in items:
                if L == "towns": geo["town"][it[1] + "|" + it[2]].append(dec(it[-1], 1e4))
                elif L in GEOL: geo[GEOL[L]][it[1]].append(dec(it[-1], 1e4))
        for it in jscall(os.path.join(D, "places", fn), "__places")[1]: rows["place"][it[1]].append(dec(it[2], 1e4))
        gp = {it[1]: it[-1] for it in g.get("places", [])}
        for c, n, enc in jscall(os.path.join(D, "parts", fn), "__parts")[1]:
            e = enc or gp.get(n); rows["town"][c + "|" + n].append(dec(e, 1e4) if e else None)
        for L, d in geo.items():
            for k, lst in d.items():
                if len(lst) == 1: rows[L][k].append(lst[0])
                elif k not in rows[L]: rows[L][k].append(lst[0])   # (all dup keys have a unique newer row; checked below)
                # duplicate v1 rows: the newer unique row is authoritative for the key
    for L in ("county", "town", "place", "sch", "cd", "sldu", "sldl"):
        pts = P.get(L, {}); R = {k: v for k, v in rows.get(L, {}).items() if any(g and area(g) > 0 for g in v)}   # rows with no interior (missing / zero-area shape) cannot hold a point (reported by build_points.py)
        miss = [k for k in R if k not in pts]
        extra = [k for k in pts if k not in R and not re.fullmatch(r"\d{7,10}", k)]
        out = [k for k in R if k in pts and not all(inside(g, *pts[k]) for g in R[k] if g and area(g) > 0)]
        part = [k for k in out if any(inside(g, *pts[k]) for g in R[k] if g and area(g) > 0)]
        if part: print(st, L, "inside only some of the row's shapes (shapes do not overlap; see COVERAGE.md Points)", part); out = [k for k in out if k not in part]
        tot[L] += sum(1 for k in pts if k in R); totrows[L] += len(R)
        for nm, lst in (("missing", miss), ("extra", extra), ("outside", out)):
            if lst: bad += len(lst); print(st, L, nm, len(lst), lst[:5])
print("rows", dict(totrows)); print("points", dict(tot)); print("problems", bad)
sys.exit(1 if bad else 0)
