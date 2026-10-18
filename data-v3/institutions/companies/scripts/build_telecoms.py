"""organizations/telecoms_world.csv: telecom operators and their consumer brands, worldwide, from Wikidata.

Selection (scripts/fetch_wikidata_orgs.py telecoms, ULTIMATE=1 INDUSTRY=Q418,Q2401742,Q11371,Q1941618): items whose P31 is (a subclass of)
mobile network operator Q1941618, telecommunications company Q2401749, internet service provider Q11371,
cable television company Q1717176, mobile virtual network operator Q1058891 or telephone company Q1266169,
plus items whose P452 industry is telecommunications Q418 / telecommunications industry Q2401742 / ISP Q11371 / MNO Q1941618.
One row per Wikidata item: a consumer brand that has its own item (Visible, Metro by T-Mobile, Cricket ...) is its own row with
its operator as corporate_*. No ITU/GSMA MCC-MNC list is used (not openly licensed); MNCs are Wikidata P2259 only.
"""
import collections
import json
import urllib.parse

import pandas as pd

from common import RAW, ROOT, read_meta
from orgs_common import LCOL, V2, by_item, commons_meta, county, load, logo, point, qid, sha

W = load("telecoms")
WM = read_meta("wikidata_telecoms")
S_WD = f"wikidata-telecoms-{WM['retrieved_at']}"
CM = commons_meta("telecoms", [urllib.parse.unquote(r["v"].rsplit("/", 1)[-1]) for r in W["P154"]])
CMM = read_meta("commons_telecoms")
S_LOGO = f"wikidata-commons-logos-telecoms-{CMM['retrieved_at']}"
CB = RAW / "inputs" / "cb_2024_us_county_500k.shp"
SOURCES = [
    dict(source_id=S_WD, source="Wikidata: telecom operators and brands (P31/P279* Q1941618, Q2401749, Q11371, Q1717176, Q1058891, Q1266169; or P452 Q418, Q2401742, Q11371, Q1941618); "
         "P17, P159(+P625), P137, P749 (+top of P749 chain), P127, P571, P576, P856, P154, P2258, P2259",
         source_url="https://query.wikidata.org/", license="CC0 1.0", retrieved_at=WM["retrieved_at"], commit="", sha256=""),
    dict(source_id=S_LOGO, source="Wikidata P154 (logo image) + Wikimedia Commons file licence metadata (telecoms)",
         source_url="https://commons.wikimedia.org/w/api.php", license="per file: see logo_license", retrieved_at=CMM["retrieved_at"], commit="",
         sha256=sha(RAW / "commons_telecoms.json")),
    dict(source_id="census-cb2024-county", source="U.S. Census Bureau cartographic boundary file, counties 2024 (500k)",
         source_url="https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip", license="public domain (US government work)",
         retrieved_at=pd.Timestamp(CB.stat().st_mtime, unit="s").date().isoformat(), commit="", sha256=sha(CB)),
]
P = {k: by_item(v) for k, v in W.items() if k != "items"}
items = {}
for r in W["items"]:
    items.setdefault(qid(r["i"]), r)
# P31 class -> service type (direct P31 values; generic company classes give none)
SVC = {"Q1941618": "mobile", "Q6887204": "mobile", "Q1058891": "MVNO", "Q11371": "broadband", "Q2585571": "broadband",
       "Q1717176": "cable", "Q105547053": "cable", "Q1266169": "fixed", "Q5156358": "fixed", "Q13405549": "fixed"}
TEL = set(SVC) | {"Q2401749", "Q7696092", "Q133521340"}
NOT_ORG = {"Q5", "Q35127", "Q7397", "Q620615", "Q11016", "Q1616075"}  # human, website, software, app, technology, TV station


IND_ONLY_DROP_P31 = {"Q170584", "Q83405", "Q2424752", "Q1058914", "Q18388277", "Q29643579", "Q1433061", "Q15911314"}
IND_DROP = {"Q5358497": "electronics industry", "Q73768396": "consumer electronics industry", "Q1326885": "electrical industry",
            "Q880371": "software industry", "Q1546066": "networking hardware", "Q132898730": "computer hardware industry",
            "Q16955053": "defence industry", "Q3477363": "aerospace industry", "Q392933": "weapons industry",
            "Q1780509": "telecommunications device", "Q101333": "mechanical engineering", "Q190117": "automotive industry",
            "Q941594": "video game industry", "Q638608": "software development"}
DROPPED = []


def labels(p, q):
    return list(dict.fromkeys((qid(x["v"]), x.get("vLabel", "")) for x in P.get(p, {}).get(q, [])))


rows, locs, st = [], [], collections.Counter()
for q, it in items.items():
    nm = it.get("iLabel", "")
    if not nm or nm == q:
        st["excluded_no_label"] += 1
        continue
    p31 = labels("P31", q)
    c31 = {c for c, _ in p31}
    if c31 & NOT_ORG and not c31 & TEL:
        st["excluded_not_an_operator:" + "|".join(n for c, n in p31 if c in NOT_ORG)] += 1
        continue
    if not c31 & TEL:  # selected by P452 industry only: drop projects, manufacturers and the like (see SCHEMA.md)
        ind = {qid(x["v"]) for x in P.get("P452", {}).get(q, [])}
        why = sorted(n for c, n in p31 if c in IND_ONLY_DROP_P31) + sorted(IND_DROP[c] for c in ind if c in IND_DROP)
        if why or nm.lower().startswith("telecommunications in "):
            st["excluded_industry_only_not_operator"] += 1
            DROPPED.append(dict(entity_id=f"wikidata:{q}", name=nm, reason="; ".join(why) or "topic item (telecommunications in ...)"))
            continue
    fl = []
    svc = list(dict.fromkeys(SVC[c] for c, _ in p31 if c in SVC))
    if any("satellite" in n.lower() for _, n in p31):
        svc.append("satellite")
    if not svc:
        fl.append("service_type_not_stated")
    if not c31 & TEL:
        fl.append("selected_by_p452_industry_only")
    ctry = list(dict.fromkeys((qid(x["v"]), x.get("vLabel", ""), x.get("iso", "")) for x in P.get("P17", {}).get(q, [])))
    hq = P.get("P159", {}).get(q, [])
    hq_iso = {x.get("iso") for x in hq if x.get("iso")}
    pick = None
    if len(ctry) > 1:
        m = [c for c in ctry if c[2] in hq_iso]
        pick = m[0] if len(m) == 1 else sorted(ctry, key=lambda c: c[1])[0]
        fl.append("multiple_p17_countries:" + "|".join(c[1] for c in ctry))
    elif ctry:
        pick = ctry[0]
    else:
        fl.append("no_p17_country")
    cq, cname, ciso = pick if pick else ("", "", "")
    if pick and not ciso:
        fl.append("country_no_iso_code")
    hq_names = list(dict.fromkeys((qid(x["v"]), x.get("vLabel", "")) for x in hq))
    lat = lon = ""
    hq_q = hq_n = hq_cc = ""
    if len(hq_names) == 1:
        hq_q, hq_n = hq_names[0]
        pts = list(dict.fromkeys(filter(None, [point(x.get("qcoord")) for x in hq]))) or \
            list(dict.fromkeys(filter(None, [point(x.get("coord")) for x in hq])))
        if len(pts) == 1:
            lat, lon = pts[0]
        else:
            fl.append("hq_several_coordinates_review" if pts else "hq_no_coordinates")
        isos = list(dict.fromkeys(x.get("iso", "") for x in hq if x.get("iso")))
        hq_cc = isos[0] if len(isos) == 1 else ""
    elif hq_names:
        fl.append("hq_several_p159_review:" + "|".join(n for _, n in hq_names))
    else:
        fl.append("no_hq")
    cnty = cg = ""
    if lat != "" and hq_cc == "US":
        cn, g, _ = county(lat, lon)
        cnty, cg = cn, g if g in V2 else ""
        if g and g not in V2:
            fl.append(f"county_not_in_v2-2024:{g}")
    # corporate: operator P137, else parent P749, else owned-by P127 (first property that has exactly one value)
    corp, how = [], ""
    for p in ("P137", "P749", "P127"):
        v = [x for x in labels(p, q) if x[0] != q]
        if p == "P127":  # owned-by lists shareholders (BlackRock, Vanguard); keep only owners that are telecoms in this set
            v = [x for x in v if x[0] in items]
        if v:
            corp, how = v, p
            break
    if len(corp) > 1:
        fl.append(f"several_corporate_{how}_review")
    if not corp:
        corp, how = [(q, nm)], "self"
    ult = [x for x in labels("ultimate", q) if x[0] != q]
    if not ult and how in ("self", "P749"):
        ult = corp if how == "P749" else [(q, nm)]
    if len(ult) > 1:
        fl.append("several_ultimate_parents_review")
    dis = sorted(x["v"].lstrip("+")[:4 if int(x.get("prec", 11)) <= 9 else 7 if int(x.get("prec", 11)) == 10 else 10] for x in P.get("P576", {}).get(q, []))
    inc = sorted(x["v"].lstrip("+")[:4 if int(x.get("prec", 11)) <= 9 else 7 if int(x.get("prec", 11)) == 10 else 10] for x in P.get("P571", {}).get(q, []))
    mcc = [x["v"] for x in P.get("P2258", {}).get(q, [])]
    mnc = [x["v"] for x in P.get("P2259", {}).get(q, [])]
    web = [x["v"] for x in P.get("P856", {}).get(q, [])]
    lc, lfl = logo([x["v"] for x in P.get("P154", {}).get(q, [])], CM)
    fl += lfl
    rows.append(dict(
        country=cname, country_code=ciso, country_qid=f"wikidata:{cq}" if cq else "",
        brand_name=nm, brand_qid=f"wikidata:{q}", entity_id=f"wikidata:{q}", kind="company" if how == "self" else "brand",
        description=it.get("iDescription", ""),
        corporate_name=";".join(n for _, n in corp), corporate_qid=";".join(f"wikidata:{c}" for c, _ in corp), corporate_from=how,
        ultimate_parent_name=";".join(n for _, n in ult), ultimate_parent_qid=";".join(f"wikidata:{c}" for c, _ in ult),
        service_type=";".join(svc), instance_of=";".join(n for _, n in p31),
        mcc=";".join(sorted(set(mcc))), mnc=";".join(sorted(set(mnc))),
        active="no" if dis else "yes", inception=inc[0] if inc else "", dissolved=dis[0] if dis else "",
        hq_name=hq_n, hq_qid=f"wikidata:{hq_q}" if hq_q else "", hq_country_code=hq_cc, lat=lat, lon=lon, county=cnty, county_geoid=cg,
        website=";".join(web),
        logo_file=lc.get("logo_file", ""), logo_license=lc.get("logo_license", ""),
        logo_attribution=lc.get("logo_attribution", ""), logo_source_url=lc.get("logo_source_url", ""),
        flags=";".join(fl), source_id=";".join([S_WD] + ([S_LOGO] if lc else []) + (["census-cb2024-county"] if cnty else [])),
        source_url=f"https://www.wikidata.org/wiki/{q}", source_date=WM["retrieved_at"]))
    if lat != "":
        locs.append(dict(location_id=f"telecoms_world:hq:{q}", entity_id=f"wikidata:{q}", sub_entity_id="", role="hq_in", name=nm,
                         address=", ".join(t for t in (hq_n, cname) if t), geoid=cg, boundary_set="v2-2024" if cg else "",
                         lat=lat, lon=lon, source_id=S_WD, retrieved_at=WM["retrieved_at"], brand_name=nm,
                         geoid_method="point_in_polygon_cb2024" if cg else "", flags=";".join(fl), country_code=hq_cc or ciso))

df = pd.DataFrame(rows)
df["_s"] = df.country.eq("")
df = df.sort_values(["_s", "country", "brand_name", "entity_id"], key=lambda s: s.str.casefold() if s.dtype == object else s).drop(columns="_s")
OUT = ROOT / "organizations"
df.to_csv(OUT / "telecoms_world.csv", index=False, lineterminator="\n")
pd.DataFrame(locs, columns=LCOL).to_csv(OUT / "telecoms_world_locations.csv", index=False, lineterminator="\n")
pd.DataFrame(DROPPED).to_csv(OUT / "telecoms_world_dropped.csv", index=False, lineterminator="\n")
pd.DataFrame(SOURCES).to_csv(OUT / "telecoms_world_sources.csv", index=False, lineterminator="\n")
svc = df.service_type.replace("", "not_stated").str.split(";").explode().value_counts().to_dict()
summ = dict(rows=len(df), active=df.active.value_counts().to_dict(), **dict(st), by_service_type=svc,
            kind=df.kind.value_counts().to_dict(), corporate_from=df.corporate_from.value_counts().to_dict(),
            countries=int(df.country[df.country != ""].nunique()), no_country=int((df.country == "").sum()),
            top_countries=df[df.country != ""].country.value_counts().head(25).to_dict(),
            with_mnc=int((df.mnc != "").sum()), with_mcc=int((df.mcc != "").sum()),
            with_hq_coordinates=int((df.lat != "").sum()), with_logo=int((df.logo_file != "").sum()),
            with_ultimate_parent=int((df.ultimate_parent_qid != "").sum()), hq_in_rows=len(locs),
            flag_counts=df["flags"].str.split(";").explode().str.split(":").str[0].value_counts().drop("", errors="ignore").to_dict())
(OUT / "telecoms_world_summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False, default=int) + "\n")
print(json.dumps(summ, indent=1, ensure_ascii=False, default=int))
