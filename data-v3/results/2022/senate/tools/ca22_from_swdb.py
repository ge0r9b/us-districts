#!/usr/bin/env python3
"""MEDSL's CA 2022 file has no US Senate rows. Convert the California Statewide Database 2022 general SOV by SRPREC
(state_g22_sov_data_by_g22_srprec.csv; USSDEM01/USSREP01 = full term, USPDEM01/USPREP01 = unexpired term; top-two, 2 candidates)
into MEDSL-format rows. jurisdiction_name = county name as in MEDSL 2024 CA (so keys line up with the 2024 bridge).
usage: ca22_from_swdb.py <swdb_csv> <medsl24_ca_csv> <out_csv>"""
import sys, csv
src, m24, out = sys.argv[1:4]
J = {}
for r in csv.DictReader(open(m24, encoding='utf-8', errors='replace')):
    J.setdefault(r['county_fips'], r['jurisdiction_name'])
    if len(J) >= 58: break
C = {'USSDEM01': ('FALSE', 'ALEX PADILLA', 'DEMOCRAT'), 'USSREP01': ('FALSE', 'MARK P MEUSER', 'REPUBLICAN'),
     'USPDEM01': ('TRUE', 'ALEX PADILLA', 'DEMOCRAT'), 'USPREP01': ('TRUE', 'MARK P MEUSER', 'REPUBLICAN')}
w = csv.writer(open(out, 'w', newline='')); w.writerow(['precinct','office','party_simplified','mode','votes','county_fips','jurisdiction_name','candidate','district','special','stage'])
for r in csv.DictReader(open(src)):
    for col, (sp, cand, party) in C.items():
        w.writerow([r['SRPREC'], 'US SENATE', party, 'TOTAL', r[col] or 0, r['FIPS'], J.get(r['FIPS'], ''), cand, 'STATEWIDE', sp, 'GEN'])
