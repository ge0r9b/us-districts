"""Brand logos: Wikidata P154 (logo image) + the Wikimedia Commons file page's licence metadata.

Reads entity ids from brands.csv, asks WDQS for every non-deprecated P154 value (best rank first),
then the Commons API (prop=imageinfo, iiprop=extmetadata|url) for each file.
Writes raw/logos.json untouched-ish (query results + Commons extmetadata) and raw/logos.meta.json.
"""
import json
import sys
import urllib.parse

import pandas as pd

from common import RAW, ROOT, get, today, write_meta

ids = [e.split(":", 1)[1] for e in pd.read_csv(ROOT / "brands.csv", dtype=str).entity_id]
q = """SELECT ?item ?logo ?rank ?start ?end WHERE { VALUES ?item { %s }
  ?item p:P154 ?st . ?st ps:P154 ?logo ; wikibase:rank ?rank . FILTER(?rank != wikibase:DeprecatedRank)
  OPTIONAL { ?st pq:P580 ?start } OPTIONAL { ?st pq:P582 ?end } }""" % " ".join(f"wd:{i}" for i in ids)
r = get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"}, min_interval=1)
r.raise_for_status()
rows = [{k: v["value"] for k, v in b.items()} for b in r.json()["results"]["bindings"]]
files = sorted({urllib.parse.unquote(x["logo"].rsplit("/", 1)[-1]) for x in rows})
meta = {}
for i in range(0, len(files), 40):
    chunk = files[i:i + 40]
    j = get("https://commons.wikimedia.org/w/api.php", min_interval=1, params={
        "action": "query", "format": "json", "prop": "imageinfo", "iiprop": "extmetadata|url",
        "titles": "|".join("File:" + f for f in chunk)}).json()
    norm = {n["to"]: n["from"] for n in j["query"].get("normalized", [])}
    for p in j["query"]["pages"].values():
        meta[p["title"]] = {"requested": norm.get(p["title"], p["title"]), "missing": "missing" in p,
                            "imageinfo": p.get("imageinfo", [{}])[0]}
(RAW / "logos.json").write_text(json.dumps({"wdqs": rows, "commons": meta}, indent=1))
write_meta("logos", {"retrieved_at": today(), "wdqs": "https://query.wikidata.org/sparql", "commons": "https://commons.wikimedia.org/w/api.php"})
print(len(rows), "P154 statements,", len(files), "files", file=sys.stderr)
