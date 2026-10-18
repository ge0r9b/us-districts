"""Texas special-district changes since the CoG 2022 snapshot, from the TCEQ Water Districts Database (WDD,
https://www14.tceq.texas.gov/iwud/). Reads the crawl cached by tceq_wdd.py (list of every district + detail pages of
the dissolved/merged ones and of every district with WDD ID >= 101150, i.e. created from mid-2021 on) and writes
changes_tceq_wdd.csv in the changes_curated.csv format, which build_changes.py applies like the curated table.

  dissolution  a CoG 2022 Texas special district whose name (abbreviations expanded: MUD, WCID, FWSD, SUD, ...) is
               unique among CoG Texas special districts AND unique in the WDD, with the WDD primary county equal to
               the CoG county, WDD status DELETED/DISSOLVED or MERGED/ANNEXED and WDD activity date on or after
               2021-01-01 (a labelled name link: detail says so)
  new          a WDD district created on or after 2022-01-01 with status ACTIVE whose name matches no CoG Texas
               special district (INACTIVE = created but not operating, and PROPOSED, are counted, not added)
Each row cites its WDD detail page. Run: python3 scripts/tceq_wdd.py (list) then this script."""
import collections, csv, datetime, json, os, re
import tceq_wdd
from common import ROOT, CACHE, norm, write_csv

AB = {'MUD': 'MUNICIPAL UTILITY DISTRICT', 'WCID': 'WATER CONTROL AND IMPROVEMENT DISTRICT', 'FWSD': 'FRESH WATER SUPPLY DISTRICT',
      'LID': 'LEVEE IMPROVEMENT DISTRICT', 'MMD': 'MUNICIPAL MANAGEMENT DISTRICT', 'SUD': 'SPECIAL UTILITY DISTRICT',
      'PUD': 'PUBLIC UTILITY DISTRICT', 'UD': 'UTILITY DISTRICT', 'WSD': 'WATER SUPPLY DISTRICT', 'ID': 'IMPROVEMENT DISTRICT',
      'GCD': 'GROUNDWATER CONSERVATION DISTRICT', 'UWCD': 'UNDERGROUND WATER CONSERVATION DISTRICT', 'CD': 'CONSERVATION DISTRICT',
      'CRD': 'CONSERVATION AND RECLAMATION DISTRICT', 'MWD': 'MUNICIPAL WATER DISTRICT', 'WA': 'WATER AUTHORITY',
      'DD': 'DRAINAGE DISTRICT', 'RA': 'RIVER AUTHORITY', 'WID': 'WATER IMPROVEMENT DISTRICT', 'NO': '', 'CO': 'COUNTY', 'DIST': 'DISTRICT'}
DEAD = ('DELETED/DISSOLVED', 'MERGED/ANNEXED')
FIRST_NEW_ID = 101150
COLS = ['subject', 'change_type', 'effective_date', 'name', 'state', 'new_type', 'new_subtype', 'county_geoid', 'geoid_layer',
        'geoid', 'successor', 'source_id', 'source_url', 'retrieved_at', 'detail']


def key(n):
    return ' '.join(x for t in norm(n).split() for x in AB.get(t, t).split())


def iso(d):
    return datetime.datetime.strptime(d, '%m/%d/%Y').date().isoformat() if re.match(r'\d\d/\d\d/\d{4}$', d) else ''


def main():
    L = json.load(open(os.path.join(tceq_wdd.DIR, 'list.json')))
    cog = [r for r in csv.DictReader(open(os.path.join(ROOT, 'local', 'TX.csv'), encoding='utf-8'))
           if r['type'] == 'special_district' and r['flags'].find('not_in_cog2022') < 0]
    county = {}
    for r in csv.DictReader(open(os.path.join(CACHE, '2024_Gaz_counties_national.txt'), encoding='utf-8'), delimiter='\t'):
        if r['USPS'] == 'TX':
            county[norm(r['NAME'].replace(' County', ''))] = r['GEOID']
    ck, wk = collections.defaultdict(list), collections.defaultdict(list)
    for r in cog:
        ck[key(r['name'])].append(r)
    for x in L:
        wk[key(x[1])].append(x)
    out, stats = [], collections.Counter()
    ra = lambda i: datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(tceq_wdd.DIR, 'd_{}.html'.format(i)))).date().isoformat()
    for k_, rs in sorted(ck.items()):
        ws = wk.get(k_, [])
        if len(rs) != 1 or len(ws) != 1 or ws[0][3] not in DEAD:
            continue
        r, w = rs[0], ws[0]
        d = tceq_wdd.detail(w[0])
        date = iso(d['activity_date'])
        if county.get(norm(d['primary_county'])) != r['county_geoid']:
            stats['dead_county_mismatch'] += 1
            continue
        if not date or date < '2021-01-01':
            stats['dead_before_2021_or_undated'] += 1
            continue
        out.append({'subject': r['entity_id'], 'change_type': 'dissolution', 'effective_date': date, 'name': r['name'], 'state': 'TX',
                    'source_id': 'tceq_wdd', 'source_url': tceq_wdd.BASE + 'fuseaction=DetailDistrict&ID={}&command=list&name='.format(w[0]),
                    'retrieved_at': ra(w[0]),
                    'detail': 'TCEQ WDD district {} ({}, {} County): activity status {} as of {}; linked to the CoG unit by unique '
                              'name (abbreviations expanded) and same county'.format(w[0], w[1], d['primary_county'].title(), w[3], d['activity_date'])})
        stats['dissolution'] += 1
    for x in sorted(L, key=lambda x: int(x[0])):
        if int(x[0]) < FIRST_NEW_ID or key(x[1]) in ck or x[3] in DEAD:
            continue
        d = tceq_wdd.detail(x[0])
        made = iso(d['creation_date'])
        if not made or made < '2022-01-01':
            stats['live_unmatched_created_before_2022'] += 1
            continue
        if x[3] != 'ACTIVE':
            stats['new_not_added_' + x[3].lower()] += 1
            continue
        cg = county.get(norm(d['primary_county']), '')
        out.append({'subject': 'new:tceq_wdd:' + x[0], 'change_type': 'creation', 'effective_date': made, 'name': x[1], 'state': 'TX',
                    'new_type': 'special_district', 'new_subtype': d['district_type'].lower(), 'county_geoid': cg,
                    'source_id': 'tceq_wdd', 'source_url': tceq_wdd.BASE + 'fuseaction=DetailDistrict&ID={}&command=list&name='.format(x[0]),
                    'retrieved_at': ra(x[0]),
                    'detail': 'TCEQ WDD district {} ({}): {}, created {} ({}), activity status ACTIVE as of {}; not in CoG 2022; '
                              'no TIGER layer for special districts'.format(x[0], x[2], d['district_type'].title(), d['creation_date'],
                                                                             d['creation_type'] or 'creation type not stated', d['activity_date'])})
        stats['creation'] += 1
    write_csv(os.path.join(ROOT, 'changes_tceq_wdd.csv'), out, COLS)
    print(dict(stats))


if __name__ == '__main__':
    main()
