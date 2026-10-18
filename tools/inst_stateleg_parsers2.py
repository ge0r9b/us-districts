"""Official-roster parsers, batches 2+ (imported by tools/inst_stateleg_official.py). Each returns
(records, source name, source URL(s), raw files) like the parsers in inst_stateleg_official.py."""
import re, os, csv, glob, html, json

def setup(fold, last):
    globals().update(fold=fold, last=last)

def rec(ch, d, nm, pty, oid, **k):
    nm = html.unescape(re.sub(r"\s+", " ", nm)).strip()
    m = re.match(r"^([^,]+),\s*(Jr|Sr|II|III|IV)\.?,\s*(.+)$", nm)   # "Love, Jr., Harold" / "Love Jr., Harold"
    if m: nm = "%s %s %s" % (m.group(3), m.group(1), m.group(2) + ("." if m.group(2) in ("Jr", "Sr") else ""))
    elif "," in nm and not re.search(r",\s*(Jr|Sr|II|III|IV)\.?$", nm):
        a_, b_ = [x.strip() for x in nm.split(",", 1)]
        sm = re.match(r"^(.+?)\s+(Jr|Sr|II|III|IV)\.?$", a_)
        nm = "%s %s %s" % (b_, sm.group(1), sm.group(2) + ("." if sm.group(2) in ("Jr", "Sr") else "")) if sm else "%s %s" % (b_, a_)
    return dict(dict(chamber=ch, district=str(d).strip(), name=nm, last=last(nm), party=pty.strip(), oid=oid, serving=True, session=False, status_src=""), **k)

def p_ct(R):
    out = []
    for r in csv.DictReader(open(R + "/ct_LegislatorDatabase.csv", encoding="latin-1")):
        ch = "upper" if r["office code"] == "S" else "lower"
        nm = " ".join(x for x in (r["first name"].strip(), r["middle initial"].strip(), r["last name"].strip(), r["suffix"].strip()) if x)
        out.append(dict(rec(ch, int(r["dist"]), nm, r["party"], "ct-%s%s" % (r["office code"], r["dist"].strip())), last=last(r["last name"])))
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
        out.append(dict(rec(ch, c["DISTRICT"], c["FULLNAME"], c.get("PARTY", ""), "ks-" + c["KPID"]), last=last(c.get("LASTNAME") or c["FULLNAME"])))
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
        out.append(dict(rec("upper", x["district"], nm, x["party"], "mi-sen-%s" % x["id"]), last=last(x["lastName"])))
    return out, "Michigan House all-representatives list; Michigan Senate all-senators list", "https://www.house.mi.gov/AllRepresentatives ; https://senate.michigan.gov/senators/all-senators/", ["mi_house.html", "mi_senate.html"]

def p_wa(R):
    out = []
    t = open(R + "/wa_sponsors_2025-26.xml", encoding="utf-8").read()
    for m in re.findall(r"<Member>(.*?)</Member>", t, re.S):
        g = lambda k: (re.search(r"<%s>([^<]*)</%s>" % (k, k), m) or [None, ""])[1].strip()
        if g("Agency") not in ("House", "Senate") or not g("District"): continue
        out.append(dict(rec("upper" if g("Agency") == "Senate" else "lower", g("District"), g("Name"), g("Party"), "wa-%s" % g("Id"), nostatus=True, session=True,
                            status_src="2025-26 biennium sponsor list (no in-office dates)"), last=last(g("LastName"))))
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

def chunks(t, sep):
    return t.split(sep)[1:]

def p_ky(R):
    out = []
    for f, ch in (("ky_house_bydistrict.html", "lower"), ("ky_senate_bydistrict.html", "upper")):
        for d, nm, pty in re.findall(r'<tr><td>(\d+)</td><td><div class="hover_img"><a href="[^"]*">([^<]+)<span>.*?</td><td>([^<]*)</td>', open(R + "/" + f, errors="ignore").read()):
            out.append(rec(ch, d, nm, pty, "ky-%s-%s" % (ch[0], d), vacant=bool(re.search("vacant", nm, re.I))))
    return out, "Kentucky General Assembly members by district (House, Senate)", "https://apps.legislature.ky.gov/Legislators/hmembers_district.html ; smembers_district.html", ["ky_house_bydistrict.html", "ky_senate_bydistrict.html"]

def p_wv(R):
    out = []
    for f, ch in (("wv_house_roster.html", "lower"), ("wv_senate_roster.html", "upper")):
        t = open(R + "/" + f, errors="ignore").read()
        for code, nm, pty, d in re.findall(r'lawmaker.cfm\?member=([^"]*)" style="vertical-align:top">([^<]+)</a></td>\s*<td class="tdborder">([^<]*)</td>\s*<td class="tdborder">(\d+)', t):
            out.append(rec(ch, int(d), nm, pty, "wv-%s-%s" % (ch[0], code.replace(" ", "_"))))
    return out, "West Virginia Legislature House and Senate rosters (2025-2026)", "https://www.wvlegislature.gov/House/roster.cfm ; https://www.wvlegislature.gov/Senate1/roster.cfm", ["wv_house_roster.html", "wv_senate_roster.html"]

def p_ar(R):
    out = []
    for f, ch in (("ar_house_2025.html", "lower"), ("ar_senate_2025.html", "upper")):
        t = open(R + "/" + f, errors="ignore").read()
        for code, nm, d in re.findall(r'(?:Representative|Senator)\s*<a href="/Legislators/Detail\?member=([^&"]+)[^"]*">([^<]+)</a>.*?<span class="screenreader">District:</span>\s*(\d+)', t, re.S):
            out.append(rec(ch, d, nm, "", "ar-%s-%s" % (ch[0], code), nostatus=True, session=True, status_src="2025 regular session member list (no in-office dates)"))
    return out, "Arkansas State Legislature member lists, 2025 session (party not listed there)", "https://arkleg.state.ar.us/Legislators/List?chamber=House&ddBienniumSession=2025%2F2025R ; ...chamber=Senate", ["ar_house_2025.html", "ar_senate_2025.html"]

def p_wi(R):
    out = []
    for f, ch in (("wi_assembly_2025.html", "lower"), ("wi_senate_2025.html", "upper")):
        t = open(R + "/" + f, errors="ignore").read()
        for c in chunks(t, '<span class="info" style="width:16em;">'):
            m = re.search(r'<strong><a href="[^"]*">([^<]+)</a></strong>\s*<small>\((\w+)\s*-[^)]*\)</small>', c); d = re.search(r"<small>District (\d+)</small>", c)
            dl = re.search(r'href="/2025/legislators/(?:assembly|senate)/(\d+)"', c)
            if m and d: out.append(rec(ch, d.group(1), m.group(1), m.group(2), "wi-%s-%s" % (ch[0], dl.group(1) if dl else d.group(1))))
    return out, "Wisconsin Legislature 2025 member lists (Assembly, Senate)", "https://docs.legis.wisconsin.gov/2025/legislators/assembly ; .../senate", ["wi_assembly_2025.html", "wi_senate_2025.html"]

def p_oh(R):
    out = []
    for f, ch in (("oh_house_dir.html", "lower"), ("oh_senate_dir.html", "upper")):
        for nm, d, pty in re.findall(r'media-overlay-caption-text-line-1">([^<]+)</div>\s*<div class="media-overlay-caption-text-line-2"><div>District (\d+) \| (\w+)</div>', open(R + "/" + f, errors="ignore").read()):
            out.append(rec(ch, d, nm, pty, "oh-%s-%s" % (ch[0], d), vacant=bool(re.search("vacant", nm, re.I))))
    return out, "Ohio General Assembly House and Senate directories", "https://www.legislature.ohio.gov/legislators/house-directory ; senate-directory", ["oh_house_dir.html", "oh_senate_dir.html"]

def p_nj(R):
    out = []
    t = open(R + "/nj_roster.html", errors="ignore").read()
    j = json.loads(re.search(r'__NEXT_DATA__" type="application/json">(.*?)</script>', t, re.S).group(1))
    for x in j["props"]["pageProps"]["legrosterData"][0]:
        ch = "upper" if x["RosterHouseCode"] == "S" else "lower"
        vac = bool(re.search("vacan", (x.get("Full_Name") or "") + str(x.get("VacantSort") or ""), re.I)) and not x.get("Last_Name")
        nm = " ".join(v for v in (x.get("First_Name"), x.get("Middle_Name"), x.get("Last_Name"), x.get("Suffix")) if v and v.strip())
        out.append(dict(rec(ch, x["Roster_District"], nm, x.get("Party") or "", "nj-" + (x.get("BioLink") or "").rstrip("/").split("/")[-2] if x.get("BioLink") else "nj-%s-%s" % (ch[0], x["Roster_District"]), vacant=vac), last=last(nm) if x.get("Last_Name") else ""))
    return out, "New Jersey Legislature legislative roster", "https://www.njleg.state.nj.us/legislative-roster", ["nj_roster.html"]

def p_nm(R):
    out = []
    for f, ch in (("nm_house_list.html", "lower"), ("nm_senate_list.html", "upper")):
        t = open(R + "/" + f, errors="ignore").read()
        for c in chunks(t, "linkLegislatorPicture_"):
            sp = re.search(r'SponCode=(\w+)"', c); m = re.search(r'lblName_\d+"[^>]*>\s*([^<]+?)\s*-\s*\((\w+)\)\s*</span>', c); d = re.search(r"District:\s*(\d+)", c)
            if sp and m and d: out.append(rec(ch, d.group(1), m.group(1), m.group(2), "nm-" + sp.group(1)))
    return out, "New Mexico Legislature legislator lists (House, Senate)", "https://www.nmlegis.gov/Members/Legislator_List?T=R ; ?T=S", ["nm_house_list.html", "nm_senate_list.html"]

def p_id(R):
    out = []
    for f, ch in (("id_house_2026.html", "lower"), ("id_senate_2026.html", "upper")):
        for nm, pty, d in re.findall(r'<p><strong>([^<]+)</strong>\s*\((\w+)\)<br />.*?district=(\d+)">District \d+</a>', open(R + "/" + f, errors="ignore").read(), re.S):
            out.append(rec(ch, d, html.unescape(nm).replace("\xa0", " "), pty, "id-%s-%s-%s" % (ch[0], d, fold(nm)[:12])))
    return out, "Idaho Legislature 2026 House and Senate membership pages", "https://legislature.idaho.gov/house/membership/ ; https://legislature.idaho.gov/senate/membership/", ["id_house_2026.html", "id_senate_2026.html"]

def p_sd(R):
    out = []
    for x in json.load(open(R + "/sd_session71_members.json")):
        ch = "upper" if x["MemberType"] == "S" else "lower"
        nm = " ".join(v for v in (x.get("FirstName"), x.get("Initial"), x.get("LastName")) if v)
        k = {}
        if x.get("InactiveDate"): k = dict(serving=False, term_end=x["InactiveDate"][:10], status_src="inactive since %s" % x["InactiveDate"][:10])
        out.append(dict(rec(ch, x["District"], nm, x.get("Politics") or "", "sd-%s" % x["PersonId"]), last=last(x["LastName"]), **k))
    return out, "South Dakota Legislature API, SessionMembers for session 71 (2026, 101st session)", "https://sdlegislature.gov/api/SessionMembers/Session/71", ["sd_session71_members.json"]

def p_tn(R):
    out = []
    for f, ch in (("tn_house_dir.html", "lower"), ("tn_senate_dir.html", "upper")):
        t = open(R + "/" + f, errors="ignore").read()
        for c in chunks(t, 'aria-label="View details for '):
            m = re.search(r'^[^"]*">([^<]+)</a><br />[^<]*</td>\s*<td>(\w*)</td>.*?View map for District (\d+)', c, re.S)
            if m: out.append(rec(ch, m.group(3), m.group(1), m.group(2), "tn-%s-%s" % (ch[0], m.group(3))))
    return out, "Tennessee General Assembly legislator directory (114th GA)", "https://wapp.capitol.tn.gov/apps/LegislatorInfo/Directory?chamber=H ; ?chamber=S", ["tn_house_dir.html", "tn_senate_dir.html"]

def p_ut(R):
    out = []
    for row in re.findall(r"<tr><td>.*?</tr>", open(R + "/ut_roster.html", errors="ignore").read()):
        td = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<td>(.*?)</td>", row)]
        if len(td) < 4 or td[1] not in ("Representative", "Senator"): continue
        linked = "leglookup.asp" in row
        out.append(rec("upper" if td[1] == "Senator" else "lower", td[3], td[0], td[2], "ut-%s-%s-%s" % (td[1][0], td[3], fold(td[0])[:10]), nostatus=True, session=True,
                       status_src="legislature roster" + ("" if linked else " (row without a district-lookup link)")))
    return out, "Utah Legislature roster", "https://le.utah.gov/asp/roster/roster.asp", ["ut_roster.html"]

def p_co(R):
    out = []
    t = open(R + "/co_legislators.html", errors="ignore").read()
    for title, slug, nm, d, pty in re.findall(r'data-label="Title">\s*<span>(\w+)</span>.*?href="/legislators/([^"]+)">([^<]+)</a>.*?data-label="District">\s*<span>(\d+)</span>.*?data-label="Party">\s*<span>([^<]*)</span>', t, re.S):
        out.append(rec("upper" if title == "Senator" else "lower", d, nm, pty, "co-" + slug, nostatus=True, session=True, status_src="General Assembly legislator list (no in-office dates)"))
    return out, "Colorado General Assembly legislator list", "https://leg.colorado.gov/legislators", ["co_legislators.html"]

def p_az(R):
    out = []
    for f, ch in (("az_house_roster.html", "lower"), ("az_senate_roster.html", "upper")):
        seen = set()
        for lid, nm, d, pty in re.findall(r'legislator=(\d+)" class="roster-tooltip">([^<]+)<strong>.*?class="district-tooltip" title="District (\d+)".*?<span title="([^"]*)">', open(R + "/" + f, errors="ignore").read(), re.S):
            if lid in seen: continue
            seen.add(lid); out.append(rec(ch, d, nm, pty, "az-" + lid, nostatus=True, session=True, status_src="57th Legislature member roster (no in-office dates)"))
    return out, "Arizona Legislature member rosters (57th Legislature)", "https://www.azleg.gov/memberroster/?body=H ; ?body=S", ["az_house_roster.html", "az_senate_roster.html"]

def p_or(R):
    out = []
    for x in json.load(open(R + "/or_legislators_2026R1.json"))["value"]:
        nm = "%s %s" % (x["FirstName"], x["LastName"])
        out.append(dict(rec("upper" if x["Chamber"] == "S" else "lower", x["DistrictNumber"], nm, x.get("Party") or "", "or-" + x["LegislatorCode"].replace(" ", "_"), session=True,
                            status_src="OData Legislators for session 2026R1"), last=last(nm)))
    return out, "Oregon Legislature OData API, Legislators of session 2026R1", "https://api.oregonlegislature.gov/odata/odataservice.svc/LegislativeSessions('2026R1')/Legislators", ["or_legislators_2026R1.json"]

def p_nv(R):
    out = []
    for f, ch, b in (("nv_assembly_current.html", "lower", "Assembly"), ("nv_senate_current.html", "upper", "Senate")):
        t = open(R + "/" + f, errors="ignore").read()
        for nm, lid, pty, d in re.findall(r'<td data-order="([^"]+)" class="text-center">\s*<span[^>]*><a href="/App/Legislator/A/%s/Current/(\d+)">.*?<td data-order="([^"]*)" class="text-center">.*?<td data-order="No\. (\d+)"' % b, t, re.S):
            out.append(rec(ch, d, nm, pty, "nv-%s-%s" % (ch[0], lid)))
    return out, "Nevada Legislature current Assembly and Senate lists", "https://www.leg.state.nv.us/App/Legislator/A/Assembly/Current ; .../Senate/Current", ["nv_assembly_current.html", "nv_senate_current.html"]

def p_ak(R):
    out = []
    for f, ch in (("ak_house.html", "lower"), ("ak_senate.html", "upper")):
        t = open(R + "/" + f, errors="ignore").read(); seen = set()
        for c in chunks(t, "Member/Detail/"):
            code = re.match(r"\d+\?code=(\w+)", c); nm = re.search(r'class="name"[^>]*>([^<]+)<', c)
            d = re.search(r"<dt>District:</dt>\s*<dd>(\w+)</dd>", c) or re.search(r"District <span>(\w+)</span>", c)
            p = re.search(r"<dt>Party:</dt>\s*<dd>([^<]*)</dd>", c) or re.search(r"Party:?\s*<span>([^<]*)</span>", c)
            if not (code and nm and d) or code.group(1) in seen: continue
            seen.add(code.group(1)); out.append(rec(ch, d.group(1), nm.group(1), p.group(1) if p else "", "ak-" + code.group(1)))
    return out, "Alaska State Legislature House and Senate member pages (34th Legislature)", "https://akleg.gov/house.php ; https://akleg.gov/senate.php", ["ak_house.html", "ak_senate.html"]

def p_ne(R):
    out = []; seen = set()
    for d, nm in re.findall(r'index.php\?District=(\d+)"><div class="row"><span class="col-9">([^<]+)</span>', open(R + "/ne_senator_list.html", errors="ignore").read()):
        if d in seen: continue
        seen.add(d); out.append(rec("upper", d, nm, "", "ne-" + d, vacant=bool(re.search("vacant", nm, re.I))))
    return out, "Nebraska Legislature senator list (nonpartisan; no party listed)", "https://nebraskalegislature.gov/senators/senator_list.php", ["ne_senator_list.html"]

def p_mo_sen(R):
    out = []
    for sid, nm, d in re.findall(r'Senators/Member\?id=(\d+)".*?Senator ([^<]+?)\s*<br/>\s*District (\d+)', open(R + "/mo_senators.html", errors="ignore").read(), re.S):
        out.append(rec("upper", d, nm, "", "mo-sen-" + sid))
    return out, "Missouri Senate senator list (party not listed there)", "https://www.senate.mo.gov/senators/", ["mo_senators.html"]

def p_il(R):
    out = []
    for f, ch in (("il_house_members.html", "lower"), ("il_senate_members.html", "upper")):
        for mid, nm, d, pty in re.findall(r'href="/(?:House|Senate)/Members/Details/(\d+)">([^<]+)</a></td>\s*<td>(\d+)</td>\s*<td>(\w*)</td>', open(R + "/" + f, errors="ignore").read()):
            out.append(rec(ch, d, nm, pty, "il-" + mid, vacant=bool(re.search("vacant", nm, re.I)), nostatus=True, session=True, status_src="104th GA member list (lists former members too; no in-office dates)"))
    return out, "Illinois General Assembly House and Senate member lists (104th GA)", "https://www.ilga.gov/House/Members/List ; https://www.ilga.gov/Senate/Members/List", ["il_house_members.html", "il_senate_members.html"]

PARSERS = {"Maine": p_me, "Maryland": p_md, "Connecticut": p_ct, "Mississippi": p_ms, "North Carolina": p_nc, "South Carolina": p_sc, "Kansas": p_ks, "Florida": p_fl,
           "Iowa": p_ia, "Michigan": p_mi, "Washington": p_wa, "Oklahoma": p_ok, "Louisiana": p_la, "North Dakota": p_nd,
           "Kentucky": p_ky, "West Virginia": p_wv, "Arkansas": p_ar, "Wisconsin": p_wi, "Ohio": p_oh, "New Jersey": p_nj, "New Mexico": p_nm, "Idaho": p_id, "South Dakota": p_sd,
           "Tennessee": p_tn, "Utah": p_ut, "Colorado": p_co, "Arizona": p_az, "Oregon": p_or, "Nevada": p_nv, "Alaska": p_ak, "Nebraska": p_ne, "Illinois": p_il}
CHAMBERS = {"Florida": {"upper"}, "Oklahoma": {"lower"}, "Nebraska": {"upper"}}
EXTRA = {"California": p_ca_sen, "Missouri": p_mo_sen}   # additional chamber for a state whose first parser is in inst_stateleg_official.py
FALLBACK = {
    "Georgia/upper": "legis.ga.gov member pages are an Angular app; its member API (legis.ga.gov/api/members/list) returns 401 without the app's session token; no CSV/XML/PDF roster found",
    "Georgia/lower": "same as Georgia/upper",
    "Florida/lower": "myfloridahouse.gov returns a WAF 'Request Rejected' page to the box (a block; not routed around)",
    "Indiana/upper": "iga.in.gov is a client-side app; the IGA data API requires a registered API key (not requested); no CSV/XML/PDF roster found",
    "Indiana/lower": "same as Indiana/upper",
    "Montana/upper": "api.legmt.gov/legislators/v1/legislators answers, but its 209 records do not give a consistent current roster (legislature tags 69/70 mixed with start/end dates; only 119 of 150 seats under the 69th tag; placeholder district 999), so it was not used",
    "Montana/lower": "same as Montana/upper",
    "Oklahoma/upper": "oksenate.gov answers with a Sucuri/Cloudproxy challenge (HTTP 307); a block, not routed around",
    "Alabama/upper": "alison.legislature.state.al.us member pages are a client-side app with no member data in the HTML; no CSV/XML/PDF roster found",
    "Alabama/lower": "same as Alabama/upper",
    "Virginia/upper": "lis.virginia.gov is a client-side app; legacylis.virginia.gov member pages (legp604 ...+mbr+H/S) answer 'document does not exist' for the 2026 session",
    "Virginia/lower": "same as Virginia/upper",
    "Hawaii/upper": "capitol.hawaii.gov answers with a Cloudflare 'Attention Required' challenge (HTTP 403); a block, not routed around; no other official machine-readable roster found",
    "Hawaii/lower": "same as Hawaii/upper",
    "Delaware/upper": "legis.delaware.gov member lists are a client-side grid filled from the site's internal JSON; /json/House/GetRepresentatives and /json/Senate/GetSenators answer 'Page not found'; no CSV/XML/PDF roster found",
    "Delaware/lower": "same as Delaware/upper",
    "Rhode Island/upper": "rilegislature.gov member pages load the list client-side from SharePoint; no CSV/XML/PDF roster found (RIGeneralAssemblyMembers.xlsx 404)",
    "Rhode Island/lower": "same as Rhode Island/upper",
    "Wyoming/upper": "wyoleg.gov LsoService legislator API answers [] for 2025 and 2026; the site is a client-side app",
    "Wyoming/lower": "same as Wyoming/upper",
}
