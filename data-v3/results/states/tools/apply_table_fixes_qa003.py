#!/usr/bin/env python3
"""QA-003 follow-up: county-table fixes in v2/data/election2020.js / election2024.js from official certified county data.
Root data/ is v1 and never changes. Only entries whose D or R differ from the official figure are rewritten (key order and format kept).
  PA 2020 Allegheny : PA Department of State certified (data-v3/results/PA/pa_president_county_official.csv), orchestrator-approved
  CA 2020           : CA SOS Statement of Vote, President by County (18-presidential.xlsx)
  WI 2020           : WEC County by County Report, President, post recount (Dane, Milwaukee)
  AL 2020           : AL SOS Final Canvass of Results, pages 3-4 (President)
  IN 2020           : Indiana Election Division final results, AllOfficeResults.csv (precinct rows where a county has them, else the county row)
  MA 2024           : MA Secretary of the Commonwealth electionstats, President by city/town (election 165300), towns -> counties
                      via v2/data/precincts2024/Massachusetts.js (+ fixed list for towns whose names differ or are split there)
t rule: WI, AL and IN list every candidate (write-ins included) and v2's totals there already equal those all-candidate totals,
so t = the official total. CA and MA: v2's totals leave out some write-ins in every county, and PA DOS lists only 3 candidates,
so t = v2 t + Δd + Δr (the same rule as NY 2020), which keeps each state's totals on one basis.
Writes ../qa003_official_counties.csv (official d, r, t of every county compared) and prints before/after statewide sums.
usage: apply_table_fixes_qa003.py <repo> <raw_dir>"""
import sys, os, re, csv, json, collections, subprocess, openpyxl
repo, raw = sys.argv[1:3]
OFF = {}   # (year, 'State|County') -> (d, r, t, rule)
# PA
pa = collections.defaultdict(lambda: [0, 0, 0])
for r in csv.DictReader(open(f'{repo}/data-v3/results/PA/pa_president_county_official.csv')):
    if r['year'] == '2020' and r['unit_id'] == '42003':
        a = pa['x']; v = int(r['votes']); a[2] += v
        if r['party'] == 'DEM': a[0] += v
        if r['party'] == 'REP': a[1] += v
OFF[(2020, 'Pennsylvania|Allegheny County')] = (*pa['x'], 'delta')
# CA
ws = openpyxl.load_workbook(f'{raw}/ca20_18-presidential.xlsx', data_only=True).active
for r in ws.iter_rows(values_only=True):
    if r[0] and isinstance(r[1], (int, float)) and 'Total' not in str(r[0]):
        OFF[(2020, f'California|{r[0].strip()} County')] = (r[1], r[2], sum(x for x in r[1:] if isinstance(x, (int, float))), 'delta')
# WI (post-recount PDF: total, Biden, Trump, ...)
t = subprocess.run(['pdftotext', '-layout', f'{raw}/wi20_post_recount.pdf', '-'], capture_output=True, text=True).stdout
for line in t.splitlines():
    m = re.match(r'^\s*(DANE|MILWAUKEE)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s', line)
    if m:
        n = [int(x.replace(',', '')) for x in m.groups()[1:]]
        OFF[(2020, f'Wisconsin|{m.group(1).title()} County')] = (n[1], n[2], n[0], 'official')
# AL (Biden, Trump, Jorgensen, Write-in, Jones, Tuberville, Write-in)
t = subprocess.run(['pdftotext', '-layout', '-f', '3', '-l', '4', f'{raw}/al20_final_canvass.pdf', '-'], capture_output=True, text=True).stdout
for line in t.splitlines():
    m = re.match(r'^\s*([A-Z][A-Za-z\. ]+?)\s{2,}([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$', line)
    if m and m.group(1) != 'Total':
        n = [int(x.replace(',', '')) for x in m.groups()[1:]]
        OFF[(2020, f'Alabama|{m.group(1).strip()} County')] = (n[0], n[1], n[0] + n[1] + n[2] + n[3], 'official')
# IN
rows = [r for r in csv.DictReader(open(f'{raw}/in20_AllOfficeResults.csv', encoding='utf-8-sig', errors='replace')) if r['OfficeCategory'].startswith('President')]
lv = collections.defaultdict(collections.Counter)
for r in rows: lv[r['ReportingCountyName']][r['DataEntryLevelName']] += int(r['TotalVotes'] or 0)
ina = collections.defaultdict(lambda: [0, 0, 0])
for r in rows:
    c = r['ReportingCountyName']
    if r['DataEntryLevelName'] != ('Precinct' if lv[c]['Precinct'] > 0 else 'Locality'): continue
    v = int(r['TotalVotes'] or 0); a = ina[c]; a[2] += v
    if 'Biden' in r['NameonBallot']: a[0] += v
    if 'Trump' in r['NameonBallot']: a[1] += v
FIXN = {'Lagrange': 'LaGrange', 'Laporte': 'LaPorte', 'Dekalb': 'DeKalb'}
for c, a in ina.items(): OFF[(2020, f'Indiana|{FIXN.get(c, c)} County')] = (*a, 'official')
# MA
tt = open(f'{repo}/v2/data/precincts2024/Massachusetts.js').read(); V = json.JSONDecoder().raw_decode(tt, tt.index('[['))[0]
T2C = collections.defaultdict(set)
for r in V: T2C[re.sub(r'\s+(Precinct|Ward)\b.*$', '', r[1]).strip().upper()].add(r[0])
MAFIX = {'BOSTON': 'Suffolk', 'CAMBRIDGE': 'Middlesex', 'NEWTON': 'Middlesex', 'MILTON': 'Norfolk', 'AQUINNAH': 'Dukes', 'CHILMARK': 'Dukes',
         'EDGARTOWN': 'Dukes', 'GOSNOLD': 'Dukes', 'OAK BLUFFS': 'Dukes', 'TISBURY': 'Dukes', 'WEST TISBURY': 'Dukes', 'NANTUCKET': 'Nantucket',
         'EASTHAM': 'Barnstable', 'PROVINCETOWN': 'Barnstable', 'WELLFLEET': 'Barnstable', 'MARION': 'Plymouth'}
num = lambda x: int(x.replace(',', '')) if x else 0
maa = collections.defaultdict(lambda: [0, 0, 0])
for r in list(csv.reader(open(f'{raw}/ma24_president_by_town.csv')))[2:]:
    if not r or r[0] == 'TOTALS': continue
    u = re.sub(r'^([ENSW])\. ', lambda m: {'E': 'EAST ', 'N': 'NORTH ', 'S': 'SOUTH ', 'W': 'WEST '}[m.group(1)], r[0].upper())
    c = MAFIX[u] + ' County' if u in MAFIX else (next(iter(T2C[u])) if len(T2C.get(u, ())) == 1 else None)
    assert c, r[0]
    a = maa[c]; a[0] += num(r[3]); a[1] += num(r[4]); a[2] += sum(num(x) for x in r[3:12])   # candidates + All Others; Blanks excluded
for c, a in maa.items(): OFF[(2024, f'Massachusetts|{c}')] = (*a, 'delta')
with open(f'{repo}/data-v3/results/states/qa003_official_counties.csv', 'w', newline='') as f:
    w = csv.writer(f, lineterminator='\n'); w.writerow(['year', 'key', 'official_d', 'official_r', 'official_t', 't_rule'])
    for (y, k), v in sorted(OFF.items()): w.writerow([y, k, *v])
for y in (2020, 2024):
    fn = f'{repo}/v2/data/election{y}.js'; s = open(fn).read(); d = json.loads(s[s.index('{'):s.rindex('}') + 1])
    tot = lambda st: [sum(v[i] for k, v in d.items() if k.split('|')[0] == st) for i in range(3)]
    states = sorted({k.split('|')[0] for (yy, k) in OFF if yy == y}); before = {st: tot(st) for st in states}; n = 0
    for (yy, k), (od, orr, ot, rule) in OFF.items():
        if yy != y: continue
        assert k in d, k
        v = d[k]
        if v[0] == od and v[1] == orr: continue
        nv = [od, orr, ot if rule == 'official' else v[2] + (od - v[0]) + (orr - v[1])]
        pat = re.compile(re.escape(json.dumps(k)) + r':\[[^\]]*\]')
        s, c = pat.subn(json.dumps(k) + ':' + json.dumps(nv, separators=(',', ':')), s); assert c == 1, k
        print(y, k, v, '->', nv); d[k] = nv; n += 1
    open(fn, 'w').write(s)
    for st in states: print(y, st, 'before', before[st], 'after', tot(st))
    print(y, 'entries changed', n)
