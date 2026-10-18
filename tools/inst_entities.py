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
ap.add_argument('--oh-ref', required=True); ap.add_argument('--out'); ap.add_argument('--stability-test', action='store_true')
ap.add_argument('--gov-ref', required=True, help='Governments bot commit (data-v3/institutions/governments, read only)')
ap.add_argument('--foreign-ref', required=True, help='Governments bot commit for data-v3/institutions/governments/foreign/ + its images.csv foreign rows (read only)')
ap.add_argument('--seating-ref', required=True, help='Seating Charts bot commit (data-v3/seating/bodies.csv, build_meta.json, city_bodies.csv; read with git show)')
ap.add_argument('--commons-cache', required=True, help='dir written by tools/inst_commons.py fetch (Commons imageinfo/extmetadata answers + SHA256SUMS); read only')
ap.add_argument('--world-raw', required=True, help='dir written by tools/inst_world.py fetch (Wikidata answers); Natural Earth lists read from origin/main')
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
            e['gov_status'] = 'dependent'; flag(e, 'tiger_funcstat_G:active_government_subordinate_to_another_unit'); flag(e, 'not_in_cog2022')
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

# school gov_status from the Governments bot: its nces_leaid = the TIGER school GEOID (NCES LEA ID); read only
GOV_SHA = subprocess.run(['git', '-C', R, 'rev-parse', A.gov_ref], capture_output=True, text=True, check=True).stdout.strip()
S_GOV = f'Governments bot local/<ST>.csv (gov_status, nces_leaid; CoG 2022 + F-33 NCESID) at {GOV_SHA}'
GP = 'data-v3/institutions/governments/local/'
BOTSCH = C.defaultdict(list)
for f_ in subprocess.run(['git', '-C', R, 'ls-tree', '--name-only', GOV_SHA, GP], capture_output=True, text=True, check=True).stdout.split():
    for r in csv.DictReader(io.StringIO(subprocess.run(['git', '-C', R, 'show', f'{GOV_SHA}:{f_}'], capture_output=True, check=True).stdout.decode('utf-8'))):
        if r['type'] == 'school_district' and r.get('nces_leaid'): BOTSCH[r['nces_leaid']].append(r)
GSM = {'independent': 'government', 'dependent': 'dependent'}
SCHFILL = C.Counter(); SCHCONF = []
for (eid, vint), e in ENT.items():
    if not eid.startswith('school:'): continue
    b = BOTSCH.get(e['geoid'], [])
    st = sorted({GSM.get(x['gov_status'], '?' + x['gov_status']) for x in b})
    if not b: SCHFILL['no_bot_row'] += 1; continue
    if len(st) > 1 or st[0].startswith('?'):
        SCHFILL['conflict'] += 1; SCHCONF.append((eid, ';'.join(x['entity_id'] + '=' + x['gov_status'] for x in b))); continue
    e['gov_status'] = st[0]; SCHFILL[st[0]] += 1
    e['_flags'] = [x for x in e['_flags'] if not x.startswith('gov_status_unknown:cog2022_school')]
    pids = sorted({x['cog_id'] for x in b})
    e['cog_pid6'] = ';'.join(pids)
    if len(b) > 1: flag(e, 'multiple_cog_units:' + ','.join(pids)); SCHFILL['filled_from_several_bot_rows_same_status'] += 1
    src(e, S_GOV)
for e in ENT.values():
    if e['entity_id'].startswith('school:') and not e['gov_status']:
        e['_flags'] = [x if not x.startswith('gov_status_unknown:cog2022_school') else 'gov_status_unknown:no_governments_bot_row_with_this_nces_leaid' for x in e['_flags']]
for eid, d in SCHCONF:
    GAPS.append({'gap': 'school_gov_status_conflict', 'key': eid, 'detail': d})
    e = ENT[(eid, '2024')]; e['_flags'] = [x for x in e['_flags'] if not x.startswith('gov_status_unknown')]; flag(e, 'gov_status_unknown:governments_bot_rows_disagree')
for e in ENT.values():
    if e['entity_id'].startswith('school:') and not e['gov_status']: GAPS.append({'gap': 'gov_status_unknown', 'key': e['entity_id'], 'detail': ';'.join(e['_flags'])})
ours_ = {e['geoid'] for e in ENT.values() if e['entity_id'].startswith('school:')}
SCHFILL['bot_leaids'] = len(BOTSCH); SCHFILL['bot_school_rows_with_leaid'] = sum(len(v) for v in BOTSCH.values())
SCHFILL['bot_leaids_not_a_tiger2024_school_entity'] = len(set(BOTSCH) - ours_)
print('school gov_status fill', dict(SCHFILL), file=sys.stderr)

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
add(entity_id='us-senate', level='federal', kind='chamber', type='upper_chamber', name='United States Senate',
    parent_entity_id='nation:us', source='U.S. Constitution art. I', license=PD)   # frozen id, mirrors us-house (Full Stack, Oct 18)
flag(ENT[('us-senate', '')], 'gov_status_na:legislative_chamber')
# Seating Charts bodies (pinned commit; tools/inst_bodies.py): courts are minted from bodies.csv, links written to body_entity.csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inst_bodies
SEAT = inst_bodies.load(R, A.seating_ref); SEAT_SHA = SEAT['commit']
S_BODIES = 'Seating Charts bot bodies.csv'; S_SEATMETA = 'Seating Charts bot build_meta.json'; S_CITYB = 'Seating Charts bot city_bodies.csv'
ABBR2F = {ab: f for f, ab, nm in ST}
for cid, ctyp, cst, cname, ckey in inst_bodies.courts(SEAT['bodies']):
    cf = ABBR2F[cst]
    e = add(entity_id=cid, level='state', kind='court', type=ctyp, state_fips=cf, state=FIPS[cf][1], name=cname,
            parent_entity_id=f'state:{cf}', source=S_BODIES, license=PD, source_record_id=ckey)
    flag(e, 'gov_status_na:judicial_body')
SEAT_GAPS = [{'gap': 'not_in_seating_charts', 'key': code, 'detail': f"Seating Charts build_meta.json {lst}: no body in bodies.csv; court not minted"}
             for code, lst in inst_bodies.not_in_seating(SEAT['meta'])]
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
            officeholder_unit_key=r['district'], source=S_OH + ' (district)', license='')
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
    eo['successor_id'] = ';'.join(succ); eo['_flags'] += ['valid_to_not_recorded:last_tiger_vintage_here_2020', 'replaced_by_planning_regions_in_tiger_2022']
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
    e['flags'] = ';'.join(f_.replace(';', ',') for f_ in e['_flags']); e['source'] = '; '.join(e['_src'])   # ';' separates flags; ',' inside one
    lays = []
    for l, _ in e['_v2']:
        if l not in lays: lays.append(l)
    e['v2_layer'] = ';'.join(lays)
    e['v2_row'] = ';'.join(esc(f'{l}#{r}') for l, r in e['_v2'])
    e['v2_key'] = ';'.join(esc(k) for k in e.get('_v2key', []))
    e['feed'] = 'inst-lane' if e['kind'] in ('nation', 'chamber', 'dc_council', 'court') else 'tiger/cog'
    e.setdefault('predecessor_id', ''); e.setdefault('successor_id', '')
    OUTROWS.append(e)
# ---------------- world: nations, foreign dependencies, Canadian provinces/territories (tools/inst_world.py) ----------------
# Natural Earth (v2/data/countries.js, canada.js on origin/main) is only the LIST; no geometry, no xwalk unit, no boundary_set.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inst_world
WORLD = inst_world.build(R, A.world_raw)
S_NE_C = 'Natural Earth 1:50m admin-0 country list via v2/data/countries.js'
S_NE_CA = 'Natural Earth 1:50m admin-1 Canada provinces/territories list via v2/data/canada.js'
S_WD = 'Wikidata SPARQL (tools/inst_world.py)'
WGAPS = []
for w in WORLD['rows']:
    if w['kind'] == 'territory' and not w['parent_id']:   # SCHEMA: a territory needs a nation parent; never guessed
        WGAPS.append({'gap': 'world_entity_excluded_no_sovereign', 'key': w['entity_id'],
                      'detail': f"{w['ne_name']} ({w['wikidata']}): not written to entities.csv until Wikidata/ISO names its sovereign"})
        continue
    lvl = 'national' if w['kind'] == 'nation' else 'subnational'
    typ = {'nation': 'sovereign_state', 'province': 'province', 'territory': 'territory' if w['entity_id'].startswith('territory:ca-') else 'dependency'}[w['kind']]
    e = {c: '' for c in COLS}
    e.update(entity_id=w['entity_id'], kind=w['kind'], name=w['ne_name'], parent_entity_id=w['parent_id'], parent_id=w['parent_id'],
             label='sovereign' if w['kind'] == 'nation' else '', gov_status='government' if w['kind'] == 'nation' else '',
             level=lvl, type=typ, feed='inst-lane', wikidata=w['wikidata'], source_record_id=w['wikidata'])
    e['alias'] = esc(w['wd_label']) if w['wd_label'] and w['wd_label'] != w['ne_name'] else ''
    fl = list(w['flags']) + ([] if w['kind'] == 'nation' else ['gov_status_unknown:outside_cog2022_scope']) + ['outside_v2_scope:no_unit_no_boundary_set']
    e['flags'] = ';'.join(f_.replace(';', ',') for f_ in fl); e['_flags'] = fl
    e['_src'] = ([S_WD] if w['wikidata'] else []) + ([] if w.get('origin') == 'wikidata' else [S_NE_CA if w['entity_id'].startswith(('province:ca-', 'territory:ca-')) else S_NE_C])
    for k_ in ('v2_layer', 'v2_row', 'v2_key', 'predecessor_id', 'successor_id', 'valid_from', 'valid_to', 'state_fips', 'state', 'cog_pid6'): e[k_] = ''
    OUTROWS.append(e)
for g in WORLD['gaps'] + WGAPS: GAPS.append(dict(g))
# nation:us keeps its id and values; it gets the Wikidata QID that P297 US resolves to
for e in OUTROWS:
    if e['entity_id'] == 'nation:us' and WORLD['qid_us']: e['wikidata'] = WORLD['qid_us']
# source_record_id: the entity's id inside its FIRST cited source (GEOID / FIPS code for TIGER, Gazetteer and ANSI rows; QID for Wikidata)
for e in OUTROWS:
    if e.get('source_record_id'): continue
    f0 = e['_src'][0] if e['_src'] else ''
    e['source_record_id'] = e['geoid'] if e['geoid'] and (f0 == S_GEOJSON or f0.startswith('U.S. Census Bureau,') and 'Gazetteer' in f0 or f0.startswith(S_ST)) else ''
    e.setdefault('wikidata', '')
# ---------------- Governments bot feed (tools/inst_govfeed.py): id map, QIDs, ceased/new units, seals and flags ----------------
import inst_govfeed
GOVF = inst_govfeed.load(R, GOV_SHA)
_ents = {e['entity_id']: e for e in OUTROWS}
for e in OUTROWS: e.setdefault('wikidata', '')
_cons = {CG24[c]['cog_pid6']: f'county:{c}' for c in UNLINKED_CONS if CG24[c]['cog_pid6']}
# special districts (Full Stack, Oct 18): kind special_district, id special_district:<st>-<source>-<source_id> (frozen;
# normalisation in tools/inst_govfeed.py). Minted from the bot's TCEQ WDD rows; parent state:<FIPS> (+ `parent` relation);
# county link = relation in_county with `method` (tceq_wdd_primary_county: the WDD primary county, as given by the bot's
# county_geoid; a sourced value, not an estimate, so no ≈). No county in the row -> special_district_county_unknown gap.
S_TCEQ = 'TCEQ Water Districts Database (Governments bot source tceq_wdd)'
import inst_commons
CM, CM_SHA, CM_AT = inst_commons.info(A.commons_cache)
CM_AT = CM_AT + ' (v2: ' + open(os.path.join(A.commons_cache, 'v2_retrieved_at.txt')).read().strip() + ')'
CM_AT = CM_AT[:-1] + '; v3: ' + open(os.path.join(A.commons_cache, 'v3_retrieved_at.txt')).read().strip() + ')'
CM_AT = CM_AT[:-1] + '; v4: ' + open(os.path.join(A.commons_cache, 'v4_retrieved_at.txt')).read().strip() + ', ' + open(os.path.join(A.commons_cache, 'v4b_retrieved_at.txt')).read().strip() + ')'
S_COMMONS = 'Wikimedia Commons API cache (tools/inst_commons.py)'
SDGAPS, SDRELS, SDSTAT, _sdmint = [], [], C.Counter(), {}
for sid_, r in inst_govfeed.special_districts(GOVF):
    e = {c: '' for c in COLS}
    for k_ in ('v2_layer', 'v2_row', 'v2_key', 'predecessor_id', 'successor_id', 'valid_from', 'valid_to', 'cog_pid6', 'parent_id', 'iso_3166_2', 'constituent_qid', 'inception', 'inception_precision', 'inception_source'): e[k_] = ''
    e.update(entity_id=sid_, kind='special_district', level='local', type=r['subtype'], state_fips=r['state_fips'], state=FIPS[r['state_fips']][1],
             name=r['name'], gov_status=GSM[r['gov_status']], parent_id=r['parent_id'], parent_entity_id=r['parent_id'], feed='governments-bot',
             source_record_id=r['entity_id'], wikidata='')
    e['_alias'] = set(); e['_v2'] = []; e['_src'] = [S_GOV, S_TCEQ]; e['_flags'] = ['outside_v2_scope:no_unit_no_boundary_set']
    assert sid_ not in _ents and r['parent_id'] in _ents
    OUTROWS.append(e); _ents[sid_] = e; _sdmint[r['entity_id']] = sid_; SDSTAT['minted'] += 1
    SDRELS.append({'entity_id': sid_, 'relation': 'parent', 'related_entity_id': r['parent_id'], 'method': '', '_k': 'parent'})
    cg = r.get('county_geoid', '')
    if cg and f'county:{cg}' in _ents and _ents[f'county:{cg}']['state_fips'] == r['state_fips']:
        SDRELS.append({'entity_id': sid_, 'relation': 'in_county', 'related_entity_id': f'county:{cg}', 'method': 'sourced', 'note': 'tceq_wdd_primary_county', '_k': 'county'}); SDSTAT['county|sourced'] += 1
    else:
        SDGAPS.append({'gap': 'special_district_county_unknown', 'key': sid_, 'detail': f"{r['name']} ({r['entity_id']}): " + (f'county_geoid {cg} not a county of state {r["state_fips"]} in the registry' if cg else 'the bot row has no county_geoid (TCEQ WDD primary county not given or not matched to a Census county name) and no coordinates; no county link')})
        SDSTAT['county|none_gap'] += 1
GFMAP, GIMG, GGAPS, GSTAT, GRELS = inst_govfeed.integrate(GOVF, _ents, {k: v for k, v in GIDX.items()}, _cons, _sdmint)
GGAPS.extend(SDGAPS)
_relc = {r['entity_id'][len('county:'):] for r in GRELS}
GAPS[:] = [g for g in GAPS if not (g['gap'] == 'consolidated_county_cog_code_not_in_tiger' and g['key'] in _relc)]
# Full Stack ruling (Oct 18): a county in a consolidated_with relation is governed by the consolidated government ->
# gov_status government; the 'not linked to a TIGER code' unknown flag is dropped (the relation is the link). No relation -> flag stays.
_relcounties = sorted({x for r in GRELS if r['relation'] == 'consolidated_with' for x in (r['entity_id'], r['related_entity_id']) if x.startswith('county:')})
for cid in _relcounties:
    e = _ents[cid]; e['gov_status'] = 'government'
    e['_flags'] = [x for x in e['_flags'] if not x.startswith('gov_status_unknown:consolidated_government_not_linked_to_tiger_code')]
GSTAT['consolidated_counties_gov_status_set'] = len(_relcounties)
# ---------------- Governments bot foreign layer (tools/inst_foreign.py): nations, dependencies, ISO 3166-2 subdivisions ----------------
import inst_foreign
FOR = inst_foreign.load(R, A.foreign_ref); FOR_SHA = FOR['commit']
S_GF = {f: f'Governments bot {f} (foreign layer)' for f in inst_foreign.FILES}
def _newrow(**kw):
    e = {c: '' for c in COLS}
    for k_ in ('v2_layer', 'v2_row', 'v2_key', 'predecessor_id', 'successor_id', 'valid_from', 'valid_to', 'cog_pid6', 'parent_id', 'iso_3166_2', 'constituent_qid', 'inception', 'inception_precision', 'inception_source'): e[k_] = ''
    e.update(kw); e['alias'] = esc(e['alias']) if e['alias'] else ''
    e['parent_entity_id'] = e['parent_id']; e['_alias'] = set(); e['_v2'] = []; e['_src'] = []; e['_flags'] = []
    return e
_dom_f2e = {m['feed_id']: m['entity_id'] for m in GFMAP if m['entity_id']}
FRES = inst_foreign.integrate(FOR, _ents, _newrow, _dom_f2e)
OUTROWS.extend(FRES['rows'])
for e in OUTROWS:
    f_ = e.pop('_gf', None)
    if f_: src(e, S_GF[f_])
_minted = {e['entity_id'] for e in FRES['rows']}
FCLOSE = [(g, k) for g, k, need in [('not_in_source_list', 'Palestine', 'nation:ps'), ('not_in_source_list', 'Faroe Islands', 'territory:fo'),
                                     ('world_entity_excluded_no_sovereign', 'territory:im', 'territory:im'), ('territory_sovereign_unknown', 'territory:im', 'territory:im')] if need in _minted]
FCLOSED = [g for g in GAPS if (g['gap'], g['key']) in FCLOSE]
GAPS[:] = [g for g in GAPS if (g['gap'], g['key']) not in FCLOSE]
for g in GAPS:
    if g['gap'] == 'not_in_source_list' and g['key'] == 'Kosovo' and 'subdivision:rs-km' in _ents:
        g['detail'] += '; Governments bot: not in nations/dependencies; ISO 3166-2 RS-KM (Kosovo-Metohija) is a Serbian subdivision row, minted as subdivision:rs-km under nation:rs; pending the user'
    if g['gap'] == 'not_in_source_list' and g['key'] == 'Western Sahara' and 'nation:eh' in FRES['review']:
        g['detail'] += '; Governments bot nations.csv has nation:eh flagged review_status: feed_only, not minted; pending the user'
GAPS.extend(FRES['gaps'])
# ---------------- Governments bot country layers gb / de / fr (tools/inst_foreign_local.py; same pinned commit as the foreign layer) ----------------
import inst_foreign_local
LOC = inst_foreign_local.load(R, A.foreign_ref); assert LOC['commit'] == FOR_SHA
LRES = inst_foreign_local.integrate(LOC, _ents, _newrow)
OUTROWS.extend(LRES['rows'])
GAPS.extend(LRES['gaps'])
print('country layers', LRES['stats'], file=sys.stderr)
# Full Stack (Oct 18): the home-part QID rule is confirmed by the bot (sovereign-state item + constituent_qid) -> gap closed, flag kept
_hp = [g for g in GAPS if g['gap'] == 'wikidata_qid_via_home_part_rule' and _ents.get(g['key'], {}).get('constituent_qid') and _ents[g['key']]['constituent_qid'] in g['detail']]
GAPS[:] = [g for g in GAPS if g not in _hp]; FCLOSED += _hp
# wikidata: 'wikidata:Q…', nullable + unique (SCHEMA); a QID on several entities is blanked on all of them and logged
_qc = C.Counter(e['wikidata'] for e in OUTROWS if e.get('wikidata'))
for e in OUTROWS:
    q_ = e.get('wikidata', '')
    if q_ and _qc[q_] > 1:
        GGAPS.append({'gap': 'wikidata_qid_duplicate', 'key': e['entity_id'], 'detail': f"{q_} also on " + ';'.join(sorted(x['entity_id'] for x in OUTROWS if x.get('wikidata') == q_ and x is not e)) + '; left empty'})
        e['wikidata'] = ''
    elif q_: e['wikidata'] = 'wikidata:' + q_
GSTAT['wikidata_duplicates_blanked'] = sum(1 for g in GGAPS if g['gap'] == 'wikidata_qid_duplicate')
GAPS.extend(GGAPS)
for e in OUTROWS:
    if e.pop('_gov', False): src(e, S_GOV)
    e['flags'] = ';'.join(f_.replace(';', ',') for f_ in e['_flags'])
print('governments feed', dict(sorted(GSTAT.items())), file=sys.stderr)
# body_entity.csv (Full Stack, Oct 18): body_key (PK) -> entity_id + role; officeholders and seats attach to body_key, not the entity
_xwp = {}
for x in XW:
    if x['geoid_layer'] == 'place': _xwp.setdefault(x['entity_id'], set()).add(x['geoid'])
BLINKS, BGAPS, BSTAT = inst_bodies.match(SEAT, {e['entity_id']: e for e in OUTROWS}, {f: v[0] for f, v in FIPS.items()}, _xwp, GRELS)
GAPS.extend(SEAT_GAPS)
ids = [e['entity_id'] for e in OUTROWS]; assert len(ids) == len(set(ids)), 'entity_id not unique'

# ---------------- sources.csv: every cited source once, stable ids (tools/inst_sources.py) ----------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inst_sources import Registry
GEO_SHA = subprocess.run(['git', '-C', R, 'merge-base', 'HEAD', 'origin/data/geo'], capture_output=True, text=True).stdout.strip()
OH_SOURCES = git_show('data-v3/inst/sources.csv')
REPO = 'https://github.com/ge0r9b/us-districts'
OHLIC = 'per row: CC0 1.0 / public domain (US government work) / official public record (see the officeholder rows)'
GAZ = re.compile(r'(\d{4}) TIGER/Line Gazetteer \((\d{4}_Gaz_\w+?_national)\.txt\)')
GOVSRC_IDS = {r_['source_id'] for r_ in GOVF['sources']}
LOCLIC = {'gb': 'Open Government Licence v3.0 (ONS); CC0 1.0 (Wikidata)', 'de': 'dl-de/by-2-0 (Destatis, BKG); CC0 1.0 (Wikidata)',
          'fr': 'Licence Ouverte / Open Licence 2.0 (INSEE, IGN); CC0 1.0 (Wikidata)'}
def build_registry():
    reg = Registry(); reg.load(OH_SOURCES, text=True)
    CGID = next(r['source_id'] for r in CG if r['vintage'] == '2024').split(';')   # exact ids county_government.csv cites
    def pre(p): return next(k for k in CGID if k.startswith(p))
    def atom(t):
        if t == S_TCEQ: return ['tceq_wdd']
        if t.startswith('GOVSRC:'):   # a Governments-bot source id cited by a country-layer row (unioned from the bot's sources.csv)
            assert t[7:] in GOVSRC_IDS, t; return [t[7:]]
        if t.startswith('GF:'): return atom(S_GF[t[3:]])
        if t.startswith('GOVLOCAL:'):
            f_ = t[9:]; F_ = LOC['files'][f_]; cc_ = f_.split('/')[0]
            what = 'unit rows' if '/units' in f_ else 'code crosswalk (GSS / ARS / INSEE / SIREN / ISO 3166-2 codes -> government rows)'
            return [reg.add(None, f"Governments bot, {F_['path']} ({ {'gb': 'United Kingdom', 'de': 'Germany', 'fr': 'France'}[cc_]} country layer: {what}; {F_['rows']} rows); pinned at this commit",
                            f"{REPO}/blob/{LOC['commit']}/{F_['path']}", LOCLIC[cc_], RETRIEVED, LOC['commit'], F_['sha256'])]   # the Governments bot's own sources.csv id (added by the union with its sources.csv below)
        if t == S_COMMONS: return [reg.add('commons-api-cache', 'Wikimedia Commons API imageinfo/extmetadata (descriptionurl, Artist, Credit, LicenseShortName) for free image rows with missing fields; responses cached by tools/inst_commons.py; sha256 = of the cache SHA256SUMS file',
                                           'https://commons.wikimedia.org/w/api.php', 'metadata: CC BY-SA 4.0 / CC0 (Wikimedia); each image under its own licence', CM_AT, '', CM_SHA)]
        m = GAZ.search(t)
        if m: return [reg.add(None, f'U.S. Census Bureau, {m.group(1)} TIGER/Line Gazetteer ({m.group(2)}.txt)',
                              f'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/{m.group(1)}_Gazetteer/{m.group(2)}.zip', PD, RETRIEVED)]
        if t.startswith('ANSI/FIPS state codes'): return [reg.add(None, S_ST, 'https://www.census.gov/library/reference/code-lists/ansi.html', PD, RETRIEVED)]
        if t.startswith('U.S. Constitution'): return [reg.add(None, 'U.S. Constitution (National Archives transcript)', 'https://www.archives.gov/founding-docs/constitution-transcript', PD, RETRIEVED)]
        if 'Home Rule Act' in t: return [reg.add(None, 'District of Columbia Home Rule Act (D.C. Code title 1 ch. 2)', 'https://code.dccouncil.gov/us/dc/council/code/titles/1/chapters/2', PD, RETRIEVED)]
        if t == S_GEOJSON or 'town_pairs.csv' in t:
            return [reg.add(None, 'U.S. Census Bureau TIGER/Line 2024 county subdivisions + places (FUNCSTAT, CLASSFP, NAMELSAD, geometry; via data-v3/geo GeoJSON and town_pairs.csv)',
                            'https://www2.census.gov/geo/tiger/TIGER2024/COUSUB/ ; https://www2.census.gov/geo/tiger/TIGER2024/PLACE/', PD, RETRIEVED)]
        if t == S_COG: return [pre('census-cog2022-')]
        if t == S_GOV: return [reg.add(None, 'Governments bot, data-v3/institutions/governments (gov_status, nces_leaid, wikidata_qid, ceased/new units, id map; files pinned at this commit)', f'{REPO}/tree/{GOV_SHA}/data-v3/institutions/governments', 'public domain (US government work)', RETRIEVED, GOV_SHA)]
        if t == S_CG: return [pre('repo-governments-'), pre('census-cog2022-'), pre('census-tiger2024-county-')]
        if t.startswith(S_OH): return [reg.add(None, 'data-v3/inst officeholder files (entity_id + unit as published there)', f'{REPO}/tree/{OH_SHA}/data-v3/inst', OHLIC, RETRIEVED, OH_SHA)]
        if t.startswith('v2/data/dc.js'): return [reg.add(None, 'v2/data/dc.js (DC wards stand in for state senate and house)', f'{REPO}/blob/{GEO_SHA}/v2/data/dc.js', 'project data (v2), derived from public-domain Census TIGER', RETRIEVED, GEO_SHA)]
        if t == 'U.S. Census Bureau Gazetteer': return []
        if t in (S_NE_C, S_NE_CA):
            f_ = inst_world.COUNTRIES if t == S_NE_C else inst_world.CANADA; ne_ = WORLD['ne'][f_]
            return [reg.add(None, t + ' (Natural Earth, public domain; list of institutions only, no geometry used)',
                            f"{REPO}/blob/{ne_['commit']}/{f_} ; https://www.naturalearthdata.com/downloads/50m-cultural-vectors/",
                            'public domain (Natural Earth)', RETRIEVED, ne_['commit'], ne_['sha256'])]
        if t in (S_BODIES, S_SEATMETA, S_CITYB):
            f_ = {S_BODIES: 'bodies.csv', S_SEATMETA: 'build_meta.json', S_CITYB: 'city_bodies.csv'}[t]; F_ = SEAT['files'][f_]
            what = {S_BODIES: 'bodies (legislative chambers, courts, city councils and mayors; key, st, kind, office, name, geoid, entity)',
                    S_SEATMETA: 'build metadata (excluded_courts, dropped_courts, skipped_cities)',
                    S_CITYB: 'city bodies (geoid, entity per council/mayor; read-only cross-check of the bodies.csv geoid/entity)'}[t]
            return [reg.add(None, f"Seating Charts bot, {F_['path']}: {what}; committed on branch data/seating, pinned at this commit; joined on bodies.csv key only",
                            f"{REPO}/blob/{SEAT_SHA}/{F_['path']}",
                            'project data (Seating Charts bot; its sources: congress-legislators, senate.gov, House Clerk, Ballotpedia, Open States, court and city pages)',
                            RETRIEVED, SEAT_SHA, F_['sha256'])]
        if t in S_GF.values():
            f_ = next(k for k, v in S_GF.items() if v == t); F_ = FOR['files'][f_]
            lic = 'per row: Commons licence (see entity_images.csv license)' if f_ == 'images.csv' else 'LGPL-2.1-or-later (Debian iso-codes); CC0 1.0 (Wikidata); facts only (UN website); Statistics Canada SGC (Open Government Licence - Canada)'
            return [reg.add(None, f"Governments bot, {F_['path']} (foreign layer: nations, dependencies, ISO 3166-2 subdivisions, ISO->domestic crosswalk, foreign flags/seals); pinned at this commit",
                            f"{REPO}/blob/{FOR_SHA}/{F_['path']}", lic, RETRIEVED, FOR_SHA, F_['sha256'])]
        if t == S_WD:
            qs = hashlib.sha256(''.join(open(os.path.join(A.world_raw, f_)).read() for f_ in sorted(WORLD['files']) if f_.endswith('.rq')).encode('utf-8')).hexdigest()
            return [reg.add(None, 'Wikidata Query Service: ISO 3166-1 P297 / ISO 3166-2 P300 items + current P31 Q3624078, P463 Q1065, P17, P361, P300, P36 '
                            '(tools/inst_world.py; sha256 = of the 4 .rq query texts concatenated in file-name order; answer sha256s in entities_summary.json world.files)',
                            'https://query.wikidata.org/sparql', 'CC0 1.0 (Wikidata)', WORLD['retrieved_at'], '', qs)]
        raise SystemExit('unmapped source text: ' + t)
    def ids_for(texts):
        out = []
        for t in texts:
            for part in re.split(r' \+ (?=U\.S\. )', t):
                for i in atom(part.strip()):
                    if i not in out: out.append(i)
        return ';'.join(out)
    geo = reg.add(None, 'data-v3/geo crosswalk tables (v2 row -> TIGER GEOID; counties, schools, ushouse, sldu/sldl, v1_towns, town_pairs)', f'{REPO}/tree/{GEO_SHA}/data-v3/geo', 'project data, derived from public-domain Census TIGER', RETRIEVED, GEO_SHA)
    v2p = reg.add(None, 'v2/data/parts/*.js (v2 county-part rows)', f'{REPO}/tree/{GEO_SHA}/v2/data/parts', 'project data (v2)', RETRIEVED, GEO_SHA)
    v2c = reg.add(None, 'v2/data/places/*.js (v2 place rows)', f'{REPO}/tree/{GEO_SHA}/v2/data/places', 'project data (v2)', RETRIEVED, GEO_SHA)
    tig = atom(S_GEOJSON)[0]; cog = pre('census-cog2022-'); oh = atom(S_OH)[0]
    V2SRC = {'v2:parts': f'{geo};{v2p};{tig}', 'v2:places': f'{geo};{v2c};{tig}'}
    GAPSRC = {'orphan_officeholder_unit': oh, 'officeholder_unit_without_tiger_geoid': oh, 'cog2022_unit_not_linked_by_code': cog,
              'gov_status_unknown': f'{tig};{cog}', 'excluded_not_defined': '', 'consolidated_county_cog_code_not_in_tiger': f'{cog};{tig}',
              'consolidated_county_no_government_linked': f'{cog};{tig}', 'same_code_place_cousub_overlap_unmeasured': tig,
              'town_pair_same_neither_in_cog': f'{geo};{cog}', 'school_gov_status_conflict': atom(S_GOV)[0]}
    wd_ = atom(S_WD)[0]; nec = atom(S_NE_C)[0]
    GAPSRC['not_in_source_list'] = f'{nec};{wd_}'
    GAPSRC['not_in_seating_charts'] = atom(S_SEATMETA)[0]
    atom(S_BODIES); atom(S_CITYB); atom(S_COMMONS)
    GAPSRC['image_free_field_missing'] = atom(S_COMMONS)[0] + ';' + atom(S_GOV)[0]
    for f_ in inst_foreign.FILES: atom(S_GF[f_])
    GAPSRC['govbot_foreign_parent_differs'] = GAPSRC['govbot_foreign_parent_missing'] = GAPSRC['govbot_foreign_attr_differs'] = ';'.join(atom(S_GF[f_])[0] for f_ in inst_foreign.FILES[:3])   # body_entity.csv / body_key_gaps.csv cite these; registered here so the stability rebuild has them
    for g_ in ('wikidata_p297_several_items', 'wikidata_qid_via_home_part_rule', 'territory_sovereign_unknown', 'nation_not_un_member',
               'territory_sovereign_several_candidates', 'wikidata_status_ambiguous', 'world_entity_excluded_no_sovereign'): GAPSRC[g_] = wd_
    GAPSRC['wikidata_qid_missing'] = f'{nec};{wd_}'
    L_ = lambda *fs: ';'.join(atom('GOVLOCAL:' + f_)[0] for f_ in fs)
    for f_ in sorted(LOC['files']): atom('GOVLOCAL:' + f_)
    GAPSRC['intermunicipal_council_unknown'] = L_('de/units.csv')
    GAPSRC['govbot_mapping_overridden'] = L_('fr/code_xwalk.csv', 'fr/units_upper.csv', 'fr/units_communes_01.csv', 'fr/units_communes_04.csv')
    GAPSRC['govbot_unit_duplicates_registry'] = L_('fr/units_communes_om.csv', 'fr/code_xwalk.csv')
    GAPSRC['siren_bad_join'] = L_('fr/units_communes_44.csv', 'fr/units_communes_76.csv')
    GAPSRC['govbot_xwalk_relation_overridden'] = L_('gb/code_xwalk.csv')
    GAPSRC['code_terminated_unresolved'] = L_('gb/units.csv')
    gv_ = atom(S_GOV)[0]
    for g_ in ('govbot_territory_key_differs', 'govbot_frozen_id_conflict', 'govbot_mapping_conflict', 'govbot_mapping_ambiguous', 'govbot_registry_id_not_in_files',
               'wikidata_qid_conflict', 'wikidata_qid_duplicate', 'image_fair_use_inconsistent', 'govbot_ceased_dates_disagree', 'govbot_ceased_partial', 'govbot_new_unit_not_in_registry', 'image_entity_unmapped', 'special_district_county_unknown', 'image_attribution_missing'): GAPSRC[g_] = gv_
    return reg, ids_for, (lambda l: V2SRC.get(l, geo)), GAPSRC
REG, IDS_FOR, V2SRC_FOR, GAPSRC = build_registry()
COLS2 = ['entity_id', 'kind', 'state_fips', 'state', 'name', 'alias', 'label', 'gov_status', 'parent_id', 'valid_from', 'valid_to',
         'predecessor_id', 'successor_id', 'v2_layer', 'v2_row', 'v2_key', 'source_id',
         'feed', 'level', 'type', 'cog_pid6', 'flags', 'source_record_id', 'wikidata', 'iso_3166_2', 'constituent_qid', 'inception', 'inception_precision', 'inception_source', 'valid_from_source', 'code_scheme', 'code', 'code_valid_from']
ORDER = ['nation', 'state', 'territory', 'province', 'chamber', 'dc_council', 'court', 'subdivision', 'regional_authority', 'county', 'local_authority',
         'intermunicipal', 'municipality', 'submunicipal', 'parish', 'township', 'school_unified', 'school_elementary', 'school_secondary', 'special_district']
FEEDS = {'tiger/cog', 'inst-lane', 'governments-bot', 'companies-bot', 'user-upload'}   # DATA_LOADING §15.1 feed -> origin map
for e in OUTROWS:
    e['source_id'] = IDS_FOR(e['_src']); assert e['source_id'], e['entity_id']
    assert not e.get('valid_from') or e.get('valid_from_source'), ('valid_from without valid_from_source', e['entity_id'])
    assert e['feed'] in FEEDS, (e['entity_id'], e['feed'])
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
                'boundary_set': 'v2-2024' if x['vintage'] == '2024' else f"tiger-{x['vintage']}-{x['geoid_layer']}", 'source_id': IDS_FOR(srcs),
                'overlap': 'equal' if x['relation'] == 'primary' else x['relation'], 'share_of_geoid_in_entity': x['share_of_geoid_in_entity'],
                'share_of_entity_in_geoid': x['share_of_entity_in_geoid'],
                # the GEOID is the record id inside the cited Census source (Gazetteer / TIGER / ANSI); empty for derived links
                'source_record_id': x['geoid'] if srcs and (srcs[0] in (S_GEOJSON, S_ST, 'U.S. Census Bureau Gazetteer') or (srcs[0].startswith('U.S. Census Bureau,') and 'Gazetteer' in srcs[0])) else ''})
XC2 = ['entity_id', 'unit_layer', 'geoid', 'vintage', 'boundary_set', 'relation', 'source_id', 'overlap', 'share_of_geoid_in_entity', 'share_of_entity_in_geoid', 'source_record_id']
xk = [(x['entity_id'], x['unit_layer'], x['geoid'], x['vintage']) for x in XW2]; assert len(xk) == len(set(xk))
assert {x['entity_id'] for x in XW2} <= set(ids)
with open(os.path.join(OUT, 'entity_geoid_xwalk.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, XC2, lineterminator='\n'); w.writeheader(); w.writerows(sorted(XW2, key=lambda x: (x['entity_id'], x['vintage'], x['relation'] != 'primary', x['unit_layer'], x['geoid'])))
# v2 back-link table: district rows resolve to chamber entity + unit
SEATPAR = {e['entity_id']: e['parent_entity_id'] for e in SEATS}
VC = ['v2_layer', 'state', 'v2_row', 'v2_name', 'unit_layer', 'geoid', 'vintage', 'entity_id', 'resolved', 'note', 'source_id']
V2OUT = []
for v in V2:
    o = dict(v); o['unit_layer'] = o.pop('geoid_layer')
    if o['entity_id'] in SEATPAR: o['entity_id'] = SEATPAR[o['entity_id']]; o['note'] = ('district unit of the chamber; ' + o['note']).rstrip('; ')
    o['source_id'] = V2SRC_FOR(o['v2_layer'])
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
# Full Stack (Oct 18): every fair-use row carries license, attribution, source_url. An empty attribution is filled with the
# issuing body's name (the registry entity's name, else the bot feed row's name), never invented; attribution_source says which.
_botname = {r['entity_id']: r['name'] for r in GOVF['rows']}
IMGATTR = C.Counter()
for i in GIMG + FRES['imgs']:
    i['attribution_source'] = 'feed' if i['attribution'] else ''
    if i['fair_use'] != 'yes' or i['attribution']: continue
    nm_ = _ents[i['entity_id']]['name'] if i['entity_id'] else _botname.get(i['feed_id'], '')
    if nm_:
        i['attribution'] = f'{nm_} (issuing body)'; i['attribution_source'] = 'issuing_body_name:' + ('registry_entity' if i['entity_id'] else 'governments_bot_row'); IMGATTR[i['attribution_source']] += 1
    else:
        GAPS.append({'gap': 'image_attribution_missing', 'key': i['feed_id'], 'detail': f"fair-use {i['role']} {i['source_url']}: no attribution in the feed and no issuing-body name"}); IMGATTR['gap'] += 1
# Commons backfill (Full Stack, Oct 18): free rows missing source_url / attribution / license are filled from the cached
# Commons API answers (source_url = file page descriptionurl, attribution = Artist else Credit, license = LicenseShortName);
# never invented. A free row still missing license or attribution -> public no + gap image_free_field_missing. Free rows
# with a Copyrighted-free-use / Attribution licence stay public only with an attribution (same rule).
CMSTAT = C.Counter()
CMPG = inst_commons.pages(A.commons_cache)
PD_TXT = 'Public domain, via Wikimedia Commons'
def _is_pd(rec):   # a Commons public-domain licence (LicenseShortName or License), not merely the absence of an author
    ls, li = rec['LicenseShortName'].lower(), rec['License'].lower()
    return ls == 'public domain' or ls.startswith(('public domain', 'pd-', 'pd ')) or li == 'pd' or li.startswith('pd-')
def _page_reason(t):
    pg = CMPG.get(t)
    if not pg: return ''
    lic_t = [x for x in pg['templates'] if re.match(r'Template:(PD|Cc-|CC-|GFDL|FAL|Copyrighted free use|Attribution|OGL|Licen)', x)]
    if lic_t: return ''
    r_ = f"Commons file page (revid {pg['revid']}) has no licence template: only " + ', '.join('{{' + x[len('Template:'):] + '}}' for x in pg['templates'] if x in ('Template:Insignia', 'Template:Non-copyright restriction'))
    r_ += '; categories: ' + ', '.join(c_[len('Category:'):] for c_ in pg['categories'] if 'license' in c_.lower() or 'deletion' in c_.lower())
    return r_ + '; licence not determined, not guessed'
V3LIC, V3HIST, V3QC = inst_commons.v3(A.commons_cache)
def _spdx(li): return li.upper().replace('CC0', 'CC0-1.0') if li.lower() == 'cc0' else li.upper()   # cc-by-sa-4.0 -> CC-BY-SA-4.0
# explicit, logged image overrides (tools/inst_image_overrides.py); each drops itself once the feed carries the new file
import inst_image_overrides
_v4p, _v4h = inst_commons.v4(A.commons_cache)
_ovp = {p_['title']: p_ for p_ in V3QC}; _ovp.update({p_['title']: p_ for p_ in _v4p})
IMGOVR = inst_image_overrides.apply(GIMG + FRES['imgs'], _ovp, inst_commons.text, _spdx)
CMSTAT['overrides_applied'] = sum(1 for x in IMGOVR if x['outcome'] == 'applied')
for i in GIMG + FRES['imgs']:
    if i['fair_use'] == 'yes': continue
    unk = inst_commons.is_unknown(i['attribution'])
    if unk: CMSTAT['unknown_attribution_rows'] += 1; i['attribution'] = ''
    need = [c for c in ('source_url', 'attribution', 'license') if not i[c]]
    if not need: continue
    t_ = inst_commons.norm(i['file']) if i['file'] else ''
    rec = CM.get(t_) if t_ else None
    ok = rec and not rec['missing']
    for c in need:
        v, how = '', ''
        if ok:
            if c == 'source_url': v = rec['descriptionurl']
            elif c == 'license': v = rec['LicenseShortName']
            else:
                art = '' if inst_commons.is_unknown(rec['Artist']) else rec['Artist']
                if unk and _is_pd(rec): v, how = PD_TXT, 'commons_license'   # Unknown artist + PD licence -> rule 1
                elif art: v, how = art, 'commons_artist'
                elif rec['Credit'] and not inst_commons.is_unknown(rec['Credit']): v, how = rec['Credit'], 'commons_credit'
                elif _is_pd(rec): v, how = PD_TXT, 'commons_license'
                elif rec['LicenseShortName'].lower() == 'cc0' or rec['License'].lower() == 'cc0': v, how = 'CC0, via Wikimedia Commons', 'commons_license'
                elif rec['LicenseShortName'].lower() == 'copyrighted free use': v, how = 'Copyrighted free use, via Wikimedia Commons', 'commons_license'
                elif rec['LicenseShortName'].upper().startswith('CC BY-SA') and t_ in V3HIST and V3HIST[t_] is not None:
                    h_ = V3HIST[t_]   # earliest upload revision = original uploader (TASL: title/source via the file page URL)
                    if h_.get('user') and 'userhidden' not in h_: v, how = f"{h_['user']}, {rec['descriptionurl']}, {rec['LicenseShortName']}", 'commons_uploader'
                    else: v, how = f"Wikimedia Commons contributors, {rec['descriptionurl']}, {rec['LicenseShortName']}", 'commons_contributors'
        if v:
            i[c] = v; i['_cm'] = True; CMSTAT[f'{c}|filled' + (f'|{how}' if how else '') + ('|was_unknown' if unk and c == 'attribution' else '')] += 1
            if how: i['attribution_source'] = how
        else: CMSTAT[f'{c}|still_missing' + ('|was_unknown' if unk and c == 'attribution' else '')] += 1
    miss = [c for c in ('license', 'attribution', 'source_url') if not i[c]]
    if miss:
        pr_ = _page_reason(t_) if 'license' in miss else ''
        _nr = inst_image_overrides.NO_REPLACEMENT.get((i['entity_id'], i['role']))
        if _nr: pr_ = (pr_ + '; ' if pr_ else '') + _nr
        why = pr_ or ('file not in the Commons cache' if not rec else ('Commons has no such file page' if rec['missing'] else 'Commons extmetadata has no ' + '/'.join({'license': 'LicenseShortName', 'attribution': 'Artist or Credit (and no PD licence)', 'source_url': 'descriptionurl'}[c] for c in miss)))
        if unk and 'attribution' in miss: why += '; feed/Commons author is only "Unknown"'
        priv = any(c in miss for c in ('license', 'attribution'))
        GAPS.append({'gap': 'image_free_field_missing', 'key': i['entity_id'] or i['feed_id'], 'detail': f"{i['role']} {i['file']}: missing {','.join(miss)} ({why})" + ('; set public=no' if priv else '; stays public (licence and attribution present)')})
        if priv: i['_private'] = True; CMSTAT['switched_to_private'] += 1
def _cc_deed(l):
    if l.upper() == 'CC0-1.0': return 'https://creativecommons.org/publicdomain/zero/1.0/'
    m_ = re.fullmatch(r'CC-(BY(?:-SA|-NC|-ND|-NC-SA|-NC-ND)?)-(\d\.\d)(?:-([A-Z]{2}))?', l.upper())
    return f"https://creativecommons.org/licenses/{m_.group(1).lower()}/{m_.group(2)}/" + (m_.group(3).lower() + '/' if m_.group(3) else '') if m_ else ''
LICURL = C.Counter()
for i in GIMG + FRES['imgs']:
    if i.get('licence_url'): LICURL['commons_licenseurl'] += 1; continue
    cu = (V3LIC.get(inst_commons.norm(i['file'])) or {}).get('LicenseUrl', '') if i['file'] and i['fair_use'] == 'no' else ''
    is_cc = i['license'].upper().startswith(('CC-', 'CC0'))
    i['licence_url'] = cu or (_cc_deed(i['license']) if is_cc else '')
    if i['licence_url']: LICURL['commons_licenseurl' if cu else 'cc_canonical_deed'] += 1
    elif is_cc: LICURL['cc_without_url'] += 1
# CC licence_url -> canonical https://creativecommons.org deed (same licence + version + port; scheme https, trailing '/', no deed.xx)
LICCAN = C.Counter()
for i in GIMG + FRES['imgs']:
    u = i.get('licence_url', '')
    m_ = re.fullmatch(r'https?://creativecommons\.org/(licenses|publicdomain)/([a-z-]+)/(\d\.\d)(/[a-z]{2})?(/deed\.[a-z-]+)?/?', u)
    if not m_: continue
    c_ = f"https://creativecommons.org/{m_.group(1)}/{m_.group(2)}/{m_.group(3)}/" + (m_.group(4)[1:] + '/' if m_.group(4) else '')
    if c_ != u:
        LICCAN['scheme_http_to_https' if u.startswith('http:') else 'form_only'] += 1; i['licence_url'] = c_
    else: LICCAN['already_canonical'] += 1
IMGMISS = {c: sorted(f"{i['feed_id']}|{i['role']}|{i['file'] or i['source_url']}" for i in GIMG + FRES['imgs'] if i['fair_use'] == 'yes' and not i[c]) for c in ('license', 'attribution', 'source_url')}
IMGMISS_ALL = {c: sum(1 for i in GIMG + FRES['imgs'] if not i[c]) for c in ('license', 'attribution', 'source_url')}
def gap_sid(g, ids_for, v2f, gapsrc):
    if g['gap'] == 'orphan_v2_row': return v2f(g['key'].split('|')[0])
    if g['gap'] == 'excluded_not_defined':   # TIGER 'not defined' pseudo-units (ZZZ / water), from the Gazetteer of that layer
        lay = g['key'].split(':')[0]; yr = g['key'].split(':')[2] if g['key'].count(':') >= 2 else '2024'
        fn_ = {('cd', '2024'): '2024_Gaz_119CDs_national.txt', ('cd', '2020'): '2020_Gaz_116CDs_national.txt'}.get((lay, yr), f'{yr}_Gaz_{lay}_national.txt')
        return ids_for([gazsrc(int(yr), fn_)])
    return gapsrc[g['gap']]
for g in GAPS: g['source_id'] = gap_sid(g, IDS_FOR, V2SRC_FOR, GAPSRC)
with open(os.path.join(OUT, 'entity_gaps.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, ['gap', 'key', 'detail', 'source_id'], lineterminator='\n'); w.writeheader(); w.writerows(GAPS)
_bsid = IDS_FOR([S_BODIES]); _csid = IDS_FOR([S_CITYB])
for g in BGAPS: g['source_id'] = _bsid
for l_ in BLINKS: l_['source_id'] = _bsid + (';' + _csid if l_.pop('_m') else '')
with open(os.path.join(OUT, 'body_key_gaps.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, inst_bodies.GAPCOLS, lineterminator='\n'); w.writeheader(); w.writerows(BGAPS)
with open(os.path.join(OUT, 'body_entity.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, inst_bodies.LINKCOLS, lineterminator='\n'); w.writeheader(); w.writerows(BLINKS)
USED = set()
for tbl in (rows, XW2, V2OUT, GAPS, BGAPS, BLINKS):
    for x in tbl: USED.update(i for i in x['source_id'].split(';') if i)
assert USED <= set(REG.rows) | GOVSRC_IDS, USED - set(REG.rows)   # Governments-bot source ids (tceq_wdd, ons_rgc, insee_cog2026, ...): unioned below
REG.write(os.path.join(OUT, 'sources.csv'), keep_existing=False)
# Governments bot sources.csv: union on the bot's own ids (feed-owned rows; their ids are the bot's, not '<slug>-<sha8>')
GV_ID = IDS_FOR([S_GOV])
GOVSRC = {r['source_id']: {c: r.get(c, '') for c in ['source_id', 'source', 'source_url', 'license', 'retrieved_at', 'commit', 'sha256']} for r in GOVF['sources']}
_coll = sorted(set(GOVSRC) & set(REG.rows))
GSTAT['source_id_collisions'] = len(_coll)
for k in _coll:
    if {c: REG.rows[k][c] for c in ('source_url', 'commit')} != {c: GOVSRC[k][c] for c in ('source_url', 'commit')}: raise SystemExit('source_id collision with the Governments bot: ' + k)
FMC = ['feed', 'feed_id', 'entity_id', 'status', 'note', 'source_id']
for m in GFMAP: m['source_id'] = GV_ID
for m in FRES['fmap']: m['source_id'] = IDS_FOR([S_GF[m['_file']]])
for m in LRES['fmap']: m['source_id'] = IDS_FOR(['GOVLOCAL:' + m['_file']])
GFMAP = GFMAP + FRES['fmap'] + LRES['fmap']
with open(os.path.join(OUT, 'entity_feed_map.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, FMC, extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(GFMAP)
IMC = ['entity_id', 'role', 'file', 'license', 'licence_url', 'fair_use', 'public', 'icon', 'usage_basis', 'source_url', 'attribution', 'attribution_source', 'feed_id', 'commons_url', 'wikidata_qid', 'retrieved_at', 'source_id', 'note']
for i in GIMG:
    i['source_id'] = ';'.join([GV_ID] + i['_sid']); assert all(x in GOVSRC for x in i['_sid']), i['_sid']
_gfi = IDS_FOR([S_GF['images.csv']])
for i in FRES['imgs']: i['source_id'] = _gfi
_cmid = IDS_FOR([S_COMMONS])
for i in GIMG + FRES['imgs']:
    if i.get('_cm'): i['source_id'] += ';' + _cmid
GIMG = GIMG + FRES['imgs']
# public = free licence only (fair-use rows stay hidden); icon (one per entity, public only): nation -> its flag, every
# government below the sovereign level -> its seal (coat of arms rows are role seal); no flag fallback, no logo icons
_kind = {e['entity_id']: e['kind'] for e in rows}
for i in GIMG: i['public'] = 'yes' if i['fair_use'] == 'no' and not i.get('_private') else 'no'; i['icon'] = 'no'
_cand = C.defaultdict(list)
for n_, i in enumerate(GIMG):
    if i['entity_id'] and i['public'] == 'yes' and i['role'] == ('flag' if _kind.get(i['entity_id']) == 'nation' else 'seal'): _cand[i['entity_id']].append((i['file'], n_))
for eid_, c_ in _cand.items(): GIMG[min(c_)[1]]['icon'] = 'yes'
ICONSTAT = {'icons': sum(1 for i in GIMG if i['icon'] == 'yes'), 'icons_by_kind_role': dict(sorted(C.Counter(f"{_kind.get(i['entity_id'])}|{i['role']}" for i in GIMG if i['icon'] == 'yes').items())),
            'entities_with_images_no_icon': len({i['entity_id'] for i in GIMG if i['entity_id']} - set(_cand))}
with open(os.path.join(OUT, 'entity_images.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, IMC, extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(GIMG)
RC = ['entity_id', 'relation', 'related_entity_id', 'method', 'note', 'source_id']
_rsid = ';'.join([IDS_FOR([S_COG]), GV_ID, IDS_FOR([S_CG])][:1] + [GV_ID] + IDS_FOR([S_CG]).split(';'))
_rsid = ';'.join(dict.fromkeys(x for x in _rsid.split(';') if x))
for r_ in GRELS: r_['source_id'] = _rsid
# court -> its state government: relation `parent` (related_entity_id is the parent of entity_id; same as entities.parent_id)
for r_ in FRES['rels']: r_['source_id'] = IDS_FOR([S_GF[r_['_file']]])
_tq = [k for k in GOVSRC if k == 'tceq_wdd']; assert _tq
for r_ in SDRELS: r_['source_id'] = GV_ID if r_['_k'] == 'parent' else ';'.join([GV_ID] + _tq)
for r_ in LRES['rels']: r_['source_id'] = IDS_FOR(['GOVLOCAL:' + r_['_file']])
RELS = GRELS + FRES['rels'] + SDRELS + LRES['rels'] + [{'entity_id': e['entity_id'], 'relation': 'parent', 'related_entity_id': e['parent_id'], 'source_id': _bsid} for e in rows if e['kind'] == 'court']
# Full Stack (Oct 18): every current relation is stated by its cited source -> method sourced (parent, consolidated_with, in_county)
for r_ in RELS:
    if not r_.get('method'): r_['method'] = 'sourced'
    assert r_['method'] in ('sourced', 'overlay', 'point_in_polygon', 'manual'), r_
with open(os.path.join(OUT, 'entity_relations.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, RC, extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(sorted(RELS, key=lambda r: (r['entity_id'], r['relation'])))
for k, v in GOVSRC.items(): REG.rows.setdefault(k, v)
REG.write(os.path.join(OUT, 'sources.csv'), keep_existing=False)
# source_urls.csv (SCHEMA source_url): every URL of every source, ord = position in the ' ; '-list, label for multi-URL sources
def url_label(u):
    ul = u.lower()
    for pat, lab in [(r'tiger\d{4}/cousub', 'cousub'), (r'tiger\d{4}/place', 'place'), (r'github\.com/ge0r9b/us-districts/', 'repo file (pinned commit)'),
                     (r'naturalearthdata\.com', 'upstream (Natural Earth)'), (r'/members/members/<chamber>', 'member detail'),
                     (r'senate|chamber=s\b|body=s\b|ss_membs|smembers|t=s\b|/s$', 'senate'),
                     (r'house|assembl|chamber=h\b|body=h\b|hr_membs|hmembers|t=r\b|/h$', 'house')]:
        if re.search(pat, ul): return lab
    return ''
SU = []
for sid in sorted(REG.rows):
    us_ = [u.strip() for u in REG.rows[sid]['source_url'].split(' ; ') if u.strip()]
    for i, u in enumerate(us_, 1):
        lab = url_label(u) if len(us_) > 1 else ''
        assert lab or len(us_) == 1, ('unlabelled url in a multi-URL source', sid, u)
        SU.append({'source_id': sid, 'ord': i, 'url': u, 'label': lab})
    if len(us_) > 1: assert len({url_label(u) for u in us_}) == len(us_), ('duplicate labels', sid, us_)
with open(os.path.join(OUT, 'source_urls.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, ['source_id', 'ord', 'url', 'label'], lineterminator='\n'); w.writeheader(); w.writerows(SU)
if A.stability_test:   # rebuild the registry and every row's ids a second time (texts in reverse order) and compare
    reg2, ids2, v2f, gs2 = build_registry()
    def setof(x): return set(i for i in x.split(';') if i)
    bad = [(e['entity_id'], e['source_id'], ids2(e['_src'][::-1])) for e in rows if setof(ids2(e['_src'][::-1])) != setof(e['source_id'])]
    XWF = [x for x in XW if x['geoid_layer'] not in ('cd', 'sldu', 'sldl')]
    bad += [(x2['entity_id'], x2['source_id'], ids2([y for y in x['source'].split('; ') if y][::-1])) for x, x2 in zip(XWF, XW2)
            if setof(ids2([y for y in x['source'].split('; ') if y][::-1])) != setof(x2['source_id'])]
    bad += [(v['v2_layer'], v['source_id'], v2f(v['v2_layer'])) for v in V2OUT if v2f(v['v2_layer']) != v['source_id']]
    bad += [(g['key'], g['source_id']) for g in GAPS[::-1] if gap_sid(g, ids2, v2f, gs2) != g['source_id']]
    bad += [(l_['body_key'], l_['source_id']) for l_ in BLINKS if l_['source_id'] != ids2([S_BODIES] + ([S_CITYB] if l_['kind'] == 'M' else []))]
    _gonly = {k for k in GOVSRC if k not in reg2.rows}   # Governments-bot ids cited directly (tceq_wdd): checked against the bot's row
    bad += [(k, REG.rows[k], reg2.rows.get(k)) for k in sorted(USED) if (GOVSRC[k] if k in _gonly else reg2.rows.get(k)) != REG.rows[k]]
    same = not bad
    if bad: print('stability mismatches', len(bad), bad[:5])
    _bak = {k: REG.rows.pop(k) for k in list(REG.rows) if k in GOVSRC and (k not in USED or k in _gonly)}
    n = REG.check_ids(); REG.rows.update(_bak); n = f'{n} own + {len(_bak)} Governments-bot'
    print(f'stability test: {n} sources; second build identical: {same}; ids re-derive from url+commit: OK')
    assert same
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
  'district_units_checked': dict(sorted(C.Counter(f"{k[0]}|{k[2]}" for k in UNITS).items())),
  'town_pairs_same_merged': len(pairs_merged), 'town_pairs_same_two_cog_governments': len(pairs_separate_gov),
  'counties_merged_into_city': len(cty_merged),
  'v2_rows': {l: dict(C.Counter(v['resolved'] for v in V2OUT if v['v2_layer'] == l)) for l in sorted({v['v2_layer'] for v in V2OUT})},
  'officeholders': oh_stats,
  'gaps': dict(C.Counter(g['gap'] for g in GAPS)),
  'school_gov_status_fill': dict(SCHFILL), 'governments_ref': GOV_SHA,
  'foreign': dict(FRES['stats'], ref=FOR_SHA, files={f_: v_['sha256'] for f_, v_ in sorted(FOR['files'].items())}, review_status=FRES['review'],
                  gaps_closed=[f"{g['gap']}|{g['key']}" for g in FCLOSED], images_icons=ICONSTAT),
  'special_districts': dict(sorted(SDSTAT.items())),
  'country_layers': dict(LRES['stats'], ref=LOC['commit'], workarounds=LRES['workarounds'], pruned_already_minted=LRES['pruned_already_minted'], files={f_: v_['sha256'] for f_, v_ in sorted(LOC['files'].items())}, areas_set_area_only=LRES['areas'],
                         by_country_kind={f'{c_}|{k_}': n_ for (c_, k_), n_ in sorted(C.Counter((e['entity_id'].split(':')[1][:2], e['kind']) for e in LRES['rows']).items())},
                         gov_status_by_kind={f'{c_}|{k_}|{g_ or "unknown"}': n_ for (c_, k_, g_), n_ in sorted(C.Counter((e['entity_id'].split(':')[1][:2], e['kind'], e['gov_status']) for e in LRES['rows']).items())}),
  'inception': {'rows': sum(1 for e in rows if e.get('inception')), 'by_precision': dict(sorted(C.Counter(e['inception_precision'] for e in rows if e.get('inception')).items())),
                'by_kind': dict(sorted(C.Counter(e['kind'] for e in rows if e.get('inception')).items())), 'valid_from_rows': sum(1 for e in rows if e.get('valid_from'))},
  'images_attribution_filled': dict(sorted(IMGATTR.items())), 'commons_backfill': dict(sorted(CMSTAT.items()), cache_sha256=CM_SHA), 'licence_url': dict(sorted(LICURL.items())), 'image_overrides': IMGOVR, 'licence_url_canonicalised': dict(sorted(LICCAN.items())), 'images_fair_use_missing_field': IMGMISS, 'images_missing_field_all_rows': IMGMISS_ALL,
  'feed_map_by_status': dict(sorted(C.Counter(m['status'] for m in GFMAP).items())),
  'images_by_public_role': dict(sorted(C.Counter(f"{i['public']}|{i['role']}" for i in GIMG).items())),
  'governments_id_registry': {'files': GOVF['registry_files'], 'rows': GOVF['registry_rows_all'], 'domestic_rows': len(GOVF['registry'])},
  'governments_feed': dict(sorted((k, v) for k, v in GSTAT.items())), 'feed_map_rows': len(GFMAP), 'images_rows': len(GIMG),
  'wikidata_filled': sum(1 for e in rows if e['wikidata']),
  'sources': len(REG.rows), 'sources_used_here': len(USED), 'geo_base': GEO_SHA, 'source_urls': len(SU),
  'source_record_id_filled': {'entities': sum(1 for e in rows if e.get('source_record_id')), 'xwalk': sum(1 for x in XW2 if x['source_record_id'])},
  'feed_values': dict(sorted(C.Counter(e['feed'] for e in rows).items())),
  'bodies': dict(BSTAT, seating_ref=SEAT_SHA, files={f_: v_['sha256'] for f_, v_ in sorted(SEAT['files'].items())}, body_entity_rows=len(BLINKS),
                 body_key_gaps=len(BGAPS), courts_minted=sum(1 for e in rows if e['kind'] == 'court'), not_in_seating_charts=[g['key'] for g in SEAT_GAPS],
                 relations=dict(sorted(C.Counter(r['relation'] for r in RELS).items())),
                 entities_without_body=sorted(set(e['entity_id'] for e in rows if e['kind'] in ('chamber', 'dc_council', 'court')) - {l_['entity_id'] for l_ in BLINKS})),
  'world': {'natural_earth': {f_: {'commit': v_['commit'], 'sha256': v_['sha256'], 'rows': len(v_['rows'])} for f_, v_ in sorted(WORLD['ne'].items())},
            'wikidata_retrieved_at': WORLD['retrieved_at'], 'files': WORLD['files'],
            'by_kind': dict(sorted(C.Counter(e['kind'] for e in rows if e['feed'] == 'inst-lane' and e['level'] in ('national', 'subnational')).items())),
            'excluded': [g['key'] for g in WGAPS], 'skipped_us_territory_codes': WORLD['skipped'], 'un_comparison': WORLD['compare']},
}
json.dump(summ, open(os.path.join(OUT, 'entities_summary.json'), 'w'), indent=1)
print(json.dumps(summ, indent=1))
