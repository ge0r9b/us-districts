import json, re, collections
from bs4 import BeautifulSoup
pages = json.load(open('bp/chambers/pages.json'))
res = {}
for k, title in pages.items():
    try: s = BeautifulSoup(open(f'bp/elections/{k}.html').read(), 'lxml')
    except FileNotFoundError: res[k] = None; continue
    h1 = s.find('h1'); 
    if not h1 or 'elections, 2026' not in h1.get_text(): res[k] = dict(page=False); continue
    tbl = None
    for t in s.find_all('table'):
        tr = t.find('tr')
        if tr and re.search(r'general election,? 2026', tr.get_text(' ', strip=True)): tbl = t; break
    dists = []; cands = []
    if tbl:
        hdr = None
        for r in tbl.find_all('tr'):
            cells = r.find_all(['th','td'])
            c = [x.get_text(' ', strip=True) for x in cells]
            if c and c[0] == 'Office': hdr = c; continue
            if not (hdr and len(c) >= 2 and c[0]): continue
            # cells may include an empty spacer cell after the office cell
            body = cells[1:]
            if len(body) == len(hdr): body = body[1:]
            slots = {}
            for h, cell in zip(hdr[1:], body):
                lst = []
                for el in cell.descendants:
                    if isinstance(el, str) and 'did not make' in el.lower(): break
                    if getattr(el, 'name', None) == 'span' and 'candidate' in (el.get('class') or []):
                        a = el.find('a'); txt = el.get_text(' ', strip=True)
                        pm = re.search(r'\(([^)]*)\)', txt.replace('(i)', ''))
                        lst.append(dict(name=a.get_text(' ', strip=True) if a else txt.replace('(i)', '').strip(),
                                        inc='(i)' in txt, bp=(a['href'].rstrip('/').split('/')[-1] if a and a.has_attr('href') else ''),
                                        party=pm.group(1) if pm else ''))
                if not lst:
                    for a in cell.find_all('a'):
                        if a.find('img') or '#' in (a.get('href') or '') or not a.get_text(strip=True): continue
                        nxt = a.next_sibling
                        inc = isinstance(nxt, str) and '(i)' in nxt
                        lst.append(dict(name=a.get_text(' ', strip=True), inc=inc, bp=a['href'].rstrip('/').split('/')[-1], party=''))
                slots[h] = lst
            dists.append(c[0]); cands.append(slots)
    txt = s.get_text(' ', strip=True)
    m = None; tot = None
    for t in s.find_all('table'):
        tr = t.find('tr')
        if tr and tr.get_text(' ', strip=True).lower().startswith('open seats in'):
            for r in t.find_all('tr'):
                c = [x.get_text(' ', strip=True) for x in r.find_all(['th','td'])]
                if c and c[0] == '2026': tot = c[1]
    m = re.search(r'(\d+) of the (\d+) seats', txt)
    res[k] = dict(page=True, districts=dists, candidates=cands, up_text=m.group(0) if m else None, open_table_total=tot)
    print(k, len(dists), tot, dists[:2], list(cands[0].keys()) if cands else None)
json.dump(res, open('bp_elections2026.json', 'w'), indent=0)
