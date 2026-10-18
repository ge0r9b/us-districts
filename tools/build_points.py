#!/usr/bin/env python3
"""Star points for the state-silhouette icon beside every v2 geo-list row.

Writes v2/data/points/<State>.js (State file name as in STATE_FILES, e.g. New-Hampshire.js; DC -> District-of-Columbia.js):
  __points("State",{county:{...},town:{...},place:{...},sch:{...},cd:{...},sldu:{...},sldl:{...}});
each entry  key: [lon, lat]  (WGS84 degrees, same space as the icon code's star argument: window.__stSil(st,[lon,lat])
projects it with the silhouette's own projection, so no icon-relative x/y is needed).

Keys = the exact row keys the app uses (KEYFN without the leading "State|"):
  county  NAT row name (v2/data/uscounties.js, e.g. "Union County")            [also checked against __geo counties]
  town    "County|Name" for every v2/data/parts/<State>.js row and every __geo towns row (the townsIn() sources);
          a name TIGER uses twice in one county already carries " (<GEOID>)" in the row name (Ohio, Union County,
          "Washington township (3915981242)"), so keys are unique and equal the row
  place   row name of v2/data/places/<State>.js and __geo places
  sch     school district row name (__geo schools and v2/data/ussch.js)
  cd      US House row code ("01", "00" at large) (__geo ushouse and uscd.js)
  sldu    state senate row code (__geo senate and ussldu.js)
  sldl    state house row code (__geo statehouse and ussldl.js)
  DC: dc.js rows (county "District of Columbia", cd "00", sch DCPS, sldu/sldl "Ward 1".."Ward 8"); no towns/places.

Point rule (guaranteed inside): every shape the app holds for that row (state-file shape and national-file shape) is
decoded; the point must lie strictly inside all of them (shapely, holes respected).
  1. Census TIGER 2024 Gazetteer INTPTLAT/INTPTLONG of the matching feature, if inside all shapes after rounding;
  2. else polylabel (pole of inaccessibility) of the intersection of the shapes (largest polygon part);
  3. if the shapes do not overlap, polylabel of the primary shape (reported).
Rounding: 3 decimals (a state whose file would exceed 60 KB at gzip level 6 is redone trying 2 decimals first, used
where the 2-decimal point is still inside every shape: ~1 km, far below one pixel of the 30x22 icon); if the 3-decimal point falls outside (very small or thin shapes) the nearest inside point of the
0.001 grid around it is used, else 4, then 5 decimals (counted in the report).
TIGER matching: counties by name; towns/places through data-v3 towns_2024/places_2024 GeoJSON (v2_parts / v2_places ->
GEOID); school districts by name (unified, elementary, secondary); CD and SLD by GEOID district code == row code.
usage: build_points.py <repo> <gaz_dir[,gaz_dir2]> <v3_raw_dir> [--report OUT.json] [--only State,...]
"""
import sys, os, json, re, gzip, collections, argparse
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import polylabel, unary_union
from shapely.validation import make_valid
from shapely.prepared import prep

ap = argparse.ArgumentParser()
ap.add_argument("repo"); ap.add_argument("gaz"); ap.add_argument("v3raw")
ap.add_argument("--report"); ap.add_argument("--only")
a = ap.parse_args()
D = os.path.join(a.repo, "v2", "data")

def jscall(path, name):
    s = open(path, encoding="utf-8").read()
    i = s.index(name + "(") + len(name) + 1
    j = s.rindex(")")
    return json.loads("[" + s[i:j] + "]")

def dec(enc, scale):
    polys = []
    for rings in enc:
        rr = []
        for f in rings:
            x = y = 0; out = []
            for k in range(0, len(f), 2):
                x += f[k]; y += f[k + 1]; out.append((x / scale, y / scale))
            if len(out) >= 3: rr.append(out)
        if rr: polys.append(rr)
    return polys

class G:
    """shapely geometry + the raw decoded rings (the app tests points with an even-odd ray cast on those)"""
    __slots__ = ("g", "raw")
    def __init__(self, g, raw): self.g = g; self.raw = raw

def inring(r, x, y):
    c = False; j = len(r) - 1
    for i in range(len(r)):
        xi, yi = r[i]; xj, yj = r[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: c = not c
        j = i
    return c

def rawin(raw, x, y): return any(inring(p[0], x, y) and not any(inring(h, x, y) for h in p[1:]) for p in raw)

def geom(polys):
    g = geom0(polys)
    return G(g, polys) if g is not None and g.area > 0 else None

def geom0(polys):
    ps = []
    for rr in polys:
        p = Polygon(rr[0], rr[1:])
        if not p.is_valid: p = make_valid(p)
        ps.append(p)
    g = unary_union(ps) if len(ps) > 1 else ps[0]
    if not g.is_valid: g = make_valid(g)
    return polyonly(g)

def polyonly(g):
    if g is None or g.is_empty: return None
    if g.geom_type in ("Polygon", "MultiPolygon"): return g
    parts = [x for x in getattr(g, "geoms", []) if x.geom_type in ("Polygon", "MultiPolygon")]
    return unary_union(parts) if parts else None

# ---------- TIGER gazetteers ----------
def gaz(fn):
    p = next(os.path.join(d, fn) for d in a.gaz.split(",") if os.path.exists(os.path.join(d, fn)))
    rows = []
    with open(p, encoding="utf-8", errors="replace") as f:
        hdr = [h.strip() for h in f.readline().split("\t")]
        for line in f:
            v = [x.strip() for x in line.split("\t")]
            rows.append(dict(zip(hdr, v)))
    return rows
def ll(r): return (float(r["INTPTLONG"]), float(r["INTPTLAT"]))
GZ = {k: gaz(f) for k, f in [("county", "2024_Gaz_counties_national.txt"), ("cousub", "2024_Gaz_cousubs_national.txt"),
      ("place", "2024_Gaz_place_national.txt"), ("unsd", "2024_Gaz_unsd_national.txt"), ("elsd", "2024_Gaz_elsd_national.txt"),
      ("scsd", "2024_Gaz_scsd_national.txt"), ("cd", "2024_Gaz_119CDs_national.txt"), ("sldu", "2024_Gaz_sldu_national.txt"),
      ("sldl", "2024_Gaz_sldl_national.txt")]}
BYST = {k: collections.defaultdict(list) for k in GZ}
for k in GZ:
    for r in GZ[k]: BYST[k][r["USPS"]].append(r)
BYGEOID = {}
for k in ("cousub", "place"):
    for r in GZ[k]: BYGEOID[r["GEOID"]] = ll(r)

FIPS = {}
ABBR = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO","Connecticut":"CT","Delaware":"DE",
"District of Columbia":"DC","Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS",
"Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS",
"Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY",
"North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI",
"South Carolina":"SC","South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA","Washington":"WA",
"West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY"}

# v3 GeoJSON: v2 row key -> GEOID
TOWNGEO = {}; PLACEGEO = {}
def v3feat(fn):
    with gzip.open(os.path.join(a.v3raw, fn), "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip().rstrip(",")
            if not line.startswith('{"type":"Feature"'): continue
            m = re.search(r'"properties":(\{.*?\}),"geometry"', line)
            yield json.loads(m.group(1))
for p in v3feat("towns_2024.geojson.gz"):
    for k in p.get("v2_parts") or []: TOWNGEO.setdefault((p["state"], k), p["geoid"])
for p in v3feat("places_2024.geojson.gz"):
    for k in p.get("v2_parts") or []: TOWNGEO.setdefault((p["state"], k), p["geoid"])
    if p.get("v2_places"): PLACEGEO.setdefault((p["state"], p["v2_places"]), p["geoid"])

GZBYGEOID = {}
for z in GZ:
    for r in GZ[z]: GZBYGEOID.setdefault((z, r["GEOID"]), r)
def intpt(st, layer, key):
    ab = ABBR[st]
    if re.fullmatch(r"\d{7,10}", key):   # GEOID key of a duplicate v1 row
        for z in ("unsd", "elsd", "scsd", "place", "cousub"):
            if (z, key) in GZBYGEOID: return ll(GZBYGEOID[(z, key)])
    if layer == "county":
        for r in BYST["county"][ab]:
            if r["NAME"] == key: return ll(r)
    elif layer == "town":
        g = TOWNGEO.get((st, key)); return BYGEOID.get(g) if g else None
    elif layer == "place":
        g = PLACEGEO.get((st, key)); return BYGEOID.get(g) if g else None
    elif layer == "sch":
        base = re.sub(r" \([^)]*\)$", "", key)
        hits = [r for k in ("unsd", "elsd", "scsd") for r in BYST[k][ab] if r["NAME"] == key]
        if not hits and base != key: hits = [r for k in ("unsd", "elsd", "scsd") for r in BYST[k][ab] if r["NAME"] == base]
        if len(hits) == 1: return ll(hits[0])
        return [ll(h) for h in hits] or None   # several candidates: the inside test picks
    elif layer in ("cd", "sldu", "sldl"):
        hits = [r for r in BYST[layer][ab] if r["GEOID"][2:] == key]
        if len(hits) == 1: return ll(hits[0])
    return None

# ---------- v2 rows and shapes ----------
NATK = {"county": ("uscounties.js", "window.__uscty", None), "sch": ("ussch.js", "window.__usdist", "schools"),
        "cd": ("uscd.js", "window.__uscd", None), "sldu": ("ussldu.js", "window.__usdist", "senate"),
        "sldl": ("ussldl.js", "window.__usdist", "statehouse")}
NAT = collections.defaultdict(lambda: collections.defaultdict(dict))   # NAT[st][layer][key] = enc (1e3)
for layer, (fn, call, _) in NATK.items():
    v = jscall(os.path.join(D, fn), call)
    rows = v[-1]
    for r in rows: NAT[r[0]][layer][r[1]] = r[2]
# dc.js replaces the DC rows of the national files
dcs = open(os.path.join(D, "dc.js"), encoding="utf-8").read()
mW = re.search(r"var W=(.*?),A=0,P=(.*?),A24=", dcs, re.S)
W = json.loads(mW.group(1)); P = json.loads(mW.group(2))
DC = "District of Columbia"
NAT[DC] = collections.defaultdict(dict)
NAT[DC]["county"][DC] = P; NAT[DC]["cd"]["00"] = P; NAT[DC]["sch"]["District of Columbia Public Schools"] = P
for r in W: NAT[DC]["sldu"][r[1]] = r[2]; NAT[DC]["sldl"][r[1]] = r[2]

GEOL = {"counties": "county", "schools": "sch", "ushouse": "cd", "senate": "sldu", "statehouse": "sldl", "places": "place"}

def round_inside(pt, gs, nd):
    q = 10 ** -nd
    x, y = round(pt[0], nd), round(pt[1], nd)
    def ok(X, Y):
        P = Point(X, Y)   # inside (shapely, holes respected), off the boundary, and inside by the app's ray cast too
        return all(g.g.contains(P) and g.g.boundary.distance(P) > 1e-7 and rawin(g.raw, X, Y) for g in gs)
    if ok(x, y): return (x, y)
    best = None
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            X, Y = round(x + dx * q, nd), round(y + dy * q, nd)
            if ok(X, Y):
                d = (X - pt[0]) ** 2 + (Y - pt[1]) ** 2
                if best is None or d < best[0]: best = (d, X, Y)
    return (best[1], best[2]) if best else None

def biggest(g):
    return max(g.geoms, key=lambda p: p.area) if g.geom_type == "MultiPolygon" else g

NDS = (3, 4, 5)
def pick(st, layer, key, shapes):
    """shapes: list of (label, shapely geom); first = primary. returns (pt, method, ndec, note)"""
    gs = [g for _, g in shapes if g is not None]
    if not gs: return None, "noshape", 0, "no interior: every shape of the row is missing or has zero area (a degenerate sliver of a place clipped to this county), so no point can lie inside it"
    cands = []
    ip = intpt(st, layer, key)
    if ip:
        for c in (ip if isinstance(ip, list) else [ip]): cands.append(("intpt", c, gs))
    inter = gs[0].g
    for g in gs[1:]:
        inter = polyonly(inter.intersection(g.g))
        if inter is None: break
    if inter is not None and not inter.is_empty:
        pl = polylabel(biggest(inter), tolerance=1e-5)
        cands.append(("polylabel", (pl.x, pl.y), gs))
    else:
        pl = polylabel(biggest(gs[0].g), tolerance=1e-5)
        cands.append(("polylabel-primary", (pl.x, pl.y), gs[:1]))
    for nd in NDS:
        for meth, c, use in cands:
            r = round_inside(c, use, nd)
            if r: return r, meth, nd, ("inside primary shape only (shapes do not overlap)" if meth == "polylabel-primary" else "")
    return None, "fail", 0, "no inside point found at 5 decimals"

def statefile(st): return st.replace(" ", "-") + ".js"

states = sorted(ABBR)
if a.only: states = [s for s in states if s in a.only.split(",")]
REPORT = {}
for st in states:
    fn = statefile(st)
    rows = collections.defaultdict(lambda: collections.defaultdict(list))  # rows[layer][key] = [(label, geom)]
    # national files (1e3)
    for layer, d in NAT[st].items():
        for k, enc in d.items(): rows[layer][k].append(("nat", geom(dec(enc, 1000))))
    if st != DC:
        g = jscall(os.path.join(D, "states", fn), "__geo")[1]
        for L, items in g.items():
            if L == "towns":
                for it in items: rows["town"][it[1] + "|" + it[2]].append(("geo", geom(dec(it[-1], 10000))))
            elif L in GEOL:
                for it in items: rows[GEOL[L]][it[1]].append(("geo", geom(dec(it[-1], 10000))))
        pl = jscall(os.path.join(D, "places", fn), "__places")[1]
        placegeom = {}
        for it in pl:
            gg = geom(dec(it[2], 10000)); placegeom[it[1]] = gg
            rows["place"][it[1]].append(("places", gg))
        geoplaces = {it[1]: it[-1] for it in g.get("places", [])}
        for c, n, enc in jscall(os.path.join(D, "parts", fn), "__parts")[1]:
            if enc: gg = geom(dec(enc, 10000))
            else:   # townsIn(): a parts row without geometry uses the GEOM.places row of that name
                gg = geom(dec(geoplaces[n], 10000)) if n in geoplaces else None
            rows["town"][c + "|" + n].append(("parts", gg))
    # v1 (__geo) rows that share one key (58 school, 11 place, 1 town key nationally): the key keeps the v1 row that
    # overlaps the unique-keyed row of the newer file; every other v1 row of that key gets an extra entry keyed by its
    # TIGER GEOID (the Gazetteer feature of that name whose INTPT lies in the row's shape)
    dups = []
    for layer, R in rows.items():
        for k, lst in R.items():
            geo = [x for x in lst if x[0] == "geo"]
            if len(geo) < 2: continue
            other = [x for x in lst if x[0] != "geo" and x[1] is not None]
            if other:
                keep = [x for x in geo if x[1] is not None and x[1].g.intersection(other[0][1].g).area > 0.5 * min(x[1].g.area, other[0][1].g.area)]
                keep = keep[:1]
            else:
                keep = geo[:1]
            R[k] = other + keep
            for x in geo:
                if x not in keep: dups.append((layer, k, x[1]))
    GZMAX = 60000   # per-state budget, measured at gzip level 6 (level 9 is smaller)
    for NDS in ((3, 4, 5), (2, 3, 4, 5)):
      out = {}; rep = {"rows": {}, "points": {}, "intpt": {}, "polylabel": {}, "dec4plus": {}, "misses": [], "geoid_keys": [], "ndec": list(NDS)}
      GZL = {"sch": ("unsd", "elsd", "scsd"), "place": ("place",), "town": ("cousub", "place")}
      for layer, k, gg in dups:
          nm = k.split("|")[-1]
          hits = [r for z in GZL.get(layer, ()) for r in BYST[z][ABBR[st]] if r["NAME"] == nm and gg is not None and gg.g.contains(Point(ll(r)))]
          if len(hits) != 1:
              rep["misses"].append([layer, k, "second v1 row with this key: no unique TIGER 2024 feature of that name inside it, no point"]); continue
          rows[layer][hits[0]["GEOID"]] = [("geo", gg)]
          rep["geoid_keys"].append([layer, k, hits[0]["GEOID"]])
      for layer in ("county", "town", "place", "sch", "cd", "sldu", "sldl"):
          out[layer] = {}
          R = rows.get(layer, {})
          rep["rows"][layer] = len(R)
          ni = npl = n4 = 0
          for k in sorted(R):
              pt, meth, nd, note = pick(st, layer, k, R[k])
              if pt is None:
                  rep["misses"].append([layer, k, note]); continue
              if note: rep["misses"].append([layer, k, "point given; " + note])
              out[layer][k] = [pt[0], pt[1]]
              if meth == "intpt": ni += 1
              else: npl += 1
              if nd > 3: n4 += 1
              if nd < 3: rep.setdefault("dec2", collections.Counter())[layer] += 1
          rep["points"][layer] = len(out[layer]); rep["intpt"][layer] = ni; rep["polylabel"][layer] = npl; rep["dec4plus"][layer] = n4
      def fmt(v):
          return "[" + ",".join(("%.5f" % c).rstrip("0").rstrip(".") for c in v) + "]"
      body = ",".join(json.dumps(L) + ":{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + fmt(v) for k, v in out[L].items()) + "}" for L in out)
      js = "__points(" + json.dumps(st) + ",{" + body + "});\n"
      if len(gzip.compress(js.encode(), 6)) <= GZMAX: break
    path = os.path.join(D, "points", fn)
    open(path, "w", encoding="utf-8").write(js)
    rep["bytes"] = len(js.encode()); rep["gzip"] = len(gzip.compress(js.encode(), 9)); rep["gzip6"] = len(gzip.compress(js.encode(), 6))
    REPORT[st] = rep
    print(st, rep["bytes"], rep["gzip"], rep["gzip6"], rep["ndec"], {L: (rep["rows"][L], rep["points"][L], rep["intpt"][L]) for L in out}, "misses", len(rep["misses"]), flush=True)
if a.report: json.dump(REPORT, open(a.report, "w"), indent=1, ensure_ascii=False)
