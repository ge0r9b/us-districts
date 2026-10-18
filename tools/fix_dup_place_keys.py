#!/usr/bin/env python3
"""Q-G8: v1 place names used twice in one state (data/<State>.js "places", e.g. Ohio's two Oakwood villages) break the
v2 town layer: a v2/data/parts/<State>.js row with no geometry borrows the v1 place polygon by (state, name), and the app
takes the first one, so the second county showed the other place's polygon and figures. Fix, v2 only (root data/ untouched):
every parts row whose name is such a duplicate and that the app shows is renamed "<name> (<county without ' County'>)" (the convention of the
renamed school rows), and a row with no geometry gets, verbatim, the v1 polygon of the same-named place whose largest part
lies in its county (checked against TIGER 2024 places: the GEOID is the same-named incorporated place in that county).
Rows the app hides anyway (townsIn(): a v1 town row or an earlier parts row of that county has the same normT() name, which
then shows the right polygon) are left alone: renaming them would un-hide them and show the town twice.
Appends the renamed rows to data-v3/geo/v2_name_collisions.csv (row = index in the parts file).
usage: fix_dup_place_keys.py <repo> <tiger_dir> <tl_2024_us_county.zip> [--dry]
"""
import sys, os, json, collections, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coverage_audit as A
from town_gaps import recs, FIPS
from town_area_gaps import dec

def main():
    a = sys.argv[1:]; dry = "--dry" in a; repo, td, cz = [x for x in a if not x.startswith("--")][:3]
    st2f = {v: k for k, v in FIPS.items()}; C = collections.defaultdict(dict)
    for d, g in recs(cz): C[d["STATEFP"]][d["NAMELSAD"]] = g
    out = []
    for st in sorted(st2f):
        fn = st.replace(" ", "-") + ".js"; pv = os.path.join(repo, "data", fn); pp = os.path.join(repo, "v2", "data", "parts", fn)
        if not os.path.exists(pv) or not os.path.exists(pp): continue
        G1 = A.jsargs(pv, r"__geo\(")[1]; places = G1.get("places") or []
        from town_gaps import normT
        cnt = collections.Counter(p[1] for p in places); dup = {n for n, c in cnt.items() if c > 1}
        if not dup: continue
        s = open(pp).read(); i = s.index("[", s.index("(")); j = s.rindex("]") + 1; parts = json.loads(s[i:j])
        sf = st2f[st]; TP = [(d, g) for d, g in recs(os.path.join(td, "tl_2024_%s_place.zip" % sf)) if d["NAMELSAD"] in dup]
        grp = collections.Counter(p[1] for p in parts if p[1] in dup)
        seen = collections.defaultdict(set); hidden = set()
        for t in G1.get("towns") or []: seen[t[1]].add(normT(t[2]))
        for k, p in enumerate(parts):
            if normT(p[1]) in seen[p[0]]: hidden.add(k)
            else: seen[p[0]].add(normT(p[1]))
        for k, p in enumerate(parts):
            if p[1] not in dup: continue
            if k in hidden: print(st, k, p[0], p[1], "hidden by a same-name row, left alone"); continue
            cg = C[sf][p[0]]; old = p[1]
            cand = [(dec(q[-1]).intersection(cg).area / dec(q[-1]).area, q) for q in places if q[1] == old]
            share, best = max(cand, key=lambda x: x[0])
            first = next(q for q in places if q[1] == old)
            tg = max(((g.intersection(cg).area / g.area, d) for d, g in TP if d["NAMELSAD"] == old), key=lambda x: x[0])
            wrong = (not p[2]) and first is not best
            if not p[2]: p[2] = best[-1]
            p[1] = "%s (%s)" % (old, p[0][:-7] if p[0].endswith(" County") else p[0])
            out.append({"state": st, "old_name": old, "new_name": p[1], "geoid": tg[1]["GEOID"], "county": p[0], "county_area_share": round(tg[0], 3),
                        "row": k, "rows_in_group": grp[old], "showed_other_row_figures_before": "yes" if wrong else "no",
                        "wrong_2024_before": "yes" if wrong else "no", "wrong_2020_before": "yes" if wrong else "no", "wrong_est_flag_before": "no"})
            print(st, k, old, "->", p[1], "geoid", tg[1]["GEOID"], "share %.3f" % tg[0], "v1 share %.3f" % share, "wrong before" if wrong else "")
        keys = collections.Counter((p[0], p[1]) for p in parts); assert max(keys.values()) == 1
        if not dry: open(pp, "w").write(s[:i] + json.dumps(parts, separators=(",", ":")) + s[j:])
    if not dry and out:
        f = os.path.join(repo, "data-v3", "geo", "v2_name_collisions.csv")
        hdr = open(f).readline().strip().split(",")
        with open(f, "a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=hdr, lineterminator="\n"); [w.writerow(r) for r in out]
    print(len(out), "rows renamed")

if __name__ == "__main__":
    main()
