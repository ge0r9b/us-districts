#!/usr/bin/env python3
"""Step 5 of the officeholder pipeline (after inst_v3format.py): normalize provenance into data-v3/inst/sources.csv.

Every row gets source_id (a ';'-list when a row rests on more than one source) pointing at sources.csv
(source_id, source, source_url, license, retrieved_at, commit, sha256); the repeated columns source / license /
retrieved_at / source_commit leave the row. source_url and sha256 stay on a row only when they are row-specific
(an OpenStates person file at the pinned commit); otherwise they live once in sources.csv.
The upstream record id that used to be in the officeholder column 'source_id' (ocd-person id, bioguide id, roster id)
moves to 'source_record_id'.

--stability-test: rebuild the normalization twice in memory from the same step-4 input (second pass with every table's
rows in reverse order and the tables in reverse order) and require identical source ids, rows and sources.csv; then
re-derive every id from its own url + commit.
usage: inst_oh_sources.py <repo> [--dir data-v3/inst] [--stability-test]
"""
import csv, io, os, re, sys, collections, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inst_sources import Registry, COLS as SCOLS
R = sys.argv[1]; D = os.path.join(R, sys.argv[sys.argv.index('--dir') + 1] if '--dir' in sys.argv else 'data-v3/inst')
OHF = ['officeholders_house_current', 'officeholders_house_2024', 'officeholders_house_2020', 'officeholders_stateleg_current', 'officeholders_stateleg_2024']
OTHER = ['county_government', 'persons', 'person_id_matches', 'stateleg_official_diffs']
DROP = ['source', 'license', 'retrieved_at', 'source_commit']
OSB = re.compile(r'^https://github\.com/openstates/people/(?:blob|tree)/([0-9a-f]{40})/')
OSS = re.compile(r'^(OpenStates people \(commit [0-9a-f]{12} [^)]*\))')

def rd(f):
    with open(os.path.join(D, f + '.csv'), encoding='utf-8', newline='') as fh:
        r = csv.DictReader(fh); return r.fieldnames, list(r)
def dump(cols, rows):
    b = io.StringIO(); w = csv.DictWriter(b, cols, lineterminator='\n'); w.writeheader(); w.writerows(rows); return b.getvalue()

def openstates(reg, commit, retrieved):
    return reg.add('openstates-people', 'OpenStates people (commit %s)' % commit[:12], 'https://github.com/openstates/people',
                   'CC0 1.0', retrieved, commit)

def row_source(reg, f, r):
    """-> (source_id, row-specific source_url, row-specific sha256)"""
    url, src = r['source_url'], r['source']
    m = OSB.match(url)
    if m:
        m2 = OSS.match(src); assert m2, (f, src)
        sid = reg.add('openstates-people', m2.group(1).rsplit(' ', 1)[0] + ')', 'https://github.com/openstates/people',
                      r['license'], r['retrieved_at'], m.group(1))
        if r['status'] == 'vacant' and not r.get('person_id'):
            return sid, '', ''        # step 4 had copied a member's file URL onto the vacancy; not row-specific
        return sid, url, r['sha256']
    if 'congress-legislators' in url: slug = 'congress-legislators'
    elif 'clerk.house.gov' in url: slug = 'house-clerk-memberdata'
    else:
        ab = re.match(r'^chamber:([a-z]{2})-', r['entity_id']); assert ab, (f, r['entity_id'])
        slug = 'roster-' + ab.group(1)
    sid = reg.add(slug, src, url, r['license'], r['retrieved_at'], r.get('source_commit', ''), r['sha256'])
    return sid, '', ''

def normalize(tables, reverse=False):
    T = copy.deepcopy(tables); reg = Registry()
    names = OHF[::-1] if reverse else OHF
    if reverse:
        for k in T: T[k] = (T[k][0], T[k][1][::-1])
    out = {}; byp = collections.defaultdict(set); roster_by_url = {}
    for f in names:
        cols, rows = T[f]
        for r in rows:
            sid, u, h = row_source(reg, f, r)
            r['source_record_id'] = r.pop('source_id', ''); r['source_id'] = sid; r['source_url'] = u; r['sha256'] = h
            if r.get('person_id'): byp[r['person_id']].add(sid)
            if sid.startswith('roster-'): roster_by_url[reg.rows[sid]['source_url']] = sid
            for c in DROP: r.pop(c, None)
        nc = []
        for c in cols:
            if c == 'source': nc.append('source_id')
            elif c == 'source_id': nc.append('source_record_id')
            elif c not in DROP: nc.append(c)
        if reverse: rows = rows[::-1]
        out[f] = (nc, rows)
    osc = collections.Counter(reg.rows[s]['commit'] for f in OHF for r in out[f][1] for s in [r['source_id']] if s.startswith('openstates')).most_common(1)[0][0]
    ret = next(iter(reg.rows.values()))['retrieved_at']
    # county_government: CoG 2022 (cross-checked against TIGER FUNCSTAT, named in the source text)
    cols, rows = T['county_government']
    for r in rows:
        cog, second = r['source'].split('; ', 1)
        ids = [reg.add(None, cog, r['source_url'], r['license'], r['retrieved_at'], '', r['sha256'])]
        if 'FUNCSTAT' in second:
            ids.append(reg.add(None, 'U.S. Census Bureau, TIGER/Line 2024 counties, FUNCSTAT (via data-v3/geo/county_funcstat.csv)',
                               'https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/', 'public domain (US government work)', r['retrieved_at']))
        elif '2020 Gazetteer counties' in second:
            ids.append(reg.add(None, 'U.S. Census Bureau, 2020 TIGER/Line Gazetteer (2020_Gaz_counties_national.txt)',
                               'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_counties_national.zip',
                               'public domain (US government work)', r['retrieved_at']))
        else: raise SystemExit('unknown county_government source ' + second)
        r['source_id'] = ';'.join(ids)
        for c in DROP + ['source_url', 'sha256']: r.pop(c, None)
    out['county_government'] = ([('source_id' if c == 'source' else c) for c in cols if c not in DROP[1:] + ['source_url', 'sha256']], rows)
    # persons: every source behind the person's officeholder rows (canonical id and aliases)
    cols, rows = T['persons']
    for p in rows:
        s = set(byp.get(p['person_id'], ()))
        for a in [x for x in p.get('aliases', '').split(';') if x]: s |= byp.get(a, set())
        assert s, p['person_id']; p['source_id'] = ';'.join(sorted(s))
        for c in ['source_url', 'retrieved_at', 'source_commit']: p.pop(c, None)
    out['persons'] = ([c for c in cols if c not in ('source_url', 'retrieved_at', 'source_commit')] + ['source_id'], rows)
    # person_id_matches: OpenStates at the pinned commit; the person file URL stays when there is one
    cols, rows = T['person_id_matches']
    for r in rows:
        m = OSB.match(r['source_url']); assert m, r
        r['source_id'] = openstates(reg, m.group(1), ret) if m.group(1) != osc else openstates(reg, osc, ret)
        if '/tree/' in r['source_url']: r['source_url'] = ''
        for c in ['retrieved_at', 'source_commit']: r.pop(c, None)
    out['person_id_matches'] = ([c for c in cols if c not in ('retrieved_at', 'source_commit')] + ['source_id'], rows)
    # diffs: the official roster compared + the OpenStates commit compared against
    cols, rows = T['stateleg_official_diffs']
    for r in rows:
        parts = r['source_url'].split(' ; ')
        off = ' ; '.join(p for p in parts if 'openstates/people' not in p)
        m = next(OSB.match(p) for p in parts if 'openstates/people' in p)
        ids = []
        if off:
            assert off in roster_by_url, ('diff roster url not in registry', off[:120]); ids.append(roster_by_url[off])
        ids.append(openstates(reg, m.group(1), ret))
        r['source_id'] = ';'.join(ids)
        for c in ['source_url', 'retrieved_at', 'source_commit']: r.pop(c, None)
    out['stateleg_official_diffs'] = ([c for c in cols if c not in ('source_url', 'retrieved_at', 'source_commit')] + ['source_id'], rows)
    if reverse:
        for f in OTHER: out[f] = (out[f][0], out[f][1][::-1])
    for f in OHF + OTHER:
        for r in out[f][1]:
            for s in r['source_id'].split(';'): assert s in reg.rows, (f, s)
    return out, reg

if __name__ == '__main__':
    tables = {f: rd(f) for f in OHF + OTHER}
    if 'source' not in tables['officeholders_house_current'][0]:
        raise SystemExit('already normalized (no source column); rerun steps 1-4 first, or check out the step-4 files')
    out, reg = normalize(tables)
    if '--stability-test' in sys.argv:
        out2, reg2 = normalize(tables, reverse=True)
        same_reg = dump(SCOLS, [reg.rows[k] for k in sorted(reg.rows)]) == dump(SCOLS, [reg2.rows[k] for k in sorted(reg2.rows)])
        same_rows = all(dump(*out[f]) == dump(*out2[f]) for f in out)
        n = reg.check_ids()
        print('stability test: sources %d, registry identical %s, all rows identical %s, ids re-derive from url+commit OK' % (n, same_reg, same_rows))
        assert same_reg and same_rows
    for f, (cols, rows) in out.items():
        with open(os.path.join(D, f + '.csv'), 'w', encoding='utf-8', newline='') as fh: fh.write(dump(cols, rows))
    reg.write(os.path.join(D, 'sources.csv'))
    print('sources', len(reg.rows), collections.Counter(k.rsplit('-', 1)[0].split('-')[0] for k in reg.rows))
