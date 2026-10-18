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
import re
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
ATP_USED = ("mcdonalds", "marriott_hotels", "ritz_carlton")
S_ATP = {s: src(f"atp-{s}-{ATP_DATE}", f"All The Places spider '{s}' (run {ATP['run_id']})", ATP["spiders"][s]["url"],
                "CC0 1.0", ATP_DATE, RAW / "atp" / f"{s}.geojson") for s in ATP_USED}

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

def parent_of(qid):
    return ";".join(f"wikidata:{p}" for p in WD.get(qid, {}).get("p749", {})) if qid else ""

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
    if hit:
        s, f = hit
        p = f["properties"]
        srcs.append(S_ATP[s])
        stats["atp_matched"] += 1
        g = f.get("geometry")
        if g:
            alon, alat = g["coordinates"][:2]
            if lat == "":
                lat, lon = alat, alon
                fl.append("coordinates_from_atp")
                stats["coords_filled_from_atp"] += 1
            elif km(lat, lon, alat, alon) > 1:
                fl.append(f"v5_vs_atp_coordinates_{km(lat, lon, alat, alon):.1f}km")
        if not addr and p.get("addr:street_address"):
            addr = p["addr:street_address"]
            fl.append("address_from_atp")
            stats["address_filled_from_atp"] += 1
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
    if not bq and BRAND_Q.get(x.brand):
        bq = BRAND_Q[x.brand]
        fl.append("brand_qid_from_brand_name")
    if cc == "US" or not cc and x.country == "United States":
        phone = phone_us(phone) or phone
    rows.append(dict(store_id=x.marsha, brand=x.brand, brand_qid=qid(bq), parent_brand_qid=parent_of(bq), address=addr,
                     city=city, state=state, zip=zipc, county="", lat=round(lat, 6) if lat != "" else "",
                     lon=round(lon, 6) if lon != "" else "", phone=phone, sub_brand=sub, flags=fl,
                     source=";".join(srcs + [S_CEN, S_WD]), source_url=url or (hit[1]["properties"].get("website", "") if hit else ""),
                     source_date=max(SOURCES[s]["retrieved_at"] for s in srcs), name=x.hotel_name, sub_brand_qid="",
                     county_geoid="", country_code=cc, status="", store_type=""))
df = finish(rows, check_county=False)
v5_codes = set(v5.marsha)
summary["marriott"] = {"file": write(df, "marriott"), "rows": len(df), "input_rows": n_in, "exact_duplicate_rows_dropped": exact_dups,
                       "v5_missing_coordinates": int((v5.coordinates == "").sum()), **stats,
                       "still_missing_coordinates": int((df.lat == "").sum()),
                       "atp_properties_not_in_v5": len(set(atp) - v5_codes),
                       "us_rows": int((df.country_code == "US").sum()),
                       "flags": dict(Counter(re.sub(r"_[\d.]+km$", "_km", f.split(":")[0]) for fl in df["flags"] for f in fl.split(";") if f))}

# ---------------- brands.csv ----------------
used = Counter()
files = defaultdict(set)
for name in ("walgreens", "cvs", "mcdonalds", "marriott"):
    p = OUT / summary[name]["file"]
    d = pd.read_csv(p, dtype=str, keep_default_na=False)
    for col in ("brand_qid", "sub_brand_qid"):
        for q, n in d[col].value_counts().items():
            if q:
                used[q] += n
                files[q].add(summary[name]["file"])
brows = []
for q, e in sorted(WD.items(), key=lambda t: int(t[0][1:])):
    wid = f"wikidata:{q}"
    is_brand = wid in used
    is_parent = any(wid in parent_of(k[9:]).split(";") for k in used)
    if not (is_brand or is_parent):
        continue
    brows.append(dict(entity_id=wid, name=e["label"], kind="brand" if is_brand else "organization",
                      instance_of=";".join(e["p31"].values()), parent_brand_id=parent_of(q),
                      parent_brand_name=";".join(e["p749"].values()), website=";".join(e["website"]),
                      location_files=";".join(sorted(files.get(wid, []))), location_count=used.get(wid, 0),
                      source=S_WD, source_url=f"https://www.wikidata.org/wiki/{q}", source_date=SOURCES[S_WD]["retrieved_at"]))
pd.DataFrame(brows).to_csv(ROOT / "brands.csv", index=False, lineterminator="\n")
pd.DataFrame(SOURCES.values()).to_csv(ROOT / "sources.csv", index=False, lineterminator="\n")
summary["brands_rows"] = len(brows)
summary["marriott_brand_name_to_qid_learned_from_atp"] = BRAND_Q
summary["marriott_brand_name_to_qid_wikidata"] = WD_BRAND
summary["built"] = today()
(ROOT / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
print(json.dumps(summary, indent=1, ensure_ascii=False))
