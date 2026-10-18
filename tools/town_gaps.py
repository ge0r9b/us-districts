#!/usr/bin/env python3
"""Town-layer gap audit: what the v2 app shows per county in its town layer (townsIn() of v2/index.html: v1 town rows of
data/<State>.js, then v2/data/parts/<State>.js rows, a parts row being hidden when its normT() name is already shown in
that county; a parts row with no geometry borrows the v1 'places' polygon of the same name) against Census TIGER 2024:
  expected per county = incorporated places (CLASSFP C*) whose land in the county is >= 2 % of the place or >= 0.5 km2
                        + county subdivisions with a government (FUNCSTAT A, B, C, G),
  keyed by normT(NAMELSAD) like the app (one key per county).
Every app row (shown or hidden) is resolved to a TIGER GEOID: county subdivision of that county by NAMELSAD, else
incorporated place / CDP of the state by NAMELSAD touching the county.
usage: town_gaps.py <repo> <tiger_dir with tl_2024_SS_place.zip, tl_2024_SS_cousub.zip> <tl_2024_us_county.zip> --json OUT [--states A,B]
"""
import sys, os, json, re, collections, io, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shapefile
from shapely.geometry import shape
from shapely.strtree import STRtree
import coverage_audit as A

def normT(n): return re.sub(r"\s+(city|borough|town|township|village|cdp|municipality|charter township|plantation)$", "", str(n).lower()).strip()

def recs(z, flt=None):
    Z = zipfile.ZipFile(z); b = [n for n in Z.namelist() if n.endswith(".shp")][0][:-4]
    r = shapefile.Reader(shp=io.BytesIO(Z.read(b + ".shp")), dbf=io.BytesIO(Z.read(b + ".dbf")), shx=io.BytesIO(Z.read(b + ".shx")), encoding="utf-8")
    for i, rec in enumerate(r.iterRecords()):
        d = rec.as_dict()
        if flt and not flt(d): continue
        yield d, shape(r.shape(i).__geo_interface__).buffer(0)

FIPS={'01':'Alabama','02':'Alaska','04':'Arizona','05':'Arkansas','06':'California','08':'Colorado','09':'Connecticut','10':'Delaware','12':'Florida','13':'Georgia','15':'Hawaii','16':'Idaho','17':'Illinois','18':'Indiana','19':'Iowa','20':'Kansas','21':'Kentucky','22':'Louisiana','23':'Maine','24':'Maryland','25':'Massachusetts','26':'Michigan','27':'Minnesota','28':'Mississippi','29':'Missouri','30':'Montana','31':'Nebraska','32':'Nevada','33':'New Hampshire','34':'New Jersey','35':'New Mexico','36':'New York','37':'North Carolina','38':'North Dakota','39':'Ohio','40':'Oklahoma','41':'Oregon','42':'Pennsylvania','44':'Rhode Island','45':'South Carolina','46':'South Dakota','47':'Tennessee','48':'Texas','49':'Utah','50':'Vermont','51':'Virginia','53':'Washington','54':'West Virginia','55':'Wisconsin','56':'Wyoming'}

def main():
    a = sys.argv[1:]; opt = lambda k: a[a.index(k) + 1] if k in a else None
    repo, td, cz = [x for x in a if not x.startswith("--") and x not in (opt("--json"), opt("--states"))][:3]
    st2f = {v: k for k, v in FIPS.items()}
    states = opt("--states").split(",") if opt("--states") else sorted(st2f)
    C = collections.defaultdict(dict)
    for d, g in recs(cz): C[d["STATEFP"]][d["COUNTYFP"]] = (d["NAMELSAD"], g)
    out = {}
    for st in states:
        sf = st2f[st]; fn = st.replace(" ", "-") + ".js"
        if not os.path.exists(os.path.join(repo, "data", fn)): continue
        geo = A.jsargs(os.path.join(repo, "data", fn), r"__geo\(")[1]
        pp = os.path.join(repo, "v2", "data", "parts", fn)
        parts = []
        if os.path.exists(pp):
            s = open(pp).read(); parts = json.loads(s[s.index("[", s.index("(")):s.rindex("]") + 1])
        places_v1 = {p[1] for p in geo.get("places") or []}
        cty = {cn: (cf, g) for cf, (cn, g) in C[sf].items()}
        # TIGER
        PL = [(d, g) for d, g in recs(os.path.join(td, "tl_2024_%s_place.zip" % sf))]
        CS = [(d, g) for d, g in recs(os.path.join(td, "tl_2024_%s_cousub.zip" % sf)) if not d["GEOID"].endswith("00000")]
        T = STRtree([g for _, g in PL])
        pl_in = collections.defaultdict(list)  # county -> [(rec, share, km2)]
        for cn, (cf, cg) in cty.items():
            for i in T.query(cg):
                d, g = PL[i]; x = g.intersection(cg).area
                if x <= 0: continue
                sh = x / g.area; km2 = x * 111.0 * 111.0 * 0.75
                pl_in[cn].append((d, sh, km2))
        cs_in = collections.defaultdict(list)
        cf2n = {cf: cn for cn, (cf, g) in cty.items()}
        for d, g in CS: cs_in[cf2n.get(d["COUNTYFP"])].append(d)
        res = {"counties": {}, "tot": collections.Counter()}
        for cn in sorted(cty):
            # app rows
            rows = []; have = set()
            for t in geo.get("towns") or []:
                if t[1] == cn: rows.append({"name": t[2], "src": "v1"}); have.add(normT(t[2]))
            for p in parts:
                if p[0] != cn: continue
                r = {"name": p[1], "src": "parts" + ("" if p[2] else "-place")}
                if not p[2] and p[1] not in places_v1: r["hidden"] = "no v1 place polygon"
                elif normT(p[1]) in have: r["hidden"] = "normT"
                else: have.add(normT(p[1]))
                rows.append(r)
            csn = {d["NAMELSAD"]: d for d in cs_in.get(cn, [])}
            pln = {}
            for d, sh, km2 in pl_in.get(cn, []): pln.setdefault(d["NAMELSAD"], (d, sh, km2))
            for r in rows:
                if r["name"] in csn: d = csn[r["name"]]; r["geoid"] = d["GEOID"]; r["tiger"] = "cousub " + d["FUNCSTAT"]
                elif r["name"] in pln: d = pln[r["name"]][0]; r["geoid"] = d["GEOID"]; r["tiger"] = "place " + d["CLASSFP"] + " " + d["FUNCSTAT"]
            exp = {}
            for d, sh, km2 in pl_in.get(cn, []):
                if d["CLASSFP"].startswith("C") and (sh >= 0.02 or km2 >= 0.5): exp.setdefault(normT(d["NAMELSAD"]), ("place", d["GEOID"], d["NAMELSAD"]))
            for d in cs_in.get(cn, []):
                if d["FUNCSTAT"] in ("A", "B", "C", "G"): exp.setdefault(normT(d["NAMELSAD"]), ("cousub", d["GEOID"], d["NAMELSAD"]))
            shown = {normT(r["name"]) for r in rows if "hidden" not in r}
            miss = {k: v for k, v in exp.items() if k not in shown}
            extra = sorted(r["name"] for r in rows if "hidden" not in r and normT(r["name"]) not in exp)
            res["counties"][cn] = {"rows": rows, "missing": sorted(miss.values()), "extra": extra}
            t = res["tot"]; t["expected"] += len(exp); t["shown"] += len(shown); t["shown_expected"] += len(exp) - len(miss)
            t["missing"] += len(miss); t["missing_place"] += sum(1 for v in miss.values() if v[0] == "place"); t["missing_cousub"] += sum(1 for v in miss.values() if v[0] == "cousub")
            t["extra"] += len(extra); t["hidden_normT"] += sum(1 for r in rows if r.get("hidden") == "normT"); t["hidden_nopoly"] += sum(1 for r in rows if r.get("hidden") == "no v1 place polygon")
        res["tot"] = dict(res["tot"]); out[st] = res
        print(st, res["tot"], flush=True)
    json.dump(out, open(opt("--json"), "w"), ensure_ascii=False)

if __name__ == "__main__":
    main()
