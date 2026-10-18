"""Official-roster parsers, batches 2+ (imported by tools/inst_stateleg_official.py). Each returns
(records, source name, source URL(s), raw files) like the parsers in inst_stateleg_official.py."""
import re, os, csv, glob, html, json

def setup(fold, last):
    globals().update(fold=fold, last=last)

def rec(ch, d, nm, pty, oid, **k):
    nm = html.unescape(re.sub(r"\s+", " ", nm)).strip()
    if "," in nm and not re.search(r",\s*(Jr|Sr|II|III|IV)\.?$", nm): nm = " ".join(reversed([x.strip() for x in nm.split(",", 1)]))
    return dict(dict(chamber=ch, district=str(d).strip(), name=nm, last=last(nm), party=pty.strip(), oid=oid, serving=True, session=False, status_src=""), **k)

def p_ct(R):
    out = []
    for r in csv.DictReader(open(R + "/ct_LegislatorDatabase.csv", encoding="latin-1")):
        ch = "upper" if r["office code"] == "S" else "lower"
        nm = " ".join(x for x in (r["first name"].strip(), r["middle initial"].strip(), r["last name"].strip(), r["suffix"].strip()) if x)
        out.append(dict(rec(ch, int(r["dist"]), nm, r["party"], "ct-%s%s" % (r["office code"], r["dist"].strip())), last=fold(r["last name"].split()[-1])))
    return out, "Connecticut General Assembly LegislatorDatabase.csv", "https://www.cga.ct.gov/ftp/pub/data/LegislatorDatabase.csv", ["ct_LegislatorDatabase.csv"]

def p_ms(R):
    out = []
    for f in sorted(glob.glob(R + "/ms_m/*")):
        t = open(f, encoding="latin-1").read(); ch = "upper" if "/senate__" in f else "lower"
        g = lambda k: (re.search(r"<%s>([^<]*)</%s>" % (k, k), t) or [None, ""])[1].strip()
        if not g("DISTRICT"): continue
        out.append(rec(ch, g("DISTRICT"), g("DISP_NAME"), g("PARTY"), "ms-" + os.path.basename(f).replace(".xml", ""), nostatus=True, status_src="member XML (no in-office dates)"))
    return out, "Mississippi Legislature member XML (term 2024-2027)", "https://billstatus.ls.state.ms.us/members/hr_membs.xml ; ss_membs.xml ; members/<chamber>/<member>.xml", ["ms_hr_membs.xml", "ms_ss_membs.xml", "ms_m/*"]

def p_md(R):
    out = []
    for f, ch in (("md_house.html", "lower"), ("md_senate.html", "upper")):
        seen = set()
        for code, nm, d, pty in re.findall(r'Details/(\w+)">([^<]+)</a>\s*<br />\s*District (\w+)\s*<br />[^<]*<br />\s*([A-Za-z]+)', open(R + "/" + f, errors="ignore").read()):
            if code in seen: continue
            seen.add(code); out.append(rec(ch, d, nm, pty, "md-" + code))
    return out, "Maryland General Assembly member index (2026 session)", "https://mgaleg.maryland.gov/mgawebsite/Members/Index/house ; .../senate", ["md_house.html", "md_senate.html"]

def p_nc(R):
    out = []
    for f, ch in (("nc_house.html", "lower"), ("nc_senate.html", "upper")):
        t = open(R + "/" + f, errors="ignore").read()
        for pty, d, bid, nm, mark in re.findall(r"<tr>\s*<td>(\w*)</td>\s*<td>(\d+)</td>.*?Biography/[HS]/(\d+)\">([^<]+)</a>\s*(?:<span[^>]*>\(([^)]*)\)</span>)?", t, re.S):
            gone = re.match(r"(Resigned|Deceased|Died|Removed|Expelled)", mark or "")
            out.append(dict(rec(ch, d, nm, pty, "nc-%s-%s" % (ch[0], bid)), session=True, serving=not gone, status_src=mark or ""))
    return out, "North Carolina General Assembly member tables (2025-2026 session, with resignations/appointments marked)", "https://www.ncleg.gov/Members/MemberTable/H ; .../S", ["nc_house.html", "nc_senate.html"]

def p_sc(R):
    out = []
    for f, ch in (("sc_house.html", "lower"), ("sc_senate.html", "upper")):
        t = open(R + "/" + f, errors="ignore").read()
        for d, code, nm, pty in re.findall(r'District (\d+)</a></h1></div>.*?class="membername" href="/member.php\?code=(\d+)">(?:Representative|Senator) ([^<]+)</a>\s*\((\w+)\)', t, re.S):
            out.append(rec(ch, d, nm, pty, "sc-" + code))
    return out, "South Carolina Legislature member lists", "https://www.scstatehouse.gov/member.php?chamber=H ; ?chamber=S", ["sc_house.html", "sc_senate.html"]

def p_ks(R):
    out = []
    for f in sorted(glob.glob(R + "/ks_m/*.json")):
        c = json.load(open(f))["content"]; ch = "upper" if c["KPID"].startswith("sen_") else "lower"
        out.append(dict(rec(ch, c["DISTRICT"], c["FULLNAME"], c.get("PARTY", ""), "ks-" + c["KPID"]), last=fold(c.get("LASTNAME") or last(c["FULLNAME"]))))
    return out, "Kansas Legislature KLISS API v13 (members list + member records)", "https://www.kslegislature.org/li/api/v13/rev-1/members/", ["ks_members.json", "ks_m/*"]

def p_fl(R):
    out = []
    t = open(R + "/fl_senate.html", errors="ignore").read()
    for sd, nm, d, pty in re.findall(r'senatorLink" href="/Senators/[^"]*/S(\d+)">(?:<img[^>]*>)?([^<]+)</a>.*?<td class="middle">(\d+)</td>\s*<td class="middle">([^<]*)</td>', t, re.S):
        out.append(rec("upper", d, nm, pty, "fl-sen-" + sd, vacant=bool(re.search(r"vacant", nm, re.I))))
    return out, "Florida Senate senator list (2024-2026)", "https://www.flsenate.gov/Senators/", ["fl_senate.html"]

def p_ca_sen(R):
    out = []
    t = open(R + "/ca_senate.html", errors="ignore").read()
    for d, pty, nm in re.findall(r'page-members__member" data-name="[^"]*" data-district="(\d+)" data-party="(\w*)">.*?member__name"[^>]*>([^<]+)<', t, re.S):
        out.append(rec("upper", d, nm, pty, "ca-sen-" + d))
    return out, "California State Senate roster", "https://www.senate.ca.gov/senators", ["ca_senate.html"]

def p_me(R):
    out = []
    t = open(R + "/me_house_bydist.html", errors="ignore").read()
    for row in re.findall(r"<tr>(.*?)</tr>", t, re.S):
        m = re.search(r'Details/(\d+)">\s*([^<]+?)\s*</a>\s*<br><small[^>]*>(?:<i[^>]*></i>)?([^<]+)</small>(.*?)</td>.*?badge[^>]*>(\w+)</span>.*?<td data-order="(\d+)">', row, re.S)
        if not m: continue
        mid, nm, role, extra, pty, d = m.groups()
        gone = re.search(r'badge[^>]*>\s*(Deceased|Resigned|Former|Vacated)[^<]*<', extra)
        k = dict(session=True, serving=not gone, status_src=gone.group(1) if gone else role.strip())
        if "Tribal" in role: out.append(dict(rec("lower", "Tribal seat %s" % d, nm, pty, "me-house-" + mid, tribal=True), **k)); continue
        out.append(dict(rec("lower", d, nm, pty, "me-house-" + mid), **k))
    t = open(R + "/me_senate_list.html", errors="ignore").read()
    for d, nm, pty in re.findall(r'<a href="/[Dd]istrict(\d+)">([^<]+)</a>(?:&nbsp;|\s)*\(([DRI])-', t):
        out.append(rec("upper", d, nm, pty, "me-sen-" + d))
    return out, "Maine Legislature: House member listing by district (132nd, with deceased/resigned marked); 132nd Senate senator list", "https://legislature.maine.gov/house/house/MemberProfiles/List?sort=district ; https://legislature.maine.gov/senate/senators/9536", ["me_house_bydist.html", "me_senate_list.html"]

def p_ia(R):
    out = []
    for f, ch in (("ia_house.html", "lower"), ("ia_senate.html", "upper")):
        t = open(R + "/" + f, errors="ignore").read()
        for _, ga, pid, nm, d, pty in re.findall(r'<td>(House|Senate)</td>\s*<td[^>]*><a href="/legislators/legislator\?ga=(\d+)&personID=(\d+)"[^>]*>([^<]+)</a></td>\s*<td><a[^>]*>(\d+)</a></td>\s*<td>([^<]*)</td>', t):
            dm = re.search(r"\((\d\d)/(\d\d)/(\d{4})\s*-\s*(?:(\d\d)/(\d\d)/(\d{4}))?\s*\)", nm)
            k = dict(nostatus=True, session=True, status_src="91st General Assembly list")
            if dm:
                g = dm.groups(); nm = nm[:dm.start()].strip()
                k["term_start"] = "%s-%s-%s" % (g[2], g[0], g[1])
                if g[5]: k.update(serving=False, term_end="%s-%s-%s" % (g[5], g[3], g[4]), status_src="91st General Assembly list: served %s to %s-%s-%s" % (k["term_start"], g[5], g[3], g[4]))
                else: k["status_src"] = "91st General Assembly list: serving since %s" % k["term_start"]
            out.append(dict(rec(ch, d, nm, pty, "ia-" + pid), **k))
    return out, "Iowa Legislature legislator lists (91st General Assembly)", "https://www.legis.iowa.gov/legislators/house ; .../senate", ["ia_house.html", "ia_senate.html"]

def p_mi(R):
    out = []; seen = set()
    t = open(R + "/mi_house.html", errors="ignore").read()
    for nm, pty, d in re.findall(r'page-search-target"[^>]*>\s*([^<]+?)\s*\((\w[^)]*)\)\s*District-(\d+)', t):
        if (nm, d) in seen: continue
        seen.add((nm, d)); out.append(rec("lower", int(d), nm.replace("Rep. ", ""), pty, "mi-house-%s" % d))
    t = open(R + "/mi_senate.html", errors="ignore").read()
    m = re.search(r'"(\[\{&quot;id&quot;.*?\}\])"', t)
    for x in json.loads(html.unescape(m.group(1))):
        nm = " ".join(v for v in (x["firstName"], x.get("middleInitial") or "", x["lastName"], x.get("suffix") or "") if v)
        out.append(dict(rec("upper", x["district"], nm, x["party"], "mi-sen-%s" % x["id"]), last=fold(x["lastName"].split()[-1])))
    return out, "Michigan House all-representatives list; Michigan Senate all-senators list", "https://www.house.mi.gov/AllRepresentatives ; https://senate.michigan.gov/senators/all-senators/", ["mi_house.html", "mi_senate.html"]

def p_wa(R):
    out = []
    t = open(R + "/wa_sponsors_2025-26.xml", encoding="utf-8").read()
    for m in re.findall(r"<Member>(.*?)</Member>", t, re.S):
        g = lambda k: (re.search(r"<%s>([^<]*)</%s>" % (k, k), m) or [None, ""])[1].strip()
        if g("Agency") not in ("House", "Senate") or not g("District"): continue
        out.append(dict(rec("upper" if g("Agency") == "Senate" else "lower", g("District"), g("Name"), g("Party"), "wa-%s" % g("Id"), nostatus=True, session=True,
                            status_src="2025-26 biennium sponsor list (no in-office dates)"), last=fold(g("LastName").split()[-1])))
    return out, "Washington Legislature web services, SponsorService.GetSponsors (biennium 2025-26)", "https://wslwebservices.leg.wa.gov/SponsorService.asmx/GetSponsors?biennium=2025-26", ["wa_sponsors_2025-26.xml"]

def p_ok(R):
    out = []; seen = set()
    t = open(R + "/ok_house.html", errors="ignore").read()
    for slug, title, fn, ln, suf, d, _, pty in re.findall(r'"slug":"([^"]*)","title":([^,]*),"firstName":"([^"]*)","lastName":"([^"]*)","suffix":([^,]*),.*?"District","state":null,"number":(\d+)\}\}\},"party":\{"__typename":"PartyEntityResponse","data":(null|\{"__typename":"PartyEntity","id":"\d+","attributes":\{"__typename":"Party","color":"[^"]*","name":"([^"]*)")', t):
        if slug in seen: continue
        seen.add(slug); vac = ln.upper() == "VACANT" or slug.lower().startswith("vacant")
        nm = "" if vac else " ".join(v for v in (fn, ln, suf.strip('"') if suf != "null" else "") if v)
        out.append(dict(rec("lower", d, nm, pty, "ok-house-" + slug, vacant=vac), last="" if vac else fold(ln.split()[-1])))
    return out, "Oklahoma House of Representatives member list", "https://www.okhouse.gov/representatives", ["ok_house.html"]

def p_la(R):
    out = []
    for f, ch in (("la_house.html", "lower"), ("la_senate.html", "upper")):
        t = open(R + "/" + f, errors="ignore").read()
        for i, nm, d, pty in re.findall(r'LASTFIRSTLabel_(\d+)">([^<]+)</span>.*?DISTRICTNUMBERLabel\w*_\1">(\d+)</span>.*?PARTYAFFILIATIONLabel\w*_\1">([^<]*)</span>', t, re.S):
            out.append(dict(rec(ch, d, nm, pty, "la-%s-%s" % (ch[0], d), vacant=bool(re.search("vacant", nm, re.I))), last=fold(re.sub(r"\s+(Jr|Sr|II|III|IV)\.?$", "", nm.split(",")[0].strip()).split()[-1])))
    return out, "Louisiana House and Senate member lists", "https://house.louisiana.gov/H_Reps/H_Reps_FullInfo ; https://senate.la.gov/Senators_FullInfo", ["la_house.html", "la_senate.html"]

def p_nd(R):
    out = []
    t = open(R + "/nd_members_by_district.html", errors="ignore").read()
    for it in re.findall(r'<li class="member-item.*?</li>', t, re.S):
        bio = re.search(r'href="/biography/([^"]+)"', it); chm = re.search(r'member-chamber">(\w+)<', it); nm = re.search(r'member-name">([^<]+)<', it)
        d = re.search(r'District (\d+[AB]?)\s*\|\s*<span class="sr-only">([^<]*)</span>', it)
        if not (bio and chm and nm and d): continue
        out.append(rec("upper" if chm.group(1) == "Senator" else "lower", d.group(1), nm.group(1), d.group(2), "nd-" + bio.group(1), nostatus=True, session=True,
                       status_src="69th Legislative Assembly members by district (no in-office dates)"))
    return out, "North Dakota Legislative Assembly, 69th (2025) members by district", "https://ndlegis.gov/assembly/69-2025/regular/members/members-by-district", ["nd_members_by_district.html"]

PARSERS = {"Maine": p_me, "Maryland": p_md, "Connecticut": p_ct, "Mississippi": p_ms, "North Carolina": p_nc, "South Carolina": p_sc, "Kansas": p_ks, "Florida": p_fl,
           "Iowa": p_ia, "Michigan": p_mi, "Washington": p_wa, "Oklahoma": p_ok, "Louisiana": p_la, "North Dakota": p_nd}
CHAMBERS = {"Florida": {"upper"}, "Oklahoma": {"lower"}}
EXTRA = {"California": p_ca_sen}   # additional chamber for a state whose first parser is in inst_stateleg_official.py
FALLBACK = {
    "Georgia/upper": "legis.ga.gov member pages are an Angular app; its member API (legis.ga.gov/api/members/list) returns 401 without the app's session token; no CSV/XML/PDF roster found",
    "Georgia/lower": "same as Georgia/upper",
    "Florida/lower": "myfloridahouse.gov returns a WAF 'Request Rejected' page to the box (a block; not routed around)",
    "Illinois/upper": "ilga.gov returns 503 to the box on every member-list request this round (after supplying its missing TLS intermediate from the Mozilla CCADB list)",
    "Illinois/lower": "same as Illinois/upper",
    "Indiana/upper": "iga.in.gov is a client-side app; the IGA data API requires a registered API key (not requested); no CSV/XML/PDF roster found",
    "Indiana/lower": "same as Indiana/upper",
    "Montana/upper": "api.legmt.gov/legislators/v1/legislators answers, but its 209 records do not give a consistent current roster (legislature tags 69/70 mixed with start/end dates; only 119 of 150 seats under the 69th tag; placeholder district 999), so it was not used",
    "Montana/lower": "same as Montana/upper",
    "Oklahoma/upper": "oksenate.gov answers with a Sucuri/Cloudproxy challenge (HTTP 307); a block, not routed around",
    "Alabama/upper": "alison.legislature.state.al.us member pages are a client-side app with no member data in the HTML; no CSV/XML/PDF roster found",
    "Alabama/lower": "same as Alabama/upper",
    "Virginia/upper": "lis.virginia.gov is a client-side app; legacylis.virginia.gov member pages (legp604 ...+mbr+H/S) answer 'document does not exist' for the 2026 session",
    "Virginia/lower": "same as Virginia/upper",
}
