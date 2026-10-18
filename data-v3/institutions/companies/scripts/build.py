"""Build companies.csv + relationships.csv from the raw downloads (see SCHEMA.md).

Inputs (raw/, gitignored; produced by fetch_sec.py, fetch_gleif.py, fetch_elf.py, fetch_wikidata.py):
  raw/sec/company_tickers_exchange.json, raw/sec/submissions/CIK*.json.gz
  raw/gleif/lei2.csv.zip, raw/gleif/rr.csv.zip, raw/gleif/elf.csv, raw/gleif.meta.json
  raw/wikidata/xids.csv
Scope of this first pull:
  * every CIK on the SEC ticker list (company_tickers*.json);
  * every GLEIF entity (any status) on either side of an ACTIVE level-2 consolidation relationship
    (IS_DIRECTLY_CONSOLIDATED_BY / IS_ULTIMATELY_CONSOLIDATED_BY) where at least one side is a US
    entity (legal jurisdiction US*, or legal/HQ address country US).
Nothing is matched by name. CIK<->LEI links come only from the SEC submissions `lei` field or from a
single Wikidata item that carries both identifiers.
"""
import csv
import glob
import gzip
import json
import re
import sys
import zipfile
from collections import defaultdict

import pandas as pd

from common import RAW, ROOT, read_meta

US = set("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY "
         "NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR VI GU AS MP".split())
CONS = {"IS_DIRECTLY_CONSOLIDATED_BY": "direct", "IS_ULTIMATELY_CONSOLIDATED_BY": "ultimate"}
NONPROFIT = re.compile(r"non-?\s?profit|not-for-profit|not for profit|nonstock|non-stock|religious", re.I)
SEC_SRC = "sec:submissions"
SEC_LIST = "sec:company_tickers"
GLEIF_L1 = "gleif:lei-cdf"
GLEIF_L2 = "gleif:rr-cdf"
WD_SRC = "wikidata"

COLS = ["entity_id", "name", "type", "legal_form", "jurisdiction", "state_of_incorporation",
        "hq_address", "hq_state", "lat", "lon", "parent_id", "ultimate_parent_id",
        "lei", "cik", "wikidata_qid", "state_registry_id",
        "source", "source_url", "source_date",
        # extras (additive; readers may ignore)
        "ticker", "exchange", "sic", "sec_entity_type", "gleif_category", "legal_form_code",
        "entity_status", "lei_registration_status", "cik_lei_link", "flags"]
RCOLS = ["child_id", "parent_id", "relationship", "child_lei", "parent_lei", "start_date",
         "relationship_status", "registration_status", "accounting_standard",
         "source", "source_url", "source_date"]


def j(*xs, sep=", "):
    return sep.join(x.strip() for x in xs if x and str(x).strip() and str(x).strip().upper() != "NULL")


def main():
    gm = read_meta("gleif")
    gdate = gm["publish_date"][:10]
    gl1_url, rr_url = gm["files"]["lei2"]["url"], gm["files"]["rr"]["url"]
    sec_list_meta = read_meta("sec_company_tickers_exchange")
    wd_date = read_meta("wikidata")["retrieved_at"]

    # ---------- SEC ----------
    tx = json.loads((RAW / "sec" / "company_tickers_exchange.json").read_text())
    f = tx["fields"]
    tick = defaultdict(list)
    for row in tx["data"]:
        d = dict(zip(f, row))
        tick[int(d["cik"])].append((d["ticker"], d.get("exchange") or ""))
    sec = {}
    for p in glob.glob(str(RAW / "sec" / "submissions" / "CIK*.json.gz")):
        with gzip.open(p, "rt") as fh:
            s = json.load(fh)
        sec[int(s["cik"])] = s
    missing_sub = [c for c in tick if c not in sec]
    print(f"SEC: {len(tick)} ticker CIKs, {len(sec)} submissions, {len(missing_sub)} without submissions", file=sys.stderr)

    # ---------- Wikidata crosswalk ----------
    wd = pd.read_csv(RAW / "wikidata" / "xids.csv", dtype=str, keep_default_na=False)
    wd_cik_qid, wd_cik_lei, wd_lei_qid = defaultdict(set), defaultdict(set), defaultdict(set)
    for q, c, l in wd.itertuples(index=False):
        if c:
            c = int(re.sub(r"\D", "", c) or 0)
            wd_cik_qid[c].add(q)
            if l:
                wd_cik_lei[c].add(l)
        if l:
            wd_lei_qid[l].add(q)

    # ---------- CIK -> LEI ----------
    cik_lei, cik_lei_src, flags = {}, {}, defaultdict(list)
    for c in tick:
        s_lei = ((sec.get(c) or {}).get("lei") or "").strip().upper()
        w = wd_cik_lei.get(c, set())
        if s_lei:
            cik_lei[c], cik_lei_src[c] = s_lei, "sec"
            if w and s_lei not in w:
                flags[c].append("wikidata_lei_differs:" + "|".join(sorted(w)))
        elif len(w) == 1:
            cik_lei[c], cik_lei_src[c] = next(iter(w)), "wikidata"
        elif len(w) > 1:
            flags[c].append("wikidata_multiple_lei:" + "|".join(sorted(w)))
    lei_ciks = defaultdict(list)
    for c, l in cik_lei.items():
        lei_ciks[l].append(c)
    for l, cs in lei_ciks.items():
        if len(cs) > 1:  # one LEI claimed by several CIKs: do not merge, keep as flag only
            for c in cs:
                flags[c].append(f"lei_shared_by_ciks:{l}:" + "|".join(map(str, sorted(cs))))
                del cik_lei[c]

    # ---------- GLEIF level 2 ----------
    rz = zipfile.ZipFile(RAW / "gleif" / "rr.csv.zip")
    rr = pd.read_csv(rz.open(rz.namelist()[0]), dtype=str, keep_default_na=False)
    rr = rr[rr["Relationship.RelationshipType"].isin(CONS) & (rr["Relationship.RelationshipStatus"] == "ACTIVE")]

    # ---------- GLEIF level 1 (only what we need) ----------
    want_cols = ["LEI", "Entity.LegalName", "Entity.LegalJurisdiction", "Entity.EntityCategory",
                 "Entity.LegalForm.EntityLegalFormCode", "Entity.LegalForm.OtherLegalForm", "Entity.EntityStatus",
                 "Registration.RegistrationStatus", "Entity.RegistrationAuthority.RegistrationAuthorityID",
                 "Entity.RegistrationAuthority.RegistrationAuthorityEntityID", "Entity.LegalAddress.Country",
                 "Entity.HeadquartersAddress.FirstAddressLine", "Entity.HeadquartersAddress.AdditionalAddressLine.1",
                 "Entity.HeadquartersAddress.AdditionalAddressLine.2", "Entity.HeadquartersAddress.AdditionalAddressLine.3",
                 "Entity.HeadquartersAddress.City", "Entity.HeadquartersAddress.Region",
                 "Entity.HeadquartersAddress.Country", "Entity.HeadquartersAddress.PostalCode"]
    lz = zipfile.ZipFile(RAW / "gleif" / "lei2.csv.zip")
    us_lei, keep = set(), []
    rr_leis = set(rr["Relationship.StartNode.NodeID"]) | set(rr["Relationship.EndNode.NodeID"])
    sec_leis = set(cik_lei.values())
    for ch in pd.read_csv(lz.open(lz.namelist()[0]), usecols=want_cols, dtype=str, chunksize=500000, keep_default_na=False):
        isus = (ch["Entity.LegalJurisdiction"].str.startswith("US") | (ch["Entity.LegalAddress.Country"] == "US")
                | (ch["Entity.HeadquartersAddress.Country"] == "US"))
        us_lei.update(ch.loc[isus, "LEI"])
        keep.append(ch[ch["LEI"].isin(rr_leis | sec_leis)])
    g = pd.concat(keep).set_index("LEI")
    rr = rr[rr["Relationship.StartNode.NodeID"].isin(us_lei) | rr["Relationship.EndNode.NodeID"].isin(us_lei)]
    in_scope = (set(rr["Relationship.StartNode.NodeID"]) | set(rr["Relationship.EndNode.NodeID"])) & set(g.index)
    print(f"GLEIF: {len(us_lei)} US LEIs; {len(rr)} active consolidation rels touching US; {len(in_scope)} entities", file=sys.stderr)
    for c in list(cik_lei):
        if cik_lei[c] not in g.index:
            flags[c].append(f"lei_not_in_gleif:{cik_lei[c]}")
            del cik_lei[c]
            continue
        # A Wikidata item often merges a holding company with its bank / operating subsidiary. Reject a
        # Wikidata-only CIK<->LEI link when SEC and GLEIF disagree on the US state of incorporation.
        inc = ((sec.get(c) or {}).get("stateOfIncorporation") or "").upper()
        gj = g.loc[cik_lei[c], "Entity.LegalJurisdiction"]
        if cik_lei_src[c] == "wikidata" and inc in US and gj and gj != f"US-{inc}":
            flags[c].append(f"wikidata_lei_rejected_jurisdiction:{cik_lei[c]}:US-{inc}|{gj}")
            del cik_lei[c]

    elf = pd.read_csv(RAW / "gleif" / "elf.csv", dtype=str, keep_default_na=False).set_index("code")["name"].to_dict()

    # ---------- ids ----------
    lei_to_id = {l: f"lei:{l}" for l in in_scope}
    for c, l in cik_lei.items():
        lei_to_id[l] = f"cik:{c}"
    parents = defaultdict(dict)
    for r in rr.itertuples(index=False):
        parents[r[0]][CONS[r[4]]] = r[2]  # child LEI -> {direct|ultimate: parent LEI}

    def gleif_fields(l):
        x = g.loc[l]
        code = x["Entity.LegalForm.EntityLegalFormCode"]
        lf = elf.get(code, "") if code not in ("8888", "9999", "") else x["Entity.LegalForm.OtherLegalForm"]
        reg = x["Entity.HeadquartersAddress.Region"]
        hq_state = reg[3:] if x["Entity.HeadquartersAddress.Country"] == "US" and reg.startswith("US-") else ""
        ra, rid = x["Entity.RegistrationAuthority.RegistrationAuthorityID"], x["Entity.RegistrationAuthority.RegistrationAuthorityEntityID"]
        jur = x["Entity.LegalJurisdiction"]
        return {
            "name": x["Entity.LegalName"], "legal_form": lf, "legal_form_code": code, "jurisdiction": jur,
            "state_of_incorporation": jur[3:] if jur.startswith("US-") else "",
            "hq_address": j(x["Entity.HeadquartersAddress.FirstAddressLine"], x["Entity.HeadquartersAddress.AdditionalAddressLine.1"],
                            x["Entity.HeadquartersAddress.AdditionalAddressLine.2"], x["Entity.HeadquartersAddress.AdditionalAddressLine.3"],
                            x["Entity.HeadquartersAddress.City"], reg, x["Entity.HeadquartersAddress.PostalCode"],
                            x["Entity.HeadquartersAddress.Country"]),
            "hq_state": hq_state,
            "state_registry_id": f"{ra}:{rid}" if jur.startswith("US") and rid and ra not in ("RA888888", "RA999999") else "",
            "gleif_category": x["Entity.EntityCategory"], "entity_status": x["Entity.EntityStatus"],
            "lei_registration_status": x["Registration.RegistrationStatus"],
            "type": ("nonprofit" if NONPROFIT.search(lf or "") else
                     "company" if x["Entity.EntityCategory"] in ("GENERAL", "BRANCH", "SOLE_PROPRIETOR") else "other"),
        }

    def rel_ids(l):
        p = parents.get(l, {})
        return (lei_to_id.get(p.get("direct", ""), ""), lei_to_id.get(p.get("ultimate", ""), ""))

    rows = []
    done_leis = set()
    for c in sorted(tick):
        s = sec.get(c)
        l = cik_lei.get(c, "")
        r = {k: "" for k in COLS}
        r.update(entity_id=f"cik:{c}", cik=str(c), lei=l,
                 ticker=";".join(t for t, _ in tick[c]),
                 exchange=";".join(sorted({e for _, e in tick[c] if e})))
        src, urls = [], []
        if s:
            b = (s.get("addresses") or {}).get("business") or {}
            st = (b.get("stateOrCountry") or "").upper()
            inc = (s.get("stateOfIncorporation") or "").upper()
            r.update(name=s.get("name") or "", sic=s.get("sic") or "", sec_entity_type=s.get("entityType") or "",
                     state_of_incorporation=inc, jurisdiction=f"US-{inc}" if inc in US else "",
                     hq_address=j(b.get("street1"), b.get("street2"), b.get("city"),
                                  b.get("stateOrCountryDescription") or st, b.get("zipCode")),
                     hq_state=st if st in US and not b.get("isForeignLocation") else "",
                     type="company" if s.get("entityType") == "operating" else "other")
            if inc and inc not in US:
                flags[c].append(f"sec_foreign_incorporation_code:{inc}")
            src.append(SEC_SRC); urls.append(s["_source_url"]); date = s["_retrieved_at"]
        else:
            name = next((v for v in tx["data"] if int(v[0]) == c), [None, ""])[1]
            r.update(name=name)
            src.append(SEC_LIST); urls.append(sec_list_meta["url"]); date = sec_list_meta["retrieved_at"]
            flags[c].append("no_submissions_record")
        if l:
            gf = gleif_fields(l)
            for k, v in gf.items():  # SEC wins where it has a value
                if not r.get(k) or k in ("legal_form", "legal_form_code", "state_registry_id", "gleif_category",
                                         "entity_status", "lei_registration_status"):
                    r[k] = v
            if NONPROFIT.search(gf["legal_form"] or ""):
                if r["type"] == "company":  # SEC operating issuer with a ticker: keep SEC, flag the conflict
                    flags[c].append("gleif_legal_form_nonprofit_vs_sec_operating")
                else:
                    r["type"] = "nonprofit"
            if gf["jurisdiction"] and r["jurisdiction"] and gf["jurisdiction"] != r["jurisdiction"]:
                flags[c].append(f"jurisdiction_sec_vs_gleif:{r['jurisdiction']}|{gf['jurisdiction']}")
            r["parent_id"], r["ultimate_parent_id"] = rel_ids(l)
            src.append(GLEIF_L1); urls.append(f"https://api.gleif.org/api/v1/lei-records/{l}")
            if parents.get(l):
                src.append(GLEIF_L2)
            r["cik_lei_link"] = cik_lei_src[c]
            if cik_lei_src[c] == "wikidata":
                src.append(WD_SRC)
            done_leis.add(l)
            date = max(date, gdate)
        q = set(wd_cik_qid.get(c, set())) | (wd_lei_qid.get(l, set()) if l else set())
        if q:
            r["wikidata_qid"] = ";".join(sorted(q))
            if len(q) > 1:
                flags[c].append("multiple_wikidata_items")
            src.append(WD_SRC); urls.extend(f"https://www.wikidata.org/wiki/{x}" for x in sorted(q))
            date = max(date, wd_date)
        r.update(source=";".join(dict.fromkeys(src)), source_url=";".join(urls), source_date=date,
                 flags=";".join(flags.get(c, [])))
        rows.append(r)

    for l in sorted(in_scope - done_leis):
        r = {k: "" for k in COLS}
        r.update(gleif_fields(l))
        r.update(entity_id=f"lei:{l}", lei=l)
        r["parent_id"], r["ultimate_parent_id"] = rel_ids(l)
        src, urls, date = [GLEIF_L1], [f"https://api.gleif.org/api/v1/lei-records/{l}"], gdate
        if parents.get(l):
            src.append(GLEIF_L2)
        q = wd_lei_qid.get(l)
        if q:
            r["wikidata_qid"] = ";".join(sorted(q))
            src.append(WD_SRC); urls.extend(f"https://www.wikidata.org/wiki/{x}" for x in sorted(q))
            date = max(date, wd_date)
        r.update(source=";".join(src), source_url=";".join(urls), source_date=date)
        rows.append(r)

    out = pd.DataFrame(rows, columns=COLS)
    assert out.entity_id.is_unique
    assert (out.source_url != "").all() and (out.source_date != "").all()
    known = set(out.entity_id)
    assert set(out.parent_id[out.parent_id != ""]) <= known and set(out.ultimate_parent_id[out.ultimate_parent_id != ""]) <= known

    rels = []
    for _, x in rr.iterrows():
        ch, pa = x["Relationship.StartNode.NodeID"], x["Relationship.EndNode.NodeID"]
        if ch not in lei_to_id or pa not in lei_to_id:
            continue
        start = ""
        for k in range(1, 6):
            if x.get(f"Relationship.Period.{k}.periodType") == "RELATIONSHIP_PERIOD":
                start = x[f"Relationship.Period.{k}.startDate"][:10]
        acct = j(*[x.get(f"Relationship.Qualifiers.{k}.QualifierCategory", "") for k in range(1, 6)], sep=";")
        rels.append({"child_id": lei_to_id[ch], "parent_id": lei_to_id[pa],
                     "relationship": CONS[x["Relationship.RelationshipType"]] + "_parent", "child_lei": ch, "parent_lei": pa,
                     "start_date": start, "relationship_status": x["Relationship.RelationshipStatus"],
                     "registration_status": x["Registration.RegistrationStatus"], "accounting_standard": acct,
                     "source": GLEIF_L2, "source_url": f"https://api.gleif.org/api/v1/lei-records/{ch}/direct-parent-relationship"
                     if CONS[x["Relationship.RelationshipType"]] == "direct" else
                     f"https://api.gleif.org/api/v1/lei-records/{ch}/ultimate-parent-relationship",
                     "source_date": gdate})
    rel = pd.DataFrame(rels, columns=RCOLS).sort_values(["child_id", "relationship"])
    GZ = {"method": "gzip", "mtime": 0, "compresslevel": 9}  # deterministic gzip
    out.to_csv(ROOT / "companies.csv.gz", index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n", compression=GZ)
    rel.to_csv(ROOT / "relationships.csv.gz", index=False, lineterminator="\n", compression=GZ)
    summ = {
        "companies_rows": len(out), "companies_from_sec": int(out.entity_id.str.startswith("cik:").sum()),
        "companies_gleif_only": int(out.entity_id.str.startswith("lei:").sum()),
        "sec_with_lei": int(((out.cik != "") & (out.lei != "")).sum()),
        "sec_lei_via_sec_field": sum(1 for c in cik_lei if cik_lei_src[c] == "sec"),
        "sec_lei_via_wikidata": sum(1 for c in cik_lei if cik_lei_src[c] == "wikidata"),
        "with_wikidata_qid": int((out.wikidata_qid != "").sum()),
        "with_parent": int((out.parent_id != "").sum()), "with_ultimate_parent": int((out.ultimate_parent_id != "").sum()),
        "relationships_rows": len(rel), "relationships_by_type": rel.relationship.value_counts().to_dict(),
        "type_counts": out["type"].value_counts().to_dict(), "flagged_rows": int((out["flags"] != "").sum()),
        "sec_ticker_ciks_without_submissions": len(missing_sub),
        "gleif_publish": gm["publish_date"], "sec_retrieved_at": sec_list_meta["retrieved_at"], "wikidata_retrieved_at": wd_date,
    }
    (ROOT / "summary.json").write_text(json.dumps(summ, indent=1) + "\n")
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
