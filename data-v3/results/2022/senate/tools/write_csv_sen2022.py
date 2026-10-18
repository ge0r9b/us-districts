#!/usr/bin/env python3
"""Write data-v3/results/2022/senate/*.csv: the 13 bot columns, then boundary_set (column 14, Q-E12) and the optional method (column 15, Q-E3).
usage: write_csv_sen2022.py <repo> <work_dir> <clerk_senate.json> <raw_dir>
 state    : Clerk of the House, Statistics of the Nov 8 2022 election (GA general from its footnote; GA Dec 6 runoff as listed) (official), every candidate; fusion lines merged into their candidate.
 county   : MEDSL 2022 precinct returns (CA: SWDB 2022 SOV) summed by county (d slot, r, all-others).          method=retabulated
 precinct : MEDSL 2022 precincts bridged 1:1 (or as a whole town) to a v2 2024 precinct polygon. method=official (MEDSL precinct row)
 districts: polygons area-weighted into v2's current districts.                          method=retabulated, or area_weighted (= ≈)
Files over ~5 MB are gzipped (same rule as data-v3/geo); all precinct files are gzipped to stay lean. 2022: precinct polygons are v2's 2024 polygons."""
import sys, os, csv, json, gzip, re, io, datetime, collections
sys.path.insert(0, os.path.dirname(__file__)); from races22 import *
repo, wd, clerkj, raw = sys.argv[1:5]
OUT = f'{repo}/data-v3/results/2022/senate'; os.makedirs(OUT + '/precincts', exist_ok=True)
# Q-E12: boundary_set is column 14 (right after retrieved_at); the optional method column is column 15.
# Values are lowercase with hyphens (e.g. tiger-2020, v2-2016-precincts). Every row here, state rows included, is v2-2024.
BOUNDARY_SET = 'v2-2024'
COLS = ['state','year','office','district','unit_id','unit_type','candidate_id','answer','party','votes','weight','source_url','retrieved_at','boundary_set','method']
CLERK = 'https://clerk.house.gov/member_info/electionInfo/2022/statistics2022.pdf'
SWDB = 'https://statewidedatabase.org/pub/data/G22/state/state_g22_sov_data_by_g22_srprec.zip'
IDSOS = 'https://archive.sos.idaho.gov/elections/data/results/2022/2022_General_Canvass.zip'
INIED = 'https://enr.indianavoters.in.gov/archive/2022General/download/AllOfficeResults.csv'
MURL = lambda ab: {'CA': SWDB, 'ID': IDSOS, 'IN': INIED}[ab] if ab in ('CA', 'ID', 'IN') else f'https://github.com/MEDSL/2022-elections-official/raw/main/individual_states/2022-{ab.lower()}-local-precinct-general.zip'
RAWZ = lambda raw, ab: {'CA': f'{raw}/state_g22_sov_data_by_g22_srprec.zip', 'ID': f'{raw}/id_sos/2022_General_Canvass.zip', 'IN': f'{raw}/in_ied/AllOfficeResults.csv'}[ab] if ab in ('CA', 'ID', 'IN') else f'{raw}/2022-{ab.lower()}.zip'
def ts(p): return datetime.datetime.fromtimestamp(os.path.getmtime(p), datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
SLUG = {'Lisa Blunt Rochester': 'blunt-rochester-lisa', 'Debbie Mucarsel-Powell': 'mucarsel-powell-debbie'}
def slug(n):
    if n in SLUG: return SLUG[n]
    m = re.sub(r'“[^”]*”|"[^"]*"', '', n)
    if len(m.replace(',', ' ').split()) < 2: m = re.sub(r'[“”"]', '', n)   # Clerk prints only the nickname as first name ("“Luke” Mixon")
    n = m.replace('.', '').replace(',', ' ')
    w = [x for x in re.split(r'\s+', n.strip()) if x]
    suf = [x for x in w if x.upper() in ('JR', 'SR', 'II', 'III')]; w = [x for x in w if x not in suf]
    return '-'.join([w[-1]] + w[:-1] + suf).lower() if w else 'unknown'
PARTY = {'Republican':'REP','Democrat':'DEM','Democratic-Nonpartisan League':'DEM','Independent':'IND','Libertarian':'LIB','Green':'GRN','By Petition':'IND','Constitution':'CON','Unaffiliated':'UNA','Independent American':'IAP','No Party':'NPA','LaRouche':'LAR','Other':'OTH'}
office = lambda race: {'regular': 'us_senate', 'special': 'us_senate_special', 'runoff': 'us_senate_runoff'}[race]
GEO = {}; STF = {}
for lay in ('counties', 'ushouse', 'senate', 'statehouse', 'schools'):
    for r in csv.DictReader(open(f'{repo}/data-v3/geo/{lay}.csv')):
        GEO[(lay, r['state'], r['v2_name'])] = (r['geoid'], r['tiger_set']); STF[r['state']] = r['geoid'][:2]
def write(name, rows, gz=False):
    b = io.StringIO(); w = csv.writer(b, lineterminator='\n'); w.writerow(COLS); w.writerows([list(x[:13]) + [BOUNDARY_SET] + list(x[13:]) for x in rows]); s = b.getvalue().encode()
    p = f'{OUT}/{name}'
    for q in (p, p + '.gz'):
        if os.path.exists(q): os.remove(q)
    if gz or len(s) > 5_000_000: p += '.gz'; open(p, 'wb').write(gzip.compress(s, 9, mtime=0))
    else: open(p, 'wb').write(s)
    return p, os.path.getsize(p), len(rows)
files = []
# ---- state rows
clerk = json.load(open(clerkj)); rt_c = ts(f'{raw}/clerk_statistics2022.pdf')
DR = {}; srows = []; OFF = {}
for stn, secs in clerk.items():
    ab = USPS[stn]; cs = [c for s in secs for c in s['c']]
    SPL = {'CA': 2, 'OK': 4}
    parts = {'special': cs[:SPL[ab]], 'regular': cs[SPL[ab]:]} if ab in SPL else {'regular': cs}
    if ab == 'GA':   # Clerk prints the Dec 6 runoff for Walker/Warnock; the Nov 8 general is in its footnote
        parts = {'regular': [['Herschel Junior Walker, Republican', 1908442], ['Raphael G. Warnock, Democrat', 1946117], ['Chase Oliver, Libertarian', 81365]],
                 'runoff': [['Herschel Junior Walker, Republican', 1721244], ['Raphael G. Warnock, Democrat', 1820633]]}
    for race, lst in parts.items():
        cand = collections.OrderedDict(); prev = None
        for nm, v in lst:
            nm = re.sub(r'\s*\(For (full|unexpired) term.*?\)|\s+[A-Z ]+—Continued', '', nm)
            if is_nonvote(nm): continue
            wi = re.search(r'write|scatter|other', nm, re.I) is not None
            if ',' not in nm and prev and not wi: cand[prev][2] += v; continue   # fusion line (Working Families, Conservative)
            if ',' in nm: person, party = [x.strip() for x in nm.split(',', 1)]
            else: person, party = nm, ''
            if person.upper().startswith(('ROBERT P', 'ANGUS S')) and party.startswith('Jr'): pass
            if party.startswith('Jr'):   # "Angus S. King, Jr., Independent"
                person += ' Jr'; party = party.split(',', 1)[1].strip() if ',' in party else ''
            pc = PARTY.get(party, 'WRI' if (wi or 'Write-in' in party) else (re.sub(r'[^A-Z]', '', party.upper())[:10] or 'OTH'))
            cid = slug(person) if ',' in nm and not person.lower().startswith('write') else 'write-ins'
            if cid in cand: cand[cid][2] += v
            else: cand[cid] = [person, pc, v]
            prev = cid
        t = [0, 0, 0]
        for cid, (person, pc, v) in cand.items():
            k = slot(ab, race, person) if cid != 'write-ins' else 'o'
            if k in ('d', 'r'): DR.setdefault((ab, race), {})[k] = (cid, person, pc)
            t[{'d':0,'r':1,'o':2}[k]] += v
            srows.append([ab, 2022, office(race), 'statewide', STF[NAME[ab]], 'state', cid, person, pc, v, 1, CLERK, rt_c, 'official'])
        OFF[(ab, race)] = [t[0], t[1], sum(t)]
files.append(write('us_senate_2022_state.csv', srows))
def tri_rows(ab, race, uid, utype, d, r, t, src, rt, method):
    dd, rr = DR[(ab, race)]['d'], DR[(ab, race)]['r']; o = t - d - r
    if min(d, r, o) < 0: raise ValueError(f'negative value {ab} {race} {utype} {uid}: d={d} r={r} t={t}')   # all-others is apportioned on its own upstream
    out = [[ab, 2022, office(race), 'statewide', uid, utype, dd[0], dd[1], dd[2], d, 1, src, rt, method],
           [ab, 2022, office(race), 'statewide', uid, utype, rr[0], rr[1], rr[2], r, 1, src, rt, method]]
    if o != 0: out.append([ab, 2022, office(race), 'statewide', uid, utype, 'all-others', 'All others', 'OTH', o, 1, src, rt, method])
    return out
# ---- county + precinct rows, from build_sen2022.py reports
crows = []; deltas = []; cov = []; gaps = []
for ab in sorted({k[0] for k in RACES}):
    if not os.path.exists(f'{wd}/{ab}.json'):
        gaps.append([ab, 'regular', 'all', '(state)', 'no county/precinct/district rows: MEDSL 2022 Idaho Senate rows are about 2x the official totals (1,177,836 vs 590,890), cause not found; only the official state rows are kept'])
        continue
    rep = json.load(open(f'{wd}/{ab}.json')); stn = NAME[ab]; rt = ts(RAWZ(raw, ab)); prows = []
    for race in ('regular', 'special', 'runoff'):
        if race not in rep: continue
        R = rep[race]
        for c, (d, r, t) in sorted(R['counties'].items()):
            g = GEO.get(('counties', stn, c))
            if not g: gaps.append([ab, race, 'county', c, 'no GEOID in data-v3/geo/counties.csv']); continue
            crows += tri_rows(ab, race, g[0], 'county', d, r, t, MURL(ab), rt, 'retabulated')
        keys = collections.Counter(k.rsplit('|', 1)[0] for k in R['precincts'])
        for k, (d, r, t) in R['precincts'].items():
            c, p, j = k.split('|', 2)[0], k.split('|')[1], k.rsplit('|', 1)[1]
            uid = f'{ab}|{c}|{p}' + (f'|#{j}' if keys[f'{c}|{p}'] > 1 else '')
            prows += tri_rows(ab, race, uid, 'precinct', d, r, t, MURL(ab), rt, 'official')
        m = R['medsl_state']; o = OFF[(ab, race)]
        deltas.append([ab, race, *o, *m, m[0]-o[0], m[1]-o[1], m[2]-o[2], round(100*(m[2]-o[2])/o[2], 2)])
        cov.append([ab, race, R['medsl_precincts'], R['matched_precincts'], R.get('matched_polys', ''), rep['v2_rows'], R['matched_share']])
        for c, (n, v) in sorted(R['unmatched_by_county'].items(), key=lambda x: -x[1][1]):
            if v > 0: gaps.append([ab, race, 'precinct', c, f'{n} MEDSL precinct(s), {v} votes not matched to a v2 polygon: allocated to the county polygons by president votes (≈ in districts)'])
    files.append(write(f'precincts/{ab}.csv', prows, gz=True))
files.append(write('us_senate_2022_county.csv', crows))
# ---- districts
UT = {'ushouse': 'ushouse', 'senate': 'sldu', 'statehouse': 'sldl'}; SCH = {'unsd': 'school_unified', 'elsd': 'school_elementary', 'scsd': 'school_secondary'}
uni = collections.Counter()
for lay, fn in (('ushouse', 'us_senate_2022_ushouse.csv'), ('senate', 'us_senate_2022_sldu.csv'), ('statehouse', 'us_senate_2022_sldl.csv'), ('schools', 'us_senate_2022_school.csv')):
    drows = []
    for race in ('regular', 'special', 'runoff'):
        if not os.path.exists(f'{wd}/layers_{race}.json'): continue
        L = json.load(open(f'{wd}/layers_{race}.json'))
        for key, v in sorted(L['values'][lay].items()):
            stn, nm = key.split('|', 1); ab = USPS[stn]; g = GEO.get((lay, stn, nm))
            if not g: gaps.append([ab, race, lay, nm, 'no GEOID in data-v3/geo']); continue
            if lay == 'statehouse' and g[1] == 'sldu':   # NE unicameral (and DC): v2's statehouse layer repeats the SLDU districts; v3 has no sldl unit for them
                uni[(ab, race)] += 1; continue
            ut = SCH.get(g[1], 'school_unified') if lay == 'schools' else UT[lay]
            drows += tri_rows(ab, race, g[0], ut, v[0], v[1], v[2], MURL(ab), ts(RAWZ(raw, ab)), 'area_weighted' if len(v) > 3 else 'retabulated')
        for stn, items in L['gray'][lay].items():
            for nm, why in items: gaps.append([USPS[stn], race, lay, nm, f'gray (no value): {why}'])
    files.append(write(fn, drows))
for (ab, race), n in sorted(uni.items()):
    gaps.append([ab, race, 'statehouse', '(all)', f'{n} statehouse districts left out of the sldl file: unicameral legislature, v2 statehouse districts = the state senate (SLDU) districts, whose GEOIDs are not v3 sldl units; the same values are in us_senate_2022_sldu.csv'])
def plain(name, head, rows):
    with open(f'{OUT}/{name}', 'w', newline='') as f: w = csv.writer(f, lineterminator='\n'); w.writerow(head); w.writerows(rows)
    files.append((f'{OUT}/{name}', os.path.getsize(f'{OUT}/{name}'), len(rows)))
plain('statewide_vs_official.csv', ['state','race','official_d','official_r','official_t','medsl_d','medsl_r','medsl_t','delta_d','delta_r','delta_t','delta_t_pct'], deltas)
plain('precinct_match.csv', ['state','race','medsl_precincts','matched_precincts','v2_polygons_with_exact_value','v2_polygons','matched_vote_share'], cov)
plain('GAPS.csv', ['state','race','layer','unit','reason'], gaps)
json.dump({f'{a}|{r}': v for (a, r), v in DR.items()}, open(f'{wd}/dr.json', 'w'))
for p, s, n in files: print(os.path.relpath(p, OUT), s, n)
