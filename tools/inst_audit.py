#!/usr/bin/env python3
"""Institutions gap inventory for the us-districts v2 map (READ-ONLY on every data file).

usage: python3 tools/inst_audit.py <audited repo> [--out DIR] [--tiger24 DIR] [--tiger20 DIR] [--place24 FILE]

<audited repo> is a checkout of the branch being audited (e.g. a worktree of origin/data/geo at/after 0c4afbc).
It must contain tools/coverage_audit.py (geo lane); this script runs it unchanged (--json) and adds:
  * institution types: US House (CD), state senate (SLDU), state house (SLDL), school districts split into
    unified / elementary / secondary (TIGER set from data-v3/geo/schools.csv), DC wards, counties and
    municipalities as governments, precincts; years 2020 and 2024;
  * expected counts with their source: Census TIGER 2024 Gazetteer (boundaries drawn by the app for both years),
    Census TIGER 2020 Gazetteer (116th CDs, 2018 SLD plans = the lines the 2020 elections were held on),
    2 U.S.C. 2a (435 seats), 2022 Census of Governments (national counts of county / municipal / township
    governments). Anything without a cited source is written as "unknown";
  * results coverage: with results, exact, ≈ (est both years, e24 2024 only, e20 2020 only), gray (no value),
    with the gray names and the reason recorded in v2/data/COVERAGE.md;
  * attributes per row, officeholders (searched for in every v2 data file and v2/index.html, read-only);
  * key checks: v2 data rows vs the app's embedded PACK.lists (v2/index.html, read-only), at-large CD code,
    GEOID side table coverage, duplicate (state, name) keys, v1 per-state files vs v2 national files,
    identical-figure pairs listed in COVERAGE.md that still share figures;
  * file size (raw and gzip -9) of every v2 file a fix would touch (load cost).
Outputs: <out>/inst_gaps.csv and <out>/inst_audit.json; the per-type table is printed (pasted into <out>/AUDIT.md).  Nothing is estimated or invented.
"""
import argparse, collections, csv, gzip, io, json, os, re, subprocess, sys, tempfile

STATES = None  # filled from coverage_audit
CA = None

def load_ca(repo):
    global CA, STATES
    sys.path.insert(0, os.path.join(repo, "tools"))
    import coverage_audit as ca
    CA = ca; STATES = ca.STATES
    return ca

def gaz(path, keep=lambda r: True):
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        hdr = [h.strip() for h in f.readline().split("\t")]
        for line in f:
            r = dict(zip(hdr, [c.strip() for c in line.split("\t")]))
            if keep(r): out.append(r)
    return out

def notdef(r):
    g, n = r["GEOID"], r.get("NAME", "")
    return g.endswith("ZZZ") or g.endswith("ZZ") or "not defined" in n.lower()

def tiger_counts(d, year):
    """per USPS counts for the district sets of one Gazetteer vintage."""
    sets = {"2024": {"ushouse": "119CDs", "senate": "sldu", "statehouse": "sldl", "unsd": "unsd", "elsd": "elsd", "scsd": "scsd", "counties": "counties", "cousubs": "cousubs"},
            "2020": {"ushouse": "116CDs", "senate": "sldu", "statehouse": "sldl", "unsd": "unsd", "elsd": "elsd", "scsd": "scsd", "counties": "counties", "cousubs": "cousubs"}}[year]
    exp = collections.defaultdict(collections.Counter)
    for k, s in sets.items():
        p = os.path.join(d, "%s_Gaz_%s_national.txt" % (year, s))
        if not os.path.exists(p): continue
        for r in gaz(p):
            if notdef(r): continue
            st = r["USPS"]
            if k == "cousubs":
                if r["GEOID"].endswith("00000"): continue
                if r.get("FUNCSTAT") in ("A", "B", "C", "G"): exp[st]["towngov"] += 1
                if r.get("FUNCSTAT") not in ("N", "S", "I"): exp[st]["towns"] += 1  # same rule as coverage_audit.py
                continue
            exp[st][k] += 1
    if exp["NE"]["statehouse"] == 0: exp["NE"]["statehouse"] = exp["NE"]["senate"]
    for st in exp:
        if not exp[st]["towngov"]: exp[st]["towns"] = 0
    return exp

def fsize(p):
    if not os.path.exists(p): return None, None
    b = open(p, "rb").read()
    return len(b), len(gzip.compress(b, 9))

def pack_lists(repo):
    for line in open(os.path.join(repo, "v2", "index.html"), encoding="utf-8"):
        if line.startswith("const PACK = { lists:"):
            i = line.index('{"localities"')
            return json.JSONDecoder().raw_decode(line, i)[0]
    return {}

# Gray reasons as recorded in v2/data/COVERAGE.md (build 1539 'Still gray', geo-lane sections of Oct 18, 2026).
GRAY_REASON = {
 ("statehouse", "2024"): "no 2024 House race in AL/LA/MS/VA to apportion split precincts and 2024 precinct polygons cover 39-80 % (AL Limestone/Morgan, LA St. John the Baptist, MS Harrison, VA Suffolk/Chesapeake); WY Fremont 05-1 one unit across HD 33/34/54 (COVERAGE.md build 1539). Geo lane IN PROGRESS.",
 ("senate", "2024"): "WY SD 018: usable 2024 precinct cover 89 % (< 90 % rule), grayed in 737b440 after its figure was found copied from SD 027 (COVERAGE.md 'identical figures').",
}
SCHOOL_REASON = {
 "South Dakota": "vote-center counties (Brown, Brookings, Hughes, Yankton, Potter, Haakon, Sully) report without geography; Lawrence renumbered precincts, no shapes",
 "Maine": "unorganized territories/plantations reported combined with a town (e.g. 'Brownville/Twps'); no official split",
 "Vermont": "unorganized gores with no reporting unit (0-30 residents); 2020 Averill reported with Canaan",
 "Missouri": "Cape Girardeau, Cole, Miller, Pettis precincts renumbered/merged since 2020, no 2024 shapes found",
 "Alaska": "area-weighting rejected for Alaska (build 1533); Kake, Nenana grayed in 737b440 (2-vote copied figure)",
 "Kentucky": "2024: precinct cover 51-79 %; 2020: Graves County reported as one unit by VEST (Mayfield cannot be separated)",
 "Alabama": "Fort Rucker military post; Guntersville: 2 new Marshall County polling places with no shape",
 "Colorado": "Pitkin, Chaffee 2024 precinct counts differ from 2020, no public 2024 precinct layer",
 "Wyoming": "Uinta, Weston 2020 shape names do not match 2024 precinct codes",
 "Texas": "Boys Ranch ISD: no voters",
 "California": "2020: usable precinct cover under 90 %",
}
DEFAULT_SCHOOL_REASON = "usable precinct polygons cover only part of the district (17-88 %; per-district reasons in /workspace/db/fill_gray_2024.json on the box)"

def ests(flag, yr):
    return flag == "est" or (flag == "e24" and yr == "2024") or (flag == "e20" and yr == "2020")

def has(v): return CA.has(v)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data-v3", "inst"))
    ap.add_argument("--tiger24", default="/workspace/w/tiger")
    ap.add_argument("--tiger20", default="/workspace/w/inst-raw/tiger2020")
    ap.add_argument("--place24", default="/workspace/w/inst-raw/tiger2024/2024_Gaz_place_national.txt")
    a = ap.parse_args()
    R = os.path.abspath(a.repo); V = os.path.join(R, "v2", "data"); D = os.path.join(R, "data")
    ca = load_ca(R)
    ABBR = ca.ABBR
    head = subprocess.run(["git", "-C", R, "log", "-1", "--format=%h %s"], capture_output=True, text=True).stdout.strip()

    # 1) geo lane audit, unchanged
    tj = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    old = sys.argv; sys.argv = ["coverage_audit.py", R, "--tiger", a.tiger24, "--json", tj, "--md", os.devnull]
    try: ca.main()
    finally: sys.argv = old
    CELL = json.load(open(tj))

    E24 = tiger_counts(a.tiger24, "2024"); E20 = tiger_counts(a.tiger20, "2020")
    # TIGER 2024 school set per row (data-v3/geo/schools.csv, joined on row index)
    sset = {}
    sp = os.path.join(R, "data-v3", "geo", "schools.csv")
    gidrows = {}
    for lay in ("ushouse", "senate", "statehouse", "schools", "counties"):
        p = os.path.join(R, "data-v3", "geo", lay + ".csv")
        gidrows[lay] = list(csv.DictReader(open(p))) if os.path.exists(p) else []
    for r in gidrows["schools"]:
        sset[(r["state"], r["v2_name"])] = r["tiger_set"]

    # 2) v2 district rows (+ dc.js the way the app applies it)
    dcsrc = open(os.path.join(V, "dc.js"), encoding="utf-8").read()
    def dclit(n):
        m = re.search(r"\b%s=" % n, dcsrc); return ca.DEC.raw_decode(dcsrc, m.end())[0] if m else None
    DCW, DCP, DCA24, DCA20 = dclit("W"), dclit("P"), dclit("A24"), dclit("A20")
    FILES = [("ushouse", "uscd.js", r"__uscd\("), ("senate", "ussldu.js", r"__usdist\(\"senate\","),
             ("statehouse", "ussldl.js", r"__usdist\(\"statehouse\","), ("schools", "ussch.js", r"__usdist\(\"schools\",")]
    ROWS = {}
    for ly, fn, pat in FILES:
        rows = [r for r in ca.jsargs(os.path.join(V, fn), pat)[0] if r[0] != "District of Columbia"]
        if ly == "ushouse": rows.append(["District of Columbia", "98", DCP, DCA24, DCA20])
        elif ly in ("senate", "statehouse"): rows += [list(r[:5]) for r in DCW]
        else: rows.append(["District of Columbia", "District of Columbia Public Schools", DCP, DCA24, DCA20])
        ROWS[ly] = rows
    ROWS["dcwards"] = [list(r[:5]) for r in DCW]

    # officeholders: any field beyond [state, name, geometry, v2024, v2020, flag]? any roster-like keys anywhere?
    attr = {}
    for ly, rows in ROWS.items():
        L = collections.Counter(len(r) for r in rows)
        flags = collections.Counter((r[5] if len(r) > 5 else None) for r in rows)
        attr[ly] = {"row_lengths": dict(L), "flags": {str(k): v for k, v in flags.items()}}
    off_hits = {}
    pat = re.compile(r"bioguide|officeholder|incumbent|\bsenator\b|representative_name|member_name|openstates|\"party\"\s*:", re.I)
    for fn in sorted(os.listdir(V)) + ["../index.html"]:
        p = os.path.join(V, fn)
        if os.path.isfile(p):
            s = open(p, encoding="utf-8", errors="replace").read()
            off_hits[fn] = len(pat.findall(s))

    # 3) PACK.lists (institution menu lists) vs data rows
    P = pack_lists(R)
    packchk = {}
    for ly in ("ushouse", "senate", "statehouse", "schools"):
        dk = {(r[0], r[1]) for r in ROWS[ly] if r[0] != "District of Columbia"}
        if ly == "schools": pl = [(r[0], r[2]) for r in P.get(ly, [])]
        else: pl = [(r[0], r[1]) for r in P.get(ly, [])]
        pk = set(pl); dup = sum(c - 1 for c in collections.Counter(pl).values() if c > 1)
        a1 = dk - pk; b1 = pk - dk
        packchk[ly] = {"data_rows": len(dk), "pack_rows": len(pl), "pack_unique": len(pk), "pack_dupe_rows": dup,
                       "data_not_in_pack": len(a1), "data_not_in_pack_by_state": dict(collections.Counter(s for s, _ in a1).most_common()),
                       "pack_not_in_data": len(b1), "pack_not_in_data_by_state": dict(collections.Counter(s for s, _ in b1).most_common()),
                       "examples_data_not_in_pack": sorted(a1)[:5], "examples_pack_not_in_data": sorted(b1)[:5]}
    # school type in PACK vs TIGER set
    ptype = {(r[0], r[2]): r[1] for r in P.get("schools", [])}
    tmap = {"unsd": "unified", "elsd": "elementary", "scsd": "secondary"}
    tmis = collections.Counter()
    for k, t in sset.items():
        if k in ptype and ptype[k] != tmap.get(t): tmis[(tmap.get(t), ptype[k])] += 1
    pn = [(r[0], r[2]) for r in P.get("schools", [])]
    packchk["schools"]["not_defined_rows"] = sorted({s for s, n in pn if n == "School District Not Defined"})
    packchk["schools"]["mojibake_rows"] = sorted({n for s, n in pn if "\u00c3" in n})
    oldn = set()
    cp = os.path.join(R, "data-v3", "geo", "v2_name_collisions.csv")
    if os.path.exists(cp): oldn = {(r["state"], r["old_name"]) for r in csv.DictReader(open(cp))}
    packchk["schools"]["pack_rows_with_pre_9ff4c00_names"] = sum(1 for k in pn if k in oldn)
    packchk["schools"]["type_mismatch_vs_tiger"] = {"%s->pack %s" % k: v for k, v in tmis.items()}

    # 4) at-large CDs
    atl = [r[0] for r in ROWS["ushouse"] if r[1] == "00"]
    exp_atl = sorted(st for st, c in E24.items() if c["ushouse"] == 1 and st != "DC")
    js_label = subprocess.run(["node", "-e", 'console.log("District "+String("00").replace(/^0+(?=\\d)/,""))'], capture_output=True, text=True).stdout.strip()

    # 5) duplicates and GEOID side table
    dupes = {ly: sum(c for c in collections.Counter((r[0], r[1]) for r in rows).values() if c > 1) for ly, rows in ROWS.items()}
    gidchk = {}
    for ly in ("ushouse", "senate", "statehouse", "schools", "counties"):
        g = gidrows[ly]
        gidchk[ly] = {"rows": len(g), "unmatched": sum(1 for r in g if not r["geoid"]), "geoid_dupes": sum(c - 1 for c in collections.Counter(r["geoid"] for r in g).values() if c > 1),
                      "v2_rows": (len(ROWS[ly]) if ly in ROWS else None)}

    # 6) v1 per-state files vs v2 national
    v1diff = []
    for st in STATES:
        p = os.path.join(D, st.replace(" ", "-") + ".js")
        if not os.path.exists(p) or st == "District of Columbia": continue
        g = ca.jsargs(p, r"__geo\(")[1]
        for ly in ("ushouse", "senate", "statehouse", "schools"):
            n2 = sum(1 for r in ROWS[ly] if r[0] == st)
            n1 = len(g.get(ly) or [])
            if n1 != n2: v1diff.append((st, ly, n1, n2))

    # 7) identical-figure partial-overlap pairs listed in COVERAGE.md: do they still share figures?
    cov = open(os.path.join(V, "COVERAGE.md"), encoding="utf-8").read()
    m = re.search(r"\*\*Partial overlaps, not changed \(37 pairs, review\):\*\*(.*)", cov)
    pairs = []
    if m:
        for yr, st, x, y in re.findall(r"(20\d\d) ([A-Z][a-zA-Z ]+?): (.+?) / (.+?) \(IoU", m.group(1)):
            pairs.append((yr, st.strip(), x.strip(), y.strip()))
    sch = {(r[0], r[1]): r for r in ROWS["schools"]}
    pchk = []
    for yr, st, x, y in pairs:
        rx, ry = sch.get((st, x)), sch.get((st, y))
        vi = 3 if yr == "2024" else 4
        vx = rx[vi] if rx and len(rx) > vi else None; vy = ry[vi] if ry and len(ry) > vi else None
        pchk.append({"year": yr, "state": st, "a": x, "b": y, "found": bool(rx and ry), "still_identical": bool(vx and vy and vx == vy), "value": vx})

    # 8) per type x year inventory
    def cells(layer, yr): return {st: CELL.get("%s|%s|%s" % (st, layer, yr)) for st in STATES}
    INV = []
    def add(typ, yr, files, have, exp, exp_src, exp20, exp20_src, missing, mism, filled, exact, est, gray, gray_names, why, attrs, office, notes):
        INV.append(dict(type=typ, year=yr, files=files, have=have, expected=exp, expected_src=exp_src, expected_vintage=exp20,
                        expected_vintage_src=exp20_src, states_missing=missing, states_count_mismatch=mism, with_results=filled,
                        exact=exact, approx=est, gray=gray, gray_names=gray_names, gray_reason=why, attributes=attrs,
                        officeholders=office, notes=notes))
    T24 = "Census TIGER 2024 Gazetteer (%s)"; T20 = "Census TIGER 2020 Gazetteer (%s)"
    lay_meta = {"ushouse": ("US House (CD)", "v2/data/uscd.js (+ DC delegate from v2/data/dc.js)", "119CDs", "116CDs"),
                "senate": ("State senate (SLDU)", "v2/data/ussldu.js (+ DC wards from dc.js)", "sldu", "sldu, 2018 plans"),
                "statehouse": ("State house (SLDL)", "v2/data/ussldl.js (+ DC wards; NE mirrors its 49 LDs)", "sldl", "sldl, 2018 plans")}
    for ly in ("ushouse", "senate", "statehouse"):
        typ, files, s24, s20 = lay_meta[ly]
        for yr in ("2020", "2024"):
            vi = 4 if yr == "2020" else 3
            rows = ROWS[ly]; n = len(rows)
            byst = collections.Counter(r[0] for r in rows)
            e = sum(E24[ABBR[s]][ly] for s in STATES); e20 = sum(E20[ABBR[s]][ly] for s in STATES)
            if ly == "ushouse": e = sum(E24[ABBR[s]][ly] for s in STATES)
            if ly in ("senate", "statehouse"):
                e += E24["DC"]["senate"] - E24["DC"][ly]; e20 += E20["DC"]["senate"] - E20["DC"][ly]
            miss = [ABBR[s] for s in STATES if byst[s] == 0]
            mism = ["%s %d vs %d" % (ABBR[s], byst[s], E24[ABBR[s]][ly] if not (s == "District of Columbia" and ly != "ushouse") else E24["DC"]["senate"]) for s in STATES
                    if byst[s] != (E24[ABBR[s]][ly] if not (s == "District of Columbia" and ly != "ushouse") else E24["DC"]["senate"])]
            vint = ["%s %d->%d" % (ABBR[s], E20[ABBR[s]][ly], E24[ABBR[s]][ly]) for s in STATES if s != "District of Columbia" and E20[ABBR[s]][ly] != E24[ABBR[s]][ly]]
            fl = [r for r in rows if has(r[vi] if len(r) > vi else None)]
            est = [r for r in fl if ests(r[5] if len(r) > 5 else None, yr)]
            gr = [r for r in rows if not has(r[vi] if len(r) > vi else None)]
            gn = ["%s %s" % (ABBR[r[0]], r[1]) for r in gr]
            why = GRAY_REASON.get((ly, yr), "") if gr else ""
            notes = []
            if yr == "2020":
                notes.append("2020 results are shown on the 2024 lines (app rule). Election-day lines differ in %d states by district count (TIGER 2020 vs 2024: %s)%s." % (len(vint), ", ".join(vint[:14]) + (" …" if len(vint) > 14 else ""), "; states with equal counts may still have redrawn lines (2021-22 redistricting)" ))
            if ly == "ushouse":
                notes.append("At-large CDs coded '00' in %d states (%s; TIGER 2024 at-large states: %s); the map pop-up label code in v2/index.html (aname, build 18 block) turns '00' into %r. DC delegate is GEOID 1198 in data-v3/geo, injected from dc.js." % (len(atl), ", ".join(ABBR[s] for s in atl if s in ABBR), ", ".join(exp_atl), js_label))
            if ly == "statehouse":
                notes.append("TIGER counts districts, not seats: multi-member districts (e.g. NH, AZ, NJ, WV, VT, SD, ND, ID, WA, MD) have more members than districts; seat counts per chamber need the legislatures' own rosters (not fetched).")
            add(typ, yr, files, n, e, T24 % (s24 + ", 50 states + DC delegate" if ly == "ushouse" else s24 + " + 8 DC wards"), e20, T20 % s20, miss, mism,
                len(fl), len(fl) - len(est), len(est), len(gr), gn, why,
                "state, name/code, geometry, 2024 [D,R,total], 2020 [D,R,total], flag (est/e24/e20/cty); GEOID only in data-v3/geo/%s.csv" % ly,
                "no", " ".join(notes))
    # schools by TIGER set
    for t, lab, gs in (("unsd", "School districts, unified", "unsd"), ("elsd", "School districts, elementary", "elsd"), ("scsd", "School districts, secondary", "scsd")):
        for yr in ("2020", "2024"):
            vi = 4 if yr == "2020" else 3
            rows = [r for r in ROWS["schools"] if sset.get((r[0], r[1])) == t]
            byst = collections.Counter(r[0] for r in rows)
            e = sum(E24[ABBR[s]][t] for s in STATES); e20 = sum(E20[ABBR[s]][t] for s in STATES)
            miss = sorted(ABBR[s] for s in STATES if E24[ABBR[s]][t] and byst[s] == 0)
            mism = ["%s %d vs %d" % (ABBR[s], byst[s], E24[ABBR[s]][t]) for s in STATES if byst[s] != E24[ABBR[s]][t] and not (s == "District of Columbia" and t == "unsd")]
            fl = [r for r in rows if has(r[vi] if len(r) > vi else None)]
            est = [r for r in fl if ests(r[5] if len(r) > 5 else None, yr)]
            gr = [r for r in rows if not has(r[vi] if len(r) > vi else None)]
            gst = collections.Counter(r[0] for r in gr)
            why = "; ".join("%s %d: %s" % (ABBR[s], c, SCHOOL_REASON.get(s, DEFAULT_SCHOOL_REASON)) for s, c in gst.most_common())
            vint = sum(abs(E20[ABBR[s]][t] - E24[ABBR[s]][t]) for s in STATES)
            add(lab, yr, "v2/data/ussch.js (+ DCPS from dc.js)", len(rows), e, T24 % gs, e20, T20 % gs, miss, mism,
                len(fl), len(fl) - len(est), len(est), len(gr), ["%s %s" % (ABBR[r[0]], r[1]) for r in gr], why,
                "state, name (unique since 9ff4c00), geometry, 2024, 2020, flag; type and GEOID only in data-v3/geo/schools.csv; PACK.lists.schools in v2/index.html carries a type label",
                "no (no board members anywhere)", "sum of per-state |TIGER 2020 - 2024| counts = %d" % vint if yr == "2020" else "")
    # DC wards
    for yr in ("2020", "2024"):
        vi = 4 if yr == "2020" else 3
        rows = ROWS["dcwards"]; fl = [r for r in rows if has(r[vi])]
        add("DC wards", yr, "v2/data/dc.js (W)", len(rows), E24["DC"]["senate"], T24 % "sldu, DC = council wards", E20["DC"]["senate"], T20 % "sldu, 2012 ward plan",
            [], [], len(fl), len(fl), 0, len(rows) - len(fl), [], "",
            "state, 'Ward n', geometry, 2024, 2020 (DCBOE certified)", "no",
            "2020 values are DCBOE's 2012-plan ward totals drawn on the 2022 lines (COVERAGE.md build 1559 caveat).")
    # counties as governments
    cog = "2022 Census of Governments (Census Bureau, 2022_gov_org_meth_tech_doc.pdf): 3,031 county governments, 19,491 municipal, 16,214 town/township (national only)"
    for yr in ("2020", "2024"):
        cs = cells("counties", yr)
        n = sum(c["n"] for c in cs.values() if c); f = sum(c["filled"] for c in cs.values() if c)
        e = sum(E24[ABBR[s]]["counties"] for s in STATES); e20 = sum(E20[ABBR[s]]["counties"] for s in STATES)
        mism = ["%s %d vs %d" % (ABBR[s], c["n"], c.get("exp") or 0) for s, c in cs.items() if c and c.get("exp") and c["n"] != c["exp"]]
        nov = [s for s, c in cs.items() if c and c["n"] - c["filled"] > 0]
        add("Counties (as governments)", yr, "v2/data/uscounties.js + data/election%s.js (v1, read-only) + v2/data/ak.js boroughs" % yr, n, e,
            T24 % "counties; county governments: 3,031 per " + cog, e20, T20 % "counties (CT 8 old counties in 2020, 9 planning regions in 2024)",
            [], mism, f, f - (cs.get("Alaska") or {}).get("est", 0), (cs.get("Alaska") or {}).get("est", 0), n - f,
            ["Hawaii Kalawao County"] if "Hawaii" in nov else [], "Kalawao County votes are reported with Maui County (official)",
            "state, name, geometry; results keyed 'State|County' by name in data/election20XX.js (no FIPS); GEOID in data-v3/geo/counties.csv",
            "no", "Map counts county-equivalents (TIGER). Governments differ: CT and RI have no county governments, consolidated city-counties count as municipalities (CoG); no government/area flag in v2.")
    # municipalities (towns = county subdivisions; places)
    pl = gaz(a.place24) if os.path.exists(a.place24) else []
    inc = collections.Counter(r["USPS"] for r in pl if r.get("FUNCSTAT") == "A")
    v1pl = collections.Counter(); v1cdp = collections.Counter()
    for st in STATES:
        p = os.path.join(D, st.replace(" ", "-") + ".js")
        if not os.path.exists(p): continue
        g = ca.jsargs(p, r"__geo\(")[1]
        for r in g.get("places") or []:
            (v1cdp if str(r[1]).endswith(" CDP") else v1pl)[st] += 1
    for yr in ("2020", "2024"):
        cs = cells("towns", yr)
        n = sum(c["n"] for c in cs.values() if c and c["status"] != "-")
        e = sum((c.get("exp") or 0) for c in cs.values() if c and c["status"] != "-")
        mism = ["%s %d vs %d" % (ABBR[s], c["n"], c["exp"]) for s, c in cs.items() if c and c["status"] == "S" and c.get("exp")]
        add("Towns/townships (county subdivisions as governments)", yr, "data/<State>.js towns (v1, read-only) + v2/data/parts/<State>.js", n, e,
            T24 % "cousubs in states with governmental MCDs, all FUNCSTAT except N/S/I; township governments 16,214 per " + cog, sum(E20[ABBR[s]]["towns"] for s in STATES) or "unknown",
            T20 % "cousubs, same rule", [], mism, n, "runtime", "runtime", 0, [], "",
            "county, name, geometry; no stored results (computed at runtime from precincts, ≈ when area-weighted); GEOID only for Iowa townships (data-v3/geo/towns.csv)",
            "no", "Every town value is a runtime precinct aggregation; app hides parts rows by normT() name de-duplication (IL 473, NY 197, KS 154, IA 173 …).")
        add("Municipalities (incorporated places)", yr, "data/<State>.js places (v1, read-only)", sum(v1pl.values()), sum(inc.values()) or "unknown",
            "Census TIGER 2024 place Gazetteer, FUNCSTAT A (active incorporated places); municipal governments 19,491 per " + cog, "unknown", "2020 place counts not fetched",
            [ABBR[s] for s in STATES if inc[ABBR[s]] and not v1pl[s]], ["%s %d vs %d" % (ABBR[s], v1pl[s], inc[ABBR[s]]) for s in STATES if inc[ABBR[s]] and abs(v1pl[s] - inc[ABBR[s]]) > 0.02 * inc[ABBR[s]]],
            "unknown", 0, 0, "unknown", [], "",
            "state, name with LSAD suffix, geometry; CDPs (%d rows) mixed in; no GEOID; results only through the town/precinct runtime path" % sum(v1cdp.values()), "no",
            "Counted rows without ' CDP' suffix vs TIGER FUNCSTAT A; v1 file is outside the lane (read-only).")
    # precincts
    for yr in ("2020", "2024"):
        cs = cells("precincts", yr)
        n = sum(c["n"] for c in cs.values() if c); f = sum(c["filled"] for c in cs.values() if c)
        vs = sum(c.get("votes") or 0 for c in cs.values() if c); off = sum(c.get("official") or 0 for c in cs.values() if c)
        miss = [ABBR[s] for s, c in cs.items() if c and c["n"] == 0]
        low = ["%s %.1f%%" % (ABBR[s], 100 * c["ratio"]) for s, c in cs.items() if c and c.get("ratio") and not 0.98 <= c["ratio"] <= 1.02]
        off_c = ["%s %d" % (ABBR[s], len(c.get("cty_off") or [])) for s, c in cs.items() if c and c.get("cty_off")]
        none_c = ["%s %d" % (ABBR[s], len(c.get("cty_none") or [])) for s, c in cs.items() if c and c.get("cty_none")]
        add("Precincts", yr, "data/precincts%s/<State>.js (v1, read-only; no v2 override per orchestrator) + v2/data/precincts%s-DC.js; v2/data/x20 (2020->2024 links)" % (yr, yr), n, "unknown",
            "no TIGER count for election-year precincts; official per-state counts would come from the EAC EAVS %s (not fetched)" % yr, "unknown", "",
            miss, low, f, "n/a", "n/a", "n/a (%d zero-vote rows)" % (n - f), [], "zero-vote rows (e.g. CA SR precincts with no voters, TX, WA); counties outside 90-110 %% (Dem+Rep): %s; counties with no precincts: %s" % (", ".join(off_c) or "none", ", ".join(none_c) or "none"),
            "county, name, D, R, total, geometry; key 'County|Precinct' (not unique, see QUESTIONS.md Q-G7); no precinct id", "no",
            "votes %.2f%% of official state totals; states outside 98-102 %%: %s" % (100.0 * vs / off if off else 0, ", ".join(low) or "none"))

    # 8b) county shortfalls in the 2024 precinct files of the states handed to this lane (OR, WY, MO) + SD
    E24res = ca.jsargs(os.path.join(D, "election2024.js"), r"ELECTION2024\s*=")[0]
    short = {}
    for st in ("Oregon", "Wyoming", "Missouri", "South Dakota"):
        c = CELL.get("%s|precincts|2024" % st) or {}
        pr = ca.jsargs(os.path.join(D, "precincts2024", st.replace(" ", "_") + ".js"), r"__prec\(")[1]
        by = collections.Counter(); by2 = collections.Counter()
        for r in pr: by[r[0]] += r[4] or 0; by2[r[0]] += (r[2] or 0) + (r[3] or 0)
        lst = []
        for cn in (c.get("cty_off") or []) + (c.get("cty_none") or []):
            v = E24res.get(st + "|" + cn)
            if v: lst.append({"county": cn, "precinct_votes": by[cn], "official_votes": v[2], "dem_rep_ratio": round(by2[cn] / ((v[0] or 0) + (v[1] or 0)), 3), "missing": v[2] - by[cn]})
        short[st] = {"precinct_votes": c.get("votes"), "official": c.get("official"), "ratio": c.get("ratio"), "counties": lst}
    # gray 2024 schools in those states
    for st in short:
        short[st]["gray_schools_2024"] = [r[1] for r in ROWS["schools"] if r[0] == st and not has(r[3] if len(r) > 3 else None)]
        short[st]["gray_statehouse_2024"] = [r[1] for r in ROWS["statehouse"] if r[0] == st and not has(r[3] if len(r) > 3 else None)]
    # 9) sizes of v2 files a fix would touch
    sizes = {}
    for fn in ("uscd.js", "ussldu.js", "ussldl.js", "ussch.js", "dc.js", "uscounties.js", "ak.js", "parts/Oregon.js", "parts/Wyoming.js", "parts/Missouri.js", "parts/Maine.js", "x20/Oregon.js", "x20/Wyoming.js", "x20/Missouri.js"):
        sizes["v2/data/" + fn] = fsize(os.path.join(V, fn))
    for fn in ("data/precincts2024/Oregon.js", "data/precincts2024/Wyoming.js", "data/precincts2024/Missouri.js", "v2/index.html"):
        sizes[fn] = fsize(os.path.join(R, fn))

    res = dict(audited=head, inventory=INV, pack=packchk, at_large=dict(rows=atl, tiger=exp_atl, label=js_label), dupes=dupes,
               geoid=gidchk, v1_vs_v2=v1diff, partial_pairs=pchk, attributes=attr, officeholder_hits=off_hits, sizes=sizes,
               shortfalls=short, precinct_cells={k: CELL.get(k) for k in ("Oregon|precincts|2024", "Wyoming|precincts|2024", "Missouri|precincts|2024", "South Dakota|precincts|2024")})
    os.makedirs(a.out, exist_ok=True)
    json.dump(res, open(os.path.join(a.out, "inst_audit.json"), "w"), indent=1, ensure_ascii=False, default=list)
    with open(os.path.join(a.out, "inst_gaps.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["type", "year", "files", "have", "expected", "expected_source", "expected_election_vintage", "expected_election_vintage_source",
                    "states_missing", "states_count_mismatch", "with_results", "exact", "approx", "gray", "gray_names", "gray_reason", "attributes", "officeholders", "notes"])
        for r in INV:
            w.writerow([r["type"], r["year"], r["files"], r["have"], r["expected"], r["expected_src"], r["expected_vintage"], r["expected_vintage_src"],
                        " ".join(r["states_missing"]), "; ".join(r["states_count_mismatch"]), r["with_results"], r["exact"], r["approx"], r["gray"],
                        "; ".join(r["gray_names"]), r["gray_reason"], r["attributes"], r["officeholders"], r["notes"]])
    # compact table for AUDIT.md (the narrative is written by hand around it)
    L = ["| Type | Year | Have | Expected (TIGER 2024) | Election-year lines (TIGER 2020) | With results | exact / ≈ | Gray | Officeholders |", "|---|---|---|---|---|---|---|---|---|"]
    for r in INV:
        L.append("| %s | %s | %s | %s | %s | %s | %s / %s | %s | %s |" % (r["type"], r["year"], r["have"], r["expected"], r["expected_vintage"], r["with_results"], r["exact"], r["approx"], r["gray"], r["officeholders"].split(" ")[0]))
    print("\n".join(L))

if __name__ == "__main__":
    main()
