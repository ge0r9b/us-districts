"""US colleges and universities from the NCES IPEDS HD (institutional characteristics directory) file.

Inputs (raw/, gitignored): raw/ipeds/HD2024.zip (+ HD2024_dict.xlsx for code labels), raw/wikidata_ipeds.json
(scripts/fetch_wikidata_ipeds.py). Outputs:
  organizations/colleges_us.csv            one row per institution (unitid)
  organizations/colleges_us_locations.csv  company_locations rows (role establishment_at), appended by build_locations.py
  organizations/colleges_us_sources.csv    sources for both, merged into sources.csv by build_locations.py
Scope: CYACTIVE=1 (active) and PSET4FLG=1 (Title IV postsecondary). Degree-granting rows (DEGGRANT=1) are the core;
non-degree Title IV rows are kept with flag non_degree_granting. Sector 0 (administrative units / system offices) are
not institutions and are only used to link F1SYSNAM to a unitid. Values are copied from IPEDS; nothing is estimated.
"""
import collections
import hashlib
import json
import zipfile

import pandas as pd

from common import RAW, ROOT, read_meta

YEAR = "2024"
ZIP = RAW / "ipeds" / f"HD{YEAR}.zip"
DICT = RAW / "ipeds" / f"HD{YEAR}_dict.xlsx"
OUT = ROOT / "organizations"
OUT.mkdir(exist_ok=True)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


ret = pd.Timestamp(ZIP.stat().st_mtime, unit="s").date().isoformat()
S_IP = f"ipeds-hd{YEAR}-{ret}"
WDM = read_meta("wikidata_ipeds")
S_WDI = f"wikidata-ipeds-p1771-{WDM['retrieved_at']}"
S_CEN = "census-cb2024-county"
SOURCES = [
    dict(source_id=S_IP, source=f"NCES IPEDS HD{YEAR} institutional characteristics directory (provisional release; latest HD file published)",
         source_url=f"https://nces.ed.gov/ipeds/datacenter/data/HD{YEAR}.zip", license="public domain (US government work)",
         retrieved_at=ret, commit="", sha256=sha(ZIP)),
    dict(source_id=S_WDI, source="Wikidata items with IPEDS ID (P1771), truthy statements",
         source_url="https://query.wikidata.org/", license="CC0 1.0", retrieved_at=WDM["retrieved_at"], commit="",
         sha256=sha(RAW / "wikidata_ipeds.json")),
]

with zipfile.ZipFile(ZIP) as z:
    name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
    hd = pd.read_csv(z.open(name), encoding="latin-1", dtype=str, keep_default_na=False)
hd.columns = [c.replace("ï»¿", "").replace("\ufeff", "").strip() for c in hd.columns]
hd = hd.apply(lambda s: s.str.strip())
fr = pd.read_excel(DICT, sheet_name="Frequencies", dtype=str)
LAB = {(r.VarName, r.CodeValue): str(r.ValueLabel).strip() for r in fr.itertuples()}

# Wikidata P1771 -> QID; an IPEDS id with two items, or an item with two in-scope ids, is not used (flagged)
b = json.loads((RAW / "wikidata_ipeds.json").read_text())["results"]["bindings"]
pairs = {(x["item"]["value"].rsplit("/", 1)[1], x["id"]["value"].strip()) for x in b}
by_id, by_q = collections.defaultdict(set), collections.defaultdict(set)
for q, i in pairs:
    by_id[i].add(q)

V2 = set(pd.read_csv(ROOT.parents[1] / "geo" / "counties.csv", dtype=str, keep_default_na=False).geoid)
TERR = {"PR": "PR", "GU": "GU", "VI": "VI", "AS": "AS", "MP": "MP", "FM": "FM", "MH": "MH", "PW": "PW"}
CONTROL = {"1": "public", "2": "private_nonprofit", "3": "private_for_profit"}
KIND = {"1": "nonprofit", "2": "nonprofit", "3": "company"}
LEVEL = {"1": "four_year", "2": "two_year", "3": "less_than_two_year"}

def v(x):
    return "" if x in ("-1", "-2", "-3") else x


scope = hd[(hd.CYACTIVE == "1") & (hd.PSET4FLG == "1") & (hd.SECTOR != "0")].copy()
for u in scope.UNITID:
    for q in by_id.get(u, ()):
        by_q[q].add(u)

# system name -> unitid of the IPEDS row with that exact name (system offices are sector 0; some systems share a campus name)
by_name = collections.defaultdict(set)
for r in hd.itertuples():
    by_name[r.INSTNM.casefold()].add(r.UNITID)
s0_by_code = collections.defaultdict(set)
for r in hd[hd.SECTOR == "0"].itertuples():
    if v(r.F1SYSCOD):
        s0_by_code[r.F1SYSCOD].add(r.UNITID)
# main campus by OPEID: 8-digit OPEID, branch = same first 6 digits with a non-00 suffix
opeid_main = {r.OPEID: r.UNITID for r in hd.itertuples() if len(r.OPEID) == 8 and r.OPEID.endswith("00")}


def qid_for(u):
    qs = by_id.get(u, set())
    if len(qs) == 1:
        q = next(iter(qs))
        if len(by_q.get(q, ())) <= 1:
            return q, ""
        return "", f"wikidata_item_has_several_ipeds_ids_review:{q}"
    if len(qs) > 1:
        return "", "wikidata_p1771_several_items_review:" + "|".join(sorted(qs))
    return "", ""


def ent_of(u):
    q, _ = qid_for(u)
    return f"wikidata:{q}" if q else f"ipeds:{u}"


rows, st = [], collections.Counter()
for r in scope.itertuples():
    fl = []
    q, qf = qid_for(r.UNITID)
    if qf:
        fl.append(qf)
    if r.DEGGRANT != "1":
        fl.append("non_degree_granting")
    cc = TERR.get(r.STABBR, "US")
    cg = r.COUNTYCD.zfill(5) if v(r.COUNTYCD) else ""
    if cc != "US":
        fl.append(f"us_territory_{cc}")
    if cg and cg not in V2:
        fl.append(f"county_not_in_v2-2024:{cg}")
    if not cg:
        fl.append("no_county_in_ipeds")
    if not (v(r.LATITUDE) and v(r.LONGITUD)):
        fl.append("no_coordinates_in_ipeds")
    if v(r.CLOSEDAT) or (r.DEATHYR not in ("-2", "")):
        fl.append(f"ipeds_closing:{v(r.CLOSEDAT) or r.DEATHYR}")
    if r.CONTROL not in CONTROL:
        fl.append("control_unknown")
    sysname = v(r.F1SYSNAM)
    # system office: the one sector-0 IPEDS row with the same F1SYSCOD, else the one IPEDS row named exactly like F1SYSNAM
    sys_u = s0_by_code.get(r.F1SYSCOD, set()) if sysname else set()
    if len(sys_u) != 1 and sysname:
        sys_u = by_name.get(sysname.casefold(), set()) or sys_u
    sys_q = ""
    if len(sys_u) == 1:
        sys_q = qid_for(next(iter(sys_u)))[0]
    elif len(sys_u) > 1:
        fl.append("system_name_matches_several_ipeds_rows")
    par_u = ""
    if len(r.OPEID) == 8 and not r.OPEID.endswith("00"):
        par_u = opeid_main.get(r.OPEID[:6] + "00", "")
        if par_u == r.UNITID:
            par_u = ""
        if not par_u:
            fl.append("branch_opeid_main_campus_not_in_ipeds")
    web = v(r.WEBADDR)
    rows.append(dict(
        entity_id=f"wikidata:{q}" if q else f"ipeds:{r.UNITID}",
        kind=KIND.get(r.CONTROL, ""), control=CONTROL.get(r.CONTROL, ""),
        name=r.INSTNM, aliases=v(r.IALIAS),
        address=r.ADDR, city=r.CITY, state=r.STABBR, zip=r.ZIP,
        county=v(r.COUNTYNM), county_geoid=cg if cg in V2 else "",
        lat=v(r.LATITUDE), lon=v(r.LONGITUD), country_code=cc,
        unitid=r.UNITID, opeid=v(r.OPEID), ein=v(r.EIN), website=web,
        sector=r.SECTOR, sector_label=LAB.get(("SECTOR", r.SECTOR), ""),
        level=LEVEL.get(r.ICLEVEL, ""), degree_granting="yes" if r.DEGGRANT == "1" else "no",
        highest_offering=LAB.get(("HLOFFER", r.HLOFFER), "") if v(r.HLOFFER) else "",
        carnegie_basic=v(r.C21BASIC), carnegie_basic_label=LAB.get(("C21BASIC", r.C21BASIC), "").strip() if v(r.C21BASIC) else "",
        hbcu="yes" if r.HBCU == "1" else "no", tribal="yes" if r.TRIBAL == "1" else "no",
        land_grant="yes" if r.LANDGRNT == "1" else "no",
        system_name=sysname, system_unitid=next(iter(sys_u)) if len(sys_u) == 1 else "",
        system_entity_id=f"wikidata:{sys_q}" if sys_q else "",
        main_campus_unitid=par_u, main_campus_entity_id=ent_of(par_u) if par_u else "",
        wikidata_qid=f"wikidata:{q}" if q else "",
        flags=";".join(fl),
        source=";".join([S_IP, S_WDI] if q else [S_IP]),
        source_url=f"https://nces.ed.gov/collegenavigator/?id={r.UNITID}",
        source_date=ret))
df = pd.DataFrame(rows).sort_values(["state", "name", "unitid"])
assert not df.entity_id.duplicated().any()
df.to_csv(OUT / "colleges_us.csv", index=False, lineterminator="\n")

loc = pd.DataFrame(dict(
    location_id="colleges_us:" + df.unitid, entity_id=df.entity_id, sub_entity_id="", role="establishment_at", name=df.name,
    address=[", ".join(t for t in x if t) for x in zip(df.address, df.city, df.state, df.zip)],
    geoid=df.county_geoid, boundary_set=df.county_geoid.map(lambda g: "v2-2024" if g else ""), lat=df.lat, lon=df.lon,
    source_id=S_IP, retrieved_at=ret, brand_name=df.name,
    geoid_method=df.county_geoid.map(lambda g: "ipeds_countycd" if g else ""), flags=df["flags"], country_code=df.country_code))
loc = loc[(loc.lat != "") | (loc.geoid != "")]
loc.to_csv(OUT / "colleges_us_locations.csv", index=False, lineterminator="\n")
pd.DataFrame(SOURCES).to_csv(OUT / "colleges_us_sources.csv", index=False, lineterminator="\n")

summ = dict(rows=len(df), degree_granting=int((df.degree_granting == "yes").sum()),
            non_degree_granting=int((df.degree_granting == "no").sum()),
            by_control=df.control.value_counts().to_dict(), by_kind=df.kind.value_counts().to_dict(),
            by_level=df.level.value_counts().to_dict(),
            by_control_level=df.groupby(["control", "level"]).size().unstack(fill_value=0).to_dict("index"),
            by_control_level_degree=df[df.degree_granting == "yes"].groupby(["control", "level"]).size().unstack(fill_value=0).to_dict("index"),
            qid_matched=int((df.wikidata_qid != "").sum()),
            qid_matched_degree=int(((df.wikidata_qid != "") & (df.degree_granting == "yes")).sum()),
            qid_review=int(df["flags"].str.contains("wikidata_").sum()),
            with_system=int((df.system_name != "").sum()), system_linked_unitid=int((df.system_unitid != "").sum()),
            system_linked_qid=int((df.system_entity_id != "").sum()),
            distinct_systems=int(df.system_name[df.system_name != ""].nunique()),
            distinct_systems_with_qid=int(df.system_name[df.system_entity_id != ""].nunique()),
            branches=int((df.main_campus_unitid != "").sum()),
            county_geoid=int((df.county_geoid != "").sum()), no_coordinates=int((df.lat == "").sum()),
            hbcu=int((df.hbcu == "yes").sum()), tribal=int((df.tribal == "yes").sum()),
            territories=df.country_code[df.country_code != "US"].value_counts().to_dict(),
            locations_rows=len(loc), ipeds_hd_rows=len(hd),
            excluded_inactive=int((hd.CYACTIVE != "1").sum()),
            excluded_not_title_iv=int(((hd.CYACTIVE == "1") & (hd.PSET4FLG != "1")).sum()),
            excluded_admin_units=int(((hd.CYACTIVE == "1") & (hd.PSET4FLG == "1") & (hd.SECTOR == "0")).sum()))
(OUT / "colleges_us_summary.json").write_text(json.dumps(summ, indent=1, default=int) + "\n")
print(json.dumps(summ, indent=1, default=int))
