import json, re, unicodedata
from bs4 import BeautifulSoup
bp = json.load(open('bp_courts.json'))
def norm(s): return unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode().lower()
out = {}
for k in bp:
    s = BeautifulSoup(open(f'wiki/courts/{k}.html').read(), 'lxml')
    sec = None
    for sect in s.find_all('section'):
        h = sect.find(['h2','h3'])
        if h and re.search(r'current|composition|^justices$|^judges$|members|membership', h.get_text(strip=True), re.I) and sect.find('table'):
            sec = sect; break
    if sec is None:
        out[k] = dict(section=None); print(k, 'NO SECTION'); continue
    tbl = sec.find('table'); txt = norm(tbl.get_text(' '))
    rows = [r for r in tbl.find_all('tr') if r.find('td')]
    missing = [r['name'] for r in bp[k]['rows'] if r['name'] != 'Vacant' and norm(r['name']).replace(' jr.','').replace(',','').split()[-1] not in txt]
    nbp = len([r for r in bp[k]['rows'] if r['name'] != 'Vacant'])
    out[k] = dict(section=sec.find(['h2','h3']).get_text(strip=True), wiki_rows=len(rows), bp_filled=nbp, missing_in_wiki=missing, table_text=tbl.get_text(' | ', strip=True)[:3000])
    flag = '' if (len(rows) == nbp and not missing) else '  <<<'
    print(k, out[k]['section'], 'wiki', len(rows), 'bp', nbp, missing, flag)
json.dump(out, open('wiki_courts_check.json','w'), indent=1)
