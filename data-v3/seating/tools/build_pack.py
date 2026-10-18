#!/usr/bin/env python3
"""Pack the CSV tables into one compact client file (holders.pack.json + .gz).
Event stream per body: flat int array of 5-tuples [dday, seat, person, party, caucus],
dday = days since previous event of the same body (first one: days since EPOCH).
person 0 = nobody (vacant or unknown), party 0 = vacant, 9 = unknown, caucus 0 = same as party."""
import csv, json, gzip, datetime, collections, os
D = '/workspace/seating/v3data'
EPOCH = datetime.date(2000, 1, 1)
def day(s):
    if not s: return None
    if len(s) == 4: s += '-01-01'
    return (datetime.date.fromisoformat(s) - EPOCH).days
bodies = list(csv.DictReader(open(f'{D}/bodies.csv')))
seats = collections.defaultdict(list)
for r in csv.DictReader(open(f'{D}/seats.csv')): seats[int(r['b'])].append(r)
terms = collections.defaultdict(list)
for r in csv.DictReader(open(f'{D}/terms.csv')): terms[int(r['b'])].append(r)
people = list(csv.DictReader(open(f'{D}/people.csv')))
pack = dict(v=1, epoch=EPOCH.isoformat(), parties=[r['key'] for r in csv.DictReader(open(f'{D}/parties.csv'))],
            sel=[r['key'] for r in csv.DictReader(open(f'{D}/selection_methods.csv'))],
            people=[[r['key'], r['name']] for r in people], bodies=[])
for b in bodies:
    bi = int(b['b']); t0 = day(b['complete_from'])
    ev = []   # (day, seat, person, party, caucus)
    filled_at_t0 = set()
    for t in terms[bi]:
        s = int(t['s']); st = day(t['start']) or t0; en = day(t['end'])
        ev.append((st, s, int(t['p']), int(t['party']), int(t['caucus'] or 0), 1))
        if en is not None: ev.append((en, s, 0, 0, 0, 0))
        if st <= t0 and (en is None or en > t0): filled_at_t0.add(s)
    # seats empty at t0 are known vacancies from t0 (for Congress: also every gap after t0 is a vacancy end-event above)
    for s in range(len(seats[bi])):
        if s not in filled_at_t0: ev.append((t0, s, 0, 0, 0, 0))
    # order: by day, vacancy-closing before new holder on the same day/seat
    ev.sort(key=lambda e: (e[0], e[1], e[5]))
    flat, prev = [], 0
    for d, s, p, pa, ca, _ in ev:
        flat += [d - prev, s, p, pa, ca]; prev = d
    sv = seats[bi]
    pack['bodies'].append(dict(key=b['key'], st=b['st'], kind=b['kind'], office=b['office'], n=int(b['seats']), maj=int(b['majority']),
                               unit=b['unit_type'], term=b['term'], sel=int(b['sel']), t0=t0,
                               dist=[r['dist'] for r in sv], geoid=[r['geoid'] for r in sv],
                               valid={str(i): [day(r['valid_from']), day(r['valid_to'])] for i, r in enumerate(sv) if r['valid_from'] or r['valid_to']},
                               up26=''.join(r['up26'] if r['up26'] != '' else '-' for r in sv), ev=flat,
                               **({'role': [r.get('role', '') for r in sv]} if any(r.get('role') for r in sv) else {}),
                               **({'place': b['geoid'], 'entity': b['entity']} if b.get('geoid') else {})))
# ---- results: per body list of contests [dday, stage, slots, n_up, total, label, cands...]
STAGE = {'general': 0, 'runoff': 1, 'special': 2, 'special_runoff': 3, 'retention': 4, 'primary_decided': 5, 'unopposed': 6}
rc = collections.defaultdict(list)
if os.path.exists(f'{D}/results_contests.csv'):
    cands = collections.defaultdict(list)
    for r in csv.DictReader(open(f'{D}/results_candidates.csv')):
        cands[int(r['c'])].append([int(r['p']), int(r['party']), int(r['votes']) if r['votes'] else -1, int(r['win']) + 2 * int(r['inc'])])
    for r in csv.DictReader(open(f'{D}/results_contests.csv')):
        sl = [int(x) for x in r['seats'].split()]
        rc[int(r['b'])].append([day(r['date']), STAGE[r['stage']], sl if len(sl) != 1 else sl[0] if sl else -1, int(r['n_up']),
                                int(r['total']) if r['total'] else -1, '' if sl else r['district'], [x for cc in cands[int(r['c'])] for x in cc]])
    for b, bp in zip(bodies, pack['bodies']):
        L = sorted(rc[int(b['b'])], key=lambda x: x[0]); prev = 0
        for x in L: d_ = x[0]; x[0] = d_ - prev; prev = d_
        bp['res'] = L
    pack['res_fmt'] = '[dday, stage(0 gen,1 runoff,2 special,3 special_runoff,4 retention,5 primary_decided,6 unopposed/canceled), slot|[slots]|-1, n_up, total|-1, district label if unlinked, [p, party, votes|-1, win+2*inc, ...]]; retention: yes row first then no row'
js = json.dumps(pack, separators=(',', ':'), ensure_ascii=False)
open(f'{D}/holders.pack.json', 'w').write(js)
gzip.open(f'{D}/holders.pack.json.gz', 'wb', 9).write(js.encode())
# ---- self-test: replay at the snapshot and compare with terms.csv
def replay(bp, at):
    occ = [(0, 9, 0)] * len(bp['dist']); d = 0; e = bp['ev']
    for i in range(0, len(e), 5):
        d += e[i]
        if d > at: break
        occ[e[i + 1]] = (e[i + 2], e[i + 3], e[i + 4])
    return occ
snap = day('2026-10-18'); bad = 0
for b, bp in zip(bodies, pack['bodies']):
    occ = replay(bp, snap)
    want = {}
    for t in terms[int(b['b'])]:
        if (day(t['start']) or 0) <= snap and (not t['end'] or day(t['end']) > snap): want[int(t['s'])] = int(t['p'])
    got = {s: o[0] for s, o in enumerate(occ) if o[0]}
    if got != want: bad += 1; print('MISMATCH', b['key'], len(got), len(want))
print('replay mismatches', bad)
# composition table
rows = []
for b, bp in zip(bodies, pack['bodies']):
    dates = ['2017-01-03', '2019-01-03', '2021-01-03', '2023-01-03', '2025-01-03', '2026-10-18'] if b['st'] == 'US' else [d_ for d_ in ['2017-02-01', '2019-02-01', '2021-02-01', '2023-02-01', '2025-02-01'] if d_ >= b['complete_from']] + ['2026-10-18']
    for ds in dates:
        dd = day(ds); occ = replay(bp, dd)
        act = [o for i, o in enumerate(occ) if not (str(i) in bp['valid'] and ((bp['valid'][str(i)][0] or -1) > dd or (bp['valid'][str(i)][1] or 10**9) <= dd))]
        assert len(act) == bp['n'], (b['key'], ds, len(act))
        for basis, f in (('party', lambda o: o[1]), ('caucus', lambda o: o[2] or o[1])):
            c = collections.Counter(f(o) for o in act)
            for pc, n in sorted(c.items()): rows.append([b['b'], ds, basis, pc, n])
with open(f'{D}/composition.csv', 'w', newline='') as f:
    w = csv.writer(f, lineterminator='\n'); w.writerow(['b', 'date', 'basis', 'party', 'n']); w.writerows(rows)
print('pack bytes', len(js), 'gz', os.path.getsize(f'{D}/holders.pack.json.gz'))
# lite pack: structure + party events only (no people table, no person ids in events -> 4-tuples)
lite = dict(pack); lite['people'] = None; lite['bodies'] = []
for bp in pack['bodies']:
    e = bp['ev']; q = dict(bp); q['ev'] = [x for i in range(0, len(e), 5) for x in (e[i], e[i + 1], e[i + 3], e[i + 4])]
    if 'res' in bp:
        q['res'] = [x[:6] + [[v for i in range(0, len(x[6]), 4) for v in x[6][i + 1:i + 4]]] for x in bp['res']]
    lite['bodies'].append(q)
lite['v'] = 'lite-1'
js2 = json.dumps(lite, separators=(',', ':'), ensure_ascii=False)
gzip.open(f'{D}/holders.lite.json.gz', 'wb', 9).write(js2.encode())
print('lite bytes', len(js2), 'gz', os.path.getsize(f'{D}/holders.lite.json.gz'))
