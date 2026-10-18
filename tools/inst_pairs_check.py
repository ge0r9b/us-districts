#!/usr/bin/env python3
"""Fix 5 (institutions lane): verify the partially-overlapping school-district pairs whose stored figures are
identical (inst_audit.json 'partial_pairs', baseline a0c2262: 37 pairs, mostly Montana elementary/high-school pairs).

Per pair:
 1. Census 2020 block population (tl_2020_<fips>_tabblock20 POP20, block internal points; public domain) inside each
    district's full-resolution TIGER 2024 polygon (UNSD/ELSD/SCSD, by GEOID from data-v3/geo/schools.csv):
    pop(A), pop(B), pop(A xor B). If the territory that differs holds <= 2 % of the pair's population, the same
    figure is legitimate (the extra land is empty) -> verified, kept.
 2. Otherwise each row is recomputed on its own TIGER polygon: first the strict exact rule of add_tiger_schools.py
    (on the app geometry); else a POPULATION-weighted ≈: every precinct of the app's file (2024: data/precincts2024,
    official results via NYT / MEDSL; 2020: data/precincts2020, MEDSL + Census VTDs) gives the district the share of
    its 2020 block population that lies inside, scaled per county to the official county totals as fill_gray.py
    does; it needs >= 97 % of the district's population inside precincts. (Area-weighting, fill_gray's estimate, is
    also reported; it spreads ranch-land precincts evenly and misallocates small towns, so it is not used.)
    Montana 2020 is cross-checked with the same population weighting on VEST 2020 MT precincts (official SOS returns,
    CC BY 4.0): Biden and Trump must agree within 5 %, else the row is not written.
    Then the 2020/2024 consistency rule (turnout ratio 0.7-1.4, Republican share within 12 points) against the row's
    other-year final figure. A row whose stored figure differs from its recomputation by > 3 % gets it (flag ≈);
    a row that cannot be recomputed, or fails a check, is grayed when its partner's recomputation shows the stored
    figure is the partner's, else kept and logged.
A recomputation above 90 % of the 2020 population is rejected. The pair rows' other-year figures above 90 % of
the population are logged, and with --gray-implausible-other grayed (separate step).
usage: inst_pairs_check.py <repo> --pairs inst_audit.json --raw DIR --vest-mt mt_2020.zip --report OUT.json [--fix] [--gray-implausible-other]
"""
import sys, os, io, csv, json, zipfile, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_tiger_schools import load_fill_gray, strict, read_tiger
from v3_geoids import poly
from recheck_identical import load, setflag
import shapefile
from shapely.geometry import Point, shape
from shapely.strtree import STRtree
from shapely.prepared import prep

FIPS = {"Montana": "30", "California": "06", "Illinois": "17", "Oregon": "41"}

def blocks(raw, f):
    Z = zipfile.ZipFile(os.path.join(raw, "tl_2020_%s_tabblock20.zip" % f)); b = "tl_2020_%s_tabblock20" % f
    r = shapefile.Reader(shp=io.BytesIO(Z.read(b + ".shp")), dbf=io.BytesIO(Z.read(b + ".dbf")), shx=io.BytesIO(Z.read(b + ".shx")))
    P = []; W = []
    for rec in r.iterRecords(fields=["POP20", "INTPTLAT20", "INTPTLON20"]):
        d = rec.as_dict()
        if d["POP20"] > 0: P.append(Point(float(d["INTPTLON20"]), float(d["INTPTLAT20"]))); W.append(d["POP20"])
    return STRtree(P), P, W

def popset(B, g):
    T, P, W = B; gp = prep(g)
    return {i for i in T.query(g) if gp.contains(P[i])}

def vest_mt(path):
    Z = zipfile.ZipFile(path); b = "mt_2020"
    r = shapefile.Reader(shp=io.BytesIO(Z.read(b + ".shp")), dbf=io.BytesIO(Z.read(b + ".dbf")), shx=io.BytesIO(Z.read(b + ".shx")))
    G, V = [], []
    for sr in r.iterShapeRecords():
        d = sr.record.as_dict(); g = shape(sr.shape.__geo_interface__).buffer(0)
        G.append(g); V.append((d["COUNTY"], d["G20PREDBID"], d["G20PRERTRU"], d["G20PREDBID"] + d["G20PRERTRU"] + d["G20PRELJOR"]))
    return STRtree(G), G, V, {}

class PopW:
    """population-weighted allocation of one precinct set (tree, geoms, values (county,d,r,t,...), county scale)"""
    def __init__(self, B, T, G, V, sc):
        self.V, self.sc = V, sc; Tb, P, W = B; self.W = W
        self.of = {}; self.pp = collections.Counter()
        for bi, pt in enumerate(P):
            for k in T.query(pt):
                if G[k].contains(pt): self.of[bi] = k; self.pp[k] += W[bi]; break
    def est(self, inside):
        part = collections.Counter(); dpop = 0; placed = 0
        for bi in inside:
            dpop += self.W[bi]; k = self.of.get(bi)
            if k is not None and self.V[k][3] > 0: part[k] += self.W[bi]; placed += self.W[bi]
        if not dpop: return None, "no population"
        if placed < 0.97 * dpop: return None, "population in precincts with votes %.0f %%" % (100 * placed / dpop)
        v = [0.0, 0.0, 0.0]
        for k, w in part.items():
            f = w / self.pp[k]; c = self.sc.get(self.V[k][0], (1.0, 1.0, 1.0))
            d, r, t = self.V[k][1:4]   # county scale is per (dem, rep, other), as in fill_gray.py
            v[0] += f * d * c[0]; v[1] += f * r * c[1]; v[2] += f * (d * c[0] + r * c[1] + (t - d - r) * c[2])
        return [round(x) for x in v], "population-weighted, %d precincts" % len(part)

PLAUS = 0.9   # votes above 90 % of the 2020 resident population are not credible outside Alaska (max seen in these pairs: 0.79)
POP = {}; IMPL = set(); GRAY_OTHER = "--gray-implausible-other" in sys.argv

def sh(v): return v[1] / (v[0] + v[1]) if v and v[0] + v[1] else 0

def main():
    a = sys.argv[1:]; repo = a[0]; pairs = json.load(open(a[a.index("--pairs") + 1]))["partial_pairs"]
    raw = a[a.index("--raw") + 1]; rep = a[a.index("--report") + 1]; fix = "--fix" in a
    vest = a[a.index("--vest-mt") + 1] if "--vest-mt" in a else None
    gid = {(r["state"], r["v2_name"]): r["geoid"] for r in csv.DictReader(open(os.path.join(repo, "data-v3/geo/schools.csv")))}
    TG = {}
    for st, f in FIPS.items():
        for t in ("unsd", "elsd", "scsd"):
            z = os.path.join(raw, "tl_2024_%s_%s.zip" % (f, t))
            if os.path.exists(z):
                for rec, g in read_tiger(z): TG[rec["GEOID"]] = g
    p = os.path.join(repo, "v2/data/ussch.js"); s, i, j, rows = load(p)
    idx = {(r[0], r[1]): k for k, r in enumerate(rows)}
    NS = {y: load_fill_gray(repo, y) for y in ("2024", "2020")}
    BL = {}; PW = {}; out = []; plan = {}
    for e in pairs:
        st, yr = e["state"], e["year"]; YI = 3 if yr == "2024" else 4
        ka, kb = idx[(st, e["a"])], idx[(st, e["b"])]; ra, rb = rows[ka], rows[kb]
        v = ra[YI]; rec = {"year": yr, "state": st, "a": e["a"], "b": e["b"], "stored": v}
        if v != rb[YI]: rec["verdict"] = "no longer identical"; out.append(rec); continue
        if st not in BL: BL[st] = blocks(raw, FIPS[st])
        for src in ([yr] + (["vest"] if st == "Montana" and yr == "2020" and vest else [])):
            if (st, src) not in PW:
                if src == "vest": T, G, V, sc = vest_mt(vest)
                else: T, G, V, sc = NS[src]["prec"](st)[:4]
                PW[(st, src)] = PopW(BL[st], T, G, V, sc)
        W = BL[st][2]; geo = {}
        for name in (e["a"], e["b"]):
            g = TG.get(gid.get((st, name))); geo[name] = popset(BL[st], g) if g is not None else None
        A, Bs = geo[e["a"]], geo[e["b"]]
        if A is not None and Bs is not None:
            un = sum(W[x] for x in A | Bs); px = sum(W[x] for x in A ^ Bs)
            rec.update(pop_a=sum(W[x] for x in A), pop_b=sum(W[x] for x in Bs), pop_differing_share=round(px / un, 4) if un else None)
        rc = {}
        for name, r in ((e["a"], ra), (e["b"], rb)):
            D = poly(r[2]); c = {}
            ex, why = strict(NS[yr], st, D, yr)
            aw, _ = NS[yr]["estimate"](st, D); c["area_weighted"] = aw
            if ex: c.update(recomputed=ex, method="exact", why=why)
            elif geo[name] is None: c.update(recomputed=None, method="none", why="no TIGER polygon")
            else:
                pv, w2 = PW[(st, yr)].est(geo[name]); c.update(recomputed=pv, method="estimate" if pv else "none", why="%s; %s" % (why, w2))
                if pv and (st, "vest") in PW:
                    vv, _ = PW[(st, "vest")].est(geo[name]); c["vest_popweighted"] = vv
                    if not vv or abs(vv[0] - pv[0]) > 0.05 * pv[0] + 3 or abs(vv[1] - pv[1]) > 0.05 * pv[1] + 3:
                        c.update(method="none", why=c["why"] + "; VEST 2020 cross-check disagrees (%s)" % vv, rejected=pv, recomputed=None)
            pop = rec.get("pop_a") if name == e["a"] else rec.get("pop_b")
            if c["recomputed"] and pop and c["recomputed"][2] > PLAUS * pop:
                c.update(method="none", why=c["why"] + "; implausible: %d votes for %d residents" % (c["recomputed"][2], pop), rejected=c["recomputed"], recomputed=None)
            c["dev"] = round(abs(c["recomputed"][2] - v[2]) / v[2], 3) if c["recomputed"] else None
            rc[name] = c
        rec["recomputed"] = rc
        if rec.get("pop_differing_share") is not None and rec["pop_differing_share"] <= 0.02:
            rec["verdict"] = "verified: the differing territory holds %.1f %% of the population; identical figures legitimate" % (100 * rec["pop_differing_share"])
        else:
            rec["verdict"] = "recomputed"
            for name, other in ((e["a"], e["b"]), (e["b"], e["a"])):
                c, o = rc[name], rc[other]
                if c["dev"] is not None and c["dev"] > 0.03: plan[(name, st, yr)] = ["set", c["recomputed"], c["method"], other]
                elif c["dev"] is None and o["dev"] is not None and o["dev"] <= 0.03: plan[(name, st, yr)] = ["gray", None, "none", other]
                elif c["dev"] is None: plan[(name, st, yr)] = ["keep", None, None, other, "cannot recompute; partner does not confirm whose figure it is"]
                else: plan[(name, st, yr)] = ["keep", None, None, other, "matches its own recomputation"]
        POP[(st, e["a"])] = rec.get("pop_a"); POP[(st, e["b"])] = rec.get("pop_b")
        out.append(rec)
    # rows of the pairs whose OTHER-year figure (not part of the identical pair) is implausible
    for (st, name), pop in POP.items():
        for oy in ("2024", "2020"):
            if (name, st, oy) in plan: continue
            r = rows[idx[(st, name)]]; YI = 3 if oy == "2024" else 4; o = r[YI] if len(r) > YI else None
            if o and pop and o[2] > PLAUS * pop: IMPL.add((st, name, oy))
    # consistency rule against the row's other-year final figure
    def final(name, st, yr):
        q = plan.get((name, st, yr))
        if q and q[0] in ("set", "gray"): return q[1]
        r = rows[idx[(st, name)]]; YI = 3 if yr == "2024" else 4; return r[YI] if len(r) > YI else None
    for (name, st, yr), q in list(plan.items()):
        if q[0] != "set": continue
        oy = "2020" if yr == "2024" else "2024"; o = final(name, st, oy); v = q[1]
        pop = POP.get((st, name))
        if o and pop and o[2] > PLAUS * pop:
            q.append("other-year figure %s implausible for %d residents; consistency check skipped" % (o, pop)); IMPL.add((st, name, oy)); continue
        if o and o[2]:
            ratio = v[2] / o[2] if yr == "2024" else o[2] / v[2]
            if not (0.7 <= ratio <= 1.4 and abs(sh(v) - sh(o)) <= 0.12):
                q.append("2020/2024 consistency check vs %s %s failed (ratio %.2f)" % (oy, o, ratio)); q[0] = "check_failed"
    changed = 0
    for (name, st, yr), q in plan.items():
        r = rows[idx[(st, name)]]; YI = 3 if yr == "2024" else 4; before = r[YI]
        if fix and q[0] == "set": r[YI] = q[1]; setflag(r, yr, q[2]); changed += 1
        elif fix and q[0] == "gray": r[YI] = None; setflag(r, yr, "gray"); changed += 1
        print("PLAN", yr, st[:3], name[:44].ljust(44), before, "->", q[1] if q[0] in ("set", "gray") else before, q[0], q[4:] if len(q) > 4 else "")
    for rec in out:
        for name in (rec["a"], rec["b"]):
            q = plan.get((name, rec["state"], rec["year"]))
            if q: rec.setdefault("actions", {})[name] = q
    impl = []
    for st, name, oy in sorted(IMPL):
        r = rows[idx[(st, name)]]; YI = 3 if oy == "2024" else 4; o = r[YI] if len(r) > YI else None
        if (name, st, oy) in plan or not o: continue
        impl.append({"state": st, "name": name, "year": oy, "value": o, "pop2020": POP[(st, name)]})
        print("IMPLAUSIBLE other-year", oy, st[:3], name, o, "pop", POP[(st, name)], "-> gray" if GRAY_OTHER else "(logged)")
        if fix and GRAY_OTHER: r[YI] = None; setflag(r, oy, "gray"); changed += 1
    out.append({"implausible_other_year": impl, "grayed": GRAY_OTHER and fix})
    if fix and changed: open(p, "w").write(s[:i] + json.dumps(rows, separators=(",", ":")) + s[j:])
    json.dump(out, open(rep, "w"), indent=1, ensure_ascii=False)
    print(collections.Counter(r["verdict"].split(":")[0] for r in out if "verdict" in r), collections.Counter(q[0] for q in plan.values()), "rows changed", changed)

if __name__ == "__main__":
    main()
