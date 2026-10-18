import json, re, unicodedata
from bs4 import BeautifulSoup
bp = json.load(open('bp_courts.json'))
def norm(s): return unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode().lower()
res = {}
for k in bp:
    s = BeautifulSoup(open(f'wiki/courts/{k}.html').read(), 'lxml')
    best = None
    for t in s.find_all('table'):
        tr = t.find('tr')
        if not tr: continue
        hdr = [norm(c.get_text(' ', strip=True)) for c in tr.find_all(['th','td'])]
        if any('appoint' in h for h in hdr) and any(h.startswith('name') or h in ('justice','judge') for h in hdr):
            best = (t, hdr); break
    if not best: res[k] = None; continue
    t, hdr = best
    ai = [i for i,h in enumerate(hdr) if 'appoint' in h][0]
    pi = [i for i,h in enumerate(hdr) if h.startswith('party')]
    ni = [i for i,h in enumerate(hdr) if h.startswith('name') or h in ('justice','judge')][0]
    rows = {}
    for r in t.find_all('tr')[1:]:
        c = r.find_all(['td','th'])
        if len(c) < len(hdr) - 2: continue
        # rowspans/place columns can shift; align from right if count differs
        off = len(c) - len(hdr)
        def g(i):
            j = i + off if i > ni else i
            return c[j].get_text(' ', strip=True) if 0 <= j < len(c) else ''
        nm = c[ni + (0 if off >= 0 else 0)].get_text(' ', strip=True) if ni < len(c) else ''
        # find name cell: first cell that contains a link and letters
        cand = [x for x in c if x.find('a') and re.search(r'[A-Za-z]{3}', x.get_text())]
        if cand: nm = cand[0].get_text(' ', strip=True) if not re.match(r'^\d', cand[0].get_text(strip=True)) else (cand[1].get_text(' ', strip=True) if len(cand) > 1 else nm)
        nm = re.sub(r'\s*,.*$', '', nm)
        rows[nm] = dict(appointer=re.sub(r'\[.*?\]', '', g(ai)).strip(), party=g(pi[0]) if pi else None)
    res[k] = rows
json.dump(res, open('wiki_court_tables.json','w'), indent=1)
for k in ['MT_SC','KY_SC','WI_SC','MS_SC','NV_SC','WA_SC','ID_SC','GA_SC','AR_SC','MI_SC','PA_SC','LA_SC','MN_SC']:
    print(k, res.get(k))
