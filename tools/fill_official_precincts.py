#!/usr/bin/env python3
"""Recompute gray district values for one state from official precinct shapes + official precinct returns for the
counties whose precincts are missing or unusable in the app's precinct file (data/precincts<year>/<State>.js).
Nothing in root data/ is changed: the app's precinct rows for the replaced counties are swapped, in a temporary
copy only, for the official rows of a replacement file, and then the unchanged rules of the lane are applied:
 1. exact (no flag): the strict rule of tools/add_tiger_schools.py (every precinct overlapping by > 3 % lies >= 97 %
    inside, they cover >= 97 % of the district, touched counties' precinct totals within 0.5 % of official);
 2. otherwise the area-weighted estimate of tools/fill_gray.py (executed from that file: precinct votes shared by
    area, scaled per county and party to the official county totals in data/election<year>.js, >= 90 % usable cover,
    < 2 % failing counties), flagged ≈ ('e24' / 'e20' / 'est');
 3. otherwise the row stays gray and the reason is reported.
Only rows that are gray for the year (value null) are written, and only those named with --targets (layer:name,...)
or, with --all-gray, every gray row of the state in the layers given by --layers. With --recompute, the rows named in
--targets are recomputed even when they already have a value (for values built on a county the replacement corrects);
the old value is kept in the report.
Replacement file (JSON, built from the raw official downloads, kept outside the repo):
  {"state": S, "year": "2024", "counties": {"<v2 county name>": {"source": "...", "rows": [[precinct, dem, rep, total, <GeoJSON geometry, lon/lat>], ...],
   "not_located": {"<unit>": [dem, rep, total]}}}}
  'not_located' = official units with no geography (early voting, absentee, provisional, vote centres): they are
  not placed anywhere; the county scaling of rule 2 spreads them like fill_gray does for every state.
usage: fill_official_precincts.py <repo> <replacement.json> (--targets ussldl:057,... [--recompute] | --all-gray --layers ussch) --report OUT.json [--dry]
"""
import sys, os, json, tempfile, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shapely.geometry import shape
from add_tiger_schools import load_fill_gray, strict
from resimplify_towns import enc_geom

def main():
    a = sys.argv[1:]; dry = "--dry" in a; rec = "--recompute" in a
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    repo, rf = [x for x in a if not x.startswith("--") and x not in (opt("--targets"), opt("--report"), opt("--layers"))][:2]
    R = json.load(open(rf)); st = R["state"]; year = R.get("year", "2024"); YI = 3 if year == "2024" else 4
    fn = st.replace(" ", "_") + ".js"
    src = os.path.join(repo, "data", "precincts" + year, fn)
    t = open(src).read(); i = t.index(","); j = t.rindex(");")
    head, body = t[:i + 1], json.loads("[" + t[i + 1:j] + "]")
    rows, credit = body[0], (body[1] if len(body) > 1 else {})
    rep_c = set(R["counties"])
    new = [r for r in rows if r[0] not in rep_c]
    for c, v in R["counties"].items():
        for nm, d, rp, tot, geom in v["rows"]:
            enc = enc_geom(shape(geom).buffer(0), 10000)
            if enc: new.append([c, nm, d, rp, tot, enc])
    tmp = tempfile.mkdtemp(prefix="offprec_")
    os.makedirs(os.path.join(tmp, "data", "precincts" + year))
    os.symlink(os.path.abspath(os.path.join(repo, "data", "election" + year + ".js")), os.path.join(tmp, "data", "election" + year + ".js"))
    open(os.path.join(tmp, "data", "precincts" + year, fn), "w").write(head + json.dumps(new, separators=(",", ":")) + "," + json.dumps(credit) + t[j:])
    ns = load_fill_gray(repo, year); ns["repo"] = tmp; ns["PC"].clear()
    _, _, _, sc, _, _ = ns["prec"](st)
    cty = {}
    for c in rep_c:
        s = [sum(r[k] for r in new if r[0] == c) for k in (2, 3, 4)]; o = ns["E"].get(st + "|" + c)
        cty[c] = {"located_sum": s, "official": o, "located_share_of_official_dem_rep": round((s[0] + s[1]) / max(1, o[0] + o[1]), 4) if o else None,
                  "usable": c in sc, "units": len(R["counties"][c]["rows"]), "not_located": R["counties"][c].get("not_located")}
    targets = None
    if opt("--targets"):
        targets = collections.defaultdict(set)
        for x in opt("--targets").split(","): l, n = x.split(":", 1); targets[l].add(n)
    layers = list(targets) if targets else opt("--layers").split(",")
    out = {"state": st, "year": year, "replacement": os.path.abspath(rf), "counties": cty, "rows": []}
    for L in layers:
        p = os.path.join(repo, "v2", "data", L + ".js"); s = open(p).read(); i = s.index("[", s.index("(")); j = s.rindex("]") + 1
        d = json.loads(s[i:j]); ch = 0
        for r in d:
            if r[0] != st or (targets and r[1] not in targets[L]): continue
            if len(r) > YI and r[YI] is not None and not (rec and targets): continue
            D = ns["mp"](r[2], 1000)
            v, w = strict(ns, st, D, year); how = "exact"
            if not v:
                v, w2 = ns["estimate"](st, D); how = "estimate" if v else "gray"; w = "exact: %s; estimate: %s" % (w, w2) if not v else "exact: " + w
            old = list(r)
            if not v and rec: how = "unchanged (no rule applies; old value kept)"
            if v:
                while len(r) < 5: r.append(None)
                r[YI] = v
                fl = r[5] if len(r) > 5 else None
                if how == "estimate":
                    nf = {"2024": {None: "e24", "cty": "e24", "e20": "est", "e24": "e24", "est": "est"}, "2020": {None: "e20", "cty": "e20", "e24": "est", "e20": "e20", "est": "est"}}[year].get(fl, "est")
                    r[5:] = [nf]
                ch += 1
            out["rows"].append({"layer": L, "name": r[1], "method": how, "value": v, "value_before": old[YI] if len(old) > YI else None, "flag_before": old[5] if len(old) > 5 else None, "flag_after": r[5] if len(r) > 5 else None, "why": w})
        if ch and not dry: open(p, "w").write(s[:i] + json.dumps(d, separators=(",", ":")) + s[j:])
        print(L, "changed", ch)
    json.dump(out, open(opt("--report"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, ensure_ascii=False)[:1500])
    for x in out["rows"]: print(x["layer"], x["name"], x["method"], x["value"], x["flag_after"], (x["why"] or "")[:160])

if __name__ == "__main__":
    main()
