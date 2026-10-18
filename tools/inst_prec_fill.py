#!/usr/bin/env python3
"""Fix 3 (institutions lane): build replacement files for tools/fill_official_precincts.py (geo lane, unchanged) for
2024 counties whose precinct file (root data/precincts2024/<State>.js, v1, never edited) misses units, so that gray
2024 district rows can be computed. Nothing in the repo is written by this script.

Per county (CONFIG below, every choice has its reason):
  votes  : official precinct returns (county clerk / state election office); MEDSL 2024-elections-official (CC0) only
           where no official precinct file was fetched. dem = Harris, rep = Trump, total = all presidential candidates
           incl. write-ins (over/under votes excluded).
  shapes : the app's own 2024 precinct polygon for units it already has (joined by code/name); for a missing unit,
           the union of the named VEST 2020 precinct polygons from data/precincts2020/<State>.js (CC BY 4.0), only
           where the reason column shows the 2024 unit is the same territory (same precinct number, Census 2020 VTD code,
           or the 2024 unit name lists the 2020 precincts it merges).
  pool   : countywide units with no geography (absentee, central poll, write-ins) -> 'not_located'.
Checks (any failure stops the county): every unit with votes is matched once; a 2020 polygon is used once and is not
already covered by an app 2024 polygon (overlap < 5 % of its area); every new unit passes the 2020 consistency test of
tools/check_vs2020.py scaled for pooled votes (turnout ratio 0.7-1.4 after spreading not_located votes pro rata,
Republican share within 12 points); located + not_located Harris and Trump vs the county total in data/election2024.js
are reported (official source wins where they differ; see COVERAGE.md).
usage: inst_prec_fill.py <repo> <State> <out.json> [--report R.json]
"""
import sys, os, re, csv, json, collections, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coverage_audit as ca
from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely.ops import unary_union

RAW = "/workspace/w/inst-raw/fix3"
MEDSL = "/workspace/db/medsl24/%s24.csv"   # github.com/MEDSL/2024-elections-official individual_states/<st>24.zip (CC0)

def mp(enc, S=10000):
    ps = []
    for rg in enc:
        rr = []
        for f in rg:
            o = []; x = y = 0
            for k in range(0, len(f) - 1, 2): x += f[k]; y += f[k + 1]; o.append((x / S, y / S))
            if len(o) >= 3: rr.append(o)
        if rr: ps.append(Polygon(rr[0], rr[1:]))
    g = MultiPolygon(ps); return g if g.is_valid else g.buffer(0)

# ---------- vote readers ----------
def wy_pbp(county):
    """Wyoming SOS / county clerk 'Official Precinct-by-Precinct Summary', page 'United States President'."""
    pdf = "%s/wy/2024_%s_County_General_PbP.pdf" % (RAW, county)
    t = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
    sec = t.split("United States President", 1)[1].split("Total", 1)[0]
    out = {}
    for ln in sec.splitlines():
        m = re.match(r"\s*(\d+-\d+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$", ln)
        if m:
            r, d, l, w = (int(m.group(i).replace(",", "")) for i in (2, 3, 4, 5))
            out[m.group(1)] = [d, r, r + d + l + w]
    return out, "Wyoming county clerk, 2024 General 'Official Precinct-by-Precinct Summary' (%s County), United States President; total = Trump + Harris + Oliver + write-ins (over/under votes excluded). Published via the WY Secretary of State election results page" % county

def columbia_pdf(_):
    t = open("%s/or/c.txt" % RAW).read() if os.path.exists("%s/or/c.txt" % RAW) else subprocess.run(["pdftotext", "-layout", "%s/or/columbia_2024-11-05_SUMMARY-PRECINCT_certified.pdf" % RAW, "-"], capture_output=True, text=True).stdout
    i = t.index("Precinct Abstract Report", t.index("United States President and Vice President Federal"))
    sec = t[t.index("PRECINCT NAME", i):]
    out = {}
    for ln in sec.splitlines():
        m = re.match(r"(\d\d) (.+?)\s{2,}([\d\s]+)$", ln)
        if not m:
            if out and ln.strip().startswith("COUNTY TOTALS"): break
            continue
        n = [int(x) for x in m.group(3).split()]
        if len(n) != 13: continue
        reg, bal, blank, rfk, west, oli, terry, trump, stein, harris, wi, ov, un = n
        out[m.group(1)] = [harris, trump, rfk + west + oli + terry + trump + stein + harris + wi]
        if len(out) == 33: break
    return out, "Columbia County Clerk (OR), November 5, 2024 General Election Certified Final Results, Precinct Abstract Report (Dec 2, 2024), https://www.columbiacountyor.gov/media/Election/Abstracts/2024-11-05_SUMMARY-PRECINCT_certified.pdf ; total = all presidential candidates + write-ins"

def medsl(st_ab, county):
    P = collections.defaultdict(lambda: [0, 0, 0])
    for r in csv.DictReader(open(MEDSL % st_ab)):
        if r["office"] != "US PRESIDENT" or r["county_name"] != county or r["mode"] != "TOTAL": continue
        try: v = int(float(r["votes"]))
        except ValueError: continue
        k = r["precinct"]; P[k][2] += v
        cu = r["candidate"].upper()
        if "HARRIS" in cu: P[k][0] += v
        if "TRUMP" in cu: P[k][1] += v
    return dict(P), "MEDSL 2024-elections-official, individual_states/%s24 (CC0), compiled from the official county returns; US PRESIDENT, mode TOTAL; total = all candidates incl. write-ins" % st_ab

# ---------- per-county configuration ----------
nrm = lambda s: re.sub(r"[^A-Z0-9]", "", s.upper())
def mo_key(u):
    u = re.sub(r"^\d+_", "", u)
    m = re.match(r"2024-(\d\d)-(\d\d) 00:00:00$", u)   # Excel turned 'W-P' into a date in the MEDSL file: 2024-01-02 = Ward 1 Precinct 2
    return "W%dP%d" % (int(m.group(1)), int(m.group(2))) if m else u
COLE = {"CL/BRA": "Clark Township Brazito Precinct", "CL/EUG": "Clark Township Eugene Precinct", "JE/APF": "Jefferson Township Apache Flats Precinct",
        "JE/CCG": "Jefferson Township CC General Precinct", "JE/EXR": "Jefferson Township Expressway Rental Precinct", "JE/JCF": "Jefferson Township JC Fair Precinct",
        "JE/SCS": "Jefferson Township Scott Station", "LI/TAO": "Liberty Township Taos Precinct", "MA/CEN": "Marion Township Centertown Precinct",
        "MA/STM": "Marion Township St Martins Precinct", "MO/LOH": "Moreau Township Lohman Precinct", "MO/RUS": "Moreau Township Russellville Precinct",
        "OS/STT": "Osage Township St. Thomas Precinct", "OS/WAR": "Osage Township Wardsville"}
CONFIG = {
 "Oregon": {"Columbia County": dict(votes=lambda: columbia_pdf(None), unit_key=lambda u: u, app_key=lambda n: n.split()[0], pool=None,
     from2020={"10": ["10"], "15": ["15"], "21": ["21"], "35": ["35"], "48": ["48"]},
     why="same precinct number in VEST 2020 (Columbia keeps its 2-digit precinct numbers); 2020 polygon not covered by any app 2024 polygon")},
 "Wyoming": {
   "Uinta County": dict(votes=lambda: wy_pbp("Uinta"), unit_key=lambda u: u, app_key=lambda n: n.split()[0], pool=None,
     from2020={"4-1": ["FT. BRIDGER"]}, why="Census 2020 TIGER VTD 56041 VTDST20 000401 'FT. BRIDGER' = precinct 4-1; the only 2020 precinct not covered by the app's 2024 polygons"),
   "Weston County": dict(votes=lambda: wy_pbp("Weston"), unit_key=lambda u: u, app_key=lambda n: n.split()[0], pool=None,
     from2020={"1-1": ["NEWCASTLE RURAL OUTSIDE"], "4-1": ["UPTON INSIDE"], "5-3": ["NEWCASTLE SOUTH"]},
     why="Census 2020 TIGER VTD 56045 VTDST20 000101 / 000401 / 000503 = precincts 1-1 / 4-1 / 5-3; the three 2020 precincts not covered by the app's 2024 polygons")},
 "Missouri": {
   "Cape Girardeau County": dict(votes=lambda: medsl("mo", "CAPE GIRARDEAU"), unit_key=mo_key, app_key=lambda n: n, pool=r"ABSENTEE|CENTRAL POLL",
     from2020={"BYRD 5 & 6": ["Byrd 5/6"], "BROWN OWL PRECINCT": ["Brown Owl"], "CAMPSTER PRECINCT": ["Campster/Pecan Grove"], "HANOVER PRECINCT": ["Hanover"]},
     why="same rural precinct names as VEST 2020 (Campster = 2020 'Campster/Pecan Grove'); 2020 polygons not covered by the app's 2024 polygons"),
   "Cole County": dict(votes=lambda: medsl("mo", "COLE"), unit_key=lambda u: COLE.get(mo_key(u), mo_key(u)), app_key=lambda n: n, pool=r"ABSENTEE|WRITE-INS",
     from2020={"Jefferson Township Scott Station": ["Jefferson Township Scott Station"], "Osage Township Wardsville": ["Osage Township Wardsville"]},
     why="same township precinct names as VEST 2020; 2020 polygons not covered by the app's 2024 polygons"),
   "Miller County": dict(votes=lambda: medsl("mo", "MILLER"), unit_key=mo_key, app_key=lambda n: n, pool=r"^AB\.$",
     from2020={"ELDON NORTH": ["Eldon North"], "T-TOWN": ["Tuscumbia"]}, why="same precinct (T-TOWN = Tuscumbia, as in the county's other abbreviations L.O. = Lake Ozark, M.H. = Marys Home); 2020 polygons not covered by the app's 2024 polygons"),
   "Pettis County": dict(votes=lambda: medsl("mo", "PETTIS"), unit_key=mo_key, app_key=lambda n: n, pool=r"ABSENTEE",
     from2020={"1 WARD": ["1st Ward"], "4 WARD/SED W/FLAT CREEK": ["4th Ward/Sedalia W", "Flat Creek"], "BLACKWATER/LA MONTE/DRESDEN": ["Blackwater/La Monte", "Dresden"]},
     why="the 2024 unit name lists the 2020 precincts it merges; 2020 polygons not covered by the app's 2024 polygons")},
}

def main():
    a = sys.argv[1:]; repo, st, out = a[:3]
    rep = a[a.index("--report") + 1] if "--report" in a else None
    p20 = [r for r in ca.jsargs(os.path.join(repo, "data/precincts2020/%s.js" % st.replace(" ", "_")), r"__prec\(")[1]]
    p24 = [r for r in ca.jsargs(os.path.join(repo, "data/precincts2024/%s.js" % st.replace(" ", "_")), r"__prec\(")[1]]
    E = ca.jsargs(os.path.join(repo, "data/election2024.js"), r"ELECTION2024\s*=")[0]
    res = {"state": st, "year": "2024", "counties": {}}; report = {}
    for c, cf in CONFIG[st].items():
        votes, src = cf["votes"]()
        units = collections.defaultdict(lambda: [0, 0, 0])
        for u, v in votes.items():
            k = cf["unit_key"](u)
            for i in range(3): units[k][i] += v[i]
        pool = {k: v for k, v in units.items() if cf["pool"] and re.search(cf["pool"], k)}
        app = {}
        for r in p24:
            if r[0] == c: app.setdefault(nrm(cf["app_key"](r[1])), []).append(r)
        old20 = {r[1]: r for r in p20 if r[0] == c}
        appgeo = unary_union([mp(r[-1]) for rs in app.values() for r in rs])
        rows, problems, newu, used20 = [], [], [], set()
        for k, v in sorted(units.items()):
            if k in pool: continue
            if k in cf["from2020"]:
                names = cf["from2020"][k]
                if any(n not in old20 or n in used20 for n in names): problems.append("2020 polygon missing or reused for %s" % k); continue
                g = unary_union([mp(old20[n][-1]) for n in names]).buffer(0)
                ov = g.intersection(appgeo).area / g.area
                if ov >= 0.05: problems.append("%s: 2020 polygon %.1f %% under app 2024 polygons" % (k, 100 * ov))
                used20.update(names)
                v20 = [sum(old20[n][i] for n in names) for i in (2, 3, 4)]
                newu.append({"unit": k, "from2020": names, "votes2024": v, "votes2020": v20, "overlap_with_app_2024": round(ov, 4)})
                rows.append([k, v[0], v[1], v[2], mapping(g)])
            else:
                hit = app.get(nrm(cf["app_key"](k))) or app.get(nrm(k))
                if not hit: problems.append("unit %s (%d votes) has no polygon" % (k, v[2])); continue
                if len(hit) > 1: problems.append("unit %s matches %d app rows" % (k, len(hit))); continue
                rows.append([hit[0][1], v[0], v[1], v[2], mapping(mp(hit[0][-1]))])
        matched_app = {nrm(cf["app_key"](r[0])) for r in rows} | {nrm(r[0]) for r in rows}
        unmatched_app = [r[1] for rs in app.values() for r in rs if nrm(cf["app_key"](r[1])) not in matched_app and nrm(r[1]) not in matched_app]
        if unmatched_app: problems.append("app 2024 rows without a returns unit: %s" % unmatched_app)
        loc = [sum(r[i] for r in rows) for i in (1, 2, 3)]; nl = [sum(v[i] for v in pool.values()) for i in range(3)]
        scale = (loc[2] + nl[2]) / loc[2] if loc[2] else 0
        t20loc = sum(r[4] for r in p20 if r[0] == c)
        for u in newu:
            v, w = u["votes2024"], u["votes2020"]
            tr = v[2] * scale / w[2] if w[2] else None
            sh24 = v[1] / max(1, v[0] + v[1]); sh20 = w[1] / max(1, w[0] + w[1])
            u["turnout_ratio_scaled"] = round(tr, 3) if tr else None; u["rep_share_2024"] = round(sh24, 3); u["rep_share_2020"] = round(sh20, 3)
            if tr is None or not 0.7 <= tr <= 1.4 or abs(sh24 - sh20) > 0.12: problems.append("2020 consistency test failed for %s: %s" % (u["unit"], u))
        off = E.get(st + "|" + c)
        report[c] = {"source_votes": src, "units": len(units), "located_units": len(rows), "not_located": pool, "located": loc, "located_plus_not_located": [loc[i] + nl[i] for i in range(3)],
                     "election2024_js": off, "dem_rep_vs_election2024_js": round((loc[0] + nl[0] + loc[1] + nl[1]) / (off[0] + off[1]), 5) if off else None,
                     "new_units_from_2020": newu, "why": cf["why"], "problems": problems}
        if problems: print("FAIL", c, problems); continue
        res["counties"][c] = {"source": src + ". Shapes: the app's 2024 precinct polygons; for %s: VEST 2020 precinct polygons (CC BY 4.0) from data/precincts2020 (%s)" % (", ".join(u["unit"] for u in newu), cf["why"]),
                              "rows": rows, "not_located": pool}
        print("OK", c, "units", len(units), "located", len(rows), "new", [(u["unit"], u["turnout_ratio_scaled"]) for u in newu], "D+R vs election2024.js", report[c]["dem_rep_vs_election2024_js"])
    json.dump(res, open(out, "w"))
    if rep: json.dump(report, open(rep, "w"), indent=1, ensure_ascii=False)

if __name__ == "__main__":
    main()
