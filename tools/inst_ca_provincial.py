"""Canada, provincial / territorial level -> data-v3/inst/ca/ (institutions lane). Deterministic; read-only raw inputs.

Entities: one legislature (unicameral chamber) per province / territory, chamber:ca-<iso>-legislature, parent = the province /
territory entity agreed with Full Stack (province:ca-<code> / territory:ca-<code>; minted on data/inst-entities).
Units (not entities): provincial electoral districts (unit_type ped) and provincial polling divisions / voting areas
(unit_type ppoll), keyed by the agency's own codes, from each agency's official boundary file. Attributes only, no geometry.
Provinces / territories without an open structured file are logged in gaps_ca_provincial.csv.
"""
import collections, csv, io, json, glob, re, sys, zipfile, fnmatch
from inst_ca_common import *
import shapefile

OUT = sys.argv[1] if len(sys.argv) > 1 else 'data-v3/inst/ca'
RET = '2026-10-18'
P = RAW + '/prov'
reg = Registry()
def src(slug, name, url, files, lic):
    return reg.add(slug, name, url, lic, RET, '', ';'.join(sha256(f'{P}/{x}') for x in files) if files else '')
def dbf(zpath, glob_, inner=None):
    z = zipfile.ZipFile(zpath)
    if inner: z = zipfile.ZipFile(io.BytesIO(z.read(inner)))
    n = [x for x in z.namelist() if fnmatch.fnmatch(x.lower(), glob_.lower()) and not x.startswith('__MACOSX')]
    assert len(n) == 1, (zpath, n)
    b = z.read(n[0])
    for enc in ('utf-8', 'cp1252'):
        try:
            r = shapefile.Reader(dbf=io.BytesIO(b), encoding=enc, encodingErrors='strict'); f = [x[0] for x in r.fields[1:]]
            return [dict(zip(f, rec)) for rec in r.records()], enc
        except UnicodeDecodeError: continue
    raise ValueError(zpath)

gaps = []
def gap(level, g, key, detail, sid=''): gaps.append({'level': level, 'gap': g, 'key': key, 'detail': detail, 'source_id': sid})
units, ents = [], []
LIC_UNSTATED = 'no licence stated on the agency download page (official public download; only district/poll codes and names are used here)'

def ped(prov, bset, key, name, sid, rec, name_fr='', alias='', attrs='', flags='', gref=''):
    units.append({'boundary_set': bset, 'unit_type': 'ped', 'unit_key': str(key), 'name': name, 'name_fr': name_fr, 'alias': alias,
        'country': 'ca', 'province': prov, 'parent_boundary_set': '', 'parent_unit_key': '', 'entity_id': 'chamber:ca-%s-legislature' % prov.lower(),
        'attrs': attrs, 'source_id': sid, 'source_record_id': rec, 'geometry_ref': gref, 'flags': flags})
def ppoll(prov, bset, pbset, ed, key, name, sid, rec, attrs='', flags='', gref=''):
    units.append({'boundary_set': bset, 'unit_type': 'ppoll', 'unit_key': '%s:%s' % (ed, key), 'name': name, 'name_fr': '', 'alias': '',
        'country': 'ca', 'province': prov, 'parent_boundary_set': pbset, 'parent_unit_key': str(ed), 'entity_id': 'chamber:ca-%s-legislature' % prov.lower(),
        'attrs': attrs, 'source_id': sid, 'source_record_id': rec, 'geometry_ref': gref, 'flags': flags})
def dedupe_polls(rows, keyf, attrf, label):
    """one unit per poll code; shapefile parts of one poll must agree on the attributes kept."""
    g = {}
    for r in rows:
        k = keyf(r); a = attrf(r)
        if k in g and g[k] != a: raise AssertionError((label, k, g[k], a))
        g[k] = a
    return g

CH = {  # official names of the 13 legislatures (unicameral)
 'NL': ('House of Assembly of Newfoundland and Labrador', 'Chambre d\'assemblée de Terre-Neuve-et-Labrador', 'https://www.assembly.nl.ca/'),
 'PE': ('Legislative Assembly of Prince Edward Island', 'Assemblée législative de l\'Île-du-Prince-Édouard', 'https://www.assembly.pe.ca/'),
 'NS': ('Nova Scotia House of Assembly', 'Assemblée législative de la Nouvelle-Écosse', 'https://nslegislature.ca/'),
 'NB': ('Legislative Assembly of New Brunswick', 'Assemblée législative du Nouveau-Brunswick', 'https://www.legnb.ca/'),
 'QC': ('National Assembly of Quebec', 'Assemblée nationale du Québec', 'https://www.assnat.qc.ca/'),
 'ON': ('Legislative Assembly of Ontario', 'Assemblée législative de l\'Ontario', 'https://www.ola.org/'),
 'MB': ('Legislative Assembly of Manitoba', 'Assemblée législative du Manitoba', 'https://www.gov.mb.ca/legislature/'),
 'SK': ('Legislative Assembly of Saskatchewan', 'Assemblée législative de la Saskatchewan', 'https://www.legassembly.sk.ca/'),
 'AB': ('Legislative Assembly of Alberta', 'Assemblée législative de l\'Alberta', 'https://www.assembly.ab.ca/'),
 'BC': ('Legislative Assembly of British Columbia', 'Assemblée législative de la Colombie-Britannique', 'https://www.leg.bc.ca/'),
 'YT': ('Yukon Legislative Assembly', 'Assemblée législative du Yukon', 'https://yukonassembly.ca/'),
 'NT': ('Legislative Assembly of the Northwest Territories', 'Assemblée législative des Territoires du Nord-Ouest', 'https://www.ntassembly.ca/'),
 'NU': ('Legislative Assembly of Nunavut', 'Assemblée législative du Nunavut', 'https://www.assembly.nu.ca/'),
}
ch_src = {}
for p, (en, fr, url) in CH.items():
    ch_src[p] = reg.add('legislature-' + p.lower(), en + ' (official website; cited for the chamber name, not downloaded)', url, 'official legislature website (public record)', '')

seats = {}
# ---- Ontario: Elections Ontario ED shapefile (2022 GE; districts of the Representation Act, 2015 as amended 2017); PDs are limited-use
S = src('eo-ed-2022', 'Elections Ontario, Electoral District Shapefile - 2022 General Election (Open Use Data Product Licence)',
        'https://www.elections.on.ca/content/dam/NGW/sitecontent/2017/preo/shapefiles/Electoral%20District%20Shapefile%20-%202022%20General%20Election.zip',
        ['Electoral_District_Shapefile_-_2022_General_Election.zip'],
        'Elections Ontario Open Use Data Product Licence (worldwide, royalty-free, commercial use allowed, no endorsement) https://www.elections.on.ca/en/voting-in-ontario/electoral-district-shapefiles/open-use-data-product-licence-agreement.html')
rows, enc = dbf(f'{P}/Electoral_District_Shapefile_-_2022_General_Election.zip', '*ELECTORAL_DISTRICT.dbf')
eds = {}
for r in rows: assert eds.setdefault(r['ED_ID'], (r['ENGLISH_NA'], r['FRENCH_NAM'])) == (r['ENGLISH_NA'], r['FRENCH_NAM'])
for k, (e, f) in sorted(eds.items()): ped('ON', 'eo-2022-ed', k, e, S, 'ED_ID=%d' % k, f, gref='Electoral District Shapefile - 2022 General Election.zip:ELECTORAL_DISTRICT')
seats['ON'] = len(eds)
gap('ppoll', 'licence_restricts_redistribution', 'ON', 'Elections Ontario polling-division shapefiles are offered only under the Limited Use Data Product Licence (no redistribution, no derived products); not downloaded, no ON polling-division units', S)

# ---- Quebec: Élections Québec 2026 map (127 circonscriptions, Loi 2026 c. 15) + sections de vote of 2026-07-15
LQC = ('Licence d\'utilisation des données ouvertes du DGEQ (free, worldwide, sublicensable, attribution required) https://www.dgeq.org/licence.html; '
       'NOTE the file metadata says reproduction is allowed except for commercial purposes (electionsquebec.qc.ca/notre-institution/conditions-dutilisation/)')
S = src('eq-ced-2026', 'Élections Québec, données ouvertes: circonscriptions électorales 2026 (shapefile) + liste_circonscriptions2026.csv',
        'https://donnees.electionsquebec.qc.ca/autres/provincial/circonscriptions_electorales_2026_shapefile.zip ; https://donnees.electionsquebec.qc.ca/autres/provincial/liste_circonscriptions2026.csv',
        ['circonscriptions_electorales_2026_shapefile.zip', 'liste_circonscriptions2026.csv'], LQC)
SV = src('eq-sv-2026', 'Élections Québec, données ouvertes: sections de vote 2026 (shapefile, tracé du 15 juillet 2026)',
         'https://donnees.electionsquebec.qc.ca/autres/provincial/sections_vote_2026_shapefile.zip', ['sections_vote_2026_shapefile.zip'], LQC)
rows, enc = dbf(f'{P}/circonscriptions_electorales_2026_shapefile.zip', '*.dbf')
eds = {}
for r in rows: assert eds.setdefault(r['CO_CEP'], r['NM_CEP']) == r['NM_CEP']
lst = {int(r['CODE 2026']): r['CIRCONSCRIPTION 2026'] for r in csv.DictReader(open(f'{P}/liste_circonscriptions2026.csv', encoding='cp1252'), delimiter=';')}
assert set(lst) == set(eds), (len(lst), len(eds))
for k, n in sorted(eds.items()):
    ped('QC', 'eq-2026-ced', k, n, S, 'CO_CEP=%d' % k, n, flags='' if lst[k] == n else 'name_differs_in_liste_csv:' + lst[k].replace(';', ','),
        gref='circonscriptions_electorales_2026_shapefile.zip:Circonscription_electorales_2026_shapefile')
seats['QC'] = len(eds)
rows, enc = dbf(f'{P}/sections_vote_2026_shapefile.zip', '*.dbf')
g = dedupe_polls(rows, lambda r: (r['CO_CEP'], r['NO_SV']), lambda r: (r['CO_UNIQUE'], r['IND_OFF']), 'QC SV')
mun = collections.defaultdict(set)
for r in rows: mun[(r['CO_CEP'], r['NO_SV'])].add((r['CODE_MUNCP'], r['NM_MUNCP'], r['CO_DESIGN']))
for (ed, sv), (cu, off) in sorted(g.items()):
    assert ed in eds and cu == ed * 1000 + sv
    m = sorted(mun[(ed, sv)])
    nm = ('Section %d (%s)' % (sv, ' / '.join(x[1] for x in m))) if (len(m) <= 3 or off == 'O') else 'Section %d (no electors; %d municipalities)' % (sv, len(m))
    ppoll('QC', 'eq-2026-sv', 'eq-2026-ced', ed, sv, nm, SV, 'CO_UNIQUE=%d' % cu,
          'muni_code=%s;muni_name=%s;muni_design=%s;ind_off=%s' % (','.join(str(x[0]) for x in m), ' | '.join(x[1].replace(';', ',') for x in m), ','.join(x[2] for x in m), off),
          ';'.join(x for x in ('' if off == 'O' else 'no_electors:ind_off_N', 'spans_municipalities' if len(m) > 1 else '') if x), 'sections_vote_2026_shapefile.zip:sections_de_vote_15_07_2026_shapefile')
gap('ppoll', 'boundaries_may_change', 'QC', 'Élections Québec: sections de vote of 15 July 2026 "could still change until the 2026 election decree"; re-pull after the 2026 general election', SV)

# ---- Quebec, 2022 general election (3 Oct 2022): 125 circonscriptions (Gazette officielle 22 June 2022, in force from the end of
# the 42nd legislature) + sections de vote as delimited on 28 August 2022 (file metadata). Superseded by the 2026 map (not current).
S22 = src('eq-ced-2022', 'Élections Québec, données ouvertes: circonscriptions électorales 2022 (shapefile; G.O. partie 2, no 25, 22 juin 2022, p. 3465)',
          'https://donnees.electionsquebec.qc.ca/autres/provincial/circonscriptions_electorales_2022_shapefile.zip', ['circonscriptions_electorales_2022_shapefile.zip'], LQC)
SV22 = src('eq-sv-2022', 'Élections Québec, données ouvertes: sections de vote 2022 (shapefile, délimitation du 28 août 2022, élection générale du 3 octobre 2022)',
           'https://donnees.electionsquebec.qc.ca/autres/provincial/sections_vote_2022_shapefile.zip', ['sections_vote_2022_shapefile.zip'], LQC)
rows, enc = dbf(f'{P}/circonscriptions_electorales_2022_shapefile.zip', '*.dbf')
eds22 = {}
for r in rows: assert eds22.setdefault(r['CO_CEP'], r['NM_CEP']) == r['NM_CEP']
assert len(eds22) == 125, len(eds22)
for k, n in sorted(eds22.items()):
    ped('QC', 'eq-2022-ced', k, n, S22, 'CO_CEP=%d' % k, n, gref='circonscriptions_electorales_2022_shapefile.zip:Circonscription_electorale_2022_shapefile',
        flags='' if n in set(eds.values()) else 'name_not_in_2026_map')
assert not set(eds22) & set(eds), 'CO_CEP reused between the 2022 and 2026 maps'
gap('ped', 'superseded_map', 'QC 2022', '2022 map (125 circonscriptions, %d names recur in 2026) is not current: the 2026 map (127) renumbers every CO_CEP, so 2022 and 2026 keys never collide; no 2022->2026 crosswalk built' % len(set(eds22.values()) & set(eds.values())), S22)
rows, enc = dbf(f'{P}/sections_vote_2022_shapefile.zip', '*.dbf')
for r in rows: assert r['NO_SV_VG'] == int(r['NO_SV_VG']), r
g = dedupe_polls(rows, lambda r: (r['CO_CEP_VG'], int(r['NO_SV_VG'])), lambda r: (r['IND_OFF'], r['NM_CEP_VG']), 'QC SV 2022')
mun = collections.defaultdict(set)
for r in rows: mun[(r['CO_CEP_VG'], int(r['NO_SV_VG']))].add((r['CO_MUNCP'], r['NM_MUNCP'], r['CO_DESIGN']))
for (ed, sv), (off, en) in sorted(g.items()):
    assert eds22[ed] == en, (ed, en)
    m = sorted(mun[(ed, sv)])
    nm = ('Section %d (%s)' % (sv, ' / '.join(x[1] for x in m))) if (len(m) <= 3 or off == 'O') else 'Section %d (no electors; %d municipalities)' % (sv, len(m))
    ppoll('QC', 'eq-2022-sv', 'eq-2022-ced', ed, sv, nm, SV22, 'CO_CEP_VG=%d;NO_SV_VG=%d' % (ed, sv),
          'muni_code=%s;muni_name=%s;muni_design=%s;ind_off=%s' % (','.join(str(x[0]) for x in m), ' | '.join(x[1].replace(';', ',') for x in m), ','.join(x[2] for x in m), off),
          ';'.join(x for x in ('' if off == 'O' else 'no_electors:ind_off_N', 'spans_municipalities' if len(m) > 1 else '') if x), 'sections_vote_2022_shapefile.zip:Section_de_vote')

# ---- British Columbia: BC Geographic Warehouse (Elections BC), 2023 redistribution EDs + voting areas gazetted 2024-09-19
LBC = 'Elections BC Open Data Licence (BC Data Catalogue)'
B = 'https://delivery.maps.gov.bc.ca/arcgis/rest/services/whse/bcgw_pub_whse_admin_boundaries/MapServer'
S = src('ebc-ed-2023', 'Elections BC / BC Geographic Warehouse, Provincial Electoral Districts - Electoral Boundaries Redistribution, 2023 (WHSE_ADMIN_BOUNDARIES.EBC_ELECTORAL_DISTS_BS11_SVW), attributes via ArcGIS REST layer 74',
        B + '/74/query?where=1%3D1&outFields=ED_NAME,ED_ABBREVIATION,GAZETTE_DATE,ELECTORAL_DISTRICT_ID,BOUNDARY_SET_ID&returnGeometry=false&orderByFields=ELECTORAL_DISTRICT_ID&f=json',
        ['bc_ed_2023.json'], LBC + ' https://catalogue.data.gov.bc.ca/dataset/1cba4b16-263f-4d42-8d84-f5fecaa03d1a')
VA = src('ebc-va-2024', 'Elections BC / BC Geographic Warehouse, Provincial Electoral District Voting Areas - Gazetted 09-19-2024 (WHSE_ADMIN_BOUNDARIES.EBC_VOTING_AREAS_BS11_POLY_SVW), attributes via ArcGIS REST layer 73 (6 pages of 1000)',
         B + '/73/query?where=1%3D1&returnGeometry=false&orderByFields=VOTING_AREA_POLY_ID&f=json',
         ['bc_va_%d.json' % o for o in range(0, 6000, 1000)], LBC + ' https://catalogue.data.gov.bc.ca/dataset/2a73ba6d-0707-4335-9f4f-7f8a6d922654')
e = [f['attributes'] for f in json.load(open(f'{P}/bc_ed_2023.json'))['features']]
eds = {r['ED_ABBREVIATION']: r for r in e}; assert len(eds) == len(e) == 93
for k, r in sorted(eds.items()):
    ped('BC', 'ebc-2023-ed', k, r['ED_NAME'], S, 'ELECTORAL_DISTRICT_ID=%d' % r['ELECTORAL_DISTRICT_ID'], attrs='ed_id=%d;boundary_set_id=%d' % (r['ELECTORAL_DISTRICT_ID'], r['BOUNDARY_SET_ID']),
        gref='BCGW WHSE_ADMIN_BOUNDARIES.EBC_ELECTORAL_DISTS_BS11_SVW')
seats['BC'] = len(eds)
va = []
for o in range(0, 6000, 1000): va += [f['attributes'] for f in json.load(open(f'{P}/bc_va_{o}.json'))['features']]
assert len({v['VOTING_AREA_POLY_ID'] for v in va}) == len(va) == 5778
g = dedupe_polls(va, lambda r: (r['ED_ABBREVIATION'], r['VA_CODE']), lambda r: (r['EDVA_CODE'], r['VA_TYPE']), 'BC VA')
for (ed, c), (code, t) in sorted(g.items()):
    assert ed in eds and code == ed + c
    ppoll('BC', 'ebc-2024-va', 'ebc-2023-ed', ed, c, 'Voting area %s' % code, VA, 'EDVA_CODE=' + code, 'va_type=' + t.lower(), gref='BCGW WHSE_ADMIN_BOUNDARIES.EBC_VOTING_AREAS_BS11_POLY_SVW')

# ---- Alberta: Elections Alberta 2019 boundaries (87 EDs, Bill 33 of 2017) + voting areas 2026
S = src('ea-ed-2019', 'Elections Alberta, 2019 Boundaries electoral division shapefiles (EDS_ENACTED_BILL33_15DEC2017)',
        'https://www.elections.ab.ca/uploads/2019Boundaries_ED-Shapefiles.zip', ['2019Boundaries_ED-Shapefiles.zip'], LIC_UNSTATED)
VA = src('ea-va-2026', 'Elections Alberta, Voting Area Boundaries 2026 (EA_Voting_Area_Boundaries_2026)',
         'https://www.elections.ab.ca/uploads/EA_Voting_Area_Boundaries_2026.zip', ['EA_Voting_Area_Boundaries_2026.zip'], LIC_UNSTATED)
rows, _ = dbf(f'{P}/2019Boundaries_ED-Shapefiles.zip', '*.dbf')
eds = {}
for r in rows: assert eds.setdefault(int(r['EDNumber20']), r['EDName2017']) == r['EDName2017']
var, _ = dbf(f'{P}/EA_Voting_Area_Boundaries_2026.zip', '*.dbf')
n26 = {}
for r in var: assert n26.setdefault(int(r['ED_NUM']), r['ED_NAME']) == r['ED_NAME']
assert set(n26) == set(eds) and len(eds) == 87
for k in sorted(eds):
    cur = n26[k]
    ped('AB', 'ea-2019-ed', k, cur, S + ';' + VA, 'EDNumber20=%d' % k, alias='' if cur == eds[k] else eds[k],
        flags='' if cur == eds[k] else 'renamed_since_2017_act', gref='2019Boundaries_ED-Shapefiles.zip:EDS_ENACTED_BILL33_15DEC2017')
seats['AB'] = len(eds)
g = dedupe_polls(var, lambda r: (int(r['ED_NUM']), r['VA_NUMBER']), lambda r: (), 'AB VA')
for (ed, v) in sorted(g): ppoll('AB', 'ea-2026-va', 'ea-2019-ed', ed, v, 'Voting area %s' % v, VA, 'ED_NUM=%d;VA_NUMBER=%s' % (ed, v), gref='EA_Voting_Area_Boundaries_2026.zip:EA_Voting_Area_Boundaries_2026')
gap('ppoll', 'not_the_2023_ge_voting_areas', 'AB', 'EA_Voting_Area_Boundaries_2026: files dated 2026-09-23, the only VA file on elections.ab.ca/resources/maps (page modified 2026-09-24); same 87-ED map as the 2023 general election (2017 Electoral Divisions Act, Bill 33, in force 2019-03-19; ED 17 now Calgary-Bhullar-McCall), but the voting areas are the 2026 revision; the 2023 GE voting-area file is not published there (uploads/*2023* VA names 404). Do not join 2023 poll results to these units without checking', VA)
gap('ped', 'next_boundaries_not_loaded', 'AB', 'Electoral Boundaries Commission final report (2026-03-23) proposes 89 divisions for the next election; no official shapefile found; current 87 loaded', S)

# ---- Manitoba: Elections Manitoba 2018 final boundaries (57 EDs, rural + Winnipeg files) + voting areas 2023
S = src('em-ed-2018', 'Elections Manitoba, 2018 final electoral division boundaries (EDBC2018 rural + Winnipeg shapefiles)',
        'https://www.electionsmanitoba.ca/downloads/2018_Final_ED_Manitoba_Public_Urban.zip ; https://www.electionsmanitoba.ca/downloads/2018_Final_ED_Winnipeg_Public_Urban.zip',
        ['2018_Final_ED_Manitoba_Public_Urban.zip', '2018_Final_ED_Winnipeg_Public_Urban.zip'], LIC_UNSTATED)
VA = src('em-va-2023', 'Elections Manitoba, voting areas 2023 general election (VA_MB2023_public)', 'https://www.electionsmanitoba.ca/downloads/VA_MB2023_public.zip', ['VA_MB2023_public.zip'], LIC_UNSTATED)
r1, _ = dbf(f'{P}/2018_Final_ED_Manitoba_Public_Urban.zip', '*.dbf'); r2, _ = dbf(f'{P}/2018_Final_ED_Winnipeg_Public_Urban.zip', '*.dbf')
bnames = {norm_name(r['ED']) for r in r1 + r2}
var, _ = dbf(f'{P}/VA_MB2023_public.zip', '*.dbf')
eds = {}
for r in var: assert eds.setdefault(r['EDNUM'], (r['EDNAMEEN'], r['EDNAMEFR'])) == (r['EDNAMEEN'], r['EDNAMEFR'])
assert len(eds) == 57
for k, (en, fr) in sorted(eds.items()):
    ped('MB', 'em-2018-ed', k, en, VA + ';' + S, 'EDNUM=%d' % k, fr, flags='' if norm_name(en) in bnames else 'name_not_in_2018_boundary_file',
        gref='2018_Final_ED_*_Public_Urban.zip:EDBC2018_FinalBoundaries_(Rural|Winnipeg) (by name; that file has no ED number)')
seats['MB'] = len(eds)
g = dedupe_polls(var, lambda r: (r['EDNUM'], r['VANUM']), lambda r: (), 'MB VA')
for (ed, v) in sorted(g, key=lambda x: (x[0], int(re.sub(r'\D', '', x[1]) or 0), x[1])):
    ppoll('MB', 'em-2023-va', 'em-2018-ed', ed, v, 'Voting area %s' % v, VA, 'EDNUM=%d;VANUM=%s' % (ed, v), gref='VA_MB2023_public.zip:VA_MB2023_public')
gap('ppoll', 'by_election_voting_areas_not_loaded', 'MB', 'Elections Manitoba also publishes by-election voting-area files (Fort Whyte, Kirkfield Park, Thompson, Tuxedo, Transcona 2025, Spruce Woods 2025, The Pas-Kameesak 2026); only the 2023 general-election set is loaded', VA)

# ---- Saskatchewan: Elections Saskatchewan GE30 (2024) constituencies + voting areas (zip inside zip)
S = src('esk-ge30-shp', 'Elections Saskatchewan, KML and shapefiles for the 30th General Election (Constituency30th, VotingAreas_30thGE)',
        'https://cdn.elections.sk.ca/maps-ge30/ESK_KML_Shape_Files_Mar2024.zip', ['ESK_KML_Shape_Files_Mar2024.zip'], LIC_UNSTATED)
Z = f'{P}/ESK_KML_Shape_Files_Mar2024.zip'
rows, _ = dbf(Z, '*.dbf', 'ShapeFile/Constituency/Constituency30th.zip')
eds = {}
for r in rows: assert eds.setdefault(r['Constitu_1'], (r['Constituen'], r['Constitu_2'])) == (r['Constituen'], r['Constitu_2'])
assert len(eds) == 61
for k, (n, c) in sorted(eds.items()): ped('SK', 'esk-2022-ed', k, n, S, 'Constituency number=%d' % k, attrs='code=' + c, gref='Constituency30th.zip:ConstituencyGE30th')
seats['SK'] = len(eds)
rows, _ = dbf(Z, '*.dbf', 'ShapeFile/Voting Areas/VotingAreas_30thGE.zip')
g = dedupe_polls(rows, lambda r: (r['ConNumber'], r['VACode']), lambda r: (r['VANumber'], r['VAType'], r['ConCode']), 'SK VA')
for (ed, code), (num, t, cc) in sorted(g.items()):
    assert ed in eds and eds[ed][1] == cc
    ppoll('SK', 'esk-2024-va', 'esk-2022-ed', ed, code, 'Voting area %s' % code, S, 'VACode=' + code, 'va_number=%s;va_type=%s' % (num, {'R': 'rural', 'U': 'urban'}.get(t, t)),
          gref='VotingAreas_30thGE.zip:VotingAreas_30thGE')

# ---- New Brunswick: GeoNB Polling Divisions - Provincial, Current (2024) (Socrata CSV; carries PED number + names)
LNB = 'Open Government Licence - New Brunswick (https://www.gnb.ca/en/campaign/geonb/open-government-license.html)'
S = src('geonb-ppd-2024', 'Government of New Brunswick / GeoNB (Elections NB), Polling Divisions - Provincial, Current (2024), open.canada.ca 38f78a2f-cb64-2b7f-ddfc-c085f83664ec (CSV export)',
        'https://gnb.socrata.com/api/views/s8s4-3dia/rows.csv?accessType=DOWNLOAD', ['nb_ppd_2024.csv'], LNB)
csv.field_size_limit(10 ** 9)
rows = list(csv.DictReader(open(f'{P}/nb_ppd_2024.csv', encoding='utf-8-sig')))
eds = {}
for r in rows: assert eds.setdefault(int(r['PED']), (r['PED_Names_'], r['PED_Names1'])) == (r['PED_Names_'], r['PED_Names1'])
assert len(eds) == 49
for k, (en, fr) in sorted(eds.items()):
    ped('NB', 'enb-2024-ed', k, en, S, 'PED=%d' % k, fr, flags='ed_list_derived_from_polling_division_file', gref='GeoNB geonb_2024_ppd_svp (dissolve by PED)')
seats['NB'] = len(eds)
g = dedupe_polls(rows, lambda r: (int(r['PED']), int(r['ProvPoll'])), lambda r: (r['ProPollPad'], r['Date']), 'NB PD')
for (ed, pn), (pad, d) in sorted(g.items()):
    ppoll('NB', 'enb-2024-pd', 'enb-2024-ed', ed, pn, 'Poll %s' % pad, S, 'PED=%d;ProvPoll=%d' % (ed, pn), 'file_date=' + d.split(' ')[0], gref='GeoNB geonb_2024_ppd_svp')

# ---- Prince Edward Island: Government of PEI GIS, Provincial Electoral Wards and Polls (REST layer 0, attributes)
LPE = 'Government of Prince Edward Island open data (reuse and redistribution permitted; Elections PEI Open Data Standards https://www.electionspei.ca/open-data-standards)'
S = src('pei-wards-polls', 'Government of PEI GIS, Provincial_Electoral_Wards_and_Polls MapServer layer 0 (attributes via ArcGIS REST)',
        'https://gis.princeedwardisland.ca/server/rest/services/Provincial_Electoral_Wards_and_Polls/MapServer/0/query?where=1%3D1&outFields=*&returnGeometry=false&f=json',
        ['pe_polls.json'], LPE)
rows = [f['attributes'] for f in json.load(open(f'{P}/pe_polls.json'))['features']]
blank = [r for r in rows if not r['DIST_NO']]; rows = [r for r in rows if r['DIST_NO']]
gap('ppoll', 'blank_records_skipped', 'PE', '%d features with DIST_NO 0, empty DISTRICT/POLL_NAME and AREA_SQM 0 skipped' % len(blank), S)
dn = collections.defaultdict(set)
for r in rows: dn[r['DIST_NO']].add(r['DISTRICT'].strip())
assert len(dn) == 27
for k in sorted(dn):
    names = sorted(dn[k], key=lambda s: (-sum(1 for r in rows if r['DIST_NO'] == k and r['DISTRICT'].strip() == s), s))
    ped('PE', 'epei-2017-ed', k, names[0], S, 'DIST_NO=%d' % k, alias=';'.join(names[1:]).replace(';', ' | '),
        flags='ed_list_derived_from_poll_layer' + (';district_name_variants_in_poll_layer' if len(names) > 1 else ''), gref='Provincial_Electoral_Wards_and_Polls layer 0 (dissolve by DIST_NO)')
seats['PE'] = len(dn)
pg = collections.defaultdict(set)
for r in rows: pg[(r['DIST_NO'], r['POLL_NO'])].add((r['POLL_NAME'] or '').strip())
for (ed, pn), nm in sorted(pg.items()):
    nm = sorted(nm)
    ppoll('PE', 'epei-2017-poll', 'epei-2017-ed', ed, pn, nm[0] if len(nm) == 1 else '', S, 'DIST_NO=%d;POLL_NO=%d' % (ed, pn),
          flags='' if len(nm) == 1 else 'poll_name_ambiguous:' + ','.join(nm), gref='Provincial_Electoral_Wards_and_Polls layer 0')
gap('ppoll', 'vintage_not_stated', 'PE', 'PEI GIS layer gives no boundary date; the 27 districts are those recommended in 2017 (used 2019, 2023); polls loaded as epei-2017-poll; verify against Elections PEI poll maps', S)

# ---- Newfoundland and Labrador: Elections NL polls April 2019 (40 districts)
S = src('enl-polls-2019', 'Elections Newfoundland and Labrador, GIS data: NL Polls (2019) (OCEO_Polls_April_2019)', 'https://www.elections.gov.nl.ca/files/NL-Polls-2019.zip', ['NL-Polls-2019.zip'], LIC_UNSTATED)
rows, _ = dbf(f'{P}/NL-Polls-2019.zip', '*.dbf')
eds = {}
for r in rows: assert eds.setdefault(int(r['District']), r['District_N']) == r['District_N']
assert len(eds) == 40
for k, n in sorted(eds.items()): ped('NL', 'enl-2015-ed', k, n, S, 'District=%d' % k, flags='ed_list_derived_from_poll_file', gref='NL-Polls-2019.zip:OCEO_Polls_April_2019 (dissolve by District)')
seats['NL'] = len(eds)
g = collections.defaultdict(set)
for r in rows: g[(int(r['District']), r['DistPoll'])].add(int(r['Poll']))
for (ed, dp), pn in sorted(g.items(), key=lambda x: (x[0][0], [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', x[0][1])])):
    assert dp.split('-')[0] == str(ed)
    ppoll('NL', 'enl-2019-poll', 'enl-2015-ed', ed, dp.split('-', 1)[1], 'Poll %s' % dp, S, 'DistPoll=' + dp, flags='vintage_2019:check_against_ge2025_polls')
gap('ppoll', 'vintage_older_than_last_election', 'NL', 'Elections NL GIS page offers the April 2019 poll file only; the 2021 and 2025 general elections may have used revised polls (Open Data NL mentioned as access route)', S)

# ---- not built
for p, why in [('NS', 'Elections Nova Scotia publishes the 55 districts as PDF maps and an online lookup (enstools.electionsnovascotia.ca/edinfo); no open shapefile/CSV of districts or polling divisions found'),
               ('YT', 'Elections Yukon: no open structured district / polling-division file found in this pass'),
               ('NT', 'Elections NWT: no open structured district / polling-division file found in this pass'),
               ('NU', 'Elections Nunavut: no open structured constituency / polling-division file found in this pass')]:
    gap('ped', 'no_open_structured_source_found', p, why, ch_src[p])
for p in CH:
    if p not in seats: continue
gap('officeholder', 'provincial_members_not_built', 'all', 'MLAs / MNAs / MPPs / MHAs are not loaded in this batch (each legislature publishes a member list; OpenStates does not cover Canada)', '')

for p, (en, fr, url) in sorted(CH.items(), key=lambda x: ISO2SGC[x[0]]):
    ents.append({'entity_id': 'chamber:ca-%s-legislature' % p.lower(), 'kind': 'chamber', 'name': en, 'name_fr': fr, 'parent_id': prov_entity(p),
        'source_id': ';'.join([ch_src[p]] + sorted({u['source_id'].split(';')[0] for u in units if u['province'] == p and u['unit_type'] == 'ped'})),
        'feed': 'inst-lane', 'level': 'province' if p not in CA_TERR else 'territory', 'type': 'unicameral',
        'flags': 'gov_status_na:legislative_chamber' + ((';seats:%d' % seats[p]) if p in seats else ';no_electoral_units_loaded') + (';consensus_government_no_parties' if p in ('NT', 'NU') else ''),
        'country': 'ca', 'province': p, 'external_id': ''})

os.makedirs(OUT, exist_ok=True)
nat = lambda s: [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]
ukey = lambda r: (ISO2SGC[r['province']], r['boundary_set'], r['unit_type'], nat(r['unit_key']))
counts = {
 'entities_ca_provincial.csv': write_csv(f'{OUT}/entities_ca_provincial.csv', ENTITY_COLS, ents, key=lambda r: r['entity_id']),
 'units_ca_ped.csv': write_csv(f'{OUT}/units_ca_ped.csv', UNIT_COLS, [u for u in units if u['unit_type'] == 'ped'], key=ukey),
 'units_ca_ppoll.csv': write_csv(f'{OUT}/units_ca_ppoll.csv', UNIT_COLS, [u for u in units if u['unit_type'] == 'ppoll'], key=ukey),
 'gaps_ca_provincial.csv': write_csv(f'{OUT}/gaps_ca_provincial.csv', GAP_COLS, gaps, key=lambda r: (r['level'], r['gap'], r['key'])),
}
reg.check_ids()
write_csv(f'{OUT}/sources_ca_provincial.csv', SOURCE_COLS, list(reg.rows.values()), key=lambda r: r['source_id'])
by = collections.Counter((u['province'], u['boundary_set'], u['unit_type']) for u in units)
write_json(f'{OUT}/summary_ca_provincial.json', {'rows': counts, 'sources': len(reg.rows), 'retrieved_at': RET, 'seats_loaded': seats,
 'units_by_set': {'%s %s %s' % k: v for k, v in sorted(by.items())}, 'provinces_without_units': sorted(set(CH) - set(seats))})
print(counts); print(json.dumps({'%s %s %s' % k: v for k, v in sorted(by.items())}, indent=0))
