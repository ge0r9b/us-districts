#!/usr/bin/env python3
"""Coverage audit for the us-districts v2 map data (read-only on data files).

Usage: python3 tools/coverage_audit.py [REPO] [--tiger DIR] [--csv OUT.csv] [--md OUT.md] [--json OUT.json]

For every layer x year (2020, 2024) x state (50 + DC) it reports feature counts,
how many features carry results, empty geometries, duplicate/missing names and
broken references, and compares boundary feature counts with the Census TIGER
2024 Gazetteer (public domain; downloaded once and cached in --tiger, default
~/.cache/us-districts/tiger2024).

Layers: states (v2/data/usstates.js), counties (v2/data/uscounties.js + data/election20XX.js),
towns = county subdivisions (data/<State>.js "towns" + v2/data/parts/<State>.js),
precincts (data/precincts20XX/<State>.js, v2/data/precincts20XX-DC.js), ushouse (v2/data/uscd.js),
senate (v2/data/ussldu.js), statehouse (v2/data/ussldl.js), schools (v2/data/ussch.js),
dcwards (v2/data/dc.js, DC only).  dc.js overrides DC rows at runtime; the audit applies it the same way.

Status per cell: P present (count matches TIGER within tolerance and >=99% of features have results),
S suspect (count off, fill <99%, empty geometries, broken refs, precinct votes outside 90-110% of official),
M missing (no features / no file), - not applicable.  Nothing is fabricated: values are only counted.
"""
import json, os, re, sys, io, zipfile, urllib.request, collections, argparse

STATES = ["Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware","District of Columbia",
"Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana","Maine","Maryland",
"Massachusetts","Michigan","Minnesota","Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire","New Jersey",
"New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania","Rhode Island",
"South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont","Virginia","Washington","West Virginia","Wisconsin","Wyoming"]
ABBR = dict(zip(STATES, "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()))
GAZ = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_%s_national.zip"
GAZ_SETS = ["counties","cousubs","119CDs","sldu","sldl","unsd","elsd","scsd"]
LAYERS = ["states","counties","towns","precincts","ushouse","senate","statehouse","schools","dcwards"]
YEARS = ["2020","2024"]
DEC = json.JSONDecoder()

def jsargs(path, start_pat):
    """Decode the JSON literals that follow start_pat in a JS data file (call args or assignment)."""
    s = open(path, encoding="utf-8").read()
    m = re.search(start_pat, s)
    if not m: raise ValueError("pattern %r not in %s" % (start_pat, path))
    i, out = m.end(), []
    while i < len(s):
        while i < len(s) and s[i] in " \t\r\n,": i += 1
        if i >= len(s) or s[i] in ");": break
        v, i = DEC.raw_decode(s, i); out.append(v)
    return out

def tiger(dirp):
    os.makedirs(dirp, exist_ok=True)
    exp = collections.defaultdict(lambda: collections.Counter())
    for k in GAZ_SETS:
        txt = os.path.join(dirp, "2024_Gaz_%s_national.txt" % k)
        if not os.path.exists(txt):
            data = urllib.request.urlopen(GAZ % k, timeout=120).read()
            zipfile.ZipFile(io.BytesIO(data)).extractall(dirp)
        with open(txt, encoding="utf-8", errors="replace") as f:
            hdr = [h.strip() for h in f.readline().split("\t")]
            for line in f:
                r = dict(zip(hdr, [c.strip() for c in line.split("\t")]))
                st, gid, nm = r["USPS"], r["GEOID"], r.get("NAME", "")
                if gid.endswith("ZZZ") or gid.endswith("ZZ") or "not defined" in nm.lower(): continue
                if k == "cousubs":
                    if gid.endswith("00000"): continue  # county subdivisions not defined
                    fs = r.get("FUNCSTAT", "")
                    if fs in ("A", "B", "C", "G"): exp[st]["towngov"] += 1
                    if fs not in ("N", "S", "I"): exp[st]["towns"] += 1  # governmental MCDs + places-as-MCDs (F)
                elif k == "119CDs": exp[st]["ushouse"] += 1
                elif k == "sldu": exp[st]["senate"] += 1
                elif k == "sldl": exp[st]["statehouse"] += 1
                elif k in ("unsd","elsd","scsd"): exp[st]["schools"] += 1
                elif k == "counties": exp[st]["counties"] += 1
    for st in exp:
        exp[st]["states"] = 1
        if not exp[st]["towngov"]: exp[st]["towns"] = 0  # statistical CCD states: no town governments
    # DC: council wards are TIGER SLDU; the app shows them as senate+house+wards; one school district (DCPS)
    exp["DC"]["dcwards"] = exp["DC"]["senate"]; exp["DC"]["statehouse"] = exp["DC"]["senate"]
    # Nebraska is unicameral: TIGER has no SLDL; the app mirrors the 49 LDs under state house
    if exp["NE"]["statehouse"] == 0: exp["NE"]["statehouse"] = exp["NE"]["senate"]
    return exp

def nonempty(g):
    try: return any(len(ring) >= 6 for poly in g for ring in poly)
    except TypeError: return False

def tot(v):
    return v[2] if isinstance(v, list) and len(v) >= 3 and isinstance(v[2], (int, float)) else (sum(x for x in v if isinstance(x,(int,float))) if isinstance(v, list) else 0)

def has(v):
    return isinstance(v, list) and len(v) >= 2 and tot(v) > 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", nargs="?", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--tiger", default=os.path.expanduser("~/.cache/us-districts/tiger2024"))
    ap.add_argument("--csv"); ap.add_argument("--md"); ap.add_argument("--json")
    a = ap.parse_args()
    R = a.repo; V = os.path.join(R, "v2", "data"); D = os.path.join(R, "data")
    exp = tiger(a.tiger)
    cell = {}   # (state, layer, year) -> dict
    def C(st, ly, yr): return cell.setdefault((st, ly, yr), {"n": 0, "filled": 0, "est": 0, "empty": 0, "dupe": 0, "noname": 0, "notes": []})

    # ---- dc.js override (parse literals W, P, A24, A20) ----
    dcsrc = open(os.path.join(V, "dc.js"), encoding="utf-8").read()
    def dclit(name):
        m = re.search(r"\b%s=" % name, dcsrc); return DEC.raw_decode(dcsrc, m.end())[0] if m else None
    DCW, DCP, DCA24, DCA20 = dclit("W"), dclit("P"), dclit("A24"), dclit("A20")

    AK = jsargs(os.path.join(V, "ak.js"), r"__ak\s*=")[0]
    # ---- national district layers ----
    for ly, fn, pat in [("ushouse","uscd.js",r"__uscd\("),("senate","ussldu.js",r"__usdist\(\"senate\","),
                        ("statehouse","ussldl.js",r"__usdist\(\"statehouse\","),("schools","ussch.js",r"__usdist\(\"schools\",")]:
        rows = jsargs(os.path.join(V, fn), pat)[0]
        rows = [r for r in rows if r[0] != "District of Columbia"]
        if ly == "ushouse": rows.append(["District of Columbia","00",DCP,DCA24,DCA20])
        elif ly in ("senate","statehouse"): rows += DCW
        else: rows.append(["District of Columbia","District of Columbia Public Schools",DCP,DCA24,DCA20])
        seen = collections.Counter((r[0], r[1]) for r in rows)
        for r in rows:
            st, nm, g = r[0], r[1], r[2]
            a24 = r[3] if len(r) > 3 else None; a20 = r[4] if len(r) > 4 else None; est = r[5] if len(r) > 5 else None
            for yr, v in (("2020", a20), ("2024", a24)):
                c = C(st, ly, yr); c["n"] += 1; c["filled"] += has(v)
                c["est"] += bool(est) and has(v)
                c["empty"] += not nonempty(g); c["noname"] += not str(nm or "").strip()
                c["dupe"] += seen[(st, nm)] > 1
                if not has(v): c.setdefault("gray", []).append(str(nm))
    # DC wards as their own layer
    for r in DCW:
        for yr, v in (("2020", r[4]), ("2024", r[3])):
            c = C("District of Columbia", "dcwards", yr); c["n"] += 1; c["filled"] += has(v); c["empty"] += not nonempty(r[2])

    # ---- states ----
    srows = jsargs(os.path.join(V, "usstates.js"), r"__usst\(")[0]
    sn = collections.Counter(r[0] for r in srows)
    # ---- counties: shapes + election tables ----
    crows = [r for r in jsargs(os.path.join(V, "uscounties.js"), r"__uscty\(")[0] if r[0] != "District of Columbia"]
    crows.append(["District of Columbia","District of Columbia",DCP])
    E = {}
    for yr in YEARS:
        E[yr] = jsargs(os.path.join(D, "election%s.js" % yr), r"ELECTION%s\s*=" % yr)[0]
        E[yr]["District of Columbia|District of Columbia"] = DCA24 if yr == "2024" else DCA20
    shapes = collections.defaultdict(set)
    for r in crows: shapes[r[0]].add(r[1])
    for yr in YEARS:
        ek = collections.defaultdict(set)
        for k in E[yr]:
            st, cn = k.split("|", 1); ek[st].add(cn)
        ak_b = AK.get("boro" + yr) or {}
        ek["Alaska"] |= {b for b, v in ak_b.items() if has(v)}  # merged into ELECTION20XX at runtime, flagged ≈
        stsum = collections.Counter()
        for k, v in E[yr].items(): stsum[k.split("|",1)[0]] += tot(v)
        stsum["Alaska"] = tot(AK.get("state" + yr))
        E[yr+"sum"] = stsum
        for st in STATES:
            c = C(st, "states", yr); c["n"] = sn.get(st, 0) or (1 if st == "District of Columbia" else 0)
            c["filled"] = c["n"] if stsum[st] > 0 else 0
            c = C(st, "counties", yr)
            names = shapes[st]; c["n"] = len(names)
            c["filled"] = len(names & ek[st])
            for r in crows:
                if r[0] == st and not nonempty(r[2]): c["empty"] += 1
            orphan = sorted(ek[st] - names); noval = sorted(names - ek[st])
            if orphan: c["notes"].append("%d election rows without shape (e.g. %s)" % (len(orphan), "; ".join(orphan[:3])))
            if st == "Alaska": c["est"] = c["filled"]; c["info"] = "borough values from v2/data/ak.js (≈, official precinct results allocated)"
            if st == "Hawaii" and noval == ["Kalawao County"]: c["structural"] = 1; noval = []; c["info"] = "Kalawao County votes are reported with Maui County (official)"
            if noval: c["notes"].append("%d shapes without %s result (e.g. %s)" % (len(noval), yr, "; ".join(noval[:3])))

    # ---- per-state files: towns (county subdivisions) + parts; precincts ----
    for st in STATES:
        fn = st.replace(" ", "-") + ".js"
        geo = {}
        p = os.path.join(D, fn)
        if os.path.exists(p):
            geo = jsargs(p, r"__geo\(")[1]
        towns = geo.get("towns") or []
        parts = []
        pp = os.path.join(V, "parts", fn)
        if os.path.exists(pp): parts = jsargs(pp, r"__parts\(")[1]
        tn = {(r[1], r[2]) for r in towns}
        extra = [(r[0], r[1]) for r in parts if (r[0], r[1]) not in tn]
        for yr in YEARS:
            c = C(st, "towns", yr); c["n"] = len(towns); c["empty"] = sum(not nonempty(r[-1]) for r in towns)
            c["filled"] = c["n"]  # town values are derived from precincts at runtime (area-weighted, ≈)
            c["parts"] = len(parts); c["parts_nogeom"] = sum(1 for r in parts if not r[2])
        # cross-check: per-state geo file vs national layers
        for ly in ("ushouse","senate","statehouse","schools"):
            if ly in geo and st != "District of Columbia":
                n_nat = C(st, ly, "2024")["n"]
                if len(geo[ly]) != n_nat:
                    C(st, ly, "2024")["notes"].append("data/%s %s has %d features vs %d in v2 national file" % (fn, ly, len(geo[ly]), n_nat))
        for yr in YEARS:
            c = C(st, "precincts", yr)
            if st == "District of Columbia": pf = os.path.join(V, "precincts%s-DC.js" % yr)
            else: pf = os.path.join(D, "precincts%s" % yr, st.replace(" ", "_") + ".js")
            if not os.path.exists(pf):
                c["notes"].append("no precinct file"); continue
            args = jsargs(pf, r"__prec\(")
            rows = args[1] if len(args) > 1 else []
            c["n"] = len(rows)
            vs = 0; bycty = collections.Counter(); by2 = collections.Counter()
            for r in rows:
                t = r[4] if len(r) > 4 and isinstance(r[4], (int, float)) else 0
                vs += t; bycty[r[0]] += t; by2[r[0]] += (r[2] or 0) + (r[3] or 0)
                c["filled"] += t > 0; c["empty"] += not nonempty(r[-1])
            off = E[yr+"sum"][st]
            c["votes"] = vs; c["official"] = off; c["ratio"] = round(vs / off, 4) if off else None
            # per-county ratio vs official county totals
            # per county vs official, two ways: Dem+Rep (the rule used by the v2/data/COVERAGE.md inventory, qc.py)
            # and all votes. "outside" = Dem+Rep ratio outside 0.9-1.1; the all-votes list is informational.
            bad = []; none = []; badt = []
            for cn in sorted(shapes[st]):
                ov = E[yr].get(st + "|" + cn)
                o = tot(ov)
                if not o: continue
                v = bycty.get(cn, 0)
                if v == 0: none.append(cn); continue
                o2 = (ov[0] or 0) + (ov[1] or 0)
                if o2 and not (0.9 <= by2.get(cn, 0) / o2 <= 1.1): bad.append(cn)
                if not (0.9 <= v / o <= 1.1): badt.append(cn)
            c["cty_none"] = none; c["cty_off"] = bad; c["cty_off_total"] = badt
            if yr == "2024" and st != "District of Columbia":
                xf = os.path.join(V, "x20", fn)
                if os.path.exists(xf):
                    xa = jsargs(xf, r"__x20\(")
                    xk = set(xa[1].keys()) if len(xa) > 1 else set()
                    pk = {r[0] + "|" + r[1] for r in rows}
                    c["x20"] = len(xk); c["x20_orphan"] = len(xk - pk)
                    if xk - pk: c["notes"].append("%d x20 keys with no 2024 precinct" % len(xk - pk))
            unk = sorted(set(bycty) - shapes[st])
            if unk and st != "District of Columbia": c["notes"].append("%d precinct county names not in county layer (e.g. %s)" % (len(unk), "; ".join(unk[:3])))

    # ---- status ----
    def expected(st, ly):
        e = exp[ABBR[st]].get(ly)
        if ly == "precincts": return None
        if ly == "dcwards": return e if st == "District of Columbia" else None
        if ly == "schools" and st == "District of Columbia": return 1
        if ly == "ushouse" and st == "District of Columbia": return 1
        if ly == "counties" and st == "District of Columbia": return 1
        return e
    for (st, ly, yr), c in cell.items():
        e = expected(st, ly); c["exp"] = e
        why = []
        if ly == "dcwards" and st != "District of Columbia": c["status"] = "-"; continue
        if ly == "towns" and not e:
            c["status"] = "-"; c["why"] = ("%d town rows in a state without town governments (TIGER CCD state)" % c["n"]) if c["n"] else ""; continue
        if c["n"] == 0:
            c["status"] = "M"; c["why"] = (c["notes"] or ["no features"])[0]; continue
        if e:
            tol = 0 if ly in ("states","ushouse","senate","statehouse","dcwards","counties") else 0.02
            if abs(c["n"] - e) > tol * e: why.append("count %d vs TIGER %d" % (c["n"], e))
        if ly == "precincts":
            z = c["n"] - c["filled"]
            if z: c["info"] = "%d zero-vote precinct rows" % z
        elif ly != "towns" and c["filled"] < c["n"] - c.get("structural", 0):
            g = c.get("gray") or []
            why.append("gray %d/%d%s" % (c["n"] - c["filled"], c["n"], (" (" + ", ".join(g[:8]) + (" …" if len(g) > 8 else "") + ")") if g else ""))
        if c["empty"]: why.append("%d empty geometries" % c["empty"])
        if c["dupe"]: why.append("%d duplicate names" % c["dupe"])
        if c["noname"]: why.append("%d missing names" % c["noname"])
        if ly == "precincts":
            r = c.get("ratio")
            if r is not None and not (0.98 <= r <= 1.02): why.append("votes %.1f%% of official" % (100 * r))
            if c.get("cty_none"): why.append("%d counties with no precincts" % len(c["cty_none"]))
            if c.get("cty_off"): why.append("%d counties outside 90-110%% (Dem+Rep)" % len(c["cty_off"]))
            if set(c.get("cty_off_total") or []) != set(c.get("cty_off") or []):
                c["info"] = ((c.get("info") or "") + "; all-votes rule: %d outside (%s)" % (len(c["cty_off_total"]), ", ".join(c["cty_off_total"][:6]))).strip("; ")
        why += c["notes"]
        c["why"] = "; ".join(why)
        c["status"] = "S" if why else "P"

    # ---- outputs ----
    if a.csv:
        import csv
        with open(a.csv, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["state","layer","year","status","features","tiger_expected","with_results","est","empty_geom","dupe_names","precinct_votes","official_votes","ratio","reasons","info"])
            for st in STATES:
                for ly in LAYERS:
                    for yr in YEARS:
                        c = cell.get((st, ly, yr))
                        if not c: continue
                        w.writerow([st, ly, yr, c["status"], c["n"], c.get("exp") or "", c["filled"], c["est"], c["empty"], c["dupe"], c.get("votes",""), c.get("official",""), c.get("ratio",""), c.get("why",""), c.get("info","")])
    if a.json:
        json.dump({"%s|%s|%s" % k: v for k, v in cell.items()}, open(a.json, "w"), indent=0, default=list)
    # markdown matrix: one row per state, one column per layer, "2020/2024" status
    L = ["| State | " + " | ".join(LAYERS) + " |", "|---|" + "---|" * len(LAYERS)]
    for st in STATES:
        L.append("| %s | " % ABBR[st] + " | ".join("%s/%s" % (cell.get((st, ly, "2020"), {}).get("status", "-"), cell.get((st, ly, "2024"), {}).get("status", "-")) for ly in LAYERS) + " |")
    tots = []
    for ly in LAYERS:
        for yr in YEARS:
            cs = [c for (s, l, y), c in cell.items() if l == ly and y == yr and c["status"] != "-"]
            n = sum(c["n"] for c in cs); f = sum(c["filled"] for c in cs); e = sum((c.get("exp") or 0) for c in cs)
            sc = collections.Counter(c["status"] for c in cs)
            tots.append("| %s | %s | %d | %s | %d | %d | %d | %d |" % (ly, yr, n, e or "", f, sc["P"], sc["S"], sc["M"]))
    md = "\n".join(L) + "\n\n| Layer | Year | Features | TIGER 2024 expected | With results | P | S | M |\n|---|---|---|---|---|---|---|---|\n" + "\n".join(tots) + "\n"
    if a.md: open(a.md, "w").write(md)
    else: print(md)

if __name__ == "__main__":
    main()
