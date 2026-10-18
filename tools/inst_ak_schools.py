#!/usr/bin/env python3
"""Fix 4 (institutions lane): gray Alaska school districts from the app's official Alaska precinct files, placed by
Census 2020 block POPULATION instead of area (build 1533 rejected area-weighting for Alaska because a town sits inside
a huge, nearly empty rural precinct).

Rule (per district and year, only rows that are gray for that year):
  district polygon = TIGER 2024 UNSD (full resolution, joined by GEOID from data-v3/geo/schools.csv);
  population = Census 2020 P.L. 94-171 block POP20 (tl_2020_02_tabblock20, internal points, public domain);
  every precinct holding > 3 % of its population inside the district must hold >= 97 % of its population inside it,
  and those precincts must hold >= 97 % of the district's population; the value is then the sum of those precincts.
  Flag ≈ (e24 / e20): the precinct figures themselves carry absentee / early / question ballots that the Division of
  Elections reports by House district and that were allocated to precincts (2024: the app's allocation, see
  data/precincts2024/Alaska.js credit; 2020: VEST's), so the district figure is not an exact official number.
  Otherwise the row stays gray, with the measured shares as the reason.
Precincts: data/precincts2024/Alaska.js (Alaska Division of Elections official 2024 results by precinct and precinct
boundaries) and data/precincts2020/Alaska.js (VEST 2020, CC BY 4.0). Root data/ is read only.
Rows that already carry an ≈ value for the year are re-tested; when the rule passes the ≈ value is replaced by the
precinct sum (the old ≈ figures came from area-weighting, which build 1533 found misleading for Alaska). Rows with
exact values are only reported (--all), never overwritten.
usage: inst_ak_schools.py <repo> --raw DIR --report OUT.json [--all] [--gray-implausible] [--write]
"""
import sys, os, io, csv, json, zipfile, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coverage_audit as ca
import shapefile
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from shapely.strtree import STRtree
from shapely.prepared import prep

def mp(enc, S=10000):
    ps = []
    for rg in enc:
        rr = []
        for f in rg:
            o = []; x = y = 0
            for k in range(0, len(f) - 1, 2): x += f[k]; y += f[k + 1]; o.append((x / S, y / S))
            if len(o) >= 3: rr.append(o)
        if rr: ps.append(Polygon(rr[0], rr[1:]))
    g = MultiPolygon(ps); return g if g.is_valid else g.buffer(0)

def zshp(z):
    Z = zipfile.ZipFile(z); b = [n for n in Z.namelist() if n.endswith(".shp")][0][:-4]
    return shapefile.Reader(shp=io.BytesIO(Z.read(b + ".shp")), dbf=io.BytesIO(Z.read(b + ".dbf")), shx=io.BytesIO(Z.read(b + ".shx")))

def main():
    a = sys.argv[1:]; repo = a[0]; raw = a[a.index("--raw") + 1]; rep = a[a.index("--report") + 1]; write = "--write" in a
    global ALL, GRAY_IMPL; ALL = "--all" in a; GRAY_IMPL = "--gray-implausible" in a
    gid = {r["v2_name"]: r["geoid"] for r in csv.DictReader(open(os.path.join(repo, "data-v3/geo/schools.csv"))) if r["state"] == "Alaska"}
    U = {}
    r = zshp(os.path.join(raw, "tl_2024_02_unsd.zip"))
    for s in r.iterShapeRecords(): U[s.record.as_dict()["GEOID"]] = shape(s.shape.__geo_interface__).buffer(0)
    B = []
    r = zshp(os.path.join(raw, "tl_2020_02_tabblock20.zip"))
    for rec in r.iterRecords(fields=["POP20", "INTPTLAT20", "INTPTLON20"]):
        d = rec.as_dict()
        if d["POP20"] > 0: B.append((Point(float(d["INTPTLON20"]), float(d["INTPTLAT20"])), d["POP20"]))
    bt = STRtree([p for p, _ in B])
    p = os.path.join(repo, "v2/data/ussch.js"); s = open(p).read(); i = s.index("[", s.index("(")); j = s.rindex("]") + 1; D = json.loads(s[i:j])
    out = []; ch = 0
    for yr, YI in (("2024", 3), ("2020", 4)):
        P = [(x[1], x[2], x[3], x[4], mp(x[-1])) for x in ca.jsargs(os.path.join(repo, "data/precincts%s/Alaska.js" % yr), r"__prec\(")[1]]
        pt = STRtree([q[4] for q in P])
        # population of every precinct (each block point to the precinct containing it)
        ppop = collections.Counter(); bprec = {}
        for bi, (pt_, pop) in enumerate(B):
            for k in pt.query(pt_):
                if P[k][4].contains(pt_): ppop[k] += pop; bprec[bi] = k; break
        for row in D:
            if row[0] != "Alaska": continue
            fl = row[5] if len(row) > 5 else None
            cur = row[YI] if len(row) > YI else None
            cur_est = cur is not None and (fl == "est" or fl == ("e24" if yr == "2024" else "e20"))
            if cur is not None and not (ALL or cur_est): continue
            g = U.get(gid.get(row[1]))
            if g is None: out.append({"year": yr, "name": row[1], "result": "gray", "why": "no TIGER polygon"}); continue
            gp = prep(g); inside = collections.Counter(); dpop = 0; unplaced = 0
            for bi in pt_idx(bt, g):
                pt_, pop = B[bi]
                if not gp.contains(pt_): continue
                dpop += pop
                if bi in bprec: inside[bprec[bi]] += pop
                else: unplaced += pop
            touched = {k: (inside[k], ppop[k]) for k in inside if inside[k] > 0.03 * ppop[k]}
            bad = {P[k][0]: round(v / t, 3) for k, (v, t) in touched.items() if v < 0.97 * t}
            cov = sum(v for v, _ in touched.values()) / dpop if dpop else 0
            info = {"year": yr, "name": row[1], "current": cur, "current_flag": fl, "geoid": gid.get(row[1]), "district_pop2020": dpop, "pop_not_in_any_precinct": unplaced,
                    "precincts": {P[k][0]: {"pop_inside": v, "pop_total": t, "votes": P[k][1:4]} for k, (v, t) in touched.items()}, "pop_cover": round(cov, 4)}
            if dpop and not bad and cov >= 0.97:
                v = [sum(P[k][n] for k in touched) for n in (1, 2, 3)]
                info.update(result="estimate", value=v)
                if cur is not None and not cur_est:   # exact row: report only, never overwrite
                    info["result"] = "check_exact_row" if v != cur else "matches_exact_row"; out.append(info); print(yr, row[1], info["result"], v, cur); continue
                if cur == v:
                    info["result"] = "unchanged"; out.append(info); print(yr, row[1], "unchanged", v); continue
                info["result"] = "estimate" if cur is None else "replace_estimate"
                if cur is not None and abs(v[2] - cur[2]) <= 0.03 * cur[2] and abs(sh(v) - sh(cur)) <= 0.02:
                    info["result"] = "within_3pct_kept"; CONF.add((row[1], yr)); out.append(info); print(yr, row[1], "within 3 %, kept", cur, v); continue
                PLAN[(row[1], yr)] = v
            else:
                info.update(result="gray" if cur is None else "keep_current", why=("no 2020 population inside" if not dpop else ("precincts split: %s" % bad if bad else "population cover %.0f %% < 97 %%" % (100 * cov))))
            info["_row"] = row; out.append(info)
            print(yr, row[1], info["result"], info.get("value"), info.get("why", ""), {k: (x["pop_inside"], x["pop_total"]) for k, x in info["precincts"].items()})
    # second pass: 2020<->2024 consistency (turnout ratio 0.7-1.4, R share within 12 points) against the other year's
    # final value; a planned value failing it is not written. Existing ≈ values with more votes than the district's
    # whole 2020 population are not credible and are grayed (Alaska rolls run high: Skagway, Denali reach ~80 %, and
    # match their precinct sums, so the bar is 100 %); values confirmed by a precinct sum within 3 % are exempt.
    rows = {r[1]: r for r in D if r[0] == "Alaska"}; pop = {}
    for x in out:
        if "district_pop2020" in x: pop[x["name"]] = x["district_pop2020"]
    def final(n, yr):
        if (n, yr) in PLAN: return PLAN[(n, yr)]
        r_ = rows[n]; YI = 3 if yr == "2024" else 4; return r_[YI] if len(r_) > YI else None
    dec = {}
    for (n, yr), v in PLAN.items():
        o = final(n, "2020" if yr == "2024" else "2024")
        ok = o is None or (0.7 <= (v[2] / o[2] if yr == "2024" else o[2] / v[2]) <= 1.4 and abs(sh(v) - sh(o)) <= 0.12)
        dec[(n, yr)] = v if ok else None
    for (n, yr), v in dec.items():
        if v is None: del PLAN[(n, yr)]
    changes = []
    for n, r_ in rows.items():
        for yr, YI in (("2024", 3), ("2020", 4)):
            fl = r_[5] if len(r_) > 5 else None
            cur = r_[YI] if len(r_) > YI else None
            isest = cur is not None and fl in ("est", "e24" if yr == "2024" else "e20")
            if (n, yr) in PLAN: changes.append((n, yr, cur, PLAN[(n, yr)], "precinct sum (population rule)"))
            elif (n, yr) in dec: changes.append((n, yr, cur, cur, "precinct sum failed 2020/2024 consistency; not written"))
            if GRAY_IMPL and (n, yr) not in PLAN and (n, yr) not in CONF and isest and n in pop and cur[2] > pop[n]:
                changes.append((n, yr, cur, None, "≈ value has more votes than the district's whole 2020 population (%d); grayed" % pop[n]))
    for n, yr, cur, new, why in changes:
        print("CHANGE", yr, n, cur, "->", new, why)
        if not write or new is cur: continue
        r_ = rows[n]; YI = 3 if yr == "2024" else 4
        while len(r_) < 5: r_.append(None)
        fl = r_[5] if len(r_) > 5 else None
        e = {"2024": fl in ("e24", "est") and r_[3] is not None, "2020": fl in ("e20", "est") and r_[4] is not None}
        r_[YI] = new; e[yr] = new is not None
        nf = "est" if e["2024"] and e["2020"] else "e24" if e["2024"] else "e20" if e["2020"] else None
        r_[5:] = [nf] if nf else []
        ch += 1
    for x in out: x.pop("_row", None)
    out.append({"changes": [{"name": n, "year": yr, "before": c, "after": w, "why": y} for n, yr, c, w, y in changes]})
    if write and ch: open(p, "w").write(s[:i] + json.dumps(D, separators=(",", ":")) + s[j:])
    json.dump(out, open(rep, "w"), indent=1, ensure_ascii=False)

PLAN = {}; CONF = set()
def sh(v): return v[1] / (v[0] + v[1]) if v[0] + v[1] else 0

def pt_idx(tree, g):
    return tree.query(g)

if __name__ == "__main__":
    main()
