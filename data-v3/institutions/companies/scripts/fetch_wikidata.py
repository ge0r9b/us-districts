"""Fetch Wikidata cross-identifiers: every item with an SEC CIK (P5531) or an LEI (P1278).

Source: Wikidata Query Service, https://query.wikidata.org/ (CC0 1.0).
Used only as an ID crosswalk (QID <-> CIK <-> LEI). An identifier pair is used only when Wikidata
states it on one item; nothing is matched by name. Writes raw/wikidata/xids.csv (gitignored).
"""
import csv
import io

from common import RAW, get, today, write_meta

EP = "https://query.wikidata.org/sparql"
QUERIES = {
    "cik": "SELECT ?item ?cik ?lei WHERE { ?item wdt:P5531 ?cik . OPTIONAL { ?item wdt:P1278 ?lei } }",
    "lei": "SELECT ?item ?cik ?lei WHERE { ?item wdt:P1278 ?lei . OPTIONAL { ?item wdt:P5531 ?cik } }",
}


def main():
    d = RAW / "wikidata"
    d.mkdir(parents=True, exist_ok=True)
    rows = set()
    for name, q in QUERIES.items():
        r = get(EP, params={"query": q}, headers={"Accept": "text/csv"})
        r.raise_for_status()
        for row in csv.DictReader(io.StringIO(r.text)):
            qid = row["item"].rsplit("/", 1)[-1]
            rows.add((qid, row.get("cik", "").strip(), row.get("lei", "").strip().upper()))
    with open(d / "xids.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["qid", "cik", "lei"])
        w.writerows(sorted(rows))
    write_meta("wikidata", {"endpoint": EP, "queries": QUERIES, "retrieved_at": today(), "rows": len(rows)})
    print(len(rows))


if __name__ == "__main__":
    main()
