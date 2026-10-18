"""organizations/airlines_world.csv: every Wikidata airline (P31/P279* Q46970), active and defunct.

Inputs (raw/, gitignored): raw/wikidata_airlines/*.json (scripts/fetch_wikidata_orgs.py airlines Q46970 P229,P230,P432,P113),
raw/openflights/airlines.dat (OpenFlights, ODbL 1.0; only used to cross-check or fill `active`), Commons licence metadata.
Outputs: organizations/airlines_world.csv, airlines_world_locations.csv (hq_in rows), airlines_world_sources.csv, airlines_world_summary.json.
"""
import collections
import csv
import json

import pandas as pd

from common import RAW, ROOT, read_meta
from orgs_common import LCOL, V2, by_item, commons_meta, county, load, logo, point, qid, sha

W = load("airlines")
WM = read_meta("wikidata_airlines")
S_WD = f"wikidata-airlines-{WM['retrieved_at']}"
OF = RAW / "openflights" / "airlines.dat"
OF_DATE = pd.Timestamp(OF.stat().st_mtime, unit="s").date().isoformat()
S_OF = f"openflights-airlines-{OF_DATE}"
import urllib.parse
CM = commons_meta("airlines", [urllib.parse.unquote(r["v"].rsplit("/", 1)[-1]) for r in W["P154"]])
import urllib.parse
CM_FILES = {urllib.parse.unquote(k[5:]) for k in CM}
CMM = read_meta("commons_airlines")
S_LOGO = f"wikidata-commons-logos-airlines-{CMM['retrieved_at']}"
SOURCES = [
    dict(source_id=S_WD, source="Wikidata: items with P31/P279* airline (Q46970); P17, P159(+P625), P749, P571, P576, P856, P154, P229, P230, P432, P113",
         source_url="https://query.wikidata.org/", license="CC0 1.0", retrieved_at=WM["retrieved_at"], commit="", sha256=""),
    dict(source_id=S_OF, source="OpenFlights airlines.dat (used only to cross-check or fill the active flag). Attribution: OpenFlights.org, https://openflights.org/data",
         source_url="https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat",
         license="ODbL 1.0 (Open Database License); attribution required, share-alike for derived databases", retrieved_at=OF_DATE, commit="", sha256=sha(OF)),
    dict(source_id=S_LOGO, source="Wikidata P154 (logo image) + Wikimedia Commons file licence metadata (airlines)",
         source_url="https://commons.wikimedia.org/w/api.php", license="per file: see logo_license", retrieved_at=CMM["retrieved_at"], commit="",
         sha256=sha(RAW / "commons_airlines.json")),
    dict(source_id="census-cb2024-county", source="U.S. Census Bureau cartographic boundary file, counties 2024 (500k)",
         source_url="https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip", license="public domain (US government work)",
         retrieved_at=pd.Timestamp((RAW / "inputs" / "cb_2024_us_county_500k.shp").stat().st_mtime, unit="s").date().isoformat(), commit="",
         sha256=sha(RAW / "inputs" / "cb_2024_us_county_500k.shp")),
]

# OpenFlights: id, name, alias, IATA, ICAO, callsign, country, active
ofr = [r for r in csv.reader(OF.open(encoding="utf-8")) if len(r) == 8 and r[0] not in ("-1", "1")]
clean = lambda x: "" if x in ("\\N", "-", "N/A") else x.strip()
of_icao = collections.defaultdict(list)
of_iata_name = collections.defaultdict(list)
for r in ofr:
    if clean(r[4]):
        of_icao[clean(r[4]).upper()].append(r)
    if clean(r[3]):
        of_iata_name[(clean(r[3]).upper(), r[1].casefold().strip())].append(r)

P = {k: by_item(v) for k, v in W.items() if k != "items"}
items = {}
for r in W["items"]:
    items.setdefault(qid(r["i"]), r)


def vals(p, q, key="v"):
    return [x[key] for x in P.get(p, {}).get(q, []) if x.get(key)]


def labels(p, q):
    return [(qid(x["v"]), x.get("vLabel", "")) for x in P.get(p, {}).get(q, [])]


def tdate(x):
    v, prec = x["v"].lstrip("+"), int(x.get("prec", 11))
    return v[:4] if prec <= 9 else v[:7] if prec == 10 else v[:10]


rows, locs, st = [], [], collections.Counter()
for q, it in items.items():
    nm = it.get("iLabel", "")
    if not nm or nm == q:
        st["excluded_no_label"] += 1
        continue
    fl = []
    p31 = labels("P31", q)
    if any(c == "Q4357531" for c, _ in p31):
        fl.append("virtual_airline")
    ctry = [(qid(x["v"]), x.get("vLabel", ""), x.get("iso", "")) for x in P.get("P17", {}).get(q, [])]
    ctry = list(dict.fromkeys(ctry))
    hq = P.get("P159", {}).get(q, [])
    hq_iso = {x.get("iso") for x in hq if x.get("iso")}
    if len(ctry) > 1:
        m = [c for c in ctry if c[2] in hq_iso]
        pick = m[0] if len(m) == 1 else sorted(ctry, key=lambda c: c[1])[0]
        fl.append("multiple_p17_countries:" + "|".join(c[1] for c in ctry))
    elif ctry:
        pick = ctry[0]
    else:
        pick = None
    if pick:
        cname, cq, ciso = pick[1], pick[0], pick[2]
        if not ciso:
            fl.append("country_no_iso_code")
    else:
        hc = [(qid(x["vctry"]), x.get("iso", "")) for x in hq if x.get("vctry")]
        cname, cq, ciso = "", "", ""
        fl.append("no_p17_country")
    # HQ: one current P159 value; coordinates from the statement's P625 qualifier, else the HQ item's P625
    hq_names = list(dict.fromkeys((qid(x["v"]), x.get("vLabel", "")) for x in hq))
    lat = lon = ""
    hq_q = hq_n = hq_cc = ""
    if len(hq_names) == 1:
        hq_q, hq_n = hq_names[0]
        pts = list(dict.fromkeys(filter(None, [point(x.get("qcoord")) for x in hq] or [])))
        if not pts:
            pts = list(dict.fromkeys(filter(None, [point(x.get("coord")) for x in hq])))
        if len(pts) == 1:
            lat, lon = pts[0]
        elif len(pts) > 1:
            fl.append("hq_several_coordinates_review")
        else:
            fl.append("hq_no_coordinates")
        isos = list(dict.fromkeys(x.get("iso", "") for x in hq if x.get("iso")))
        hq_cc = isos[0] if len(isos) == 1 else ""
    elif len(hq_names) > 1:
        fl.append("hq_several_p159_review:" + "|".join(n for _, n in hq_names))
    else:
        fl.append("no_hq")
    cnty = cg = ""
    if lat != "" and hq_cc == "US":
        cn, g, _ = county(lat, lon)
        cnty, cg = cn, g if g in V2 else ""
        if g and g not in V2:
            fl.append(f"county_not_in_v2-2024:{g}")
        if not g:
            fl.append("point_outside_us_counties")
    inc = sorted(tdate(x) for x in P.get("P571", {}).get(q, []))
    dis = sorted(tdate(x) for x in P.get("P576", {}).get(q, []))
    if len(set(dis)) > 1:
        fl.append("several_p576_dates:" + "|".join(dict.fromkeys(dis)))
    iata, icao, cs = vals("P229", q, "vLabel") or vals("P229", q), vals("P230", q, "vLabel") or vals("P230", q), vals("P432", q, "vLabel") or vals("P432", q)
    # OpenFlights cross-check: unique ICAO match, else unique IATA + exact name
    ofm = []
    for c in icao:
        ofm += of_icao.get(c.upper(), [])
    if len(ofm) != 1:
        ofm2 = []
        for c in iata:
            ofm2 += of_iata_name.get((c.upper(), nm.casefold()), [])
        ofm = ofm if len(ofm2) != 1 else ofm2
    of = ofm[0] if len(ofm) == 1 else None
    if len(ofm) > 1:
        fl.append("openflights_several_matches")
    of_act = {"Y": "yes", "N": "no"}.get(of[7], "") if of else ""
    if dis:
        active = "no"
        if of_act == "yes":
            fl.append("openflights_active_but_wikidata_dissolved")
    elif of_act:
        active = of_act
        fl.append("active_from_openflights")
    else:
        active = ""
        fl.append("active_unknown")
    par = labels("P749", q)
    hubs = labels("P113", q)
    lc, lfl = logo(vals("P154", q), CM)
    fl += lfl
    web = vals("P856", q)
    src = [S_WD] + ([S_OF] if of else []) + ([S_LOGO] if lc else []) + (["census-cb2024-county"] if cnty else [])
    rows.append(dict(
        country=cname, country_code=ciso, country_qid=f"wikidata:{cq}" if cq else "",
        entity_id=f"wikidata:{q}", kind="company", name=nm, description=it.get("iDescription", ""),
        iata=";".join(iata), icao=";".join(icao), callsign=";".join(cs),
        active=active, inception=inc[0] if inc else "", dissolved=dis[0] if dis else "",
        hq_name=hq_n, hq_qid=f"wikidata:{hq_q}" if hq_q else "", hq_country_code=hq_cc, lat=lat, lon=lon,
        county=cnty, county_geoid=cg,
        parent_entity_id=";".join(f"wikidata:{c}" for c, _ in par), parent_name=";".join(n for _, n in par),
        hubs=";".join(n for _, n in hubs), hub_qids=";".join(f"wikidata:{c}" for c, _ in hubs),
        website=web[0] if len(web) == 1 else ";".join(web),
        logo_file=lc.get("logo_file", ""), logo_license=lc.get("logo_license", ""),
        logo_attribution=lc.get("logo_attribution", ""), logo_source_url=lc.get("logo_source_url", ""),
        instance_of=";".join(n for _, n in p31),
        openflights_id=of[0] if of else "", openflights_active=of_act,
        flags=";".join(fl), source=";".join(src), source_url=f"https://www.wikidata.org/wiki/{q}", source_date=WM["retrieved_at"]))
    if lat != "":
        locs.append(dict(location_id=f"airlines_world:hq:{q}", entity_id=f"wikidata:{q}", sub_entity_id="", role="hq_in", name=nm,
                         address=", ".join(t for t in (hq_n, cname) if t), geoid=cg, boundary_set="v2-2024" if cg else "",
                         lat=lat, lon=lon, source_id=S_WD, retrieved_at=WM["retrieved_at"], brand_name=nm,
                         geoid_method="point_in_polygon_cb2024" if cg else "", flags=";".join(fl), country_code=hq_cc or ciso))

df = pd.DataFrame(rows)
df["_s"] = df.country.eq("")  # rows with no country last
df = df.sort_values(["_s", "country", "name", "entity_id"], key=lambda s: s.str.casefold() if s.dtype == object else s).drop(columns="_s")
OUT = ROOT / "organizations"
df.to_csv(OUT / "airlines_world.csv", index=False, lineterminator="\n")
pd.DataFrame(locs, columns=LCOL).to_csv(OUT / "airlines_world_locations.csv", index=False, lineterminator="\n")
pd.DataFrame(SOURCES).to_csv(OUT / "airlines_world_sources.csv", index=False, lineterminator="\n")
summ = dict(rows=len(df), active=df.active.value_counts().to_dict(), **dict(st),
            top_countries=df[df.country != ""].country.value_counts().head(20).to_dict(),
            top_countries_active=df[(df.active == "yes") & (df.country != "")].country.value_counts().head(10).to_dict(),
            countries=int(df.country[df.country != ""].nunique()), no_country=int((df.country == "").sum()),
            with_iata=int((df.iata != "").sum()), with_icao=int((df.icao != "").sum()), with_callsign=int((df.callsign != "").sum()),
            with_hq=int((df.hq_name != "").sum()), with_hq_coordinates=int((df.lat != "").sum()),
            us_hq_with_county=int((df.county_geoid != "").sum()), with_parent=int((df.parent_entity_id != "").sum()),
            with_logo=int((df.logo_file != "").sum()), openflights_matched=int((df.openflights_id != "").sum()),
            hq_in_rows=len(locs), flag_counts=df["flags"].str.split(";").explode().str.split(":").str[0].value_counts().drop("", errors="ignore").to_dict())
(OUT / "airlines_world_summary.json").write_text(json.dumps(summ, indent=1, ensure_ascii=False, default=int) + "\n")
print(json.dumps(summ, indent=1, ensure_ascii=False, default=int))
