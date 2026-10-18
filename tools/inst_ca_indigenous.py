"""Canada, First Nations (Indian Act bands) -> data-v3/inst/ca/ (institutions lane). Full Stack ruling: kind indigenous_government,
ids first_nation:ca-<band number>, entity_unit role reserve_of to ca_csd units.

Sources (ISC "First Nations Location", OGL-Canada): the band list (BAND_NUMBER, BAND_NAME, location point) and the First Nation -
reserve relation (BAND_NUMBER -> ADMIN_LAND_ID, ISC reserve number). The relation carries no StatCan CSDUID and no official ISC
reserve number -> CSDUID crosswalk exists (StatCan's 2021 correspondence files cover DB / DA only), so, per Full Stack's ruling (b),
reserve_of links come from a geometry OVERLAY (method=overlay, every row ≈): NRCan CLSS Aboriginal Lands polygons (AL_TA, keyed by
ALCODE = ISC reserve number) x StatCan 2021 CSD polygons of the First Nations types, areas in Canada Albers Equal Area (ESRI:102001).
Link iff the overlap is >= 50% of the CSD's area or >= 50% of the reserve's area; everything else that overlaps is listed in
gaps_ca_reserve_overlay.csv; reserves with no linked CSD are flagged no_csd (never mapped to a parent CSD). Names are never matched.
Parent: the province / territory whose StatCan 2021 CSD polygon (lcsd000b21a_e) contains the band's ISC location point; nation:ca
if the point falls in no polygon. Flagged on every row.
"""
import collections, csv, io, sys, zipfile
from inst_ca_common import *
import shapefile, numpy as np, shapely
from shapely.geometry import shape, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
from pyproj import Transformer
OUT = sys.argv[1] if len(sys.argv) > 1 else 'data-v3/inst/ca'
RET = '2026-10-18'
I = f'{RAW}/isc'
B = 'https://data.sac-isc.gc.ca/geomatics/rest/directories/arcgisoutput/DonneesOuvertes_OpenData/Premiere_Nation_First_Nation/'
reg = Registry()
F_BAND, F_REL = f'{I}/Premiere_Nation_First_Nation_CSV.zip', f'{I}/Relation_Premiere_Nation_reserve_Relation_First_Nation_Reserve_CSV.zip'
F_DB, F_DR = f'{I}/First_Nation_Data_Dictionary_CSV.csv', f'{I}/Relation_First_Nation_Reserve_Data_Dictionary_CSV.csv'
F_BND = f'{RAW}/lcsd000b21a_e.zip'
S_BAND = reg.add('isc-first-nations-location', 'Indigenous Services Canada, First Nations Location (open.canada.ca b6567c5c-8339-4055-99fa-63f92114d9e4): Premiere_Nation_First_Nation.csv (BAND_NUMBER, BAND_NAME, LONGITUDE, LATITUDE) + data dictionary; browser download',
                 B + 'Premiere_Nation_First_Nation_CSV.zip|' + B + 'Reference/First_Nation_Data_Dictionary_CSV.csv', OGL_CA, RET, '', sha256(F_BAND) + ';' + sha256(F_DB))
S_REL = reg.add('isc-first-nation-reserve', 'Indigenous Services Canada, First Nations Location: Relation First Nation - Reserve (BAND_NUMBER, ADMIN_LAND_ID reserve number, reserve names) + data dictionary; browser download',
                B + 'Relation_Premiere_Nation_reserve_Relation_First_Nation_Reserve_CSV.zip|' + B + 'Reference/Relation_First_Nation_Reserve_Data_Dictionary_CSV.csv', OGL_CA, RET, '', sha256(F_REL) + ';' + sha256(F_DR))
S_BND = reg.add('statcan-lcsd-2021', 'Statistics Canada, 2021 Census cartographic boundary file, census subdivisions (lcsd000b21a_e: CSDUID, CSDNAME, CSDTYPE, PRUID)',
                'https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lcsd000b21a_e.zip',
                'Statistics Canada Open Licence (https://www.statcan.gc.ca/en/terms-conditions/open-licence)', RET, '', sha256(F_BND))
F_AL = f'{I}/AL_TA_CA_SHP_DCM_eng.zip'
S_AL = reg.add('nrcan-al-ta-ca', 'Natural Resources Canada (CLSS), Aboriginal Lands of Canada Legislative Boundaries, AL_TA_CA_SHP_DCM_eng.zip edition 2.189 (CONFIRMED + MODIFIED + ADDED change files; ALCODE, ALTYPE, polygons)',
               'https://ftp.maps.canada.ca/pub/nrcan_rncan/vector/geobase_al_ta/shp_eng/AL_TA_CA_SHP_DCM_eng.zip', OGL_CA, RET, '', sha256(F_AL))
def rd(z):
    zz = zipfile.ZipFile(z); n = zz.namelist(); assert len(n) == 1
    return list(csv.DictReader(io.StringIO(zz.read(n[0]).decode('utf-8-sig'))))
bands, rel = rd(F_BAND), rd(F_REL)
assert len({b['BAND_NUMBER'] for b in bands}) == len(bands)
bn = {b['BAND_NUMBER']: b for b in bands}
assert {r['BAND_NUMBER'] for r in rel} <= set(bn), 'relation band not in band list'
for r in rel: assert r['BAND_NAME'] == bn[r['BAND_NUMBER']]['BAND_NAME'], r
for b in bands: assert b['COORD_SYS'] == 'GCS_North_American_1983_CSRS' and b['BAND_NUMBER'].isdigit(), b

# parent: province of the CSD polygon containing the band location (geometry only; no names)
z = zipfile.ZipFile(F_BND)
sf = shapefile.Reader(shp=io.BytesIO(z.read('lcsd000b21a_e.shp')), shx=io.BytesIO(z.read('lcsd000b21a_e.shx')),
                      dbf=io.BytesIO(z.read('lcsd000b21a_e.dbf')), encoding='cp1252')
polys, pr, cuid, ctyp = [], [], [], []
for s in sf.iterShapeRecords():
    polys.append(shape(s.shape.__geo_interface__)); pr.append(s.record['PRUID']); cuid.append(s.record['CSDUID']); ctyp.append(s.record['CSDTYPE'])
tree = STRtree(polys)
tf = Transformer.from_crs('EPSG:4269', 'EPSG:3347', always_xy=True)
ents, res, gaps, eu = [], [], [], []
def gap(g, key, detail, sid): gaps.append({'level': 'indigenous_government', 'gap': g, 'key': key, 'detail': detail, 'source_id': sid})
nres = collections.Counter(r['BAND_NUMBER'] for r in rel)
share = collections.defaultdict(set)
for r in rel: share[r['ADMIN_LAND_ID']].add(r['BAND_NUMBER'])
for b in sorted(bands, key=lambda b: int(b['BAND_NUMBER'])):
    n = b['BAND_NUMBER']
    x, y = tf.transform(float(b['LONGITUDE']), float(b['LATITUDE']))
    hit = sorted({pr[i] for i in tree.query(Point(x, y), predicate='intersects')})
    fl = []
    if len(hit) == 1: parent, prov = prov_entity(SGC[hit[0]]), SGC[hit[0]]; fl.append('parent_from:isc_location_in_statcan_csd_2021')
    else:
        parent, prov = 'nation:ca', ''; fl.append('parent_nation:isc_location_in_%s_csd_polygons' % ('no' if not hit else 'several'))
        gap('location_outside_csd_polygons' if not hit else 'location_on_province_boundary', 'band:' + n,
            '%s: ISC location point (%s, %s) falls in %s 2021 CSD polygon(s); parent nation:ca' % (b['BAND_NAME'], b['LONGITUDE'], b['LATITUDE'], len(hit) or 'no'), S_BAND + ';' + S_BND)
    if '?' in b['BAND_NAME']: fl.append('name_has_question_mark_in_source')   # the ISC CSV carries '?' (likely a lost glottal stop)
    fl.append('isc_reserves:%d' % nres[n])
    if not nres[n]:
        fl.append('no_reserve_in_isc_relation')
        gap('band_without_reserve', 'band:' + n, '%s: no reserve in the ISC First Nation - reserve relation' % b['BAND_NAME'], S_REL)
    ents.append({'entity_id': 'first_nation:ca-%s' % n, 'kind': 'indigenous_government', 'name': b['BAND_NAME'], 'gov_status': 'government',
                 'parent_id': parent, 'source_id': S_BAND + ';' + S_BND, 'feed': 'inst-lane', 'level': 'local', 'type': 'First Nation (Indian Act band)',
                 'flags': ';'.join(fl), 'country': 'ca', 'province': prov, 'external_id': 'isc:band:%s' % n})
for a in sorted(share):
    if len(share[a]) > 1:
        nm = next(r['ADMIN_LAND_EN'] for r in rel if r['ADMIN_LAND_ID'] == a)
        gap('shared_reserve', 'reserve:' + a, '%s: held by %d bands (%s)' % (nm, len(share[a]), ','.join(sorted(share[a], key=int))), S_REL)
# ---- (b) overlay: NRCan reserve polygons x StatCan 2021 First Nations-type CSD polygons, equal-area --------------------------
FN_TYPES = {'IRI', 'S-É', 'IGD', 'TC', 'TK', 'NL', 'TWL', 'TAL'}     # geo012's eight First Nations types (1,028 CSDs)
ALB = 'ESRI:102001'
def reproj(g, t): return shapely.transform(g, lambda c: np.column_stack(t.transform(c[:, 0], c[:, 1])))
t_csd, t_al = Transformer.from_crs('EPSG:3347', ALB, always_xy=True), Transformer.from_crs('EPSG:4617', ALB, always_xy=True)
fn_idx = [i for i in range(len(polys)) if ctyp[i] in FN_TYPES]
assert len(fn_idx) == 1028, len(fn_idx)
csd_alb = {cuid[i]: shapely.make_valid(reproj(polys[i], t_csd)) for i in fn_idx}
oth_idx = [i for i in range(len(polys)) if ctyp[i] not in FN_TYPES]
za = zipfile.ZipFile(F_AL); al = {}
for part in ('CONFIRMED', 'MODIFIED', 'ADDED'):
    r = shapefile.Reader(shp=io.BytesIO(za.read(f'AL_TA_CA_2_189_{part}_eng.shp')), shx=io.BytesIO(za.read(f'AL_TA_CA_2_189_{part}_eng.shx')),
                         dbf=io.BytesIO(za.read(f'AL_TA_CA_2_189_{part}_eng.dbf')), encoding='utf-8', encodingErrors='replace')
    for sr in r.iterShapeRecords():
        c = sr.record['ALCODE']; assert c not in al, ('ALCODE in two change files', c)
        al[c] = (shapely.make_valid(reproj(shape(sr.shape.__geo_interface__), t_al)), sr.record['ALTYPE'])
keys = sorted(csd_alb); ctree = STRtree([csd_alb[k] for k in keys])
oth_alb = None
links, below, nocsd = collections.defaultdict(list), [], []
for a_ in sorted(share):
    if a_ not in al:
        nocsd.append((a_, 'no polygon for this ISC reserve number in NRCan AL_TA 2.189')); continue
    g, alt = al[a_]; ga = g.area
    hits = []
    for j in sorted(ctree.query(g, predicate='intersects')):
        k = keys[j]; c = csd_alb[k]; ia = g.intersection(c).area
        if ia <= 0: continue
        s_c, s_r = ia / c.area, ia / ga
        (hits if (s_c >= 0.5 or s_r >= 0.5) else below).append((a_, k, s_c, s_r, ia))
    for h in hits: links[a_].append(h)
    if not hits:
        nocsd.append((a_, 'no 2021 First Nations-type CSD overlaps >= 50%% (ALTYPE %s; %d below-threshold overlaps)' % (alt, sum(1 for b_ in below if b_[0] == a_))))
# entity_unit rows: one per band x CSD x ISC reserve (Full Stack: merged rows split), each with its own area and shares; the 50% rule
# is applied to each reserve on its own (a reserve that passed only as part of a merged group would go to the gaps file instead)
per_csd = collections.defaultdict(set)
for a_ in links:
    for h in links[a_]:
        for band in share[a_]: per_csd[(band, h[1])].add(a_)
merged_fail = []
for a_ in sorted(links):
    for (_, k, s_c, s_r, ia) in links[a_]:
        if not (s_c >= 0.5 or s_r >= 0.5):
            merged_fail.append((a_, k, s_c, s_r, ia)); continue
        for band in sorted(share[a_], key=int):
            eu.append({'entity_id': 'first_nation:ca-%s' % band, 'boundary_set': 'statcan-2021-csd', 'unit_type': 'ca_csd', 'unit_key': k, 'role': 'reserve_of',
               'method': 'overlay', 'share_of_geoid_in_entity': '%.4f' % min(1.0, s_c), 'share_of_entity_in_geoid': '%.4f' % min(1.0, s_r),
               'is_estimate': 'true', 'share_basis': '≈ overlay, equal-area (ESRI:102001): NRCan AL_TA 2.189 reserve polygon x StatCan 2021 CSD; share_of_geoid_in_entity = share of the CSD inside the reserve, share_of_entity_in_geoid = share of the reserve inside the CSD',
               'source_id': ';'.join([S_AL, S_REL, S_BND]), 'source_record_id': 'isc_reserve_no=%s' % a_,
               'flags': ';'.join(x for x in ('shared_reserve' if len(share[a_]) > 1 else '', 'several_reserves_in_csd' if len(per_csd[(band, k)]) > 1 else '') if x)})
eu.sort(key=lambda e: (int(e['entity_id'].split('-')[-1]), e['unit_key'], e['source_record_id']))
agg = {(e['entity_id'].split('-')[-1], e['unit_key']) for e in eu}
OV_COLS = ['isc_reserve_number', 'reserve_name_en', 'csd_unit_key', 'csd_name', 'csd_type', 'share_of_csd_in_reserve', 'share_of_reserve_in_csd', 'overlap_m2', 'status', 'source_id']
csdn = {r['CSDUID']: r['CSDNAME'] for r in (dict(zip([f[0] for f in sf.fields[1:]], rec)) for rec in sf.records())}
ctp = dict(zip(cuid, ctyp))
rname = {r['ADMIN_LAND_ID']: r['ADMIN_LAND_EN'] for r in rel}
ov = []
for (a_, k, s_c, s_r, ia) in sorted(below):
    ov.append({'isc_reserve_number': a_, 'reserve_name_en': rname[a_], 'csd_unit_key': k, 'csd_name': csdn[k], 'csd_type': ctp[k], 'share_of_csd_in_reserve': '%.4f' % s_c,
               'share_of_reserve_in_csd': '%.4f' % s_r, 'overlap_m2': '%.0f' % ia, 'status': 'below_threshold', 'source_id': S_AL + ';' + S_BND})
for (a_, k, s_c, s_r, ia) in sorted(merged_fail):
    ov.append({'isc_reserve_number': a_, 'reserve_name_en': rname[a_], 'csd_unit_key': k, 'csd_name': csdn[k], 'csd_type': ctp[k], 'share_of_csd_in_reserve': '%.4f' % s_c,
               'share_of_reserve_in_csd': '%.4f' % s_r, 'overlap_m2': '%.0f' % ia, 'status': 'below_threshold_individually_was_merged', 'source_id': S_AL + ';' + S_BND})
for a_, why in sorted(nocsd):
    ov.append({'isc_reserve_number': a_, 'reserve_name_en': rname[a_], 'csd_unit_key': '', 'csd_name': '', 'csd_type': '', 'share_of_csd_in_reserve': '',
               'share_of_reserve_in_csd': '', 'overlap_m2': '', 'status': 'no_csd: ' + why, 'source_id': S_AL + ';' + S_REL})
linked_csd = {k for (_, k) in agg}
for k in sorted(set(csd_alb) - linked_csd):
    gap('fn_csd_without_band', 'csd:' + k, '%s (%s): no ISC reserve overlaps this 2021 CSD >= 50%%; no reserve_of link' % (csdn[k], ctp[k]), S_AL + ';' + S_BND)
gap('reserve_of_by_overlay', 'all', 'no official ISC reserve number -> CSDUID crosswalk (StatCan 2021 correspondence files: DB / DA only); reserve_of links are an equal-area overlay (method=overlay, ≈), threshold 50%% of CSD or reserve; %d below-threshold overlaps and %d no_csd reserves in gaps_ca_reserve_overlay.csv' % (len(below), len(nocsd)), S_AL + ';' + S_REL)
# first_nation_reserves_ca.csv: one row per ISC band x reserve, CSD key filled from the overlay above. Exactly one link status
# flag per row: csd_linked (>= 1 linked CSD; several -> semicolon-joined, sorted CSDUIDs, csd_link_count > 1), below_threshold
# (no link, but >= 1 First Nations-type CSD overlap under 50%, listed as below_threshold in gaps_ca_reserve_overlay.csv), no_csd
# (no link and no overlap at all, or no NRCan polygon: no_al_ta_polygon). Both unlinked kinds are 'no_csd: ...' rows in the gaps file.
lk = collections.defaultdict(set)
for e in eu: lk[e['source_record_id'].split('=', 1)[1]].add(e['unit_key'])
bel_r = collections.Counter(b_[0] for b_ in below)
for r in sorted(rel, key=lambda r: (int(r['BAND_NUMBER']), r['ADMIN_LAND_ID'])):
    a_ = r['ADMIN_LAND_ID']; k = len(share[a_]); ks = sorted(lk.get(a_, ()))
    st = ['csd_linked'] if ks else ['below_threshold'] if bel_r[a_] else ['no_csd'] + (['no_al_ta_polygon'] if a_ not in al else [])
    if ks and bel_r[a_]: st.append('also_below_threshold_overlaps:%d' % bel_r[a_])
    res.append({'entity_id': 'first_nation:ca-%s' % r['BAND_NUMBER'], 'band_number': r['BAND_NUMBER'], 'isc_reserve_number': a_,
                'reserve_name_en': r['ADMIN_LAND_EN'], 'reserve_name_fr': r['ADMIN_LAND_FR'], 'bands_sharing': k,
                'csd_boundary_set': 'statcan-2021-csd' if ks else '', 'csd_unit_key': ';'.join(ks), 'csd_link_count': len(ks),
                'source_id': S_REL + (';' + S_AL + ';' + S_BND if a_ in al else ''),
                'flags': ';'.join((['shared_reserve'] if k > 1 else []) + st)})
EU_COLS = ['entity_id', 'boundary_set', 'unit_type', 'unit_key', 'role', 'method', 'share_of_geoid_in_entity', 'share_of_entity_in_geoid', 'is_estimate', 'share_basis', 'source_id', 'source_record_id', 'flags']
R_COLS = ['entity_id', 'band_number', 'isc_reserve_number', 'reserve_name_en', 'reserve_name_fr', 'bands_sharing', 'csd_boundary_set', 'csd_unit_key', 'csd_link_count', 'source_id', 'flags']
counts = {'entities_ca_indigenous.csv': write_csv(f'{OUT}/entities_ca_indigenous.csv', ENTITY_COLS, ents),
          'entity_unit_ca.csv': write_csv(f'{OUT}/entity_unit_ca.csv', EU_COLS, eu),
          'gaps_ca_reserve_overlay.csv': write_csv(f'{OUT}/gaps_ca_reserve_overlay.csv', OV_COLS, ov),
          'first_nation_reserves_ca.csv': write_csv(f'{OUT}/first_nation_reserves_ca.csv', R_COLS, res),
          'gaps_ca_indigenous.csv': write_csv(f'{OUT}/gaps_ca_indigenous.csv', GAP_COLS, gaps, key=lambda r: (r['gap'], r['key']))}
reg.check_ids()
write_csv(f'{OUT}/sources_ca_indigenous.csv', SOURCE_COLS, list(reg.rows.values()), key=lambda r: r['source_id'])
write_json(f'{OUT}/summary_ca_indigenous.json', {'rows': counts, 'bands': len(ents), 'isc_reserve_links': len(rel), 'isc_reserves': len(share),
  'shared_reserves': sum(1 for v in share.values() if len(v) > 1), 'reserve_of_links': len(eu), 'method': 'overlay',
  'distinct_reserves_linked': len({e['source_record_id'] for e in eu}), 'below_threshold_individually_was_merged': len(merged_fail), 'approx_rows': sum(1 for e in eu if e['is_estimate'] == 'true'), 'below_threshold_overlaps': len(below),
  'no_csd_reserves': len(nocsd), 'fn_csds_linked': len(linked_csd), 'fn_csds': len(csd_alb), 'bands_with_links': len({b for b, _ in agg}),
  'reserve_rows_by_link_status': dict(sorted(collections.Counter(next(f for f in r['flags'].split(';') if f in ('csd_linked', 'below_threshold', 'no_csd')) + ('_multi' if r['csd_link_count'] > 1 else '') for r in res).items())),
  'reserves_by_link_status': dict(sorted(collections.Counter(v for v in {r['isc_reserve_number']: next(f for f in r['flags'].split(';') if f in ('csd_linked', 'below_threshold', 'no_csd')) + ('_multi' if r['csd_link_count'] > 1 else '') for r in res}.values()).items())),
  'parents': dict(sorted(collections.Counter(e['parent_id'] for e in ents).items())),
  'gaps': dict(sorted(collections.Counter(g['gap'] for g in gaps).items())), 'retrieved_at': RET})
print(counts)
