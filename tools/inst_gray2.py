#!/usr/bin/env python3
"""Gray batch 2 (institutions lane): try every remaining gray cell of ussch.js / ussldu.js / ussldl.js with the
batch-1 methods, outside Alaska (Alaska: tools/inst_ak_schools.py):
  1. strict exact rule on the app geometry (add_tiger_schools.strict: precincts >= 97 % inside, >= 97 % cover,
     touched counties within 0.5 % of official);
  2. population-weighted ≈ (tools/inst_pairs_check.PopW): Census 2020 block population inside the full-resolution
     TIGER 2024 polygon (by GEOID from data-v3/geo/<layer>.csv); each precinct of the app's file gives the share of
     its population inside, scaled per county to the official county totals; >= 97 % of the district's people
     must be in precincts with votes;
  checks: estimate <= 90 % of the 2020 population; 2020/2024 consistency (turnout ratio 0.7-1.4, R share within
  12 points) against the row's other-year figure (skipped only when that figure is itself > 90 % of population).
Every cell gets a result and a reason (district population, cover, failing check) in the report.
Excluded by ruling: LA 057, SD (2024), Maine 2024 combined units, Kalawao.
usage: inst_gray2.py <repo> --raw DIR --report OUT.json [--fix] [--only State,...]
"""
import sys, os, csv, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_tiger_schools import load_fill_gray, strict, read_tiger
from v3_geoids import poly
from recheck_identical import load, setflag
import inst_pairs_check as M

FIPS = {"Alabama": "01", "Arkansas": "05", "California": "06", "Colorado": "08", "Kentucky": "21", "Maine": "23", "Mississippi": "28",
        "Missouri": "29", "Montana": "30", "New Jersey": "34", "New Mexico": "35", "New York": "36", "Ohio": "39", "Oregon": "41",
        "Texas": "48", "Vermont": "50", "Wisconsin": "55", "Wyoming": "56"}
LAYERS = [("schools", "ussch.js", "schools.csv", ("unsd", "elsd", "scsd")), ("senate", "ussldu.js", "senate.csv", ("sldu",)), ("statehouse", "ussldl.js", "statehouse.csv", ("sldl",))]
PLAUS = 0.9
# hand-checked cases where the generic rule would be wrong (reason recorded in the report and COVERAGE.md)
SKIP = {
  ("schools", "Kentucky", "Graves County School District", "2020"): "VEST 2020 reports Graves County as one county-wide unit (17,019) that includes Mayfield ISD; the 'exact' county total is not the district (override in recheck_identical.py)",
  ("schools", "Vermont", "Averill School District", "2020"): "Averill (21 residents) is reported with Canaan as one official unit 'Canaan/Averill'; no official split (same ruling as Maine's combined units)",
  ("schools", "Texas", "Boys Ranch Independent School District", "2024"): "Boys Ranch is a residential children's ranch: most of its 120 residents are minors, so block population is not a proxy for voters and a population-weighted share would place adult votes on children; no separate polling unit",
  ("schools", "Texas", "Boys Ranch Independent School District", "2020"): "same as 2024",
}

def excluded(st, name, yr, layer):
    return (st == "Alaska") or (layer == "statehouse" and st == "Louisiana" and name == "057") or (st == "South Dakota" and yr == "2024") \
        or (st == "Maine" and yr == "2024")

def sh(v): return v[1] / (v[0] + v[1]) if v and v[0] + v[1] else 0

def main():
    a = sys.argv[1:]; repo = a[0]; raw = a[a.index("--raw") + 1]; rep = a[a.index("--report") + 1]; fix = "--fix" in a
    only = set(a[a.index("--only") + 1].split(",")) if "--only" in a else None
    NS = {}; BL = {}; PW = {}; TG = {}; out = []
    for layer, fn, gcsv, sets in LAYERS:
        p = os.path.join(repo, "v2/data", fn); s, i, j, rows = load(p)
        gid = {(r["state"], r["v2_name"]): r["geoid"] for r in csv.DictReader(open(os.path.join(repo, "data-v3/geo", gcsv)))}
        changed = 0
        for r in rows:
            st = r[0]
            for yr, YI in (("2024", 3), ("2020", 4)):
                if (r[YI] if len(r) > YI else None) is not None or excluded(st, r[1], yr, layer): continue
                if only and st not in only: continue
                rec = {"layer": layer, "state": st, "name": r[1], "year": yr, "geoid": gid.get((st, r[1]))}
                if (layer, st, r[1], yr) in SKIP: rec.update(result="gray", why="override: " + SKIP[(layer, st, r[1], yr)]); out.append(rec); print(rec); continue
                if yr not in NS: NS[yr] = load_fill_gray(repo, yr)
                ex, why = strict(NS[yr], st, poly(r[2]), yr)
                if ex: rec.update(result="exact", value=ex)
                else:
                    rec["strict_fail"] = why
                    f = FIPS.get(st); g = None
                    if f:
                        for t in sets:
                            z = os.path.join(raw, "tl_2024_%s_%s.zip" % (f, t))
                            if (f, t) not in TG and os.path.exists(z): TG[(f, t)] = {x["GEOID"]: gg for x, gg in read_tiger(z)}
                            g = g or TG.get((f, t), {}).get(rec["geoid"])
                    bz = os.path.join(raw, "tl_2020_%s_tabblock20.zip" % f) if f else None
                    if g is None or not bz or not os.path.exists(bz): rec.update(result="gray", why="no TIGER polygon or block file"); out.append(rec); print(rec); continue
                    if st not in BL: BL[st] = M.blocks(raw, f)
                    ins = M.popset(BL[st], g); pop = sum(BL[st][2][x] for x in ins); rec["pop2020"] = pop
                    if pop == 0: rec.update(result="gray", why="no residents in the 2020 Census (0 population): no voters, no source can exist"); out.append(rec); print(rec); continue
                    P = NS[yr]["prec"](st)
                    if not P or P[0] is None: rec.update(result="gray", why="no %s precinct file for the state" % yr); out.append(rec); print(rec); continue
                    if (st, yr) not in PW: PW[(st, yr)] = M.PopW(BL[st], *P[:4])
                    v, w = PW[(st, yr)].est(ins); rec["popw"] = w
                    if not v: rec.update(result="gray", why="%s; %s" % (why, w))
                    elif v[2] > PLAUS * pop: rec.update(result="gray", why="implausible: %d votes for %d residents" % (v[2], pop), rejected=v)
                    else: rec.update(result="estimate", value=v)
                if rec.get("value"):
                    oy, OI = ("2020", 4) if yr == "2024" else ("2024", 3); o = r[OI] if len(r) > OI else None; v = rec["value"]
                    pop = rec.get("pop2020")
                    if o and o[2] and not (pop and o[2] > PLAUS * pop):
                        ratio = v[2] / o[2] if yr == "2024" else o[2] / v[2]
                        if not (0.7 <= ratio <= 1.4 and abs(sh(v) - sh(o)) <= 0.12):
                            rec.update(result="gray", why="consistency rule failed vs %s %s (ratio %.2f, R share %.2f vs %.2f)" % (oy, o, ratio, sh(v), sh(o)), rejected=v); v = None
                    if v and fix: r[YI] = v; setflag(r, yr, rec["result"]); changed += 1
                out.append(rec); print({k: rec.get(k) for k in ("layer", "state", "name", "year", "result", "value", "pop2020", "why", "strict_fail")})
        if fix and changed: open(p, "w").write(s[:i] + json.dumps(rows, separators=(",", ":")) + s[j:])
    json.dump(out, open(rep, "w"), indent=1, ensure_ascii=False)
    print(collections.Counter((x["layer"], x["year"], x["result"]) for x in out))

if __name__ == "__main__":
    main()
