#!/usr/bin/env python3
"""Step 6: derive data-v3/inst/county_government.csv (TIGER 2024 rows) from the Governments bot's
data-v3/institutions/governments/county_government_check.csv (+ its local/<ST>.csv gov_status), read with `git show <gov-ref>`
(read only; nothing is written under data-v3/institutions/). Our own CoG 2022 pull (the current file) is the comparison
baseline: every difference goes to county_government_govbot_diffs.csv.

gov_status (new column): bot 'independent' -> government, bot 'dependent' -> dependent; a county-equivalent with no CoG
government (bot cog_county_government = no and no governing city) -> area_only (ours).
has_own_government = the bot's cog_county_government. cog_pid6 = the bot's cog_id, or the independent city named in its note
('county-equivalent governed by independent city cog:<id>'). Where the bot names no unit but our pull has the consolidated
city-county government (CoG type 2), ours is kept and the row says so (diff kind bot_no_unit_ours_consolidated_municipal).
The 2020 CT county rows are not in the bot file (TIGER 2024 only) and stay as they are. The bot's 78 PR municipios are not
carried (CoG does not cover PR; v2 has no PR counties); listed in the diffs.
usage: inst_county_government_govbot.py <repo> --gov-ref <sha> [--dir data-v3/inst]
"""
import csv, io, os, re, subprocess, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inst_sources import Registry
R = sys.argv[1]; REF = sys.argv[sys.argv.index('--gov-ref') + 1]
D = os.path.join(R, sys.argv[sys.argv.index('--dir') + 1] if '--dir' in sys.argv else 'data-v3/inst')
GP = 'data-v3/institutions/governments'
SHA = subprocess.run(['git', '-C', R, 'rev-parse', REF], capture_output=True, text=True, check=True).stdout.strip()
def show(p): return subprocess.run(['git', '-C', R, 'show', f'{SHA}:{p}'], capture_output=True, check=True).stdout.decode('utf-8')
chk = {r['county_geoid']: r for r in csv.DictReader(io.StringIO(show(f'{GP}/county_government_check.csv')))}
loc = {}
for f in subprocess.run(['git', '-C', R, 'ls-tree', '--name-only', SHA, f'{GP}/local/'], capture_output=True, text=True, check=True).stdout.split():
    for r in csv.DictReader(io.StringIO(show(f))): loc[r['cog_id']] = r
reg = Registry(); reg.load(os.path.join(D, 'sources.csv'))
ret = next(r['retrieved_at'] for r in loc.values())[:10]
BOT = reg.add(None, 'Governments bot, data-v3/institutions/governments (county_government_check.csv + local/<ST>.csv gov_status; from CoG 2022 + TIGER 2024 Gazetteer)',
              f'https://github.com/ge0r9b/us-districts/tree/{SHA}/{GP}', 'public domain (US government work)', ret, SHA)
COG = next(k for k in reg.rows if k.startswith('census-cog2022-'))
TIG = next(k for k in reg.rows if k.startswith('census-tiger2024-county-'))
with open(os.path.join(D, 'county_government.csv'), encoding='utf-8', newline='') as fh:
    rd = csv.DictReader(fh); cols = rd.fieldnames; rows = list(rd)
base = {r['county_geoid']: dict(r) for r in rows if r['vintage'] == '2024'}  # our CoG pull, before this step
if 'gov_status' not in cols: cols = cols[:cols.index('has_own_government') + 1] + ['gov_status'] + cols[cols.index('has_own_government') + 1:]
if 'govbot_entity_id' not in cols: cols = cols[:cols.index('cog_pid6') + 1] + ['govbot_entity_id'] + cols[cols.index('cog_pid6') + 1:]
GST = {'independent': 'government', 'dependent': 'dependent'}
D_ = []
def diff(g, kind, field, ours, bot, note=''): D_.append({'county_geoid': g, 'kind': kind, 'field': field, 'ours_cog2022_pull': ours, 'governments_bot': bot, 'note': note, 'source_id': f'{COG};{BOT}'})
for r in rows:
    if r['vintage'] != '2024':
        r.setdefault('gov_status', 'area_only' if r['has_own_government'] == 'no' else ''); r.setdefault('govbot_entity_id', ''); continue
    b = chk[r['county_geoid']]; o = base[r['county_geoid']]
    m = re.search(r'cog:(\d+)', b['note']); bpid = b['cog_id'] or (m.group(1) if m else '')
    if b['tiger_name'] != o['county_name']: diff(r['county_geoid'], 'name_differs', 'county_name', o['county_name'], b['tiger_name'])
    if b['cog_county_government'] != o['has_own_government']: diff(r['county_geoid'], 'has_own_government_differs', 'has_own_government', o['has_own_government'], b['cog_county_government'])
    r['has_own_government'] = b['cog_county_government']
    pid = bpid
    if not bpid and o['cog_pid6']:
        pid = o['cog_pid6']; diff(r['county_geoid'], 'bot_no_unit_ours_consolidated_municipal', 'cog_pid6', o['cog_pid6'], '', f"{o['cog_unit_name']} ({o['cog_unit_type']}); kept from our pull")
        r['government_note'] = '; '.join(x for x in [o['government_note'], 'governing unit from our CoG 2022 pull (the Governments bot check names none)'] if x)
    elif bpid != o['cog_pid6']: diff(r['county_geoid'], 'cog_pid6_differs', 'cog_pid6', o['cog_pid6'], bpid); 
    if bpid and b['cog_name'] and b['cog_name'] != o['cog_unit_name']: diff(r['county_geoid'], 'cog_name_differs', 'cog_unit_name', o['cog_unit_name'], b['cog_name'])
    if bpid and not b['cog_name'] and o['cog_unit_name']: diff(r['county_geoid'], 'bot_unit_name_blank', 'cog_unit_name', o['cog_unit_name'], '', 'bot names the unit only in note as cog:<id>')
    r['cog_pid6'] = pid
    if pid:
        L = loc.get(pid); assert L, (r['county_geoid'], pid)
        r['govbot_entity_id'] = L['entity_id']; r['gov_status'] = GST[L['gov_status']]
        if L['name'] != (o['cog_unit_name'] or L['name']): diff(r['county_geoid'], 'local_name_differs', 'cog_unit_name', o['cog_unit_name'], L['name'])
    else:
        r['govbot_entity_id'] = ''; r['gov_status'] = 'area_only'
    r['source_id'] = ';'.join([BOT, COG, TIG])
for g, b in sorted(chk.items()):
    if g not in base: diff(g, 'bot_only_not_carried', 'county_geoid', '', f"{b['tiger_name']} ({b['state']})", 'Puerto Rico municipio: CoG 2022 covers no PR governments; v2 has no PR counties' if g[:2] == '72' else '')
with open(os.path.join(D, 'county_government.csv'), 'w', encoding='utf-8', newline='') as fh:
    w = csv.DictWriter(fh, cols, lineterminator='\n'); w.writeheader(); w.writerows(rows)
DC = ['county_geoid', 'kind', 'field', 'ours_cog2022_pull', 'governments_bot', 'note', 'source_id']
with open(os.path.join(D, 'county_government_govbot_diffs.csv'), 'w', encoding='utf-8', newline='') as fh:
    w = csv.DictWriter(fh, DC, lineterminator='\n'); w.writeheader(); w.writerows(D_)
reg.write(os.path.join(D, 'sources.csv'))
print('gov ref', SHA, 'rows', len(rows), collections.Counter(r['gov_status'] for r in rows), 'diffs', collections.Counter(d['kind'] for d in D_))
