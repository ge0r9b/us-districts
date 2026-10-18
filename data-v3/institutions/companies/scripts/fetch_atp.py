"""Download All The Places (CC0) spider outputs for the latest completed run.

https://data.alltheplaces.xyz/runs/latest.json -> run_id;
https://alltheplaces-data.openaddresses.io/runs/<run_id>/output/<spider>.geojson
Writes raw/atp/<spider>.geojson and raw/atp.meta.json (run id, URLs, retrieval date).
Usage: python fetch_atp.py mcdonalds marriott_hotels ritz_carlton starbucks_us ...  (adds to raw/atp.meta.json for the same run)
"""
import json
import sys

from common import RAW, get, read_meta, today, write_meta


def main(spiders):
    run = get("https://data.alltheplaces.xyz/runs/latest.json").json()
    rid = run["run_id"]
    d = RAW / "atp"
    d.mkdir(parents=True, exist_ok=True)
    meta = read_meta("atp")  # keep entries for spiders fetched earlier from the same run
    if meta.get("run_id") != rid:
        meta = {"run_id": rid, "run_end_time": run.get("end_time"), "retrieved_at": today(), "spiders": {}}
    for s in spiders:
        url = f"https://alltheplaces-data.openaddresses.io/runs/{rid}/output/{s}.geojson"
        r = get(url)
        r.raise_for_status()
        (d / f"{s}.geojson").write_bytes(r.content)
        n = len(json.loads(r.content)["features"]) if r.content.strip() else 0  # an empty file = spider found nothing
        meta["spiders"][s] = {"url": url, "features": n, "retrieved_at": today()}
        print(s, n, file=sys.stderr)
    write_meta("atp", meta)


if __name__ == "__main__":
    main(sys.argv[1:])
