"""Download the GLEIF Golden Copy (LEI-CDF level 1 + RR-CDF level 2 relationship records).

Source: GLEIF Golden Copy, https://www.gleif.org/en/lei-data/gleif-golden-copy (CC0 1.0).
Publish metadata: https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest
Writes raw/gleif/{lei2,rr,repex}.csv.zip (gitignored) and raw/gleif.meta.json with the exact file URLs
and publish timestamp, which build.py uses as source_url / source_date.
"""
import sys

from common import RAW, get, today, write_meta

API = "https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest"


def main():
    d = RAW / "gleif"
    d.mkdir(parents=True, exist_ok=True)
    pub = get(API).json()["data"]
    meta = {"api": API, "publish_date": pub["publish_date"], "retrieved_at": today(), "files": {}}
    for kind in ("lei2", "rr", "repex"):
        f = pub[kind]["full_file"]["csv"]
        out = d / f"{kind}.csv.zip"
        print(f"{kind}: {f['size_human_readable']} {f['url']}", file=sys.stderr)
        if out.exists() and out.stat().st_size == f["size"]:
            print("  cached", file=sys.stderr)
        else:
          with get(f["url"], stream=True) as r:
            r.raise_for_status()
            with open(out, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
        meta["files"][kind] = {"url": f["url"], "record_count": f["record_count"],
                               "publish_date": pub[kind]["publish_date"], "cdf_version": f.get("cdf_version")}
    write_meta("gleif", meta)


if __name__ == "__main__":
    main()
