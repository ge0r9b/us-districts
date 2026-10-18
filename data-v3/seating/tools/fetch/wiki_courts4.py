import json, re, unicodedata
from bs4 import BeautifulSoup
bp = json.load(open('bp_courts.json'))
def norm(s): return unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode().lower()
res = {}
for k in bp:
    s = BeautifulSoup(open(f'wiki/courts/{k}.html').read(), 'lxml')
    surn = [norm(r['name']).replace(' jr.','').replace(',','').split()[-1] for r in bp[k]['rows'] if r['name'] != 'Vacant']
    best = None; bestscore = 0
    for t in s.find_all('table'):
        txt = norm(t.get_text(' '))
        sc = sum(1 for x in surn if x in txt)
        rows = t.find_all('tr')
        h0 = norm(rows[0].get_text(' ')) if rows else ''
        if sc > bestscore and len(rows) <= 25 and 'name' in h0: best, bestscore = t, sc
    if not best: res[k] = None; continue
    rows = best.find_all('tr')
    def clean(x): return re.sub(r'\[.*?\]', '', x.get_text(' ', strip=True)).strip()
    hdr = [clean(c) for c in rows[0].find_all(['th','td'])]
    pending = {}  # col -> (text, remaining)
    out = []
    for r in rows[1:]:
        cells = r.find_all(['th','td']); grid = []; ci = 0; col = 0
        while col < len(hdr):
            if col in pending:
                txt, rem = pending[col]; grid.append(txt)
                if rem <= 1: del pending[col]
                else: pending[col] = (txt, rem - 1)
                col += 1; continue
            if ci >= len(cells): break
            c = cells[ci]; ci += 1
            txt = clean(c); rs = int(c.get('rowspan', 1) or 1); cs = int(c.get('colspan', 1) or 1)
            for _ in range(cs):
                grid.append(txt)
                if rs > 1: pending[col] = (txt, rs - 1)
                col += 1
        if len(grid) == len(hdr): out.append(dict(zip(hdr, grid)))
    res[k] = dict(headers=hdr, rows=out, score=bestscore, n=len(surn))
json.dump(res, open('wiki_court_tables.json','w'), indent=1)
for k, v in res.items():
    print(k, v and v['score'], v and v['n'], v and v['headers'][:9], v and sum('_cells' in r for r in v['rows']))
