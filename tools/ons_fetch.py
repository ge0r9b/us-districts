#!/usr/bin/env python3
"""Fetch ONS Open Geography Portal boundary layers (Open Government Licence v3.0) from ONS's ArcGIS Online feature services
(services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/<service>/FeatureServer/<layer>), in British National Grid
(EPSG:27700), full resolution (no maxAllowableOffset, geometryPrecision 3 = mm), Esri JSON, by object-id batches.
Output: <out>/<NAME>.jsonl.gz, one Esri feature per line sorted by the GSS code (gzip mtime 0), and <out>/<NAME>.meta.json
(service name, layer item description fields, record count, fetch date). A finished layer is skipped on rerun (resumable).
usage: ons_fetch.py <out_dir> [LAD CTYUA CAUTH PAR]"""
import sys, os, json, gzip, time, urllib.request, urllib.parse
B = "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services"
L = {"LAD": ("Local_Authority_Districts_May_2026_Boundaries_UK_BFC", 0, "LAD26CD", 4),
     "CTYUA": ("Counties_and_Unitary_Authorities_December_2025_Boundaries_UK_BFC", 0, "CTYUA25CD", 4),
     "CAUTH": ("Combined_Authorities_December_2025_Boundaries_EN_BFC", 1, "CAUTH25CD", 2),
     "PAR": ("PARNCP_MAY_2026_EW_BFC", 0, "PARNCP26CD", 50)}
def get(url, data=None, tries=8):
    for k in range(tries):
        try:
            rq = urllib.request.Request(url, data=data, headers={"User-Agent": "us-districts geo build"})
            with urllib.request.urlopen(rq, timeout=600) as r: d = json.loads(r.read())
            if "error" in d: raise ValueError(d["error"])
            return d
        except Exception as e:
            print("  retry", k, str(e)[:80], flush=True); time.sleep(2 + 3 * k)
    return None
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
for name in (sys.argv[2:] or list(L)):
    svc, lid, key, n = L[name]; p = os.path.join(out, name + ".jsonl.gz")
    if os.path.exists(p): print(name, "exists, skipped"); continue
    U = "%s/%s/FeatureServer/%d" % (B, svc, lid); info = get(U + "?f=json")
    ids = sorted(get(U + "/query?where=1%3D1&returnIdsOnly=true&f=json")["objectIds"]); feats = []
    def fetch(batch):
        q = urllib.parse.urlencode({"objectIds": ",".join(map(str, batch)), "outFields": "*", "returnGeometry": "true",
                                    "outSR": "27700", "geometryPrecision": "3", "f": "json"}).encode()
        d = get(U + "/query", data=q)
        if d is None and len(batch) > 1: return fetch(batch[:len(batch) // 2]) + fetch(batch[len(batch) // 2:])
        if d is None: raise SystemExit("cannot fetch %s %s" % (name, batch))
        if d.get("exceededTransferLimit"):
            if len(batch) == 1: raise SystemExit("transfer limit on one feature %s" % batch)
            return fetch(batch[:len(batch) // 2]) + fetch(batch[len(batch) // 2:])
        return d["features"]
    for i in range(0, len(ids), n):
        feats += fetch(ids[i:i + n])
        if i // n % 20 == 0: print(name, len(feats), "/", len(ids), flush=True)
    assert len(feats) == len(ids), (name, len(feats), len(ids))
    feats.sort(key=lambda f: f["attributes"][key])
    with gzip.GzipFile(p + ".tmp", "wb", mtime=0) as g:
        for f in feats: g.write((json.dumps(f, separators=(",", ":"), ensure_ascii=False, sort_keys=True) + "\n").encode())
    os.replace(p + ".tmp", p)
    json.dump({"service": svc, "layer": lid, "layer_name": info.get("name"), "key": key, "count": len(feats),
               "copyright": info.get("copyrightText"), "fetched": time.strftime("%Y-%m-%d")}, open(os.path.join(out, name + ".meta.json"), "w"), indent=1)
    print(name, "done", len(feats), flush=True)
