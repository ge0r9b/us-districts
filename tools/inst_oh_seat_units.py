#!/usr/bin/env python3
"""Step 7 of the officeholder pipeline (after inst_county_government_govbot.py): SCHEMA b66f889 alignment. Idempotent.

1. unit_key on every officeholder row: the TIGER GEOID where the row has one; else a 'seat' unit (no geometry,
   SCHEMA unit_type 'seat'): seat:<chamber slug>:<district label, lowercased, non-alphanumerics to '-'>; House delegates use the
   Clerk statedistrict code (seat:us-house:PR00). Those rows get unit_layer 'seat' and boundary_set from unit_plan
   (cd116 -> tiger-2020-cd116, cd119 / sldl2024 / sldu2024 -> v2-2024).
2. seat_member_units.csv: NH floterial seat -> its base sldl districts, derived ONLY from the official statute RSA 662:5
   (State Representative Districts, 2022, 9:1): a floterial's members are the districts of the same county whose towns/wards
   are all in the floterial's list and whose union is exactly that list. Base district -> TIGER 2024 SLDL GEOID by the
   Gazetteer label 'State House District <County> <NN>'. Anything that doesn't check out exactly is a gap, not a link.
3. county_government.csv source_record_id = the record id in its first cited source: govbot_entity_id (Governments bot) or cog_pid6 (CoG 2022).
4. the RSA 662:5 source goes into sources.csv (stable id, tools/inst_sources.py).
usage: inst_oh_seat_units.py <repo> --rsa DIR(662-5.htm, retrieved_at.txt) --gaz24 DIR [--check]
"""
import csv, hashlib, html, io, os, re, sys, collections as C
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inst_sources import Registry
R = sys.argv[1]; D = os.path.join(R, 'data-v3/inst')
RSA = sys.argv[sys.argv.index('--rsa') + 1]; GAZ = sys.argv[sys.argv.index('--gaz24') + 1]
OHF = ['officeholders_house_current', 'officeholders_house_2024', 'officeholders_house_2020', 'officeholders_stateleg_current', 'officeholders_stateleg_2024']
RSA_URL = 'https://gc.nh.gov/rsa/html/LXIII/662/662-5.htm'
BS = {'cd116': 'tiger-2020-cd116', 'cd119': 'v2-2024', 'sldl2024': 'v2-2024', 'sldu2024': 'v2-2024'}

def rd(f):
    with open(os.path.join(D, f + '.csv'), encoding='utf-8', newline='') as fh:
        r = csv.DictReader(fh); return list(r.fieldnames), list(r)
def dump(cols, rows):
    b = io.StringIO(); w = csv.DictWriter(b, cols, lineterminator='\n'); w.writeheader(); w.writerows(rows); return b.getvalue()
def slug(s): return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

def run():
    out = {}; gaps = []; stats = C.Counter(); seats = {}
    for f in OHF:
        cols, rows = rd(f)
        if 'unit_key' not in cols: cols.insert(cols.index('unit_geoid') + 1, 'unit_key')
        for r in rows:
            if r['unit_geoid']:
                r['unit_key'] = r['unit_geoid']; continue
            if r.get('unit_layer') != 'seat': r['_orig_layer'] = r['unit_layer']
            ch = r['entity_id'].split(':', 1)[-1]
            key = 'seat:%s:%s' % (ch, r['statedistrict'] if f.startswith('officeholders_house') else slug(r['district']))
            assert r['unit_plan'] in BS, (f, r['unit_plan'])
            r['unit_key'] = key; r['unit_layer'] = 'seat'; r['boundary_set'] = BS[r['unit_plan']]
            stats['rows_seat_unit'] += 1; stats['rows_' + f] += 1
            seats[(key, r['boundary_set'])] = (r['entity_id'], r['join_status'])
        out[f] = (cols, rows)
    # county_government source_record_id
    cols, rows = rd('county_government')
    if 'source_record_id' not in cols: cols.append('source_record_id')
    for r in rows:
        f0 = r['source_id'].split(';')[0]
        if f0.startswith('repo-governments-'): r['source_record_id'] = r['govbot_entity_id']
        elif f0.startswith('census-cog2022-'): r['source_record_id'] = r['cog_pid6']
        else: raise SystemExit('unexpected first source ' + f0)
    out['county_government'] = (cols, rows)
    # RSA 662:5
    raw = open(os.path.join(RSA, '662-5.htm'), 'rb').read(); sha = hashlib.sha256(raw).hexdigest()
    ret = open(os.path.join(RSA, 'retrieved_at.txt')).read().strip()
    reg = Registry(); reg.load(os.path.join(D, 'sources.csv'))
    rsa_id = reg.add('nh-rsa-662-5', 'New Hampshire RSA 662:5 State Representative Districts (2022, 9:1, eff. Mar. 23, 2022), official text, General Court',
                     RSA_URL, 'public record (New Hampshire statute)', ret, '', sha)
    t = raw.decode('latin-1')
    dist = {}   # (county, n) -> [towns]
    for m in re.finditer(r'(\b[IVXL]+)\.\s+([A-Za-z ]+?) County\s*<br>\s*<table>(.*?)</table>', t, re.S):
        county = m.group(2).strip(); cur = None; trs = re.findall(r'<tr>(.*?)</tr>', m.group(3), re.S)
        cells = [[html.unescape(re.sub(r'<[^>]+>', '', c)).strip() for c in re.findall(r'<td>(.*?)</td>', tr, re.S)] for tr in trs]
        cells = [(c + ['', '', ''])[:3] for c in cells if any(c)]
        for i, c in enumerate(cells):
            if c[0].startswith('District No.'): cur = (county, int(c[0].split('.')[1])); dist[cur] = []
            last = i + 1 == len(cells) or cells[i + 1][0].startswith('District No.')
            name = c[1]
            if not name and c[0].startswith('District No.') and not c[2]: continue   # district label alone on its row; towns follow
            if not name: gaps.append({'gap': 'nh_rsa_row_unparsed', 'key': f'{cur[0]} {cur[1]}' if cur else '', 'detail': '|'.join(c), 'source_id': rsa_id}); continue
            if not last and len(c) > 2 and c[2]: name = f'{name} {c[2]}'   # ward number split into the count column
            if last and (len(c) < 3 or not c[2]) and re.search(r' \d+$', name):
                if re.search(r'Ward \d+$', name):
                    gaps.append({'gap': 'nh_rsa_ward_number_ambiguous', 'key': f'{cur[0]} {cur[1]}', 'detail': name + ' (no count cell)', 'source_id': rsa_id})
                else: name = re.sub(r' \d+$', '', name); stats['rsa_count_merged_into_name_cell'] += 1   # 'Westmoreland 2' = Westmoreland, 2 reps
            if last and name.endswith(' Ward'): gaps.append({'gap': 'nh_rsa_ward_number_ambiguous', 'key': f'{cur[0]} {cur[1]}', 'detail': name, 'source_id': rsa_id})
            dist[cur].append(name)
    stats['rsa_districts'] = len(dist)
    tiger = {}
    for line in open(os.path.join(GAZ, '2024_Gaz_sldl_national.txt'), encoding='utf-8', errors='replace').read().splitlines()[1:]:
        p = [x.strip() for x in line.split('\t')]
        if p[0] != 'NH': continue
        m = re.match(r'State House District (.+) (\d+)$', p[2])
        if m: tiger[(m.group(1), int(m.group(2)))] = p[1]
    stats['tiger_nh_sldl'] = len(tiger)
    links = []
    flo = sorted({k for k, (e, js) in seats.items() if js == 'no_v3_unit_floterial'})
    for key, bs in flo:
        lab = key.split(':', 2)[2]; m = re.match(r'(.+)-(\d+)$', lab)
        cand = [k for k in dist if slug(k[0]) == m.group(1) and k[1] == int(m.group(2))]
        if len(cand) != 1: gaps.append({'gap': 'nh_floterial_not_in_rsa_662_5', 'key': key, 'detail': lab, 'source_id': rsa_id}); continue
        F = cand[0]; tf = set(dist[F])
        if F in tiger: gaps.append({'gap': 'nh_floterial_has_tiger_geoid', 'key': key, 'detail': tiger[F], 'source_id': rsa_id}); continue
        mem = sorted(k for k in dist if k != F and k[0] == F[0] and set(dist[k]) <= tf and set(dist[k]) != tf)
        mem = [k for k in mem if k in tiger]
        towns = [x for k in mem for x in dist[k]]
        if not mem or set(towns) != tf or len(towns) != len(set(towns)):
            gaps.append({'gap': 'nh_floterial_members_not_exact', 'key': key, 'detail': f"towns {sorted(tf)}; candidate base districts {[f'{a} {b}' for a, b in mem]}", 'source_id': rsa_id}); continue
        for k in mem:
            links.append({'seat_unit_key': key, 'boundary_set': bs, 'member_unit_layer': 'sldl', 'member_unit_key': tiger[k], 'member_boundary_set': 'v2-2024',
                          'member_label': f'{k[0]} {k[1]}', 'towns': ';'.join(dist[k]), 'source_id': rsa_id})
    stats['floterial_seats'] = len(flo); stats['floterials_linked'] = len({l['seat_unit_key'] for l in links}); stats['member_links'] = len(links)
    for k, (e, js) in sorted(seats.items()): stats['seat_units_' + js] += 1
    stats['seat_units'] = len(seats); stats['distinct_seat_keys'] = len({k for k, _ in seats})
    return out, links, gaps, stats, reg

out, links, gaps, stats, reg = run()
texts = {f: dump(c, [{k: v for k, v in r.items() if not k.startswith('_')} for r in rows]) for f, (c, rows) in out.items()}
texts['seat_member_units'] = dump(['seat_unit_key', 'boundary_set', 'member_unit_layer', 'member_unit_key', 'member_boundary_set', 'member_label', 'towns', 'source_id'], links)
texts['seat_member_unit_gaps'] = dump(['gap', 'key', 'detail', 'source_id'], gaps)
for f, s in texts.items():
    with open(os.path.join(D, f + '.csv'), 'w', encoding='utf-8', newline='') as fh: fh.write(s)
reg.write(os.path.join(D, 'sources.csv'), keep_existing=False)
import json
json.dump(dict(sorted(stats.items())), open(os.path.join(D, 'seat_units_summary.json'), 'w'), indent=1)
print(json.dumps(dict(sorted(stats.items())), indent=1)); print(len(gaps), 'gaps'); [print(g) for g in gaps]
