import json, re
from bs4 import BeautifulSoup
pages = json.load(open('bp/courts/pages.json'))
res = {}
for k, title in pages.items():
    s = BeautifulSoup(open(f'bp/courts/{k}.html').read(), 'lxml')
    txt = s.get_text(' ', strip=True)
    m = re.search(r'Selection Method:\s*\*?\s*(.*?)\s+Term:\s*(.*?)\s+Active justices', txt)
    tbl = None
    for t in s.find_all('table'):
        tr = t.find('tr')
        if not tr: continue
        h = [c.get_text(' ', strip=True) for c in tr.find_all(['th','td'])]
        if h[:3] == ['Office','Name','Party']: tbl = t; break
    rows = []
    if tbl:
        for r in tbl.find_all('tr')[1:]:
            c = [x.get_text(' ', strip=True) for x in r.find_all(['td','th'])]
            a = r.find_all(['td','th'])[1].find('a') if len(c) > 1 else None
            if len(c) >= 4: rows.append(dict(office=c[0], name=c[1], party=c[2], since=c[3], appointed_by=c[4] if len(c) > 4 else '', link=a['href'] if a and a.has_attr('href') else None))
    chief = re.search(r'The (?:current )?chief (?:justice|judge|of the court) (?:of the court )?is ([A-Z][^.\[]+?)\s*[.\[]', txt)
    asof = re.search(r'As of ([A-Z][a-z]+ \d{4}), ([^.]+)\.', txt)
    res[k] = dict(title=title, method=m.group(1) if m else None, term=m.group(2) if m else None, rows=rows,
                  chief=chief.group(1).strip() if chief else None, summary=(asof.group(0) if asof else None))
    print(k, '|', res[k]['method'], '|', res[k]['term'], '|', len(rows), '|', res[k]['chief'], '|', [ (r['party'], r['appointed_by']) for r in rows][:9])
json.dump(res, open('bp_courts.json','w'), indent=1)
