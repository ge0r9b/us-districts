#!/usr/bin/env python3
"""Parse Ballotpedia state-legislative district pages (cached .html.gz) into general-election results per year.
Output src/results/bp_district_results.json: {url: {chamber, office, elections:[{year, kind, title, date, cands:[{name, bp, party, pct, votes, win, inc}] , total}]}}"""
import gzip, json, os, re, sys
from bs4 import BeautifulSoup
from concurrent.futures import ProcessPoolExecutor
D = '/workspace/seating/src/bp/districts'
urls = json.load(open(f'{D}/urls.json'))
def fname(u): return f"{D}/" + re.sub(r'[^A-Za-z0-9_.-]', '_', u.split('/')[-1]) + '.html.gz'
def pnum(s):
    s = (s or '').replace(',', '').replace('%', '').strip()
    try: return float(s)
    except ValueError: return None
PARTY = re.compile(r'\(([A-Za-z.\- /]+)\)\s*$')
LA_MODE = [False]
def kind_of(title):
    t = title.lower()
    if LA_MODE[0] and 'primary' in t and 'democratic' not in t and 'republican' not in t:   # Louisiana jungle primary decides most seats
        return 'special' if 'special' in t else 'general'
    if LA_MODE[0] and ('general' in t or 'runoff' in t) and 'primary' not in t:
        return 'special_runoff' if 'special' in t else 'runoff'
    if 'primary' in t or 'convention' in t: return None
    if 'retention' in t: return 'retention'
    k = 'general'
    if 'runoff' in t: k = 'runoff'
    if 'special' in t: k = 'special' if k == 'general' else 'special_runoff'
    if 'general' not in t and 'special' not in t and 'runoff' not in t: return None
    return k
def votebox(v):
    h = v.select_one('.votebox-header-election-type')
    title = h.get_text(' ', strip=True) if h else ''
    k = kind_of(title)
    rt = ' '.join(p.get_text(' ', strip=True) for p in v.select('p.results_text'))
    if not k and re.search(r'\bwas (not )?retained\b', rt): k = 'retention'
    if not k and 'primary' in title.lower() and re.search(r'won election (outright|without)', rt): k = 'primary_decided'   # general canceled (e.g. OK)
    if not k: return None
    if k == 'retention' or 'Retention Vote' in v.get_text(' ', strip=True):
        m_ = re.match(r'^(.*?) was (not )?retained', rt); dm = re.search(r'on (\w+ \d{1,2}, \d{4})', rt)
        yes = no = None; yp = np_ = None; total = None
        for r in v.select('tr.results_row'):
            tx = [t_.get_text(' ', strip=True) for t_ in r.find_all('td')]
            if 'Yes' in tx: i = tx.index('Yes'); yp, yes = pnum(tx[i + 1]) if len(tx) > i + 1 else None, pnum(tx[i + 2]) if len(tx) > i + 2 else None
            elif 'No' in tx: i = tx.index('No'); np_, no = pnum(tx[i + 1]) if len(tx) > i + 1 else None, pnum(tx[i + 2]) if len(tx) > i + 2 else None
            elif any(x.startswith('Total Votes') for x in tx): total = pnum(tx[-1])
        a = None
        for p_ in v.select('p.results_text'):
            a = p_.find('a') or a
        nm = m_.group(1).strip() if m_ else (a.get_text(' ', strip=True) if a else '')
        return dict(kind='retention', title=title, date=dm.group(1) if dm else '', retained=not (m_ and m_.group(2)), judge=nm,
                    judge_bp=(a['href'].rstrip('/').split('/')[-1] if a and a.has_attr('href') else ''),
                    cands=[dict(name=nm, ans='yes', pct=yp, votes=yes), dict(name=nm, ans='no', pct=np_, votes=no)], total=total, fmt='votebox')
    txt = ' '.join(p.get_text(' ', strip=True) for p in v.select('p.results_text'))
    dm = re.search(r'on (\w+ \d{1,2}, \d{4})', txt)
    cands = []; total = None
    for r in v.select('tr'):
        cls = r.get('class') or []
        tds = r.find_all('td')
        tx = [t.get_text(' ', strip=True) for t in tds]
        if 'results_row' in cls:
            cell = r.select_one('td.votebox-results-cell--text')
            if not cell: continue
            a = cell.find('a'); name = a.get_text(' ', strip=True) if a else cell.get_text(' ', strip=True)
            full = cell.get_text(' ', strip=True)
            pm = PARTY.search(full.replace('(i)', ''))
            nums = [t.get_text(' ', strip=True) for t in r.select('td.votebox-results-cell--number')]
            pct = pnum(nums[0]) if nums else None; votes = pnum(nums[1]) if len(nums) > 1 else None
            cands.append(dict(name=name, bp=(a['href'].rstrip('/').split('/')[-1] if a and a.has_attr('href') and 'ballotpedia' in a['href'] else ''),
                              party=pm.group(1) if pm else '', pct=pct, votes=votes, win='winner' in cls or (tx and '✔' in tx[0]),
                              inc=bool(cell.find('u')), writein=name.lower().startswith('other/write-in')))
        m_ = re.search(r'Total votes:?\s*([\d,]+)', ' '.join(tx), re.I)
        if m_ and ('results_row' not in cls or any(t_.lower().startswith('total votes') for t_ in tx)):
            total = pnum(m_.group(1))
    # "This election was canceled/ uncontested" boxes without numbers still give winners
    return dict(kind=k, title=title, date=dm.group(1) if dm else '', cands=cands, total=total, fmt='votebox')
def bptable(t):
    cap = t.find('tr').get_text(' ', strip=True) if t.find('tr') else ''
    k = kind_of(cap)
    if not k: return None
    cands = []; total = None
    for r in t.find_all('tr')[1:]:
        tx = [c.get_text(' ', strip=True) for c in r.find_all(['td', 'th'])]
        if not tx: continue
        if tx[0].startswith('Total'):
            total = pnum(tx[-1]); continue
        if len(tx) >= 5 and tx[0] == '': tx = tx[1:]
        if len(tx) < 3 or tx[1] == 'Candidate': continue
        a = next((x for x in r.find_all('a') if x.has_attr('href') and x['href'] not in ('/Won', '/Incumbent') and not x.find('img')), None)
        name = a.get_text(' ', strip=True) if a else re.sub(r'\s*(Incumbent|\(unopposed\)).*$', '', tx[1]).strip()
        pct = next((pnum(x) for x in tx if x.endswith('%')), None)
        votes = pnum(tx[-1]) if not tx[-1].endswith('%') else None
        win = bool(r.find('img', alt=re.compile('Green check', re.I)))
        slug = a['href'].rstrip('/').split('/')[-1] if a else ''
        cands.append(dict(name=name, bp=slug, party=tx[0], pct=pct, votes=votes, win=win, inc='Incumbent' in ' '.join(tx), writein=name.lower().startswith(('write', 'scatter'))))
    if not cands: return None
    if not any(c['win'] for c in cands):   # bptables mark winners with an image in older pages; fall back to max votes
        m = max(cands, key=lambda c: c['votes'] or -1); m['win'] = True; m['win_inferred'] = True
    return dict(kind=k, title=cap, date='', cands=cands, total=total, fmt='bptable')
def rcvbox(v):
    h = v.select_one('.rcvrace_header'); title = h.get_text(' ', strip=True) if h else ''
    k = kind_of(title)
    if not k: return None
    cands = []
    for r in v.select('tr'):
        cell = r.select_one('td.votebox-results-cell--text')
        if not cell: continue
        a = cell.find('a'); name = a.get_text(' ', strip=True) if a else cell.get_text(' ', strip=True)
        nums = [t.get_text(' ', strip=True) for t in r.select('td.votebox-results-cell--number')]
        cands.append(dict(name=name, bp=(a['href'].rstrip('/').split('/')[-1] if a and a.has_attr('href') else ''), party='',
                          pct=pnum(nums[0]) if nums else None, votes=pnum(nums[1]) if len(nums) > 1 else None,
                          win=bool(nums) and nums[-1].startswith('Won'), inc=bool(cell.find('u')), writein=False))
    for r in v.select('tr'):
        c2 = r.select_one('td.votebox-results-cell-text')
        if c2 and 'write-in' in c2.get_text().lower():
            nums = [t.get_text(' ', strip=True) for t in r.select('td.votebox-results-cell--number')]
            cands.append(dict(name='Other/Write-in votes', bp='', party='', pct=pnum(nums[0]) if nums else None, votes=pnum(nums[1]) if len(nums) > 1 else None, win=False, inc=False, writein=True))
    return dict(kind=k, title=title, date='', cands=cands, total=None, fmt='rcv', note='ranked-choice: final-round votes')
def parse(item):
    u, (ck, off) = item
    fn = fname(u)
    if not os.path.exists(fn): return u, None
    s = BeautifulSoup(gzip.open(fn).read(), 'lxml')
    LA_MODE[0] = ck.startswith('LA_')
    el = s.find('span', id='Elections')
    out = []
    if not el: return u, dict(chamber=ck, office=off, elections=[], note='no Elections section')
    year = None
    for x in el.find_parent(['h2']).find_all_next():
        if x.name == 'h2': break
        if x.name == 'h3':
            m = re.match(r'^(\d{4})', x.get_text(strip=True)); year = int(m.group(1)) if m else year; continue
        if year is None or year < 2015 or year > 2025: continue
        e = None
        if x.name == 'div' and 'votebox' in (x.get('class') or []): e = votebox(x)
        elif x.name == 'div' and 'rcvvotebox' in (x.get('class') or []): e = rcvbox(x)
        elif x.name == 'p' and not x.find_parent('div', class_='votebox') and ('without appearing on the ballot' in x.get_text() or
                (re.search(r'general\s+election.{0,60}was\s+canceled', x.get_text(' ', strip=True)) and ' won ' in x.get_text(' ', strip=True))):
            txt_ = x.get_text(' ', strip=True)
            for sent in re.split(r'(?<=\.)\s+(?=[A-Z])', txt_):
                m_ = re.search(r'^(?:Incumbents?\s+)?(.+?)\s*(?:\(([A-Za-z. ]+)\)\s*)?won (?:the )?(?:election|without)', sent)
                if not m_ or 'primary' in sent.split(' won ')[-1][:40]: continue
                nm = m_.group(1).strip()
                a = next((a_ for a_ in x.find_all('a') if a_.get_text(' ', strip=True) and a_.get_text(' ', strip=True) in nm), None)
                e = dict(kind='unopposed', title='canceled election', date='', fmt='text', total=None,
                         cands=[dict(name=a.get_text(' ', strip=True) if a else nm, bp=(a['href'].rstrip('/').split('/')[-1] if a and a.has_attr('href') else ''),
                                     party=m_.group(2) or '', pct=None, votes=None, win=True, inc=sent.startswith('Incumbent'), writein=False)])
                e['year'] = year; out.append(e)
            e = None
        elif x.name == 'table' and 'bptable' in (x.get('class') or []): e = bptable(x)
        if e: e['year'] = year; out.append(e)
    # RCV boxes carry no party: take it from the same candidate in other boxes on the page (primaries)
    pm = {}
    for v in s.select('div.votebox'):
        for r in v.select('tr.results_row'):
            cell = r.select_one('td.votebox-results-cell--text')
            if not cell: continue
            a = cell.find('a'); full = cell.get_text(' ', strip=True); m_ = PARTY.search(full.replace('(i)', ''))
            if a and m_: pm.setdefault(a.get_text(' ', strip=True), m_.group(1))
    for e in out:
        for c in e['cands']:
            if c.get('party'): pm.setdefault(c['name'], c['party'])
    for e in out:
        if e['fmt'] == 'rcv':
            for c in e['cands']: c['party'] = c['party'] or pm.get(c['name'], '')
    return u, dict(chamber=ck, office=off, elections=out)
if __name__ == '__main__':
    res = {}
    with ProcessPoolExecutor(8) as ex:
        for u, r in ex.map(parse, urls.items(), chunksize=20):
            if r is not None: res[u] = r
    json.dump(res, open('/workspace/seating/src/results/bp_district_results.json', 'w'))
    import collections
    c = collections.Counter((e['year'], e['kind'], e['fmt']) for r in res.values() for e in r['elections'])
    print(len(res), sorted(c.items()))
