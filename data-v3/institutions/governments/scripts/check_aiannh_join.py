"""Check that every tribal GEOID in tribes.csv and governments_geoid_xwalk.csv (layer aiannh) exists in the Geography
bot's TIGER 2024 tribal-area CSVs (data-v3/geo/aiannh_2024.csv, anrc_2024.csv, aitsn_2024.csv on data/geo).

    python3 scripts/check_aiannh_join.py [GEO_REF]      # GEO_REF default ed866a4 (read with `git show`, read-only)
Writes aiannh_join_check.csv (one row per entity/GEOID pair) and prints the counts."""
import collections, csv, io, json, os, subprocess, sys
from common import ROOT, write_csv

REF = sys.argv[1] if len(sys.argv) > 1 else 'ed866a4'


def geo_csv(name):
    out = subprocess.check_output(['git', 'show', '{}:data-v3/geo/{}'.format(REF, name)], cwd=ROOT)
    return list(csv.DictReader(io.StringIO(out.decode('utf-8'))))


def main():
    geo = {}
    for f in ('aiannh_2024.csv', 'anrc_2024.csv', 'aitsn_2024.csv'):
        for r in geo_csv(f):
            geo[r['geoid']] = (f, r.get('namelsad') or r.get('name', ''))
    pairs = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'tribes.csv'), encoding='utf-8')):
        if r['geoid']:
            pairs[(r['entity_id'], r['geoid'])] = 'tribes.csv primary (' + r['geoid_layer'] + ')'
    for x in csv.DictReader(open(os.path.join(ROOT, 'governments_geoid_xwalk.csv'), encoding='utf-8')):
        if x['unit_layer'] == 'aiannh' or x['entity_id'].startswith('bia:'):
            pairs.setdefault((x['entity_id'], x['geoid']), 'xwalk ' + x['relation'])
    rows = []
    for (eid, g), where in sorted(pairs.items()):
        f, nm = geo.get(g, ('', ''))
        rows.append({'entity_id': eid, 'geoid': g, 'found_in': where, 'joins': 'yes' if f else 'no', 'geo_file': f,
                     'geo_namelsad': nm, 'geo_ref': 'data/geo@' + REF})
    write_csv(os.path.join(ROOT, 'aiannh_join_check.csv'), rows,
              ['entity_id', 'geoid', 'found_in', 'joins', 'geo_file', 'geo_namelsad', 'geo_ref'])
    c = collections.Counter(r['joins'] for r in rows)
    print(json.dumps({'pairs': len(rows), 'joins': dict(c), 'entities': len({r['entity_id'] for r in rows}),
                      'geoids': len({r['geoid'] for r in rows}), 'geo_features': len(geo),
                      'not_joining': [(r['entity_id'], r['geoid'], r['found_in']) for r in rows if r['joins'] == 'no']}, indent=1))


if __name__ == '__main__':
    main()
