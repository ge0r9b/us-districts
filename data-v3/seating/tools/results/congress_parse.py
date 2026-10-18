#!/usr/bin/env python3
"""Normalise US House / Senate returns 2016-2024 into one contest list.
Sources: FEC 'Federal Elections' xlsx 2016-2022 (House + Senate generals, LA/GA runoffs, special sheets),
House Clerk 'Statistics of the Presidential and Congressional Election' 2024 (House),
Election Data teammate rows (US Senate 2022/2024, read only). Output: src/results/congress_contests.json"""
import openpyxl, re, json, csv, collections, datetime
R = '/workspace/seating/src/results'
TM = '/workspace/w/lanes/election-data/data-v3/results'
GEN = {2016: '2016-11-08', 2018: '2018-11-06', 2020: '2020-11-03', 2022: '2022-11-08', 2024: '2024-11-05'}
RUNOFF = {2016: '2016-12-10', 2018: '2018-11-27', 2020: '2021-01-05', 2022: '2022-12-06'}   # LA Dec / MS 2018 / GA
contests = []
def num(x):
    if x is None: return None
    if isinstance(x, (int, float)): return x
    x = str(x).replace(',', '').strip()
    try: return float(x)
    except ValueError: return None
def col(hdr, *keys, avoid=()):
    for i, h in enumerate(hdr):
        h = str(h or '').upper()
        if all(k in h for k in keys) and not any(a in h for a in avoid): return i
    return None
def fec_sheet(rows, year, office, stage_default='general', date=None):
    hdr = rows[0]
    c = dict(st=col(hdr, 'STATE ABBREVIATION'), d=col(hdr, 'DISTRICT') if col(hdr, 'DISTRICT') is not None else 3, fid=col(hdr, 'FEC ID'),
             inc=col(hdr, '(I)'), name=col(hdr, 'CANDIDATE NAME', avoid=('(FIRST)', '(LAST)')), first=col(hdr, '(FIRST)'), last=col(hdr, '(LAST)'),
             party=col(hdr, 'PARTY', avoid=('COMBINED', 'TOTALS')), gv=col(hdr, 'GENERAL VOTES'), gp=col(hdr, 'GENERAL %'),
             rv=col(hdr, 'GE RUNOFF', 'VOTES'), comb=col(hdr, 'COMBINED', 'TOTALS'), win=col(hdr, 'GE', 'WINNER'), foot=col(hdr, 'FOOTNOTE'))
    if c['d'] is None or str(hdr[c['d']]).upper() not in ('D', 'DISTRICT'): c['d'] = 3
    groups = collections.OrderedDict()
    for r in rows[1:]:
        st = r[c['st']]
        if not st or len(str(st).strip()) != 2: continue
        d = str(r[c['d']] or '').strip()
        if not d or d == 'H': continue
        name = r[c['name']]; fid = str(r[c['fid']] or '').strip()
        if name in (None, '') or str(r[c['name']]).startswith(('Party Votes', 'Total')) or (r[9] and str(r[9]).startswith(('Party Votes', 'Total', 'District Votes'))): continue
        m = re.match(r'^(\d+|S)\s*-?\s*(FULL|UNEXPIRED|UNE|FUL)?', d.upper())
        dist = m.group(1) if m else d
        term = 'unexpired' if m and m.group(2) and m.group(2).startswith('UNE') else ''
        foot = str(r[c['foot']] or '') if c['foot'] is not None else ''
        key = (st.strip(), dist, term)
        fl = ' '.join(str(r[c[x]]).strip() for x in ('first', 'last') if c[x] is not None and r[c[x]])
        groups.setdefault(key, []).append(dict(fid=fid if fid not in ('n/a', 'None') else '', name=fl or str(name).strip(), party=str(r[c['party']] or '').strip(),
            gv=num(r[c['gv']]), gp=num(r[c['gp']]), rv=num(r[c['rv']]) if c['rv'] is not None else None, comb=num(r[c['comb']]) if c['comb'] is not None else None,
            win=str(r[c['win']] or '').strip() if c['win'] is not None else '', inc=bool(r[c['inc']]) if c['inc'] is not None else False,
            raw_gv=str(r[c['gv']] or ''), foot=foot))
    for (st, dist, term), lines in groups.items():
        for stage, vk in (('general', 'gv'), ('runoff', 'rv')):
            cand = collections.OrderedDict()
            for l in lines:
                v = l[vk]
                unopp = stage == 'general' and 'unopposed' in (l['raw_gv'] or '').lower()
                if v is None and not unopp: continue
                k = l['fid'] or l['name']
                if k not in cand:
                    cand[k] = dict(name=l['name'], fec=l['fid'], party=l['party'], parties=[l['party']], votes=v, inc=l['inc'],
                                   win=('W' in l['win'].upper()) if stage == 'general' else None, writein=l['name'].lower().startswith(('scatter', 'write', 'none of', 'blank', 'over', 'under')), unopposed=unopp)
                    if stage == 'general' and l['comb']: cand[k]['votes'] = l['comb']; cand[k]['combined'] = True
                else:
                    cand[k]['parties'].append(l['party'])
                    if not cand[k].get('combined') and v: cand[k]['votes'] = (cand[k]['votes'] or 0) + v
            if not cand: continue
            cl = [x for x in cand.values() if not x['name'].lower().startswith(('blank', 'over vote', 'under vote', 'void'))]
            # LA Nov 'general' is a jungle primary when a runoff follows; winner flag then belongs to the runoff
            if stage == 'runoff':
                mx = max(cl, key=lambda x: x['votes'] or 0); [x.__setitem__('win', x is mx) for x in cl]
            spec = 'special' if term == 'unexpired' else ''
            off = office if not (office == 'us_senate' and term == 'unexpired') else 'us_senate_special'
            contests.append(dict(year=year, date=(date or (GEN[year] if stage == 'general' else RUNOFF.get(year, ''))), stage=stage if not spec or stage == 'runoff' else 'general',
                                 special=bool(spec), office=off, st=st, district=dist, cands=cl, src=f'FEC Federal Elections {year}' + ('' if not date else ' (special sheet)')))
for y in (2016, 2018, 2020, 2022):
    wb = openpyxl.load_workbook(f'{R}/fec{y}.xlsx', read_only=True)
    for n in wb.sheetnames:
        rows = list(wb[n].iter_rows(values_only=True))
        if 'House Results' in n: fec_sheet(rows, y, 'us_house')
        elif 'Senate Results' in n: fec_sheet(rows, y, 'us_senate')
        elif 'Special Elections' in n or 'New Election' in n:
            # one sheet, House and Senate specials; date from footnote 'SPECIAL GENERAL ELECTION: m/d/yyyy'
            n0 = len(contests)
            fec_sheet(rows, y, 'us_house', date='x')
            for c in contests[n0:]:
                foot = ' '.join(x.get('foot', '') for x in c['cands']) if False else ''
            # re-read footnotes for dates
            byk = collections.defaultdict(str)
            hdr = rows[0]; fc = col(hdr, 'FOOTNOTE'); dc = 3
            for r in rows[1:]:
                if r[1] and fc is not None and r[fc]: byk[(str(r[1]).strip(), str(r[dc] or '').strip())] += ' ' + str(r[fc])
            for c in contests[n0:]:
                f = byk.get((c['st'], c['district']), '') or next((v for k, v in byk.items() if k[0] == c['st'] and k[1].upper().startswith(c['district'])), '')
                m = re.search(r'SPECIAL GENERAL ELECTION:\s*(\d+)/(\d+)/(\d{4})', f, re.I) or re.search(r'GENERAL ELECTION:\s*(\d+)/(\d+)/(\d{4})', f, re.I)
                c['date'] = datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2))).isoformat() if m else ''
                c['special'] = True; c['stage'] = 'special' if c['stage'] == 'general' else c['stage']
                if c['district'] == 'S': c['office'] = 'us_senate_special'
                c['year'] = int(c['date'][:4]) if c['date'] else y
                c['src'] = f'FEC Federal Elections {y} special-election sheet'
                if 'RUNOFF' in f.upper() and c['stage'] == 'runoff':
                    m = re.search(r'RUNOFF ELECTION:\s*(\d+)/(\d+)/(\d{4})', f, re.I)
                    if m: c['date'] = datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2))).isoformat()
# ---- 2024 House from the Clerk statistics
STATES = {}
for line in open('/workspace/seating/src/results/clerk2024.txt'): pass
import us_states_helper as H  # noqa (small helper below)
txt = open(f'{R}/clerk2024.txt').read().split('\n')
cur_st = None; sect = None; dist = None; cand = None; out = collections.OrderedDict()
NAMES = H.NAMES
for ln in txt:
    s = ln.strip()
    up = s.replace('—Continued', '').strip()
    if up in NAMES: cur_st = NAMES[up]; continue
    if s.startswith('FOR UNITED STATES REPRESENTATIVE'): sect = 'H'; continue
    if s.startswith('FOR UNITED STATES SENATOR'): sect = 'S'; continue
    if s.startswith('FOR PRESIDENTIAL') or s.startswith('Recapitulation') or s.startswith('FOR DELEGATE') or s.startswith('FOR RESIDENT'): sect = None; continue
    if sect != 'H' or not cur_st: continue
    if s in ('AT LARGE',): dist = '00'; continue
    m = re.match(r'^(\s*)(?:(\d+)\.\s+)?(.*?)\s*\.{3,}\s*([\d,]+|\(\d+\))$', ln)
    if not m: continue
    ind, dn, body = m.group(1), m.group(2), m.group(3).strip()
    v = None if m.group(4).startswith('(') else int(m.group(4).replace(',', ''))
    if dn: dist = f'{int(dn):02d}'
    if dist is None: continue
    k = (cur_st, dist); out.setdefault(k, [])
    low = body.lower()
    if low.startswith(('blank', 'void', 'over vote', 'under vote', 'overvote', 'undervote')): continue
    if ',' in body and not (len(ind) > 8 and not dn and out[k] and len(ind) > out[k][-1]['ind'] + 2):
        nm, pt = body.rsplit(',', 1) if not re.search(r',\s*(Jr|Sr|II|III|IV)\.?,', body) else (body.rsplit(',', 1))
        out[k].append(dict(name=nm.strip(), party=pt.strip(), parties=[pt.strip()], votes=v, ind=len(ind) + (len(dn) + 2 if dn else 0), writein=False))
    elif low.startswith(('write-in', 'scattering', 'write in', 'all others', 'others')):
        out[k].append(dict(name=body, party='W', parties=['W'], votes=v, ind=len(ind), writein=True))
    elif out[k]:   # fusion line: extra party line for previous candidate
        out[k][-1]['votes'] = (out[k][-1]['votes'] or 0) + (v or 0); out[k][-1]['parties'].append(body)
for (st, d), cl in out.items():
    if not cl: continue
    real = [x for x in cl if not x['writein']]
    mx = max(real, key=lambda x: x['votes'] or 0) if real else None
    for x in cl: x['win'] = x is mx; x.pop('ind', None); x['fec'] = ''; x['unopposed'] = x['votes'] is None
    contests.append(dict(year=2024, date=GEN[2024], stage='general', special=False, office='us_house', st=st, district=d, cands=cl, src='Clerk Statistics of the Presidential and Congressional Election 2024'))
# ---- Senate 2022 / 2024 from the teammate (state level rows, all candidates)
for y in (2022, 2024):
    g = collections.OrderedDict()
    for r in csv.DictReader(open(f'{TM}/{y}/senate/us_senate_{y}_state.csv')):
        g.setdefault((r['state'], r['office']), []).append(r)
    for (st, off), rows in g.items():
        cl = [dict(name=r['answer'], party=r['party'], parties=[r['party']], votes=float(r['votes']), candidate_id=r['candidate_id'],
                   writein=r['party'] in ('WRI', 'W') or r['answer'].lower().startswith(('write', 'scatter'))) for r in rows]
        real = [x for x in cl if not x['writein']]; mx = max(real, key=lambda x: x['votes'])
        for x in cl: x['win'] = x is mx
        runoff = off.endswith('_runoff')
        ccc = dict(year=y, date=(RUNOFF.get(y, '') if runoff else GEN[y]), stage='runoff' if runoff else 'general', special=off.startswith('us_senate_special'),
                   office='us_senate_special' if off.startswith('us_senate_special') else 'us_senate',
                   st=st, district='S', cands=cl, src=f'Election Data teammate data-v3/results/{y}/senate (official)', src_url=rows[0]['source_url'])
        contests.append(ccc)
json.dump(contests, open(f'{R}/congress_contests.json', 'w'))
print(collections.Counter((c['year'], c['office'], c['stage']) for c in contests))
