"""Wikidata items of a class (P31/P279*), one SPARQL query per property, for organizations/<name>_world.csv builds.

Usage: python fetch_wikidata_orgs.py <name> <classQID>[,<classQID>...] [extra props P229,P230,...]
Writes raw/wikidata_<name>/<prop>.json (WDQS answers, untouched) and raw/wikidata_<name>.meta.json.
Truthy statements (wdt:) only, so deprecated values are skipped and preferred ones win.
"""
import json
import os
import sys
import time

from common import RAW, get, today, write_meta

name, classes = sys.argv[1], sys.argv[2].split(",")
extra = sys.argv[3].split(",") if len(sys.argv) > 3 else []
out = RAW / f"wikidata_{name}"
out.mkdir(exist_ok=True)
CLS = " UNION ".join(f"{{ ?i wdt:P31/wdt:P279* wd:{c} . }}" for c in classes)
if os.environ.get("INDUSTRY"):  # also items whose P452 (industry) is one of these
    CLS += "".join(f" UNION {{ ?i wdt:P452 wd:{c} . }}" for c in os.environ["INDUSTRY"].split(","))
LBL = 'SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul". }'
Q = {
    "items": f"SELECT DISTINCT ?i ?iLabel ?iDescription WHERE {{ {CLS} {LBL} }}",
    "P31": f"SELECT DISTINCT ?i ?v ?vLabel WHERE {{ {CLS} ?i wdt:P31 ?v . {LBL} }}",
    "P17": f"SELECT DISTINCT ?i ?v ?vLabel ?iso WHERE {{ {CLS} ?i wdt:P17 ?v . OPTIONAL {{ ?v wdt:P297 ?iso }} {LBL} }}",
    "P159": f"""SELECT DISTINCT ?i ?v ?vLabel ?coord ?qcoord ?iso ?vctry WHERE {{ {CLS} ?i p:P159 ?st . ?st ps:P159 ?v .
               FILTER NOT EXISTS {{ ?st pq:P582 ?e }} OPTIONAL {{ ?st pq:P625 ?qcoord }} OPTIONAL {{ ?v wdt:P625 ?coord }}
               OPTIONAL {{ ?v wdt:P17 ?vctry . ?vctry wdt:P297 ?iso }} {LBL} }}""",
    "P749": f"SELECT DISTINCT ?i ?v ?vLabel WHERE {{ {CLS} ?i wdt:P749 ?v . {LBL} }}",
    "P127": f"SELECT DISTINCT ?i ?v ?vLabel WHERE {{ {CLS} ?i wdt:P127 ?v . {LBL} }}",
    "P571": f"SELECT DISTINCT ?i ?v ?prec WHERE {{ {CLS} ?i p:P571 ?st . ?st wikibase:rank ?rk . FILTER(?rk != wikibase:DeprecatedRank) ?st psv:P571 [ wikibase:timeValue ?v ; wikibase:timePrecision ?prec ] . }}",
    "P576": f"SELECT DISTINCT ?i ?v ?prec WHERE {{ {CLS} ?i p:P576 ?st . ?st wikibase:rank ?rk . FILTER(?rk != wikibase:DeprecatedRank) ?st psv:P576 [ wikibase:timeValue ?v ; wikibase:timePrecision ?prec ] . }}",
    "P856": f"SELECT DISTINCT ?i ?v WHERE {{ {CLS} ?i wdt:P856 ?v . }}",
    "P154": f"SELECT DISTINCT ?i ?v WHERE {{ {CLS} ?i wdt:P154 ?v . }}",
}
if os.environ.get("ULTIMATE"):  # top of the P749 chain: an ancestor that itself has no P749
    Q["ultimate"] = f"SELECT DISTINCT ?i ?v ?vLabel WHERE {{ {CLS} ?i wdt:P749+ ?v . FILTER NOT EXISTS {{ ?v wdt:P749 ?x }} {LBL} }}"
for p in extra:
    Q[p] = f"SELECT DISTINCT ?i ?v ?vLabel WHERE {{ {CLS} ?i wdt:{p} ?v . {LBL} }}"
import os
ONLY = os.environ.get("ONLY", "").split(",") if os.environ.get("ONLY") else None
meta_old = json.loads((RAW / f"wikidata_{name}.meta.json").read_text()) if (RAW / f"wikidata_{name}.meta.json").exists() else {}
counts = dict(meta_old.get("rows", {})) if ONLY else {}
for k, q in Q.items():
    if ONLY and k not in ONLY:
        continue
    for attempt in range(3):
        r = get("https://query.wikidata.org/sparql", min_interval=2, params={"query": q, "format": "json"},
                headers={"Accept": "application/sparql-results+json"})
        if r.ok:
            break
        time.sleep(10)
    r.raise_for_status()
    j = r.json()
    (out / f"{k}.json").write_text(json.dumps(j))
    counts[k] = len(j["results"]["bindings"])
    print(k, counts[k], file=sys.stderr)
write_meta(f"wikidata_{name}", {"retrieved_at": today(), "url": "https://query.wikidata.org/sparql", "classes": classes,
                                "industry_p452": os.environ.get("INDUSTRY", ""),
                                "queries": Q, "rows": counts})
