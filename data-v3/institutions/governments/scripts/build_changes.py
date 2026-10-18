"""Changes to general-purpose and school governments after the 2022 Census of Governments snapshot.

Inputs : cache/national_gcn_YYYY.txt   Census Bureau Geographic Change Notes (BAS), effective years 2021-2025
         changes_curated.csv           hand-entered changes, each cited to an official state source (legislature,
                                       state agency registry, official election results); the file is committed
Output : changes_since_cog2022.csv; applies the changes to the CoG unit rows in place:
           ceased units  -> is_active=false, valid_to=<effective date>, flag 'ceased' (rows are never deleted)
           new units     -> new rows with valid_from=<effective date>, flag 'not_in_cog2022'
           renames       -> the new name is added to alias (CoG name stays in name)
Rules  : a GCN record is used only when its state + 5-digit code or its ANSI (GNIS) code is the CoG unit's code AND
         the GCN core name is the CoG core name. New units must be a governmental kind (city, town, village, borough,
         township, plantation) that is not already a CoG unit; township-type units only in states whose CoG has
         township governments; redistricting-only records (voting districts) and CDP/UT/precinct records are skipped.
         Anything not confirmed this way is not recorded.
"""
import collections, csv, os, re
from common import ROOT, COLUMNS, PUBLIC_DOMAIN, GCN, GCN_YEARS, CACHE, meta, read_gaz, norm

CHANGE_COLUMNS = ['entity_id', 'change_type', 'effective_date', 'name', 'state', 'source_url', 'retrieved_at',
                  'source_id', 'successor_id', 'cog_id', 'detail']
GOV_KINDS = ('charter township', 'township', 'city', 'town', 'village', 'borough', 'plantation', 'municipality')
PREFIX = re.compile(r'^(CHARTER TOWNSHIP|TOWNSHIP|TOWN|CITY|VILLAGE|BOROUGH|PLANTATION|MUNICIPALITY) OF ')
SUFFIX = re.compile(r' (CHARTER TOWNSHIP|TOWNSHIP|TOWN|CITY|VILLAGE|BOROUGH|PLANTATION|MUNICIPALITY)$')
STATE_LICENSE = 'state government public record (facts only; not a U.S. Government work)'
CURATED_SOURCES = {   # source_id -> description, landing URL
    'fl_legislature': ('The Florida Senate, bill records and Laws of Florida', 'https://www.flsenate.gov/'),
    'me_legislature': ('Maine State Legislature, Private and Special Laws', 'https://legislature.maine.gov/'),
    'ne_kearney_election': ('Nebraska Secretary of State county election results (Kearney County 2020 General, official) '
                            'and Nebraska Revised Statutes 23-295', 'https://countyelectionresults.nebraska.gov/'),
    'sc_legislature': ('South Carolina Legislature, 124th session bills and acts', 'https://www.scstatehouse.gov/'),
    'wi_mds': ('Wisconsin Department of Administration, Municipal Data System (incorporations)', 'https://mds.wi.gov/View/Incorporations'),
}


def core(name):
    n = norm(name)
    n = PREFIX.sub('', n)
    return SUFFIX.sub('', n).strip()


def iso(d):
    mm, dd, yy = d.split('-')
    return '{}-{}-{}'.format(yy, mm, dd)


def read_gcn():
    out = []
    for y in GCN_YEARS:
        with open(os.path.join(CACHE, 'national_gcn_{}.txt'.format(y)), encoding='latin-1') as f:
            for i, x in enumerate(csv.DictReader(f, delimiter='|')):
                x = {k.strip(): (v or '').strip() for k, v in x.items() if k}
                x['_url'], x['_key'], x['_line'] = GCN.format(y), 'gcn_' + y, i + 2
                out.append(x)
    return out


def build(reg, rows):
    """rows: CoG unit rows (modified in place). Returns (new rows, change rows, extra sources.csv rows)."""
    for r in rows:
        for c in COLUMNS:
            r.setdefault(c, '')
    by_id = {r['entity_id']: r for r in rows}
    gp = [r for r in rows if r['type'] in ('municipality', 'township')]
    by_code, by_ansi = collections.defaultdict(list), collections.defaultdict(list)
    for r in gp:
        for c in {r['fips_place'][-5:] if r['fips_place'] else '', r['geoid'][-5:] if r['geoid'] else ''} - {''}:
            by_code[(r['state_fips'], c)].append(r)
        if r['gnis_id']:
            by_ansi[r['gnis_id']].append(r)
    county_of = {(r['state_fips'], r['county_geoid']): r for r in rows if r['type'] == 'county'}
    county_by_geoid = {r['county_geoid']: r for r in rows if r['type'] == 'county'}
    township_states = {r['state_fips'] for r in rows if r['type'] == 'township'}
    place24 = {g['GEOID']: g for g in read_gaz('place')}
    cousub24 = collections.defaultdict(list)
    for g in read_gaz('cousubs'):
        cousub24[(g['GEOID'][:2], g['GEOID'][-5:])].append(g)

    def kind_ok(r, name):
        low = name.lower().strip()
        k = next((k for k in GOV_KINDS if low.endswith(' ' + k)), '')
        if k in ('township', 'charter township', 'plantation'):
            return r['type'] == 'township'
        if k in ('city', 'village', 'borough', 'municipality'):
            return r['type'] == 'municipality'
        return True          # 'town' (place or MCD) or no kind word

    def find(ss, code, ansi, name):
        hits = {r['entity_id']: r for r in by_ansi.get(ansi, []) + by_code.get((ss, code.zfill(5)), [])
                if r['state_fips'] == ss and core(r['name']) == core(name) and kind_ok(r, name)}
        return list(hits.values())

    changes, new_rows = [], []
    dated = lambda x: iso(x['Effective Date'])

    def change(eid, ctype, date, name, st, url, ra, sid, succ='', cog='', detail=''):
        changes.append({'entity_id': eid, 'change_type': ctype, 'effective_date': date, 'name': name, 'state': st,
                        'source_url': url, 'retrieved_at': ra, 'source_id': sid, 'successor_id': succ, 'cog_id': cog,
                        'detail': detail})

    def cease(r, date, sid):
        r['is_active'] = 'false'
        r['valid_to'] = date
        fl = [f for f in r.get('flags', '').split(';') if f]
        r['flags'] = ';'.join(sorted(set(fl) | {'ceased'}))
        r['source'] = ';'.join(dict.fromkeys(r['source'].split(';') + [sid]))

    gcn = read_gcn()
    # ---- GCN: ceased, renamed and reclassified CoG units
    pending_new = []
    for x in gcn:
        t, desc, name = x['Type of Change'], x['Description of Change'], x['Entity Name']
        ss = x['State'][-2:]
        if 'redistricting' in desc.lower():
            continue
        hits = find(ss, x['Entity Code'], x['ANSI Code'], name)
        ra = meta(x['_key'])['retrieved_at']
        detail = 'GCN {} line {}: {}'.format(x['_key'][4:], x['_line'], desc)
        if t.startswith('Deleted') and len(hits) == 1:
            change(hits[0]['entity_id'], 'dissolution', dated(x), hits[0]['name'], hits[0]['state'], x['_url'], ra,
                   'census_gcn', cog=hits[0]['cog_id'], detail=detail)
        elif t.startswith('Name Change') and len(hits) == 1 and desc.startswith('Changed to '):
            # 'Changed to' = a rename reported by the government; 'Corrected ...' records are Census spelling fixes
            new = re.split(r' ?\(|\. ', desc[len('Changed to '):], maxsplit=1)[0].strip().rstrip('.')
            change(hits[0]['entity_id'], 'rename', dated(x), new, hits[0]['state'], x['_url'], ra, 'census_gcn',
                   cog=hits[0]['cog_id'], detail=detail)
        elif t.startswith('Legal/Statistical Description Change') and len(hits) == 1 and not desc.startswith('Corrected'):
            change(hits[0]['entity_id'], 'reclassification', dated(x), hits[0]['name'], hits[0]['state'], x['_url'], ra,
                   'census_gcn', cog=hits[0]['cog_id'], detail=detail)
        elif t.startswith('New') and not hits:
            low = name.lower()
            kind = next((k for k in GOV_KINDS if low.endswith(' ' + k)), None)
            if kind is None:
                continue
            if kind in ('township', 'charter township', 'plantation') and ss not in township_states:
                continue
            pending_new.append((x, kind, ra, detail))
        if t.startswith('New') and 'Formed from all of' in desc:
            m = re.search(r'Formed from all of (.+?) \((\d{5})\)', desc)
            pred = find(ss, m.group(2), '', m.group(1)) if m else []
            if len(pred) == 1:
                change(pred[0]['entity_id'], 'dissolution', dated(x), pred[0]['name'], pred[0]['state'], x['_url'], ra,
                       'census_gcn', cog=pred[0]['cog_id'],
                       detail='GCN {} line {}: {} ({}) {}'.format(x['_key'][4:], x['_line'], name, x['Entity Code'], desc))

    # ---- GCN: new governmental units
    seen_new = set()
    ansi_count = collections.Counter(x['ANSI Code'] for x in gcn if x['Type of Change'].startswith('New'))
    for x, kind, ra, detail in sorted(pending_new, key=lambda p: (iso(p[0]['Effective Date']), p[0]['_key'], p[0]['_line'])):
        ss, code, ansi = x['State'][-2:], x['Entity Code'].zfill(5), x['ANSI Code']
        if ss + code in seen_new:      # one unit can have several GCN records; the earliest one creates it
            continue
        seen_new.add(ss + code)
        layer, geoid, cty, vint, gn = '', '', '', '', ''
        if kind in ('township', 'charter township', 'plantation') or (ss in township_states and kind == 'town' and ss + code not in place24):
            cs = cousub24.get((ss, code), [])
            if len(cs) > 1 and ansi:
                cs = [g for g in cs if g['ANSICODE'] == ansi]
            if len(cs) == 1:
                layer, geoid, cty, vint, gn = 'cousub', cs[0]['GEOID'], cs[0]['GEOID'][:5], '2024', cs[0]['ANSICODE']
            typ = 'township'
        else:
            g = place24.get(ss + code)
            if g and g['NAME'].endswith(' CDP'):
                # TIGER 2024 (boundaries as of Jan 1, 2024) still shows the pre-incorporation CDP under this code
                detail += ' [TIGER 2024 has {} (GEOID {}) as a CDP; no 2024 GEOID for the government]'.format(g['NAME'], g['GEOID'])
            elif g:
                layer, geoid, vint, gn = 'place', g['GEOID'], '2024', g['ANSICODE']
            typ = 'municipality'
        if gn and ansi and gn != ansi:
            detail += ' [GCN ANSI {} differs from TIGER 2024 ANSI {}; TIGER kept]'.format(ansi, gn)
        if not gn and ansi_count[ansi] == 1:
            gn = ansi
        key = 'census_code:{}:{}{}'.format('cousub' if typ == 'township' else 'place', ss, code)
        if reg.by_key.get(key) in by_id:
            continue
        eid = reg.get([key], 'gcn:{}{}'.format(ss, code) if typ == 'municipality' else 'gcn:' + (geoid or ss + code), ra[:10])
        usps = x['State'][:2]
        row = {c: '' for c in COLUMNS}
        row.update(entity_id=eid, name=x['Entity Name'], type=typ, subtype='', gov_status='independent',
                   parent_id='state:' + ss, state_fips=ss, state=usps, county_geoid=cty, geoid=geoid, geoid_layer=layer,
                   geoid_vintage=vint, geoid_match=('gcn_code_' + vint) if geoid else 'not_in_tiger_2024',
                   fips_place=code, gnis_id=gn, is_active='Y',
                   note=detail, source='census_gcn' + (';gaz2024' if geoid else ''), source_url=x['_url'],
                   source_date=meta(x['_key'])['last_modified'], retrieved_at=ra, license=PUBLIC_DOMAIN,
                   tiger_status='current_2024' if geoid else 'not_in_tiger_2024', flags='not_in_cog2022',
                   valid_from=iso(x['Effective Date']))
        new_rows.append(row)
        change(eid, 'incorporation' if typ == 'municipality' else 'new_township', row['valid_from'], row['name'], usps,
               x['_url'], ra, 'census_gcn', detail=detail)

    # ---- curated official state sources
    with open(os.path.join(ROOT, 'changes_curated.csv'), encoding='utf-8') as f:
        cur = list(csv.DictReader(f))
    used_src = set()
    for c in cur:
        used_src.add(c['source_id'])
        succ = c['successor']
        if succ.startswith('county:'):
            succ = county_by_geoid[succ.split(':', 1)[1]]['entity_id']
        if succ.startswith('new:'):
            succ = reg.by_key.get(succ[4:], succ[4:])
        if c['subject'].startswith('new:'):
            key = c['subject'][4:]
            eid = reg.get([key], key, c['retrieved_at'])
            ss = next(s for s, r in ((r['state_fips'], r) for r in rows) if r['state'] == c['state'])
            row = {k: '' for k in COLUMNS}
            row.update(entity_id=eid, name=c['name'], type=c['new_type'], subtype=c['new_subtype'], gov_status='independent',
                       parent_id='state:' + ss, state_fips=ss, state=c['state'], county_geoid=c['county_geoid'],
                       geoid=c['geoid'], geoid_layer=c['geoid_layer'], geoid_vintage='2024' if c['geoid'] else '',
                       geoid_match='official_source_code_2024' if c['geoid'] else 'not_in_tiger_2024',
                       nces_leaid=c['geoid'] if c['new_type'] == 'school_district' else '', is_active='Y',
                       note=c['detail'], source=c['source_id'] + (';gaz2024' if c['geoid'] else ''), source_url=c['source_url'],
                       retrieved_at=c['retrieved_at'], license=STATE_LICENSE,
                       tiger_status='current_2024' if c['geoid'] else 'not_in_tiger_2024', flags='not_in_cog2022',
                       valid_from=c['effective_date'])
            # a CoG predecessor whose F-33 code was carried into the new district's LEAID gives that GEOID up
            for r in rows:
                if c['geoid'] and r['geoid'] == c['geoid'] and r['geoid_layer'] == c['geoid_layer']:
                    r['note'] = (r['note'] + '; ' if r['note'] else '') + 'GEOID {} {} moved to successor {}'.format(
                        r['geoid_layer'], r['geoid'], eid)
                    r.update(geoid='', geoid_layer='', geoid_vintage='', geoid_match='ceased_geoid_to_successor', tiger_status='')
            new_rows.append(row)
            change(eid, c['change_type'], c['effective_date'], c['name'], c['state'], c['source_url'], c['retrieved_at'],
                   c['source_id'], detail=c['detail'])
        else:
            r = by_id[c['subject']]
            assert core(r['name']) == core(c['name']) or norm(r['name']) == norm(c['name']), (r['name'], c['name'])
            change(r['entity_id'], c['change_type'], c['effective_date'], r['name'], r['state'], c['source_url'],
                   c['retrieved_at'], c['source_id'], succ, r['cog_id'], c['detail'])

    # ---- one row per (entity, change): curated state source first, GCN second (both cited)
    merged = {}
    for ch in sorted(changes, key=lambda c: c['source_id'] == 'census_gcn'):
        k = (ch['entity_id'], 'ceased' if ch['change_type'] in ('dissolution', 'consolidation_abolished') else ch['change_type'])
        if k in merged:
            m = merged[k]
            if ch['source_url'] not in m['source_url']:
                m['source_url'] += ' ; ' + ch['source_url']
                m['source_id'] += ';' + ch['source_id']
                m['detail'] += ' | ' + ch['detail']
            continue
        merged[k] = dict(ch)
    changes = sorted(merged.values(), key=lambda c: (c['state'], c['effective_date'], c['entity_id'], c['change_type']))
    for ch in changes:
        r = by_id.get(ch['entity_id'])
        if r is None:
            continue
        if ch['change_type'] in ('dissolution', 'consolidation_abolished'):
            for s in ch['source_id'].split(';'):
                cease(r, ch['effective_date'], s)
        elif ch['change_type'] == 'rename':
            al = [a for a in r['alias'].split(';') if a]
            if ch['name'] not in al:
                r['alias'] = ';'.join(al + [ch['name']])
            r['source'] = ';'.join(dict.fromkeys(r['source'].split(';') + ['census_gcn']))
    src_rows = [{'source_id': s, 'source': CURATED_SOURCES[s][0], 'source_url': CURATED_SOURCES[s][1], 'license': STATE_LICENSE,
                 'retrieved_at': max(c['retrieved_at'] for c in cur if c['source_id'] == s), 'commit': ''}
                for s in sorted(used_src)]
    return new_rows, changes, src_rows
