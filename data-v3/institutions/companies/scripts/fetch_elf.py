"""Fetch the ISO 20275 Entity Legal Form (ELF) code list from the GLEIF API (CC0 1.0).

https://api.gleif.org/api/v1/entity-legal-forms  ->  raw/gleif/elf.csv (code, country, subdivision, name)
Used only to turn Entity.LegalForm.EntityLegalFormCode into a readable legal_form.
"""
import csv

from common import RAW, get, today, write_meta

URL = "https://api.gleif.org/api/v1/entity-legal-forms?page[size]=200&page[number]={n}"


def main():
    rows, n = [], 1
    while True:
        j = get(URL.format(n=n), 0.3).json()
        for d in j["data"]:
            a = d["attributes"]
            names = a.get("names") or []
            en = [x for x in names if x.get("languageCode") == "en"] or names
            nm = (en[0].get("transliteratedName") or en[0].get("localName")) if en else ""
            rows.append([a["code"], a.get("countryCode") or "", a.get("subdivisionCode") or "", nm, a.get("status") or ""])
        if n >= j["meta"]["pagination"]["lastPage"]:
            break
        n += 1
    (RAW / "gleif").mkdir(parents=True, exist_ok=True)
    with open(RAW / "gleif" / "elf.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["code", "country", "subdivision", "name", "status"])
        w.writerows(rows)
    write_meta("gleif_elf", {"url": "https://api.gleif.org/api/v1/entity-legal-forms", "retrieved_at": today(), "rows": len(rows)})
    print(len(rows))


if __name__ == "__main__":
    main()
