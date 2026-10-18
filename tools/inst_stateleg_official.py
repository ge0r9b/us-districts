#!/usr/bin/env python3
"""Official state legislature rosters -> replace the OpenStates fallback state by state (institutions lane).

For each state in PARSERS the official roster(s) fetched into inst-raw/rosters/ (sha256 + URL in SOURCES.txt) are
parsed to (chamber, district label, name, party, official id, serving?). Then:
  current file  : the state's OpenStates rows are replaced by the official rows that are serving today, joined by
                  district label exactly as tools/inst_officeholders_stateleg.py does. person_id keeps the OpenStates
                  ocd-person id when the same unit has an OpenStates member with the same last name (cross-reference),
                  else it is the official id. Official members in units OpenStates leaves empty are added.
  2024 file     : official rosters carry no in-office dates, so rows stay timed by OpenStates (snapshot 2025-04-01);
                  each row is cross-checked: `official_check` = confirmed (same unit, same last name in the official
                  session roster, or in the current roster for states without one) / not_in_official_roster.
                  Empty 2024 units are NOT filled from undated rosters (a member there may have started after the
                  snapshot; filling would be a guess).
  diffs         : every disagreement between the official roster and OpenStates (missing either side, party,
                  different person in a unit) goes to stateleg_official_diffs.csv.
Special cases, never joined to a fake unit: NH House floterial districts (labels outside the 164 TIGER 2024 SLDL base
districts; NH RSA 662:5 overlays) -> join_status no_v3_unit_floterial; Maine's tribal representatives -> no_v3_unit_tribal.
usage: inst_stateleg_official.py <repo> --raw inst-raw/rosters --out data-v3/inst --retrieved DATE
"""
import sys, os, re, csv, json, glob, html, hashlib, unicodedata, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inst_officeholders_stateleg as L

ORD = {"FIRST": "1ST", "SECOND": "2ND", "THIRD": "3RD", "FOURTH": "4TH", "FIFTH": "5TH", "SIXTH": "6TH", "SEVENTH": "7TH", "EIGHTH": "8TH",
       "NINTH": "9TH", "TENTH": "10TH", "ELEVENTH": "11TH", "TWELFTH": "12TH", "THIRTEENTH": "13TH", "FOURTEENTH": "14TH", "FIFTEENTH": "15TH",
       "SIXTEENTH": "16TH", "SEVENTEENTH": "17TH", "EIGHTEENTH": "18TH", "NINETEENTH": "19TH", "TWENTIETH": "20TH"}
def fold(s): return re.sub(r"[^A-Z]", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper())
def last(name):
    n = name.strip()
    for _ in range(2): n = re.sub(r",?\s+(JR|SR|II|III|IV|V|PH\.?\s?D|M\.?\s?D|ED\.?\s?D|J\.?\s?D|ESQ)\.?$", "", n, flags=re.I)
    if "," in n: n = n.split(",")[0]
    else: n = n.split()[-1] if n.split() else n
    return fold(n)
def same(a_last, full):
    """official last name vs an OpenStates full name: equal, contained, or one hyphen/space part equal"""
    if not a_last: return False
    b = last(full); fb = fold(full)
    if a_last == b or a_last in fb or (b and b in a_last): return True
    return False
def npty(p):
    p = p.strip().upper()
    if p in ("U", "UNENROLLED", "NO PARTY AFFILIATION", "NPA", "I", "INDEPENDENT", "UNAFFILIATED", "NONPARTISAN"): return "I"
    if p == "DFL" or p.startswith("DEMOCRAT"): return "D"
    return p[0]
def txt(s): return html.unescape(re.sub(r"<[^>]+>", " ", s)).strip()

def p_nh(R):
    out = []
    for r in csv.DictReader(open(R + "/nh_Members.txt", encoding="latin-1"), delimiter="\t"):
        ch = "upper" if r["LegislativeBody"] == "S" else "lower"
        d = r["District"].strip() if ch == "upper" else "%s %s" % (r["County"].strip(), r["District"].strip())
        out.append(dict(chamber=ch, district=d, name=" ".join(x for x in (r["FirstName"], r["MiddleName"], r["LastName"]) if x.strip()), last=fold(r["LastName"]),
                        party=r["party"].strip(), oid="nh-seat-%s" % r["seatno"].strip() if r["seatno"].strip() not in ("", "0") else "", serving=r["electedStatus"].strip() != "Former",
                        session=True, status_src=r["electedStatus"].strip()))
    return out, "New Hampshire General Court, Members.txt (gc.nh.gov/downloads)", "https://gc.nh.gov/downloads/Members.txt", ["nh_Members.txt"]
def p_vt(R):
    out = []
    for r in json.load(open(R + "/vt_people_2026.json"))["data"]:
        ch = "upper" if r["Title"] == "Senator" else "lower"
        d = re.sub(r"\s+District$", "", r["District"].strip())
        out.append(dict(chamber=ch, district=d, name=" ".join(x for x in (r["FirstName"], r["MI"], r["LastName"], r["NameSuffix"]) if x and x.strip()), last=fold(r["LastName"]),
                        party=r["Party"], oid="vt-%s" % r["PersonID"], serving=not r["TerminationReason"].strip(), session=True, status_src=r["TerminationReason"].strip()))
    return out, "Vermont General Assembly, people/loadAll/2026 (2025-2026 biennium)", "https://legislature.vermont.gov/people/loadAll/2026", ["vt_people_2026.json"]
def p_ma(R):
    cur = set()
    for f in ("ma_house_current.html", "ma_senate_current.html"):
        cur |= set(re.findall(r"Legislators/Profile/([A-Za-z_0-9]+)", open(R + "/" + f).read()))
    out = []
    for f in sorted(glob.glob(R + "/ma194/*.json")):
        m = json.load(open(f)); ch = "upper" if m["Branch"] == "Senate" else "lower"
        d = m["District"].strip()
        out.append(dict(chamber=ch, district=d, name=m["Name"], last=last(m["Name"]), party=m["Party"], oid="ma-" + m["MemberCode"],
                        serving=m["MemberCode"] in cur, session=True, status_src="on current member page" if m["MemberCode"] in cur else "194th General Court, not on current member page"))
    return out, "Massachusetts Legislature API, 194th General Court LegislativeMembers + current member pages", "https://malegislature.gov/api/GeneralCourts/194/LegislativeMembers", ["ma_194.json", "ma194/*.json", "ma_house_current.html", "ma_senate_current.html"]
def p_mn(R):
    out = []
    for m in json.load(open(R + "/mn_senate.json"))["members"]:
        out.append(dict(chamber="upper", district=str(m["dist"]), name=m["preferred_full_name"], last=fold(m["preferred_last_name"]), party=m["party"], oid="mn-sen-%s" % m["mem_id"], serving=True, session=False, status_src=""))
    t = open(R + "/mn_house.html").read(); seen = set()
    for pid, nm, d, pty in re.findall(r'<a href="/members/profile/(\d+)"><b>([^<(]+)\((\d+[AB]),\s*([^)]+)\)</b>', t):
        if pid in seen: continue
        nm = html.unescape(nm); seen.add(pid); out.append(dict(chamber="lower", district=d, name=nm.strip(), last=last(nm), party=pty.strip(), oid="mn-house-" + pid, serving=True, session=False, status_src=""))
    return out, "Minnesota Senate members API + Minnesota House member list (2025-2026)", "https://www.senate.mn/api/members ; https://www.house.mn.gov/members/list", ["mn_senate.json", "mn_house.html"]
def p_mo(R):
    t = open(R + "/mo_house.html").read(); out = []; seen = set()
    for row in re.findall(r"<tr>(.*?)</tr>", t, re.S):
        td = [txt(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if len(td) >= 5 and re.fullmatch(r"\d{3}", td[3] or ""):
            if (td[3], td[1]) in seen: continue
            seen.add((td[3], td[1]))
            vac = "vacant" in (td[1] + td[2]).lower()
            if vac: out.append(dict(chamber="lower", district=td[3], name="", last="", party="", oid="", serving=False, session=False, status_src="Vacant", vacant=True)); continue
            out.append(dict(chamber="lower", district=td[3], name="%s %s" % (td[2], td[1]), last=fold(td[1].split()[-1] if td[1].split() else td[1]), party=td[4], oid="mo-house-%s" % td[3], serving=True, session=False, status_src=""))
    return out, "Missouri House of Representatives, member grid (2026)", "https://house.mo.gov/MemberGridCluster.aspx", ["mo_house.html"]
def p_pa(R):
    out = []
    for f, ch in (("pa_house.html", "lower"), ("pa_senate.html", "upper")):
        t = open(R + "/" + f).read(); seen = set()
        for nm, pty, d in re.findall(r'thumb-info-inner">([^<]+)</span>\s*<span class="thumb-info-type[^"]*">\s*([A-Za-z]+)<br>District (\d+)', t):
            if (d, nm) in seen: continue
            seen.add((d, nm)); out.append(dict(chamber=ch, district=d, name=html.unescape(nm.strip()), last=last(html.unescape(nm)), party=pty, oid="pa-%s-%s" % (ch, d), serving=True, session=False, status_src=""))
    return out, "Pennsylvania General Assembly, House and Senate member lists (palegis.us)", "https://www.palegis.us/house/members ; https://www.palegis.us/senate/members", ["pa_house.html", "pa_senate.html"]
def p_ny(R):
    t = open(R + "/ny_assembly.html").read(); out = []
    for slug, nm, d in re.findall(r'<h3 class="mem-name"><a rel="noopener" href="/mem/([^"]+)">\s*([^<]+?)\s*<span>District (\d+)</span>', t):
        out.append(dict(chamber="lower", district=d, name=html.unescape(nm), last=last(html.unescape(nm)), party="", oid="ny-asm-" + slug, serving=True, session=False, status_src=""))
    return out, "New York State Assembly member list (party not listed there)", "https://nyassembly.gov/mem/", ["ny_assembly.html"]
def p_ca(R):
    t = open(R + "/ca_assembly.html").read(); out = []
    for d, pty, nm in re.findall(r'data-district="(\d+)" data-party="([^"]*)"[^>]*>.*?<h2 class="members-list__name">([^<]+)</h2>', t, re.S):
        nm = html.unescape(nm); out.append(dict(chamber="lower", district=d, name=" ".join(reversed([x.strip() for x in nm.split(",", 1)])), last=last(nm), party=pty, oid="ca-asm-" + d, serving=True, session=False, status_src=""))
    return out, "California State Assembly member list", "https://www.assembly.ca.gov/assemblymembers", ["ca_assembly.html"]

NODISTRICT = collections.defaultdict(list)   # (state, chamber) -> session-roster names whose member page no longer shows a district (left office)

def p_tx(R):
    out = []
    for f in sorted(glob.glob(R + "/tx89/*.html")):
        t = open(f, errors="ignore").read(); ch = "upper" if os.path.basename(f).startswith("S_") else "lower"
        m = re.search(r"<h1>Information for (?:Rep\.|Sen\.)\s*([^<]+)</h1>", t); d = re.search(r'id="lblDistrict">(\d+)<', t)
        if not m or "Lt. Gov." in m.group(0): continue
        nm = html.unescape(m.group(1).strip())
        if not d: NODISTRICT[("Texas", ch)].append(nm); continue   # 89th member whose page has no district any more: left office during the 89th
        out.append(dict(chamber=ch, district=d.group(1), name=nm, last=last(nm), party="", oid="tx-" + os.path.basename(f)[:-5], serving=True, session=True,
                        status_src="89th Legislature member page", nostatus=True))
    return out, "Texas Legislature Online, 89th Legislature member pages (party not listed there)", "https://capitol.texas.gov/Members/Members.aspx?Chamber=H ; ...Chamber=S", ["tx_house.html", "tx_senate.html", "tx89/*.html"]

PARSERS = {"Texas": p_tx, "New Hampshire": p_nh, "Pennsylvania": p_pa, "Massachusetts": p_ma, "Minnesota": p_mn, "Vermont": p_vt, "Missouri": p_mo, "New York": p_ny, "California": p_ca}
# chambers a state's official source covers (the other chamber stays OpenStates)
CHAMBERS = {"Missouri": {"lower"}, "New York": {"lower"}, "California": {"lower"}}
import inst_stateleg_parsers2 as P2
P2.setup(fold, last)
for _st, _f in P2.EXTRA.items():
    def _both(R, a=PARSERS[_st], b=_f):
        x, n1, u1, f1 = a(R); y, n2, u2, f2 = b(R); return x + y, n1 + "; " + n2, u1 + " ; " + u2, f1 + f2
    PARSERS[_st] = _both; CHAMBERS.pop(_st, None)
PARSERS.update(P2.PARSERS); CHAMBERS.update(P2.CHAMBERS)
FALLBACK = {
    "New York/upper": "nysenate.gov returns 403 (Cloudflare challenge) to the box; the official alternative, the NY Senate Open Legislation API (legislation.nysenate.gov/api/3/members), returns 401 without an API key, and a key needs an account sign-up (not done)",
    "Missouri/upper": "senate.mo.gov senator listing URL returned 404; not located this round",
}

FALLBACK.update(P2.FALLBACK)

def main():
    a = sys.argv[1:]; repo = a[0]; R = a[a.index("--raw") + 1]; out = a[a.index("--out") + 1]; retrieved = a[a.index("--retrieved") + 1]
    join, units = L.build_join(repo)
    shas = {}
    for ln in open(R + "/SOURCES.txt"):
        p = ln.split("  ");
        if len(p) >= 2: shas[p[1]] = p[0]
    cur = list(csv.DictReader(open(os.path.join(out, "officeholders_stateleg_current.csv"))))
    v24 = list(csv.DictReader(open(os.path.join(out, "officeholders_stateleg_2024.csv"))))
    COLS = list(cur[0].keys()) + ["official_check"]
    diffs = []; report = {}
    newcur = [r for r in cur]; 
    for st, P in PARSERS.items():
        recs, srcname, url, files = P(R); chs = CHAMBERS.get(st, {"upper", "lower"})
        sha = "; ".join("%s %s" % (f, shas.get(f, "")) for f in files)
        for x in recs:
            if re.search(r"\bvacant\b", x["name"], re.I) or x.get("vacant"):
                x["vacant"] = True; x["serving"] = False; x["status_src"] = "listed as vacant"; x["last"] = ""
            if x.get("vacant"): x["unit"], x["seat"], x["js"] = join(st, x["chamber"], x["district"]); continue
            g, seat, js = join(st, x["chamber"], x["district"])
            if js == "no_v3_unit" and st == "Massachusetts":   # House labels use '3rd', Senate labels 'Third' (TIGER both ways)
                g, seat, js = join(st, x["chamber"], " ".join(ORD.get(w.upper(), w) for w in x["district"].split()))
            if js == "no_v3_unit" and st == "New Hampshire" and x["chamber"] == "lower": js = "no_v3_unit_floterial"
            if x.get("tribal"):
                g, seat, js = "", "", "no_v3_unit_tribal"
                osl = [r["district"] for r in cur if r["state"] == st and r["join_status"] == "no_v3_unit_tribal" and same(x["last"], r["name"])]
                if osl: x["district"] = osl[0]   # use the tribe label OpenStates carries for this person (the official list gives only seat numbers)
            x["unit"], x["seat"], x["js"] = g, seat, "joined" if js.startswith("joined") else js
        if any(x.get("nostatus") for x in recs):
            grp = collections.defaultdict(list)
            for x in recs: grp[(x["chamber"], x["unit"])].append(x)
            for k, xs in grp.items():
                osn = [r["name"] for r in cur if r["state"] == st and r["unit_geoid"] == k[1] and (("upper" if r["chamber"] in ("upper", "legislature") else "lower") == k[0])]
                if not osn and k[1]:   # undated session roster + OpenStates has nobody current here: the listed member may have left; do not assert
                    for x in xs:
                        if x.get("serving") and not x.get("term_start"):
                            x["serving"] = False; x["status_src"] += "; NOT ASSERTED: undated session roster and OpenStates lists no current member for this unit"
                            diffs.append({"state": st, "chamber": x["chamber"], "unit_geoid": x["unit"], "district": x["district"], "kind": "session_roster_member_not_asserted_unit_empty_in_openstates", "official": x["name"], "openstates": ""})
                    continue
                if len(xs) > max(1, len(osn)):   # more listed members than seats (seat count taken from OpenStates current rows of the unit)
                    keep = [x for x in xs if any(same(x["last"], n) for n in osn)]
                    for x in xs:
                        if keep and x not in keep: x["serving"] = False; x["status_src"] += "; another listed member of this district is the current one (official list gives no status; resolved with OpenStates current)"
                        elif not keep: x["status_src"] += "; AMBIGUOUS: %d listed members for this district, none listed current by OpenStates" % len(xs)
        os_cur = [r for r in cur if r["state"] == st and (("upper" if r["chamber"] in ("upper", "legislature") else "lower") in chs)]
        by_unit = collections.defaultdict(list)
        for r in os_cur: by_unit[(("upper" if r["chamber"] in ("upper", "legislature") else "lower"), r["unit_geoid"] or "label:" + r["district"])].append(r)
        rep = {"source": srcname, "chambers": sorted(chs), "official_records": len(recs), "official_serving": sum(1 for x in recs if x["serving"]),
               "openstates_current_rows": len(os_cur)}
        rows = []; matched_os = set()
        for x in recs:
            if x.get("vacant") and x.get("unit"):
                rows.append({"unit_geoid": x["unit"], "unit_vintage": "sldu2024" if x["chamber"] == "upper" else "sldl2024", "join_status": "joined",
                             "entity_id": "%s-%s" % (L.AB[L.ST.index(st.replace(" ", "_"))].lower(), "senate" if x["chamber"] == "upper" else "house"), "seat": x["seat"],
                             "state": st, "chamber": x["chamber"], "district": x["district"], "person_id": "", "name": "", "party": "", "status": "vacant", "term_start": "", "term_end": "",
                             "note": "official roster lists this seat as vacant", "source": srcname, "source_url": url, "upstream_url": url, "source_id": "", "retrieved_at": retrieved,
                             "sha256": sha, "license": "official state legislature website (public record)", "official_check": "official"}); continue
            if not x["serving"]: continue
            k = (x["chamber"], x["unit"] or "label:" + x["district"])
            m = next((r for r in by_unit.get(k, []) if same(x["last"], r["name"])), None)
            if m: matched_os.add(id(m))
            if m and x["party"] and m["party"] and npty(x["party"]) != npty(m["party"]) and not x.get("tribal"):
                diffs.append({"state": st, "chamber": x["chamber"], "unit_geoid": x["unit"], "district": x["district"], "kind": "party_differs", "official": "%s (%s)" % (x["name"], x["party"]), "openstates": "%s (%s)" % (m["name"], m["party"])})
            if not m:
                o = by_unit.get(k, [])
                diffs.append({"state": st, "chamber": x["chamber"], "unit_geoid": x["unit"], "district": x["district"], "kind": "official_member_not_in_openstates_unit" if o else "official_member_in_unit_openstates_leaves_empty",
                              "official": "%s (%s)" % (x["name"], x["party"]), "openstates": "; ".join("%s (%s)" % (r["name"], r["party"]) for r in o)})
            note = ["official roster"]
            if x["js"] == "no_v3_unit_floterial": note.append("NH House floterial district: label '%s' is not among the 164 TIGER 2024 SLDL base districts (floterials overlay base districts, RSA 662:5); no v3 unit, deliberately not joined" % x["district"])
            elif x["js"] == "no_v3_unit_tribal": note.append("Maine tribal representative (non-voting seat with no district); deliberately not joined")
            elif x["js"] == "no_v3_unit": note.append("district label '%s' matches no unit of data-v3/geo" % x["district"])
            if x.get("status_src"): note.append("official status: %s" % x["status_src"])
            if not m: note.append("no OpenStates member with this last name in this unit")
            if not x["party"] and m and m["party"]: note.append("party and term_start from OpenStates %s (official page lists no party)" % m["person_id"])
            rows.append({"unit_geoid": x["unit"], "unit_vintage": "sldu2024" if x["chamber"] == "upper" else "sldl2024", "join_status": x["js"],
                         "entity_id": "%s-%s" % (L.AB[L.ST.index(st.replace(" ", "_"))].lower(), "senate" if x["chamber"] == "upper" else "house"), "seat": x["seat"],
                         "state": st, "chamber": x["chamber"], "district": x["district"], "person_id": m["person_id"] if m else x["oid"], "name": x["name"], "party": x["party"] or (m["party"] if m else ""),
                         "status": "serving", "term_start": x.get("term_start") or (m["term_start"] if m else ""), "term_end": x.get("term_end") or (m["term_end"] if m else ""), "note": "; ".join(note), "source": srcname, "source_url": url,
                         "upstream_url": url, "source_id": x["oid"], "retrieved_at": retrieved, "sha256": sha, "license": "official state legislature website (public record)",
                         "official_check": "official"})
        for r in os_cur:
            if id(r) not in matched_os:
                diffs.append({"state": st, "chamber": r["chamber"], "unit_geoid": r["unit_geoid"], "district": r["district"], "kind": "openstates_member_not_in_official_roster", "official": "", "openstates": "%s (%s)" % (r["name"], r["party"])})
        # Maine-style tribal or other no-unit OpenStates rows outside these states are untouched
        ids = {id(r) for r in os_cur}
        newcur = [r for r in newcur if id(r) not in ids] + rows
        units_filled = {(r["chamber"], r["unit_geoid"]) for r in rows if r["unit_geoid"] and r["status"] != "vacant"}
        os_filled = {(("upper" if r["chamber"] in ("upper", "legislature") else "lower"), r["unit_geoid"]) for r in os_cur if r["unit_geoid"]}
        rep.update(official_rows_written=len(rows), joined=sum(r["join_status"] == "joined" and r["status"] != "vacant" for r in rows), vacant_rows=sum(r["status"] == "vacant" for r in rows),
                   floterial=sum(r["join_status"] == "no_v3_unit_floterial" for r in rows), no_v3_unit=sum(r["join_status"] == "no_v3_unit" for r in rows),
                   units_filled_official=len(units_filled), units_filled_openstates=len(os_filled), units_newly_filled=sorted(g for _, g in units_filled - os_filled),
                   units_empty_official=sorted(g for ch in chs for g in units[(st, ch)] if (ch, g) not in units_filled), diffs=sum(1 for d in diffs if d["state"] == st))
        # 2024 cross-check
        allrec = collections.defaultdict(set)
        for x in recs:
            if x["last"]: allrec[(x["chamber"], x["unit"] or "label:" + x["district"])].add(x["last"])
        c24 = collections.Counter()
        for r in v24:
            if r["state"] != st: continue
            ch = "upper" if r["chamber"] in ("upper", "legislature") else "lower"
            if ch not in chs: continue
            ok = any(same(l, r["name"]) for l in allrec.get((ch, r["unit_geoid"] or "label:" + r["district"]), ()))
            r["official_check"] = ("confirmed_%s" % ("session_roster" if recs and recs[0]["session"] else "current_roster")) if ok else "not_in_official_roster"
            if not ok and any(fold(n) == fold(r["name"]) for n in NODISTRICT.get((st, ch), ())):
                ok = True; r["official_check"] = "confirmed_session_roster_name_only"   # on the 89th roster, page no longer shows the district
            c24[r["official_check"]] += 1
            if not ok and recs[0]["session"]:
                diffs.append({"state": st, "chamber": ch, "unit_geoid": r["unit_geoid"], "district": r["district"], "kind": "2024_openstates_member_not_in_session_roster", "official": "", "openstates": "%s (%s)" % (r["name"], r["party"])})
        rep["vintage_2024_check"] = dict(c24); rep["official_vacancies"] = sorted("%s %s" % (x["chamber"], x["district"]) for x in recs if x.get("vacant")); report[st] = rep
        print(st, {k: v for k, v in rep.items() if k not in ("units_empty_official",)})
    for r in newcur: r.setdefault("official_check", r.get("official_check") or "openstates_fallback")
    for r in v24: r.setdefault("official_check", "openstates_fallback")
    newcur.sort(key=lambda x: (x["state"], x["chamber"], x["unit_geoid"] or "~", x["district"], x["name"]))
    for fn, rs in (("officeholders_stateleg_current.csv", newcur), ("officeholders_stateleg_2024.csv", v24)):
        with open(os.path.join(out, fn), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader()
            for r in rs: w.writerow({c: r.get(c, "") for c in COLS})
    with open(os.path.join(out, "stateleg_official_diffs.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["state", "chamber", "unit_geoid", "district", "kind", "official", "openstates"]); w.writeheader()
        for d in diffs: w.writerow(d)
    json.dump({"states": report, "fallback_reasons": FALLBACK, "current_rows": len(newcur),
               "current_joined": sum(r["join_status"] == "joined" for r in newcur), "current_official_rows": sum(r["official_check"] == "official" for r in newcur)},
              open(os.path.join(out, "stateleg_official_summary.json"), "w"), indent=1)
    print("current rows", len(newcur), "joined", sum(r["join_status"] == "joined" for r in newcur), "diffs", len(diffs), collections.Counter(d["kind"] for d in diffs))

if __name__ == "__main__":
    main()
