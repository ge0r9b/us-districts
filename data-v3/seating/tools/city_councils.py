"""City councils + mayors of the 25 most populous US cities with a city council (imported by build_v3data.py).
Inputs (all cached under src/city/): cities.json (curated structure/calendar), sub-est2025.csv (Census Vintage 2025
place estimates), bp/<City,_ST>.html (Ballotpedia city pages: council member table, mayor), bp/mayors100.html (Ballotpedia
list of current mayors of the top 100 cities). Keys are deterministic: us-<st>-<place-slug>-city-council / -mayor, where
place-slug = Census place NAME minus the trailing LSAD word ('city'), lowercased, non-alphanumerics -> '-'.
"""
import json, re, csv, datetime, unicodedata
from bs4 import BeautifulSoup
CITY = '/workspace/seating/src/city'

def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')

def iso(s):
    s = (s or '').strip()
    for f in ('%B %d, %Y', '%b %d, %Y', '%Y-%m-%d'):
        try: return datetime.datetime.strptime(s, f).strftime('%Y-%m-%d')
        except ValueError: pass
    m = re.match(r'^(\d{4})$', s)
    return m.group(1) if m else ''

def census_rank():
    rows = [r for r in csv.DictReader(open(f'{CITY}/sub-est2025.csv', encoding='latin1')) if r['SUMLEV'] == '162']
    rows.sort(key=lambda r: -int(r['POPESTIMATE2025']))
    return {r['STATE'] + r['PLACE']: (i + 1, int(r['POPESTIMATE2025']), r['NAME']) for i, r in enumerate(rows)}

def seat_label(office):
    t = office.split('Council', 1)[-1].strip()
    m = re.match(r'(?i)at-large(?: (?:position|seat) (\w+))?$', t)
    if m: return ('AL' + (m.group(1) or ''), 'at-large')
    m = re.match(r'(?i)position (\d+) at-large$', t)
    if m: return ('AL' + m.group(1), 'at-large')
    m = re.match(r'(?i)super district (\d+)(?: position (\d+))?$', t)
    if m: return ('SD' + m.group(1), 'super-district')
    m = re.match(r'(?i)(?:district|ward) (\w+)$', t)
    if m: return (m.group(1), 'district')
    if re.match(r'(?i)president$', t): return ('PRES', 'president-at-large')
    return (t, 'other')

PARTY_MAP = {'Democratic': 'dem', 'Democrat': 'dem', 'Republican': 'rep', 'Nonpartisan': 'np', 'Independent': 'ind', '': 'unk'}

def build(add_body, seats, terms, person, P, SELC, SNAP):
    cfg = json.load(open(f'{CITY}/cities.json'))
    rank = census_rank()
    m100 = {}
    s = BeautifulSoup(open(f'{CITY}/bp/mayors100.html').read(), 'lxml')
    t = [t for t in s.find_all('table') if len(t.find_all('tr')) > 50][0]
    for r in t.find_all('tr')[1:]:
        c = r.find_all('td')
        if len(c) < 8: continue
        a = c[3].find('a')
        m100[c[1].get_text(strip=True).replace(' ', '_')] = dict(name=a.get_text(' ', strip=True) if a else c[3].get_text(' ', strip=True),
            bp=a['href'].split('/')[-1] if a else '', party=c[3].get('aria-label', ''), took=c[4].get_text(strip=True), ends=c[5].get_text(strip=True),
            gov=c[6].get_text(strip=True), el26=c[7].get_text(strip=True))
    city_bodies, city_detail, xc = [], [], []
    for c in cfg['cities']:
        rk, pop, cname = rank[c['geoid']]
        place = re.sub(r'\s+(city|town|village|municipality|metropolitan government|consolidated government)(\s+\(balance\))?$', '', cname)
        base = f"us-{c['st'].lower()}-{slug(place)}"
        page = BeautifulSoup(open(f"{CITY}/bp/{c['bp']}.html").read(), 'lxml'); txt = page.get_text(' ', strip=True)
        # council table = first Office/Name table whose offices contain 'City Council'
        rows = None
        for tb in page.find_all('table'):
            tr = tb.find('tr'); hdr = [x.get_text(' ', strip=True) for x in tr.find_all(['th', 'td'])] if tr else []
            if hdr[:2] != ['Office', 'Name']: continue
            rr = []
            for r in tb.find_all('tr')[1:]:
                cs = r.find_all(['td', 'th']); v = [x.get_text(' ', strip=True) for x in cs]
                a = cs[1].find('a') if len(cs) > 1 else None
                rr.append(dict(office=v[0], name=v[1], party=v[2] if len(v) > 2 else '', since=v[3] if len(v) > 3 else '', ends=v[4] if len(v) > 4 else '',
                               bp=a['href'].rstrip('/').split('/')[-1] if a and a.has_attr('href') else ''))
            if any('City Council' in x['office'] or 'Oklahoma City Council' in x['office'] for x in rr): rows = rr; break
        # Denver: Ballotpedia lists a generic 'At-large' vacancy row besides 'Seat A'/'Seat B' -> keep the lettered rows;
        # the filled generic at-large row is Seat A (official site / 2027 filings: Gonzales-Gutierrez = Seat A)
        if c['bp'].startswith('Denver'):
            filled = [r for r in rows if r['office'].endswith('At-large') and r['name'] != 'Vacant']
            rows = [r for r in rows if not r['office'].endswith('At-large')]
            for r in rows:
                if r['office'].endswith('Seat A') and r['name'] == 'Vacant' and filled: r.update({k: filled[0][k] for k in ('name', 'party', 'since', 'ends', 'bp')})
            xc.append(dict(body=base + '-city-council', check='Denver at-large rows', ok=True, detail='BP generic At-large rows folded into Seat A/B (Seat B vacant since 2026-08-05; vacancy election 2026-11-03)'))
        # mayor: city page (fresher) first, then the top-100 list
        mm = re.search(r'The current Mayor of [\w .]+? is ([^()]+?) \((\w+)\)\.\s*\w[\w .\'-]* assumed office in (\d{4})', txt)
        ib = re.search(r'Mayor of [A-Z][\w .]+?\s+([A-Z][^\n]{2,40}?)\s+(Democratic|Republican|Nonpartisan|Independent)\s+Assumed office:\s*([A-Za-z]+ \d+, \d{4}|\d{4})', txt)
        L = m100.get(c['bp'], {})
        mname = (mm.group(1).strip() if mm else '') or (ib.group(1).strip() if ib else '') or L.get('name', '')
        msince = iso(ib.group(3)) if ib and ib.group(1).strip() == mname else (mm.group(3) if mm else L.get('took', ''))
        aff = re.search(r'has an? (Democratic|Republican|independent|nonpartisan|Libertarian) mayor', txt)
        mparty_lbl = (aff.group(1) if aff else '') or L.get('party', '')
        mparty_lbl = {'Democratic': 'Democrat', 'independent': 'Independent', 'nonpartisan': 'Nonpartisan'}.get(mparty_lbl, mparty_lbl)
        same = L and L.get('name', '').split(' (')[0].split()[-1].lower() == mname.split()[-1].lower()
        mbp = L.get('bp', '') if same else ''
        if L and not same:
            xc.append(dict(body=base + '-mayor', check='mayor: city page vs top-100 list', ok=False, detail=f"city page {mname} (since {msince}) / list {L.get('name')} (took {L.get('took')}); city page kept"))
        mends = L.get('ends', '')
        # ---- council body
        cseats = []
        for r in rows:
            lab, typ = seat_label(r['office']); cseats.append((lab, typ, r))
        pos = {}
        for i, (lab, typ, r) in enumerate(cseats):
            pos[lab] = pos.get(lab, 0) + 1
        n_mayor = 1 if c['mayor_role'] == 'member' else 0
        n = len(cseats) + n_mayor
        nd = sum(1 for x in cseats if x[1] in ('district', 'super-district')); na = sum(1 for x in cseats if x[1] in ('at-large', 'president-at-large'))
        mix = 'district' if na == 0 else ('mixed' if nd else 'at-large')
        sel = SELC['partisan'] if c['partisan'] else SELC['nonpartisan']
        nb = place + ' City Council' if 'Oklahoma City' not in place else 'Oklahoma City Council'
        b = add_body(key=base + '-city-council', st=c['st'], kind='M', office='city_council', name=nb, seats=n, majority=n // 2 + 1,
                     unit_type='council_district', term=c['term'], stagger=c['stagger'], last_el=c['last_el'], next_el=c['next_el'], sel=sel,
                     complete_from=SNAP, src='ballotpedia;' + c['url'], note=c['next_note'], geoid=c['geoid'], entity='muni:place:' + c['geoid'])
        up_by = '2027-04-30'
        cnt = {}
        s_i = 0
        for lab, typ, r in cseats:
            cnt[lab] = cnt.get(lab, 0) + 1
            k = cnt[lab] if pos[lab] > 1 or lab.startswith('SD') else 1
            ends = iso(r['ends'])
            up = 1 if (c['next_el'].startswith('2026') and (r['name'] == 'Vacant' or (ends and (len(ends) == 4 and ends <= '2026' or len(ends) > 4 and ends <= up_by)))) else 0
            role = {'at-large': 'at-large', 'president-at-large': 'president', 'super-district': 'super-district'}.get(typ, '')
            label = r['office'].split('Council', 1)[-1].strip()
            seats.append(dict(b=b, s=s_i, dist=lab, geoid='', pos=k, label=label, valid_from='', valid_to='', up26=up, role=role))
            if r['name'] != 'Vacant':
                key = 'bp:' + r['bp'] if r['bp'] else 'bp:' + r['name'].replace(' ', '_')
                plbl = r['party']
                code = P.get(PARTY_MAP.get(plbl, 'oth'), P['oth'])
                p = person(key, r['name'])
                terms.append(dict(b=b, s=s_i, start=iso(r['since']), end='', p=p, party=code, caucus='', how='', appt=''))
                city_detail.append(dict(b=b, s=s_i, p=p, party_label=plbl, affil='ballot' if c['partisan'] else ('nonpartisan office' if plbl == 'Nonpartisan' else 'known affiliation (Ballotpedia)'),
                                        assumed=r['since'], term_ends=r['ends'], office=r['office']))
            s_i += 1
        if n_mayor:
            seats.append(dict(b=b, s=s_i, dist='MAYOR', geoid='', pos=1, label='Mayor (ex officio, voting)', valid_from='', valid_to='', up26=0, role='mayor'))
        # ---- mayor body (1 seat); mayor elections are nonpartisan except NYC/Philadelphia/Charlotte/Jacksonville/Baltimore -> party = affiliation
        mb = add_body(key=base + '-mayor', st=c['st'], kind='M', office='mayor', name='Mayor of ' + place, seats=1, majority=1, unit_type='place',
                      term='', stagger='none', last_el='', next_el=c['mayor_next'], sel=sel, complete_from=SNAP, src='ballotpedia;' + c['url'],
                      note=f"mayor_role on council: {c['mayor_role']}; veto: {c['veto']}" + (f"; {c['mayor_note']}" if c.get('mayor_note') else ''), geoid=c['geoid'], entity='muni:place:' + c['geoid'])
        seats.append(dict(b=mb, s=0, dist='', geoid=c['geoid'], pos=1, label='Mayor', valid_from='', valid_to='', up26=1 if c['mayor_next'].startswith('2026') else 0, role='mayor'))
        mkey = 'bp:' + mbp if mbp else 'bp:' + mname.replace(' ', '_')
        mp = person(mkey, mname)
        mcode = P.get(PARTY_MAP.get(mparty_lbl, 'oth'), P['unk'])
        mhow = 'A' if c.get('mayor_how') == 'A' else ''
        terms.append(dict(b=mb, s=0, start=c.get('mayor_since') or msince, end='', p=mp, party=mcode, caucus='', how=mhow, appt=''))
        city_detail.append(dict(b=mb, s=0, p=mp, party_label=mparty_lbl, affil='ballot' if c['partisan'] else 'known affiliation (Ballotpedia)', assumed=c.get('mayor_since') or msince,
                                term_ends=c.get('mayor_ends') or mends, office='Mayor'))
        if n_mayor:
            terms.append(dict(b=b, s=s_i, start=c.get('mayor_since') or msince, end='', p=mp, party=mcode, caucus='', how='', appt=''))
        city_bodies.append(dict(b=b, mayor_b=mb, geoid=c['geoid'], entity='muni:place:' + c['geoid'], place=cname, pop2025=pop, census_rank=rk,
                                n_district=nd, n_atlarge=na, n_mayor_seat=n_mayor, seat_mix=mix, partisan=c['partisan'], mayor_role=c['mayor_role'], mayor_veto=c['veto'],
                                council_url=c['url'], bp_page='https://ballotpedia.org/' + c['bp']))
    return city_bodies, city_detail, xc, cfg['skipped']
