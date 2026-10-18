"""Canada, federal level -> data-v3/inst/ca/ (institutions lane). Deterministic; read-only inputs under /workspace/w/inst-raw/ca.

Entities: chamber:ca-house, chamber:ca-senate (parent nation:ca; nation:ca itself is built on data/inst-entities).
Units (not entities): FEDs of the 2023 Representation Order (boundary_set ec-2023-fed, 343) and of the 2013 order
(ec-2013-fed, 338); Elections Canada polling divisions of GE45 2025 (ec-2025-pd), GE44 2021 (ec-2021-pd), GE43 2019 (ec-2019-pd),
keyed '<FED_NUM>:<PD_NUM>-<SFX>' with the FED as parent. Geometry stays in the raw shapefiles (geometry_ref only).
Officeholders: current MPs from ourcommons.ca (person_id ca-mp:<PersonId>), vacancies as status 'vacant'.
Poll names: the poll-by-poll results files give the polling-division name; only the name is read here (results = Election bot).
"""
import collections, csv, io, re, sys, zipfile, xml.etree.ElementTree as ET
from inst_ca_common import *

OUT = sys.argv[1] if len(sys.argv) > 1 else 'data-v3/inst/ca'
RET = '2026-10-18'
reg = Registry()
def src(slug, name, url, f=None, lic=OGL_CA):
    return reg.add(slug, name, url, lic, RET, '', ';'.join(sha256(f'{RAW}/{x}') for x in (f if isinstance(f, list) else [f])) if f else '')

S_FED23 = src('ec-fed-2023-edb', 'Elections Canada, Federal Electoral Districts - Canada 2023 (2023 Representation Order; names updated by An Act to change the names of certain electoral districts, 2026 / Bill C-25), FederalElectoralDistricts_SHP.zip, open.canada.ca 18bf3ea7-1940-46ec-af52-9ba3f77ed708',
              'https://www.elections.ca/res/cir/mapsCorner/edb/FederalElectoralDistricts_SHP.zip', 'FederalElectoralDistricts_SHP.zip')
S_GE45 = src('ec-ge45-boundaries', 'Elections Canada, Electoral Geography Boundary Files (45th General Election) - Canada 2025: Federal Electoral Districts + Polling Division boundaries (SHP), open.canada.ca 97a2a33c-54cc-4f2e-82c1-047ad8212f05',
             'https://www.elections.ca/res/cir/mapsCorner/vector/FederalElectoralDistricts_2025_SHP.zip ; https://www.elections.ca/res/cir/mapsCorner/vector/PollingDivisionBoundaries_2025_SHP.zip',
             ['FederalElectoralDistricts_2025_SHP.zip', 'PollingDivisionBoundaries_2025_SHP.zip'])
S_GE44 = src('ec-ge44-boundaries', 'Elections Canada, Polling Division Boundaries - Canada 2021 (44th General Election, 2013 Representation Order): FED_CA_2021_EN + PD_CA_2021_EN (SHP), open.canada.ca 0ed37cd6-d831-4183-bf43-b05e29570298',
             'https://ftp.maps.canada.ca/pub/elections_elections/Electoral-districts_Circonscription-electorale/Elections_Canada_2021/FED_CA_2021_EN.zip ; https://ftp.maps.canada.ca/pub/elections_elections/Electoral-districts_Circonscription-electorale/Elections_Canada_2021/PD_CA_2021_EN.zip',
             ['FED_CA_2021_EN.zip', 'PD_CA_2021_EN.zip'])
S_GE43 = src('ec-ge43-boundaries', 'Elections Canada, Polling Division Boundaries - Canada 2019 (43rd General Election, 2013 Representation Order): FED_CA_2019_EN + PD_CA_2019_EN (SHP)',
             'https://ftp.maps.canada.ca/pub/elections_elections/Electoral-districts_Circonscription-electorale/Elections_Canada_2019/federal_electoral_districts_boundaries_2019.shp.zip ; https://ftp.maps.canada.ca/pub/elections_elections/Electoral-districts_Circonscription-electorale/Elections_Canada_2019/polling_divisions_boundaries_2019.shp.zip',
             ['federal_electoral_districts_boundaries_2019.shp.zip', 'polling_divisions_boundaries_2019.shp.zip'])
S_PR = {45: src('ec-ge45-pollresults', 'Elections Canada, 45th General Election: Official Voting Results (raw data), poll-by-poll Format 2, Canada (polling-division names only read here)',
                'https://www.elections.ca/res/rep/off/ovrGE45/62/data_donnees/pollresults_resultatsbureauCanada.zip', 'ge45_pollresults_Canada.zip'),
        44: src('ec-ge44-pollresults', 'Elections Canada, 44th General Election: Official Voting Results (raw data), poll-by-poll Format 2, Canada (polling-division names only read here)',
                'https://www.elections.ca/res/rep/off/ovr2021app/53/data_donnees/pollresults_resultatsbureauCanada.zip', 'ge44_pollresults_Canada.zip'),
        43: src('ec-ge43-pollresults', 'Elections Canada, 43rd General Election: Official Voting Results (raw data), poll-by-poll Format 2, Canada (polling-division names only read here)',
                'https://www.elections.ca/res/rep/off/ovr2019app/51/data_donnees/pollresults_resultatsbureauCanada.zip', 'ge43_pollresults_Canada.zip')}
S_MPS = src('ourcommons-members', 'House of Commons of Canada, Members of Parliament search export (XML), current members',
            'https://www.ourcommons.ca/Members/en/search/xml', 'mps.xml',
            'House of Commons website content (Copyright Act; "permission to reproduce ... may be sought", https://www.ourcommons.ca/en/important-notices). Only factual fields are used (PersonId, name, constituency, caucus, dates); no licence grant for commercial reuse found')
S_CONST = reg.add('ca-constitution-1867', 'Constitution Act, 1867 (Justice Laws Website), ss. 17, 21-22, 37 (Parliament: Senate and House of Commons); cited, not downloaded',
              'https://laws-lois.justice.gc.ca/eng/const/page-1.html', 'Reproduction of federal law permitted (Reproduction of Federal Law Order, SI/97-5)', '', '', '')

gaps = []
def gap(level, g, key, detail, sid=''): gaps.append({'level': level, 'gap': g, 'key': key, 'detail': detail, 'source_id': sid})

def clean_dup(s):
    """ED_CF.dbf (2026 edb file) repeats some names as 'X,X[,X...]' (multipart rows merged into one): keep X when all parts agree."""
    parts = s.split(',')
    return parts[0] if len(parts) > 1 and all(parts[0].startswith(x) for x in parts[1:]) else s   # last copy may be cut at the DBF field width

# ---------------- FED units ----------------
units_fed = []
f25, _ = dbf_rows(f'{RAW}/FederalElectoralDistricts_2025_SHP.zip', '*FED_CA_2025_EN.dbf')
fcur, _ = dbf_rows(f'{RAW}/FederalElectoralDistricts_SHP.zip', '*ED_CF.dbf')
f21, _ = dbf_rows(f'{RAW}/FED_CA_2021_EN.zip', '*FED_CA_2021_EN.dbf')
f19, _ = dbf_rows(f'{RAW}/federal_electoral_districts_boundaries_2019.shp.zip', '*FED_CA_2019_EN.dbf')
n25 = {}
for r in f25: n25.setdefault(r['FED_NUM'], set()).add((r['ED_NAMEE'], r['ED_NAMEF'], r['REPORDER']))
assert all(len(v) == 1 for v in n25.values()), 'FED_CA_2025 multipart rows disagree'
ncur = {}
for r in fcur: ncur.setdefault(r['ED_CF_NUM'], set()).add((clean_dup(r['ED_NAMEE']), clean_dup(r['CF_NOMF'])))
assert set(n25) == set(ncur) and len(n25) == 343, (len(n25), len(ncur))
renamed = 0
fed23 = {}
for k in sorted(n25):
    (e25, f25n, ro), = n25[k]; (ec, fc), = ncur[k]
    assert ro == '2023'
    if ec != e25: renamed += 1
    p = SGC[str(k)[:2]]
    fed23[k] = ec
    units_fed.append({'boundary_set': 'ec-2023-fed', 'unit_type': 'fed', 'unit_key': str(k), 'name': ec, 'name_fr': fc,
        'alias': '' if ec == e25 else e25, 'country': 'ca', 'province': p, 'parent_boundary_set': '', 'parent_unit_key': '',
        'entity_id': 'chamber:ca-house', 'attrs': 'rep_order=2023' + ('' if ec == e25 else ';name_at_ge45_2025=' + e25.replace(';', ',')),
        'source_id': S_FED23 + ';' + S_GE45, 'source_record_id': 'FED_NUM=%d' % k,
        'geometry_ref': 'FederalElectoralDistricts_SHP.zip:ED_CF (ED_CF_NUM=%d); FederalElectoralDistricts_2025_SHP.zip:FED_CA_2025_EN (FED_NUM=%d)' % (k, k),
        'flags': '' if ec == e25 else 'renamed_after_ge45:bill_c25_2026'})
n21 = {}
for r in f21: n21.setdefault(r['FED_NUM'], set()).add((r['ED_NAMEE'], r['ED_NAMEF'], r['REPORDER']))
n19 = {r['FEDNUM']: (r['ENNAME'], r['FRNAME'], r['PROVCODE'], r['REPORDER']) for r in f19}
assert set(n21) == set(n19) and len(n21) == 338 and all(len(v) == 1 for v in n21.values())
fed13 = {}
for k in sorted(n21):
    (e, fr, ro), = n21[k]; e19, fr19, pc, ro19 = n19[k]
    assert ro == ro19 == '2013' and SGC[str(k)[:2]] == pc
    fed13[k] = e
    al = '' if norm_name(e19) == norm_name(e) else e19
    units_fed.append({'boundary_set': 'ec-2013-fed', 'unit_type': 'fed', 'unit_key': str(k), 'name': e, 'name_fr': fr, 'alias': al,
        'country': 'ca', 'province': pc, 'parent_boundary_set': '', 'parent_unit_key': '', 'entity_id': 'chamber:ca-house',
        'attrs': 'rep_order=2013;used_in=ge42_2015,ge43_2019,ge44_2021', 'source_id': S_GE44 + ';' + S_GE43, 'source_record_id': 'FED_NUM=%d' % k,
        'geometry_ref': 'FED_CA_2021_EN.zip:FED_CA_2021_EN (FED_NUM=%d); federal_electoral_districts_boundaries_2019.shp.zip:FED_CA_2019_EN (FEDNUM=%d)' % (k, k),
        'flags': ''})

# ---------------- poll names from the results files (name only) ----------------
def poll_names(zname):
    z = zipfile.ZipFile(f'{RAW}/{zname}'); names = collections.defaultdict(set)
    for nm in sorted(z.namelist()):
        rd = csv.reader(io.StringIO(z.read(nm).decode('utf-8'))); next(rd)
        for r in rd:
            st = r[3].strip()
            m = re.fullmatch(r'(\d+)(?:-(\d+))?([A-Z]*)', st)
            if not m: continue                             # 'S/R 1' special voting rules: no polygon
            names[(int(r[0]), int(m.group(1)), int(m.group(2) or 0))].add(r[4].strip())
    return names

# ---------------- polling divisions ----------------
PDT = {'N': 'normal', 'S': 'single_building', 'M': 'mobile'}
def pd_units(zname, glob, bset, parent_bset, fedset, sids, ge, f):
    rows, member = dbf_rows(f'{RAW}/{zname}', glob)
    g = {}; fixed = set(); fileside = collections.defaultdict(set)
    for r in rows:
        fed, num, sfx, typ, adv = f(r)
        key = (fed, num, sfx)
        if r.get('POLLNAME'): fileside[key].add(r['POLLNAME'].strip())
        old = g.setdefault(key, (typ, adv))
        if old != (typ, adv):
            assert old[0] == typ and '' in (old[1], adv), ('PD attributes disagree across parts', bset, key, old, (typ, adv))
            g[key] = (typ, old[1] or adv); fixed.add(key)
    names = poll_names({45: 'ge45_pollresults_Canada.zip', 44: 'ge44_pollresults_Canada.zip', 43: 'ge43_pollresults_Canada.zip'}[ge])
    out = []; st = collections.Counter()
    for (fed, num, sfx), (typ, adv) in sorted(g.items()):
        assert fed in fedset, (bset, fed)
        nm = names.get((fed, num, sfx), set()); fl = []; via_file = False
        if not nm and len(fileside.get((fed, num, sfx), ())) == 1: nm = fileside[(fed, num, sfx)]; via_file = True; fl.append('poll_name_from_boundary_file')
        if (fed, num, sfx) in fixed: fl.append('adv_poll_empty_on_some_shapefile_parts')
        MOB = 'Mobile poll/Bureau itinérant'
        if len(nm) > 1 and MOB in nm and len(nm - {MOB}) == 1: nm = nm - {MOB}; fl.append('poll_name_ignores_mobile_station'); st['named_ignoring_mobile_station'] += 1
        if len(nm) == 1: name = next(iter(nm)); st['named'] += 1
        elif len(nm) > 1: name = ''; fl.append('poll_name_ambiguous_in_results'); st['name_ambiguous'] += 1
        else: name = ''; fl.append('poll_name_not_in_results'); st['no_name'] += 1
        if typ not in PDT: fl.append('pd_type_unknown:' + typ)
        k = '%d:%d-%d' % (fed, num, sfx)
        out.append({'boundary_set': bset, 'unit_type': 'poll', 'unit_key': k, 'name': name, 'name_fr': '', 'alias': '',
            'country': 'ca', 'province': SGC[str(fed)[:2]], 'parent_boundary_set': parent_bset, 'parent_unit_key': str(fed),
            'entity_id': 'chamber:ca-house',
            'attrs': 'pd_num=%d;pd_sfx=%d;pd_type=%s;adv_poll=%s' % (num, sfx, PDT.get(typ, typ), adv),
            'source_id': ';'.join(sids + ([S_PR[ge]] if name and not via_file else [])), 'source_record_id': 'FED_NUM=%d;PD_NUM=%d;PD_NBR_SFX=%d' % (fed, num, sfx),
            'geometry_ref': '%s:%s' % (zname, member.rsplit('/', 1)[-1][:-4]), 'flags': ';'.join(fl)})
    feds_with_pd = {fed for fed, _, _ in g}
    for fed in sorted(fedset - feds_with_pd): gap('poll', 'fed_without_polling_divisions', '%s:%d' % (bset, fed), 'no PD polygon in the boundary file', sids[0])
    if st['no_name']: gap('poll', 'poll_name_not_in_results', bset, '%d polling divisions have a polygon but no row in the GE%d poll-by-poll file (e.g. combined/void or merged polls); name left empty' % (st['no_name'], ge), S_PR[ge])
    if st['name_ambiguous']: gap('poll', 'poll_name_ambiguous_in_results', bset, '%d polling divisions carry several names across their polling stations; name left empty' % st['name_ambiguous'], S_PR[ge])
    for k in sorted(fixed): gap('poll', 'pd_adv_poll_empty_on_some_parts', '%s:%d:%d-%d' % ((bset,) + k), 'shapefile parts of one PD: one part has ADV_POLL empty; kept the non-empty value', sids[0])
    return out, dict(st, units=len(out), shapefile_records=len(rows), name_from_boundary_file=sum(1 for o in out if 'poll_name_from_boundary_file' in o['flags']))

pd25, st25 = pd_units('PollingDivisionBoundaries_2025_SHP.zip', '*PD_CA_2025_EN.dbf', 'ec-2025-pd', 'ec-2023-fed', set(fed23), [S_GE45], 45,
    lambda r: (r['FED_NUM'], r['PD_NUM'], int(r['PD_NBR_SFX']), r['PD_TYPE'], r['ADV_POLL_N']))
pd21, st21 = pd_units('PD_CA_2021_EN.zip', '*PD_CA_2021_EN.dbf', 'ec-2021-pd', 'ec-2013-fed', set(fed13), [S_GE44], 44,
    lambda r: (r['FED_NUM'], r['PD_NUM'], int(r['PD_NBR_SFX']), r['PD_TYPE'], r['ADV_POLL_N']))
pd19, st19 = pd_units('polling_divisions_boundaries_2019.shp.zip', '*PD_CA_2019_EN.dbf', 'ec-2019-pd', 'ec-2013-fed', set(fed13), [S_GE43], 43,
    lambda r: (r['FEDNUM'], r['PDNUM'], int(r['PDNUMSFX']), r['PDTYPE'], r['ADVPOLLNUM']))

# ---------------- entities ----------------
ents = [
 {'entity_id': 'chamber:ca-house', 'kind': 'chamber', 'name': 'House of Commons of Canada', 'name_fr': 'Chambre des communes du Canada',
  'parent_id': 'nation:ca', 'source_id': S_CONST + ';' + S_FED23, 'feed': 'inst-lane', 'level': 'federal', 'type': 'lower_chamber',
  'flags': 'gov_status_na:legislative_chamber', 'country': 'ca', 'external_id': 'seats=343(2023_rep_order)'},
 {'entity_id': 'chamber:ca-senate', 'kind': 'chamber', 'name': 'Senate of Canada', 'name_fr': 'Sénat du Canada', 'parent_id': 'nation:ca',
  'source_id': S_CONST, 'feed': 'inst-lane', 'level': 'federal', 'type': 'upper_chamber',
  'flags': 'gov_status_na:legislative_chamber;appointed_no_electoral_units', 'country': 'ca', 'external_id': 'seats=105'},
]
gap('officeholder', 'senate_officeholders_not_built', 'chamber:ca-senate', 'appointed chamber, no electoral units; senators not loaded in this batch (source: sencanada.ca senator list)', S_CONST)

# ---------------- MPs ----------------
root = ET.parse(f'{RAW}/mps.xml').getroot()
mps = [{c.tag: (c.text or '').strip() for c in m} for m in root]
idx = collections.defaultdict(list)
for u in units_fed:
    if u['boundary_set'] != 'ec-2023-fed': continue
    for nm in {u['name'], u['alias']} - {''}: idx[(norm_name(nm), u['province'])].append(int(u['unit_key']))
oh, persons, seen = [], [], set()
for m in sorted(mps, key=lambda m: int(m['PersonId'])):
    p = next(k for k, v in PROV_NAME.items() if v == m['ConstituencyProvinceTerritoryName'])
    c = sorted(set(idx.get((norm_name(m['ConstituencyName']), p), [])))
    name = ' '.join(x for x in (m['PersonOfficialFirstName'], m['PersonOfficialLastName']) if x)
    pid = 'ca-mp:' + m['PersonId']
    if len(c) != 1:
        gap('officeholder', 'mp_constituency_not_matched', pid, '%s: %s (%s) matched %s FED names' % (name, m['ConstituencyName'], p, len(c)), S_MPS); continue
    fed = c[0]; seen.add(fed)
    oh.append({'unit_layer': 'fed', 'unit_key': str(fed), 'unit_vintage': 2023, 'unit_plan': 'rep-order-2023', 'boundary_set': 'ec-2023-fed',
        'join_status': 'joined', 'entity_id': 'chamber:ca-house', 'province': p, 'seat': '', 'district': m['ConstituencyName'],
        'person_id': pid, 'name': name, 'party': m['CaucusShortName'], 'caucus': m['CaucusShortName'], 'status': 'serving',
        'term_start': m['FromDateTime'][:10], 'term_end': m['ToDateTime'][:10], 'elected_date': '', 'note': '',
        'source_id': S_MPS + ';' + S_FED23, 'source_record_id': 'PersonId=' + m['PersonId'],
        'date_flags': ';'.join(x for x in ('elected_date_missing', '' if m['ToDateTime'] else 'term_end_open') if x)})
    persons.append({'person_id': pid, 'scheme': 'ca-mp', 'name': name, 'official_ids': 'ourcommons_person_id=' + m['PersonId'],
                    'sources': 'officeholders_ca_house_current', 'aliases': '', 'source_id': S_MPS,
                    'source_record_id': m['PersonId'], 'upstream_url': 'https://www.ourcommons.ca/Members/en/%s' % m['PersonId']})
for fed in sorted(set(fed23) - seen):
    p = SGC[str(fed)[:2]]
    oh.append({'unit_layer': 'fed', 'unit_key': str(fed), 'unit_vintage': 2023, 'unit_plan': 'rep-order-2023', 'boundary_set': 'ec-2023-fed',
        'join_status': 'joined', 'entity_id': 'chamber:ca-house', 'province': p, 'seat': '', 'district': fed23[fed], 'person_id': '',
        'name': '', 'party': '', 'caucus': '', 'status': 'vacant', 'term_start': '', 'term_end': '', 'elected_date': '',
        'note': 'no current member for this FED in the House of Commons member list on %s' % RET, 'source_id': S_MPS + ';' + S_FED23,
        'source_record_id': '', 'date_flags': ''})

OH_COLS = ['unit_layer', 'unit_key', 'unit_vintage', 'unit_plan', 'boundary_set', 'join_status', 'entity_id', 'province', 'seat', 'district',
           'person_id', 'name', 'party', 'caucus', 'status', 'term_start', 'term_end', 'elected_date', 'note', 'source_id', 'source_record_id', 'date_flags']
P_COLS = ['person_id', 'scheme', 'name', 'official_ids', 'sources', 'aliases', 'source_id', 'source_record_id', 'upstream_url']
os.makedirs(OUT, exist_ok=True)
ukey = lambda r: (r['boundary_set'], r['unit_type'], tuple(int(x) for x in re.findall(r'\d+', r['unit_key'])))
counts = {
 'entities_ca_federal.csv': write_csv(f'{OUT}/entities_ca_federal.csv', ENTITY_COLS, ents, key=lambda r: r['entity_id']),
 'units_ca_fed.csv': write_csv(f'{OUT}/units_ca_fed.csv', UNIT_COLS, units_fed, key=ukey),
 'units_ca_pd_2025.csv': write_csv(f'{OUT}/units_ca_pd_2025.csv', UNIT_COLS, pd25, key=ukey),
 'units_ca_pd_2021.csv': write_csv(f'{OUT}/units_ca_pd_2021.csv', UNIT_COLS, pd21, key=ukey),
 'units_ca_pd_2019.csv': write_csv(f'{OUT}/units_ca_pd_2019.csv', UNIT_COLS, pd19, key=ukey),
 'officeholders_ca_house_current.csv': write_csv(f'{OUT}/officeholders_ca_house_current.csv', OH_COLS, oh, key=lambda r: int(r['unit_key'])),
 'persons_ca.csv': write_csv(f'{OUT}/persons_ca.csv', P_COLS, persons, key=lambda r: int(r['person_id'].split(':')[1])),
 'gaps_ca_federal.csv': write_csv(f'{OUT}/gaps_ca_federal.csv', GAP_COLS, gaps, key=lambda r: (r['level'], r['gap'], r['key'])),
}
reg.check_ids()
write_csv(f'{OUT}/sources_ca_federal.csv', SOURCE_COLS, list(reg.rows.values()), key=lambda r: r['source_id'])
write_json(f'{OUT}/summary_ca_federal.json', {'rows': counts, 'sources': len(reg.rows), 'retrieved_at': RET,
 'fed_2023': len(fed23), 'fed_2023_renamed_bill_c25': renamed, 'fed_2013': len(fed13),
 'pd_2025': st25, 'pd_2021': st21, 'pd_2019': st19,
 'mps_in_xml': len(mps), 'mps_joined': sum(1 for r in oh if r['status'] == 'serving'), 'vacant': sum(1 for r in oh if r['status'] == 'vacant'),
 'caucus': dict(sorted(collections.Counter(r['caucus'] for r in oh if r['caucus']).items()))})
print(counts, renamed, st25, st21, st19)
