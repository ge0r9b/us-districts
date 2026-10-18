#!/usr/bin/env python3
"""Gray batch 2, pass 3 (institutions lane): the deferred districts, where the app's 2024 (or 2020) precinct file
has no polygon for some of a county's official reporting units, so part of the district lies in no precinct.

Method (fix-3 approach, automated per county; nothing in data/ is written):
  1. Official units: MEDSL 2024-elections-official (CC0, compiled from the official county canvass), US PRESIDENT,
     aggregated over vote modes per precinct (TOTAL rows only where a state reports them). Countywide units with no
     geography (absentee, early, provisional, central count, UOCAVA) are pooled.
  2. Match: every app precinct row in the county is matched once to an official unit with the same Harris and Trump
     votes (names differ between sources; the vote pair is the join key). A county with an app row left unmatched fails.
  3. The official units left unmatched (and not pooled) are the county's units without a polygon. Because a county's
     precincts tile the county, their territory is the county's 2020-Census blocks that lie in no app precinct polygon
     (the "hole"). Their summed votes are placed on the hole's blocks by 2020 population (population-weighted, ≈).
  4. Hole checks: the hole holds < 50 % of the county's population (otherwise it is a county average, not a precinct
     estimate); hole votes <= 90 % of hole population; and the hole passes the 2020 consistency rule against the 2020
     precinct file on the same blocks (turnout ratio 0.7-1.4, Republican share within 12 points, >= 97 % of hole
     population in 2020 precincts with votes).
  5. District: population-weighted over app precincts plus the hole, scaled per county and party to the official county
     totals in data/election<year>.js (pooled votes enter here, as in fill_gray.py); >= 97 % of the district's
     population placed; 90 %-of-population plausibility bar; 2020/2024 consistency rule vs the stored other-year value.
usage: inst_gray2_holes.py <repo> --raw DIR --report OUT.json [--fix]
"""
import sys, os, io, re, csv, json, zipfile, collections, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coverage_audit as ca
from add_tiger_schools import read_tiger
from recheck_identical import load, setflag
from inst_prec_fill import mp
import shapefile
from shapely.geometry import Point
from shapely.strtree import STRtree
from shapely.prepared import prep

FIPS = {"Alabama": "01", "Arkansas": "05", "Colorado": "08", "Kentucky": "21", "Mississippi": "28", "Missouri": "29",
        "Montana": "30", "New York": "36", "Ohio": "39", "New Mexico": "35"}
MEDSL = {"Kentucky": "/workspace/w/inst-raw/gray2/medsl24/ky24.csv", "New York": "/workspace/w/inst-raw/gray2/medsl24/ny24.csv"}
TARGETS = [("Alabama", "Guntersville City School District"), ("Arkansas", "Jessieville School District"),
           ("Colorado", "Aspen School District 1"), ("Colorado", "Salida School District R-32"),
           ("Kentucky", "Somerset Independent School District"), ("Kentucky", "East Bernstadt Independent School District"),
           ("Kentucky", "Laurel County School District for East Bernstadt ISD"), ("Mississippi", "South Delta School District"),
           ("Missouri", "Cape Girardeau 63 School District"), ("Missouri", "Delta C-7 School District"),
           ("Missouri", "Pettis County R-XII School District"), ("Montana", "Lambert Elementary School District"),
           ("Montana", "Lambert High School District"), ("New York", "Bath Central School District"),
           ("New York", "Geneva City School District"), ("Ohio", "Shelby City School District"),
           ("Ohio", "Carey Exempted Village School District")]
TARGETS = [(s, n, "2024") for s, n in TARGETS] + [("New Mexico", "Loving Municipal Schools", "2020")]
SPECIAL = {"TOTAL VOTES CAST", "OVERVOTES", "UNDERVOTES", "CONTEST TOTAL", "REGISTERED VOTERS", "BALLOTS CAST", "BLANK", "OVER VOTES", "UNDER VOTES"}
POOL = re.compile(r"ABSENTEE|EARLY|PROVI?S?IONAL|PROVSIONAL|CENTRAL|UOCAVA|OVERSEAS|FEDERAL|MAIL|^COUNTY|COUNTYWIDE|AB\.|WRITE|FAILSAFE|AFFIDAVIT", re.I)
PLAUS = 0.9
sh = lambda v: v[1] / (v[0] + v[1]) if v and v[0] + v[1] else 0

def blocks(raw, f):
    Z = zipfile.ZipFile(os.path.join(raw, "tl_2020_%s_tabblock20.zip" % f)); b = "tl_2020_%s_tabblock20" % f
    r = shapefile.Reader(shp=io.BytesIO(Z.read(b + ".shp")), dbf=io.BytesIO(Z.read(b + ".dbf")), shx=io.BytesIO(Z.read(b + ".shx")))
    P, W, C = [], [], []
    for rec in r.iterRecords(fields=["POP20", "INTPTLAT20", "INTPTLON20", "COUNTYFP20"]):
        d = rec.as_dict()
        if d["POP20"] > 0: P.append(Point(float(d["INTPTLON20"]), float(d["INTPTLAT20"]))); W.append(d["POP20"]); C.append(f + d["COUNTYFP20"])
    return STRtree(P), P, W, C

def official_units(st, cname):
    fn = MEDSL.get(st) or "/workspace/db/medsl24/%s24.csv" % ca.ABBR[st].lower()
    rows = [r for r in csv.DictReader(open(fn)) if r["office"] == "US PRESIDENT" and r["county_name"] == cname.upper() and r["candidate"].upper() not in SPECIAL]
    has_total = {r["precinct"] for r in rows if r["mode"] == "TOTAL"}
    U = collections.defaultdict(lambda: [0, 0, 0])
    for r in rows:
        if r["precinct"] in has_total and r["mode"] != "TOTAL": continue
        try: v = int(float(r["votes"] or 0))
        except ValueError: continue
        if r.get("writein") == "TRUE": continue     # data/election<year>.js convention: total excludes write-ins
        k = r["precinct"]; c = r["candidate"].upper(); U[k][2] += v
        if "HARRIS" in c: U[k][0] += v
        if "TRUMP" in c: U[k][1] += v
    return dict(U), fn

class State:
    def __init__(self, repo, raw, st):
        f = FIPS[st]; self.st = st; self.B = blocks(raw, f)
        self.E = {}; self.rows = {}; self.T = {}; self.of = {}
        for yr in ("2024", "2020"):
            self.E[yr] = ca.jsargs(os.path.join(repo, "data/election%s.js" % yr), r"ELECTION%s\s*=" % yr)[0]
            rows = ca.jsargs(os.path.join(repo, "data/precincts%s/%s.js" % (yr, st.replace(" ", "_"))), r"__prec\(")[1]
            G = []; R = []
            for r in rows:
                g = mp(r[5])
                if g.is_empty or g.area <= 0: continue
                G.append(g); R.append(r)
            self.rows[yr] = R; T = STRtree(G); of = {}
            if yr == "2020": self.G20 = G
            for bi, pt in enumerate(self.B[1]):
                for k in T.query(pt):
                    if G[k].contains(pt): of[bi] = k; break
            self.of[yr] = of
        self.cfips = {}
        for bi, c in enumerate(self.B[3]): self.cfips.setdefault(c, []).append(bi)

    def cname(self, cf, yr):
        """county name used in the app files for a county FIPS, from the blocks that fall in its precincts"""
        n = collections.Counter(self.rows[yr][self.of[yr][bi]][0] for bi in self.cfips.get(cf, []) if bi in self.of[yr])
        return n.most_common(1)[0][0] if n else None

    def hole(self, cf, yr, rep):
        """population-weighted unit for the county's official units without a polygon; None + reason if it fails"""
        cn = self.cname(cf, yr); W = self.B[2]
        if not cn:
            return self.from2020(cf, yr, rep)
        hb = [bi for bi in self.cfips[cf] if bi not in self.of[yr]]; hpop = sum(W[b] for b in hb); cpop = sum(W[b] for b in self.cfips[cf])
        R = {"county": cn, "hole_pop2020": hpop, "county_pop2020": cpop}; rep[cn] = R
        if hpop == 0: return [[]], None
        if hpop >= 0.5 * cpop: R["why"] = "hole holds %.0f %% of the county population" % (100 * hpop / cpop); return None, R["why"]
        if yr != "2024": R["why"] = "no official %s precinct returns fetched for this county" % yr; return None, R["why"]
        U, fn = official_units(self.st, cn.replace(" County", "").replace(" Parish", ""))
        R["source"] = fn; R["official_units"] = len(U)
        if not U: R["why"] = "no MEDSL units for the county"; return None, R["why"]
        pool = {k: v for k, v in U.items() if POOL.search(k)}
        free = collections.defaultdict(list)
        for k, v in U.items():
            if k not in pool: free[(v[0], v[1])].append(k)
        unm = []; byname = []
        for r in self.rows[yr]:
            if r[0] != cn: continue
            l = free.get((r[2], r[3]))
            if l: l.pop()
            else: unm.append([r[1], r[2], r[3]])
        # fallback: same unit name (official names carry a 'NNN_' sequence prefix in some MEDSL files)
        nm = lambda x: re.sub(r"[^A-Z0-9]", "", re.sub(r"^\d+_", "", x).upper())
        left = {nm(k): k for l in free.values() for k in l}
        still = []
        for u in unm:
            k = left.pop(nm(u[0]), None)
            if k: byname.append({"app": u, "official": [k] + U[k]})
            else: still.append(u)
        for x in byname:
            for l in free.values():
                if x["official"][0] in l: l.remove(x["official"][0])
        unm = still; R["matched_by_name_votes_differ"] = byname
        miss = {k: U[k] for l in free.values() for k in l}
        R.update(pool=pool, missing_units=miss, app_rows_unmatched=unm)
        if unm: R["why"] = "%d app precinct rows match no official unit by Harris/Trump votes" % len(unm); return None, R["why"]
        if not miss: R["why"] = "every official unit already has a polygon, but %d residents lie in no precinct" % hpop; return None, R["why"]
        v = [sum(x[i] for x in miss.values()) for i in range(3)]; R["hole_votes"] = v
        if v[2] > PLAUS * hpop: R["why"] = "implausible hole: %d votes for %d residents" % (v[2], hpop); return None, R["why"]
        # 2020 votes on the hole's blocks (population-weighted from the 2020 precinct file)
        R20 = self.rows["2020"]; of20 = self.of["2020"]; ppw = collections.Counter()
        for b in self.cfips[cf]:
            if b in of20: ppw[of20[b]] += W[b]
        placed = sum(W[b] for b in hb if b in of20 and R20[of20[b]][4] > 0)
        if placed < 0.97 * hpop: R["why"] = "hole population in 2020 precincts %.0f %%" % (100 * placed / hpop); return None, R["why"]
        # split the hole into spatial components: 2020 precincts holding hole blocks, joined when their polygons touch
        ks = sorted({of20[b] for b in hb if b in of20}); G20 = self.G20
        par = {k: k for k in ks}
        def fd(k):
            while par[k] != k: par[k] = par[par[k]]; k = par[k]
            return k
        for x in range(len(ks)):
            for y in range(x + 1, len(ks)):
                if G20[ks[x]].buffer(0.0005).intersects(G20[ks[y]]): par[fd(ks[x])] = fd(ks[y])
        comp = collections.defaultdict(list)
        for b in hb:
            if b in of20: comp[fd(of20[b])].append(b)
        comps = []
        for c, bs in comp.items():
            w20 = [sum(R20[of20[b]][2 + i] * W[b] / ppw[of20[b]] for b in bs if R20[of20[b]][4] > 0) for i in range(3)]
            comps.append({"blocks": bs, "pop": sum(W[b] for b in bs), "v2020": w20, "n20": len({of20[b] for b in bs})})
        comps = [c for c in comps if c["pop"] > 0]
        names = sorted(miss)
        def ok(u, w): tr = u[2] / w[2] if w[2] else 0; return 0.7 <= tr <= 1.4 and abs(sh(u) - sh(w)) <= 0.12, tr
        valid = []
        if len(comps) <= len(names) and len(comps) ** len(names) <= 5000:
            for asg in itertools.product(range(len(comps)), repeat=len(names)):
                if len(set(asg)) != len(comps): continue
                vs = [[0, 0, 0] for _ in comps]
                for n, ci in zip(names, asg):
                    for i in range(3): vs[ci][i] += miss[n][i]
                if all(ok(vs[ci], comps[ci]["v2020"])[0] and vs[ci][2] <= PLAUS * comps[ci]["pop"] for ci in range(len(comps))): valid.append((asg, vs))
        R["hole_components"] = [{"pop2020": c["pop"], "v2020_popw": [round(x) for x in c["v2020"]]} for c in comps]
        R["valid_assignments"] = [{n: ci for n, ci in zip(names, asg)} for asg, _ in valid]
        if not valid:
            w20 = [sum(c["v2020"][i] for c in comps) for i in range(3)]; good, tr = ok(v, w20)
            R["why"] = "no assignment of the %d missing units to the %d hole components passes the 2020 consistency rule (whole hole: ratio %.2f, R share %.2f vs %.2f)" % (len(names), len(comps), tr, sh(v), sh(w20))
            return None, R["why"]
        out = []
        for asg, vs in valid:
            out.append([{"blocks": set(c["blocks"]), "pop": c["pop"], "v": vs[ci], "cn": cn, "nunits": asg.count(ci), "n20": c["n20"]} for ci, c in enumerate(comps)])
        return out, None

    def from2020(self, cf, yr, rep):
        """county with no app polygons for this year: official units matched by name to the 2020 precinct polygons (fix 3)"""
        cn = self.cname(cf, "2020"); W = self.B[2]
        if not cn or yr != "2024": return None, "county %s has no app %s precinct polygons" % (cf, yr)
        R = {"county": cn, "method": "official 2024 units matched by name to the 2020 precinct polygons"}; rep[cn] = R
        U, fn = official_units(self.st, cn.replace(" County", "")); R["source"] = fn
        pool = {k: v for k, v in U.items() if POOL.search(k)}
        # polling-place suffixes are dropped ('ADDIE VOTING PRECINCT' = 2020 'Addie'); matches must be one-to-one and use every 2020 precinct
        nm = lambda x: re.sub(r"[^A-Z0-9]", "", re.sub(r"\b(VOTING|PRECINCT|COURTHOUSE|COMMUNITY|CENTER|CTR)\b", "", re.sub(r"^\d+_", "", x).upper()))
        R20 = self.rows["2020"]; of20 = self.of["2020"]; idx = {nm(r[1]): k for k, r in enumerate(R20) if r[0] == cn}
        comps = []; bad = []; nl = [sum(v[i] for v in pool.values()) for i in range(3)]
        loc = [sum(v[i] for k, v in U.items() if k not in pool) for i in range(3)]; scale = (loc[2] + nl[2]) / loc[2] if loc[2] else 0
        used = set()
        for k, v in sorted(U.items()):
            if k in pool: continue
            j = idx.get(nm(k))
            if j is None or j in used: bad.append("unit %s has no unique same-name 2020 precinct" % k); continue
            used.add(j); w = R20[j][2:5]; bs = [b for b in self.cfips[cf] if of20.get(b) == j]
            tr = v[2] * scale / w[2] if w[2] else 0
            if not (0.7 <= tr <= 1.4 and abs(sh(v) - sh(w)) <= 0.12): bad.append("unit %s fails the 2020 consistency rule (ratio %.2f, R share %.2f vs %.2f)" % (k, tr, sh(v), sh(w)))
            comps.append({"blocks": set(bs), "pop": sum(W[b] for b in bs), "v": v, "cn": cn, "unit": k, "v2020": w, "ratio": round(tr, 3), "nunits": 1, "n20": 1})
        if len(used) != len(idx): bad.append("2020 precincts without a 2024 unit: %s" % [R20[j][1] for j in idx.values() if j not in used])
        R["units"] = [{x: c[x] for x in ("unit", "pop", "v", "v2020", "ratio")} for c in comps]; R["pool"] = pool
        if bad: R["why"] = "; ".join(bad); return None, R["why"]
        return [comps], None

    def estimate(self, g, yr, hrep):
        Tb, P, W, C = self.B; gp = prep(g)
        ins = [i for i in Tb.query(g) if gp.contains(P[i])]; pop = sum(W[i] for i in ins)
        if not pop: return None, "no population", 0
        rows = self.rows[yr]; of = self.of[yr]
        ppw = collections.Counter()
        cs = {self.B[3][i] for i in ins}
        for c in cs:
            for b in self.cfips[c]:
                if b in of: ppw[of[b]] += W[b]
        holes = {}; why = []
        for c in sorted(cs):
            if any(i not in of for i in ins if C[i] == c):
                h, w = self.hole(c, yr, hrep)
                if h: holes[c] = h
                else: why.append(w)
        # every combination of valid unit-to-component assignments, one per county
        res = []
        for combo in itertools.product(*[holes[c] for c in sorted(holes)]):
            H = dict(zip(sorted(holes), combo)); res.append(self._est(ins, pop, yr, H))
        if not res: res = [self._est(ins, pop, yr, {})]
        if any(r[0] is None for r in res): return None, res[0][1] + ("; " + "; ".join(why) if why else ""), pop
        if len(res) > 1:
            lo = min(r[0][2] for r in res); hi = max(r[0][2] for r in res); s1 = [sh(r[0]) for r in res]
            if hi > 1.03 * lo or max(s1) - min(s1) > 0.02: return None, "ambiguous: %d valid assignments of missing units to hole components give %s" % (len(res), [r[0] for r in res]), pop
        return res[0][0], res[0][1] + ("" if len(res) == 1 else "; %d valid unit assignments agree within 3 %%" % len(res)), pop

    def _est(self, ins, pop, yr, H):
        Tb, P, W, C = self.B; rows = self.rob = self.rows[yr]; of = self.of[yr]
        cs = {C[i] for i in ins}; ppw = collections.Counter()
        for c in cs:
            for b in self.cfips[c]:
                if b in of: ppw[of[b]] += W[b]
        comp_of = {}
        for c, comps in H.items():
            for k in comps:
                for b in k["blocks"]: comp_of[b] = k
        sc = {}
        for c in cs:
            cn = self.cname(c, yr) or (H[c][0]["cn"] if H.get(c) else None)
            if not cn: continue
            loc = [0, 0, 0]
            for r in rows:
                if r[0] == cn:
                    for i in range(3): loc[i] += r[2 + i]
            for k in H.get(c, []):
                for i in range(3): loc[i] += k["v"][i]
            o = self.E[yr].get(self.st + "|" + cn)
            if o and loc[0] + loc[1] > 0 and 0.5 <= (loc[0] + loc[1]) / (o[0] + o[1]) <= 1.1:
                sc[cn] = (o[0] / max(1, loc[0]), o[1] / max(1, loc[1]), max(0, o[2] - o[0] - o[1]) / max(1, loc[2] - loc[0] - loc[1]) if loc[2] - loc[0] - loc[1] > 0 else 0.0)
        v = [0.0, 0.0, 0.0]; placed = 0; fromhole = 0; contrib = collections.Counter()
        for i in ins:
            if i in of:
                r = rows[of[i]]
                if r[4] <= 0 or r[0] not in sc: continue
                f = W[i] / ppw[of[i]]; d, rp, t = r[2], r[3], r[4]; s = sc[r[0]]
            elif i in comp_of and comp_of[i]["v"][2] > 0 and comp_of[i]["cn"] in sc:
                k = comp_of[i]; f = W[i] / k["pop"]; d, rp, t = k["v"]; s = sc[k["cn"]]; fromhole += W[i]; contrib[id(k)] += W[i]
            else: continue
            placed += W[i]
            v[0] += f * d * s[0]; v[1] += f * rp * s[1]; v[2] += f * (d * s[0] + rp * s[1] + (t - d - rp) * s[2])
        if placed < 0.97 * pop: return None, "population placed %.0f %%" % (100 * placed / pop)
        # a component holding several official units, spanning several 2020 precincts, cannot be apportioned inside;
        # it may not supply most of a district that holds only part of it
        for c, comps in H.items():
            for k in comps:
                if contrib[id(k)] > 0.5 * pop and k["nunits"] > 1 and k["n20"] > 1 and contrib[id(k)] < 0.9 * k["pop"]:
                    return None, "%.0f %% of the district population lies in a hole of %d official units (spanning %d 2020 precincts, %d residents) that the district only partly covers (%.0f %%); the units cannot be apportioned inside it" % (100 * contrib[id(k)] / pop, k["nunits"], k["n20"], k["pop"], 100 * contrib[id(k)] / k["pop"])
        return [round(x) for x in v], "population-weighted; %.0f %% of the district population from hole components" % (100 * fromhole / pop)

VEST20 = {"New Mexico": ("/workspace/vest/nm_2020.zip", "nm_2020")}   # VEST 2020 (CC BY 4.0), Harvard Dataverse

def vest_estimate(S, g, path, base):
    """2020 cells whose app precinct file lacks polygons: population-weighted on the full VEST 2020 precinct layer,
    scaled per county and party to data/election2020.js"""
    from shapely.geometry import shape
    Z = zipfile.ZipFile(path)
    r = shapefile.Reader(shp=io.BytesIO(Z.read(base + ".shp")), dbf=io.BytesIO(Z.read(base + ".dbf")), shx=io.BytesIO(Z.read(base + ".shx")))
    G, V = [], []
    for sr in r.iterShapeRecords():
        d = sr.record.as_dict(); G.append(shape(sr.shape.__geo_interface__).buffer(0))
        V.append((d["COUNTYNAME"] + " County", d["G20PREDBID"], d["G20PRERTRU"], sum(v for k, v in d.items() if k.startswith("G20PRE"))))
    T = STRtree(G); Tb, P, W, C = S.B; gp = prep(g)
    ins = [i for i in Tb.query(g) if gp.contains(P[i])]; pop = sum(W[i] for i in ins)
    cs = collections.defaultdict(lambda: [0, 0, 0])
    for x in V:
        for i in range(3): cs[x[0]][i] += x[1 + i]
    sc = {}
    for c, (d, rp, t) in cs.items():
        o = S.E["2020"].get(S.st + "|" + c)
        if o and 0.5 <= (d + rp) / max(1, o[0] + o[1]) <= 1.1: sc[c] = (o[0] / max(1, d), o[1] / max(1, rp), max(0, o[2] - o[0] - o[1]) / max(1, t - d - rp) if t - d - rp > 0 else 0.0)
    of = {}; pp = collections.Counter()
    cand = {c for c in set(C[i] for i in ins)}
    for bi in range(len(P)):
        if C[bi] not in cand: continue
        for k in T.query(P[bi]):
            if G[k].contains(P[bi]): of[bi] = k; pp[k] += W[bi]; break
    v = [0.0, 0.0, 0.0]; placed = 0; n = set()
    for i in ins:
        k = of.get(i)
        if k is None or V[k][3] <= 0 or V[k][0] not in sc: continue
        f = W[i] / pp[k]; c, d, rp, t = V[k]; s = sc[c]; placed += W[i]; n.add(k)
        v[0] += f * d * s[0]; v[1] += f * rp * s[1]; v[2] += f * (d * s[0] + rp * s[1] + (t - d - rp) * s[2])
    if placed < 0.97 * pop: return None, "VEST 2020: population placed %.0f %%" % (100 * placed / pop), pop
    return [round(x) for x in v], "population-weighted on VEST 2020 precinct polygons (%d precincts)" % len(n), pop

def main():
    a = sys.argv[1:]; repo = a[0]; raw = a[a.index("--raw") + 1]; rep = a[a.index("--report") + 1]; fix = "--fix" in a
    p = os.path.join(repo, "v2/data/ussch.js"); s, i, j, rows = load(p)
    gid = {(r["state"], r["v2_name"]): r["geoid"] for r in csv.DictReader(open(os.path.join(repo, "data-v3/geo/schools.csv")))}
    S = {}; TG = {}; out = []; changed = 0
    for st, name, yr in TARGETS:
        rec = {"state": st, "name": name, "year": yr, "geoid": gid.get((st, name))}; YI = 3 if yr == "2024" else 4
        row = next(r for r in rows if r[0] == st and r[1] == name)
        if row[YI] is not None: rec.update(result="skip", why="no longer gray"); out.append(rec); continue
        f = FIPS[st]
        if f not in TG:
            TG[f] = {}
            for t in ("unsd", "elsd", "scsd"):
                z = os.path.join(raw, "tl_2024_%s_%s.zip" % (f, t))
                if os.path.exists(z): TG[f].update({x["GEOID"]: gg for x, gg in read_tiger(z)})
        g = TG[f].get(rec["geoid"])
        if g is None: rec.update(result="gray", why="no TIGER 2024 polygon"); out.append(rec); print(rec); continue
        if st not in S: S[st] = State(repo, raw, st)
        hrep = {}
        if yr == "2020" and st in VEST20: v, w, pop = vest_estimate(S[st], g, *VEST20[st])
        else: v, w, pop = S[st].estimate(g, yr, hrep)
        rec.update(pop2020=pop, how=w, counties=hrep)
        if not v: rec.update(result="gray", why=w)
        elif v[2] > PLAUS * pop: rec.update(result="gray", why="implausible: %d votes for %d residents" % (v[2], pop), rejected=v)
        else:
            o = row[4 if yr == "2024" else 3]
            if o and o[2] and not o[2] > PLAUS * pop:
                ratio = v[2] / o[2] if yr == "2024" else o[2] / v[2]
                if not (0.7 <= ratio <= 1.4 and abs(sh(v) - sh(o)) <= 0.12):
                    rec.update(result="gray", why="consistency rule failed vs other year %s (ratio %.2f, R share %.2f vs %.2f)" % (o, ratio, sh(v), sh(o)), rejected=v)
            if "result" not in rec:
                rec.update(result="estimate", value=v)
                if fix: row[YI] = v; setflag(row, yr, "estimate"); changed += 1
        out.append(rec); print({k: rec.get(k) for k in ("state", "name", "year", "result", "value", "pop2020", "why", "how")})
        for c, h in hrep.items(): print("   ", c, {k: h.get(k) for k in ("hole_pop2020", "county_pop2020", "hole_votes", "hole_2020_popw", "hole_turnout_ratio", "why")}, "missing:", list(h.get("missing_units", {}))[:8], "unmatched app:", h.get("app_rows_unmatched", [])[:4])
    if fix and changed: open(p, "w").write(s[:i] + json.dumps(rows, separators=(",", ":")) + s[j:])
    json.dump(out, open(rep, "w"), indent=1, ensure_ascii=False)
    print(collections.Counter(x["result"] for x in out))

if __name__ == "__main__":
    main()
