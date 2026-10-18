"""Download All The Places (CC0) spider outputs from an OLDER completed run.

Used only when a spider's latest-run output is empty or clearly partial (see SCHEMA.md per-brand notes).
https://alltheplaces-data.openaddresses.io/runs/<run_id>/output/<spider>.geojson
Writes raw/atp_runs/<run_id>/<spider>.geojson and records it in raw/atp_older.meta.json.
Usage: python fetch_atp_older.py <run_id> <spider> [<spider> ...]
"""
import json
import sys

from common import RAW, get, read_meta, today, write_meta


def main(rid, spiders):
    d = RAW / "atp_runs" / rid
    d.mkdir(parents=True, exist_ok=True)
    meta = read_meta("atp_older") or {"runs": {}}
    for s in spiders:
        url = f"https://alltheplaces-data.openaddresses.io/runs/{rid}/output/{s}.geojson"
        r = get(url)
        r.raise_for_status()
        (d / f"{s}.geojson").write_bytes(r.content)
        n = len(json.loads(r.content)["features"]) if r.content.strip() else 0
        meta["runs"].setdefault(rid, {})[s] = {"url": url, "features": n, "retrieved_at": today()}
        print(rid, s, n, file=sys.stderr)
    write_meta("atp_older", meta)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
