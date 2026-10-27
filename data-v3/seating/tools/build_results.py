#!/usr/bin/env python3
"""Match every seat with general-election results 2016-2024 (+ odd-year state/court elections, specials, runoffs, retention),
and back-fill the holder timeline for state chambers and courts.
Inputs: v3data/base/*.csv (from build_v3data.py), src/results/* (FEC, Clerk, teammate Senate rows, Klarner SLERs, Ballotpedia district
and court pages). Outputs (v3data/): results_contests.csv, results_candidates.csv, people.csv (extended, ids stable), terms.csv
(back-filled), bodies.csv (complete_from updated), topics.json, results_crosscheck.csv, results_coverage.csv."""
import csv, json, re, os, gzip, glob, collections, datetime, unicodedata, sys
import pandas as pd
from bs4 import BeautifulSoup
OUT = '/workspace/seating/v3data'; SRC = '/workspace/seating/src'; R = f'{SRC}/results'
TM = '/workspace/w/lanes/election-data/data-v3/results'
sys.path.insert(0, os.path.dirname(__file__))
from geo_match import match as geo_match
def rd(n): return list(csv.DictReader(open(f'{OUT}/base/{n}')))
bodies = rd('bodies.csv'); seats_rows = rd('seats.csv'); people_rows = rd('people.csv'); base_terms = rd('terms.csv')
BK = {b['key']: int(b['b']) for b in bodies}; BODY = {int(b['b']): b for b in bodies}
SEATS = collections.defaultdict(list)
for r in seats_rows: SEATS[int(r['b'])].append(r)
def norm(s): return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
ORD = {'first': '1', 'second': '2', 'third': '3', 'fourth': '4', 'fifth': '5', 'sixth': '6', 'seventh': '7', 'eighth': '8', 'ninth': '9'}
STOPT = {'district', 'and', 'the', 'of', 'seat', 'place', 'position', 'post', 'division', 'grand', 'circuit', 'judicial', 'appellate', 'supreme', 'court', 'justice', 'associate'}
def toks(s, keep_pos=True):
    s = norm(s).replace('&', ' and ')
    s = re.sub(r'[-–,./()]', ' ', s)
    out = []
    for t in s.split():
        t = ORD.get(t, t)
        m = re.match(r'^0*(\d+)(st|nd|rd|th)?$', t)
        if m: t = m.group(1)
        m2 = re.match(r'^0*(\d+)([a-z])$', t)
        if m2: out += [m2.group(1), m2.group(2)]; continue
        if t in STOPT: continue
        out.append(t)
    return ' '.join(sorted(out))
def lastname(s):
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b\.?', '', norm(s)).replace(',', ' ')
    s = re.sub(r'\([^)]*\)|"[^"]*"', ' ', s)
    return s.split()[-1] if s.split() else ''
def slugify(s): return re.sub(r'[^a-z0-9]+', '-', norm(s)).strip('-')
# ------------------------------------------------------------------ parties
PC = dict(vac=0, dem=1, rep=2, ind=3, np=4, prog=5, fwd=6, lib=7, grn=8, unk=9, oth=10)
def pcode(s, nonpartisan=False):
    s0 = (s or '').strip(); s = s0.lower().replace('.', '')
    if nonpartisan and s in ('', 'nonpartisan', 'np'): return PC['np']
    if not s: return PC['unk']
    if s in ('d', 'dem', 'democratic', 'democrat', 'dfl', 'democratic-farmer-labor', 'democratic-npl', 'democratic-nonpartisan league') or s.startswith('democrat') or s.startswith('dfl'): return PC['dem']
    if s in ('r', 'rep', 'republican', 'gop') or s.startswith('republican'): return PC['rep']
    if s in ('p', 'pro', 'prog', 'progressive', 'vermont progressive') or 'progressive' in s: return PC['prog']
    if s.startswith('forward'): return PC['fwd']
    if s in ('l', 'lib', 'libertarian') or s.startswith('libertarian'): return PC['lib']
    if s in ('g', 'grn', 'green', 'green party', 'pacific green', 'mountain', 'green-rainbow') or s.startswith('green'): return PC['grn']
    if s in ('i', 'ind', 'independent', 'unaffiliated', 'npa', 'no party affiliation', 'no party preference', 'none', 'nonpartisan', 'np', 'unenrolled', 'nm', 'n'): return PC['ind'] if not nonpartisan else PC['np']
    if s in ('w', 'wri', 'write-in', 'writein', 'scattering', 'scattered', 'oth', 'other'): return PC['oth']
    return PC['oth']
# ------------------------------------------------------------------ people
PEOPLE = {}  # key -> [p, name, cid]
for r in people_rows: PEOPLE[r['key']] = [int(r['p']), r['name'], '']
CIDS = set()
def make_cid(name, hint=''):
    n = re.sub(r'\([^)]*\)|"[^"]*"', ' ', norm(name)); n = re.sub(r'\b(jr|sr|ii|iii|iv)\b\.?', '', n).replace(',', ' ')
    parts = [x for x in re.split(r'\s+', n) if x]
    if not parts: parts = ['unknown']
    last = parts[-1]; rest = parts[:-1]
    base = slugify(' '.join([last] + rest[:1] + [x[0] for x in rest[1:2]]))
    cid = base
    if cid in CIDS: cid = f'{base}-{hint.lower()}' if hint else base
    i = 2
    while cid in CIDS: cid = f'{base}-{hint.lower()}-{i}' if hint else f'{base}-{i}'; i += 1
    CIDS.add(cid); return cid
HINT = collections.defaultdict(list)   # key -> states seen at link time (cid suffix hint)
def person(key, name, cid=None, hint=''):
    # cids are assigned at the end (assign_cids): an Election Data slug is only ever attached through a (slug, state)
    # link, never by name alone, so a same-named person in another state cannot take it
    if key not in PEOPLE: PEOPLE[key] = [len(PEOPLE) + 1, name, '']
    if hint and hint not in HINT[key]: HINT[key].append(hint)
    return PEOPLE[key][0]
# Congress id maps
CL = json.load(open(f'{SRC}/cl/legislators-current.json')) + json.load(open(f'{SRC}/cl/legislators-historical.json'))
FEC2BIO = {}; BIO = {}; CL_BY_ST_LAST = collections.defaultdict(list)
for m in CL:
    bio = m['id']['bioguide']; BIO[bio] = m
    for f in m['id'].get('fec', []): FEC2BIO[f] = bio
    sts = {t['state'] for t in m['terms'] if t['start'] >= '2009'}
    for st in sts: CL_BY_ST_LAST[(st, lastname(m['name'].get('last', '')))].append(m)
OSBP = json.load(open(f'{SRC}/os_bp_map.json'))
def bp_person(slug, name, st=''):
    slug = (slug or '').rstrip('/')
    if slug and f'bp:{slug}' in PEOPLE: return person(f'bp:{slug}', name, hint=st)
    if slug and slug in OSBP: return person('os:' + OSBP[slug], name, hint=st)
    if slug: return person(f'bp:{slug}', name, hint=st)
    return person(f'name:{st}:{slugify(name)}', name, hint=st)
def congress_person(c, st, year, ttype=None):
    fid = (c.get('fec') or '').strip()
    if fid and fid in FEC2BIO:
        bm = BIO[FEC2BIO[fid]]
        import difflib
        bl = re.sub(r'[^a-z]', '', norm(bm['name'].get('last', ''))); cl_ = re.sub(r'[^a-z]', '', lastname(c['name']))
        if not any(t['state'] == st for t in bm['terms']):
            XC.append(dict(scope='FEC id vs candidate state', item=f'{year} {st} {c["name"]}', ok=0, detail=f'FEC id {fid} -> {FEC2BIO[fid]} never served from {st}; not linked'))
        elif bl in re.sub(r'[^a-z]', '', norm(c['name'])) or bl.startswith(cl_) or difflib.SequenceMatcher(None, bl, cl_).ratio() >= 0.75:
            return person('bioguide:' + FEC2BIO[fid], c['name'], hint=st)
        XC.append(dict(scope='FEC id vs candidate name', item=f'{year} {st} {c["name"]}', ok=0, detail=f'FEC id {fid} belongs to {bm["name"].get("official_full")} in congress-legislators; ignored'))
        fid = ''
    # name match among members of this state (served 2009+)
    cands = [m for m in CL_BY_ST_LAST.get((st, lastname(c['name'])), [])
             if any(t['start'][:4] <= str(year + 1) and t['end'][:4] >= str(year) for t in m['terms'])]
    if len(cands) > 1 and ttype:
        cands = [m for m in cands if any(t['type'] == ttype and t['state'] == st and t['start'][:4] <= str(year + 1) and t['end'][:4] >= str(year) for t in m['terms'])] or cands
    if len(cands) > 1:
        f2 = norm(re.sub(r'^\W+', '', c['name']))[:2]
        cands = [m for m in cands if norm(m['name'].get('first', ''))[:2] == f2 or norm(m['name'].get('nickname', ''))[:2] == f2] or cands
    if not cands:
        # former member of this state running again (e.g. MI 2024 Senate: Mike Rogers = R000572, House MI-8 2001-2015);
        # same state + same surname + same first name/nickname + a term starting before the election; never another state
        f2 = norm(re.sub(r'^\W+', '', c['name']))[:2]
        old = [m for m in CL_BY_ST_LAST.get((st, lastname(c['name'])), [])
               if any(t['state'] == st and t['start'][:4] <= str(year) for t in m['terms'])
               and f2 in (norm(m['name'].get('first', ''))[:2], norm(m['name'].get('nickname', ''))[:2])]
        if len(old) == 1:
            return person('bioguide:' + old[0]['id']['bioguide'], c['name'], cid=c.get('candidate_id'), hint=st)
    if len(cands) == 1 and (c.get('win') or norm(cands[0]['name'].get('first', ''))[:2] == norm(re.sub(r'^\W+', '', c['name']))[:2]
                            or norm(cands[0]['name'].get('nickname', ''))[:2] == norm(re.sub(r'^\W+', '', c['name']))[:2]):
        return person('bioguide:' + cands[0]['id']['bioguide'], c['name'], cid=c.get('candidate_id'), hint=st)
    if fid: return person('fec:' + fid, c['name'], cid=c.get('candidate_id'), hint=st)
    if c.get('candidate_id'): return person('cid:' + c['candidate_id'], c['name'], cid=c['candidate_id'], hint=st)
    return person(f'name:{st}:{slugify(c["name"])}', c['name'], hint=st)
# ------------------------------------------------------------------ contests
CONTESTS = []; CANDS = []; XC = []
def seat_at(b, label_tokens, day, pos=None):
    out = []
    for s in SEATS[b]:
        if toks(s['dist']) != label_tokens and toks(s['label']) != label_tokens: continue
        if s['valid_from'] and s['valid_from'] > day: continue
        if s['valid_to'] and s['valid_to'] <= day: continue
        out.append(int(s['s']))
    return out
def add_contest(b, year, date, stage, office, st, district, vintage, geoid, cands, total, src, seats_=None, n_up=1, kind='candidate',
                nonpartisan=False, link='', note=''):
    c = len(CONTESTS) + 1
    real = [x for x in cands if not x.get('writein')]
    real.sort(key=lambda x: -(x.get('votes') or 0) if x.get('votes') is not None else (0 if x.get('win') else 1))
    if total is None and any(x.get('votes') is not None for x in cands): total = sum(x.get('votes') or 0 for x in cands)
    key = f'{year}|{st}|{office}|{district}' + ('' if stage == 'general' else f'|{stage}') + (f'|{date}' if stage in ('special', 'special_runoff') else '')
    CONTESTS.append(dict(c=c, key=key, b=b, year=year, date=date, stage=stage, kind=kind, office=office, st=st, vintage=vintage, district=district,
                         geoid=geoid or '', n_up=n_up, seats=' '.join(map(str, seats_ or [])), link=link, total=int(total) if total else '',
                         ncand=len(real), src=src, note=note))
    keep = max(2, n_up + 1)
    for i, x in enumerate(real[:keep] if kind == 'candidate' else real):
        v = x.get('votes'); pct = x.get('pct')
        if pct is None and v is not None and total: pct = 100.0 * v / total
        CANDS.append(dict(c=c, rank=i + 1, p=x['p'], party=x.get('pc', pcode(x.get('party'), nonpartisan)), votes='' if v is None else int(v),
                          pct='' if pct is None else round(pct, 2), win=int(bool(x.get('win'))), inc=int(bool(x.get('inc'))), ans=x.get('ans', '')))
    return c
GEN = {2016: '2016-11-08', 2017: '2017-11-07', 2018: '2018-11-06', 2019: '2019-11-05', 2020: '2020-11-03', 2021: '2021-11-02',
       2022: '2022-11-08', 2023: '2023-11-07', 2024: '2024-11-05'}
# ---------------- Congress
cong = json.load(open(f'{R}/congress_contests.json'))
REGCLASS = {2016: 3, 2018: 1, 2020: 2, 2022: 3, 2024: 1}
ST50 = {b['st'] for b in bodies if b['kind'] == 'L' and b['st'] != 'US'}   # states with a legislature (excludes DC: delegate is non-voting)
seen = set(); fec22sen = []
# specials held on the general-election date appear both in the main sheets and the special sheets: keep one, as stage general + special office
def sig_(x):
    top = sorted([c.get('votes') or 0 for c in x['cands']], reverse=True)[:2]
    return (x['st'], x['office'].replace('_special', ''), tuple(int(v) for v in top))
mainsig = {}
for x in cong:
    if 'special-election sheet' not in x['src']: mainsig.setdefault(sig_(x), x)
for x in cong:
    if 'special-election sheet' in x['src'] and x['year'] % 2 == 0 and x['date'] == GEN.get(x['year']) and x['stage'] in ('special', 'general'):
        m = mainsig.get(sig_(x))
        x['stage'] = 'general'
        if m is not None:
            m['office'] = x['office']; m['special'] = True; x['dup'] = True
cong = [x for x in cong if not x.get('dup')]
def senate_class(st, date, winner_bio, regular_year=None):
    if winner_bio and winner_bio in BIO:
        for t in BIO[winner_bio]['terms']:
            if t['type'] == 'sen' and t['state'] == st and date <= t['start'] <= (datetime.date.fromisoformat(date) + datetime.timedelta(days=100)).isoformat():
                return t.get('class')
    return REGCLASS.get(regular_year)
for x in cong:
    if x['st'] not in ST50: continue
    if x['year'] == 2022 and x['office'].startswith('us_senate') and x['src'].startswith('FEC'): fec22sen.append(x); continue
    k = (x['office'], x['st'], x['district'], x['date'], x['stage'])
    if k in seen: continue
    seen.add(k)
    if not x['date'] or not x['year'] or x['year'] < 2016 or x['year'] > 2024: continue
    for c in x['cands']: c['p'] = congress_person(c, x['st'], x['year'], 'rep' if x['office'] == 'us_house' else 'sen')
    real_ = [c for c in x['cands'] if not c.get('writein') and c.get('votes')]
    if real_:
        mx = max(real_, key=lambda c: c['votes'])
        flagged = [c for c in x['cands'] if c.get('win')]
        if flagged and mx not in flagged and x['st'] != 'LA':
            # FEC flags reflect the deciding round (runoff / RCV / special general); only NY-27 2020 special is a confirmed FEC flag error
            fix = (x['year'], x['st'], x['district'], x['stage']) in {(2020, 'NY', '27', 'special')}
            XC.append(dict(scope='FEC winner flag vs max first-round votes', item=f"{x['year']} {x['st']} {x['office']} {x['district']} {x['stage']}", ok=int(not fix),
                           detail=f"flag {[c['name'] for c in flagged]} | max votes {mx['name']}" + (' -> FEC flag error, max votes used (Jacobs won per congress-legislators)' if fix else ' -> decided by runoff/RCV; flag kept')))
            if fix:
                for c in x['cands']: c['win'] = c is mx
    win = [c for c in x['cands'] if c.get('win')]
    if x['office'] == 'us_house':
        b = 1; d = '00' if x['district'] in ('00', '0', 'AL') else f"{int(x['district']):02d}"
        start = f"{x['year'] + 1}-01-03" if x['stage'] in ('general', 'runoff') else x['date']
        sl = seat_at(1, toks(f'{x["st"]}-{d}'), start) or seat_at(1, toks(d), start)
        sl = [s for s in sl if SEATS[1][s]['label'].startswith(x['st'] + '-')]
        vint = 'cd' + ('2012' if x['year'] <= 2020 else '2022' if x['year'] <= 2023 else '2024')
        if x['st'] == 'PA' and 2018 <= x['year'] <= 2020: vint = 'cd2018pa'
        if x['st'] == 'NC' and x['year'] == 2020: vint = 'cd2020nc'
        if x['st'] in ('FL', 'VA', 'NC') and x['year'] == 2016: vint = 'cd2016' + x['st'].lower()
        geoid = SEATS[1][sl[0]]['geoid'] if sl and (vint == 'cd2024' or (vint == 'cd2022' and x['st'] not in ('AL', 'GA', 'LA', 'NC', 'NY'))) else ''
        cid = add_contest(1, x['year'], x['date'], x['stage'], 'us_house', x['st'], d, vint, geoid, x['cands'], None, x['src'], sl, link='label' if sl else '')
    else:
        b = 0
        wb = None
        if win:
            k_ = [k for k, v in PEOPLE.items() if v[0] == win[0]['p']]
            wb = k_[0].split(':')[1] if k_ and k_[0].startswith('bioguide:') else None
        cls = senate_class(x['st'], x['date'], wb, x['year'] if x['office'] == 'us_senate' else None)
        sl = seat_at(0, toks(f'{x["st"]} class {cls}'), x['date']) if cls else []
        cid = add_contest(0, x['year'], x['date'], x['stage'], x['office'], x['st'], '', 'state', SEATS[0][sl[0]]['geoid'] if sl else '', x['cands'], None,
                          x['src'], sl, link='class' if sl else '', note=f'class {cls}' if cls else 'class unknown')
# FEC 2022 Senate vs teammate rows
tm22 = {(c['st'], c['office']): c for c in cong if c['year'] == 2022 and c['office'].startswith('us_senate') and not c['src'].startswith('FEC')}
for x in fec22sen:
    if x['stage'] != 'general': continue
    t = tm22.get((x['st'], x['office']))
    if not t: XC.append(dict(scope='us-senate 2022', item=f"{x['st']} {x['office']}", ok=0, detail='in FEC, not in teammate rows')); continue
    fw = max(x['cands'], key=lambda c: c.get('votes') or 0); tw = max(t['cands'], key=lambda c: c.get('votes') or 0)
    ok = lastname(fw['name']) == lastname(tw['name']) and abs((fw['votes'] or 0) - tw['votes']) <= max(10, 0.001 * tw['votes'])
    XC.append(dict(scope='us-senate 2022 FEC vs Election Data teammate', item=f"{x['st']} {x['office']}", ok=int(ok), detail=f"FEC {fw['name']} {fw['votes']} | teammate {tw['name']} {tw['votes']}"))
# MEDSL Senate cross-check (2016-2024 general, state level)
ms = pd.read_csv(f'{R}/senate.tab', sep='\t', low_memory=False)
ms = ms[(ms.year >= 2016) & (ms.stage == 'gen')]
def alpha(s): return re.sub(r'[^a-z]', '', norm(s))
for (y, st, sp), g in ms.groupby(['year', 'state_po', 'special']):
    g = g.groupby('candidate', as_index=False)['candidatevotes'].sum().sort_values('candidatevotes', ascending=False)
    off = 'us_senate_special' if str(sp) == 'True' else 'us_senate'
    mine = [c for c in CONTESTS if c['b'] == 0 and c['year'] == y and c['st'] == st and c['office'] == off and c['stage'] == 'general']
    if not mine:
        XC.append(dict(scope='us-senate vs MEDSL', item=f'{y} {st} {off}', ok=0, detail='in MEDSL, missing here')); continue
    top = [cc for cc in CANDS if cc['c'] == mine[0]['c'] and cc['rank'] == 1][0]
    mv = int(g.iloc[0]['candidatevotes'])
    PEOPLE_NAME = next(v[1] for v in PEOPLE.values() if v[0] == top['p'])
    mname = re.sub(r'[^A-Za-z ,.-]', ' ', str(g.iloc[0]['candidate']))
    ok = top['votes'] != '' and abs(top['votes'] - mv) <= max(10, 0.002 * mv) and alpha(lastname(PEOPLE_NAME)) == alpha(lastname(mname))
    if not ok:   # MEDSL files Senate runoffs (GA/MS/LA) under stage 'gen'
        rr = [c for c in CONTESTS if c['b'] == 0 and c['year'] == y and c['st'] == st and c['office'] == off and c['stage'] == 'runoff']
        if rr:
            t2 = [cc for cc in CANDS if cc['c'] == rr[0]['c'] and cc['rank'] == 1][0]
            ok = t2['votes'] != '' and abs(t2['votes'] - mv) <= max(10, 0.002 * mv)
    XC.append(dict(scope='us-senate vs MEDSL', item=f'{y} {st} {off}', ok=int(ok), detail=f"here {PEOPLE_NAME} {top['votes']} | MEDSL {g.iloc[0]['candidate']} {mv}"))
# winners vs congress-legislators terms (general/runoff winners must start a term in that seat next Jan 3; specials within 120 days)
P2KEY = {v[0]: k for k, v in PEOPLE.items()}
cxc = collections.Counter()
RUNK = {(c['b'], c['st'], c['district'], c['year'], c['office']) for c in CONTESTS if c['stage'] == 'runoff'}
for c in CONTESTS:
    if c['b'] > 1 or c['year'] > 2024: continue
    w = [x for x in CANDS if x['c'] == c['c'] and x['win']]
    if not w: continue
    if c['stage'] == 'general' and (c['b'], c['st'], c['district'], c['year'], c['office']) in RUNK: continue
    key = P2KEY.get(w[0]['p'], '')
    ok = False
    if key.startswith('bioguide:'):
        m = BIO[key.split(':')[1]]; d0 = c['date']; d1 = (datetime.date.fromisoformat(d0) + datetime.timedelta(days=120)).isoformat()
        for t_ in m['terms']:
            if t_['state'] != c['st'] or t_['type'] != ('sen' if c['b'] == 0 else 'rep'): continue
            if c['b'] == 1 and int(t_.get('district', -1)) != int(c['district']) and not (int(c['district']) == 0 and t_.get('district') in (0, 1)): continue
            if d0 <= t_['start'] <= d1: ok = True; break
    cxc[ok] += 1
    if not ok: XC.append(dict(scope='congress winners vs congress-legislators terms', item=c['key'], ok=0, detail=f'winner p{w[0]["p"]} key {key or "no bioguide"}'))
XC.append(dict(scope='congress winners vs congress-legislators terms (summary)', item='all', ok=int(cxc[False] == 0), detail=f'ok {cxc[True]} fail {cxc[False]}'))
print('congress contests', len(CONTESTS), 'winner/term check', dict(cxc), flush=True)
# ---------------- State legislatures: Ballotpedia district pages (primary) + Klarner SLERs (fill + cross-check)
bpc = json.load(open(f'{SRC}/bp_chambers.json'))
OFF2DIST = {}
for k, v in bpc.items():
    for r in v['rows']: OFF2DIST[(k, r['office'])] = r['district']
CHB = {}
for b in bodies:
    if b['kind'] == 'L' and b['st'] != 'US':
        ch = {'senate': 'upper', 'house': 'lower', 'legislature': 'legislature'}[b['key'].split('-')[-1]]
        CHB[f"{b['st']}_{ch}"] = int(b['b'])
REDRAW24 = {'WI', 'OH', 'MI', 'GA', 'NC', 'MT', 'ND', 'WA'}   # legislative lines first used in 2024 (some only partly)
REDRAW23 = {'LA', 'MS', 'VA', 'NJ'}                           # odd-year states: post-2020 lines first used 2023 (VA/NJ: 2023/2021)
def leg_vintage(st, year):
    if st in ('VA',): return '2012' if year <= 2021 else '2023'
    if st == 'NJ': return '2011' if year <= 2019 else ('2021' if year == 2021 else '2023')
    if st in ('LA', 'MS'): return '2012' if year <= 2019 else '2023'
    if year <= 2021: return '2012'
    if st in REDRAW24 and year >= 2024: return '2024'
    return '2022'
def repo_vintage_ok(st, year):
    v = leg_vintage(st, year)
    return v in ('2023', '2024') or (v == '2022' and st not in REDRAW24)
bpd = json.load(open(f'{R}/bp_district_results.json'))
LEGSEEN = {}
for u, page in bpd.items():
    ck = page['chamber']; b = CHB.get(ck)
    if b is None: continue
    st = ck.split('_')[0]; chamber = ck.split('_')[1]
    dlabel = OFF2DIST.get((ck, page['office']))
    if dlabel is None: continue
    office = BODY[b]['office']
    seen_e = set()
    for e in page['elections']:
        y = e['year']
        if y < 2016 or y > 2024 or not e['cands']: continue
        sig = (y, e['kind'], e['date'], tuple((c['name'], c['votes']) for c in e['cands']))
        if sig in seen_e: continue
        seen_e.add(sig)
        stage = {'general': 'general', 'runoff': 'runoff', 'special': 'special', 'special_runoff': 'special_runoff', 'primary_decided': 'primary_decided', 'unopposed': 'unopposed'}[e['kind']]
        date = e['date']
        try: date = datetime.datetime.strptime(date, '%B %d, %Y').date().isoformat() if date else GEN.get(y, '')
        except ValueError: date = GEN.get(y, '')
        nwin = sum(1 for c in e['cands'] if c['win'] and not c.get('writein'))
        cands = []
        for c in e['cands']:
            if c.get('writein'): cands.append(dict(c, p=0, writein=True)); continue
            cands.append(dict(c, p=bp_person(c['bp'], c['name'], st)))
        vint = leg_vintage(st, y)
        dl = dlabel
        offt = re.sub(r'^(special\s+)?(general\s+)?(runoff\s+)?(election\s+)?(nonpartisan\s+)?(primary\s+)?(for\s+)', '', e.get('title', ''), flags=re.I).strip()
        if (ck, offt) in OFF2DIST: dl = OFF2DIST[(ck, offt)]
        tk = toks(dl)
        sl = [int(s['s']) for s in SEATS[b] if toks(s['label']) == tk]
        geo = geo_match(st, chamber, dl) if repo_vintage_ok(st, y) else None
        link = 'geo' if vint == leg_vintage(st, 2026) else 'label'
        nonp = st == 'NE'
        cid = add_contest(b, y, date, stage, office, st, dl, vint, geo[0] if geo else '', cands, e.get('total'),
                          'ballotpedia:' + u.split('/')[-1], sl, n_up=max(1, nwin), nonpartisan=nonp, link=link if sl else '')
        LEGSEEN[(b, y, stage, tk)] = cid
        if stage in ('unopposed', 'primary_decided'): LEGSEEN.setdefault((b, y, 'general', tk), cid)
print('after BP legislative', len(CONTESTS), flush=True)
CBYC0 = collections.defaultdict(list)
for x in CANDS: CBYC0[x['c']].append(x)
# Klarner
kl = pd.read_pickle(f'{R}/slers_2015.pkl')
kl = kl[(kl.year >= 2016) & (kl.year <= 2024) & (kl.etype.isin(['g', 'gs', 'ssg', 's']) | kl.etype.astype(str).str.match(r'^la(g|fsettled|runoff|funset)?'))]
def kl_label(r):
    parts = []
    if isinstance(r.dname, str) and r.dname: parts.append(r.dname)
    if pd.notna(r.dno): parts.append(str(int(r.dno)))
    if pd.notna(r.geopost): parts.append(chr(64 + int(r.geopost)))
    return ' '.join(parts)
kl['label'] = [kl_label(r) for r in kl.itertuples()]
kl['tk'] = kl['label'].map(toks)
kfill = 0; kchk = collections.Counter()
PNAME = {v[0]: v[1] for v in PEOPLE.values()}
def fi(name): 
    n = re.sub(r'\([^)]*\)|"[^"]*"', ' ', norm(name)).split()
    return n[0][:1] if n else ''
NIDX_D = collections.defaultdict(set); NIDX_B = collections.defaultdict(set)
for c in CONTESTS:
    if c['b'] <= 1: continue
    for x in CBYC0.get(c['c'], []):
        if x['p']:
            nm = PNAME.get(x['p'], ''); NIDX_D[(c['b'], toks(c['district']), lastname(nm), fi(nm))].add(x['p']); NIDX_B[(c['b'], lastname(nm), fi(nm))].add(x['p'])
for t_ in base_terms:
    b_ = int(t_['b'])
    if b_ <= 1: continue
    nm = PNAME.get(int(t_['p']), ''); s_ = SEATS[b_][int(t_['s'])]
    NIDX_D[(b_, toks(s_['label']), lastname(nm), fi(nm))].add(int(t_['p'])); NIDX_B[(b_, lastname(nm), fi(nm))].add(int(t_['p']))
import difflib
def same_last(a, b):
    a, b = alpha(a), alpha(b)
    return bool(a and b) and (a == b or a.endswith(b) or b.endswith(a) or a.startswith(b) or b.startswith(a) or difflib.SequenceMatcher(None, a, b).ratio() >= 0.8)
DLIST = collections.defaultdict(set)
for (b_, tk_, ln_, fi_), ps in NIDX_D.items():
    for p_ in ps: DLIST[(b_, tk_)].add((p_, ln_, fi_))
def kl_person(b, tk, name, candid, sab):
    k = (lastname(name), fi(name))
    hit = NIDX_D.get((b, tk) + k)
    if hit and len(hit) == 1: return next(iter(hit))
    fz = {p_ for p_, ln_, fi_ in DLIST.get((b, tk), ()) if same_last(ln_, k[0]) and (fi_ == k[1] or not fi_)}
    if len(fz) == 1: return next(iter(fz))
    hit = NIDX_B.get((b,) + k)
    if hit and len(hit) == 1: return next(iter(hit))
    return person(f'kl:{int(candid)}' if candid == candid and candid is not None else f'name:{sab}:{slugify(name)}', name, hint=sab)
for (sab, sen, y, et, tk, mmd, month), g in kl.groupby(['sab', 'sen', 'year', 'etype', 'tk', kl.mmdpost.fillna(0), 'month'], dropna=False):
    ch = 'legislature' if sab == 'NE' else ('upper' if sen == 1 else 'lower')
    b = CHB.get(f'{sab}_{ch}')
    if b is None: continue
    stage = 'special' if et == 's' else 'general'
    if str(et).startswith('la'): stage = 'runoff' if 'runoff' in str(et) else 'general'
    wins = g[g.outcome == 'w']
    hit = LEGSEEN.get((b, int(y), stage, tk))
    if hit is None and mmd:   # WA/ID positions: Ballotpedia keys them as '1-Position 2' / '1A'
        for alt in (toks(f'{g.label.iloc[0]} position {int(mmd)}'), toks(f'{g.label.iloc[0]} {chr(64 + int(mmd))}')):
            hit = LEGSEEN.get((b, int(y), stage, alt)) or hit
    if hit:
        mine = {lastname(next(v[1] for v in PEOPLE.values() if v[0] == cc['p'])) for cc in CANDS if cc['c'] == hit and cc['win']}
        theirs = {lastname(str(c).split(',')[0]) for c in wins.cand}
        ok = not theirs or all(any(same_last(a, b_) for a in mine) for b_ in theirs) or all(any(same_last(a, b_) for b_ in theirs) for a in mine) and mine
        kchk[ok] += 1
        if not ok:
            XC.append(dict(scope='state legislature: Ballotpedia vs Klarner SLERs winners', item=f'{BODY[b]["key"]} {y} {stage} {g.label.iloc[0]}', ok=0,
                           detail=f'BP {sorted(mine)} | Klarner {sorted(theirs)}'))
        continue
    if stage == 'special' and pd.isna(month): continue
    # fill: contest present in Klarner only (district renamed/dissolved, or BP page missing)
    cands = []
    for r in g.itertuples():
        nm = str(r.cand)
        if nm in ('scattering', 'nan') or nm.startswith('writein'): cands.append(dict(name=nm, votes=r.vote if pd.notna(r.vote) else None, writein=True, p=0)); continue
        last, _, first = nm.partition(',')
        name = (first.strip() + ' ' + last.strip()).title().strip()
        cands.append(dict(name=name, votes=r.vote if pd.notna(r.vote) else None, party={'d': 'D', 'r': 'R'}.get(str(r.partyt), 'I' if str(r.partyt) in ('nm', 'n', 'i') else 'O'),
                          win=r.outcome == 'w', p=kl_person(b, tk, name, r.candid if pd.notna(r.candid) else None, sab)))
    label = g.label.iloc[0] + (f' Position {int(mmd)}' if mmd else '')
    sl = [int(s['s']) for s in SEATS[b] if toks(s['label']) == toks(label)]
    date = f'{int(y)}-{int(month):02d}-01' if stage == 'special' and pd.notna(month) else GEN.get(int(y), '')
    add_contest(b, int(y), date, stage, BODY[b]['office'], sab, label, leg_vintage(sab, int(y)), '', cands, None, 'klarner_slers_2022', sl,
                n_up=max(1, len(wins)), link='label' if sl else '', note='Klarner-only (no Ballotpedia page for this district label)')
    kfill += 1
XC.append(dict(scope='state legislature: Ballotpedia vs Klarner SLERs winners (summary)', item='all', ok=int(kchk[False] == 0), detail=f'agree {kchk[True]} disagree {kchk[False]}'))
print('klarner fill', kfill, dict(kchk), flush=True)
# ---------------- Courts: Ballotpedia '<court> elections, <year>' pages
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'results'))
import bp_district_parse as BPP
cpages = json.load(open(f'{SRC}/bp/courts/pages.json'))
COURTB = {}
for b in bodies:
    if b['kind'] == 'C':
        k = b['st'] + ('_CCA' if 'criminal' in b['key'] else '_SC'); COURTB[k] = int(b['b'])
def court_label(title, court):
    t = re.sub(r'^(Special\s+)?(General\s+)?(runoff\s+)?(election|retention election)?\s*(for)?\s*', '', title.strip(), flags=re.I)
    t = t.replace(court, '').strip()
    return t
COURT_CONTESTS = []
COURT_MIN_YEAR = 2017   # user exclusion: no 2016 court contests/results for any court
CSEEN = collections.defaultdict(set)
for fn in sorted(glob.glob(f'{SRC}/bp/court_elections/*.html'), key=lambda f: (f.endswith('_all.html'), f)):
    k, y = os.path.basename(fn)[:-5].rsplit('_', 1)
    allpage = y == 'all'; y = None if allpage else int(y)
    if k not in COURTB: continue
    b = COURTB[k]; st = k[:2]; court = cpages[k]
    s = BeautifulSoup(open(fn, errors='ignore').read(), 'lxml')
    if 'Oops' in s.get_text()[:3000]: continue
    sel = int(BODY[b]['sel']); nonp = sel in (3, 4) or (sel == 5)
    seen_e = CSEEN[b]
    BPP.LA_MODE[0] = (st == 'LA')
    items = []
    for v in s.select('div.votebox'):
        e = BPP.votebox(v)
        if e: items.append(e)
    for t in s.select('table.bptable'):
        cap = t.find('tr').get_text(' ', strip=True) if t.find('tr') else ''
        if allpage: continue
        if 'Yes votes' in t.get_text(' ', strip=True) or 'retention' in cap.lower():
            cy_ = re.findall(r'\b(20\d\d)\b', cap)
            if cy_ and int(cy_[-1]) != y: continue   # earlier-cycle table shown on a later year page
            rows = [[c.get_text(' ', strip=True) for c in r.find_all(['td', 'th'])] for r in t.find_all('tr')[1:]]
            for r in rows:
                if len(r) >= 2 and r[0] not in ('Name', '') and r[-1].endswith('%'):
                    yp = BPP.pnum(r[-1])
                    items.append(dict(kind='retention', title=cap, date='', retained=(yp or 0) >= 50, judge=r[0], judge_bp='',
                                      cands=[dict(name=r[0], ans='yes', pct=yp, votes=None), dict(name=r[0], ans='no', pct=round(100 - yp, 2) if yp is not None else None, votes=None)], total=None, fmt='bptable'))
        else:
            e = BPP.bptable(t)
            if e and str(y) in cap: items.append(e)
    for e in items:
        date = e.get('date') or ''
        try: date = datetime.datetime.strptime(date, '%B %d, %Y').date().isoformat() if date else ''
        except ValueError: date = ''
        if allpage:
            if not date: continue
            yy = int(date[:4])
        else:
            if date and int(date[:4]) != y: continue
            yy = y
        if yy < COURT_MIN_YEAR or yy > 2024: continue
        if not date: date = GEN.get(yy, f'{yy}-11-01')
        sig = (e['kind'], e.get('judge', ''), tuple((c['name'], c.get('votes'), c.get('ans', '')) for c in e['cands']))
        sig2 = (e['kind'], yy, tuple(sorted(lastname(c['name']) for c in e['cands'] if not c.get('writein'))))
        if sig in seen_e or sig2 in seen_e: continue
        seen_e.add(sig); seen_e.add(sig2)
        label = court_label(e['title'], court) if e['fmt'] == 'votebox' else ''
        if e['kind'] == 'retention':
            jp = bp_person(e.get('judge_bp', ''), e['judge'], st)
            cands = [dict(c, p=jp, win=(c['ans'] == 'yes') == e['retained'], pc=PC['np'] if sel != 2 else PC['unk']) for c in e['cands']]
            stage = 'retention'; kind = 'retention'
        else:
            cands = [dict(c, p=0, writein=True) if c.get('writein') else dict(c, p=bp_person(c['bp'], c['name'], st)) for c in e['cands']]
            stage = e['kind']; kind = 'candidate'
        nwin = sum(1 for c in cands if c.get('win') and not c.get('writein')) if kind == 'candidate' else 1
        tk = toks(label) if label else ''
        sl = [int(x['s']) for x in SEATS[b] if tk and toks(x['dist']) == tk]
        if 'chief' in label.lower(): sl = [int(x['s']) for x in SEATS[b] if 'chief' in x['dist'].lower()] or sl
        if st == 'TX' and re.search(r'presiding|chief', label, re.I) and not sl: sl = [int(x['s']) for x in SEATS[b] if x['dist'] == '1']
        cid = add_contest(b, yy, date, stage, BODY[b]['office'], st, label, 'statewide' if not tk else 'court_seat', '', cands, e.get('total'),
                          'ballotpedia:' + os.path.basename(fn)[:-5], sl if len(sl) == 1 else [], n_up=max(1, nwin), kind=kind,
                          nonpartisan=nonp, link='label' if len(sl) == 1 else '')
        COURT_CONTESTS.append(cid)
print('court contests', len(COURT_CONTESTS), flush=True)
# ---------------- post-process: generals followed by a runoff (LA jungle, GA/AR runoffs) -> winners belong to the runoff
CBYC = collections.defaultdict(list)
for x in CANDS: CBYC[x['c']].append(x)
byd = collections.defaultdict(dict)
for c in CONTESTS: byd[(c['b'], c['st'], c['district'], c['year'], c['office'])][c['stage']] = c
for k, d in byd.items():
    if 'general' in d and 'runoff' in d:
        g, r = d['general'], d['runoff']
        g['n_up'] = r['n_up']; g['note'] = (g['note'] + '; ' if g['note'] else '') + 'runoff followed; winners marked on the runoff'
        for x in CBYC[g['c']]: x['win'] = 0
    if 'special' in d and 'special_runoff' in d:
        for x in CBYC[d['special']['c']]: x['win'] = 0
# ---------------- person-based seat links for courts (at-large seats or shared district labels)
PNAME = {v[0]: v[1] for v in PEOPLE.values()}
holder_slot = {}
for t in base_terms:
    if BODY[int(t['b'])]['kind'] == 'C': holder_slot[(int(t['b']), int(t['p']))] = int(t['s'])
cc = sorted([c for c in CONTESTS if c['c'] in set(COURT_CONTESTS)], key=lambda c: c['date'], reverse=True)
for c in cc:
    if c['seats']: 
        for x in CBYC[c['c']]:
            if x['win'] and x['p']: holder_slot.setdefault((c['b'], x['p']), int(c['seats'].split()[0]))
        continue
    wins = [x for x in CBYC[c['c']] if x['win'] and x['p']]
    incs = [x for x in CBYC[c['c']] if x['inc'] and x['p']]
    if not any(holder_slot.get((c['b'], x['p'])) is not None for x in wins + incs):
        # name fallback (2016 retention tables give names only): match surname against holders of this court
        for x in wins + incs:
            ln = alpha(lastname(PNAME.get(x['p'], '')))
            hits = {s_ for (b_, p_), s_ in holder_slot.items() if b_ == c['b'] and alpha(lastname(PNAME.get(p_, ''))) == ln}
            if len(hits) == 1:
                holder_slot[(c['b'], x['p'])] = next(iter(hits)); break
    for x in wins + incs:
        s_ = holder_slot.get((c['b'], x['p']))
        if s_ is not None:
            c['seats'] = str(s_); c['link'] = 'person'
            for y_ in wins + incs: holder_slot.setdefault((c['b'], y_['p']), s_)
            break
# ---------------- holder back-fill for state chambers and courts
W0 = '2016-01-01'
def term_start(c):
    if c['stage'] in ('special', 'special_runoff'): return c['date'], 1
    y = int(c['date'][:4]); return f'{y + 1}-01-01', 1
cur = {}   # (b,s) -> base term (open)
for t in base_terms:
    if not t['end']: cur[(int(t['b']), int(t['s']))] = t
by_seatgroup = collections.defaultdict(list)
for c in CONTESTS:
    if c['b'] <= 1 or not c['seats'] or c['stage'] == 'general' and any(x['win'] == 0 for x in CBYC[c['c']]) and 'runoff followed' in c['note']: continue
    by_seatgroup[(c['b'], c['seats'])].append(c)
seat_events = collections.defaultdict(list)   # (b,s) -> [(start, p, party, how, approx, c)]
mmd_assign_fail = 0
for (b, sg), cl in by_seatgroup.items():
    slots = [int(x) for x in sg.split()]
    occ = {s: None for s in slots}
    for s in slots:
        t = cur.get((b, s))
    cl.sort(key=lambda c: (c['date'], c['stage'] == 'runoff'))
    first = True
    for c in cl:
        wins = [x for x in CBYC[c['c']] if x['win'] and x['p'] and (x['ans'] in ('', 'yes'))]
        if c['kind'] == 'retention':
            if not wins:   # not retained -> seat open from the next term start, holder unknown
                st_, ap = term_start(c)
                for s in slots: seat_events[(b, s)].append((st_, 0, PC['unk'], '', 1, c['c']))
            else:
                for s in slots[:1]: seat_events[(b, s)].append((term_start(c)[0], wins[0]['p'], wins[0]['party'], 'R', 1, c['c']))
            continue
        if first:
            incs = [x for x in CBYC[c['c']] if x['inc'] and x['p']]
            for s, x in zip(slots, incs): seat_events[(b, s)].append((W0, x['p'], x['party'], '', 1, c['c'])); occ[s] = x['p']
            first = False
        st_, ap = term_start(c)
        if len(slots) == 1:
            if wins: seat_events[(b, slots[0])].append((st_, wins[0]['p'], wins[0]['party'], 'S' if c['stage'].startswith('special') else 'E', ap, c['c'])); occ[slots[0]] = wins[0]['p']
            continue
        pref = {int(cur[(b, s)]['p']): s for s in slots if (b, s) in cur}
        assigned = {}
        for w in wins:                                   # current holders keep their snapshot slot through history
            s = pref.get(w['p'])
            if s is not None and s not in assigned.values(): assigned[w['p']] = s
        for w in wins:                                   # re-elected members keep their previous slot
            if w['p'] in assigned: continue
            s = next((s for s in slots if occ[s] == w['p'] and s not in assigned.values()), None)
            if s is not None: assigned[w['p']] = s
        free = [s for s in slots if s not in assigned.values()]
        # prefer slots whose previous occupant did not win (they are the ones being replaced)
        free.sort(key=lambda s: (occ[s] in {w['p'] for w in wins}, s))
        for w in wins:
            if w['p'] in assigned: continue
            if not free: mmd_assign_fail += 1; break
            assigned[w['p']] = free.pop(0)
        for w in wins:
            s = assigned.get(w['p'])
            if s is None: continue
            seat_events[(b, s)].append((st_, w['p'], w['party'], 'S' if c['stage'].startswith('special') else 'E', ap, c['c'])); occ[s] = w['p']
new_terms = []; tl_xc = collections.Counter(); tl_bad = []
for (b, s), evs in seat_events.items():
    evs.sort()
    # collapse: same person consecutive -> one term (keep first start)
    seq = []
    for e in evs:
        if seq and seq[-1][1] == e[1]: continue
        if seq and seq[-1][0] == e[0]: seq[-1] = e; continue
        seq.append(e)
    base = cur.get((b, s))
    bstart = base['start'] if base else None
    if bstart and len(bstart) == 4: bstart = bstart + '-01-01'
    bp_ = int(base['p']) if base else None
    out = []
    for i, e in enumerate(seq):
        end = seq[i + 1][0] if i + 1 < len(seq) else ''
        out.append(dict(b=b, s=s, start=e[0], end=end, p=e[1], party=e[2], caucus='', how=e[3], appt='', approx=e[4], src='results', c=e[5]))
    # reconcile with the current (snapshot) holder
    if base:
        if out and out[-1]['p'] == bp_: 
            last = out.pop(); tl_xc['last winner = current holder'] += 1
            if bstart and last['start'] < bstart and last['how'] != '': tl_xc['winner term start earlier than BP assumed-office (kept BP)'] += 1
        elif out:
            tl_xc['last winner != current holder (vacancy/appointment/resignation since)'] += 1
            if len(tl_bad) < 400: tl_bad.append((BODY[b]['key'], s, out[-1]['p'], bp_, out[-1]['start'], bstart))
        # cut everything at the base term start (BP assumed-office date is authoritative for the current holder)
        if bstart:
            out = [t for t in out if t['start'] < bstart]
            for t in out:
                if not t['end'] or t['end'] > bstart: t['end'] = bstart
            # same person already holding before bstart (e.g. BP lists a later date for a re-sworn member) -> drop duplicate
            out = [t for t in out if t['p'] != bp_]
    new_terms += out
print('backfilled terms', len(new_terms), dict(tl_xc), 'mmd assign overflow', mmd_assign_fail, flush=True)
for k, v in tl_xc.items(): XC.append(dict(scope='holder timeline vs snapshot', item=k, ok=1, detail=str(v)))

# ---------------- shared candidate ids (Election Data candidate_id slugs) ----------------
def assign_cids(allterms):
    """Link Election Data (slug, state) pairs to people and pick each person's `cid`.
    Rules: a slug links only to a candidate in the SAME state, same office family and year, with the same surname and
    first initial (district breaks ties); never across states. Slugs used in >1 state upstream get a state suffix in
    people.cid (`rogers-mike-mi`) so a slug-only join cannot hit the wrong person; cid_links.csv carries every
    (slug, state) -> person link. Generated cids never reuse an upstream slug. Writes cid_links.csv, cid_collisions.csv."""
    UP = json.load(open(f'{SRC}/results/upstream_cids.json'))
    USTS = collections.defaultdict(set)
    for r in UP: USTS[r['cid']].add(r['st'])
    KEY = {v[0]: k for k, v in PEOPLE.items()}; NAME = {v[0]: v[1] for v in PEOPLE.values()}
    CBY = {c['c']: c for c in CONTESTS}
    fam = lambda o: next((f for f in ('us_house', 'us_senate', 'state_house', 'state_senate', 'state_legislature') if o.startswith(f)), None)
    IDX = collections.defaultdict(set)   # (year, st, fam) -> {(p, last, fi, district)}
    PST = collections.defaultdict(set)
    for c in CANDS:
        k = CBY[c['c']]; p_ = int(c['p'])
        if not p_: continue
        PST[p_].add(k['st'])
        f_ = fam(k['office'])
        if f_: IDX[(int(k['year']), k['st'], 'state_senate' if f_ == 'state_legislature' else f_)].add((p_, lastname(NAME[p_]), fi(NAME[p_]), str(k['district']).lstrip('0')))
    for t in allterms:
        p_ = int(t['p']) if str(t['p']) not in ('', '0') else 0
        if not p_: continue
        b_ = BODY[int(t['b'])]
        st_ = b_['st'] if b_['st'] != 'US' else SEATS[int(t['b'])][int(t['s'])]['label'][:2]
        PST[p_].add(st_)
    links, amb = [], []
    LINKP = collections.defaultdict(collections.Counter)   # p -> Counter((slug, st))
    for r in UP:
        f_ = 'state_senate' if r['fam'] == 'state_legislature' else r['fam']
        pool = IDX.get((r['year'], r['st'], f_), set())
        ln, f1 = lastname(r['name']), fi(r['name'])
        hit = {x for x in pool if x[1] == ln and (x[2] == f1 or not x[2] or not f1)}
        if len({x[0] for x in hit}) > 1:
            d = str(r['district']).lstrip('0')
            hit = {x for x in hit if x[3] == d} or hit
        ps = sorted({x[0] for x in hit})
        row = dict(cid=r['cid'], st=r['st'], year=r['year'], office=r['office'], district=r['district'], name=r['name'])
        if len(ps) == 1:
            links.append(dict(row, p=ps[0], key=KEY[ps[0]], method='state+office+year+surname+initial')); LINKP[ps[0]][(r['cid'], r['st'])] += 1
        elif len(ps) > 1:
            amb.append(dict(row, p=';'.join(map(str, ps)), key=';'.join(KEY[x] for x in ps), method='ambiguous: same surname+initial in contest pool'))
    # one person per (slug, state): if two people claim the same pair it is ambiguous
    owners = collections.defaultdict(set)
    for p_, cn in LINKP.items():
        for pair in cn: owners[pair].add(p_)
    CIDS.clear(); CIDS.update(USTS)                                     # upstream namespace is reserved
    chosen = {}
    for p_ in sorted(LINKP):
        pairs = [pr for pr, _ in LINKP[p_].most_common() if len(owners[pr]) == 1]
        if not pairs: continue
        slug, st_ = pairs[0]
        cid = slug if len(USTS[slug]) == 1 else f'{slug}-{st_.lower()}'
        if cid in chosen.values(): continue
        chosen[p_] = cid
    CIDS.update(chosen.values())
    for k, v in sorted(PEOPLE.items(), key=lambda x: x[1][0]):
        if v[0] in chosen: v[2] = chosen[v[0]]
        else:
            h = HINT.get(k) or sorted(PST.get(v[0], ()))
            v[2] = make_cid(v[1], h[0] if len(set(h)) == 1 else (h[0] if h else ''))
    for l in links + amb: l['cid_in_people'] = ';'.join(PEOPLE[k_][2] for k_ in str(l['key']).split(';'))
    wcsv('cid_links.csv', sorted(links + amb, key=lambda x: (x['cid'], x['st'], x['year'], x['office'])),
         ['cid', 'st', 'year', 'office', 'district', 'name', 'p', 'key', 'cid_in_people', 'method'])
    # ---- collisions report: every slug shared by more than one person/state, plus cross-state id links
    prev = {}
    pf = f'{SRC}/results/people_prev_06a2cc3.csv'
    if os.path.exists(pf): prev = {r['key']: r['cid'] for r in csv.DictReader(open(pf))}
    prev_by_cid = collections.defaultdict(list)
    for k_, c_ in prev.items(): prev_by_cid[c_].append(k_)
    rows = []
    PSTK = {KEY[p_]: v for p_, v in PST.items()}
    pairs = collections.defaultdict(set)
    for l in links: pairs[(l['cid'], l['st'])].add(l['p'])
    for (slug, st_), ps in sorted(pairs.items()):
        multi = len(USTS[slug]) > 1
        olds = prev_by_cid.get(slug, [])
        for p_ in sorted(ps):
            k_ = KEY[p_]; wrong = [x for x in olds if x != k_]
            if len(ps) > 1: action, kind = 'ambiguous (same slug+state, several people; not attached to people.cid)', 'same slug, same state, different people'
            elif wrong and not (PSTK.get(wrong[0], set()) & {st_}) and wrong[0] in PEOPLE:
                action, kind = 'fixed: slug-only join hit a person from another state', 'cross-state'
            elif wrong and wrong[0] not in PEOPLE: action, kind = 'fixed: previous holder re-keyed (same state)', 're-keyed'
            elif wrong: action, kind = 'ambiguous: same-state duplicate person record (different keys, not merged)', 'same state, different key'
            elif multi: action, kind = 'fixed: slug used in several states; people.cid now state-qualified', 'multi-state slug'
            else: continue
            rows.append(dict(slug=slug, st=st_, p=p_, key=k_, name=NAME[p_], person_states=' '.join(sorted(PST[p_])), slug_states=' '.join(sorted(USTS[slug])),
                             kind=kind, old_cid=prev.get(k_, ''), new_cid=PEOPLE[k_][2], old_slug_holder=';'.join(wrong), action=action))
    for a in amb:
        rows.append(dict(slug=a['cid'], st=a['st'], p=a['p'], key=a['key'], name=a['name'], person_states='', slug_states=' '.join(sorted(USTS[a['cid']])),
                         kind=f"ambiguous {a['year']} {a['office']} {a['district']}", old_cid='', new_cid='', old_slug_holder='', action='ambiguous (not linked)'))
    # cross-state id links: a bioguide / os person appearing in a contest of a state they never represented
    OSST = {}
    for st_, chs in json.load(open(f'{SRC}/openstates_current.json')).items():
        for ch in chs.values():
            for m in ch.get('members', []): OSST[m['id'].split('/')[-1]] = st_
    for p_, sts in sorted(PST.items()):
        k_ = KEY[p_]; home = None
        if k_.startswith('bioguide:') and k_[9:] in BIO: home = {t['state'] for t in BIO[k_[9:]]['terms']}
        elif k_.startswith('os:') and k_[3:] in OSST: home = {OSST[k_[3:]]}
        bad = sorted(s_ for s_ in sts if home is not None and s_ not in home)
        if bad or (k_.startswith(('bp:', 'kl:', 'cid:', 'fec:')) and len(sts) > 1):
            rows.append(dict(slug='', st=' '.join(bad or sorted(sts)), p=p_, key=k_, name=NAME[p_], person_states=' '.join(sorted(sts)),
                             slug_states=' '.join(sorted(home or ())), kind='id linked in a state outside its home state' if bad else 'Ballotpedia/other page id in several states',
                             old_cid=prev.get(k_, ''), new_cid=PEOPLE[k_][2], old_slug_holder='', action='ambiguous: one source page id used in two states (kept; check whether the person moved)'))
    # previous build's wrong slug holders (slug held by a person of another state than every upstream use)
    for c_, ks in sorted(prev_by_cid.items()):
        if c_ not in USTS: continue
        for k_ in ks:
            if k_ not in PEOPLE: continue   # re-keyed: reported on the pair side
            p_ = PEOPLE[k_][0]
            if not (PST[p_] & USTS[c_]) and PEOPLE[k_][2] != c_:
                rows.append(dict(slug=c_, st=' '.join(sorted(PST[p_])), p=p_, key=k_, name=NAME[p_], person_states=' '.join(sorted(PST[p_])), slug_states=' '.join(sorted(USTS[c_])),
                                 kind='holder side: cid equalled an upstream slug of another state', old_cid=c_, new_cid=PEOPLE[k_][2], old_slug_holder='', action='fixed: slug released (holder side of a cross-state link)'))
    wcsv('cid_collisions.csv', rows, ['slug', 'st', 'p', 'key', 'name', 'person_states', 'slug_states', 'kind', 'old_cid', 'new_cid', 'old_slug_holder', 'action'])
    print('cid links', len(links), 'ambiguous', len(amb), 'linked people', len(chosen), 'collision rows', len(rows), collections.Counter(r['action'] for r in rows), flush=True)
# ---------------- write
def wcsv(name, rows, cols):
    with open(f'{OUT}/{name}', 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(cols)
        for r in rows: w.writerow(['' if r.get(c) is None else (int(r[c]) if isinstance(r[c], bool) else r[c]) for c in cols])
for t in base_terms: t.setdefault('approx', 0); t.setdefault('src', 'snapshot' if int(t['b']) > 1 else 'congress-legislators')
allterms = base_terms + new_terms
allterms.sort(key=lambda t: (int(t['b']), int(t['s']), t['start'] if len(t['start']) > 4 else t['start'] + '-01-01'))
# ---- drop orphaned people (not referenced by any term, kept candidate row or court_detail) and renumber p contiguously
cd_rows = list(csv.DictReader(open(f'{OUT}/base/court_detail.csv')))   # base copy: ids from build_v3data
used_p = {int(t['p']) for t in allterms if str(t['p']) not in ('', '0')} | {int(c['p']) for c in CANDS if str(c['p']) not in ('', '0')} | {int(r_['p']) for r_ in cd_rows if r_['p'] not in ('', '0')} | {int(r_['p']) for r_ in csv.DictReader(open(f'{OUT}/base/city_detail.csv')) if r_['p'] not in ('', '0')}
PREMAP = {0: 0}
for k_, v_ in sorted(PEOPLE.items(), key=lambda x: x[1][0]):
    if v_[0] in used_p: PREMAP[v_[0]] = len(PREMAP)
n_orph = len(PEOPLE) - (len(PREMAP) - 1)
PEOPLE = {k_: [PREMAP[v_[0]]] + v_[1:] for k_, v_ in PEOPLE.items() if v_[0] in PREMAP}
for t in allterms:
    if str(t['p']) not in ('',): t['p'] = PREMAP[int(t['p'])]
for c in CANDS:
    if str(c['p']) not in ('',): c['p'] = PREMAP[int(c['p'])]
for r_ in cd_rows:
    if r_['p'] not in ('',): r_['p'] = PREMAP[int(r_['p'])]
wcsv('court_detail.csv', cd_rows, list(cd_rows[0].keys()))
cyd_rows = list(csv.DictReader(open(f'{OUT}/base/city_detail.csv')))
for r_ in cyd_rows:
    if r_['p'] not in ('',): r_['p'] = PREMAP[int(r_['p'])]
wcsv('city_detail.csv', cyd_rows, list(cyd_rows[0].keys()))
for x in XC: x['detail'] = re.sub(r'\bp(\d+)\b', lambda m: 'p' + str(PREMAP.get(int(m.group(1)), '?')), str(x['detail']))
print('orphaned people dropped', n_orph, flush=True)
wcsv('terms.csv', allterms, ['b', 's', 'start', 'end', 'p', 'party', 'caucus', 'how', 'appt', 'approx', 'src'])
assign_cids(allterms)
wcsv('people.csv', [dict(p=v[0], key=k, name=v[1], cid=v[2]) for k, v in sorted(PEOPLE.items(), key=lambda x: x[1][0])], ['p', 'key', 'name', 'cid'])
def srccode(s):
    if s.startswith('FEC Federal Elections') and 'special' in s: return 'FECS' + s.split()[3][2:]
    if s.startswith('FEC Federal Elections'): return 'FEC' + s.split()[3][2:]
    if s.startswith('Clerk'): return 'CLK24'
    if s.startswith('Election Data teammate'): return 'ED'
    if s.startswith('ballotpedia:') and re.search(r'_(SC|CCA)_(\d{4}|all)$', s): return 'BPC'
    if s.startswith('ballotpedia:'): return 'BPD'
    if s.startswith('klarner'): return 'KL'
    return s
for c in CONTESTS: c['src'] = srccode(c['src'])
SOURCES = [('FEC16..FEC22', 'FEC Federal Elections 2016/2018/2020/2022 xlsx, House/Senate results by state (fec.gov/documents/...)'),
           ('FECS16..FECS22', 'FEC Federal Elections special-election sheets'), ('CLK24', 'House Clerk, Statistics of the Presidential and Congressional Election of Nov 5, 2024'),
           ('ED', 'Election Data teammate, data-v3/results/{2022,2024}/senate/us_senate_*_state.csv (official; branch data/election, read only)'),
           ('BPD', 'Ballotpedia state-legislative district pages (votebox / RCV / 2016 bptable), fetched 2026-10-18'),
           ('BPC', 'Ballotpedia "<court> elections, <year>" and "<court> elections" pages, fetched 2026-10-18'),
           ('KL', 'Klarner, State Legislative Election Returns 1967-2022, Harvard Dataverse doi:10.7910/DVN/FJOGJB (file 127)'),
           ('MEDSL', 'MIT Election Lab, U.S. Senate 1976-2024, doi:10.7910/DVN/PEJ5QU (cross-check only)')]
wcsv('results_sources.csv', [dict(code=a, ref=b_) for a, b_ in SOURCES], ['code', 'ref'])
wcsv('results_contests.csv', CONTESTS, ['c', 'key', 'b', 'year', 'date', 'stage', 'kind', 'office', 'st', 'vintage', 'district', 'geoid', 'n_up', 'seats', 'link', 'total', 'ncand', 'src', 'note'])
wcsv('results_candidates.csv', CANDS, ['c', 'rank', 'p', 'party', 'votes', 'pct', 'win', 'inc', 'ans'])
# complete_from per body: the date from which every seat slot has a known holder
firsts = collections.defaultdict(dict)
for t in allterms:
    b, s = int(t['b']), int(t['s']); st_ = t['start'] if len(t['start']) > 4 else t['start'] + '-01-01'
    if t['p'] in (0, '0'): continue
    firsts[b][s] = min(firsts[b].get(s, '9999'), st_)
for b in bodies:
    bi = int(b['b'])
    if bi <= 1: continue
    act = [int(x['s']) for x in SEATS[bi]]
    if all(s in firsts[bi] for s in act):
        cf = max(firsts[bi][s] for s in act)
        if cf < b['complete_from']: b['complete_from'] = cf
wcsv('bodies.csv', bodies, list(bodies[0].keys()))
# topics (shape for the app-wide 'Senate' topic and siblings)
def ids(f): return [int(b['b']) for b in bodies if f(b)]
topics = dict(
    senate=dict(label='Senate', primary=BK['us-senate'], bodies=[BK['us-senate']] + ids(lambda b: b['office'] == 'state_senate'),
                offices=['us_senate', 'us_senate_special', 'state_senate'], note='US Senate first; state senates (incl. Nebraska unicameral) alongside'),
    house=dict(label='House', primary=BK['us-house'], bodies=[BK['us-house']] + ids(lambda b: b['office'] == 'state_house'), offices=['us_house', 'state_house']),
    courts=dict(label='High courts', primary=None, bodies=ids(lambda b: b['kind'] == 'C'), offices=['state_supreme_court', 'state_court_criminal_appeals']),
    city_councils=dict(label='City councils', primary=None, bodies=ids(lambda b: b['office'] == 'city_council'), offices=['city_council'],
                       mayors=ids(lambda b: b['office'] == 'mayor'), note='30 most populous US cities (Census V2025): city councils plus the consolidated city-county/metro councils (Indianapolis, San Francisco, Nashville, Louisville) and the Council of the District of Columbia; mayor bodies listed under mayors; city_bodies.csv links council b <-> mayor_b'))
json.dump(topics, open(f'{OUT}/topics.json', 'w'), indent=1)
wcsv('results_crosscheck.csv', XC, ['scope', 'item', 'ok', 'detail'])
tl_bad = [(a, s_, PREMAP.get(int(p1), p1), PREMAP.get(int(p2), p2), d1, d2) for a, s_, p1, p2, d1, d2 in tl_bad]
json.dump(tl_bad, open(f'{OUT}/base/timeline_mismatch_sample.json', 'w'))
# coverage: per year x body type, seats up (contest-linked) / contests / with votes
cov = collections.defaultdict(lambda: collections.Counter())
for c in CONTESTS:
    t = 'us_senate' if c['b'] == 0 else 'us_house' if c['b'] == 1 else ('court' if BODY[c['b']]['kind'] == 'C' else BODY[c['b']]['office'])
    k = (c['year'], t, c['stage'])
    cov[k]['contests'] += 1; cov[k]['linked_to_seat'] += bool(c['seats']); cov[k]['with_votes'] += bool(c['total'])
    cov[k]['with_geoid'] += bool(c['geoid']); cov[k]['seats_linked'] += len(c['seats'].split())
    cov[k]['src_' + re.sub(r'\d+$', '', c['src'])] += 1
rows = [dict(year=k[0], type=k[1], stage=k[2], **v) for k, v in sorted(cov.items())]
scols = sorted({k for v in cov.values() for k in v if k.startswith('src_')})
wcsv('results_coverage.csv', rows, ['year', 'type', 'stage', 'contests', 'linked_to_seat', 'seats_linked', 'with_votes', 'with_geoid'] + scols)
# per body x year: distinct seat slots with a deciding contest (general/runoff/special/retention) and chamber size
pb = collections.defaultdict(set); pbn = collections.Counter()
for c in CONTESTS:
    pbn[(c['b'], c['year'])] += 1
    for s_ in c['seats'].split(): pb[(c['b'], c['year'])].add(s_)
wcsv('results_coverage_body.csv', [dict(b=b, key=BODY[b]['key'], year=y, contests=pbn[(b, y)], seats_linked=len(pb[(b, y)]), seats=BODY[b]['seats'])
                                   for (b, y) in sorted(pbn)], ['b', 'key', 'year', 'contests', 'seats_linked', 'seats'])
print('contests', len(CONTESTS), 'candidates', len(CANDS), 'people', len(PEOPLE), 'xc fails', sum(1 for x in XC if not x['ok']))
