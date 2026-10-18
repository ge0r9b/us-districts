"""Wikidata items with an IPEDS unit ID (P1771), for scripts/build_colleges.py.

One SPARQL query (truthy statements, so deprecated ones are skipped); raw answer saved to raw/wikidata_ipeds.json.
"""
import json

from common import RAW, get, today, write_meta

Q = """SELECT ?item ?id ?itemLabel ?inst WHERE {
  ?item wdt:P1771 ?id .
  OPTIONAL { ?item wdt:P31 ?inst . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul". }
}"""
r = get("https://query.wikidata.org/sparql", params={"query": Q, "format": "json"},
        headers={"Accept": "application/sparql-results+json"})
r.raise_for_status()
j = r.json()
(RAW / "wikidata_ipeds.json").write_text(json.dumps(j))
write_meta("wikidata_ipeds", {"retrieved_at": today(), "url": "https://query.wikidata.org/sparql", "query": Q,
                              "rows": len(j["results"]["bindings"])})
print(len(j["results"]["bindings"]))
