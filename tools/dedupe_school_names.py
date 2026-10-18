#!/usr/bin/env python3
"""Make every v2/data/ussch.js school row name unique within its state (the app keys list rows by state|name,
so same-named districts showed the last one's figures). Every row of a same-name group is renamed
"<TIGER name> (<county>)" where <county> is the county holding most of the district's area (from
v2/data/uscounties.js, " County"/" Parish" dropped); when that county does not separate it from another row of the
group, "(<last 5 digits of the TIGER GEOID>)" is used instead. Geometry, results and ≈ flags stay on their own row
(only the name changes). GEOIDs come from data-v3/geo/schools.csv (tools/v3_geoids.py, matched by internal point).
Writes data-v3/geo/v2_name_collisions.csv (old name, new name, GEOID, ...) and updates data-v3/geo/schools.csv.
usage: dedupe_school_names.py <repo> [--dry]
"""
import sys, os, csv, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coverage_audit as A
from v3_geoids import poly
from shapely.strtree import STRtree

def main():
    repo = sys.argv[1]; dry = "--dry" in sys.argv
    p = os.path.join(repo, "v2", "data", "ussch.js")
    s = open(p).read(); i = s.index("[", s.index("(")); j = s.rindex("]") + 1
    rows = json.loads(s[i:j])
    G = {r["row"]: r for r in csv.DictReader(open(os.path.join(repo, "data-v3", "geo", "schools.csv")))}
    old_coll = {}
    oc = os.path.join(repo, "data-v3", "geo", "v2_name_collisions.csv")
    if os.path.exists(oc):
        for r in csv.DictReader(open(oc)):
            if "shadowed_geoid" in r: old_coll[r["shadowed_geoid"]] = r
    grp = collections.defaultdict(list)
    for k, r in enumerate(rows): grp[(r[0], r[1])].append(k)
    dup = {key: ks for key, ks in grp.items() if len(ks) > 1}
    C = [c for c in A.jsargs(os.path.join(repo, "v2", "data", "uscounties.js"), r"__uscty\(")[0]]
    CG = {}
    for c in C: CG.setdefault(c[0], []).append((c[1], poly(c[2])))
    trees = {st: STRtree([g for _, g in v]) for st, v in CG.items()}
    def county(st, enc):
        D = poly(enc); best = None; ba = 0
        for t in trees[st].query(D):
            nm, g = CG[st][t]
            try: a = g.intersection(D).area
            except Exception: a = 0
            if a > ba: ba, best = a, nm
        return best, (ba / D.area if D.area else 0)
    names = collections.defaultdict(set)
    for r in rows: names[r[0]].add(r[1])
    out = []; renames = {}
    for (st, nm), ks in sorted(dup.items()):
        info = []
        for k in ks:
            cn, share = county(st, rows[k][2]); info.append((k, cn, share))
        cc = collections.Counter(cn for _, cn, _ in info)
        for k, cn, share in info:
            geoid = G[str(k)]["geoid"]
            short = cn.replace(" County", "").replace(" Parish", "") if cn else None
            tag = short if short and cc[cn] == 1 else geoid[-5:]
            new = "%s (%s)" % (nm, tag)
            assert new not in names[st], new
            names[st].add(new); renames[k] = new
            last = k == ks[-1]
            prev = old_coll.get(geoid)
            out.append([st, nm, new, geoid, cn, round(share, 3), k, len(ks), "no" if last else "yes",
                        (prev or {}).get("wrong_2024", "no" if last else ""), (prev or {}).get("wrong_2020", "no" if last else ""), (prev or {}).get("wrong_est_flag", "no" if last else "")])
    for k, new in renames.items(): rows[k][1] = new
    # every name now unique within its state
    cnt = collections.Counter((r[0], r[1]) for r in rows); assert max(cnt.values()) == 1
    print("groups", len(dup), "rows renamed", len(renames), "shadowed before", sum(1 for o in out if o[8] == "yes"))
    if dry: return
    open(p, "w").write(s[:i] + json.dumps(rows, separators=(",", ":")) + s[j:])
    with open(oc, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["state", "old_name", "new_name", "geoid", "county", "county_area_share", "row", "rows_in_group",
                    "showed_other_row_figures_before", "wrong_2024_before", "wrong_2020_before", "wrong_est_flag_before"])
        w.writerows(out)
    sc = os.path.join(repo, "data-v3", "geo", "schools.csv")
    R = list(csv.DictReader(open(sc)))
    for r in R:
        if r["row"].isdigit() and int(r["row"]) in renames: r["v2_name"] = renames[int(r["row"])]
    with open(sc, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(R[0].keys())); w.writeheader(); w.writerows(R)

if __name__ == "__main__":
    main()
