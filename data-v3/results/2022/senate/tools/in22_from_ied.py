#!/usr/bin/env python3
"""MEDSL's IN 2022 file has Senate rows for only 39 of 92 counties. Convert the Indiana Election Division's final 2022
general results (enr.indianavoters.in.gov archive, download/AllOfficeResults.csv; OfficeCategory 'US Senator') into
MEDSL-format rows. 35 counties report by precinct (DataEntryLevelName 'Precinct'); 57 report only a county total ('Locality').
Precinct rows keep their precinct name (upper case, as in MEDSL 2024). A county-total row gets jurisdiction and precinct
'COUNTY TOTAL', so it never bridges to a polygon and build_sen2022.py allocates it over the county's polygons (≈ in districts).
Precinct rows in Cass, Daviess, Monroe and Scott are all 0 (those counties report the county total), so they are dropped.
usage: in22_from_ied.py <AllOfficeResults.csv> <repo> <out_csv>"""
import sys, csv, collections
src, repo, out = sys.argv[1:4]
F = {}
for r in csv.DictReader(open(f'{repo}/data-v3/geo/counties.csv')):
    if r['state'] == 'Indiana': F[r['v2_name'].replace(' County', '').upper().replace('.', '').replace(' ', '')] = r['geoid']
rows = [r for r in csv.DictReader(open(src, encoding='utf-8-sig', errors='replace')) if r['OfficeCategory'] == 'US Senator']
lvl = collections.defaultdict(lambda: collections.Counter())
for r in rows: lvl[r['ReportingCountyName']][r['DataEntryLevelName']] += int(r['TotalVotes'] or 0)
w = csv.writer(open(out, 'w', newline='')); w.writerow(['precinct','office','party_simplified','mode','votes','county_fips','jurisdiction_name','candidate','district','special','stage','county_name'])
tot = 0; npc = set(); seen = set()
for r in rows:
    c = r['ReportingCountyName']; lv = r['DataEntryLevelName']
    use = 'Precinct' if lvl[c]['Precinct'] > 0 else 'Locality'
    if lv != use: continue
    key = (c, r['DataEntryJurisdictionName'], r['NameonBallot'], r['TotalVotes'])
    if key in seen: continue          # the file repeats some write-in lines verbatim (all 0 so far); keep one
    seen.add(key)
    fips = F[c.upper().replace('.', '').replace(' ', '')]
    pr = r['DataEntryJurisdictionName'].upper() if use == 'Precinct' else 'COUNTY TOTAL'
    jur = c.upper() if use == 'Precinct' else 'COUNTY TOTAL'
    party = {'Democratic': 'DEMOCRAT', 'Republican': 'REPUBLICAN'}.get(r['PoliticalParty'], 'OTHER')
    v = int(r['TotalVotes'] or 0); tot += v
    if use == 'Precinct': npc.add(c)
    w.writerow([pr, 'US SENATE', party, 'TOTAL', v, fips, jur, r['NameonBallot'].upper().replace('.', '').replace(',', ''), 'STATEWIDE', 'FALSE', 'GEN', c.upper()])
print('votes', tot, 'precinct counties', len(npc), 'county-total counties', len(lvl) - len(npc))
