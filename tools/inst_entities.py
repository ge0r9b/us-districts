#!/usr/bin/env python3
"""Build data-v3/inst/entities.csv (institution registry, ENTITIES_SCHEMA.md) and
data-v3/inst/entity_geoid_xwalk.csv, entity_v2_rows.csv, entity_gaps.csv, entities_summary.json.

usage: inst_entities.py <repo> --gaz24 DIR --gaz20 DIR --cog XLSX --geojson DIR --oh-ref REF [--out DIR]

All inputs read-only. Officeholder files and county_government.csv are read with `git show <oh-ref>:...`.
Nothing is name-matched: every link is by GEOID / FIPS code (Census), or by the officeholder files' own
entity_id + unit key. Overlap shares come from the geo lane's TIGER 2024 GeoJSON (coverage-simplified 0.0005 deg),
measured in EPSG:6933 (equal area).
"""
import argparse, csv, gzip, io, json, os, re, subprocess, sys, hashlib, collections as C
import numpy as np, shapely
from shapely.geometry import shape
from pyproj import Transformer

ap = argparse.ArgumentParser()
ap.add_argument('repo'); ap.add_argument('--gaz24', required=True); ap.add_argument('--gaz20', required=True)
ap.add_argument('--cog', required=True); ap.add_argument('--geojson', required=True)
ap.add_argument('--oh-ref', required=True); ap.add_argument('--out')
A = ap.parse_args()
R = A.repo; OUT = A.out or os.path.join(R, 'data-v3/inst'); os.makedirs(OUT, exist_ok=True)
GEO = os.path.join(R, 'data-v3/geo')
EQ = 0.9  # mutual-overlap threshold, same as data-v3/geo ALIGNMENT.md / town_pairs

# ANSI/FIPS state codes (Census Bureau)
ST = [('01','AL','Alabama'),('02','AK','Alaska'),('04','AZ','Arizona'),('05','AR','Arkansas'),('06','CA','California'),
('08','CO','Colorado'),('09','CT','Connecticut'),('10','DE','Delaware'),('11','DC','District of Columbia'),('12','FL','Florida'),
('13','GA','Georgia'),('15','HI','Hawaii'),('16','ID','Idaho'),('17','IL','Illinois'),('18','IN','Indiana'),('19','IA','Iowa'),
('20','KS','Kansas'),('21','KY','Kentucky'),('22','LA','Louisiana'),('23','ME','Maine'),('24','MD','Maryland'),
('25','MA','Massachusetts'),('26','MI','Michigan'),('27','MN','Minnesota'),('28','MS','Mississippi'),('29','MO','Missouri'),
('30','MT','Montana'),('31','NE','Nebraska'),('32','NV','Nevada'),('33','NH','New Hampshire'),('34','NJ','New Jersey'),
('35','NM','New Mexico'),('36','NY','New York'),('37','NC','North Carolina'),('38','ND','North Dakota'),('39','OH','Ohio'),
('40','OK','Oklahoma'),('41','OR','Oregon'),('42','PA','Pennsylvania'),('44','RI','Rhode Island'),('45','SC','South Carolina'),
('46','SD','South Dakota'),('47','TN','Tennessee'),('48','TX','Texas'),('49','UT','Utah'),('50','VT','Vermont'),
('51','VA','Virginia'),('53','WA','Washington'),('54','WV','West Virginia'),('55','WI','Wisconsin'),('56','WY','Wyoming')]
TERR = [('60','AS','American Samoa','AQ00'),('66','GU','Guam','GU00'),('69','MP','Commonwealth of the Northern Mariana Islands','MP00'),
        ('72','PR','Puerto Rico','PR00'),('78','VI','United States Virgin Islands','VI00')]
FIPS = {f: (ab, nm) for f, ab, nm in ST}
BYNAME = {nm: f for f, ab, nm in ST}
BYAB = {ab: f for f, ab, nm in ST}

PD = 'public domain (US government work)'
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
SRC = {}
def gazsrc(year, f):
    return f"U.S. Census Bureau, {year} TIGER/Line Gazetteer ({f})"
S_ST = 'ANSI/FIPS state codes (U.S. Census Bureau)'
S_GEOJSON = 'U.S. Census Bureau TIGER/Line 2024 county subdivisions + places (FUNCSTAT, CLASSFP, NAMELSAD, geometry) via data-v3/geo towns_2024/places_2024 GeoJSON (tools/v3_geojson_2024.py)'
S_COG = 'U.S. Census Bureau, 2022 Census of Governments, Government Units Listing (Govt_Units_2022_Final.xlsx, General Purpose)'
S_CG = 'data-v3/inst/county_government.csv (CoG 2022 + TIGER 2024 FUNCSTAT)'
S_OH = 'data-v3/inst officeholder files (entity_id + district as published there)'

def git_show(path):
    return subprocess.run(['git', '-C', R, 'show', f'{A.oh_ref}:{path}'], capture_output=True, check=True).stdout.decode('utf-8')
OH_SHA = subprocess.run(['git', '-C', R, 'rev-parse', A.oh_ref], capture_output=True, text=True).stdout.strip()

def gaz(path):
    raw = open(path, 'rb').read()
    try: t = raw.decode('utf-8')
    except UnicodeDecodeError: t = raw.decode('latin-1')
    lines = t.splitlines(); h = [x.strip() for x in lines[0].split('\t')]
    return [dict(zip(h, [x.strip() for x in l.split('\t')])) for l in lines[1:] if l.strip()]

def rcsv(p): return list(csv.DictReader(open(p, encoding='utf-8')))

# ---------------- containers ----------------
ENT = {}       # (entity_id, vintage) -> row
XW = []        # xwalk rows
GIDX = {}      # (geoid_layer, geoid, vintage) -> entity_id
GAPS = []      # entity_gaps rows: kind, key, detail
COLS = ['entity_id','vintage','level','kind','type','state_fips','state','name','alias','label','gov_status','unit_layer','geoid',
        'geoid_alt','parent_entity_id','officeholder_entity_id','officeholder_unit_vintage','officeholder_unit_key','cog_pid6',
        'v2_layer','v2_row','flags','source','license']
def add(**kw):
    r = {c: '' for c in COLS}; r.update({k: ('' if v is None else v) for k, v in kw.items()})
    r['_alias'] = set(); r['_flags'] = []; r['_v2'] = []; r['_src'] = [x for x in r['source'].split('; ') if x]
    k = (r['entity_id'], r['vintage'])
    assert k not in ENT, k
    ENT[k] = r; return r
def idx(layer, geoid, vintage, eid):
    k = (layer, geoid, vintage)
    assert GIDX.get(k, eid) == eid, (k, GIDX[k], eid)
    GIDX[k] = eid
def flag(r, f):
    if f not in r['_flags']: r['_flags'].append(f)
def src(r, s):
    if s not in r['_src']: r['_src'].append(s)

# ---------------- nation, states, territories ----------------
add(entity_id='nation:us', level='federal', kind='nation', type='federal_government', name='United States', gov_status='government',
    source='U.S. Constitution', license=PD)
for f, ab, nm in ST:
    r = add(entity_id=f'state:{f}', vintage='2024', level='state', kind='state', type='federal_district' if f == '11' else 'state',
            state_fips=f, state=nm, name=nm, gov_status='government', unit_layer='state', geoid=f, parent_entity_id='nation:us',
            source=S_ST + ('; U.S. Constitution' if f != '11' else '; ' + S_COG), license=PD)
    if f == '11': r['cog_pid6'] = ''  # set below when DC's city/county GEOIDs fold in
    idx('state', f, '2024', r['entity_id'])
    if f != '11':
        XW.append({'entity_id': r['entity_id'], 'geoid_layer': 'state', 'geoid': f, 'relation': 'primary', 'relation_detail': '',
                   'share_of_geoid_in_entity': '1.0000', 'share_of_entity_in_geoid': '1.0000', 'vintage': '2024', 'source': S_ST})
for f, ab, nm, code in TERR:
    add(entity_id=f'territory:{f}', vintage='2024', level='federal', kind='territory', type='territory', state_fips=f, state=nm, name=nm,
        unit_layer='state', geoid=f, parent_entity_id='nation:us', source=S_ST, license=PD,
        flags='')
    flag(ENT[(f'territory:{f}', '2024')], 'outside_v2_scope:territory_with_house_delegate')
    flag(ENT[(f'territory:{f}', '2024')], 'gov_status_unknown:not_in_cog2022_scope')
    idx('state', f, '2024', f'territory:{f}')
    XW.append({'entity_id': f'territory:{f}', 'geoid_layer': 'state', 'geoid': f, 'relation': 'primary', 'relation_detail': '',
               'share_of_geoid_in_entity': '1.0000', 'share_of_entity_in_geoid': '1.0000', 'vintage': '2024', 'source': S_ST})

# ---------------- CoG 2022 general purpose ----------------
import openpyxl
wb = openpyxl.load_workbook(A.cog, read_only=True)
ws = wb['General Purpose']; it = ws.iter_rows(values_only=True); h = next(it)
COG = [dict(zip(h, r)) for r in it]
COG_BY_CODE = C.defaultdict(list)
for c in COG:
    if c['UNIT_TYPE'][0] in '23':
        COG_BY_CODE[(c['FIPS_STATE'] or '') + (c['FIPS_PLACE'] or '')].append(c)
COG_BY_PID = {c['CENSUS_ID_PID6']: c for c in COG}
assert all(len(v) == 1 for v in COG_BY_CODE.values())

# ---------------- TIGER 2024 places / cousubs (geo lane GeoJSON) ----------------
def loadgj(name):
    d = json.load(gzip.open(os.path.join(A.geojson, name)))
    return d['features']
TF = loadgj('towns_2024.geojson.gz'); PF = loadgj('places_2024.geojson.gz')
TR = Transformer.from_crs(4326, 6933, always_xy=True)
def proj(feats):
    g = np.array([shape(f['geometry']) for f in feats], dtype=object)
    g = shapely.transform(g, lambda xy: np.column_stack(TR.transform(xy[:, 0], xy[:, 1])))
    g = shapely.make_valid(g)
    return g
print('projecting geometry ...', file=sys.stderr)
TG = proj(TF); PG = proj(PF)
TA = shapely.area(TG); PA = shapely.area(PG)
TP = [f['properties'] for f in TF]; PP = [f['properties'] for f in PF]
TI = {p['geoid']: i for i, p in enumerate(TP)}; PI = {p['geoid']: i for i, p in enumerate(PP)}
# place x cousub intersection areas (all places; cousubs tile counties, so county shares are sums)
tree = shapely.STRtree(TG)
pi_, ti_ = tree.query(PG, predicate='intersects')
inter = shapely.area(shapely.intersection(PG[pi_], TG[ti_]))
PX = C.defaultdict(dict)  # place geoid -> {cousub geoid: area}
for a, b, ar in zip(pi_, ti_, inter):
    if ar > 0: PX[PP[a]['geoid']][TP[b]['geoid']] = ar
CTY_AREA = C.Counter()
for i, p in enumerate(TP): CTY_AREA[p['geoid'][:5]] += TA[i]
def place_cty(pg):  # county geoid -> intersection area
    o = C.Counter()
    for cg, ar in PX[pg].items(): o[cg[:5]] += ar
    return o
def descr(p):
    n, nl = p['name'], p['namelsad']
    return nl[len(n):].strip() if nl.startswith(n) else (p.get('lsad') or '')
FUNC = {'A': 'active government', 'B': 'active government, partially consolidated', 'C': 'active government consolidated with another',
        'F': 'fictitious entity', 'G': 'active government subordinate to another unit', 'I': 'inactive governmental unit',
        'N': 'nonfunctioning legal entity', 'S': 'statistical entity'}

def rel(s_g, s_w):
    """s_g: share of this GEOID's area inside the entity; s_w: share of the entity's area inside this GEOID."""
    if s_g >= EQ and s_w >= EQ: return 'equal'
    if s_g >= EQ: return 'split'        # this GEOID is one part of an entity that spans several GEOIDs of the layer
    if s_w >= EQ: return 'contained'    # the entity lies inside this (larger) GEOID
    return 'partial'

# ---------------- counties ----------------
CG = list(csv.DictReader(io.StringIO(git_show('data-v3/inst/county_government.csv'))))
CG24 = {r['county_geoid']: r for r in CG if r['vintage'] == '2024'}
GZC24 = {r['GEOID']: r for r in gaz(os.path.join(A.gaz24, '2024_Gaz_counties_national.txt')) if r['GEOID'][:2] in FIPS}
GZC20 = {r['GEOID']: r for r in gaz(os.path.join(A.gaz20, '2020_Gaz_counties_national.txt')) if r['GEOID'][:2] in FIPS}
FS = {r['geoid']: r for r in rcsv(os.path.join(GEO, 'county_funcstat.csv'))}
assert set(GZC24) == set(CG24) == set(FS), (len(GZC24), len(CG24), len(FS))

# ---------------- municipalities + towns ----------------
# candidates: every incorporated place (CLASSFP C*), every cousub with a governmental FUNCSTAT (A/B/C/G) or a CoG 2022 code,
# plus any place/cousub that a v1 or v2 row carries (so every v1/v2 town and place row resolves).
v1t = rcsv(os.path.join(GEO, 'v1_towns.csv'))
v1_place = {r['geoid'] for r in v1t if r['tiger_kind'] == 'place'}
v1_cousub = {r['geoid'] for r in v1t if r['tiger_kind'] != 'place'}
assert all(len(g) == 10 for g in v1_cousub)
pcand = [p for p in PP if p['classfp'].startswith('C') or p['v2_places'] or p['v2_parts'] or p['geoid'] in v1_place
         or (p['geoid'] in COG_BY_CODE)]
ccand = [p for p in TP if p['funcstat'] in 'ABCG' or p['v2_parts'] or p['geoid'] in v1_cousub
         or (p['geoid'][:2] + p['geoid'][5:]) in COG_BY_CODE]
PC = {p['geoid']: p for p in pcand}
GROUP = {}   # primary key -> dict
code2grp = {}
for p in pcand:
    k = p['geoid']; GROUP[k] = {'place': p, 'cousubs': [], 'counties': [], 'merged_place': []}
    code2grp[p['geoid']] = k
unpaired_code = []
for p in ccand:
    code = p['geoid'][:2] + p['geoid'][5:]
    if code in PC:
        pg = code; ar = PX[pg].get(p['geoid'], 0.0)
        s_g = ar / TA[TI[p['geoid']]] if TA[TI[p['geoid']]] else 0; s_w = ar / PA[PI[pg]] if PA[PI[pg]] else 0
        if s_g < 0.5 and s_w < 0.5:
            # same state + FIPS code = the same Census-coded entity; merged, but the simplified geometry does not show the overlap
            GAPS.append({'gap': 'same_code_place_cousub_overlap_unmeasured', 'key': p['geoid'], 'detail': f'place {pg}; share_in_place={s_g:.3f} place_in_cousub={s_w:.3f}; cousub aland={p["aland"]}; merged on FIPS code'})
        GROUP[pg]['cousubs'].append(p); continue
    else:
        unpaired_code.append(p)
# cousub-only governments: one entity per (state, FIPS code); parts in several counties become one entity
cg = C.defaultdict(list)
for p in unpaired_code: cg[p['geoid'][:2] + p['geoid'][5:]].append(p)
for code, parts in cg.items():
    parts.sort(key=lambda p: p['geoid'])
    k = 'T' + parts[0]['geoid']
    GROUP[k] = {'place': None, 'cousubs': parts, 'counties': [], 'merged_place': []}
# geo town_pairs "same" (mutual >= 90 %) where CoG 2022 lists only ONE of the two codes -> one government
tp = rcsv(os.path.join(GEO, 'town_pairs.csv'))
def grp_of(geoid):
    if len(geoid) == 7: return geoid if geoid in GROUP else None
    for k, g in GROUP.items():
        pass
    return None
C2G = {}
for k, g in GROUP.items():
    for p in g['cousubs']: C2G[p['geoid']] = k
    if g['place']: C2G[g['place']['geoid']] = k
def cogcodes(g):
    s = set()
    if g['place']: s.add(g['place']['geoid'])
    for p in g['cousubs']: s.add(p['geoid'][:2] + p['geoid'][5:])
    return {c for c in s if c in COG_BY_CODE}
pairs_merged = []; pairs_separate_gov = []
for t in tp:
    if t['class'] != 'same': continue
    ka, kb = C2G.get(t['geoid_a']), C2G.get(t['geoid_b'])
    if not ka or not kb or ka == kb: continue
    ca, cb = cogcodes(GROUP[ka]), cogcodes(GROUP[kb])
    if ca and cb:
        pairs_separate_gov.append((ka, kb, t)); continue
    if not ca and not cb:
        GAPS.append({'gap': 'town_pair_same_neither_in_cog', 'key': f"{t['geoid_a']}|{t['geoid_b']}", 'detail': t['name_a'] + ' / ' + t['name_b']}); continue
    keep, drop = (ka, kb) if ca else (kb, ka)
    gk, gd = GROUP[keep], GROUP.pop(kb if keep == ka else ka)
    if gk['place'] is None and gd['place'] is not None:   # keep place as primary per schema
        gk, gd = gd, gk; GROUP[keep] = gk
    gk['cousubs'] += gd['cousubs']
    if gd['place']: gk['merged_place'].append(gd['place'])
    gk.setdefault('pair_src', []).append(t)
    pairs_merged.append((keep, t))
    for p in gd['cousubs']: C2G[p['geoid']] = keep
    if gd['place']: C2G[gd['place']['geoid']] = keep
# consolidated city-counties / independent cities: county_government.csv names the CoG municipal unit (cog_pid6); its CoG code
# is a TIGER place -> the county GEOID joins that entity
cty_merged = {}
for cgeo, r in CG24.items():
    if r['has_own_government'] == 'no' and r['government_kind'] == 'municipal' and r['cog_pid6']:
        c = COG_BY_PID[r['cog_pid6']]; code = c['FIPS_STATE'] + c['FIPS_PLACE']
        k = C2G.get(code) or (code if code in GROUP else None)
        if k is None:
            GAPS.append({'gap': 'consolidated_county_cog_code_not_in_tiger', 'key': cgeo,
                         'detail': f"{r['county_name']}: CoG {r['cog_pid6']} {c['UNIT_NAME']} FIPS_PLACE {c['FIPS_PLACE']} matches no TIGER 2024 place/cousub code; county kept as its own entity"})
            continue
        GROUP[k]['counties'].append(cgeo); cty_merged[cgeo] = k
# NYC: 4 boroughs with no CoG unit of their own, TIGER county FUNCSTAT C, wholly inside New York city (place 3651000)
for cgeo, r in CG24.items():
    if cgeo in cty_merged or FS[cgeo]['tiger_funcstat'] not in 'CBF' or r['has_own_government'] != 'no': continue
    best = None
    for pg in PC:
        if pg[:2] != cgeo[:2]: continue
    # county share inside each place (via cousub tiling)
    o = C.Counter()
    for pg, d in PX.items():
        if pg[:2] != cgeo[:2] or pg not in PC: continue
        for cs, ar in d.items():
            if cs[:5] == cgeo: o[pg] += ar
    if o:
        pg, ar = o.most_common(1)[0]
        s = ar / CTY_AREA[cgeo]
        k = C2G.get(pg)
        if s >= EQ and k and cogcodes(GROUP[k]):
            GROUP[k]['counties'].append(cgeo); cty_merged[cgeo] = k
            continue
    GAPS.append({'gap': 'consolidated_county_no_government_linked', 'key': cgeo, 'detail': f"{r['county_name']}: FUNCSTAT {FS[cgeo]['tiger_funcstat']}, has_own_government=no; kept as county entity (area_only)"})

# ---------------- build county entities (not merged) ----------------
UNLINKED_CONS = {g['key'] for g in GAPS if g['gap'] == 'consolidated_county_cog_code_not_in_tiger'}
GAPS[:] = [g for g in GAPS if not (g['gap'] == 'consolidated_county_no_government_linked' and g['key'] in UNLINKED_CONS)]
for cgeo in sorted(GZC24):
    if cgeo in cty_merged: continue
    r = CG24[cgeo]; f = cgeo[:2]
    e = add(entity_id=f'county:{cgeo}', vintage='2024', level='county', kind='county', type=GZC24[cgeo]['NAME'].split()[-1].lower() if False else '',
            state_fips=f, state=FIPS[f][1], name=GZC24[cgeo]['NAME'], unit_layer='counties', geoid=cgeo,
            parent_entity_id=f'state:{f}', cog_pid6=r['cog_pid6'] if r['government_kind'] == 'county' else '',
            source=gazsrc(2024, '2024_Gaz_counties_national.txt') + '; ' + S_CG, license=PD)
    e['type'] = descr({'name': '', 'namelsad': ''}) or ''
    nm = GZC24[cgeo]['NAME']
    for suf in ['City and Borough', 'Census Area', 'Planning Region', 'Municipality', 'Borough', 'County', 'Parish', 'city']:
        if nm.endswith(' ' + suf) or nm == suf: e['type'] = suf.lower(); break
    hog = r['has_own_government']
    if cgeo in UNLINKED_CONS:
        flag(e, f"gov_status_unknown:consolidated_government_not_linked_to_tiger_code:cog_pid6={r['cog_pid6']}")
        e['cog_pid6'] = r['cog_pid6']; src(e, S_COG)
    elif hog == 'yes': e['gov_status'] = 'government'
    elif hog == 'no':
        e['gov_status'] = 'area_only'
        if r['government_kind'] == 'municipal': flag(e, f"county_area_governed_by_cog_municipal_unit:{r['cog_pid6']}")
    else: flag(e, 'gov_status_unknown')
    flag(e, f"tiger_funcstat:{FS[cgeo]['tiger_funcstat']}")
    idx('county', cgeo, '2024', e['entity_id'])
    XW.append({'entity_id': e['entity_id'], 'geoid_layer': 'county', 'geoid': cgeo, 'relation': 'primary', 'relation_detail': '',
               'share_of_geoid_in_entity': '1.0000', 'share_of_entity_in_geoid': '1.0000', 'vintage': '2024', 'source': gazsrc(2024, '2024_Gaz_counties_national.txt')})
for r in CG:
    if r['vintage'] != '2020': continue
    cgeo = r['county_geoid']; f = cgeo[:2]
    e = add(entity_id=f'county:{cgeo}', vintage='2020', level='county', kind='county', type='county', state_fips=f, state=FIPS[f][1],
            name=GZC20[cgeo]['NAME'], unit_layer='counties', geoid=cgeo, parent_entity_id=f'state:{f}',
            gov_status='area_only' if r['has_own_government'] == 'no' else '', source=gazsrc(2020, '2020_Gaz_counties_national.txt') + '; ' + S_CG, license=PD)
    flag(e, 'vintage_2020_only:replaced_by_ct_planning_regions_2022')
    idx('county', cgeo, '2020', e['entity_id'])
    XW.append({'entity_id': e['entity_id'], 'geoid_layer': 'county', 'geoid': cgeo, 'relation': 'primary', 'relation_detail': '',
               'share_of_geoid_in_entity': '1.0000', 'share_of_entity_in_geoid': '1.0000', 'vintage': '2020', 'source': gazsrc(2020, '2020_Gaz_counties_national.txt')})

# ---------------- build municipal / town entities ----------------
def lname(p): return p['namelsad']
for k, g in GROUP.items():
    pl = g['place']; parts = g['cousubs']
    if pl:
        prim = pl; eid = f"muni:place:{pl['geoid']}"; kind = 'municipality'; layer = 'places'
        whole_area = PA[PI[pl['geoid']]]
    else:
        prim = parts[0]; eid = f"town:cousub:{prim['geoid']}"; kind = 'township'; layer = 'towns'
        whole_area = sum(TA[TI[p['geoid']]] for p in parts)
    f = prim['geoid'][:2]
    e = add(entity_id=eid, vintage='2024', level='local', kind=kind, type=descr(prim), state_fips=f, state=FIPS[f][1],
            name=lname(prim), unit_layer=layer, geoid=prim['geoid'], source=S_GEOJSON, license=PD)
    if pl: e['label'] = 'incorporated' if pl['incorporated'] else 'unincorporated'
    e['_gstat'] = prim['funcstat']
    alts = []
    xs = [('place' if pl else 'cousub', prim['geoid'], 'primary', '', 1.0, 1.0, S_GEOJSON)]
    # cousub parts
    for p in parts:
        if p is prim: continue
        a_c = TA[TI[p['geoid']]]
        if pl: ar = PX[pl['geoid']].get(p['geoid'], 0.0)
        else: ar = a_c   # parts of one cousub-only government (same FIPS code) are disjoint pieces of it
        s_g = ar / a_c if a_c else 0; s_w = ar / whole_area if whole_area else 0
        rl = rel(s_g, s_w)
        det = {'equal': 'coextensive', 'split': 'place_split' if pl else 'cousub_part_in_other_county', 'contained': 'place_in_cousub', 'partial': 'partial_overlap'}[rl]
        if rl == 'partial' and pl and p['geoid'][5:] == pl['geoid'][2:] and s_g < 0.5 and s_w < 0.5:
            rl, det = 'split', 'place_split_sliver_overlap_unmeasured'   # same FIPS code; sliver lost in the simplified geometry
        if g.get('pair_src') and any(p['geoid'] in (t['geoid_a'], t['geoid_b']) for t in g['pair_src']): det = 'consolidated_town_city'; src(e, 'data-v3/geo/town_pairs.csv (class same)')
        xs.append(('cousub', p['geoid'], rl, det, s_g, s_w, S_GEOJSON)); alts.append('cousub:' + p['geoid'])
        if lname(p) != e['name']: e['_alias'].add(lname(p))
        if rl == 'partial': flag(e, 'xwalk_partial_overlap:' + p['geoid'])
    for mp in g['merged_place']:
        ar = 0.0
        a_m = PA[PI[mp['geoid']]]
        if pl:
            # share via cousub tiling is not available place-to-place; both are coextensive with the shared town (town_pairs >= 0.9)
            pass
        xs.append(('place', mp['geoid'], 'equal', 'consolidated_town_city', '', '', 'data-v3/geo/town_pairs.csv (class same, mutual overlap >= 0.9)'))
        alts.append('place:' + mp['geoid']); e['_alias'].add(lname(mp))
    for cgeo in g['counties']:
        a_c = CTY_AREA[cgeo]
        if pl: ar = place_cty(pl['geoid']).get(cgeo, 0.0)
        else: ar = sum(TA[TI[p['geoid']]] for p in parts if p['geoid'][:5] == cgeo)
        s_g = ar / a_c if a_c else 0; s_w = ar / whole_area if whole_area else 0
        rl = rel(s_g, s_w)
        det = 'independent_city_county_equivalent' if FS[cgeo]['tiger_funcstat'] == 'F' else 'consolidated_city_county'
        xs.append(('county', cgeo, rl, det, s_g, s_w, S_CG + '; ' + S_GEOJSON)); alts.append('county:' + cgeo)
        if rl == 'contained': flag(e, f'consolidated_government_covers_county:{cgeo}(primary_place_is_smaller;CoG_lists_the_place_code)')
        e['_alias'].add(GZC24[cgeo]['NAME']); src(e, S_CG)
        e['cog_pid6'] = CG24[cgeo]['cog_pid6']
    e['geoid_alt'] = ';'.join(alts)
    # CoG 2022 government status (by FIPS code, never by name)
    codes = sorted(cogcodes(g))
    pids = sorted({COG_BY_CODE[c][0]['CENSUS_ID_PID6'] for c in codes})
    if pids:
        e['gov_status'] = 'government'; src(e, S_COG)
        if not e['cog_pid6']: e['cog_pid6'] = ';'.join(pids)
        if len(pids) > 1: flag(e, 'multiple_cog_units:' + ';'.join(pids))
        for c in codes:
            if COG_BY_CODE[c][0]['IS_ACTIVE'] != 'Y': flag(e, 'cog2022_is_active_N')
    else:
        fs = prim['funcstat']
        if fs == 'G':
            e['gov_status'] = 'dependent'; flag(e, 'tiger_funcstat_G:active_government_subordinate_to_another_unit;not_in_cog2022')
        elif fs in 'ABC': flag(e, f'gov_status_unknown:tiger_funcstat_{fs}_no_cog2022_code_match')
        else: e['gov_status'] = 'area_only'; flag(e, f'tiger_funcstat_{fs}:' + FUNC[fs].replace(' ', '_'))
    if prim['funcstat'] in 'IN' and pids: flag(e, f"tiger_funcstat_{prim['funcstat']}_but_in_cog2022")
    # parent: the one county holding >= 98 % of the entity, else the state
    if g['counties']:
        e['parent_entity_id'] = f'state:{f}'
    else:
        if pl: o = place_cty(pl['geoid']); tot = whole_area
        else:
            o = C.Counter(); tot = whole_area
            for p in parts: o[p['geoid'][:5]] += TA[TI[p['geoid']]]
        cc = [(c, a / tot) for c, a in o.most_common() if tot and a / tot >= 0.01]
        if cc and cc[0][1] >= 0.98:
            pc = cc[0][0]; e['parent_entity_id'] = f'county:{pc}' if pc not in cty_merged else 'muni:place:' + cty_merged[pc] if len(cty_merged[pc]) == 7 else f'state:{f}'
        else:
            e['parent_entity_id'] = f'state:{f}'
            if cc: flag(e, 'spans_counties:' + ';'.join(c for c, s in cc))
            else: flag(e, 'county_share_unmeasured')
    for x in xs:
        XW.append({'entity_id': eid, 'geoid_layer': x[0], 'geoid': x[1], 'relation': x[2], 'relation_detail': x[3],
                   'share_of_geoid_in_entity': x[4] if x[4] == '' else f'{x[4]:.4f}', 'share_of_entity_in_geoid': x[5] if x[5] == '' else f'{x[5]:.4f}',
                   'vintage': '2024', 'source': x[6]})
        idx({'place': 'place', 'cousub': 'cousub', 'county': 'county'}[x[0]], x[1], '2024', eid)
for ka, kb, t in pairs_separate_gov:
    for a, b in ((ka, kb), (kb, ka)):
        ea = [e for (eid, v), e in ENT.items() if v == '2024' and e.get('_gstat') is not None and (eid.endswith(':' + (GROUP[a]['place'] or GROUP[a]['cousubs'][0])['geoid']))]
        for e in ea:
            ob = GROUP[b]['place'] or GROUP[b]['cousubs'][0]
            flag(e, 'coextensive_separate_government:' + ('muni:place:' if GROUP[b]['place'] else 'town:cousub:') + ob['geoid'])

# DC: one government = state:11 + county 11001 + place 1150000 (+ cousub). Fold the muni entity into state:11.
dcm = ENT.pop(('muni:place:1150000', '2024'))
dc = ENT[('state:11', '2024')]
dc['geoid_alt'] = ';'.join(['place:1150000'] + ([dcm['geoid_alt']] if dcm['geoid_alt'] else []))
dc['cog_pid6'] = dcm['cog_pid6']; dc['_alias'] |= dcm['_alias'] | {dcm['name']}
src(dc, S_GEOJSON); src(dc, S_CG)
for x in XW:
    if x['entity_id'] == 'muni:place:1150000':
        x['entity_id'] = 'state:11'
        if x['relation'] == 'primary': x['relation'] = 'equal'; x['relation_detail'] = 'federal_district_city'; x['share_of_geoid_in_entity'] = '1.0000'; x['share_of_entity_in_geoid'] = '1.0000'
for k, v in list(GIDX.items()):
    if v == 'muni:place:1150000': GIDX[k] = 'state:11'
for e in ENT.values():
    if e['parent_entity_id'] == 'muni:place:1150000': e['parent_entity_id'] = 'state:11'
XW.insert(0, {'entity_id': 'state:11', 'geoid_layer': 'state', 'geoid': '11', 'relation': 'primary', 'relation_detail': '',
              'share_of_geoid_in_entity': '1.0000', 'share_of_entity_in_geoid': '1.0000', 'vintage': '2024', 'source': S_ST})

# ---------------- school districts ----------------
SCH = {'unsd': ('school_unified', 'unified'), 'elsd': ('school_elementary', 'elementary'), 'scsd': ('school_secondary', 'secondary')}
for ss, (kind, typ) in SCH.items():
    fn = f'2024_Gaz_{ss}_national.txt'
    for r in gaz(os.path.join(A.gaz24, fn)):
        g = r['GEOID']; f = g[:2]
        if f not in FIPS: continue
        if g.endswith('99999') or 'not defined' in r['NAME'].lower():
            GAPS.append({'gap': 'excluded_not_defined', 'key': f'{ss}:{g}', 'detail': r['NAME']}); continue
        e = add(entity_id=f'school:{g}', vintage='2024', level='local', kind=kind, type=typ + (f" (grades {r['LOGRADE']}-{r['HIGRADE']})" if r.get('LOGRADE') else ''),
                state_fips=f, state=FIPS[f][1], name=r['NAME'], unit_layer='schools', geoid=g, parent_entity_id=f'state:{f}',
                source=gazsrc(2024, fn), license=PD)
        flag(e, 'gov_status_unknown:cog2022_school_lists_carry_no_nces_or_tiger_code')
        idx(ss, g, '2024', e['entity_id'])
        XW.append({'entity_id': e['entity_id'], 'geoid_layer': ss, 'geoid': g, 'relation': 'primary', 'relation_detail': '',
                   'share_of_geoid_in_entity': '1.0000', 'share_of_entity_in_geoid': '1.0000', 'vintage': '2024', 'source': gazsrc(2024, fn)})

# ---------------- legislatures ----------------
geo_names = {}
for fn, gcol, ncol, vint in [('ushouse.csv', 'geoid', 'tiger_name', '2024'), ('senate.csv', 'geoid', 'tiger_name', '2024'), ('statehouse.csv', 'geoid', 'tiger_name', '2024'),
                             ('ushouse_2020.csv', 'geoid_2020', 'tiger_name_2020', '2020'), ('senate_2020.csv', 'geoid_2020', 'tiger_name_2020', '2020'),
                             ('statehouse_2020.csv', 'geoid_2020', 'tiger_name_2020', '2020')]:
    for r in rcsv(os.path.join(GEO, fn)):
        if r[gcol] and r[ncol]: geo_names[(fn.split('_')[0].replace('.csv', ''), r[gcol], vint)] = r[ncol]
add(entity_id='us-house', level='federal', kind='chamber', type='lower_chamber', name='United States House of Representatives',
    parent_entity_id='nation:us', officeholder_entity_id='us-house', source='U.S. Constitution art. I', license=PD)
flag(ENT[('us-house', '')], 'gov_status_na:legislative_chamber')
for vint, uv, fn, yr in [('2024', 'cd119', '2024_Gaz_119CDs_national.txt', 2024), ('2020', 'cd116', '2020_Gaz_116CDs_national.txt', 2020)]:
    for r in gaz(os.path.join(A.gaz24 if yr == 2024 else A.gaz20, fn)):
        g = r['GEOID']; f = g[:2]
        if g.endswith('ZZ'): GAPS.append({'gap': 'excluded_not_defined', 'key': f'cd:{g}:{vint}', 'detail': 'Congressional Districts not defined (water)'}); continue
        if f not in FIPS: continue
        cd = g[2:]
        typ = 'delegate_district' if cd == '98' else ('at_large_district' if cd == '00' else 'congressional_district')
        nm = geo_names.get(('ushouse', g, vint), '')
        e = add(entity_id=f'seat:us-house:{g}', vintage=vint, level='federal', kind='district_seat', type=typ, state_fips=f, state=FIPS[f][1],
                name=nm, unit_layer='ushouse', geoid=g, parent_entity_id='us-house', officeholder_entity_id='us-house',
                officeholder_unit_vintage=uv, officeholder_unit_key=g, source=gazsrc(yr, fn) + ('; data-v3/geo/ushouse%s.csv (NAMELSAD)' % ('' if vint == '2024' else '_2020') if nm else ''), license=PD)
        if not nm: flag(e, 'name_missing:gazetteer_has_no_name')
        flag(e, 'gov_status_na:district_seat')
        idx('cd', g, vint, e['entity_id'])
        XW.append({'entity_id': e['entity_id'], 'geoid_layer': 'cd', 'geoid': g, 'relation': 'primary', 'relation_detail': '', 'share_of_geoid_in_entity': '1.0000',
                   'share_of_entity_in_geoid': '1.0000', 'vintage': vint, 'source': gazsrc(yr, fn)})
# territory delegates / resident commissioner: keyed on the House Clerk code the officeholder files use
gz119 = {r['GEOID'] for r in gaz(os.path.join(A.gaz24, '2024_Gaz_119CDs_national.txt'))}
gz116 = {r['GEOID'] for r in gaz(os.path.join(A.gaz20, '2020_Gaz_116CDs_national.txt'))}
for f, ab, nm, code in TERR:
    for vint, uv, gz in [('2024', 'cd119', gz119), ('2020', 'cd116', gz116)]:
        g = f + '98' if f + '98' in gz else ''
        e = add(entity_id=f'seat:us-house:{code}', vintage=vint, level='federal', kind='district_seat',
                type='resident_commissioner' if f == '72' else 'delegate_district', state_fips=f, state=nm, name='',
                unit_layer='ushouse' if g else '', geoid=g, parent_entity_id='us-house', officeholder_entity_id='us-house',
                officeholder_unit_vintage=uv, officeholder_unit_key=code, source=S_OH + ' (statedistrict, House Clerk code)' + ('; ' + gazsrc(int(vint), 'CDs national') if g else ''), license=PD)
        flag(e, 'outside_v2_scope:territory'); flag(e, 'gov_status_na:district_seat'); flag(e, 'name_missing')
        if not g: flag(e, 'no_geoid_in_gazetteer')
        else:
            idx('cd', g, vint, e['entity_id'])
            XW.append({'entity_id': e['entity_id'], 'geoid_layer': 'cd', 'geoid': g, 'relation': 'primary', 'relation_detail': '', 'share_of_geoid_in_entity': '1.0000',
                       'share_of_entity_in_geoid': '1.0000', 'vintage': vint, 'source': 'U.S. Census Bureau Gazetteer'})

OHC = list(csv.DictReader(io.StringIO(git_show('data-v3/inst/officeholders_stateleg_current.csv'))))
OH24 = list(csv.DictReader(io.StringIO(git_show('data-v3/inst/officeholders_stateleg_2024.csv'))))
oh_ids = {}; oh_alias = C.defaultdict(set)
def chn(r): return 'upper' if r['chamber'] == 'legislature' else r['chamber']   # NE unicameral = TIGER SLDU
for r in OH24 + OHC:   # current file wins; other ids recorded as aliases
    oh_ids[(BYNAME[r['state']], chn(r))] = r['entity_id']
for r in OHC + OH24:
    k = (BYNAME[r['state']], chn(r))
    if r['entity_id'] != oh_ids[k]: oh_alias[oh_ids[k]].add(r['entity_id'])
for f, ab, nm in ST:
    if f == '11':
        add(entity_id='chamber:dc-council', level='state', kind='dc_council', type='council', state_fips=f, state=nm,
            name='Council of the District of Columbia', parent_entity_id='state:11', source='District of Columbia Home Rule Act; v2/data/dc.js (wards stand in for state senate and house)', license=PD)
        flag(ENT[('chamber:dc-council', '')], 'gov_status_na:legislative_body_of_state:11'); continue
    for ch in (['upper'] if f == '31' else ['upper', 'lower']):
        oid = oh_ids.get((f, ch), '')
        e = add(entity_id=f'chamber:{ab.lower()}-{ch}', level='state', kind='chamber', type='unicameral' if f == '31' else f'{ch}_chamber',
                state_fips=f, state=nm, name=f'{nm} Legislature' + ('' if f == '31' else f' ({ch} chamber)'), parent_entity_id=f'state:{f}',
                officeholder_entity_id=oid, source=gazsrc(2024, f'2024_Gaz_sld{ch[0]}_national.txt') + '; ' + S_OH, license=PD)
        flag(e, 'gov_status_na:legislative_chamber')
        for al in sorted(oh_alias.get(oid, ())): flag(e, 'officeholder_entity_id_alias:' + al)
        if f != '31': flag(e, 'chamber_name_generic')
        if not oid: flag(e, 'officeholder_entity_id_missing')
for vint, yr, gzd in [('2024', 2024, A.gaz24), ('2020', 2020, A.gaz20)]:
    plan = '2024' if vint == '2024' else '2018'
    for ss, ch, layer in [('sldu', 'upper', 'senate'), ('sldl', 'lower', 'statehouse')]:
        fn = f'{yr}_Gaz_{ss}_national.txt'
        for r in gaz(os.path.join(gzd, fn)):
            g = r['GEOID']; f = g[:2]
            if f not in FIPS: continue
            if 'ZZZ' in g or 'not defined' in r['NAME'].lower():
                GAPS.append({'gap': 'excluded_not_defined', 'key': f'{ss}:{g}:{vint}', 'detail': r['NAME']}); continue
            ab = FIPS[f][0]
            if f == '11':
                eid = f'seat:dc-council:{g}'; par = 'chamber:dc-council'; typ = 'dc_ward'; oid = ''; uv = ''
            else:
                eid = f'seat:{ab.lower()}-{ch}:{g}'; par = f'chamber:{ab.lower()}-{ch}'; oid = oh_ids.get((f, ch), '')
                typ = 'legislative_district' if f == '31' else f'state_{"senate" if ch == "upper" else "house"}_district'; uv = f'{ss}{plan}'
            e = add(entity_id=eid, vintage=vint, level='state', kind='district_seat', type=typ, state_fips=f, state=FIPS[f][1], name=r['NAME'],
                    unit_layer=layer, geoid=g, parent_entity_id=par, officeholder_entity_id=oid, officeholder_unit_vintage=uv,
                    officeholder_unit_key=g if oid else '', source=gazsrc(yr, fn) + f' ({plan} plan)', license=PD)
            flag(e, 'gov_status_na:district_seat')
            idx(ss, g, vint, eid)
            XW.append({'entity_id': eid, 'geoid_layer': ss, 'geoid': g, 'relation': 'primary', 'relation_detail': '', 'share_of_geoid_in_entity': '1.0000',
                       'share_of_entity_in_geoid': '1.0000', 'vintage': vint, 'source': gazsrc(yr, fn)})
# seats without TIGER geography that the officeholder files carry (NH floterials, ME tribal representatives)
def slug(s): return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
for r in OHC + OH24:
    if r['unit_geoid']: continue
    f = BYNAME[r['state']]; ab = FIPS[f][0]; ch = r['chamber']
    typ = 'floterial_district' if 'floterial' in r['join_status'] else ('tribal_representative' if 'tribal' in r['join_status'] else 'district_no_geoid')
    eid = f"seat:{ab.lower()}-{ch}:{typ.split('_')[0]}:{slug(r['district'])}"
    if (eid, '2024') in ENT: continue
    e = add(entity_id=eid, vintage='2024', level='state', kind='district_seat', type=typ, state_fips=f, state=FIPS[f][1], name=r['district'],
            parent_entity_id=f'chamber:{ab.lower()}-{ch}', officeholder_entity_id=r['entity_id'], officeholder_unit_vintage=r['unit_vintage'],
            officeholder_unit_key=r['district'], source=S_OH + ' (district); ' + r['source'].split(',')[0], license=r['license'] if r['license'] else '')
    flag(e, 'no_tiger_geoid'); flag(e, 'gov_status_na:district_seat')

# ---------------- v2 / v1 row back-links + validation ----------------
V2 = []   # rows of entity_v2_rows.csv
def resolve(layer, geoid, vint):
    return GIDX.get((layer, geoid, vint), '')
def v2add(v2_layer, state, row, v2_name, glayer, geoid, vint, note=''):
    eid = resolve(glayer, geoid, vint) if geoid else ''
    V2.append({'v2_layer': v2_layer, 'state': state, 'v2_row': row, 'v2_name': v2_name, 'geoid_layer': glayer, 'geoid': geoid,
               'vintage': vint, 'entity_id': eid, 'resolved': 'yes' if eid else 'no', 'note': note})
    if eid:
        e = ENT.get((eid, vint)) or ENT.get((eid, '2024'))
        e['_v2'].append((v2_layer, row))
        if v2_layer.startswith('v2:') and '@2020' not in v2_layer:
            k_ = f'{state}|{row}' if v2_layer in ('v2:parts', 'v2:towns(IA townships)') else f'{state}|{v2_name}'
            e.setdefault('_v2key', [])
            if k_ not in e['_v2key']: e['_v2key'].append(k_)
        if v2_name and v2_name != e['name'] and not v2_layer.startswith('v2:ushouse') and not v2_layer.startswith('v2:senate') and not v2_layer.startswith('v2:statehouse'):
            e['_alias'].add(v2_name)
for r in rcsv(os.path.join(GEO, 'counties.csv')): v2add('v2:counties', r['state'], r['row'], r['v2_name'], 'county', r['geoid'], '2024')
for r in rcsv(os.path.join(GEO, 'schools.csv')): v2add('v2:schools', r['state'], r['row'], r['v2_name'], r['tiger_set'], r['geoid'], '2024')
for fn, lay in [('senate.csv', 'v2:senate'), ('statehouse.csv', 'v2:statehouse')]:
    for r in rcsv(os.path.join(GEO, fn)): v2add(lay, r['state'], r['row'], r['v2_name'], r['tiger_set'], r['geoid'], '2024')
for r in rcsv(os.path.join(GEO, 'ushouse.csv')): v2add('v2:ushouse', r['state'], r['row'], r['v2_name'], 'cd', r['geoid'], '2024')
for fn, lay, ss in [('senate_2020.csv', 'v2:senate@2020', 'sldu'), ('statehouse_2020.csv', 'v2:statehouse@2020', 'sldl'), ('ushouse_2020.csv', 'v2:ushouse@2020', 'cd')]:
    for r in rcsv(os.path.join(GEO, fn)):
        s2 = 'sldu' if (ss == 'sldl' and r['state'] in ('Nebraska', 'District of Columbia')) else ss
        if r['geoid_2020']:
            v2add(lay, r['state'], r['row'], r['v2_name'], s2, r['geoid_2020'], '2020', 'unpaired_2020 (2020 district with no v2 row)' if r['match'] == 'unpaired_2020' else r['match'])
        else:
            v2add(lay, r['state'], r['row'], r['v2_name'], s2, '', '2020', 'no 2020 district paired in data-v3/geo')
# states
s = open(os.path.join(R, 'v2/data/usstates.js'), encoding='utf-8').read()
for i, nm in enumerate(re.findall(r'\["((?:[^"\\]|\\.)*)",\[\[', s)):
    v2add('v2:states', nm, str(i), nm, 'state', BYNAME.get(nm, ''), '2024')
# parts + places: enumerate the v2 files, link through the GeoJSON's v2_parts / v2_places
RX = re.compile(r'\["((?:[^"\\]|\\.)*)","((?:[^"\\]|\\.)*)",\[\[')
pk = {}; plk = {}
for p in TP:
    for k in p['v2_parts']: pk[(p['state'], k)] = ('cousub', p['geoid'])
for p in PP:
    for k in p['v2_parts']: pk.setdefault((p['state'], k), ('place', p['geoid']))
    if p['v2_places']: plk[(p['state'], p['v2_places'])] = p['geoid']
CTYBYNAME = {}
for p in TP: CTYBYNAME[(p['state'], p['county'])] = p['geoid'][:5]
TBYN = C.defaultdict(list); PBYN = C.defaultdict(list)
for p in TP: TBYN[(p['state'], p['county'], p['namelsad'])].append(p)
for p in PP: PBYN[(p['state'], p['namelsad'])].append(p['geoid'])
for L in ['parts', 'places']:
    d = os.path.join(R, 'v2/data', L)
    for fn in sorted(os.listdir(d)):
        stn = fn[:-3].replace('_', ' ').replace('-', ' ')
        s = open(os.path.join(d, fn), encoding='utf-8').read()
        for i, (a, b) in enumerate(RX.findall(s)):
            a = json.loads('"%s"' % a); b = json.loads('"%s"' % b)
            if L == 'parts':
                hit = pk.get((stn, f'{a}|{b}')); note = ''
                if not hit:
                    # geo's method: exact TIGER NAMELSAD inside that county (county subdivision first, then a place overlapping the county)
                    cf = CTYBYNAME.get((stn, a))
                    cands = [('cousub', p['geoid']) for p in TBYN.get((stn, a, b), [])]
                    if not cands and cf:
                        cands = [('place', g) for g in PBYN.get((stn, b), []) if any(c[:5] == cf for c in PX.get(g, {}))]
                    if len(cands) == 1: hit = cands[0]; note = 'resolved_by_exact_namelsad_in_county (GeoJSON v2_parts lists this place under another county)'
                    else:
                        alt = PBYN.get((stn, b), [])
                        note = f'no GEOID in data-v3/geo GeoJSON; {len(cands)} exact-NAMELSAD candidates overlapping this county in TIGER 2024'
                        if len(alt) == 1: note += f'; candidate (not linked): place {alt[0]} (same NAMELSAD in state, does not reach this county in TIGER 2024: likely a v2 simplification sliver)'
                v2add('v2:parts', stn, f'{a}|{b}', b, hit[0] if hit else '', hit[1] if hit else '', '2024', note)
            else:
                g = plk.get((stn, b))
                v2add('v2:places', stn, b, b, 'place' if g else '', g or '', '2024', '' if g else 'no GEOID in data-v3/geo GeoJSON')
for r in rcsv(os.path.join(GEO, 'towns.csv')):
    v2add('v2:towns(IA townships)', r['state'], f"{r['county']}|{r['v2_name']}", r['v2_name'], 'cousub', r['geoid'], '2024')
for r in v1t:
    v2add('v1:' + r['layer'], r['state'], r['row'] if r['layer'] == 'places' else f"{r['county']}|{r['row']}", r['v1_name'],
          'place' if r['tiger_kind'] == 'place' else 'cousub', r['geoid'], '2024')

# ---------------- officeholder validation: chamber entity + unit (layer, geoid, vintage) + seat ----------------
UNITS = {(k[0], k[1], k[2]) for k in GIDX if k[0] in ('cd', 'sldu', 'sldl')}
NOGEO = {}   # units without a TIGER GEOID that officeholder files key by district / House Clerk code
for e in ENT.values():
    if e['kind'] == 'district_seat' and e['officeholder_unit_key'] and (not e['geoid'] or not e['officeholder_unit_key'].isdigit()):
        NOGEO[(e['parent_entity_id'], e['officeholder_unit_key'])] = e['entity_id']
LEG = {'us-house': 'us-house'}
for e in ENT.values():
    if e['kind'] == 'chamber' and e['officeholder_entity_id']:
        LEG[e['officeholder_entity_id']] = e['entity_id']
        for fl in e['_flags']:
            if fl.startswith('officeholder_entity_id_alias:'): LEG[fl.split(':', 1)[1]] = e['entity_id']
YR = {'cd119': ('cd', '2024'), 'cd116': ('cd', '2020'), 'sldu2024': ('sldu', '2024'), 'sldl2024': ('sldl', '2024')}
OHV = []; oh_stats = {}
oh_files = ['officeholders_house_current', 'officeholders_house_2024', 'officeholders_house_2020', 'officeholders_stateleg_current', 'officeholders_stateleg_2024']
for fn in oh_files:
    rows_ = list(csv.DictReader(io.StringIO(git_show(f'data-v3/inst/{fn}.csv'))))
    st = C.Counter()
    for r in rows_:
        eid = r['entity_id'] if (r['entity_id'], '') in ENT else LEG.get(r['entity_id'], '')
        if r.get('unit_layer'): lay, yr = r['unit_layer'], r['unit_vintage']
        else: lay, yr = YR[r['unit_vintage']]
        if eid and r['unit_geoid'] and (lay, r['unit_geoid'], yr) in UNITS: st['resolved'] += 1; continue
        key = r.get('statedistrict') if fn.startswith('officeholders_house') else r.get('district')
        if eid and not r['unit_geoid'] and (eid, key) in NOGEO:
            st['resolved_chamber_unit_without_tiger_geoid'] += 1; continue
        st['orphan'] += 1
        OHV.append({'file': fn, 'entity_id': r['entity_id'], 'unit': f"{lay}:{r['unit_geoid']}:{yr}", 'name': r['name']})
    oh_stats[fn] = dict(st, rows=len(rows_))

# ---------------- CT: 8 counties (TIGER <= 2021) -> 9 planning regions (TIGER 2022+), linked through shared town FIPS codes ----------------
g20 = gaz(os.path.join(A.gaz20, '2020_Gaz_cousubs_national.txt')); g24 = gaz(os.path.join(A.gaz24, '2024_Gaz_cousubs_national.txt'))
code24 = {r['GEOID'][5:]: r['GEOID'][:5] for r in g24 if r['GEOID'][:2] == '09'}
ct = C.defaultdict(set)
for r in g20:
    if r['GEOID'][:2] == '09' and r['GEOID'][5:] in code24: ct[r['GEOID'][:5]].add(code24[r['GEOID'][5:]])
def ent_of_county(c):
    return GIDX.get(('county', c, '2024'))
for old, news in ct.items():
    eo = ENT[(f'county:{old}', '2020')]
    succ = sorted({ent_of_county(n) for n in news})
    eo['successor_id'] = ';'.join(succ); eo['_flags'].append('valid_to_not_recorded:last_tiger_vintage_here_2020;replaced_by_planning_regions_in_tiger_2022')
    for n in succ:
        en = ENT[(n, '2024')]
        en['predecessor_id'] = ';'.join(sorted(set([x for x in en.get('predecessor_id', '').split(';') if x] + [eo['entity_id']])))
    src(eo, gazsrc(2020, '2020_Gaz_cousubs_national.txt') + ' + ' + gazsrc(2024, '2024_Gaz_cousubs_national.txt') + ' (town FIPS codes)')

# ---------------- finalize: one row per entity (no vintage); seats are units, not entities ----------------
URL = [(r'2024 TIGER/Line Gazetteer \((\S+)\.txt', lambda m: f'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/{m.group(1)}.zip'),
       (r'2020 TIGER/Line Gazetteer \((\S+)\.txt', lambda m: f'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/{m.group(1)}.zip'),
       (r'^ANSI/FIPS state codes', lambda m: 'https://www.census.gov/library/reference/code-lists/ansi.html'),
       (r'TIGER/Line 2024 county subdivisions \+ places', lambda m: 'https://www2.census.gov/geo/tiger/TIGER2024/COUSUB/ ; https://www2.census.gov/geo/tiger/TIGER2024/PLACE/'),
       (r'2022 Census of Governments', lambda m: 'https://www2.census.gov/programs-surveys/gus/datasets/2022/govt_units_2022.ZIP'),
       (r'county_government\.csv', lambda m: 'https://www2.census.gov/programs-surveys/gus/datasets/2022/govt_units_2022.ZIP'),
       (r'town_pairs\.csv', lambda m: 'https://www2.census.gov/geo/tiger/TIGER2024/COUSUB/ ; https://www2.census.gov/geo/tiger/TIGER2024/PLACE/'),
       (r'^U\.S\. Constitution', lambda m: 'https://www.archives.gov/founding-docs/constitution-transcript'),
       (r'Home Rule Act', lambda m: 'https://code.dccouncil.gov/us/dc/council/code/titles/1/chapters/2'),
       (r'officeholder files', lambda m: '')]
def urls_for(srcs):
    out = []
    for s_ in srcs:
        for pat, fn in URL:
            m = re.search(pat, s_)
            if m:
                for u in fn(m).split(' ; '):
                    if u and u not in out: out.append(u)
                break
    return ' ; '.join(out)
RETRIEVED = '2026-10-18'
def esc(x): return x.replace(';', '\\;')
SEATS = [e for e in ENT.values() if e['kind'] == 'district_seat']
OUTROWS = []
for (eid, vint), e in ENT.items():
    if e['kind'] == 'district_seat': continue
    e['parent_id'] = e['parent_entity_id']
    e['alias'] = ';'.join(sorted(esc(a) for a in e['_alias'] if a and a != e['name']))
    if e['kind'] == 'state': e['label'] = 'sovereign'
    elif e['kind'] in ('county', 'township') and e['gov_status'] == 'government' and not e['label']: e['label'] = 'incorporated'
    e['flags'] = ';'.join(e['_flags']); e['source'] = '; '.join(e['_src'])
    e['source_url'] = urls_for(e['_src']); e['retrieved_at'] = RETRIEVED
    if not e['source_url']: e['flags'] = ';'.join([x for x in [e['flags'], 'source_url_missing'] if x])
    lays = []
    for l, _ in e['_v2']:
        if l not in lays: lays.append(l)
    e['v2_layer'] = ';'.join(lays)
    e['v2_row'] = ';'.join(esc(f'{l}#{r}') for l, r in e['_v2'])
    e['v2_key'] = ';'.join(esc(k) for k in e.get('_v2key', []))
    e['feed'] = 'inst-lane' if e['kind'] in ('nation', 'chamber', 'dc_council') else 'tiger/cog'
    e.setdefault('predecessor_id', ''); e.setdefault('successor_id', '')
    OUTROWS.append(e)
ids = [e['entity_id'] for e in OUTROWS]; assert len(ids) == len(set(ids)), 'entity_id not unique'
COLS2 = ['entity_id', 'kind', 'state_fips', 'state', 'name', 'alias', 'label', 'gov_status', 'parent_id', 'valid_from', 'valid_to',
         'predecessor_id', 'successor_id', 'v2_layer', 'v2_row', 'v2_key', 'source', 'source_url', 'retrieved_at', 'license',
         'feed', 'level', 'type', 'cog_pid6', 'flags']
ORDER = ['nation', 'state', 'territory', 'chamber', 'dc_council', 'county', 'municipality', 'township', 'school_unified', 'school_elementary', 'school_secondary']
rows = sorted(OUTROWS, key=lambda e: (ORDER.index(e['kind']), e['state_fips'], e['entity_id']))
for e in rows:
    assert e['parent_id'] == '' or e['parent_id'] in set(ids), (e['entity_id'], e['parent_id'])
with open(os.path.join(OUT, 'entities.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, COLS2, extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(rows)
# xwalk: entity x unit_layer x vintage (district-seat units are not entities -> not in the xwalk)
RELMAP = {('primary', ''): 'primary'}
def relname(x):
    if x['relation'] == 'primary': return 'primary'
    d = x['relation_detail']
    if d in ('consolidated_city_county', 'independent_city_county_equivalent', 'consolidated_town_city', 'federal_district_city'): return d
    if x['geoid_layer'] == 'cousub': return 'coextensive' if x['relation'] == 'equal' else 'also_cousub'
    if x['geoid_layer'] == 'place': return 'coextensive' if x['relation'] == 'equal' else 'also_place'
    return x['relation']
XW2 = []
for x in XW:
    if x['geoid_layer'] in ('cd', 'sldu', 'sldl'): continue
    srcs = [y for y in x['source'].split('; ') if y]
    XW2.append({'entity_id': x['entity_id'], 'unit_layer': x['geoid_layer'], 'geoid': x['geoid'], 'vintage': x['vintage'], 'relation': relname(x),
                'source': x['source'], 'source_url': urls_for(srcs), 'retrieved_at': RETRIEVED,
                'overlap': 'equal' if x['relation'] == 'primary' else x['relation'], 'share_of_geoid_in_entity': x['share_of_geoid_in_entity'],
                'share_of_entity_in_geoid': x['share_of_entity_in_geoid']})
XC2 = ['entity_id', 'unit_layer', 'geoid', 'vintage', 'relation', 'source', 'source_url', 'retrieved_at', 'overlap', 'share_of_geoid_in_entity', 'share_of_entity_in_geoid']
xk = [(x['entity_id'], x['unit_layer'], x['geoid'], x['vintage']) for x in XW2]; assert len(xk) == len(set(xk))
assert {x['entity_id'] for x in XW2} <= set(ids)
with open(os.path.join(OUT, 'entity_geoid_xwalk.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, XC2, lineterminator='\n'); w.writeheader(); w.writerows(sorted(XW2, key=lambda x: (x['entity_id'], x['vintage'], x['relation'] != 'primary', x['unit_layer'], x['geoid'])))
# v2 back-link table: district rows resolve to chamber entity + unit
SEATPAR = {e['entity_id']: e['parent_entity_id'] for e in SEATS}
VC = ['v2_layer', 'state', 'v2_row', 'v2_name', 'unit_layer', 'geoid', 'vintage', 'entity_id', 'resolved', 'note']
V2OUT = []
for v in V2:
    o = dict(v); o['unit_layer'] = o.pop('geoid_layer')
    if o['entity_id'] in SEATPAR: o['entity_id'] = SEATPAR[o['entity_id']]; o['note'] = ('district unit of the chamber; ' + o['note']).rstrip('; ')
    V2OUT.append(o)
with open(os.path.join(OUT, 'entity_v2_rows.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, VC, lineterminator='\n'); w.writeheader(); w.writerows(V2OUT)
for v in V2OUT:
    if v['resolved'] == 'no': GAPS.append({'gap': 'orphan_v2_row', 'key': f"{v['v2_layer']}|{v['state']}|{v['v2_row']}", 'detail': v['note'] or f"{v['unit_layer']}:{v['geoid']} not in registry"})
for o in OHV: GAPS.append({'gap': 'orphan_officeholder_unit', 'key': f"{o['file']}|{o['entity_id']}|{o['unit']}", 'detail': o['name']})
for e in SEATS:
    if not e['geoid']: GAPS.append({'gap': 'officeholder_unit_without_tiger_geoid', 'key': f"{e['parent_entity_id']}|{e['officeholder_unit_key']}", 'detail': e['type']})
linked = set()
for e in rows:
    for p_ in e['cog_pid6'].split(';'):
        if p_: linked.add(p_)
for c in COG:
    if c['CENSUS_ID_PID6'] not in linked and c['UNIT_TYPE'][0] in '23':
        GAPS.append({'gap': 'cog2022_unit_not_linked_by_code', 'key': c['CENSUS_ID_PID6'], 'detail': f"{c['UNIT_NAME']} ({c['UNIT_TYPE']}) FIPS {c['FIPS_STATE']}-{c['FIPS_COUNTY']}-{c['FIPS_PLACE']}"})
for e in rows:
    for fl in e['_flags']:
        if fl.startswith('gov_status_unknown:tiger') or fl.startswith('gov_status_unknown:consolidated'):
            GAPS.append({'gap': 'gov_status_unknown', 'key': e['entity_id'], 'detail': fl})
with open(os.path.join(OUT, 'entity_gaps.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, ['gap', 'key', 'detail'], lineterminator='\n'); w.writeheader(); w.writerows(GAPS)
summ = {
  'built_from': {'repo_head': subprocess.run(['git', '-C', R, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip(),
                 'officeholder_ref': f'{A.oh_ref} {OH_SHA}',
                 'gazetteer_2024': {f: sha(os.path.join(A.gaz24, f)) for f in sorted(os.listdir(A.gaz24)) if f.endswith('.txt')},
                 'gazetteer_2020': {f: sha(os.path.join(A.gaz20, f)) for f in sorted(os.listdir(A.gaz20)) if f.endswith('.txt')},
                 'cog2022': sha(A.cog),
                 'geojson': {f: sha(os.path.join(A.geojson, f)) for f in ['towns_2024.geojson.gz', 'places_2024.geojson.gz']}},
  'entities': len(rows),
  'by_kind': dict(C.Counter(e['kind'] for e in rows)),
  'by_kind_gov_status': {f'{k}|{v}': n for (k, v), n in sorted(C.Counter((e['kind'], e['gov_status']) for e in rows).items())},
  'xwalk_rows': len(XW2),
  'xwalk_by_layer_vintage': {f'{a}|{b}': n for (a, b), n in sorted(C.Counter((x['unit_layer'], x['vintage']) for x in XW2).items())},
  'xwalk_by_relation': dict(C.Counter(x['relation'] for x in XW2)),
  'xwalk_by_overlap': dict(C.Counter(x['overlap'] for x in XW2 if x['relation'] != 'primary')),
  'multi_geoid_entities': len({x['entity_id'] for x in XW2 if x['relation'] != 'primary'}),
  'district_units_checked': dict(C.Counter(f"{k[0]}|{k[2]}" for k in UNITS)),
  'town_pairs_same_merged': len(pairs_merged), 'town_pairs_same_two_cog_governments': len(pairs_separate_gov),
  'counties_merged_into_city': len(cty_merged),
  'v2_rows': {l: dict(C.Counter(v['resolved'] for v in V2OUT if v['v2_layer'] == l)) for l in sorted({v['v2_layer'] for v in V2OUT})},
  'officeholders': oh_stats,
  'gaps': dict(C.Counter(g['gap'] for g in GAPS)),
}
json.dump(summ, open(os.path.join(OUT, 'entities_summary.json'), 'w'), indent=1)
print(json.dumps(summ, indent=1))
