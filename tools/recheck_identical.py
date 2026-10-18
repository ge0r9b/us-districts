#!/usr/bin/env python3
"""Find pairs of different v2 district rows (same layer, state and year) with identical [dem, rep, total] figures and
recompute each row on its own geometry from the app's precinct files (data/precincts<year>/<State>.js):
exact by the strict school rule of tools/add_tiger_schools.py (precincts >= 97 % inside, >= 97 % cover, touched
counties within 0.5 % of official), else the area-weighted estimate of tools/fill_gray.py (flag ≈), else none.
Pairs whose shapes overlap (IoU >= 0.9: e.g. an elementary and a high-school district on the same territory) are
legitimately identical and are only listed.
--fix applies the recomputed figure to a row of a disjoint pair (IoU < 0.05) whose stored figure differs from its own
recomputation by more than --tol (default 3 %) of the total, or grays it when nothing can be computed;
flags are updated ('e24'/'e20'/'est' when estimated, cleared for an exact year).
usage: recheck_identical.py <repo> --report OUT.json [--fix] [--tol 0.03]
"""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coverage_audit as A
from add_tiger_schools import load_fill_gray, strict
from v3_geoids import poly

# Cases where the generic rule would be wrong, with the reason (checked by hand, Oct 18, 2026):
OVERRIDES = {
  ("schools", "Kentucky", "Graves County School District", "2020"): ("gray", "VEST 2020 reports Graves County as one county-wide unit (17,019 votes); the Mayfield ISD part cannot be separated, and area-weighting would give the city of Mayfield ~160 votes"),
  ("schools", "Kentucky", "Mayfield Independent School District", "2020"): ("gray", "same county-wide 2020 unit; the stored figure was the whole county"),
  ("schools", "Vermont", "Averill School District", "2020"): ("gray", "Averill (unorganized, about 24 residents) is reported with Canaan as one unit 'Canaan/Averill' (498); no official split, same rule as the combined Maine units and the 2024 Averill row"),
  ("schools", "Vermont", "Canaan School District", "2020"): ("keep", "= the official combined 'Canaan/Averill' unit (includes Averill's few voters)"),
}

FILES = [("ushouse", "uscd.js"), ("senate", "ussldu.js"), ("statehouse", "ussldl.js"), ("schools", "ussch.js")]

def load(p):
    s = open(p).read(); i = s.index("[", s.index("(")); j = s.rindex("]") + 1
    return s, i, j, json.loads(s[i:j])

def setflag(r, yr, how):
    fl = r[5] if len(r) > 5 else None
    e24 = fl in ("e24", "est"); e20 = fl in ("e20", "est")
    if yr == "2024": e24 = how == "estimate"
    else: e20 = how == "estimate"
    nf = "est" if e24 and e20 else "e24" if e24 else "e20" if e20 else None
    while len(r) < 5: r.append(None)
    r[5:] = [nf] if nf else []

def main():
    a = sys.argv[1:]; repo = a[0]; rep = a[a.index("--report") + 1]; fix = "--fix" in a
    tol = float(a[a.index("--tol") + 1]) if "--tol" in a else 0.03
    NS = {y: load_fill_gray(repo, y) for y in ("2024", "2020")}
    report = []
    for ly, fn in FILES:
        p = os.path.join(repo, "v2", "data", fn); s, i, j, rows = load(p); changed = False
        for yi, yr in ((3, "2024"), (4, "2020")):
            g = collections.defaultdict(list)
            for k, r in enumerate(rows):
                v = r[yi] if len(r) > yi else None
                if v and v[2] > 0: g[(r[0], tuple(v))].append(k)
            for (st, v), ks in g.items():
                if len(ks) < 2: continue
                P = {k: poly(rows[k][2]) for k in ks}
                for x in range(len(ks)):
                    for y in range(x + 1, len(ks)):
                        ka, kb = ks[x], ks[y]
                        iou = P[ka].intersection(P[kb]).area / P[ka].union(P[kb]).area
                        e = {"layer": ly, "year": yr, "state": st, "rows": [ka, kb], "names": [rows[ka][1], rows[kb][1]], "value": list(v), "iou": round(iou, 3)}
                        if iou >= 0.9: e["verdict"] = "same territory (legit)"; report.append(e); continue
                        rc = []
                        for k in (ka, kb):
                            val, why = strict(NS[yr], st, P[k], yr); how = "exact"
                            if not val:
                                val, w2 = NS[yr]["estimate"](st, P[k]) if st != "Alaska" else (None, "Alaska: area-weighting rejected (build 1533)")
                                how = "estimate" if val else "none"; why = "%s; %s" % (why, w2) if not val else why
                            dev = abs(val[2] - v[2]) / v[2] if val else None
                            rc.append({"row": k, "recomputed": val, "method": how, "why": why, "dev": round(dev, 3) if dev is not None else None})
                        e["recomputed"] = rc
                        if iou < 0.05:
                            e["verdict"] = "disjoint: copy error"
                            for c in rc:
                                r = rows[c["row"]]; act = None
                                ov = OVERRIDES.get((ly, st, r[1], yr))
                                if ov:
                                    c["action"] = "%s (override: %s)" % ov
                                    if fix and ov[0] == "gray": r[yi] = None; setflag(r, yr, "gray"); changed = True
                                    continue
                                if c["dev"] is not None and c["dev"] > tol:
                                    act = "set %s (%s)" % (c["recomputed"], c["method"])
                                    if fix: r[yi] = c["recomputed"]; setflag(r, yr, c["method"]); changed = True
                                elif c["dev"] is None:
                                    act = "gray (cannot be computed)"
                                    if fix: r[yi] = None; setflag(r, yr, "gray"); changed = True
                                c["action"] = act or "keep (matches its own recomputation)"
                        else:
                            e["verdict"] = "partial overlap: review"
                        report.append(e)
        if fix and changed: open(p, "w").write(s[:i] + json.dumps(rows, separators=(",", ":")) + s[j:])
    json.dump(report, open(rep, "w"), indent=1)
    c = collections.Counter(e["verdict"] for e in report); print(dict(c))
    for e in report:
        if e["verdict"] != "same territory (legit)":
            print(e["layer"], e["year"], e["state"], e["names"], e["value"], e["iou"], [(x["recomputed"], x["method"], x["dev"], x.get("action")) for x in e["recomputed"]])

if __name__ == "__main__":
    main()
