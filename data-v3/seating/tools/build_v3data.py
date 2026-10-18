#!/usr/bin/env python3
"""Build the compact seat / holder tables for v3 (assemblies + elected high courts).
Inputs: snapshots in /workspace/seating/src (Ballotpedia, Wikipedia, Open States, congress-legislators,
House Clerk / senate.gov XML from step 1). Output: /workspace/seating/v3data/*.csv (+ pack JSON).
"""
import json, csv, re, os, sys, glob, collections, datetime, unicodedata, gzip
import yaml
SRC = '/workspace/seating/src'; OUT = '/workspace/seating/v3data'
sys.path.insert(0, os.path.dirname(__file__))
from geo_match import match as geo_match
import openstates_metadata as M
os.chdir(SRC)
SNAP = '2026-10-18'
FIPS = dict(AL='01',AK='02',AZ='04',AR='05',CA='06',CO='08',CT='09',DE='10',FL='12',GA='13',HI='15',ID='16',IL='17',IN='18',IA='19',KS='20',KY='21',LA='22',ME='23',MD='24',MA='25',MI='26',MN='27',MS='28',MO='29',MT='30',NE='31',NV='32',NH='33',NJ='34',NM='35',NY='36',NC='37',ND='38',OH='39',OK='40',OR='41',PA='42',RI='44',SC='45',SD='46',TN='47',TX='48',UT='49',VT='50',VA='51',WA='53',WV='54',WI='55',WY='56')
ST50 = sorted(FIPS)

# ---------------- dictionaries ----------------
PARTIES = [  # code, key (v3 party_key), bot code (Election Data lane), name
 (0,'vac','','Vacant'), (1,'dem','DEM','Democratic'), (2,'rep','REP','Republican'),
 (3,'ind','IND','Independent / unaffiliated'), (4,'np','NP','Nonpartisan (no party label)'),
 (5,'prog','PRO','Vermont Progressive'), (6,'fwd','FWD','Forward'), (7,'lib','LIB','Libertarian'), (8,'grn','GRN','Green'), (9,'unk','','Unknown'), (10,'oth','OTH','Other party')]
P = {k: c for c, k, _, _ in PARTIES}
def pcode(s):
    s = (s or '').strip().lower()
    if not s: return P['vac']
    if s.startswith('democrat') or s.startswith('dfl'): return P['dem']
    if s.startswith('republican'): return P['rep']
    if 'progressive' in s: return P['prog']
    if s.startswith('forward'): return P['fwd']
    if s.startswith('libertarian'): return P['lib']
    if s.startswith('green'): return P['grn']
    if s == 'nonpartisan': return P['np']
    if s in ('independent','unaffiliated','unenrolled','undeclared','no affiliation','no  affiliation','no party','none'): return P['ind']
    return P['unk']
SEL = [(0,'none','Not a court'), (1,'partisan','Partisan election'), (2,'partisan_retention','Partisan election, then retention elections for later terms'),
       (3,'party_nominated_nonpartisan','Party-nominated, nonpartisan ballot (Michigan)'), (4,'nonpartisan','Nonpartisan election'),
       (5,'retention','Appointment, then retention elections')]
SELC = {k: c for c, k, _ in SEL}
HOW = {'E': 'elected (general)', 'S': 'elected (special)', 'A': 'appointed', 'R': 'party switch / caucus change (same person)', '': 'unknown'}

people = {}  # key -> (idx, name)
def person(key, name):
    if key not in people: people[key] = (len(people) + 1, name)   # 0 reserved for vacant
    return people[key][0]
bodies, seats, terms, contests, court_detail, xcheck = [], [], [], [], [], []
def add_body(**kw):
    kw['b'] = len(bodies); bodies.append(kw); return kw['b']

def iso(s):
    s = (s or '').strip()
    for f in ('%B %d, %Y', '%b %d, %Y', '%Y-%m-%d'):
        try: return datetime.datetime.strptime(s, f).strftime('%Y-%m-%d')
        except ValueError: pass
    m = re.match(r'^(\d{4})$', s)
    return m.group(1) if m else ''

# ---------------- US Senate + House (2017-01-03 .. snapshot) ----------------
WIN0 = '2017-01-03'
leg = json.load(open('cl/legislators-current.json')) + json.load(open('cl/legislators-historical.json'))
cl_party = {'Democrat': P['dem'], 'Republican': P['rep'], 'Independent': P['ind'], 'Libertarian': P['lib']}
sen_b = add_body(key='us-senate', st='US', kind='L', office='us_senate', name='United States Senate', seats=100, majority=51,
                 unit_type='state', term='6', stagger='thirds', last_el='2024-11-05', next_el='2026-11-03', sel=0,
                 complete_from=WIN0, src='congress-legislators;senate.gov', note='VP breaks 50-50 ties')
house_b = add_body(key='us-house', st='US', kind='L', office='us_house', name='United States House of Representatives', seats=435, majority=218,
                   unit_type='cd', term='2', stagger='none', last_el='2024-11-05', next_el='2026-11-03', sel=0,
                   complete_from=WIN0, src='congress-legislators;clerk.house.gov', note='delegates excluded (non-voting)')
sen_seat = {}; house_seat = {}
for st in ST50:
    for c in (1, 2, 3):
        # only two classes per state exist
        pass
ivals = []
for p in leg:
    bg = p['id'].get('bioguide')
    nm = p['name'].get('official_full') or (p['name']['first'] + ' ' + p['name']['last'])
    for t in p['terms']:
        if t['end'] <= WIN0 or t['start'] > SNAP: continue
        if t['state'] not in FIPS: continue   # delegates / territories
        affs = t.get('party_affiliations') or [dict(start=t['start'], end=t['end'], party=t['party'], caucus=t.get('caucus'))]
        for a in affs:
            if a['end'] <= WIN0 or a['start'] > SNAP: continue
            ivals.append(dict(ch=t['type'], st=t['state'], cls=t.get('class'), dist=t.get('district'), start=max(a['start'], WIN0),
                              end=a['end'] if a['end'] <= SNAP else '', p=bg, name=nm, party=cl_party.get(a['party'], P['unk']),
                              caucus=cl_party.get(a.get('caucus') or t.get('caucus') or a['party'], P['unk']),
                              how=t.get('how', '')))
# seat slots
for iv in ivals:
    if iv['ch'] == 'sen': sen_seat.setdefault((iv['st'], iv['cls']), None)
    else: house_seat.setdefault((iv['st'], iv['dist']), [])
    if iv['ch'] == 'rep': house_seat[(iv['st'], iv['dist'])].append(iv)
# House slot validity: apportionment periods
APP = [('2013-01-03', '2023-01-03'), ('2023-01-03', '')]
def slot_periods(ivs):
    ps = set()
    for iv in ivs:
        for i, (a, b) in enumerate(APP):
            if iv['start'] < (b or '9999') and (iv['end'] or '9999') > a: ps.add(i)
    return ps
cd119 = {r['geoid']: r for r in csv.DictReader(open(f'{SRC}/us-districts/data-v3/geo/ushouse.csv'))}
assert len(sen_seat) == 100, len(sen_seat)
for i, (st, cls) in enumerate(sorted(sen_seat)):
    sen_seat[(st, cls)] = i
    seats.append(dict(b=sen_b, s=i, dist=f'{st}-{cls}', geoid=FIPS[st], pos=cls, label=f'{st} class {cls}', valid_from='', valid_to='',
                      up26=1 if cls == 2 or (st, cls) in (('OH', 3), ('FL', 3)) else 0))
hs = sorted(house_seat, key=lambda k: (k[0], k[1]))
for i, (st, d) in enumerate(hs):
    ps = slot_periods(house_seat[(st, d)])
    vf = APP[min(ps)][0] if 0 not in ps else ''
    vt = APP[max(ps)][1] if 1 not in ps else '2023-01-03'
    if 1 in ps: vt = ''
    if 0 in ps: vf = ''
    code = f'{d:02d}'
    g = FIPS[st] + code
    house_seat[(st, d)] = i
    seats.append(dict(b=house_b, s=i, dist=code, geoid=g if (g in cd119 and 1 in ps) else '', pos=1, label=f'{st}-{code}',
                      valid_from=vf, valid_to=vt, up26=1 if 1 in ps else 0))
for iv in ivals:
    b, s = (sen_b, sen_seat[(iv['st'], iv['cls'])]) if iv['ch'] == 'sen' else (house_b, house_seat[(iv['st'], iv['dist'])])
    terms.append(dict(b=b, s=s, start=iv['start'], end=iv['end'], p=person('bioguide:' + iv['p'], iv['name']), party=iv['party'],
                      caucus=iv['caucus'] if iv['caucus'] != iv['party'] else '', how='A' if iv['how'] == 'appointment' else ('S' if iv['how'] == 'special-election' else ''), appt=''))
# check the 2026-10-18 snapshot against the step-1 official rosters
cong = {x: json.load(open(f'/workspace/seating/congress/data/{x}.json')) for x in ('us-senate', 'us-house')}
def at(b, day):
    occ = {}
    for t in terms:
        if t['b'] == b and t['start'] <= day and (not t['end'] or t['end'] > day): occ[t['s']] = t
    return occ
occS, occH = at(sen_b, SNAP), at(house_b, SNAP)
pk = {v[0]: k for k, v in people.items()}
off_s = {s['bioguide_id'] for s in cong['us-senate']['seats']}
off_h = {s['bioguide_id'] for s in cong['us-house']['seats'] if s['status'] == 'filled'}
mine_s = {pk[t['p']].split(':')[1] for t in occS.values()}; mine_h = {pk[t['p']].split(':')[1] for t in occH.values()}
xcheck.append(dict(body='us-senate', check='snapshot vs senate.gov XML (bioguide set)', ok=mine_s == off_s, detail=f'{len(mine_s)} vs {len(off_s)}; diff {sorted(mine_s ^ off_s)}'))
xcheck.append(dict(body='us-house', check='snapshot vs House Clerk MemberData (bioguide set)', ok=mine_h == off_h, detail=f'{len(mine_h)} vs {len(off_h)}; diff {sorted(mine_h ^ off_h)}'))
for day in ('2017-01-03', '2019-01-03', '2021-01-03', '2023-01-03', '2025-01-03', SNAP):
    o = at(house_b, day); c = collections.Counter(t['party'] for t in o.values())
    os_ = at(sen_b, day); cs = collections.Counter(t['caucus'] or t['party'] for t in os_.values())
    xcheck.append(dict(body='us-house', check=f'composition {day}', ok=True, detail=f'D {c[1]} R {c[2]} I {c[3]} vacant {435 - len(o)}'))
    xcheck.append(dict(body='us-senate', check=f'composition by caucus {day}', ok=True, detail=f'D {cs[1]} R {cs[2]} I {cs[3]} vacant {100 - len(os_)}'))

# ---------------- State legislatures ----------------
bp = json.load(open('bp_chambers.json')); ib = json.load(open('bp_infobox.json'))
el26 = json.load(open('bp_elections2026.json'))
osj = json.load(open('openstates_current.json'))
wps = json.load(open('wiki_party_strength.json'))
CHNAME = {'upper': 'state_senate', 'lower': 'state_house', 'legislature': 'state_senate'}
def norm(s): return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
def dkey(s):
    s = norm(s).replace('-', ' ').replace(',', ' ')
    s = re.sub(r'\b(and|district)\b', ' ', s)
    return ' '.join(s.split())
def lastname(s):
    s = re.sub(r'\b(jr|sr|ii|iii|iv)\b\.?', '', norm(s)).replace(',', ' ')
    return s.split()[-1] if s.split() else ''
for st in ST50:
    meta = M.lookup(abbr=st)
    for ch in (['legislature'] if meta.unicameral else ['upper', 'lower']):
        k = f'{st}_{ch}'; rows = bp[k]['rows']; info = ib[k]
        term = {'2 years': '2', '4 years': '4', '2-4-4 year system': '2-4-4'}.get(info['term'], info['term'])
        e = el26.get(k) or {}
        b = add_body(key=f'us-{st.lower()}-' + ({'upper': 'senate', 'lower': 'house', 'legislature': 'legislature'}[ch]), st=st, kind='L',
                     office=CHNAME[ch], name=bp[k]['title'], seats=len(rows), majority=len(rows) // 2 + 1,
                     unit_type='sldu' if ch != 'lower' else 'sldl', term=term, stagger='', last_el=iso(info['last']), next_el=iso(info['next']), sel=0,
                     complete_from=SNAP, src='ballotpedia;openstates', note='')
        # 2026 seats up (district label -> number of seats up)
        up = collections.Counter()
        for dlab, cand in zip(e.get('districts', []), e.get('candidates', [])):
            m = re.match(r'^(?:District\s+)?(.*?)(?:\s+\((\d+) seats\))?$', dlab)
            up[dkey(m.group(1))] += int(m.group(2) or 1)
        nup = sum(up.values())
        bodies[b]['stagger'] = ('all' if nup == len(rows) else 'partial' if nup else ('none_2026' if e.get('page') is not None else ''))
        # Open States lookup for person ids: district -> [(last, id, name)]
        osd = collections.defaultdict(list)
        for m_ in osj[st][ch]['members']:
            osd[norm(m_['district'])].append(m_)
        pos = collections.Counter(); used = set()
        for i, r in enumerate(rows):
            g = geo_match(st, ch, r['district'])
            dk = dkey(r['district'])
            pos[r['district']] += 1
            u = ''
            if e.get('page'):
                # match on label (WA "1-Position 2", ID "1A", NH "Belknap 2") or on bare district
                cand_keys = [dk, re.sub(r'\s*position.*$', '', dk).strip(), re.sub(r'^(\d+)[ab]$', r'\1', dk)]
                hit = next((ck for ck in cand_keys if up.get(ck, 0) > 0), None)
                if hit: up[hit] -= 1; u = 1
                else: u = 0
            seats.append(dict(b=b, s=i, dist=g[1] if g else r['district'], geoid=g[0] if g else '', pos=pos[r['district']],
                              label=r['district'], valid_from='', valid_to='', up26=u))
            if r['name'] == 'Vacant': continue
            ln = lastname(r['name'])
            om = [m_ for m_ in osd.get(norm(re.sub(r'\s*-\s*Position.*$', '', r['district'])), []) + osd.get(norm(r['district']), []) if lastname(m_['name']) == ln and m_['id'] not in used]
            if not om:   # some sources label districts differently; fall back to name-only within chamber
                om = [m_ for m_ in osj[st][ch]['members'] if lastname(m_['name']) == ln and norm(m_['name'].split()[0])[:3] == norm(r['name'].split()[0])[:3] and m_['id'] not in used]
            if om:
                used.add(om[0]['id']); key = 'os:' + om[0]['id'].split('/')[-1]
            else:
                key = 'bp:' + (r['link'] or '').rstrip('/').split('/')[-1] if r['link'] else 'bp:' + r['name'].replace(' ', '_')
            terms.append(dict(b=b, s=i, start=iso(r['since']), end='', p=person(key, r['name']), party=pcode(r['party']), caucus='', how='', appt=''))
        left = sum(v for v in up.values() if v > 0)
        # cross-checks
        c = collections.Counter(pcode(r['party']) for r in rows)
        n_os = len(osj[st][ch]['members']); n_meta = osj[st][ch]['num_seats']
        oth = len(rows) - c[1] - c[2] - c[0]
        ibd = (int(info['dem'] or 0), int(info['rep'] or 0), int(re.match(r'\d+', info['other'] or '0').group(0)), int(info['vac'] or 0))
        xcheck.append(dict(body=bodies[b]['key'], check='Ballotpedia member table vs Ballotpedia infobox (D,R,other,vacant)', ok=(c[1], c[2], oth, c[0]) == ibd, detail=f'table {(c[1], c[2], oth, c[0])} infobox {ibd}'))
        xcheck.append(dict(body=bodies[b]['key'], check='seat count vs Open States metadata', ok=len(rows) == n_meta, detail=f'{len(rows)} vs {n_meta}'))
        osc = collections.Counter(pcode(m_['party'].split('/')[0]) for m_ in osj[st][ch]['members'])
        xcheck.append(dict(body=bodies[b]['key'], check='filled seats and D/R vs Open States people repo (official sites)', ok=(osc[1], osc[2], n_os) == (c[1], c[2], len(rows) - c[0]),
                           detail=f'OS D{osc[1]} R{osc[2]} filled {n_os} | BP D{c[1]} R{c[2]} filled {len(rows) - c[0]}'))
        if e.get('page') is not None:
            xcheck.append(dict(body=bodies[b]['key'], check='2026 seats up: matched to seats vs Ballotpedia open-seat table total', ok=left == 0 and str(nup) == str(e.get('open_table_total') or nup),
                               detail=f'up {nup} (unmatched {left}), open-seat table {e.get("open_table_total")}'))
        w = wps.get(meta.name, {}).get('senate' if ch != 'lower' else 'house', '')
        nums = [int(x) for x in re.findall(r'(\d+)\s*[–-]\s*(\d+)', w)[0]] if re.findall(r'(\d+)\s*[–-]\s*(\d+)', w) else []
        if nums and 'Coalition' not in w and 'nonpartisan' not in w.lower():
            hi, lo = sorted([c[1], c[2]], reverse=True)
            wh, wl = nums[0], nums[1]
            exact = (wh, wl) == (hi, lo)
            slack = c[0] + oth
            ok = exact or (wh >= hi and wl >= lo and (wh - hi) + (wl - lo) <= slack) or (abs(wh - hi) + abs(wl - lo) <= 1 and slack == 0 and False)
            xcheck.append(dict(body=bodies[b]['key'], check='D/R vs Wikipedia "Political party strength in U.S. states"', ok=ok,
                               detail=f'wiki "{w}" | BP D{c[1]} R{c[2]} other {oth} vacant {c[0]}' + ('' if exact else (' | difference within vacancies+others (Wikipedia credits vacant seats to last party)' if ok else ' | REAL MISMATCH'))))
        # contests 2026 with candidates (party slot -> names)
        for dlab, cand in zip(e.get('districts', []), e.get('candidates', [])):
            m = re.match(r'^(.*?)(?:\s+\((\d+) seats\))?$', dlab)
            g = geo_match(st, ch, m.group(1)) or geo_match(st, ch, re.sub(r'^District\s+', '', m.group(1)))
            for slot, lst in cand.items():
                for c_ in lst:
                    contests.append(dict(b=b, year=2026, geoid=g[0] if g else '', n_up=int(m.group(2) or 1), district=m.group(1), slot=slot, name=c_['name'], party=c_['party'], incumbent=int(c_['inc']), bp=c_['bp']))
        if st == 'NE': bodies[b]['note'] = 'officially nonpartisan; party = registration reported by Ballotpedia'
        if st == 'AK': bodies[b]['note'] = 'bipartisan majority coalition (Wikipedia: Coalition ' + (w.split('Coalition')[-1].strip() if 'Coalition' in w else '?') + ')'
        if st == 'ME' and ch == 'lower': bodies[b]['note'] = '151 voting seats; non-voting tribal representatives excluded'
        if st == 'NH' and ch == 'lower': bodies[b]['note'] = 'floterial districts have no TIGER polygon (geoid empty)'

# ---------------- Courts ----------------
bc = json.load(open('bp_courts.json')); wt = json.load(open('wiki_court_tables.json'))
METHOD = {  # court key -> selection code (Ballotpedia method string kept in src_method)
 'AL_SC': 'partisan', 'IL_SC': 'partisan_retention', 'LA_SC': 'partisan', 'NM_SC': 'partisan_retention', 'NC_SC': 'partisan', 'OH_SC': 'partisan',
 'PA_SC': 'partisan_retention', 'TX_SC': 'partisan', 'TX_CCA': 'partisan', 'MI_SC': 'party_nominated_nonpartisan',
 **{f'{s}_SC': 'nonpartisan' for s in 'AR GA ID KY MN MS MT NV ND OR WA WV WI'.split()},
 **{f'{s}_SC': 'retention' for s in 'AK AZ CA CO FL IN IA KS MD MO NE OK SD TN UT WY'.split()}, 'OK_CCA': 'retention'}
# User exclusion (2026-10-18): these courts are removed entirely (no body, seats, terms, people, results).
DROP_COURTS = {'CA_SC', 'KS_SC', 'WV_SC'}
for _k in DROP_COURTS: METHOD.pop(_k, None)
EXCLUDED = sorted(k for k in bc if k not in METHOD and k not in DROP_COURTS)
def wiki_rows(k):
    v = wt.get(k)
    if not v: return []
    hdr = v['headers']; out = []; prev = None
    for r in v['rows']:
        if '_cells' in r:
            c = r['_cells']
            if prev and len(c) < len(hdr): c = prev[:len(hdr) - len(c)] + c
            if len(c) != len(hdr): continue
            r = dict(zip(hdr, c))
        prev = [r.get(h, '') for h in hdr]; out.append(r)
    return out
for k, sel in METHOD.items():
    st, typ = k.split('_'); v = bc[k]
    rows = v['rows']
    wr = wiki_rows(k)
    def wfind(name):
        ln = lastname(name)
        for r in wr:
            if ln and (ln in norm(r.get('Name', '') or next(iter(r.values()), '')) or ln[:5] in norm(r.get('Name', ''))): return r
        return {}
    scols = [h for h in (wt.get(k) or {}).get('headers', []) if h in ('District', 'Circuit', 'Grand Division', 'Seat', 'Place', 'Position')]
    seatcol = '/'.join(scols) if scols else None
    for r in wr: r[seatcol or '_'] = ' '.join(r.get(h, '') for h in scols).strip()
    items = []
    for r in rows:
        w = wfind(r['name']) if r['name'] != 'Vacant' else {}
        items.append((r, w))
    def sk(it):
        lab = (it[1].get(seatcol, '') if seatcol else '') or ''
        m = re.search(r'\d+', lab)
        return (int(m.group(0)) if m else 99, lab, it[0]['name'])
    if seatcol: items.sort(key=sk)
    termy = re.match(r'\d+', v['term'] or '')
    b = add_body(key=f'us-{st.lower()}-' + ('supreme-court' if typ == 'SC' else 'court-of-criminal-appeals'), st=st, kind='C',
                 office='state_supreme_court' if typ == 'SC' else 'state_court_criminal_appeals', name=v['title'], seats=len(rows), majority=len(rows) // 2 + 1,
                 unit_type='none', term=termy.group(0) if termy else (v['term'] or ''), stagger='staggered', last_el='', next_el='', sel=SELC[sel],
                 complete_from=SNAP, src='ballotpedia;wikipedia', note=f'Ballotpedia method: {v["method"]}' + (f'; seats by {seatcol}' if seatcol else ''))
    for i, (r, w) in enumerate(items):
        lab = w.get(seatcol, '') if seatcol else ''
        te = w.get('Term ends', '') or w.get('Term Ends', '')
        ty = re.search(r'(20\d\d)', te); up = ''
        if ty and sel != 'none':
            y = int(ty.group(1)); up = 1 if (y == 2026 or (y == 2027 and re.search(r'Jan', te))) else 0
        seats.append(dict(b=b, s=i, dist=lab, geoid='', pos=1, label=lab or f'seat {i + 1}', valid_from='', valid_to='', up26=up))
        if r['name'] == 'Vacant': continue
        key = 'bp:' + (r['link'] or '').rstrip('/').split('/')[-1] if r['link'] else 'bp:' + r['name'].replace(' ', '_')
        ab = r['appointed_by'] or ''
        wa = re.sub(r'—\s*N/a', '', w.get('Appointer', '') or w.get('Appointed by', '') or '').strip()
        govparty = re.search(r'\((D|R|DFL|I)\)', ab) or re.search(r'\((D|R|DFL|I)\)', wa)
        apc = {'D': P['dem'], 'DFL': P['dem'], 'R': P['rep'], 'I': P['ind']}.get(govparty.group(1)) if govparty else ''
        how = 'A' if govparty else ('E' if ab in ('Elected', 'Election') or wa == '' and ab == '' else '')
        party = pcode(r['party'])
        terms.append(dict(b=b, s=i, start=iso(r['since']), end='', p=person(key, r['name']), party=party, caucus='', how=how, appt=apc))
        chief = int(bool(v['chief']) and lastname(v['chief']) == lastname(r['name']))
        court_detail.append(dict(b=b, s=i, p=people[key][0], appointer=re.sub(r'\s*\(.*\)', '', ab if govparty and re.search(r'\(', ab) else wa) if govparty else '',
                                 appt_party=apc, chief=chief, term_ends=te, wiki_party=w.get('Party', '')))
        if ab and govparty is None and ab not in ('Elected', 'Election') and 'Supreme Court' not in ab:
            xcheck.append(dict(body=bodies[b]['key'], check='appointer parse', ok=False, detail=f'{r["name"]}: "{ab}"'))
        if re.search(r'\((D|R)\)', ab) and re.search(r'\((D|R)\)', wa) and re.search(r'\((D|R)\)', ab).group(1) != re.search(r'\((D|R)\)', wa).group(1):
            xcheck.append(dict(body=bodies[b]['key'], check='appointer party Ballotpedia vs Wikipedia', ok=False, detail=f'{r["name"]}: BP {ab} / wiki {wa}'))
    nw = len(wr); nb = len([r for r in rows if r['name'] != 'Vacant'])
    miss = [r['name'] for r, w in items if r['name'] != 'Vacant' and not w]
    xcheck.append(dict(body=bodies[b]['key'], check='justices: Ballotpedia vs Wikipedia current-court table', ok=not miss and nw >= nb,
                       detail=f'BP filled {nb}, wiki rows {nw}, not found on wiki: {miss}'))

# ---------------- City councils + mayors (30 most populous cities, incl. consolidated and DC councils) ----------------
import city_councils as CC
city_bodies, city_detail, cxc, city_skipped = CC.build(add_body, seats, terms, person, P, SELC, SNAP)
xcheck += cxc
for b_ in bodies: b_.setdefault('geoid', ''); b_.setdefault('entity', '')
for s_ in seats: s_.setdefault('role', '')

# ---------------- write ----------------
os.makedirs(OUT, exist_ok=True)
def wcsv(name, rows, cols):
    with open(f'{OUT}/{name}', 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(cols)
        for r in rows: w.writerow(['' if r.get(c) is None else (int(r[c]) if isinstance(r[c], bool) else r[c]) for c in cols])
wcsv('bodies.csv', bodies, ['b', 'key', 'st', 'kind', 'office', 'name', 'seats', 'majority', 'unit_type', 'term', 'stagger', 'last_el', 'next_el', 'sel', 'complete_from', 'src', 'note', 'geoid', 'entity'])
wcsv('seats.csv', seats, ['b', 's', 'dist', 'geoid', 'pos', 'label', 'valid_from', 'valid_to', 'up26', 'role'])
wcsv('people.csv', [dict(p=v[0], key=k, name=v[1]) for k, v in sorted(people.items(), key=lambda x: x[1][0])], ['p', 'key', 'name'])
terms.sort(key=lambda t: (t['b'], t['s'], t['start']))
wcsv('terms.csv', terms, ['b', 's', 'start', 'end', 'p', 'party', 'caucus', 'how', 'appt'])
wcsv('court_detail.csv', court_detail, ['b', 's', 'p', 'appointer', 'appt_party', 'chief', 'term_ends', 'wiki_party'])
wcsv('contests_2026.csv', contests, ['b', 'year', 'geoid', 'district', 'n_up', 'slot', 'party', 'incumbent', 'name', 'bp'])
wcsv('city_bodies.csv', city_bodies, ['b', 'mayor_b', 'geoid', 'entity', 'place', 'pop2025', 'census_rank', 'n_district', 'n_atlarge', 'n_mayor_seat', 'seat_mix', 'partisan', 'mayor_role', 'mayor_veto', 'council_url', 'bp_page', 'consolidated', 'corrections'])
wcsv('city_detail.csv', city_detail, ['b', 's', 'p', 'party_label', 'affil', 'assumed', 'term_ends', 'office'])
wcsv('parties.csv', [dict(code=c, key=k, bot=b_, name=n) for c, k, b_, n in PARTIES], ['code', 'key', 'bot', 'name'])
wcsv('selection_methods.csv', [dict(code=c, key=k, name=n) for c, k, n in SEL], ['code', 'key', 'name'])
wcsv('crosscheck.csv', xcheck, ['body', 'check', 'ok', 'detail'])
json.dump(dict(excluded_courts=EXCLUDED, dropped_courts=sorted(DROP_COURTS), court_min_year=2017, skipped_cities=city_skipped, city_estimates='Census Vintage 2025 sub-est2025 SUMLEV 162', snapshot=SNAP), open(f'{OUT}/build_meta.json', 'w'), indent=1)
import shutil
os.makedirs(f'{OUT}/base', exist_ok=True)
for fn_ in ('bodies.csv', 'people.csv', 'terms.csv', 'seats.csv', 'court_detail.csv', 'city_detail.csv'): shutil.copy(f'{OUT}/{fn_}', f'{OUT}/base/{fn_}')   # results builder reads these
print('bodies', len(bodies), 'seats', len(seats), 'people', len(people), 'terms', len(terms), 'contests', len(contests))
print('xcheck fails', sum(1 for x in xcheck if not x['ok']))
