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

def al(D):
    # Morgan County: county voter GIS (KCS GIS 'Morgan County Voting Districts', VAM/AL52_VAM_MS layer 9 Voting Precincts,
    # precinct number + current polling place name); votes: Alabama SOS 2024 General precinct-level results
    # (2024-General-Morgan.xls), reported by polling place. Polling places are matched to precinct numbers by name
    # (MATCH below, checked against registered-voter counts). Three units whose 2024 polling place has no
    # unambiguous match in the current layer, plus ABSENTEE and PROVISIONAL, are kept as not located (none of the
    # three candidate precincts touches HD 004).
    import pandas as pd
    MATCH = {"00101": "MACEDONIA C P CHURCH", "00301": "COUNTY COURTHOUSE", "00303": "AQUADOME REC CTR", "00304": "FORT DECATUR REC CTR",
             "00306": "WESTMEADE BAPT CH", "00307": "DECATUR UTILITIES", "00308": "1ST BAPT AUSTINVILLE", "00309": "AMER LEGION BLDG POST 15",
             "00310": "DECATUR BAPT CH", "00312": "TURNER SURLES COMM CTR", "00314": "DECATUR CH OF CHRIST", "00315": "FIRST BIBLE CH",
             "00401": "BURNINGTREE COUNTRY CLUB", "00402": "BCOMING CH / EPIC CH", "00403": "POINT MALLARD EVENT CTR", "00501": "PRICEVILLE EVENT CTR",
             "00601": "CTR SPRINGS METHODIST CH", "00701": "COTACO FIRE STATION", "00801": "LACEY'S SPRING SR CTR", "00901": "UNION HILL SR CTR",
             "01001": "TRI-COUNTY VFD", "01301": "S_A_V_E_S_ FIRE DEPT #1", "01401": "NEW CTR BAPT CH", "01501": "JOHN J SPARKMAN CIVIC",
             "01502": "1ST BAPT CH HARTSELLE", "01601": "TRINITY MUN BLDG", "01701": "W MORGAN E LAWRENCE W&S", "01801": "NEEL VFD",
             "01901": "DANVILLE VFD", "02001": "MASSEY FIRE DEPT", "02101": "FALKVILLE MUN BLDG", "02201": "COUNTY DISTRICT 3 VOTING",
             "02301": "ODEN RIDGE VFD", "02501": "EVA TOWN HALL", "02701": "GUM POND FIRE STATION", "02801": "LEBANON BAPT CH"}
    x = pd.read_excel(D + "/2024-General-Morgan.xls", header=None)
    cols = [str(c).strip() for c in x.iloc[0, 3:]]
    pr = x[x[0].astype(str).str.startswith("PRESIDENT AND VICE")]
    cand = [str(c).strip() for c in pr.iloc[:, 2]]
    V = {}
    for k, c in enumerate(cols):
        vals = dict(zip(cand, [int(v) for v in pr.iloc[:, 3 + k]]))
        V[c] = [vals["Kamala D. Harris"], vals["Donald J. Trump"], sum(v for n, v in vals.items() if n not in ("Over Votes", "Under Votes"))]
    G = {}
    from shapely.ops import unary_union
    for f in json.load(open(D + "/morgan_layer9.geojson"))["features"]:
        G.setdefault(f["properties"]["Precinct"], []).append(shape(f["geometry"]).buffer(0))
    rows, nl = [], {}
    used = set()
    for pnum, poll in MATCH.items():
        used.add(poll); rows.append([pnum + " " + poll] + V[poll] + [mapping(unary_union(G[pnum]))])
    for c in cols:
        if c not in used: nl[c] = V[c]
    return {"state": "Alabama", "year": "2024", "counties": {"Morgan County": {
        "source": "Shapes: Morgan County voting precincts, KCS GIS VAM/AL52_VAM_MS MapServer layer 9 (https://web4.kcsgis.com/kcsgis/rest/services/VAM/AL52_VAM_MS/MapServer/9); votes: Alabama Secretary of State, 2024 General Election precinct level results (2024-General Precinct Level Results.zip, 2024-General-Morgan.xls), https://www.sos.alabama.gov/alabama-votes/voter/election-data",
        "rows": rows, "not_located": nl, "unmatched_precincts": sorted(set(G) - set(MATCH))}}}

def wy(D):
    # Fremont County: county GIS Voter Precincts (Beacon static feature service, layer 15, 'Name N-M'); votes: Wyoming
    # SOS, Fremont County Official Precinct-by-Precinct Summary, General Election Nov 5 2024 (text PDF). The PDF's
    # Total row equals the official county result, so absentee ballots are inside the precincts.
    import subprocess
    t = subprocess.run(["pdftotext", "-layout", D + "/2024_Fremont_County_General_PbP.pdf", "-"], capture_output=True, text=True).stdout
    sec = t[t.index("United States President"):t.index("United States Senator")]
    V = {}
    for ln in sec.splitlines():
        m = re.match(r"^(\d\d-\d|Total)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$", ln)
        if m:
            n = [int(x.replace(",", "")) for x in m.groups()[1:]]
            V[m.group(1)] = [n[1], n[0], n[0] + n[1] + n[2] + n[3]]  # dem, rep, total (R, D, L, write-ins; over/under excluded)
    tot = V.pop("Total")
    assert [sum(v[k] for v in V.values()) for k in range(3)] == tot, tot
    G = {}
    for f in json.load(open(D + "/fremont_voter_precincts.geojson"))["features"]:
        a, b = re.search(r"(\d+)-(\d+)$", f["properties"]["Precincts"]).groups(); G["%02d-%s" % (int(a), b)] = (f["properties"]["Precincts"], shape(f["geometry"]).buffer(0))
    assert set(G) == set(V), set(G) ^ set(V)
    rows = [[G[k][0]] + V[k] + [mapping(G[k][1])] for k in sorted(V)]
    return {"state": "Wyoming", "year": "2024", "counties": {"Fremont County": {
        "source": "Shapes: Fremont County GIS, Voter Precincts (FremontCountyWY_BeaconStatic FeatureServer layer 15, https://services8.arcgis.com/rlGvD2ZEQWYJHMZp/arcgis/rest/services/FremontCountyWY_BeaconStatic/FeatureServer/15); votes: Wyoming Secretary of State, Fremont County Official Precinct-by-Precinct Summary, General Election Nov 5 2024 (https://sos.wyo.gov/Elections/Docs/2024/Results/General/2024_Fremont_County_General_PbP.pdf)",
        "rows": rows, "not_located": {}}}}

if __name__ == "__main__":
    D, st, o = sys.argv[1:4]
    R = globals()[st](D); json.dump(R, open(o, "w"))
    for c, v in R["counties"].items():
        print(c, "units", len(v["rows"]), "located", [sum(r[k] for r in v["rows"]) for k in (1, 2, 3)], "not located", v["not_located"])
