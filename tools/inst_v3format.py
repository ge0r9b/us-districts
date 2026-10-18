#!/usr/bin/env python3
"""Step 4 of the officeholder pipeline (run after inst_persons.py): bring every data-v3/inst officeholder-family file to the
v3 Full Stack format. Idempotent; edits in place.

- officeholder files: entity_id = the CHAMBER ENTITY of data-v3/inst/entities.csv ('us-house', 'chamber:al-lower');
  the old slug stays in entity_id_legacy. The unit is unit_layer (cd/sldu/sldl) + unit_geoid + unit_vintage (TIGER year);
  the old token (cd119, sldl2024 ...) stays in unit_plan. seat = the source's seat label where it gives one.
- boundary_set: the unit's boundary-set slug (tiger-2020-cd116, tiger-2020-sldu/-sldl, v2-2024); empty without TIGER geometry.
- every row: source_url as full URLs (' ; '-list), retrieved_at, and source_commit (OpenStates / congress-legislators commit).
- persons.csv, person_id_matches.csv, stateleg_official_diffs.csv get source_url, retrieved_at, source_commit.
usage: inst_v3format.py <repo> [--dir data-v3/inst]
"""
import csv, os, re, sys, collections, urllib.parse
R = sys.argv[1]; D = os.path.join(R, sys.argv[sys.argv.index('--dir') + 1] if '--dir' in sys.argv else 'data-v3/inst')
OHF = ['officeholders_house_current', 'officeholders_house_2024', 'officeholders_house_2020', 'officeholders_stateleg_current', 'officeholders_stateleg_2024']
OS_RE = re.compile(r'github\.com/openstates/people/blob/([0-9a-f]{40})')
CL_RE = re.compile(r'congress-legislators \(commit ([0-9a-f]{40})')
def rd(f):
    with open(os.path.join(D, f + '.csv'), encoding='utf-8', newline='') as fh:
        r = csv.DictReader(fh); return r.fieldnames, list(r)
def wr(f, cols, rows):
    with open(os.path.join(D, f + '.csv'), 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, cols, lineterminator='\n'); w.writeheader(); w.writerows(rows)
def ins(cols, after, new):
    if new in cols: return cols
    i = cols.index(after) + 1 if after in cols else len(cols)
    return cols[:i] + [new] + cols[i:]
def chamber(eid):
    if eid == 'us-house' or eid.startswith('chamber:'): return eid
    m = re.match(r'^([a-z]{2})-(senate|house|legislature)$', eid)
    if not m: raise SystemExit('unknown entity_id ' + eid)
    return 'chamber:%s-%s' % (m.group(1), 'lower' if m.group(2) == 'house' else 'upper')
PLAN = {'cd119': ('cd', '2024'), 'cd116': ('cd', '2020'), 'cd118': ('cd', '2022'),
        'sldu2024': ('sldu', '2024'), 'sldl2024': ('sldl', '2024'), 'sldu2018': ('sldu', '2020'), 'sldl2018': ('sldl', '2020')}
BSET = {'cd116': 'tiger-2020-cd116', 'sldu2018': 'tiger-2020-sldu', 'sldl2018': 'tiger-2020-sldl',
        'cd119': 'v2-2024', 'sldu2024': 'v2-2024', 'sldl2024': 'v2-2024'}
def fullurls(s):
    parts = [p.strip() for p in s.split(' ; ') if p.strip()]
    out = []
    for p in parts:
        if out and re.match(r'^https?://[^ ]*/\.\.\.\w+=', p): p = '...' + p.split('/...', 1)[1]   # repair an earlier bad join
        if re.match(r'^https?://', p) or not out: out.append(p); continue
        base = out[0]
        if p.startswith('...') and '=' in p and '?' in base:      # '...chamber=Senate': same URL, that one parameter changed
            k, v = p[3:].split('=', 1)
            q = re.sub(r'(?i)(^|&)%s=[^&]*' % re.escape(k), lambda m: '%s%s=%s' % (m.group(1), k, v), base.split('?', 1)[1])
            out.append(base.split('?')[0] + '?' + q); continue
        if p.startswith('?'): out.append(base.split('?')[0] + p)
        elif p.startswith('.../'): out.append(base.split('?')[0].rstrip('/').rsplit('/', 1)[0] + '/' + p[4:])
        else: out.append(urllib.parse.urljoin(base.split('?')[0], p))
    return ' ; '.join(out)
def commit(r):
    m = OS_RE.search(r.get('source_url', '') + ' ' + r.get('upstream_url', ''))
    if m: return m.group(1)
    m = CL_RE.search(r.get('source', ''))
    return m.group(1) if m else ''

allrows = {}
for f in OHF:
    cols, rows = rd(f)
    # rows added for units nobody holds (inst_persons.py) inherit the provenance of the roster that lists no one there
    prov = collections.defaultdict(collections.Counter)
    for r in rows:
        if r['source']: prov[r['entity_id']][(r['source'], r['source_url'], r['retrieved_at'], r['license'])] += 1
    for r in rows:
        if not r['source'] and r['status'] == 'vacant' and prov[r['entity_id']]:
            r['source'], r['source_url'], r['retrieved_at'], r['license'] = prov[r['entity_id']].most_common(1)[0][0]
    for r in rows:
        r['entity_id_legacy'] = r.get('entity_id_legacy') or r['entity_id']
        r['entity_id'] = chamber(r['entity_id'])
        if not r.get('unit_layer'):
            tok = r['unit_vintage']; lay, yr = PLAN[tok]
            r['unit_layer'], r['unit_vintage'], r['unit_plan'] = lay, yr, tok
        # boundary set of the unit (DATA_LOADING Q-E12 slugs, as Election uses); empty when the unit has no TIGER geometry
        r['boundary_set'] = BSET[r['unit_plan']] if r['unit_geoid'] else ''
        r['source_url'] = fullurls(r['source_url'])
        if 'upstream_url' in r: r['upstream_url'] = fullurls(r['upstream_url'])
        r['source_commit'] = commit(r)
        assert r['retrieved_at'], (f, r)
    cols = ['unit_layer'] + [c for c in cols if c != 'unit_layer']
    cols = ins(cols, 'unit_vintage', 'unit_plan'); cols = ins(cols, 'unit_plan', 'boundary_set'); cols = ins(cols, 'entity_id', 'entity_id_legacy'); cols = ins(cols, 'source_url', 'source_commit')
    wr(f, cols, rows); allrows[f] = rows
    print(f, len(rows), collections.Counter(r['entity_id'] for r in rows).most_common(2), 'seats', sum(1 for r in rows if r['seat']))

# persons.csv: provenance from the officeholder rows that carry each person (and its aliases)
byp = collections.defaultdict(list)
for f, rows in allrows.items():
    for r in rows:
        if r['person_id']: byp[r['person_id']].append(r)
cols, rows = rd('persons')
for p in rows:
    rs = list(byp.get(p['person_id'], []))
    for a in [x for x in p.get('aliases', '').split(';') if x]: rs += byp.get(a, [])
    urls = []; cms = []; dates = []
    for r in rs:
        for u in r['source_url'].split(' ; '):
            if u and u not in urls: urls.append(u)
        if r['source_commit'] and r['source_commit'] not in cms: cms.append(r['source_commit'])
        if r['retrieved_at'] not in dates: dates.append(r['retrieved_at'])
    p['source_url'] = ' ; '.join(urls); p['source_commit'] = ';'.join(cms); p['retrieved_at'] = ';'.join(sorted(dates))
    assert p['source_url'] and p['retrieved_at'], p
for c in ['source_url', 'retrieved_at', 'source_commit']: cols = ins(cols, cols[-1], c)
wr('persons', cols, rows)
OSC = collections.Counter(r['source_commit'] for r in allrows['officeholders_stateleg_current'] if 'openstates' in r['source_url']).most_common(1)[0][0]
RET = allrows['officeholders_stateleg_current'][0]['retrieved_at']
# person_id_matches.csv: OpenStates person file at the pinned commit
cols, rows = rd('person_id_matches')
for r in rows:
    r['source_url'] = ('https://github.com/openstates/people/blob/%s/%s' % (OSC, r['openstates_file'])) if r['openstates_file'] else 'https://github.com/openstates/people/tree/%s/data' % OSC
    r['retrieved_at'] = RET; r['source_commit'] = OSC
for c in ['source_url', 'retrieved_at', 'source_commit']: cols = ins(cols, cols[-1], c)
wr('person_id_matches', cols, rows)
# stateleg_official_diffs.csv: the official roster URL of that state/chamber + the OpenStates commit compared against
ofu = {}
for r in allrows['officeholders_stateleg_current']:
    if r['official_check'] != 'openstates_fallback' and 'openstates/people' not in r['source_url']:
        ofu.setdefault((r['state'], r['chamber']), r['source_url'])
cols, rows = rd('stateleg_official_diffs')
for r in rows:
    u = ofu.get((r['state'], r['chamber'])) or next((v for (s, c), v in ofu.items() if s == r['state']), '')
    r['source_url'] = ' ; '.join(x for x in [u, 'https://github.com/openstates/people/tree/%s/data' % OSC] if x)
    r['retrieved_at'] = RET; r['source_commit'] = OSC
for c in ['source_url', 'retrieved_at', 'source_commit']: cols = ins(cols, cols[-1], c)
wr('stateleg_official_diffs', cols, rows)
print('persons', len(byp), 'os commit', OSC)
