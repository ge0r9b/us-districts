"""Apply the approved county-table fixes to data/election2020.js and data/election2024.js in place.
Only the listed entries are rewritten; key order and compact format stay the same.
  OR 2024        : Oregon SOS official abstract of votes (rows in table_fix_proposals.csv)
  KS, RI 2020    : VEST 2020 county sums (d, r, t), which match certified statewide
  NY 2020        : VEST 2020 county d and r (fusion included) where they differ; t = v2 t + Δd + Δr
                   (VEST NY totals include blank/void in some counties, so v2's other-candidate votes are kept)
  ME 2020        : ME SOS official town results (presandvisecnty1120.xlsx) summed by county;
                   the 'STATE UOCAVA' line is not assigned to any county (see TABLE_FIXES_APPLIED.md)
  VA 2024        : unchanged
Prints before/after statewide sums of the county table."""
import csv, json, re, sys, collections, openpyxl
ROOT = sys.argv[1] if len(sys.argv) > 1 else '.'
H = ROOT + '/data-v3/results/states/'
fix = {2020: {}, 2024: {}}
for r in csv.DictReader(open(H + 'table_fix_proposals.csv')):
    y, st = int(r['year']), r['state']
    if st == 'Maine': continue   # ME comes from the official town file below, not VEST
    v = [int(r['v2_d']), int(r['v2_r']), int(r['v2_t'])]; p = [int(r['proposed_d']), int(r['proposed_r']), int(r['proposed_t'])]
    if st in ('Kansas', 'Rhode Island', 'Oregon'): fix[y][f'{st}|{r["county"]}'] = p
    elif st == 'New York' and (p[0] != v[0] or p[1] != v[1]):
        fix[y][f'{st}|{r["county"]}'] = [p[0], p[1], v[2] + (p[0] - v[0]) + (p[1] - v[1])]
CTY = dict(AND='Androscoggin', ARO='Aroostook', CUM='Cumberland', FRA='Franklin', HAN='Hancock', KEN='Kennebec', KNO='Knox',
           LIN='Lincoln', OXF='Oxford', PEN='Penobscot', PIS='Piscataquis', SAG='Sagadahoc', SOM='Somerset', WAL='Waldo', WAS='Washington', YOR='York')
ws = openpyxl.load_workbook(ROOT + '/data-v3/results/ME/raw/presandvisecnty1120.xlsx', data_only=True)['Statewide']
me = collections.defaultdict(lambda: [0, 0, 0])
for r in list(ws.iter_rows(values_only=True))[3:]:
    if r[0] in CTY and r[1]:
        a = me[r[0]]; a[0] += r[2]; a[1] += r[6]; a[2] += sum(r[2:8])   # Biden, Trump, all candidates incl. Others (write-ins); Blank excluded
for c, a in me.items(): fix[2020][f'Maine|{CTY[c]} County'] = a
for y in (2020, 2024):
    fn = f'{ROOT}/data/election{y}.js'; s = open(fn).read()
    d = json.loads(s[s.index('{'):s.rindex('}') + 1])
    def tot(st): return [sum(v[i] for k, v in d.items() if k.split('|')[0] == st) for i in range(3)]
    states = sorted({k.split('|')[0] for k in fix[y]}); before = {st: tot(st) for st in states}
    n = 0
    for k, v in fix[y].items():
        assert k in d, k
        if d[k] == v: continue
        pat = re.compile(re.escape(json.dumps(k)) + r':\[[^\]]*\]')
        s, c = pat.subn(json.dumps(k) + ':' + json.dumps(v, separators=(',', ':')), s); assert c == 1, k
        d[k] = v; n += 1
    open(fn, 'w').write(s)
    for st in states: print(y, st, 'before', before[st], 'after', tot(st))
    print(y, 'entries changed', n)
