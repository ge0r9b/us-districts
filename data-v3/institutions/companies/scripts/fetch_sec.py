"""Fetch the SEC EDGAR company list and per-CIK submissions metadata.

Sources (public, U.S. government work):
  https://www.sec.gov/files/company_tickers.json           every CIK with a current ticker
  https://www.sec.gov/files/company_tickers_exchange.json  same, with exchange
  https://data.sec.gov/submissions/CIK##########.json      name, entityType, SIC, state of
                                                           incorporation, business address, filings
Raw files land in raw/sec/ (gitignored). Re-running skips CIKs already cached unless --refresh.
Rate limit: 8 requests/second (SEC allows 10).
Usage: python fetch_sec.py [--limit N] [--refresh]
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor

from common import RAW, gz_json_dump, get, today, write_meta

LISTS = {
    "company_tickers": "https://www.sec.gov/files/company_tickers.json",
    "company_tickers_exchange": "https://www.sec.gov/files/company_tickers_exchange.json",
}
SUB_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    d = RAW / "sec"
    sub = d / "submissions"
    sub.mkdir(parents=True, exist_ok=True)

    for name, url in LISTS.items():
        r = get(url, 0.125)
        r.raise_for_status()
        (d / f"{name}.json").write_bytes(r.content)
        write_meta(f"sec_{name}", {"url": url, "retrieved_at": today(), "bytes": len(r.content)})

    tick = json.loads((d / "company_tickers.json").read_text())
    ciks = sorted({int(v["cik_str"]) for v in tick.values()})
    if a.limit:
        ciks = ciks[: a.limit]
    print(f"{len(ciks)} unique CIKs", file=sys.stderr)
    todo = [c for c in ciks if a.refresh or not (sub / f"CIK{c:010d}.json.gz").exists()]
    print(f"{len(todo)} to fetch", file=sys.stderr)

    def one(cik):
        out = sub / f"CIK{cik:010d}.json.gz"
        url = SUB_URL.format(cik=cik)
        r = get(url, 0.125)  # <= 8 req/s overall, shared across threads
        if r.status_code == 404:
            return 0
        r.raise_for_status()
        j = r.json()
        # keep only the latest annual-report rows of the filings table (for Exhibit 21 later)
        rec = j.get("filings", {}).get("recent", {})
        keep = {}
        if rec:
            idx = [k for k, f in enumerate(rec.get("form", [])) if f in ("10-K", "10-K/A", "20-F", "40-F")][:3]
            keep = {col: [vals[k] for k in idx] for col, vals in rec.items()}
        j["filings"] = {"annual_recent": keep}
        j["_retrieved_at"] = today()
        j["_source_url"] = url
        gz_json_dump(out, j)
        return 1

    got = miss = 0
    with ThreadPoolExecutor(6) as ex:
        for i, ok in enumerate(ex.map(one, todo)):
            got += ok
            miss += 1 - ok
            if i % 500 == 0:
                print(f"  {i}/{len(todo)}", file=sys.stderr)
    write_meta("sec_submissions", {"url_pattern": SUB_URL, "retrieved_at": today(), "fetched": got, "missing": miss})
    print(f"fetched {got}, 404 {miss}", file=sys.stderr)


if __name__ == "__main__":
    main()
