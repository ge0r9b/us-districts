#!/usr/bin/env python3
"""Gray batch 2, pass 2: school districts coterminous with one municipality (TIGER 2024 IoU = 1.0 with the place and
county subdivision), filled with the sum of that municipality's official precinct returns (MEDSL 2024 precinct
file, CC0, compiled from the county's official canvass). Exact (no ≈) only when every unit of the municipality is
named in the file (election-day districts + provisional + emergency) and the county's Harris and Trump sums equal
the official county totals; total = candidate votes excluding write-ins (the convention of data/election2024.js,
checked on the county: MEDSL candidate total minus write-ins = official total).
usage: inst_gray2_muni.py <repo> --medsl DIR [--fix]
"""
import sys, os, csv, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_tiger_schools import load_fill_gray
from recheck_identical import load, setflag

CASES = [  # (state, v2 school name, year, MEDSL file, county_name, precinct prefix, official county key)
    ("New Jersey", "Gibbsboro Borough School District", "2024", "nj24.csv", "CAMDEN", "Gibbsboro ", "New Jersey|Camden County"),
]
SPECIAL = {"TOTAL VOTES CAST", "OVERVOTES", "UNDERVOTES", "CONTEST TOTAL"}

def main():
    a = sys.argv[1:]; repo = a[0]; md = a[a.index("--medsl") + 1]; fix = "--fix" in a
    E = load_fill_gray(repo, "2024")["E"]; p = os.path.join(repo, "v2/data/ussch.js"); s, i, j, rows = load(p); out = []
    for st, name, yr, fn, cty, pre, ek in CASES:
        c = [0, 0, 0]; m = [0, 0, 0]; units = set()
        for r in csv.DictReader(open(os.path.join(md, fn))):
            if r["office"] != "US PRESIDENT" or r["county_name"] != cty or r["candidate"] in SPECIAL: continue
            v = int(float(r["votes"] or 0)); wi = r["writein"] == "TRUE"
            for acc, ok in ((c, True), (m, r["precinct"].startswith(pre))):
                if not ok: continue
                if r["party_simplified"] == "DEMOCRAT": acc[0] += v
                elif r["party_simplified"] == "REPUBLICAN": acc[1] += v
                if not wi: acc[2] += v
            if r["precinct"].startswith(pre): units.add(r["precinct"])
        o = E[ek]; ok = c == list(o)
        rec = {"state": st, "name": name, "year": yr, "units": sorted(units), "value": m, "county_medsl": c, "county_official": o, "exact": ok}
        print(rec)
        if fix and ok:
            for r in rows:
                if r[0] == st and r[1] == name:
                    YI = 3 if yr == "2024" else 4; assert r[YI] is None; r[YI] = m; setflag(r, yr, "exact")
        out.append(rec)
    if fix: open(p, "w").write(s[:i] + json.dumps(rows, separators=(",", ":")) + s[j:])
    json.dump(out, open(os.path.join(repo, "data-v3/inst/gray2_pass2_muni.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
