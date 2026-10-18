import csv, re, json, collections
import openstates_metadata as M
GEO = '/workspace/seating/src/us-districts/data-v3/geo'
NAME2AB = {M.lookup(abbr=a).name: a.upper() for a in M.STATES_BY_ABBR if a.upper() not in ("US","ZA")}
STOP = {'state','house','senate','district','districts','legislative','delegate','senatorial','representative','representatives','of','the','assembly','county','and'}
def norm(s):
    s = s.lower().replace('&', ' and ')
    s = re.sub(r'[-–,./()]', ' ', s)
    s = s.replace('south east', 'southeast')
    ORD = {'first':'1st','second':'2nd','third':'3rd','fourth':'4th','fifth':'5th','sixth':'6th'}
    toks = [ORD.get(t, t) for t in s.split() if t not in STOP]
    toks = [t.lstrip('0') or '0' if re.match(r'^\d+[a-z]?$', t) else t for t in toks]
    return ' '.join(toks)
def load(layer):
    idx = collections.defaultdict(dict)
    for r in csv.DictReader(open(f'{GEO}/{layer}.csv')):
        st = NAME2AB.get(r['state'])
        if not st or r['row'] == 'dc.js': continue
        for key in {norm(r['tiger_name']), norm(r['v2_name'])}:
            idx[st].setdefault(key, (r['geoid'], r['v2_name'], r['tiger_name']))
    return idx
SLDU, SLDL = load('senate'), load('statehouse')
def match(st, chamber, district):
    idx = (SLDU if chamber in ('upper', 'legislature') else SLDL)[st]
    tries = [district]
    d2 = re.sub(r'\s*-\s*Position\s*\d+$', '', district, flags=re.I)
    tries.append(d2)
    if st in ('ID',) or chamber == 'lower' and st in ('ID','WA'):
        tries.append(re.sub(r'(\d+)[AB]$', r'\1', d2))
    tries.append(re.sub(r'\s+1(\s+District)?$', '', d2))
    for t in tries:
        k = norm(t)
        if k in idx: return idx[k]
    return None
if __name__ == '__main__':
    d = json.load(open('bp_chambers.json'))
    tot = un = 0; bad = collections.Counter(); ex = collections.defaultdict(list)
    for k, v in d.items():
        st, ch = k.split('_')
        for r in v['rows']:
            tot += 1
            if not match(st, ch, r['district']):
                un += 1; bad[k] += 1; ex[k].append(r['district'])
    print(tot, un)
    for k, n in bad.most_common(): print(k, n, sorted(set(ex[k]))[:8])
