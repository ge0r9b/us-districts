"""Canada, StatCan 2021 census divisions / subdivisions -> data-v3/inst/ca/ (institutions lane).

Units: every CD (293) and CSD (5,161), keys / names / types from the 2021 Geographic Attribute File (92-151-X, collapsed from one
row per dissemination block to one row per CSD and per CD) cross-checked against the 2021 CSD boundary file (lcsd000b21a_e) and
SGC 2021. Entities: classified ONLY by StatCan's 2021 CSD / CD type definitions (Census Dictionary 98-301-X geo012 + Table 1.5,
geo008 + Table 1.4; SGC 2021 Appendix A / B titles); see CSD_CLASS / CD_CLASS. Anything StatCan's text does not settle is a gap.
"""
import collections, csv, io, sys, zipfile
from inst_ca_common import *
import shapefile
OUT = sys.argv[1] if len(sys.argv) > 1 else 'data-v3/inst/ca'
RET = '2026-10-18'
reg = Registry()
LIC = 'Statistics Canada Open Licence (https://www.statcan.gc.ca/en/terms-conditions/open-licence)'
F_SGC = f'{RAW}/statcan/sgc-cgt-2021-structure-eng.csv'
F_ATTR = f'{RAW}/2021_92-151_X.zip'
F_BND = f'{RAW}/lcsd000b21a_e.zip'
F_VOL1 = f'{RAW}/statcan/12-571-x2021001-eng.pdf'
S_SGC = reg.add('statcan-sgc2021-structure', 'Statistics Canada, Standard Geographical Classification (SGC) 2021, structure file (sgc-cgt-2021-structure-eng.csv)',
                'https://www.statcan.gc.ca/en/statistical-programs/document/sgc-cgt-2021-structure-eng.csv', LIC, RET, '', sha256(F_SGC))
S_ATTR = reg.add('statcan-92-151-x-2021', 'Statistics Canada, 2021 Census Geographic Attribute File (92-151-X), 2021_92-151_X.csv (one row per dissemination block; CSDUID, CSDNAME, CSDTYPE, CDUID, CDNAME, CDTYPE, DBPOP2021)',
                 'https://www12.statcan.gc.ca/census-recensement/2021/geo/aip-pia/attribute-attribs/files-fichiers/2021_92-151_X.zip', LIC, RET, '', sha256(F_ATTR))
S_BND = reg.add('statcan-lcsd-2021', 'Statistics Canada, 2021 Census cartographic boundary file, census subdivisions (lcsd000b21a_e: CSDUID, CSDNAME, CSDTYPE, PRUID)',
                'https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lcsd000b21a_e.zip', LIC, RET, '', sha256(F_BND))
S_DCSD = reg.add('statcan-dict2021-csd', 'Statistics Canada, Dictionary, Census of Population 2021 (98-301-X): Census subdivision (geo012), CSD types and on-reserve CSD types; Table 1.5 CSD types by province (read online, not archived)',
                 'https://www12.statcan.gc.ca/census-recensement/2021/ref/dict/az/definition-eng.cfm?ID=geo012|https://www12.statcan.gc.ca/census-recensement/2021/ref/dict/tab/index-eng.cfm?ID=t1_5', LIC, RET)
S_DCD = reg.add('statcan-dict2021-cd', 'Statistics Canada, Dictionary, Census of Population 2021 (98-301-X): Census division (geo008), CD types; Table 1.4 CD types by province (read online, not archived)',
                'https://www12.statcan.gc.ca/census-recensement/2021/ref/dict/az/definition-eng.cfm?ID=geo008|https://www12.statcan.gc.ca/census-recensement/2021/ref/dict/tab/index-eng.cfm?ID=t1_4', LIC, RET)
S_VOL1 = reg.add('statcan-sgc2021-vol1', 'Statistics Canada, SGC 2021 Volume I, The Classification (12-571-X), incl. Appendix A / B type titles',
                 'https://www.statcan.gc.ca/sites/default/files/12-571-x2021001-eng.pdf', LIC, RET, '', sha256(F_VOL1))

# --- StatCan 2021 CSD type classes. Basis quoted in csd_types_ca.csv (column basis). -------------------------------------
# municipality: the type's official title (SGC 2021 Appendix B) is a municipality / city / town / village / township / parish
#   municipality: geo012 "CSD is the general term for municipalities (as determined by provincial/territorial legislation)";
#   SGC 2021 "Municipalities are units of local government".
# first_nations: the eight "CSD types legally affiliated with First Nations or Indian bands" (geo012) -> kind proposal, not minted.
# unorganized / statistical: geo012 "areas treated as municipal equivalents ... (e.g. ... unorganized territories)"; SNO and SC
#   "created as equivalents for municipalities by Statistics Canada". settlement: listed with reserves as non-municipal (task rule).
# gap: StatCan's text does not say whether the type is an incorporated municipality, or its title is misleading.
MUNI = {'C', 'CT', 'CU', 'CV', 'CY', 'DM', 'IM', 'M', 'MD', 'MÉ', 'MRM', 'MU', 'PE', 'RGM', 'RM', 'RMU', 'RV', 'SM', 'SV', 'T',
        'TP', 'TV', 'V', 'VL', 'NV', 'VN'}
FN = {'IRI', 'S-É', 'IGD', 'TC', 'TK', 'NL', 'TWL', 'TAL'}
UNORG = {'NO': 'unorganized', 'SNO': 'statistical_equivalent', 'SC': 'statistical_equivalent'}
SETTLE = {'SET', 'SÉ'}
GAP_CSD = {
 'P': 'title "Parish / Paroisse (municipalité de)" but StatCan does not say New Brunswick parishes are incorporated',
 'HAM': 'hamlet: YT, NT, NU; StatCan does not say which are incorporated municipalities',
 'NH': 'northern hamlet (SK): StatCan does not define its municipal status',
 'CC': 'chartered community (NT): StatCan does not define its municipal status',
 'CG': 'community government (NT): StatCan does not define its municipal status',
 'LGD': 'local government district (MB): StatCan does not define its municipal status',
 'RCR': 'rural community (NB): StatCan does not define its municipal status',
 'ID': 'improvement district (AB): StatCan does not define its municipal status',
 'SA': 'special area (AB): StatCan does not define its municipal status',
 'FD': 'fire district (PE): StatCan does not define its municipal status',
 'RDA': 'regional district electoral area (BC): part of a regional district (CD), StatCan does not call it a municipality',
 'CN': 'crown colony (1 CSD, SK): StatCan does not define it',
 'GR': 'gouvernement régional (QC, 1 CSD): a regional government at CSD level, StatCan does not define it',
 'VC': 'village cri (QC): geo012 describes it with the Terres réservées aux Cris, set aside for Cree bands; not in the on-reserve list',
 'VK': 'village naskapi (QC): geo012 describes it with the Terres réservées aux Naskapis; not in the on-reserve list',
 'TI': 'terre inuite (QC): Inuit lands, not a municipality and not a First Nations type in geo012',
 'SG': 'self-government (YT): First Nation self-government lands? not in geo012 on-reserve list',
 'TL': 'Teslin land (YT): First Nation lands? not in geo012 on-reserve list',
}
def csd_class(t):
    if t in MUNI: return 'municipality'
    if t in FN: return 'first_nations'
    if t in UNORG: return UNORG[t]
    if t in SETTLE: return 'settlement'
    if t in GAP_CSD: return 'gap'
    raise AssertionError(('unclassified CSD type', t))
# CD types (geo008: "provincially legislated areas (such as county, municipalité régionale de comté (MRC) and regional district)",
# "group of neighbouring municipalities joined together for the purposes of regional planning and managing common services";
# CDR and TER "created as equivalents by Statistics Canada").
CD_GOV = {'MRC', 'RD', 'RM', 'UC', 'DM'}
CD_STAT = {'CDR', 'TER'}
GAP_CD = {'CT': 'County / Comté (NB): StatCan does not say it has a council',
          'DIS': 'District (ON): StatCan does not say it has a council',
          'REG': 'Region (BC, NT, NU): StatCan does not say it has a council',
          'TÉ': 'Territoire équivalent (QC): equivalent of an MRC; StatCan does not say whether a regional council exists',
          'CTY': 'County outside Ontario (NS, PE): StatCan does not say it has a council; NS county municipalities are CSDs (MU / MD)'}
def cd_class(t, prov):
    if t in CD_GOV or (t == 'CTY' and prov == 'ON'): return 'government'
    if t in CD_STAT: return 'statistical'
    if t in GAP_CD: return 'gap'
    raise AssertionError(('unclassified CD type', t))
TITLE_CSD = {'C': 'City / Cité', 'CC': 'Chartered community', 'CG': 'Community government', 'CN': 'Crown colony / Colonie de la couronne',
 'CT': 'Canton (municipalité de)', 'CU': 'Cantons unis (municipalité de)', 'CV': 'City / Ville', 'CY': 'City', 'DM': 'District municipality',
 'FD': 'Fire District', 'GR': 'Gouvernement régional', 'HAM': 'Hamlet', 'ID': 'Improvement district', 'IGD': 'Indian government district',
 'IM': 'Island municipality', 'IRI': 'Indian reserve / Réserve indienne', 'LGD': 'Local government district', 'M': 'Municipality / Municipalité',
 'MD': 'Municipal district', 'MÉ': 'Municipalité', 'MRM': 'Regional Municipality / Municipalité regionale', 'MU': 'Municipality',
 'NH': 'Northern hamlet', 'NL': "Nisga'a land", 'NO': 'Unorganized / Non organisé', 'NV': 'Northern village',
 'P': 'Parish / Paroisse (municipalité de)', 'PE': 'Paroisse (municipalité de)', 'RCR': 'Rural community / Communauté rurale',
 'RDA': 'Regional district electoral area', 'RGM': 'Regional municipality', 'RM': 'Rural municipality', 'RMU': 'Resort Municipality',
 'RV': 'Resort village', 'S-É': 'Indian settlement / Établissement indien', 'SA': 'Special area',
 'SC': 'Subdivision of county municipality / Subdivision municipalité de comté', 'SÉ': 'Settlement / Établissement', 'SET': 'Settlement',
 'SG': 'Self-government / Autonomie gouvernementale', 'SM': 'Specialized municipality', 'SNO': 'Subdivision of unorganized / Subdivision non organisée',
 'SV': 'Summer village', 'T': 'Town', 'TAL': "Tla'amin Lands", 'TC': 'Terres réservées aux Cris', 'TI': 'Terre inuite',
 'TK': 'Terres réservées aux Naskapis', 'TL': 'Teslin land', 'TP': 'Township', 'TV': 'Town / Ville', 'TWL': 'Tsawwassen Lands',
 'V': 'Ville', 'VC': 'Village cri', 'VK': 'Village naskapi', 'VL': 'Village', 'VN': 'Village nordique'}
TITLE_CD = {'CDR': 'Census division / Division de recensement', 'CT': 'County / Comté', 'CTY': 'County', 'DIS': 'District',
 'DM': 'District municipality', 'MRC': 'Municipalité régionale de comté', 'RD': 'Regional district', 'REG': 'Region',
 'RM': 'Regional municipality', 'TÉ': 'Territoire équivalent', 'TER': 'Territory / Territoire', 'UC': 'United counties'}
assert set(TITLE_CSD) == MUNI | FN | set(UNORG) | SETTLE | set(GAP_CSD) and len(TITLE_CSD) == 57
BASIS = {'municipality': 'geo012: "CSD is the general term for municipalities (as determined by provincial/territorial legislation)"; type title (SGC 2021 App. B) names a municipality',
         'first_nations': 'geo012: one of the eight "CSD types legally affiliated with First Nations or Indian bands"',
         'unorganized': 'geo012: "areas treated as municipal equivalents for statistical purposes (e.g. ... unorganized territories)"',
         'statistical_equivalent': 'geo012: "created as equivalents for municipalities by Statistics Canada ... for the purpose of disseminating statistical data"',
         'settlement': 'not a municipality (settlement; task rule), no First Nations affiliation stated in geo012',
         'government': 'geo008: "provincially legislated areas (such as county, MRC and regional district)": "group of neighbouring municipalities joined together for ... regional planning and managing common services"',
         'statistical': 'geo008: CDR and TER "created as equivalents by Statistics Canada ... for the purpose of disseminating statistical data"'}

# --- collapse 92-151-X (one row per DB) to one row per CSD / CD ----------------------------------------------------------------
raw = zipfile.ZipFile(F_ATTR).read('2021_92-151_X.csv').decode('cp1252')
csd, cd, pop, ndb = {}, {}, collections.Counter(), collections.Counter()
for r in csv.DictReader(io.StringIO(raw)):
    k = r['CSDUID_SDRIDU']; v = (r['CSDNAME_SDRNOM'], r['CSDTYPE_SDRGENRE'], r['CDUID_DRIDU'], r['PRUID_PRIDU'])
    assert csd.setdefault(k, v) == v, ('CSD attributes differ across DBs', k)
    c = r['CDUID_DRIDU']; w = (r['CDNAME_DRNOM'], r['CDTYPE_DRGENRE'])
    assert cd.setdefault(c, w) == w, ('CD attributes differ across DBs', c)
    pop[k] += int(r['DBPOP2021_IDPOP2021'] or 0); ndb[k] += 1
del raw
z = zipfile.ZipFile(F_BND)
bnd = {x[0]: (x[2], x[3], x[5]) for x in shapefile.Reader(dbf=io.BytesIO(z.read('lcsd000b21a_e.dbf')), encoding='cp1252').records()}
sgc = list(csv.DictReader(open(F_SGC, encoding='cp1252')))
sgc_csd = {r['Code']: r['Class title'] for r in sgc if r['Hierarchical structure'] == 'Census subdivision'}
sgc_cd = {r['Code']: r['Class title'] for r in sgc if r['Hierarchical structure'] == 'Census division'}
assert set(csd) == set(bnd) == set(sgc_csd) and len(csd) == 5161, 'CSD key sets differ'
assert set(cd) == set(sgc_cd) and len(cd) == 293, 'CD key sets differ'
for k, (n, t, c, p) in csd.items():
    assert bnd[k][:2] == (n, t) and bnd[k][2] == p and k[:4] == c and k[:2] == p, ('boundary file disagrees', k)
units, ents, xw, gaps = [], [], [], []
def gap(level, g, key, detail, sid): gaps.append({'level': level, 'gap': g, 'key': key, 'detail': detail, 'source_id': sid})
for k, (n, t, c, p) in csd.items():
    if ' '.join(n.split()) != ' '.join(sgc_csd[k].split()): gap('municipality', 'name_differs_from_sgc', k, '%r vs SGC %r' % (n, sgc_csd[k]), S_ATTR + ';' + S_SGC)

# Flin Flon and Lloydminster: one municipality, one CSD per provincial part (geo012). One entity, keyed on the larger part.
STRADDLE = collections.defaultdict(list)
for k, (n, t, c, p) in csd.items():
    if n.endswith(' (Part)') and t in MUNI: STRADDLE[(n, t)].append(k)
straddle_key = {}
for (n, t), ks in STRADDLE.items():
    assert len(ks) == 2 and len({k[:2] for k in ks}) == 2, (n, ks)
    main = max(ks, key=lambda k: (pop[k], k))
    for k in ks: straddle_key[k] = main
    gap('municipality', 'straddles_provinces', ';'.join(sorted(ks)), '%s: one municipality, a CSD in each province (geo012); entity keyed on the larger part %s (pop %d), parent %s; parent province to confirm' % (n[:-7], main, pop[main], SGC[main[:2]]), S_DCSD)

def muni_id(k): return 'muni:ca-csd:%s' % k
def cd_id(c): return 'county:ca-cd:%s' % c
cd_gov = {}
for c, (n, t) in sorted(cd.items()):
    p = SGC[c[:2]]; cl = cd_class(t, p)
    eid = cd_id(c) if cl == 'government' else ''
    if eid:
        cd_gov[c] = eid
        ents.append({'entity_id': eid, 'kind': 'county', 'name': n, 'label': 'incorporated', 'gov_status': 'government', 'parent_id': prov_entity(p),
                     'source_id': ';'.join([S_ATTR, S_DCD, S_VOL1]), 'feed': 'inst-lane', 'level': 'county', 'type': TITLE_CD[t],
                     'flags': 'statcan_cd_type:%s' % t, 'country': 'ca', 'province': p, 'external_id': 'statcan:cd:%s' % c})
        xw.append({'entity_id': eid, 'unit_layer': 'ca_cd', 'geoid': c, 'vintage': 2021, 'boundary_set': 'statcan-2021-cd', 'relation': 'primary',
                   'source_id': S_ATTR, 'overlap': 'equal', 'share_of_geoid_in_entity': '1.0000', 'share_of_entity_in_geoid': '1.0000'})
    units.append({'boundary_set': 'statcan-2021-cd', 'unit_type': 'cd', 'unit_key': c, 'name': n, 'country': 'ca', 'province': p, 'entity_id': eid,
                  'attrs': 'cd_type=%s;cd_class=%s' % (t, cl), 'source_id': S_ATTR + ';' + S_SGC, 'source_record_id': 'CDUID=' + c,
                  'geometry_ref': 'StatCan lcd_000b21a_e (CDUID=%s), not downloaded' % c, 'flags': 'cd_type_ambiguous' if cl == 'gap' else ''})
for t in sorted({t for _, t in cd.values()}):
    cs = [c for c, (_, tt) in cd.items() if tt == t]
    gp = [c for c in cs if cd_class(t, SGC[c[:2]]) == 'gap']
    if gp: gap('county', 'cd_type_ambiguous', t, '%d CDs (%s): %s; units only, no entity' % (len(gp), ','.join(sorted({SGC[c[:2]] for c in gp})), GAP_CD[t]), S_DCD)

for k, (n, t, c, pr) in sorted(csd.items()):
    p = SGC[pr]; cl = csd_class(t); eid = ''; fl = []
    if cl == 'municipality':
        main = straddle_key.get(k, k); eid = muni_id(main)
        if main == k:
            nm = n[:-7] if k in straddle_key else n
            ef = ['statcan_csd_type:%s' % t] + (['straddles_provinces'] if k in straddle_key else []) + (['zero_population_2021'] if pop[k] == 0 else [])
            ents.append({'entity_id': eid, 'kind': 'municipality', 'name': nm, 'label': 'incorporated', 'gov_status': 'government',
                         'parent_id': prov_entity(p), 'source_id': ';'.join([S_ATTR, S_BND, S_DCSD]), 'feed': 'inst-lane', 'level': 'local',
                         'type': TITLE_CSD[t], 'flags': ';'.join(ef), 'country': 'ca', 'province': p, 'external_id': 'statcan:csd:%s' % k})
        xw.append({'entity_id': eid, 'unit_layer': 'ca_csd', 'geoid': k, 'vintage': 2021, 'boundary_set': 'statcan-2021-csd',
                   'relation': 'primary' if main == k else 'part', 'source_id': S_ATTR, 'overlap': 'equal' if k not in straddle_key else 'part',
                   'share_of_geoid_in_entity': '1.0000', 'share_of_entity_in_geoid': '1.0000' if k not in straddle_key else ''})
    elif cl == 'first_nations': fl.append('first_nations_kind_proposal')
    elif cl == 'gap': fl.append('csd_type_ambiguous')
    if pop[k] == 0: fl.append('zero_population_2021')
    units.append({'boundary_set': 'statcan-2021-csd', 'unit_type': 'csd', 'unit_key': k, 'name': n, 'country': 'ca', 'province': p,
                  'parent_boundary_set': 'statcan-2021-cd', 'parent_unit_key': c, 'entity_id': eid,
                  'attrs': 'csd_type=%s;csd_class=%s;pop2021=%d;db_count=%d' % (t, cl, pop[k], ndb[k]), 'source_id': ';'.join([S_ATTR, S_BND, S_SGC]),
                  'source_record_id': 'CSDUID=' + k, 'geometry_ref': 'lcsd000b21a_e.zip:lcsd000b21a_e (CSDUID=%s)' % k, 'flags': ';'.join(fl)})
cnt = collections.Counter(t for _, t, _, _ in csd.values())
for t in sorted(GAP_CSD):
    if cnt[t]: gap('municipality', 'csd_type_ambiguous', t, '%d CSDs (%s): %s; unit only, no entity' % (cnt[t], ','.join(sorted({SGC[p_] for _, tt, _, p_ in csd.values() if tt == t})), GAP_CSD[t]), S_DCSD)
fnn = sum(cnt[t] for t in FN)
gap('municipality', 'first_nations_kind_proposal', '+'.join(sorted(FN)), '%d CSDs of the eight First Nations types (geo012) not minted; proposed new kind for First Nations / band governments (bands are not CSDs: one band can hold several reserves) - CANADA_SCHEMA_PROPOSALS.md' % fnn, S_DCSD)
gap('school_board', 'not_built', 'all', 'no national list; provincial lists exist (e.g. Ontario school board list, BC school districts, Alberta school authorities) - see CANADA_PLAN.md', '')

types = []
for t in sorted(TITLE_CSD):
    cl = csd_class(t)
    types.append({'level': 'csd', 'type': t, 'title': TITLE_CSD[t], 'class': cl, 'minted_as': 'municipality' if cl == 'municipality' else '',
                  'count': cnt[t], 'provinces': ','.join(sorted({SGC[p] for _, tt, _, p in csd.values() if tt == t})),
                  'basis': GAP_CSD[t] if cl == 'gap' else BASIS[cl], 'source_id': S_DCSD + ';' + S_VOL1})
cdc = collections.Counter((t, SGC[c[:2]]) for c, (_, t) in cd.items())
for (t, p) in sorted(cdc):
    cl = cd_class(t, p)
    types.append({'level': 'cd', 'type': t, 'title': TITLE_CD[t], 'class': cl, 'minted_as': 'county' if cl == 'government' else '',
                  'count': cdc[(t, p)], 'provinces': p, 'basis': GAP_CD[t] if cl == 'gap' else BASIS[cl], 'source_id': S_DCD + ';' + S_VOL1})
assert sum(r['count'] for r in types if r['level'] == 'csd') == 5161 and sum(r['count'] for r in types if r['level'] == 'cd') == 293
XW_COLS = ['entity_id', 'unit_layer', 'geoid', 'vintage', 'boundary_set', 'relation', 'source_id', 'overlap', 'share_of_geoid_in_entity', 'share_of_entity_in_geoid']
T_COLS = ['level', 'type', 'title', 'class', 'minted_as', 'count', 'provinces', 'basis', 'source_id']
nat = lambda r: (r['unit_type'], r['unit_key'])
counts = {'units_ca_cd.csv': write_csv(f'{OUT}/units_ca_cd.csv', UNIT_COLS, [u for u in units if u['unit_type'] == 'cd'], key=nat),
          'units_ca_csd.csv': write_csv(f'{OUT}/units_ca_csd.csv', UNIT_COLS, [u for u in units if u['unit_type'] == 'csd'], key=nat),
          'entities_ca_municipal.csv': write_csv(f'{OUT}/entities_ca_municipal.csv', ENTITY_COLS, ents, key=lambda r: r['entity_id']),
          'entity_geoid_xwalk_ca.csv': write_csv(f'{OUT}/entity_geoid_xwalk_ca.csv', XW_COLS, xw, key=lambda r: (r['entity_id'], r['unit_layer'], r['geoid'])),
          'statcan_types_ca.csv': write_csv(f'{OUT}/statcan_types_ca.csv', T_COLS, types),
          'gaps_ca_municipal.csv': write_csv(f'{OUT}/gaps_ca_municipal.csv', GAP_COLS, gaps, key=lambda r: (r['level'], r['gap'], r['key']))}
reg.check_ids()
write_csv(f'{OUT}/sources_ca_municipal.csv', SOURCE_COLS, list(reg.rows.values()), key=lambda r: r['source_id'])
kc = collections.Counter(e['kind'] for e in ents)
write_json(f'{OUT}/summary_ca_municipal.json', {'rows': counts, 'cd': len(cd), 'csd': len(csd), 'retrieved_at': RET,
  'entities_by_kind': dict(sorted(kc.items())),
  'csd_by_class': dict(sorted(collections.Counter(csd_class(t) for _, t, _, _ in csd.values()).items())),
  'cd_by_class': dict(sorted(collections.Counter(cd_class(t, SGC[c[:2]]) for c, (_, t) in cd.items()).items())),
  'municipalities_by_type': dict(sorted(collections.Counter(TITLE_CSD[csd[e['external_id'].split(':')[2]][1]] for e in ents if e['kind'] == 'municipality').items())),
  'municipalities_by_province': dict(sorted(collections.Counter(e['province'] for e in ents if e['kind'] == 'municipality').items())),
  'cd_governments_by_type': dict(sorted(collections.Counter(e['type'] for e in ents if e['kind'] == 'county').items())),
  'csd_by_province': dict(sorted(collections.Counter(SGC[c[:2]] for c in csd).items()))})
print(counts)
