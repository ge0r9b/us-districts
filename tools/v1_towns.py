#!/usr/bin/env python3
"""data-v3/geo/v1_towns.csv: TIGER 2024 GEOIDs for the root data/<State>.js "towns" and "places" rows (v1, read-only).
towns: county subdivision of the row's county with the same NAMELSAD (several: the one overlapping the v1 polygon most),
       else an incorporated place / CDP of that name touching the county, else the county subdivision containing the
       v1 polygon's representative point (match "point"). places: place of that NAMELSAD in the state (several: most overlap).
Columns: layer, state, county, row, v1_name, geoid, tiger_name, tiger_kind (cousub/place), funcstat, classfp, match, overlap
(share of the v1 polygon inside the TIGER feature).
usage: v1_towns.py <repo> <tiger_dir> <tl_2024_us_county.zip> OUT.csv
"""
import sys, os, csv, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shapely.strtree import STRtree
import coverage_audit as A
from town_gaps import recs, FIPS
from town_area_gaps import dec

def main():
    repo, td, cz, out = sys.argv[1:5]
    st2f = {v: k for k, v in FIPS.items()}; W = []
    for st in sorted(st2f):
        fn = os.path.join(repo, "data", st.replace(" ", "-") + ".js")
        if not os.path.exists(fn): continue
        geo = A.jsargs(fn, r"__geo\(")[1]; sf = st2f[st]
        towns = geo.get("towns") or []; places = geo.get("places") or []
        if not towns and not places: continue
        CTY = {d["NAMELSAD"]: d["COUNTYFP"] for d, g in recs(cz, lambda d: d["STATEFP"] == sf)}
        CS = list(recs(os.path.join(td, "tl_2024_%s_cousub.zip" % sf))) if towns else []
        PL = list(recs(os.path.join(td, "tl_2024_%s_place.zip" % sf)))
        csb = collections.defaultdict(list); plb = collections.defaultdict(list)
        for k, (d, g) in enumerate(CS): csb[(d["COUNTYFP"], d["NAMELSAD"])].append(k)
        for k, (d, g) in enumerate(PL): plb[d["NAMELSAD"]].append(k)
        CT = STRtree([g for _, g in CS]) if CS else None
        def ov(g, h):
            try: return g.intersection(h).area / g.area if g.area else 0
            except Exception: return 0
        for i, t in enumerate(towns):
            g = dec(t[-1]); cf = CTY.get(t[1]); row = None
            c = csb.get((cf, t[2]), [])
            if c:
                k = max(c, key=lambda k: ov(g, CS[k][1]) if g is not None else 0); d = CS[k][0]
                row = [d["GEOID"], d["NAMELSAD"], "cousub", d["FUNCSTAT"], d["CLASSFP"], "name" if len(c) == 1 else "name+overlap", ov(g, CS[k][1]) if g is not None else ""]
            else:
                c = [k for k in plb.get(t[2], []) if g is not None and ov(g, PL[k][1]) > 0]
                if c:
                    k = max(c, key=lambda k: ov(g, PL[k][1])); d = PL[k][0]
                    row = [d["GEOID"], d["NAMELSAD"], "place", d["FUNCSTAT"], d["CLASSFP"], "name", ov(g, PL[k][1])]
                elif g is not None and CT is not None:
                    p = g.representative_point(); h = [k for k in CT.query(p) if CS[k][1].contains(p)]
                    if h: d = CS[h[0]][0]; row = [d["GEOID"], d["NAMELSAD"], "cousub", d["FUNCSTAT"], d["CLASSFP"], "point", ov(g, CS[h[0]][1])]
            row = row or ["", "", "", "", "", "", ""]
            if row[6] != "": row[6] = round(row[6], 3)
            W.append(["towns", st, t[1], i, t[2]] + row)
        for i, p in enumerate(places):
            g = dec(p[-1]); c = plb.get(p[1], []); row = ["", "", "", "", "", "", ""]
            if c:
                k = max(c, key=lambda k: ov(g, PL[k][1]) if g is not None else 0); d = PL[k][0]
                row = [d["GEOID"], d["NAMELSAD"], "place", d["FUNCSTAT"], d["CLASSFP"], "name" if len(c) == 1 else "name+overlap", round(ov(g, PL[k][1]), 3) if g is not None else ""]
            W.append(["places", st, "", i, p[1]] + row)
        print(st, len(towns), len(places), flush=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["layer", "state", "county", "row", "v1_name", "geoid", "tiger_name", "tiger_kind", "funcstat", "classfp", "match", "overlap"]); w.writerows(W)

if __name__ == "__main__":
    main()
