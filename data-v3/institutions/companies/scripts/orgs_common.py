"""Shared helpers for organizations/<name>_world.csv builds (airlines, telecoms): Wikidata answers, HQ county, logos."""
import collections
import hashlib
import html
import json
import re
import urllib.parse

import pandas as pd
import shapefile
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

from common import RAW, ROOT, get, read_meta, today, write_meta

LCOL = ["location_id", "entity_id", "sub_entity_id", "role", "name", "address", "geoid", "boundary_set", "lat", "lon", "source_id",
        "retrieved_at", "brand_name", "geoid_method", "flags", "country_code"]
V2 = set(pd.read_csv(ROOT.parents[1] / "geo" / "counties.csv", dtype=str, keep_default_na=False).geoid)
_r = shapefile.Reader(str(RAW / "inputs" / "cb_2024_us_county_500k.shp"))
_fn = [f[0] for f in _r.fields[1:]]
GEOMS, CINFO = [], []
for _sr in _r.iterShapeRecords():
    _a = dict(zip(_fn, _sr.record))
    GEOMS.append(shape(_sr.shape.__geo_interface__))
    CINFO.append((_a["NAMELSAD"], _a["GEOID"], _a["STUSPS"]))
TREE = STRtree(GEOMS)


def county(lat, lon):
    pt = Point(float(lon), float(lat))
    for i in TREE.query(pt):
        if GEOMS[i].covers(pt):
            return CINFO[i]
    return ("", "", "")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def qid(uri):
    return uri.rsplit("/", 1)[-1]


def load(name):
    """{prop: [binding dicts with plain values]} from raw/wikidata_<name>/*.json"""
    out = {}
    for p in (RAW / f"wikidata_{name}").glob("*.json"):
        out[p.stem] = [{k: v["value"] for k, v in b.items()} for b in json.loads(p.read_text())["results"]["bindings"]]
    return out


def by_item(rows, key="v"):
    d = collections.defaultdict(list)
    for r in rows:
        if r.get(key) not in d[qid(r["i"])]:
            d[qid(r["i"])].append(r)
    return d


def point(wkt):
    m = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", wkt or "")
    return (round(float(m.group(2)), 6), round(float(m.group(1)), 6)) if m else None


FREE = re.compile(r"^(pd|cc0|cc-by(-sa)?(-[\d.]+)?(-[a-z]+)?)$", re.I)


def _txt(h):
    h = re.sub(r"<(span|div)[^>]*display: ?none[^>]*>.*?</\1>", "", h or "", flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h))).strip()


def commons_meta(name, files):
    """Commons extmetadata for the files, cached in raw/commons_<name>.json (fetched once)."""
    p = RAW / f"commons_{name}.json"
    meta = json.loads(p.read_text()) if p.exists() else {}
    todo = sorted(set(files) - {m["requested"][5:] for m in meta.values()} - {t[5:] for t in meta})
    for i in range(0, len(todo), 40):
        chunk = todo[i:i + 40]
        j = get("https://commons.wikimedia.org/w/api.php", min_interval=1, params={
            "action": "query", "format": "json", "prop": "imageinfo", "iiprop": "extmetadata|url",
            "titles": "|".join("File:" + f for f in chunk)}).json()
        norm = {n["to"]: n["from"] for n in j["query"].get("normalized", [])}
        for pg in j["query"]["pages"].values():
            meta[pg["title"]] = {"requested": norm.get(pg["title"], pg["title"]), "missing": "missing" in pg,
                                 "imageinfo": pg.get("imageinfo", [{}])[0]}
    if todo or not p.exists():
        p.write_text(json.dumps(meta))
        write_meta(f"commons_{name}", {"retrieved_at": today(), "url": "https://commons.wikimedia.org/w/api.php", "files": len(meta)})
    cm = {}
    for t, m in meta.items():
        cm[m["requested"]] = cm[t] = m
    return cm


def logo(urls, cm):
    """urls: truthy P154 values of one item. Returns (cols, flags) like brands.csv."""
    if not urls:
        return {}, ["logo_no_p154"]
    if len(urls) > 1:
        return {}, ["logo_multiple_p154_no_rank_or_dates_review"]
    fname = urllib.parse.unquote(urls[0].rsplit("/", 1)[-1])
    m = cm.get("File:" + fname, {})
    em = m.get("imageinfo", {}).get("extmetadata", {})
    g = lambda k: (em.get(k) or {}).get("value", "")
    lic, short = g("License"), _txt(g("LicenseShortName"))
    basis = [c for c in g("Categories").split("|") if c.startswith(("PD ", "PD-", "CC-"))]
    restr = g("Restrictions")
    said = ", ".join(t for t in [short + (f" ({', '.join(basis)})" if basis else ""), f"restrictions: {restr}" if restr else ""] if t)
    if m.get("missing") or not FREE.match(lic or ""):
        return {}, [f"logo_not_free_or_unknown_licence:{said}"]
    return dict(logo_file=fname, logo_license=said, logo_attribution=_txt(g("Artist")) or _txt(g("Credit")),
                logo_source_url=m["imageinfo"].get("descriptionurl", "")), []


def date(v):
    return v[:10].lstrip("+") if v else ""
