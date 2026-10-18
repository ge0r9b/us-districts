#!/usr/bin/env python3
"""Gray batch 2, KY retry: Somerset ISD, East Bernstadt ISD and its Laurel County part (2024).

The app's 2024 Kentucky precinct file leaves 62 % (Pulaski) / 51 % (Laurel) of the county population in no precinct.
Here the two counties' precinct set is rebuilt from official sources only:
  shapes : Kentucky State Board of Elections / Division of Geographic Information, 'SBE_Voting_Precinct_Boundaries'
           (kygisserver.ky.gov .../Temp_Services/SBE_VotingPrecinctboundaries/FeatureServer/0), queried per county,
           outSR 4326; raw files + sha256 in inst-raw/ky_sbe/.
  votes  : MEDSL 2024-elections-official KY (CC0, from the official county canvass), US PRESIDENT, by precinct code.
Checks: the official precinct codes and the SBE codes are the same set, one to one; the SBE polygons hold >= 99 % of
the county's 2020 population; every precinct passes votes <= 90 % of its 2020 population and the 2020 consistency
rule against the app's 2020 precinct file on the same blocks (turnout ratio 0.7-1.4 after spreading countywide votes
pro rata, Republican share within 12 points). The SBE layer is the current one (last edits Feb 2026); the identical
code set and the per-precinct 2020 checks are what tie it to Nov 2024. Then the district rules of inst_gray2_holes.py.
The stored 2020 figures of these rows were area-weighted (e20) and far too low (Somerset 278 votes for 9,536 residents);
where a population-weighted recomputation on the app's 2020 precinct file differs beyond the 0.7-1.4 band, it replaces
the 2020 figure (≈) before the 2024 consistency test.
usage: inst_gray2_ky.py <repo> --raw DIR --report OUT.json [--fix]
"""
import sys, os, csv, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inst_gray2_holes as H
from recheck_identical import load, setflag
from add_tiger_schools import read_tiger
from shapely.geometry import shape
from shapely.strtree import STRtree

SBE = "/workspace/w/inst-raw/ky_sbe/ky_%s.geojson"
CTY = {"199": ("Pulaski County", "PULASKI"), "125": ("Laurel County", "LAUREL")}
TARGETS = ["Somerset Independent School District", "East Bernstadt Independent School District", "Laurel County School District for East Bernstadt ISD"]

def main():
    a = sys.argv[1:]; repo = a[0]; raw = a[a.index("--raw") + 1]; rep = a[a.index("--report") + 1]; fix = "--fix" in a
    S = H.State(repo, raw, "Kentucky"); W = S.B[2]; out = {"counties": {}, "districts": []}; ok = True
    R24 = S.rows["2024"]; of = S.of["2024"]
    for cf, (cn, mc) in CTY.items():
        F = json.load(open(SBE % cf))["features"]
        U, fn = H.official_units("Kentucky", mc)
        rep_c = {"sbe_precincts": len(F), "official_units": len(U)}; out["counties"][cn] = rep_c
        codes = {f["properties"]["PrecinctCode"]: f for f in F}
        if set(codes) != set(U): rep_c["fail"] = "code sets differ: %s" % sorted(set(codes) ^ set(U)); ok = False; continue
        # drop the app's rows for the county, add SBE rows
        keep = [i for i, r in enumerate(R24) if r[0] != cn]
        base = len(R24); G = []
        for code in sorted(codes):
            g = shape(codes[code]["geometry"]).buffer(0); v = U[code]
            R24.append([cn, "%s %s" % (code, codes[code]["properties"]["PrecinctName"]), v[0], v[1], v[2], None]); G.append(g)
        T = STRtree(G); blocks = S.cfips["21" + cf]; placed = 0
        for b in blocks:
            of.pop(b, None)
            for k in T.query(S.B[1][b]):
                if G[k].contains(S.B[1][b]): of[b] = base + k; placed += W[b]; break
        for i, r in enumerate(R24[:base]):
            if r[0] == cn: r[0] = cn + " (app row, replaced)"
        cpop = sum(W[b] for b in blocks); rep_c["pop_in_sbe_polygons"] = round(placed / cpop, 4)
        if placed < 0.99 * cpop: rep_c["fail"] = "SBE polygons hold %.1f %% of county population" % (100 * placed / cpop); ok = False
        # per-precinct checks vs 2020
        R20 = S.rows["2020"]; of20 = S.of["2020"]; ppw = collections.Counter()
        for b in blocks:
            if b in of20: ppw[of20[b]] += W[b]
        tot = [sum(U[c][i] for c in U) for i in range(3)]; o = S.E["2024"].get("Kentucky|" + cn)
        scale = o[2] / tot[2] if o and tot[2] else 1.0; rep_c["official_county_2024"] = o; rep_c["units_sum"] = tot
        prec = []
        for k, code in enumerate(sorted(codes)):
            bs = [b for b in blocks if of.get(b) == base + k]; pop = sum(W[b] for b in bs); v = U[code]
            w20 = [sum(R20[of20[b]][2 + i] * W[b] / ppw[of20[b]] for b in bs if b in of20 and R20[of20[b]][4] > 0) for i in range(3)]
            tr = v[2] * scale / w20[2] if w20[2] else 0
            good = pop > 0 and v[2] <= H.PLAUS * pop and 0.7 <= tr <= 1.4 and abs(H.sh(v) - H.sh(w20)) <= 0.12
            prec.append({"code": code, "name": codes[code]["properties"]["PrecinctName"], "pop2020": pop, "votes2024": v, "popw2020": [round(x) for x in w20], "turnout_ratio_scaled": round(tr, 3), "ok": good})
        rep_c["precincts"] = prec; bad = [p["code"] for p in prec if not p["ok"]]
        rep_c["precincts_failing"] = bad
        print(cn, {k: v for k, v in rep_c.items() if k != "precincts"})
    p = os.path.join(repo, "v2/data/ussch.js"); s, i, j, rows = load(p)
    gid = {(r["state"], r["v2_name"]): r["geoid"] for r in csv.DictReader(open(os.path.join(repo, "data-v3/geo/schools.csv")))}
    TG = {}
    for t in ("unsd", "elsd", "scsd"):
        z = os.path.join(raw, "tl_2024_21_%s.zip" % t)
        if os.path.exists(z): TG.update({x["GEOID"]: gg for x, gg in read_tiger(z)})
    changed = 0
    for name in TARGETS:
        row = next(r for r in rows if r[0] == "Kentucky" and r[1] == name); rec = {"name": name, "geoid": gid.get(("Kentucky", name))}
        g = TG[rec["geoid"]]; hrep = {}
        v, w, pop = S.estimate(g, "2024", hrep); rec.update(pop2020=pop, how=w)
        # precincts used by the district must have passed their checks
        Tb, P, Wt, C = S.B; from shapely.prepared import prep; gp = prep(g)
        used = {R24[of[b]][1].split()[0] for b in Tb.query(g) if gp.contains(P[b]) and b in of and R24[of[b]][0] in ("Pulaski County", "Laurel County")}
        failing = [c for cr in out["counties"].values() for c in cr.get("precincts_failing", []) if c in used]
        # the stored 2020 figure: area-weighted (e20); recompute population-weighted on the app's 2020 precinct file and
        # replace it when the two disagree beyond the turnout band (Somerset 278 votes for 9,536 residents)
        v20, w20, _ = S.estimate(g, "2020", {}); rec["popw2020"] = v20; rec["stored2020"] = row[4]
        if v20 and v20[2] <= H.PLAUS * pop and row[4] and row[4][2] and not (0.7 <= row[4][2] / v20[2] <= 1.4):
            rec["replace2020"] = v20
            if fix: row[4] = v20; setflag(row, "2020", "estimate"); changed += 1
            else: row[4] = v20
        if not ok: rec.update(result="gray", why="county checks failed")
        elif failing: rec.update(result="gray", why="uses precincts failing the 2020 checks: %s" % failing)
        elif not v: rec.update(result="gray", why=w)
        elif v[2] > H.PLAUS * pop: rec.update(result="gray", why="implausible: %d votes for %d residents" % (v[2], pop))
        else:
            o = row[4]; ratio = v[2] / o[2] if o and o[2] else None
            if o and o[2] and not (0.7 <= ratio <= 1.4 and abs(H.sh(v) - H.sh(o)) <= 0.12):
                rec.update(result="gray", why="consistency rule failed vs 2020 %s (ratio %.2f, R share %.2f vs %.2f)" % (o, ratio, H.sh(v), H.sh(o)), rejected=v)
            else:
                rec.update(result="estimate", value=v, other_year=o)
                if fix and row[3] is None: row[3] = v; setflag(row, "2024", "estimate"); changed += 1
        out["districts"].append(rec); print(rec)
    if fix and changed: open(p, "w").write(s[:i] + json.dumps(rows, separators=(",", ":")) + s[j:])
    json.dump(out, open(rep, "w"), indent=1, ensure_ascii=False)

if __name__ == "__main__":
    main()
