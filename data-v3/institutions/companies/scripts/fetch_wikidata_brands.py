"""Fetch brand facts from Wikidata (CC0) for a list of QIDs: English label, instance of (P31),
parent organization (P749), owned by (P127), official website (P856).

Usage: python fetch_wikidata_brands.py Q38076 Q1591889 ...   -> raw/wikidata_brands.json
Also saves every item whose P749/P127 is Marriott International or Starwood (labels + English aliases)
to raw/wikidata_owner_children.csv, used by build_locations.py to resolve Marriott brand names exactly.
Only statements present on Wikidata are recorded; deprecated-rank statements are skipped (wdt: = best rank).
"""
import json
import sys

from common import RAW, get, today, write_meta

EP = "https://query.wikidata.org/sparql"
Q = """SELECT ?item ?itemLabel ?p31 ?p31Label ?p749 ?p749Label ?p127 ?p127Label ?web WHERE {
  VALUES ?item { %s }
  OPTIONAL { ?item wdt:P31 ?p31 }
  OPTIONAL { ?item wdt:P749 ?p749 }
  OPTIONAL { ?item wdt:P127 ?p127 }
  OPTIONAL { ?item wdt:P856 ?web }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul". }
}"""


def run(qids):
    r = get(EP, params={"query": Q % " ".join(f"wd:{q}" for q in qids)},
            headers={"Accept": "application/sparql-results+json"})
    r.raise_for_status()
    out = {}
    for b in r.json()["results"]["bindings"]:
        v = lambda k: b.get(k, {}).get("value", "")
        q = v("item").rsplit("/", 1)[-1]
        e = out.setdefault(q, {"label": v("itemLabel"), "p31": {}, "p749": {}, "p127": {}, "website": set()})
        for p in ("p31", "p749", "p127"):
            if v(p):
                e[p][v(p).rsplit("/", 1)[-1]] = v(p + "Label")
        if v("web"):
            e["website"].add(v("web"))
    for e in out.values():
        e["website"] = sorted(e["website"])
    return out


CHILDREN = """SELECT DISTINCT ?item ?itemLabel ?alt ?par WHERE {
  VALUES ?par { %s } { ?item wdt:P749 ?par } UNION { ?item wdt:P127 ?par }
  OPTIONAL { ?item skos:altLabel ?alt FILTER(lang(?alt)="en") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul". } }"""
# Brand owners whose child items are used to resolve brand names that All The Places does not tag
OWNERS = ["Q1141173", "Q552363"]  # Marriott International, Starwood


def children():
    r = get(EP, params={"query": CHILDREN % " ".join(f"wd:{q}" for q in OWNERS)}, headers={"Accept": "text/csv"})
    r.raise_for_status()
    (RAW / "wikidata_owner_children.csv").write_text(r.text)
    return {row.split(",")[0].rsplit("/", 1)[-1] for row in r.text.splitlines()[1:] if row}


REL = """SELECT ?item ?parent ?rank ?start ?end WHERE {
  VALUES ?item { %s }
  ?item p:P749 ?st . ?st ps:P749 ?parent ; wikibase:rank ?rank .
  OPTIONAL { ?st pq:P580 ?start } OPTIONAL { ?st pq:P582 ?end } }"""


def relations(qids):
    """Every P749 (parent organization) statement of each item, with rank and P580/P582 qualifiers."""
    r = get(EP, params={"query": REL % " ".join(f"wd:{q}" for q in qids)},
            headers={"Accept": "application/sparql-results+json"})
    r.raise_for_status()
    out = []
    for b in r.json()["results"]["bindings"]:
        v = lambda k: b.get(k, {}).get("value", "")
        out.append({"child": v("item").rsplit("/", 1)[-1], "parent": v("parent").rsplit("/", 1)[-1],
                    "rank": v("rank").rsplit("#", 1)[-1], "start": v("start")[:10], "end": v("end")[:10]})
    return out


def main(qids):
    children()
    data = run(qids)
    # follow P749 statements (all non-deprecated ranks) up to the top so every parent has its own row
    rels, todo, seen = [], list(qids), set()
    while todo:
        batch = [q for q in todo if q not in seen]
        seen.update(batch)
        if not batch:
            break
        rs = [x for x in relations(batch) if x["rank"] != "DeprecatedRank"]
        rels.extend(rs)
        todo = sorted({x["parent"] for x in rs} - seen)
    missing = sorted({x["parent"] for x in rels} - set(data))
    if missing:
        data.update(run(missing))
    (RAW / "wikidata_p749.json").write_text(json.dumps(rels, indent=1))
    (RAW / "wikidata_brands.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
    write_meta("wikidata_brands", {"endpoint": EP, "retrieved_at": today(), "qids": len(data)})
    print(len(data), file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
