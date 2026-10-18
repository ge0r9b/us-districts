#!/usr/bin/env python3
"""Fetch the Statistics Canada 2021 Census cartographic boundary files (CBF) from StatCan's official ArcGIS REST service
(geo.statcan.gc.ca/geo_wa/rest/services/2021/Cartographic_boundary_files/MapServer; the same data as the lxxx000b21a_e.zip
downloads, whose www12 host serves a browser security check to scripts). Statistics Canada Open Licence.
Layers: 0 PR, 4 CD, 9 CSD, 3 FED (2013 Representation Order). Geometry is requested in the native NAD83 / Statistics Canada
Lambert (EPSG:3347) without generalization (no maxAllowableOffset), in Esri JSON, by OBJECTID batches.
Output: <out>/<layer>.jsonl.gz, one Esri feature per line, sorted by OBJECTID (gzip mtime 0).
usage: statcan2021_fetch.py <out_dir> [PR CD CSD FED; NAME:attr = attributes only, to <NAME>_attr.jsonl.gz]
Then statcan2021_fetch.py <out_dir> --gen10 CSD for the features the service could not return.
The build uses CSD and FED geometry and PR:attr CD:attr (PR and CD are dissolved from the CSDs)."""
import sys, os, json, gzip, time, urllib.request, urllib.parse
B = "https://geo.statcan.gc.ca/geo_wa/rest/services/2021/Cartographic_boundary_files/MapServer"
L = {"PR": (0, 1), "CD": (4, 4), "CSD": (9, 25), "FED": (3, 4)}
def get(url, tries=6):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "us-districts geo build"}), timeout=300) as r:
                d = json.loads(r.read())
            if "error" in d: raise ValueError(d["error"])
            return d
        except Exception as e:
            print("  retry", k, str(e)[:60], flush=True); time.sleep(1 + 2 * k)
    return None
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
if sys.argv[2:3] == ["--gen10"]:
    # Features in <NAME>_failed.json that the service cannot return at full resolution, requested again with server-side
    # generalization maxAllowableOffset=10 m (CSD 6204030 Qikiqtaaluk, Unorganized: 124,000 km of coastline) ->
    # <NAME>_gen10.jsonl.gz (each feature first retried at full resolution;
    # generalized_m = 0 or 10). 10 m is a fifth of the 50 m output tolerance.
    for name in sys.argv[3:]:
        lid = L[name][0]; got = []
        for f in json.load(open(os.path.join(out, name + "_failed.json"))):
            o = f["attributes"]["OBJECTID"]
            for off in ("", "10"):  # first full resolution again (failures are partly random), then 10 m
                q = {"objectIds": o, "outFields": "*", "returnGeometry": "true", "outSR": "3347", "geometryPrecision": "3", "f": "json"}
                if off: q["maxAllowableOffset"] = off
                d = get("%s/%d/query?%s" % (B, lid, urllib.parse.urlencode(q)), tries=12)
                if d and d["features"]:
                    for f in d["features"]: f["generalized_m"] = int(off or 0)
                    got += d["features"]; print(name, o, "ok, generalized_m", off or 0, flush=True); break
            else: print(name, o, "still failing", flush=True)
        with gzip.GzipFile(os.path.join(out, name + "_gen10.jsonl.gz"), "wb", mtime=0) as g:
            for f in got: g.write((json.dumps(f, separators=(",", ":"), ensure_ascii=False, sort_keys=True) + "\n").encode())
    sys.exit()
for arg in (sys.argv[2:] or list(L)):
    name, attr = arg.split(":")[0], arg.endswith(":attr"); lid, n = L[name]
    if attr: n = 1000
    ids = sorted(get("%s/%d/query?where=1%%3D1&returnIdsOnly=true&f=json" % (B, lid))["objectIds"])
    feats = []; failed = []
    def fetch(batch):  # a batch the server cannot answer (HTTP 500 on very large responses) is split in halves
        q = urllib.parse.urlencode({"objectIds": ",".join(map(str, batch)), "outFields": "*", "returnGeometry": "false" if attr else "true",
                                    "outSR": "3347", "geometryPrecision": "3", "f": "json"})
        d = get("%s/%d/query?%s" % (B, lid, q))
        if d is None and len(batch) > 1:
            return fetch(batch[:len(batch) // 2]) + fetch(batch[len(batch) // 2:])
        if d is None: d = get("%s/%d/query?%s" % (B, lid, q), tries=10)  # one feature: keep retrying (the service fails at random)
        if d is None:  # the service cannot return this feature at all (e.g. FED 62001 Nunavut, 190,000 km of coast)
            failed.append(batch[0]); print("  FAILED", name, batch, flush=True); return []
        if d.get("exceededTransferLimit"): raise SystemExit("transfer limit at %s" % batch)
        return d["features"]
    for i in range(0, len(ids), n):
        feats += fetch(ids[i:i + n])
        if i // n % 20 == 0: print(name, len(feats), "/", len(ids), flush=True)
    assert len(feats) + len(failed) == len(ids), (name, len(feats), len(ids))
    if failed:  # record the attributes of features the service could not return with geometry
        q = urllib.parse.urlencode({"objectIds": ",".join(map(str, failed)), "outFields": "*", "returnGeometry": "false", "f": "json"})
        json.dump(get("%s/%d/query?%s" % (B, lid, q), tries=20)["features"], open(os.path.join(out, name + "_failed.json"), "w"))
    feats.sort(key=lambda f: f["attributes"]["OBJECTID"])
    with gzip.GzipFile(os.path.join(out, name + ("_attr" if attr else "") + ".jsonl.gz"), "wb", mtime=0) as g:
        for f in feats: g.write((json.dumps(f, separators=(",", ":"), ensure_ascii=False, sort_keys=True) + "\n").encode())
    print(name, "done", len(feats), flush=True)
