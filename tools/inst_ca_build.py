"""Build every data-v3/inst/ca file. Usage: inst_ca_build.py [OUT] [--stability-test]

Runs inst_ca_federal.py, inst_ca_provincial.py, inst_ca_municipal.py, then merges their source lists into ONE sources_ca.csv
(same columns and <slug>-<sha8(url|commit)> ids as data-v3/inst/sources.csv, so the two files merge as a union).
--stability-test: builds twice into temp dirs (the second run in reverse builder order), requires byte-identical output,
re-derives every source id from its own url + commit, and checks that every source_id used by a row is in sources_ca.csv.
"""
import csv, filecmp, glob, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from inst_sources import Registry
import collections, re
from inst_ca_common import SOURCE_COLS, BSET_COLS, NOT_CURRENT, licence_flags, write_csv
BUILDERS = ['inst_ca_federal.py', 'inst_ca_provincial.py', 'inst_ca_municipal.py']

def build(out, order):
    os.makedirs(out, exist_ok=True)
    for b in order: subprocess.run([sys.executable, os.path.join(HERE, b), out], check=True, stdout=subprocess.DEVNULL)
    reg = Registry()
    for f in sorted(glob.glob(os.path.join(out, 'sources_ca_*.csv'))):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            reg.add(r['source_id'].rsplit('-', 1)[0], r['source'], r['source_url'], r['license'], r['retrieved_at'], r['commit'], r['sha256'])
        os.remove(f)
    n = reg.check_ids()
    srows = []
    for r in reg.rows.values():
        r = dict(r); r['non_commercial'], r['attribution_required'] = licence_flags(r['source_id']); srows.append(r)
    write_csv(os.path.join(out, 'sources_ca.csv'), SOURCE_COLS, srows, key=lambda r: r['source_id'])
    # boundary_sets_ca.csv (Full Stack ruling 2): one row per set, is_current unique per (country, province, unit_type)
    sets = {}
    for f in sorted(glob.glob(os.path.join(out, 'units_ca_*.csv'))):
        for r in csv.DictReader(open(f, encoding='utf-8')):
            d = sets.setdefault(r['boundary_set'], {'country': set(), 'province': set(), 'unit_type': set(), 'src': collections.Counter()})
            d['country'].add(r['country']); d['province'].add(r['province']); d['unit_type'].add(r['unit_type'])
            d['src'][r['source_id'].split(';')[0]] += 1
    brows = []
    for b, d in sorted(sets.items()):
        assert len(d['country']) == 1 and len(d['unit_type']) == 1, b
        prov = d['province'].pop() if len(d['province']) == 1 and not b.startswith(('ec-', 'statcan-')) else ''
        brows.append({'boundary_set': b, 'country': d['country'].pop(), 'province': prov, 'unit_type': d['unit_type'].pop(),
                      'vintage': re.search(r'-(\d{4})-', b).group(1), 'is_current': 'false' if b in NOT_CURRENT else 'true',
                      'source_id': ';'.join(sorted(d['src']))})
    cur = collections.Counter((r['country'], r['province'], r['unit_type']) for r in brows if r['is_current'] == 'true')
    assert all(v == 1 for v in cur.values()), ('several current sets', [k for k, v in cur.items() if v > 1])
    assert not NOT_CURRENT - set(sets), NOT_CURRENT - set(sets)
    write_csv(os.path.join(out, 'boundary_sets_ca.csv'), BSET_COLS, brows)
    used = set()
    for f in glob.glob(os.path.join(out, '*.csv')):
        if f.endswith('sources_ca.csv'): continue
        for r in csv.DictReader(open(f, encoding='utf-8')):
            used.update(x for x in (r.get('source_id') or '').split(';') if x)
    missing = used - set(reg.rows)
    assert not missing, ('source_id not in sources_ca.csv', sorted(missing))
    return n, len(used)

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0] if args else 'data-v3/inst/ca'
    if '--stability-test' in sys.argv:
        a, b = tempfile.mkdtemp(), tempfile.mkdtemp()
        build(a, BUILDERS); build(b, BUILDERS[::-1])
        names = sorted(os.listdir(a)); assert names == sorted(os.listdir(b))
        diff = [n for n in names if not filecmp.cmp(os.path.join(a, n), os.path.join(b, n), shallow=False)]
        assert not diff, ('non-deterministic', diff)
        if os.path.isdir(out):
            committed = [n for n in names if os.path.exists(os.path.join(out, n)) and not filecmp.cmp(os.path.join(a, n), os.path.join(out, n), shallow=False)]
            print('differs from', out, ':', committed or 'none')
        print('stability test passed:', len(names), 'files byte-identical across two builds')
        shutil.rmtree(a); shutil.rmtree(b)
    else:
        print('sources %d, ids used %d' % build(out, BUILDERS))
