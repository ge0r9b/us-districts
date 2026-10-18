#!/usr/bin/env python3
"""data-v3/inst/county_government.csv: does each county area have its own county government? (ENTITIES_SCHEMA.md Q1)

Source (official): U.S. Census Bureau, 2022 Census of Governments: Organization, Government Units Listing
(Govt_Units_2022_Final.xlsx, tab 'General Purpose'), public domain. A county area has its own government
(has_own_government=yes) iff that listing has a UNIT_TYPE '1 - COUNTY' unit with that FIPS state+county.
Nothing else is inferred:
  - no county unit -> has_own_government=no; where TIGER FUNCSTAT says the area is consolidated (C), partly
    consolidated (B) or an independent city / DC (F), or TIGER says A but CoG has no county unit, the CoG general-purpose
    unit of that county area with the largest population is named in cog_unit_* as the government CoG counts instead
    (government_kind=municipal). It is a citation of the listing, not a claim about which unit performs county functions.
  - cross-check: TIGER 2024 FUNCSTAT from data-v3/geo/county_funcstat.csv (geo lane). agrees_with_tiger = yes when
    (FUNCSTAT A) == (CoG county unit present). Every disagreement is listed in the summary; none is resolved by guessing.
  - vintage 2020 rows only where the 2020 county set differs from 2024 (TIGER 2020 Gazetteer): Connecticut's 8 old counties.
usage: inst_county_government.py <repo> --cog Govt_Units_2022_Final.xlsx --gaz2020 2020_Gaz_counties_national.txt --out DIR --retrieved DATE
"""
import sys, os, csv, json, hashlib, collections
import openpyxl

COG_URL = "https://www2.census.gov/programs-surveys/gus/datasets/2022/govt_units_2022.ZIP"
COLS = ["county_geoid", "vintage", "county_name", "has_own_government", "government_kind", "cog_pid6", "cog_unit_name", "cog_unit_type",
        "tiger_funcstat", "agrees_with_tiger", "government_note", "source", "source_url", "retrieved_at", "sha256", "license"]

def main():
    a = sys.argv[1:]; repo = a[0]; cog = a[a.index("--cog") + 1]; gaz = a[a.index("--gaz2020") + 1]; out = a[a.index("--out") + 1]
    retrieved = a[a.index("--retrieved") + 1]
    zp = os.path.join(os.path.dirname(cog), "govt_units_2022.ZIP")
    zsha = hashlib.sha256(open(zp, "rb").read()).hexdigest() if os.path.exists(zp) else hashlib.sha256(open(cog, "rb").read()).hexdigest()
    ws = openpyxl.load_workbook(cog, read_only=True)["General Purpose"]; it = ws.iter_rows(values_only=True); H = next(it)
    U = [dict(zip(H, r)) for r in it]
    county = {}; other = collections.defaultdict(list)
    for u in U:
        g = (u["FIPS_STATE"] or "") + (u["FIPS_COUNTY"] or "")
        if u["UNIT_TYPE"].startswith("1"):
            assert g not in county, g; county[g] = u
        else: other[g].append(u)
    F = {r["geoid"]: r for r in csv.DictReader(open(os.path.join(repo, "data-v3/geo/county_funcstat.csv")))}
    C = {r["geoid"]: r for r in csv.DictReader(open(os.path.join(repo, "data-v3/geo/counties.csv")))}
    src = "U.S. Census Bureau, 2022 Census of Governments: Organization, Government Units Listing (Govt_Units_2022_Final.xlsx, General Purpose)"
    rows = []; dis = []
    for g in sorted(F):
        f = F[g]; fs = f["tiger_funcstat"]; u = county.get(g)
        r = {"county_geoid": g, "vintage": "2024", "county_name": f["tiger_name"], "tiger_funcstat": fs, "source": src + "; cross-check TIGER 2024 FUNCSTAT (data-v3/geo/county_funcstat.csv)",
             "source_url": COG_URL, "retrieved_at": retrieved, "sha256": zsha, "license": "public domain (US government work)"}
        if u:
            r.update(has_own_government="yes", government_kind="county", cog_pid6=u["CENSUS_ID_PID6"], cog_unit_name=u["UNIT_NAME"], cog_unit_type=u["UNIT_TYPE"])
        else:
            r.update(has_own_government="no")
            cand = sorted(other.get(g, []), key=lambda x: -(x["POPULATION"] or 0))
            if fs in ("C", "B", "F") or fs == "A":
                if cand:
                    m = cand[0]; r.update(government_kind="municipal", cog_pid6=m["CENSUS_ID_PID6"], cog_unit_name=m["UNIT_NAME"], cog_unit_type=m["UNIT_TYPE"])
                    r["government_note"] = "CoG 2022 lists no county government; its largest general-purpose unit in this county area is %s (%s, population %s %s)" % (m["UNIT_NAME"], m["UNIT_TYPE"], m["POPULATION"], m["POPULATION_YEAR"])
                else:
                    r["government_kind"] = "none in this county area"
                    r["government_note"] = "CoG 2022 lists no county government and no general-purpose unit with this county code"
                    if g[:2] == "36": r["government_note"] += " (CoG lists the City of New York, PID6 %s, under county area 36061)" % next((x["CENSUS_ID_PID6"] for x in other.get("36061", []) if x["UNIT_NAME"] == "CITY OF NEW YORK"), "?")
            else:
                r["government_kind"] = "none"
                r["government_note"] = "CoG 2022 lists no county government (TIGER FUNCSTAT %s: %s)" % (fs, f["meaning"])
                if g[:2] == "09": r["government_note"] += "; Connecticut planning region, the county equivalent in data-v3 and v2 for 2024 and 2020; CoG 2022 already assigns CT towns to these region codes"
        agree = (fs == "A") == bool(u); r["agrees_with_tiger"] = "yes" if agree else "no"
        if g not in C: r["government_note"] = (r.get("government_note", "") + "; not in data-v3/geo/counties.csv").strip("; ")
        if not agree:
            dis.append({"county_geoid": g, "name": f["tiger_name"], "tiger_funcstat": fs, "cog_county_unit": u["UNIT_NAME"] if u else None, "cog_unit_cited": r.get("cog_unit_name") if not u else None})
            r["government_note"] = ((r.get("government_note") or "") + "; DISAGREES with TIGER FUNCSTAT %s; not resolved" % fs).strip("; ")
        rows.append(r)
    extra = set(county) - set(F)
    # 2020-vintage rows where the county set differs (TIGER 2020 Gazetteer)
    g20 = {}
    for r in csv.DictReader(open(gaz, encoding="latin-1"), delimiter="\t"):
        g20[r["GEOID"].strip()] = r["NAME"].strip()
    states = {g[:2] for g in F}   # 50 states + DC; Puerto Rico is outside data-v3/geo/counties.csv in both years
    only20 = sorted(g for g in set(g20) - set(F) if g[:2] in states); only24 = sorted(set(F) - set(g20))
    for g in only20:
        rows.append({"county_geoid": g, "vintage": "2020", "county_name": g20[g], "has_own_government": "no", "government_kind": "none",
                     "tiger_funcstat": "", "agrees_with_tiger": "", "government_note": ("Connecticut county of the 2020 vintage (TIGER 2020), replaced by the 9 planning regions in TIGER 2022+; "
                     "CoG 2022 lists no county government in Connecticut. 2020-vintage joins go town -> planning region (data-v3/geo/ALIGNMENT.md section 2)") if g[:2] == "09" else "county of the 2020 vintage only",
                     "source": src + "; TIGER 2020 Gazetteer counties", "source_url": COG_URL, "retrieved_at": retrieved, "sha256": zsha, "license": "public domain (US government work)"})
    with open(os.path.join(out, "county_government.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader()
        for r in rows: w.writerow({c: r.get(c, "") for c in COLS})
    S = {"rows": len(rows), "vintage_2024": sum(r["vintage"] == "2024" for r in rows), "vintage_2020_extra": only20, "only_2024_vs_2020_gazetteer": only24,
         "cog_county_units": len(county), "cog_county_units_not_in_tiger": sorted(extra),
         "has_own_government": dict(collections.Counter(r["has_own_government"] for r in rows if r["vintage"] == "2024")),
         "government_kind": dict(collections.Counter(r["government_kind"] for r in rows if r["vintage"] == "2024")),
         "tiger_A": sum(1 for f in F.values() if f["tiger_funcstat"] == "A"), "disagreements": dis}
    json.dump(S, open(os.path.join(out, "county_government_summary.json"), "w"), indent=1)
    print(json.dumps(S, indent=1))

if __name__ == "__main__":
    main()
