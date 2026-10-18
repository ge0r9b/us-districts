#!/usr/bin/env python3
"""data-v3/geo/{ushouse,senate,statehouse}_2020.csv: 2020-vintage GEOIDs for the v2 rows (TIGER 2020, public domain):
116th Congress districts (tl_2020_us_cd116) and the state legislative districts of TIGER 2020 (the 2018 plans,
tl_2020_SS_sldu / _sldl). v2 keeps one row per current (2024-plan) district and stores its 2020 figures on that same
geometry, so each v2 row is paired with the 2020 district of the same code (code = the 2024 GEOID from
ushouse/senate/statehouse.csv minus the state FIPS); with no same-code 2020 district, the 2020 district overlapping the row
most. Overlap shares are by area on the v2 polygon (x1000 deltas) and the full TIGER 2020 polygon.
match: code+same (same code, each covers >= 90 % of the other), code (same code, boundary changed), overlap (no code match).
Nebraska's state house rows (unicameral) pair with its 2020 SLDU districts. Unpaired 2020 districts are listed with row empty (match = unpaired_2020).
usage: v3_geoids_2020.py <repo> <tiger2020_dir>
"""
import sys, os, csv, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shapely.strtree import STRtree
from town_gaps import recs, FIPS
from town_area_gaps import dec

def v2rows(repo, f):
    s = open(os.path.join(repo, "v2", "data", f)).read(); i = s.index("[", s.index("(")); j = s.rindex("]") + 1
    return json.loads(s[i:j])

def main():
    repo, td = sys.argv[1:3]
    st2f = {v: k for k, v in FIPS.items()}; st2f["District of Columbia"] = "11"
    L = {"ushouse": ("uscd.js", "cd116", "CD116FP"), "senate": ("ussldu.js", "sldu", "SLDUST"), "statehouse": ("ussldl.js", "sldl", "SLDLST")}
    summ = {}
    for lay, (vf, tf, cf) in L.items():
        v2 = v2rows(repo, vf)
        g24 = {(r["state"], int(r["row"])): r["geoid"] for r in csv.DictReader(open(os.path.join(repo, "data-v3", "geo", lay + ".csv"))) if r["row"].isdigit()}
        T = collections.defaultdict(list)
        if tf == "cd116":
            for d, g in recs(os.path.join(td, "tl_2020_us_cd116.zip")):
                if d["STATEFP"] in st2f.values(): T[d["STATEFP"]].append((d, g))  # 50 states + DC; territories left out
        else:
            for f in sorted(os.listdir(td)):
                if f.endswith("_%s.zip" % tf):
                    for d, g in recs(os.path.join(td, f)): T[d["STATEFP"]].append((d, g))
            if tf == "sldl" and not T.get("31"):  # Nebraska is unicameral: its v2 state house rows mirror the SLDU districts
                for d, g in recs(os.path.join(td, "tl_2020_31_sldu.zip")): d = dict(d); d["SLDLST"] = d["SLDUST"]; T["31"].append((d, g))
        out = []; used = set(); c = collections.Counter()
        for k, r in enumerate(v2):
            st = r[0]; sf = st2f.get(st); gid24 = g24.get((st, k), "")
            if not sf or not T.get(sf): out.append([lay, st, k, r[1], gid24, "", "", "no_2020_layer", "", ""]); c["no_2020_layer"] += 1; continue
            g = dec(r[2], 1000); code = gid24[2:] if gid24 else ""
            cand = [(d, h) for d, h in T[sf] if d[cf] == code and not d["GEOID"].endswith("ZZ") and not d["GEOID"].endswith("ZZZ")]
            how = "code"
            if not cand:
                cand = sorted(T[sf], key=lambda x: -(x[1].intersection(g).area if x[1].intersects(g) else 0))[:1]; how = "overlap"
            d, h = cand[0]
            try: inter = g.intersection(h).area; a, b = inter / g.area, inter / h.area
            except Exception: a = b = 0
            if how == "code" and min(a, b) >= 0.9: how = "code+same"
            used.add((sf, d["GEOID"])); c[how] += 1
            out.append([lay, st, k, r[1], gid24, d["GEOID"], d["NAMELSAD"], how, round(a, 4), round(b, 4)])
        for sf, L2 in T.items():
            for d, h in L2:
                if (sf, d["GEOID"]) not in used and not d["GEOID"].endswith("ZZ") and not d["GEOID"].endswith("ZZZ"):
                    out.append([lay, FIPS.get(sf, "District of Columbia" if sf == "11" else sf), "", "", "", d["GEOID"], d["NAMELSAD"], "unpaired_2020", "", ""]); c["unpaired_2020"] += 1
        with open(os.path.join(repo, "data-v3", "geo", lay + "_2020.csv"), "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n"); w.writerow(["layer", "state", "row", "v2_name", "geoid_2024", "geoid_2020", "tiger_name_2020", "match", "v2_in_2020", "2020_in_v2"]); w.writerows(out)
        summ[lay] = dict(c); print(lay, len(v2), dict(c), flush=True)
    json.dump(summ, open(os.path.join(repo, "data-v3", "geo", "summary_2020.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
