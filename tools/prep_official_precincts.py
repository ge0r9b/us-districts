#!/usr/bin/env python3
"""Build the replacement files read by tools/fill_official_precincts.py from untouched official downloads kept in
/workspace/w/lanes/geo-data-raw/step5/<st>/ (nothing here is written to the repo). One function per state; each joins
official 2024 precinct shapes to official 2024 presidential precinct returns 1:1 and fails loudly on any unmatched unit.
Votes: dem = Harris, rep = Trump, total = all presidential candidates incl. write-ins as reported.
Units with no geography (early voting, provisional, ...) go to 'not_located'.
usage: prep_official_precincts.py <raw dir> <st> <out.json>"""
import sys, os, csv, json, re, io, zipfile, collections
import shapefile
from shapely.geometry import shape, mapping

def shp_records(z):
    Z = zipfile.ZipFile(z); b = [n for n in Z.namelist() if n.endswith(".shp")][0][:-4]
    r = shapefile.Reader(shp=io.BytesIO(Z.read(b + ".shp")), dbf=io.BytesIO(Z.read(b + ".dbf")), shx=io.BytesIO(Z.read(b + ".shx")))
    for s in r.iterShapeRecords(): yield s.record.as_dict(), shape(s.shape.__geo_interface__).buffer(0)

def la(D):
    G = {x["UNIT_NAME"]: g for x, g in shp_records(D + "/la_2024_precincts_12-31-2024.zip") if x["COUNTY"] == "095" and x["VTD"] != "ZZZZZZ"}
    rows, nl, used = [], {}, set()
    R = list(csv.reader(open(D + "/la_president_2024_byprecinct_67190.csv")))
    for x in R[1:]:
        if x[1] != "St. John The Baptist": continue
        d, rp, tot = int(x[4]), int(x[7]), sum(int(v) for v in x[4:])
        if not x[3]: nl[x[2]] = [d, rp, tot]; continue
        k = "%d-%d" % (int(x[2]), int(x[3])); used.add(k); rows.append([k, d, rp, tot, mapping(G[k])])
    assert used == set(G), set(G) ^ used
    return {"state": "Louisiana", "year": "2024", "counties": {"St. John the Baptist Parish": {
        "source": "Shapes: Louisiana Legislature, 2024 Precinct Shapefiles (12-31-2024), https://redist.legis.la.gov/default_ShapeFiles2020 ; votes: Louisiana Secretary of State, official results Nov 5 2024, Presidential Electors (race 67190) by precinct, https://voterportal.sos.la.gov/ElectionResults/ElectionResults/Data?blob=20241105/csv/ByPrecinct_67190.csv",
        "rows": rows, "not_located": nl}}}

def va(D):
    V = collections.defaultdict(lambda: [0, 0, 0])
    for r in csv.DictReader(open(D + "/va_2024_election_results_official.csv", encoding="latin-1")):
        if r["OfficeTitle"] != "President and Vice President" or r["LocalityName"] not in ("CHESAPEAKE CITY", "SUFFOLK CITY"): continue
        p = V[(r["LocalityName"], r["PrecinctName"])]; v = int(r["TOTAL_VOTES"])
        if r["Party"] == "Democratic": p[0] += v
        if r["Party"] == "Republican": p[1] += v
        p[2] += v
    out = {}
    # Chesapeake: city GIS (Voter Registrar), PRECINCTID = number before ' - ' in the official precinct name
    ch = json.load(open(D + "/chesapeake_voting_precincts.geojson"))
    G = {int(f["properties"]["PRECINCTID"]): shape(f["geometry"]).buffer(0) for f in ch["features"] if f["properties"]["PRECINCTID"]}
    rows, nl, used = [], {}, set()
    for (L, nm), v in V.items():
        if L != "CHESAPEAKE CITY": continue
        m = re.match(r"(\d+) - ", nm)
        if not m: nl[nm] = v; continue
        k = int(m.group(1)); used.add(k)
        old = [r for r in rows if r[0] == nm]
        if old: old[0][1] += v[0]; old[0][2] += v[1]; old[0][3] += v[2]  # 054 PUGHSVILLE is reported in two parts (split precinct)
        else: rows.append([nm, v[0], v[1], v[2], mapping(G[k])])
    assert used == set(G), set(G) ^ used
    out["Chesapeake city"] = {"source": "Shapes: City of Chesapeake GIS, Voting Precincts (maintained by the Voter Registrar), https://gis.cityofchesapeake.net/mapping/rest/services/OpenData/OpenData/MapServer/28 ; votes: Virginia Department of Elections, official results 2024 November General (certified, as of 2025-03-05), Election Results CSV, https://enr.elections.virginia.gov/results/public/Virginia/elections/2024NovemberGeneral/reports",
                              "rows": rows, "not_located": nl}
    su = json.load(open(D + "/suffolk_voter_precincts.geojson"))
    n = lambda s: re.sub(r"[^A-Z]", "", s.upper().split(" - ", 1)[-1].split("/")[0]).replace("BELLE", "BEL")
    G = {n(f["properties"]["Precinct_Name"]): shape(f["geometry"]).buffer(0) for f in su["features"]}
    rows, nl, used = [], {}, set()
    for (L, nm), v in V.items():
        if L != "SUFFOLK CITY": continue
        if not re.match(r"\d+ - ", nm): nl[nm] = v; continue
        k = n(nm); used.add(k); rows.append([nm, v[0], v[1], v[2], mapping(G[k])])
    assert used == set(G), set(G) ^ used
    out["Suffolk city"] = {"source": "Shapes: City of Suffolk GIS, ALL Voter Precincts (layer 42), https://suffolkgis.suffolk-va.net/hosting/rest/services/ALL_GIS_Layers/MapServer/42 ; votes: Virginia Department of Elections, official results 2024 November General (certified), Election Results CSV",
                           "rows": rows, "not_located": nl}
    return {"state": "Virginia", "year": "2024", "counties": out}

def ms(D):
    # Harrison County: county GIS 'Voting Precincts' (District/Precincts MapServer layer 1, 49 polygons named as in the
    # recap); votes transcribed from the official county recapitulation (scanned PDF filed with the SOS on Nov 14 2024),
    # every candidate column checked against the recap's TOTAL column (exact match, 75,923 votes)
    n = lambda s: re.sub(r"[^A-Z0-9]", "", s.upper().replace("VOTING DISTRICT", "").replace("HANSBORO", "HANDSBORO"))
    ab = {"E": "EAST", "W": "WEST", "GPT": "GULFPORT", "MISS": "MISSISSIPPI"}
    n2 = lambda s: n(" ".join(ab.get(x, x) for x in s.upper().replace("/", " ").replace("#", " ").split()))
    G = {n(f["properties"]["NAME20"]): shape(f["geometry"]).buffer(0) for f in json.load(open(D + "/harrison_voting_precincts_district.geojson"))["features"]}
    rows, used = [], set()
    for r in csv.DictReader(open(D + "/harrison_president_2024_transcribed.csv")):
        k = n2(r["precinct"]); used.add(k)
        v = {c: int(x) for c, x in r.items() if c != "precinct"}
        rows.append([r["precinct"], v["harris"], v["trump"], sum(v.values()), mapping(G[k])])
    assert used == set(G), set(G) ^ used
    # The county precinct layer leaves the Back Bay of Biloxi and the Sound out (water, no voters). Those areas are
    # added as one zero-vote unit from the county's own hydrography layer (AssetMap layer 16 'MS Sound/Back bay')
    # minus the precincts, so the water does not count as missing precinct cover. It adds no votes.
    from shapely.ops import unary_union
    W = unary_union([shape(f["geometry"]).buffer(0) for f in json.load(open(D + "/harrison_ms_sound_back_bay.geojson"))["features"] if f["geometry"]])
    rows.append(["(water: Back Bay of Biloxi / Mississippi Sound, no voters)", 0, 0, 0, mapping(W.difference(unary_union(list(G.values()))))])
    return {"state": "Mississippi", "year": "2024", "counties": {"Harrison County": {
        "source": "Shapes: Harrison County GIS, Voting Precincts (https://geo.co.harrison.ms.us/server/rest/services/District/Precincts/MapServer/1, 49 precincts on the Census 2020 VTD lines); votes: Harrison County Election Commission, Official Recapitulation, 11/5/2024 Federal General Election, received by the MS SOS Elections Division Nov 14 2024 (https://sos.ms.gov/elections/electionresults/2024General/County%20Results/Harrison.pdf), transcribed; all 9 candidate columns equal the recap TOTAL column",
        "rows": rows, "not_located": {}, "water_source": "Harrison County GIS, AssetMap MapServer layer 16 MS Sound/Back bay"}}}

if __name__ == "__main__":
    D, st, o = sys.argv[1:4]
    R = globals()[st](D); json.dump(R, open(o, "w"))
    for c, v in R["counties"].items():
        print(c, "units", len(v["rows"]), "located", [sum(r[k] for r in v["rows"]) for k in (1, 2, 3)], "not located", v["not_located"])
