"""Build brand-keyed location files + brands.csv + sources.csv (see ../SCHEMA.md).

Inputs (raw/, gitignored):
  raw/inputs/all_stores.csv            Walgreens (walgreens.com locator API, 2026-10-12) + CVS (cvs.com locator pages, 2026-10-17),
                                       copied from /workspace/store-locator (see raw/inputs/store-locator-README.md)
  raw/inputs/marriott-properties-v5.csv  Marriott portfolio list (2026-10-04, see marriott-properties-v5-notes.txt)
  raw/atp/*.geojson + raw/atp.meta.json  All The Places run (CC0): mcdonalds, marriott_hotels, ritz_carlton
  raw/wikidata_brands.json              Wikidata labels / P31 / P749 / P856 (fetch_wikidata_brands.py)
  raw/inputs/cb_2024_us_county_500k.*   Census cartographic boundary counties 2024 (county by point-in-polygon)
Rules: nothing is invented; a value missing from every source stays empty and is flagged.
parent_brand_qid = Wikidata P749 (parent organization) of the brand item only (P127 shareholders are not used).
"""
import csv
import datetime as dt
import hashlib
import json
import math
import html
import os
import re
import urllib.parse
import sys
from collections import Counter, defaultdict

import pandas as pd
import shapefile
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

from common import RAW, ROOT, read_meta, today

OUT = ROOT / "locations"
OUT.mkdir(exist_ok=True)
INP = RAW / "inputs"
LCOLS = ["store_id", "brand", "brand_qid", "parent_brand_qid", "address", "city", "state", "zip", "county",
         "lat", "lon", "phone", "sub_brand", "flags", "source", "source_url", "source_date",
         # extras
         "name", "sub_brand_qid", "county_geoid", "country_code", "status", "store_type"]
WD = json.loads((RAW / "wikidata_brands.json").read_text())
ATP = read_meta("atp")
ATP_DATE = ATP["run_id"][:10]

# ---------------- sources ----------------
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

SOURCES = {}
def src(sid, name, url, lic, date, path=None):
    SOURCES[sid] = dict(source_id=sid, source=name, source_url=url, license=lic, retrieved_at=date, commit="",
                        sha256=sha(path) if path else "")
    return sid

S_WAG = src("walgreens-locator-api-2026-10-12", "walgreens.com store locator API (via /workspace/store-locator all_stores.csv)",
            "https://www.walgreens.com/storelocator/find.jsp", "walgreens.com terms of use (public locator; not an open licence)",
            "2026-10-12", INP / "all_stores.csv")
S_CVS = src("cvs-store-locator-2026-10-17", "cvs.com store-locator city pages (via /workspace/store-locator all_stores.csv)",
            "https://www.cvs.com/store-locator/cvs-pharmacy-locations", "cvs.com terms of use (public locator; not an open licence)",
            "2026-10-17", INP / "all_stores.csv")
S_MAR = src("marriott-properties-v5-2026-10-04", "Marriott property list v5 (marriott.com sitemaps; addresses partly from OpenStreetMap/Photon, ArcGIS World Geocoder, Wikidata; see notes)",
            "https://www.marriott.com/", "mixed: marriott.com terms; OSM-derived values ODbL; ArcGIS geocoder terms restrict storage",
            "2026-10-04", INP / "marriott-properties-v5.csv")
S_CEN = src("census-cb2024-county", "U.S. Census Bureau cartographic boundary file, counties 2024 (500k)",
            "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip", "public domain (US government work)",
            dt.date.fromtimestamp((INP / "cb_2024_us_county_500k.shp").stat().st_mtime).isoformat(),
            INP / "cb_2024_us_county_500k.shp")
S_WD = src(f"wikidata-brands-{read_meta('wikidata_brands')['retrieved_at']}", "Wikidata (labels, P31, P749, P856)",
           "https://query.wikidata.org/", "CC0 1.0", read_meta("wikidata_brands")["retrieved_at"], RAW / "wikidata_brands.json")
ATP_SBUX = sorted(k for k, v in ATP["spiders"].items() if k.startswith("starbucks_") and v["features"])
ATP_USED = ("mcdonalds", "marriott_hotels", "ritz_carlton", *ATP_SBUX)
S_ATP = {s: src(f"atp-{s}-{ATP_DATE}", f"All The Places spider '{s}' (run {ATP['run_id']})", ATP["spiders"][s]["url"],
                "CC0 1.0", ATP_DATE, RAW / "atp" / f"{s}.geojson") for s in ATP_USED}
S_V5OK = src("marriott-v5-user-approved-2026-10-18", "Marriott property list v5 values (coordinates/address) kept where no ATP or Marriott-feed value exists; approved by the user on 2026-10-18",
             "https://www.marriott.com/", "user-approved 2026-10-18; underlying v5 sources mixed (marriott.com, OSM ODbL, ArcGIS); see PROVENANCE-marriott-v5.md",
             "2026-10-18", INP / "marriott-properties-v5.csv")
# Marriott's own property feeds (first-party; see scripts/fetch_marriott_pacsys.py). sha256 is over the
# brand files concatenated in sorted brand-code order.
PAC_META = read_meta("marriott_pacsys")
PAC_FILES = sorted((RAW / "marriott_pacsys").glob("*.json"))
_h = hashlib.sha256()
for _f in PAC_FILES:
    _h.update(_f.read_bytes())
S_PAC = src(f"marriott-pacsys-{PAC_META['retrieved_at']}",
            "Marriott property feeds pacsys.marriott.com, brand codes " + " ".join(sorted(PAC_META["files"])),
            "https://pacsys.marriott.com/data/marriott_properties_<BRAND>_en-US.json",
            "marriott.com terms of use (first-party public feed; facts only, not an open licence)", PAC_META["retrieved_at"])
SOURCES[S_PAC]["sha256"] = _h.hexdigest()
PAC = {}
for _f in PAC_FILES:
    for _r in json.loads(_f.read_text())["regions"]:
        for _k in _r["region_countries"]:
            for _st in _k["country_states"]:
                for _c in _st["state_cities"]:
                    for _p in _c["city_properties"]:
                        PAC.setdefault(_p["marsha_code"].upper(), (_f.stem, _p))

# ---------------- helpers ----------------
r = shapefile.Reader(str(INP / "cb_2024_us_county_500k.shp"))
fn = [f[0] for f in r.fields[1:]]
GEOMS, CINFO = [], []
for sr in r.iterShapeRecords():
    a = dict(zip(fn, sr.record))
    GEOMS.append(shape(sr.shape.__geo_interface__))
    CINFO.append((a["NAMELSAD"], a["GEOID"], a["STUSPS"]))
TREE = STRtree(GEOMS)

def county(lat, lon):
    try:
        pt = Point(float(lon), float(lat))
    except (TypeError, ValueError):
        return ("", "", "")
    for i in TREE.query(pt):
        if GEOMS[i].covers(pt):
            return CINFO[i]
    return ("", "", "")


def county_near(lat, lon, max_deg=0.02):
    """Nearest county within ~2 km (piers, shoreline points the 1:500k file clips off)."""
    pt = Point(float(lon), float(lat))
    i = TREE.nearest(pt)
    return CINFO[i] if GEOMS[i].distance(pt) <= max_deg else ("", "", "")

def phone_us(p):
    d = re.sub(r"\D", "", p or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else None

RELS = json.loads((RAW / "wikidata_p749.json").read_text())
CURRENT = defaultdict(list)
for _r in RELS:
    if not _r["end"] and _r["parent"] not in CURRENT[_r["child"]]:
        CURRENT[_r["child"]].append(_r["parent"])


def parent_of(qid):
    """Current Wikidata parent organizations (P749 statements without an end date), ;-list."""
    return ";".join(f"wikidata:{p}" for p in CURRENT.get(qid, [])) if qid else ""

def qid(q):
    return f"wikidata:{q}" if q else ""

def km(a, b, c, d):
    p = math.pi / 180
    x = (c - a) * p
    y = (d - b) * p * math.cos((a + c) / 2 * p)
    return 6371 * math.hypot(x, y)

def write(df, name):
    p = OUT / f"{name}.csv"
    df.to_csv(p, index=False, lineterminator="\n")
    if p.stat().st_size > 5_000_000:
        df.to_csv(OUT / f"{name}.csv.gz", index=False, lineterminator="\n",
                  compression={"method": "gzip", "mtime": 0, "compresslevel": 9})
        p.unlink()
        return f"{name}.csv.gz"
    return f"{name}.csv"

def finish(rows, check_county=True):
    for x in rows:
        fl = x["flags"]
        if x["lat"] in ("", None):
            fl.append("missing_coordinates")
        elif x.get("country_code", "US") in ("US", "PR", "VI", "GU", "AS", "MP"):
            n, g, st = county(x["lat"], x["lon"])
            if not g:
                n, g, st = county_near(x["lat"], x["lon"])
                if g:
                    fl.append("county_nearest_within_2km")
            x["county"], x["county_geoid"] = n, g
            if not g and check_county:
                fl.append("point_outside_us_counties")
            elif st and x["state"] and len(x["state"]) == 2 and st != x["state"].upper():
                fl.append(f"point_state_{st}_vs_address_{x['state']}")
        x["flags"] = ";".join(dict.fromkeys(fl))
    return pd.DataFrame(rows, columns=LCOLS)

summary = {}

# ---------------- Walgreens + CVS ----------------
st = pd.read_csv(INP / "all_stores.csv", dtype=str, keep_default_na=False)
Q_WAG, Q_DR, Q_CVS, Q_YMAS = "Q1591889", "Q5310380", "Q2078880", "Q136695801"
for brand, sid, bq in (("Walgreens", S_WAG, Q_WAG), ("CVS", S_CVS, Q_CVS)):
    sub = st[st.brand == brand]
    rows, phone_fixed = [], 0
    for x in sub.itertuples(index=False):
        fl = []
        ph = phone_us(x.phone)
        if ph is None:
            ph = x.phone
            if x.phone:
                fl.append("phone_unparsed")
        elif ph != x.phone:
            phone_fixed += 1
        sbq = Q_DR if x.sub_brand == "Duane Reade" else Q_YMAS if x.sub_brand == "CVS Pharmacy y más" else ""
        if brand == "Walgreens":
            if re.search(r", an? Walgreens (Rx|Pharmacy)$", x.sub_brand, re.I):
                fl.append("independent_walgreens_affiliate_operator_unknown")
            elif "Powered by Walgreens" in x.sub_brand:
                fl.append("powered_by_walgreens_affiliate_operator_unknown")
        if x.status != "open":
            fl.append(f"status_{x.status}")
        rows.append(dict(store_id=x.store_id, brand="Walgreens" if brand == "Walgreens" else "CVS Pharmacy",
                         brand_qid=qid(bq), parent_brand_qid=parent_of(bq),
                         address=x.street, city=x.city, state=x.state, zip=x.zip, county="", lat=x.lat, lon=x.lon,
                         phone=ph, sub_brand=x.sub_brand, flags=fl, source=f"{sid};{S_CEN};{S_WD}", source_url=x.url,
                         source_date=SOURCES[sid]["retrieved_at"], name=x.store_name, sub_brand_qid=qid(sbq),
                         county_geoid="", country_code=x.country_code, status=x.status, store_type=x.store_type))
    df = finish(rows)
    old = dict(zip(sub.store_id, sub.county))
    diff = sum(1 for a, b in zip(df.store_id, df.county) if old.get(a, "") != b)
    key = brand.lower()
    summary[key] = {"file": write(df, key), "rows": len(df), "phone_reformatted": phone_fixed,
                    "county_differs_from_input_2023_county": diff,
                    "flags": dict(Counter(f.split(":")[0] for fl in df["flags"] for f in fl.split(";") if f))}

# ---------------- McDonald's (ATP, US only) ----------------
feats = json.loads((RAW / "atp" / "mcdonalds.geojson").read_text())["features"]
rows, seen, dups = [], set(), 0
for f in feats:
    p = f["properties"]
    if p.get("addr:country") != "US":
        continue
    ref = str(p.get("ref", ""))
    if ref in seen:
        dups += 1
        continue
    seen.add(ref)
    fl = []
    g = f.get("geometry") or {}
    lon, lat = (g.get("coordinates") or ["", ""])[:2]
    ph = phone_us(p.get("phone", "")) or p.get("phone", "")
    bq = p.get("brand:wikidata") or ""
    nm = p.get("name") or ""
    rows.append(dict(store_id=ref, brand=p.get("brand") or "McDonald's", brand_qid=qid(bq), parent_brand_qid=parent_of(bq),
                     address=p.get("addr:street_address") or " ".join(filter(None, [p.get("addr:housenumber"), p.get("addr:street")])),
                     city=p.get("addr:city", ""), state=p.get("addr:state", ""), zip=p.get("addr:postcode", ""), county="",
                     lat=round(lat, 6) if lat != "" else "", lon=round(lon, 6) if lon != "" else "", phone=ph,
                     sub_brand=nm if nm and nm != "McDonald's" else "", flags=fl,
                     source=f"{S_ATP['mcdonalds']};{S_CEN};{S_WD}", source_url=p.get("website") or p.get("@source_uri", ""),
                     source_date=ATP_DATE, name=nm, sub_brand_qid="", county_geoid="", country_code="US", status="", store_type=""))
df = finish(rows)
summary["mcdonalds"] = {"file": write(df, "mcdonalds"), "rows": len(df), "atp_us_features": len(seen) + dups,
                        "duplicate_refs_dropped": dups, "atp_non_us_features_skipped": len(feats) - len(seen) - dups,
                        "flags": dict(Counter(f.split(":")[0] for fl in df["flags"] for f in fl.split(";") if f))}

# ---------------- Marriott (v5 + ATP fill) ----------------
v5 = pd.read_csv(INP / "marriott-properties-v5.csv", dtype=str, keep_default_na=False)
n_in = len(v5)
v5 = v5.drop_duplicates()
exact_dups = n_in - len(v5)
v5["marsha"] = v5.website.str.extract(r"/hotels/([a-z0-9]{5})-", expand=False).fillna("").str.upper()
atp = {}
for s in ("marriott_hotels", "ritz_carlton"):
    for f in json.loads((RAW / "atp" / f"{s}.geojson").read_text())["features"]:
        p = f["properties"]
        ref = str(p.get("ref", ""))
        m = re.search(r"/hotels/([a-z0-9]{5})-", ref) if s == "ritz_carlton" else None
        code = (m.group(1) if m else ref).upper() if (m or s != "ritz_carlton") else ""
        if code and code not in atp:
            atp[code] = (s, f)
# v5 brand name -> QID, learned only from rows matched by MARSHA code (>= 90 % agreement)
pairs = defaultdict(Counter)
for b, c in zip(v5.brand, v5.marsha):
    if c in atp and atp[c][1]["properties"].get("brand:wikidata"):
        pairs[b][atp[c][1]["properties"]["brand:wikidata"]] += 1
BRAND_Q = {b: c.most_common(1)[0][0] for b, c in pairs.items()
           if b and sum(c.values()) >= 5 and c.most_common(1)[0][1] / sum(c.values()) >= 0.9}
# v5 brand name -> QID from Wikidata items owned by / parented to Marriott or Starwood: the normalized v5 name
# must equal the item's normalized label or an English alias, and exactly one item may match.
def _norm(t):
    t = re.sub(r"^the\s+", "", (t or "").lower().strip())
    return re.sub(r"\s+(hotels?\s*(&|and)\s*resorts|hotels?|by marriott)$", "", t).strip()
_kids = defaultdict(set)
for row in csv.DictReader(open(RAW / "wikidata_owner_children.csv", encoding="utf-8")):
    q = row["item"].rsplit("/", 1)[-1]
    for t in (row["itemLabel"], row.get("alt", "")):
        if t:
            _kids[_norm(t)].add(q)
WD_BRAND = {b: next(iter(_kids[_norm(b)])) for b in set(v5.brand) if b and len(_kids.get(_norm(b), ())) == 1}
# country name -> ISO code, learned the same way
cpairs = defaultdict(Counter)
for cn, c in zip(v5.country, v5.marsha):
    if cn and c in atp and atp[c][1]["properties"].get("addr:country"):
        cpairs[cn][atp[c][1]["properties"]["addr:country"]] += 1
CC = {cn: c.most_common(1)[0][0] for cn, c in cpairs.items() if c.most_common(1)[0][1] / sum(c.values()) >= 0.9}

rows, stats = [], Counter()
dup_marsha = set(v5.marsha[v5.marsha.duplicated() & (v5.marsha != "")])
for x in v5.itertuples(index=False):
    fl, srcs = [], [S_MAR]
    lat = lon = ""
    if x.coordinates:
        try:
            lat, lon = [float(t) for t in x.coordinates.split(",")]
        except ValueError:
            fl.append("v5_coordinates_unparsed")
    addr, city, state, zipc, phone, sub, cc = x.address, x.city, x.state_or_region, "", "", "", CC.get(x.country, "")
    url = x.website
    hit = atp.get(x.marsha) if x.marsha else None
    bq = WD_BRAND.get(x.brand, "")
    if bq:
        fl.append("brand_qid_from_wikidata_name_match")
    if not x.marsha:
        fl.append("no_marsha_code")
    if x.marsha in dup_marsha:
        fl.append("duplicate_marsha_in_v5")
    coord_src = addr_src = "v5"
    if hit:
        s, f = hit
        p = f["properties"]
        srcs.append(S_ATP[s])
        stats["atp_matched"] += 1
        g = f.get("geometry")
        if g:  # ATP (CC0) wins over v5 for coordinates
            alon, alat = g["coordinates"][:2]
            if lat == "":
                stats["coords_filled_from_atp"] += 1
            elif km(lat, lon, alat, alon) > 1:
                fl.append(f"v5_vs_atp_coordinates_{km(lat, lon, alat, alon):.1f}km")
            lat, lon, coord_src = alat, alon, "atp"
            fl.append("coordinates_from_atp")
        if p.get("addr:street_address"):  # ATP wins for the address block too
            if not addr:
                stats["address_filled_from_atp"] += 1
            addr, addr_src = p["addr:street_address"], "atp"
            city, state, zipc = p.get("addr:city", "") or city, p.get("addr:state", "") or state, p.get("addr:postcode", "")
            fl.append("address_from_atp")
        else:
            city = city or p.get("addr:city", "")
            state = state or p.get("addr:state", "")
            zipc = p.get("addr:postcode", "")
        cc = p.get("addr:country", "") or cc
        phone = p.get("phone", "")
        if not bq:
            bq = p.get("brand:wikidata", "")
        elif p.get("brand:wikidata") and p["brand:wikidata"] != bq:
            fl.append(f"atp_brand_qid_differs:{p['brand:wikidata']}")
        if p.get("brand") and p.get("brand") != x.brand:
            sub = p["brand"]
    pac = PAC.get(x.marsha) if x.marsha else None
    if pac and (coord_src == "v5" or addr_src == "v5"):  # Marriott's own feed fills what ATP did not
        bc, q = pac
        srcs.append(S_PAC)
        stats["marriott_feed_matched"] += 1
        if coord_src == "v5" and q.get("latitude") and q.get("longitude"):
            lat, lon, coord_src = float(q["latitude"]), float(q["longitude"]), "marriott_feed"
            fl.append("coordinates_from_marriott_feed")
        if addr_src == "v5" and q.get("address"):
            addr, addr_src = q["address"].strip(), "marriott_feed"
            city, state, zipc = q.get("city") or city, q.get("state") or state, q.get("postal_code") or zipc
            fl.append("address_from_marriott_feed")
        cc = cc or q.get("country_code") or ""
        phone = phone or q.get("phone") or ""
        url = url or f"https://pacsys.marriott.com/data/marriott_properties_{bc}_en-US.json"
    if lat != "" and coord_src == "v5":  # no ATP / Marriott-feed point: v5 values kept, user-approved 2026-10-18
        srcs.append(S_V5OK)
        fl.append("v5_user_approved")
    if addr and addr_src == "v5":  # kept: user approved v5 values on 2026-10-18
        fl.append("v5_user_approved")
    if not bq and BRAND_Q.get(x.brand):
        bq = BRAND_Q[x.brand]
        fl.append("brand_qid_from_brand_name")
    if not cc:
        cc = {"United States": "US", "Puerto Rico": "PR", "U.S. Virgin Islands": "VI"}.get(x.country, "")
    if cc == "US" or not cc and x.country == "United States":
        phone = phone_us(phone) or phone
    rows.append(dict(store_id=x.marsha, brand=x.brand, brand_qid=qid(bq), parent_brand_qid=parent_of(bq), address=addr,
                     city=city, state=state, zip=zipc, county="", lat=round(lat, 6) if lat != "" else "",
                     lon=round(lon, 6) if lon != "" else "", phone=phone, sub_brand=sub, flags=fl,
                     source=";".join(srcs + [S_CEN, S_WD]), source_url=url or (hit[1]["properties"].get("website", "") if hit else ""),
                     source_date=max(SOURCES[s]["retrieved_at"] for s in srcs), name=x.hotel_name, sub_brand_qid="",
                     county_geoid="", country_code=cc, status="", store_type=""))
# v5-only rows (v5_user_approved) are dropped when they duplicate another row: same MARSHA code, or the same
# normalized name and address with points within 100 m.
_nm = lambda t: re.sub(r"[^a-z0-9]", "", (t or "").lower())
_open = [x for x in rows if "v5_user_approved" not in x["flags"] and x["lat"] != ""]
_by_code = Counter(x["store_id"] for x in rows if x["store_id"])
_by_na = defaultdict(list)
for x in _open:
    _by_na[(_nm(x["name"]), _nm(x["address"]))].append(x)
for x in rows:
    if "v5_user_approved" not in x["flags"]:
        continue
    if x["store_id"] and _by_code[x["store_id"]] > 1:
        x["dup_of"] = x["store_id"]
        continue
    for y in _by_na.get((_nm(x["name"]), _nm(x["address"])), []):
        if km(x["lat"], x["lon"], y["lat"], y["lon"]) <= 0.1:
            x["dup_of"] = y["store_id"]
            break
stats["v5_user_approved_duplicates"] = sum(1 for x in rows if x.get("dup_of"))
# Scope: US + territories only (Full Stack 8639fe1). Rows that cannot load are dropped and listed.
US_CC = {"US", "PR", "VI", "GU", "AS", "MP"}
keep, dropped = [], []
for x in rows:
    reason = ("non_us" if x["country_code"] and x["country_code"] not in US_CC else
              "no_country" if not x["country_code"] else
              "no_store_id" if not x["store_id"] else
              "no_brand_qid" if not x["brand_qid"] else
              "no_coordinates_no_address" if x["lat"] == "" and not x["address"] else
              f"duplicate_of:{x['dup_of']}" if x.get("dup_of") else
              "no_coordinates" if x["lat"] == "" else "")
    (dropped if reason else keep).append((x, reason))
stats["dropped"] = dict(Counter(r for _, r in dropped))
pd.DataFrame([dict(store_id=x["store_id"], brand=x["brand"], name=x["name"], city=x["city"], state=x["state"],
                   country_code=x["country_code"], reason=r, source_url=x["source_url"]) for x, r in dropped if r not in ("non_us", "no_country")]
             ).to_csv(OUT / "marriott_dropped_us.csv", index=False, lineterminator="\n")
rows = [x for x, _ in keep]
for x in rows:
    x.pop("dup_of", None)
df = finish(rows, check_county=False)
stats["v5_user_approved_rows"] = int(df["flags"].str.contains("v5_user_approved").sum())
v5_codes = set(v5.marsha)
summary["marriott"] = {"file": write(df, "marriott"), "rows": len(df), "input_rows": n_in, "exact_duplicate_rows_dropped": exact_dups,
                       "v5_missing_coordinates": int((v5.coordinates == "").sum()), **stats,
                       "still_missing_coordinates": int((df.lat == "").sum()),
                       "atp_properties_not_in_v5": len(set(atp) - v5_codes),
                       "rows_by_country": dict(Counter(df.country_code)),
                       "flags": dict(Counter(re.sub(r"_[\d.]+km$", "_km", f.split(":")[0]) for fl in df["flags"] for f in fl.split(";") if f))}

# ---------------- Starbucks (All The Places, all countries) ----------------
# Every ATP starbucks_* spider with features. ATP refs are numbered per licensee system, so the same number can be two
# different stores in two spiders (e.g. starbucks_th 14091 vs starbucks_us 14091). store_id is therefore
# <namespace>-<ref>: namespace = the country domain for refs like "locations.starbucks.ae/#15480757" (starbucks_ae and
# starbucks_mena publish the same stores this way), else the spider suffix without "_" (us, cn, eu, arcl, hkmo, ...).
# Same store_id twice = the same store; the first spider in name order is kept. starbucks_reserve (6 Roasteries,
# brand Q71150001, no ref) is not loaded: no store id.
SBQ = "Q37158"
rows, seen, sb = [], {}, Counter()
for spider in ATP_SBUX:
    t = (RAW / "atp" / f"{spider}.geojson").read_text().strip()
    for f in json.loads(t)["features"] if t else []:
        p = f["properties"]
        sb["features"] += 1
        if p.get("brand:wikidata") != SBQ:
            sb[f"skipped_brand_{p.get('brand:wikidata')}"] += 1
            continue
        ref = str(p.get("ref") or "")
        if not ref:
            sb["skipped_no_ref"] += 1
            continue
        m = re.match(r"locations\.starbucks\.(?:com\.|co\.)?([a-z]{2})/#(\d+)$", ref)
        sid = f"{m.group(1)}-{m.group(2)}" if m else f"{spider[10:].replace('_', '')}-{ref}"
        g = f.get("geometry")
        lat, lon = (g["coordinates"][1], g["coordinates"][0]) if g else ("", "")
        if sid in seen:
            sb["duplicate_store_id_dropped"] += 1
            o = seen[sid]
            if lat != "" and o["lat"] != "" and km(lat, lon, o["lat"], o["lon"]) > 1:
                o["flags"].append(f"duplicate_in_{spider}_{km(lat, lon, o['lat'], o['lon']):.1f}km")
            continue
        cc = p.get("addr:country", "")
        name = p.get("name") or p.get("name:en") or ""
        if name == "Starbucks" and p.get("branch"):
            name = f"Starbucks {p['branch']}"
        phone = p.get("phone", "") or ""
        if cc == "US":
            phone = phone_us(phone) or phone
        x = dict(store_id=sid, brand="Starbucks", brand_qid=qid(SBQ), parent_brand_qid=parent_of(SBQ),
                 address=p.get("addr:street_address") or p.get("addr:full") or "", city=p.get("addr:city", ""),
                 state=p.get("addr:state", ""), zip=p.get("addr:postcode", ""), county="",
                 lat=round(lat, 6) if lat != "" else "", lon=round(lon, 6) if lon != "" else "", phone=phone, sub_brand="",
                 flags=[] if p.get("addr:street_address") or not p.get("addr:full") else ["address_is_addr_full"],
                 source=";".join([S_ATP[spider], S_CEN, S_WD]) if cc == "US" else ";".join([S_ATP[spider], S_WD]),
                 source_url=p.get("website") or p.get("@source_uri", ""), source_date=SOURCES[S_ATP[spider]]["retrieved_at"],
                 name=name, sub_brand_qid="", county_geoid="", country_code=cc, status="", store_type="")
        seen[sid] = x
        rows.append(x)
df = finish(rows, check_county=True)  # county point-in-polygon runs only for US / territory country codes
summary["starbucks"] = {"file": write(df, "starbucks"), "rows": len(df), **dict(sb), "spiders": ATP_SBUX,
                        "rows_by_country": dict(Counter(df.country_code).most_common()),
                        "missing_coordinates": int((df.lat == "").sum()),
                        "us_with_county_geoid": int(((df.country_code == "US") & (df.county_geoid != "")).sum())}

# ---------------- other ATP chains (all countries the brand's spiders cover) ----------------
# One config per file. inputs = (spider, run_id or None for the latest run, namespace); earlier inputs win on a
# duplicate store_id, so the latest run comes first and an older run only fills store ids the latest run lacks
# (rows flagged atp_older_run_<date>). store_id = <namespace>-<ref>; a URL ref keeps only its trailing store number.
OLDER = read_meta("atp_older").get("runs", {})
CHAINS = {
    "walmart": dict(qid="Q483551", accept={"Q483551", "Q7963529"},
                    sub_by_name={"Walmart Neighborhood Market": "Q7963529"}, drop_names={"Walmart Pharmacy"},
                    inputs=[("walmart_us", None, "us"), ("walmart_ca", None, "ca"), ("walmart_us", "2026-01-24-13-32-35", "us")]),
    "home_depot": dict(qid="Q864407", inputs=[("home_depot", None, "us"), ("home_depot_ca", None, "ca")]),
    "lowes": dict(qid="Q1373493", inputs=[("lowes_us", "2026-07-11-13-32-25", "us")]),
    "best_buy": dict(qid="Q533415", drop_name_re=r"Distribution Center",
                     inputs=[("best_buy", None, "us"), ("best_buy_ca", None, "ca")]),
    "target": dict(qid="Q1046951", inputs=[("target_us", None, "us")]),
}

if os.environ.get("CHAINS"):  # e.g. CHAINS=walmart,home_depot to build a subset (default: all)
    CHAINS = {k: v for k, v in CHAINS.items() if k in os.environ["CHAINS"].split(",")}


def atp_src(spider, run):
    if run is None:
        m = ATP["spiders"][spider]
        return src(f"atp-{spider}-{ATP_DATE}", f"All The Places spider '{spider}' (run {ATP['run_id']})", m["url"], "CC0 1.0",
                   ATP_DATE, RAW / "atp" / f"{spider}.geojson")
    m = OLDER[run][spider]
    return src(f"atp-{spider}-{run[:10]}", f"All The Places spider '{spider}' (older run {run}; latest run empty or partial)",
               m["url"], "CC0 1.0", run[:10], RAW / "atp_runs" / run / f"{spider}.geojson")


for fname, cfg in CHAINS.items():
    q = cfg["qid"]
    accept = cfg.get("accept", {q})
    rows, seen, st = [], set(), Counter()
    for spider, run, ns in cfg["inputs"]:
        path = RAW / "atp" / f"{spider}.geojson" if run is None else RAW / "atp_runs" / run / f"{spider}.geojson"
        t = path.read_text().strip()
        sid_src = atp_src(spider, run)
        for f in json.loads(t)["features"] if t else []:
            p = f["properties"]
            st[f"features:{spider}" + (f"@{run[:10]}" if run else "")] += 1
            if p.get("brand:wikidata") not in accept:
                st[f"excluded_brand:{p.get('brand')}:{p.get('brand:wikidata')}"] += 1
                continue
            nm = p.get("name") or ""
            if nm in cfg.get("drop_names", ()) or (cfg.get("drop_name_re") and re.search(cfg["drop_name_re"], nm)):
                st[f"excluded_name:{nm}"] += 1
                continue
            ref = str(p.get("ref") or "")
            if ref.startswith("http"):
                m = re.search(r"(\d+)(?:\.html)?/?$", ref)
                ref = m.group(1) if m else ""
            if not ref:
                st["excluded_no_ref"] += 1
                continue
            sid = f"{ns}-{ref}"
            if sid in seen:
                st["duplicate_store_id_dropped"] += 1
                continue
            seen.add(sid)
            cc = p.get("addr:country", "")
            g = f.get("geometry")
            lat, lon = (round(g["coordinates"][1], 6), round(g["coordinates"][0], 6)) if g else ("", "")
            phone = p.get("phone", "") or ""
            if cc in ("US", "PR"):
                phone = phone_us(phone) or phone
            fl = [f"atp_older_run_{run[:10]}"] if run else []
            if not p.get("addr:street_address") and p.get("addr:full"):
                fl.append("address_is_addr_full")
            subq = cfg.get("sub_by_name", {}).get(nm, "")
            rows.append(dict(store_id=sid, brand=WD.get(q, {}).get("label", ""), brand_qid=qid(q), parent_brand_qid=parent_of(q),
                             address=p.get("addr:street_address") or p.get("addr:full") or "", city=p.get("addr:city", ""),
                             state=p.get("addr:state", ""), zip=p.get("addr:postcode", ""), county="", lat=lat, lon=lon,
                             phone=phone, sub_brand=WD.get(subq, {}).get("label", "") if subq else "", flags=fl,
                             source=";".join([sid_src, S_CEN, S_WD]) if cc == "US" else ";".join([sid_src, S_WD]),
                             source_url=p.get("website") or p.get("@source_uri", ""), source_date=SOURCES[sid_src]["retrieved_at"],
                             name=nm, sub_brand_qid=qid(subq) if subq else "", county_geoid="", country_code=cc, status="",
                             store_type=nm))
    df = finish(rows, check_county=True)
    _nonus = df.country_code != "US"
    df.loc[_nonus, ["county", "county_geoid"]] = ""
    summary[fname] = {"file": write(df, fname), "rows": len(df), **dict(st),
                      "rows_by_country": dict(Counter(df.country_code).most_common()),
                      "rows_by_store_type": dict(Counter(df.store_type).most_common()),
                      "missing_coordinates": int((df.lat == "").sum()),
                      "us_with_county_geoid": int(((df.country_code == "US") & (df.county_geoid != "")).sum()),
                      "us_rows": int((df.country_code == "US").sum())}

# ---------------- Wawa (user-provided list, used as-is) ----------------
# raw/inputs/wawa-stores-user-2026-10-18.numbers: the user's own list (sheet "Wawa Stores"; its "About" sheet says it was
# collected 2026-09-16 from order.wawa.com's store API). The user checked it: values are copied unchanged, no validation
# or geocoding; only the brand QID, location ids and a point-in-polygon county are added.
from numbers_parser import Document  # noqa: E402
WAWA_IN = INP / "wawa-stores-user-2026-10-18.numbers"
S_WAWA = src("wawa-user-list-2026-10-18", "user-provided Wawa list, uploaded 2026-10-18 (its About sheet: order.wawa.com store API, collected 2026-09-16)",
             "https://www.wawa.com/locations", "user-provided (wawa.com facts; not an open licence)", "2026-10-18", WAWA_IN)
_wt = Document(str(WAWA_IN)).sheets[0].tables[0].rows(values_only=True)
_hdr = next(r for r in _wt if r[0] == "Store ID")  # header row sits at the bottom of the sheet
WQ = "Q5936320"
rows = []
for r in _wt:
    if r is _hdr:
        continue
    x = dict(zip(_hdr, r))
    v = lambda k: "" if x[k] is None else str(x[k])
    rows.append(dict(store_id=v("Store ID"), brand="Wawa", brand_qid=qid(WQ), parent_brand_qid=parent_of(WQ), address=v("Street"),
                     city=v("City"), state=v("State"), zip=v("ZIP"), county="", lat=x["Latitude"] if x["Latitude"] is not None else "",
                     lon=x["Longitude"] if x["Longitude"] is not None else "", phone=v("Phone"), sub_brand="", flags=[],
                     source=S_WAWA, source_url=v("URL"), source_date="2026-10-18", name=v("Name"),
                     sub_brand_qid="", county_geoid="", country_code="US", status="", store_type=""))  # Timezone, Schedule Type: no schema column
df = finish(rows, check_county=False)
df.loc[df.county_geoid == "", "flags"] = df.loc[df.county_geoid == "", "flags"].map(lambda f: ";".join([t for t in f.split(";") if t] + ["no_county"]))
summary["wawa"] = {"file": write(df, "wawa"), "rows": len(df), "with_county_geoid": int((df.county_geoid != "").sum()),
                   "input_columns": list(_hdr)}

# ---------------- brands.csv ----------------
used = Counter()
files = defaultdict(set)
LOC = {}
for name in ("walgreens", "cvs", "mcdonalds", "marriott", "starbucks", "wawa", *CHAINS):
    p = OUT / summary[name]["file"]
    d = pd.read_csv(p, dtype=str, keep_default_na=False)
    LOC[name] = d
    for col in ("brand_qid", "sub_brand_qid"):
        for q, n in d[col].value_counts().items():
            if q:
                used[q] += n
                files[q].add(summary[name]["file"])
COMPANYISH = re.compile(r"company|business|enterprise|corporation|conglomerate|airline|holding|organization|plc", re.I)
# brands with locations + every ancestor reachable through P749 statements (current or historical)
in_tree, frontier = set(used), set(used)
while frontier:
    nxt = {f"wikidata:{r['parent']}" for r in RELS if f"wikidata:{r['child']}" in frontier} - in_tree
    in_tree |= nxt
    frontier = nxt
RELS = [r for r in RELS if f"wikidata:{r['child']}" in in_tree]
# ---- logos: Wikidata P154 + Commons licence (scripts/fetch_logos.py) ----
LOGO_META = read_meta("logos")
S_LOGO = src(f"wikidata-commons-logos-{LOGO_META['retrieved_at']}", "Wikidata P154 (logo image) + Wikimedia Commons file licence metadata",
             "https://commons.wikimedia.org/w/api.php", "per file: see brands.csv logo_license (Wikidata statements CC0)",
             LOGO_META["retrieved_at"], RAW / "logos.json")
_lg = json.loads((RAW / "logos.json").read_text())
_cm = {}
for t, m in _lg["commons"].items():
    _cm[m["requested"]] = _cm[t] = m
FREE = re.compile(r"^(pd|cc0|cc-by(-sa)?(-[\d.]+)?(-[a-z]+)?)$", re.I)
def _txt(h):
    h = re.sub(r"<(span|div)[^>]*display: ?none[^>]*>.*?</\1>", "", h or "", flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h))).strip()
_by = defaultdict(list)
for r in _lg["wdqs"]:
    _by[r["item"].rsplit("/", 1)[-1]].append(r)
def logo_for(q):
    """Pick one P154 value: preferred rank, else the only one without an end date. Return (cols, flags)."""
    st = _by.get(q, [])
    if not st:
        return {}, ["logo_no_p154"]
    pref = [r for r in st if r["rank"].endswith("PreferredRank")]
    open_ = [r for r in st if not r.get("end")]
    pick = pref if len(pref) == 1 else open_ if len(open_) == 1 else []
    if not pick:
        return {}, ["logo_multiple_p154_no_rank_or_dates_review"]
    fname = urllib.parse.unquote(pick[0]["logo"].rsplit("/", 1)[-1])
    m = _cm.get("File:" + fname, {})
    em = m.get("imageinfo", {}).get("extmetadata", {})
    g = lambda k: (em.get(k) or {}).get("value", "")
    lic, short = g("License"), _txt(g("LicenseShortName"))
    cats = g("Categories").split("|")
    basis = [c for c in cats if c.startswith("PD ") or c.startswith("PD-") or c.startswith("CC-")]
    restr = g("Restrictions")
    said = ", ".join(t for t in [short + (f" ({', '.join(basis)})" if basis else ""), f"restrictions: {restr}" if restr else ""] if t)
    fl = []
    if m.get("missing") or not FREE.match(lic or ""):
        return {}, [f"logo_not_free_or_unknown_licence:{said}"]
    att = _txt(g("Artist")) or _txt(g("Credit"))
    return dict(logo_file=fname, logo_license=said, logo_attribution=att,
                logo_source_url=m["imageinfo"].get("descriptionurl", "")), fl

brows = []
for q, e in sorted(WD.items(), key=lambda t: int(t[0][1:])):
    wid = f"wikidata:{q}"
    if wid not in in_tree:
        continue
    p31 = ";".join(e["p31"].values())
    fl = []
    if wid in used:
        kind = "brand"
    elif COMPANYISH.search(p31):
        kind = "company"
    elif re.search(r"\bchain\b|\bbrand\b", p31):
        kind = "brand"
    else:
        kind = ""
        fl.append("kind_review")
    cur = CURRENT.get(q, [])
    brows.append(dict(entity_id=wid, kind=kind, name=e["label"], brand_name=e["label"] if kind == "brand" else "",
                      instance_of=p31, parent_brand_id=parent_of(q),
                      parent_brand_name=";".join(WD.get(p, {}).get("label", "") for p in cur), website=";".join(e["website"]),
                      location_files=";".join(sorted(files.get(wid, []))), location_count=used.get(wid, 0), flags=";".join(fl),
                      source_id=S_WD, source_url=f"https://www.wikidata.org/wiki/{q}", retrieved_at=SOURCES[S_WD]["retrieved_at"]))
    lc, lfl = logo_for(q)
    brows[-1].update({k: lc.get(k, "") for k in ("logo_file", "logo_license", "logo_attribution", "logo_source_url")})
    brows[-1]["logo_flags"] = ";".join(lfl)
pd.DataFrame(brows).to_csv(ROOT / "brands.csv", index=False, lineterminator="\n")
summary["brands_rows"] = len(brows)
summary["brands_by_kind"] = dict(Counter(r["kind"] or "(review)" for r in brows))

# ---------------- brand_relationships.csv (every P749 statement, dates from P580/P582) ----------------
ncur = Counter(r["child"] for r in RELS if not r["end"])
rrows = []
for r in sorted(RELS, key=lambda r: (int(r["child"][1:]), r["start"] or "9999", int(r["parent"][1:]))):
    fl = []
    if not r["start"] and not r["end"] and ncur[r["child"]] > 1:
        fl.append("multiple_current_parents_no_dates_review")
    rrows.append(dict(parent_id=f"wikidata:{r['parent']}", child_id=f"wikidata:{r['child']}", relation="parent_org",
                      valid_from=r["start"], valid_to=r["end"], current="yes" if not r["end"] else "no",
                      wikidata_rank=r["rank"].replace("Rank", "").lower(), flags=";".join(fl), source_id=S_WD,
                      source_url=f"https://www.wikidata.org/wiki/{r['child']}#P749", retrieved_at=SOURCES[S_WD]["retrieved_at"]))
rel = pd.DataFrame(rrows, columns=["parent_id", "child_id", "relation", "valid_from", "valid_to", "current", "wikidata_rank",
                                   "flags", "source_id", "source_url", "retrieved_at"])
assert set(rel.parent_id) | set(rel.child_id) <= {r["entity_id"] for r in brows}
rel.to_csv(ROOT / "brand_relationships.csv", index=False, lineterminator="\n")
summary["brand_relationships_rows"] = len(rel)
summary["brand_relationships_review_flags"] = int((rel["flags"] != "").sum())

# ---------------- company_locations.csv (one row per establishment) ----------------
# geoid only when the county is in the agreed v2-2024 set (data-v3/geo/counties.csv); PR/VI are not in it
V2_COUNTIES = set(pd.read_csv(ROOT.parents[1] / "geo" / "counties.csv", dtype=str, keep_default_na=False).geoid)
LCOL = ["location_id", "entity_id", "sub_entity_id", "role", "name", "address", "geoid", "boundary_set", "lat", "lon", "source_id",
        "retrieved_at", "brand_name", "geoid_method", "flags", "country_code"]
lrows, excluded = [], Counter()
for fname, d in LOC.items():
    for x in d.itertuples(index=False):
        ent = x.brand_qid
        if not ent:
            excluded[f"{fname}:no_brand_qid"] += 1
            continue
        if not x.store_id:
            excluded[f"{fname}:no_store_id"] += 1
            continue
        lid = f"{fname}:{x.store_id}"
        if not x.lat and not x.county_geoid:
            excluded[f"{fname}:no_point_no_geoid"] += 1
            continue
        srcs = x.source.split(";")
        if "coordinates_from_atp" in x.flags:
            sid = next(s for s in srcs if s.startswith("atp-"))
        elif "v5_user_approved" in x.flags:
            sid = S_V5OK
        elif "coordinates_from_marriott_feed" in x.flags:
            sid = S_PAC
        else:
            sid = srcs[0]
        addr = ", ".join(t for t in (x.address, x.city, x.state, x.zip) if t)
        geoid, lfl = x.county_geoid, [f for f in x.flags.split(";") if f]
        if geoid and geoid not in V2_COUNTIES:
            lfl.append(f"county_not_in_v2-2024:{geoid}")
            geoid = ""
        lrows.append(dict(location_id=lid, entity_id=ent, sub_entity_id=x.sub_brand_qid, role="establishment_at", name=x.name, address=addr,
                          geoid=geoid, boundary_set="v2-2024" if geoid else "", lat=x.lat, lon=x.lon,
                          source_id=sid, retrieved_at=SOURCES[sid]["retrieved_at"], brand_name=WD.get(ent[9:], {}).get("label", ""),
                          geoid_method=("nearest_county_within_2km" if "county_nearest_within_2km" in x.flags else
                                        "point_in_polygon_cb2024" if geoid else ""),
                          flags=";".join(lfl), country_code=x.country_code))
locs = pd.DataFrame(lrows, columns=LCOL)
dupl = locs.location_id.duplicated(keep=False)
locs.loc[dupl, "flags"] = locs.loc[dupl, "flags"].map(lambda f: ";".join(filter(None, [f, "duplicate_location_id_review"])))
p = ROOT / "company_locations.csv"
locs.to_csv(p, index=False, lineterminator="\n")
if p.stat().st_size > 5_000_000:
    locs.to_csv(ROOT / "company_locations.csv.gz", index=False, lineterminator="\n",
                compression={"method": "gzip", "mtime": 0, "compresslevel": 9})
    p.unlink()
summary["company_locations_rows"] = len(locs)
summary["company_locations_by_entity_top"] = {k: int(v) for k, v in locs.entity_id.value_counts().head(10).items()}
summary["company_locations_with_geoid"] = int((locs.geoid != "").sum())
summary["company_locations_excluded"] = dict(excluded)
summary["company_locations_duplicate_ids"] = int(dupl.sum())
summary["hq_in_rows"] = 0

# ---------------- retracted_locations.csv ----------------
# Known permanent closures only. The inputs carry temporary statuses (kept as flags), not closures, so this starts empty.
pd.DataFrame(columns=["location_id", "retracted_at", "reason", "source_id"]).to_csv(ROOT / "retracted_locations.csv", index=False)
summary["retracted_locations_rows"] = 0
pd.DataFrame(SOURCES.values()).to_csv(ROOT / "sources.csv", index=False, lineterminator="\n")
summary["marriott_brand_name_to_qid_learned_from_atp"] = BRAND_Q
summary["marriott_brand_name_to_qid_wikidata"] = WD_BRAND
summary["built"] = today()
(ROOT / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=int) + "\n")
print(json.dumps(summary, indent=1, ensure_ascii=False, default=int))
