#!/usr/bin/env python3
"""MEDSL's ID 2022 Senate rows sum to ~2x the official total. Convert the Idaho Secretary of State 2022 general canvass,
'22 General Statewide - Precinct.xlsx' sheet 'US Sen' (from 2022_General_Canvass.zip), into MEDSL-format rows.
County header rows, 'CO. TOTAL' / 'GRAND TOTAL' and repeated page headers are skipped. county_fips / jurisdiction_name are
taken from MEDSL's ID 2022 file so keys line up with the 2024 bridge. The SOS sheet has no write-in column.
usage: id22_from_sos.py <precinct_xlsx> <medsl22_id_csv> <out_csv>"""
import sys, csv, openpyxl
src, m22, out = sys.argv[1:4]
J = {}
for r in csv.DictReader(open(m22, encoding='utf-8', errors='replace')):
    J.setdefault(r['county_name'].upper(), (r['county_fips'], r['jurisdiction_name']))
rows = list(openpyxl.load_workbook(src, read_only=True, data_only=True)['US Sen'].iter_rows(values_only=True))
hdr = next(r for r in rows if r[0] == 'Precinct'); par = rows[rows.index(hdr) - 1]
cands = [(i, str(hdr[i]).upper().replace('.', ''), {'DEM':'DEMOCRAT','REP':'REPUBLICAN'}.get(par[i], 'OTHER')) for i in range(1, len(hdr)) if hdr[i]]
w = csv.writer(open(out, 'w', newline='')); w.writerow(['precinct','office','party_simplified','mode','votes','county_fips','jurisdiction_name','candidate','district','special','stage','county_name'])
cty = None; n = 0; tot = 0
for r in rows:
    nm = str(r[0]).strip() if r[0] is not None else ''
    vals = [r[i] if i < len(r) else None for i, _, _ in cands]
    if nm and all(v is None for v in vals):
        c = nm.split(',')[0].strip().upper()
        if c in J: cty = c
        continue
    if not nm or nm == 'Precinct' or 'TOTAL' in nm.upper() or cty is None: continue
    if not any(isinstance(v, (int, float)) for v in vals): continue
    for (i, cand, party), v in zip(cands, vals):
        w.writerow([nm, 'US SENATE', party, 'TOTAL', int(v or 0), J[cty][0], J[cty][1], cand, 'STATEWIDE', 'FALSE', 'GEN', cty]); tot += int(v or 0)
    n += 1
print('precincts', n, 'votes', tot)
