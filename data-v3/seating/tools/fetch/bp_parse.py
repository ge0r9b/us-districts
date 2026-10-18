import json, re, collections
from bs4 import BeautifulSoup
pages = json.load(open('bp/chambers/pages.json'))
res = {}
for key, title in pages.items():
    s = BeautifulSoup(open(f'bp/chambers/{key}.html').read(), 'lxml')
    tbl = None
    for t in s.find_all('table'):
        hdr = [c.get_text(' ', strip=True) for c in t.find('tr').find_all(['th','td'])]
        if hdr[:3] == ['Office', 'Name', 'Party']: tbl = t; break
    if tbl is None:
        res[key] = None; print(key, 'NO TABLE'); continue
    rows = []
    for r in tbl.find_all('tr')[1:]:
        c = r.find_all(['td','th'])
        if len(c) < 3: continue
        office = c[0].get_text(' ', strip=True); name = c[1].get_text(' ', strip=True)
        party = c[2].get_text(' ', strip=True); since = c[3].get_text(' ', strip=True) if len(c) > 3 else ''
        a = c[1].find('a'); link = a['href'] if a and a.has_attr('href') else None
        dist = re.sub(r'^.*?(Senate|House of Representatives|Assembly|House of Delegates|General Assembly|Legislature)\s*', '', office).strip()
        dist = re.sub(r'^District\s+', '', dist)
        rows.append(dict(office=office, district=dist, name=name, party=party, since=since, link=link))
    # "as of" / composition box text
    txt = s.get_text(' ', strip=True)
    res[key] = dict(title=title, rows=rows)
    pc = collections.Counter(r['party'] for r in rows)
    print(key, len(rows), dict(pc))
json.dump(res, open('bp_chambers.json', 'w'), indent=0)
