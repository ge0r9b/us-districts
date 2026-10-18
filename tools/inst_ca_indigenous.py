"""Canada, First Nations (Indian Act bands) -> data-v3/inst/ca/ (institutions lane). Full Stack ruling: kind indigenous_government,
ids first_nation:ca-<band number>, entity_unit role reserve_of to ca_csd units.

Sources (ISC "First Nations Location", OGL-Canada): the band list (BAND_NUMBER, BAND_NAME, location point) and the First Nation -
reserve relation (BAND_NUMBER -> ADMIN_LAND_ID, ISC reserve number). The relation carries no StatCan CSDUID and no official ISC
reserve number -> CSDUID crosswalk is on the box, so NO reserve_of links are made (names are never matched); every reserve of a band
is listed in first_nation_reserves_ca.csv with an empty csd key, and the missing crosswalk is a gap.
Parent: the province / territory whose StatCan 2021 CSD polygon (lcsd000b21a_e) contains the band's ISC location point; nation:ca
if the point falls in no polygon. Flagged on every row.
"""
import collections, csv, io, sys, zipfile
from inst_ca_common import *
import shapefile
from shapely.geometry import shape, Point
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
polys, pr = [], []
for s in sf.iterShapeRecords():
    polys.append(shape(s.shape.__geo_interface__)); pr.append(s.record['PRUID'])
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
    fl.append('reserve_of_links_pending:no_official_reserve_csd_crosswalk')
    ents.append({'entity_id': 'first_nation:ca-%s' % n, 'kind': 'indigenous_government', 'name': b['BAND_NAME'], 'gov_status': 'government',
                 'parent_id': parent, 'source_id': S_BAND + ';' + S_BND, 'feed': 'inst-lane', 'level': 'local', 'type': 'First Nation (Indian Act band)',
                 'flags': ';'.join(fl), 'country': 'ca', 'province': prov, 'external_id': 'isc:band:%s' % n})
for r in sorted(rel, key=lambda r: (int(r['BAND_NUMBER']), r['ADMIN_LAND_ID'])):
    k = len(share[r['ADMIN_LAND_ID']])
    res.append({'entity_id': 'first_nation:ca-%s' % r['BAND_NUMBER'], 'band_number': r['BAND_NUMBER'], 'isc_reserve_number': r['ADMIN_LAND_ID'],
                'reserve_name_en': r['ADMIN_LAND_EN'], 'reserve_name_fr': r['ADMIN_LAND_FR'], 'bands_sharing': k,
                'csd_boundary_set': '', 'csd_unit_key': '', 'source_id': S_REL,
                'flags': ';'.join(x for x in ('shared_reserve' if k > 1 else '', 'csd_link_pending') if x)})
for a in sorted(share):
    if len(share[a]) > 1:
        nm = next(r['ADMIN_LAND_EN'] for r in rel if r['ADMIN_LAND_ID'] == a)
        gap('shared_reserve', 'reserve:' + a, '%s: held by %d bands (%s)' % (nm, len(share[a]), ','.join(sorted(share[a], key=int))), S_REL)
gap('reserve_csd_crosswalk_missing', 'all', 'ISC relation gives the ISC reserve number (ADMIN_LAND_ID = NRCan CLSS ALCODE) but no StatCan CSDUID; no official reserve -> CSD crosswalk on the box (StatCan 2021 First Nation/Indian band geography correspondence files are on www12.statcan.gc.ca); entity_unit reserve_of links not made; names are not matched', S_REL)
EU_COLS = ['entity_id', 'boundary_set', 'unit_type', 'unit_key', 'role', 'source_id', 'source_record_id', 'flags']
R_COLS = ['entity_id', 'band_number', 'isc_reserve_number', 'reserve_name_en', 'reserve_name_fr', 'bands_sharing', 'csd_boundary_set', 'csd_unit_key', 'source_id', 'flags']
counts = {'entities_ca_indigenous.csv': write_csv(f'{OUT}/entities_ca_indigenous.csv', ENTITY_COLS, ents),
          'entity_unit_ca.csv': write_csv(f'{OUT}/entity_unit_ca.csv', EU_COLS, eu),
          'first_nation_reserves_ca.csv': write_csv(f'{OUT}/first_nation_reserves_ca.csv', R_COLS, res),
          'gaps_ca_indigenous.csv': write_csv(f'{OUT}/gaps_ca_indigenous.csv', GAP_COLS, gaps, key=lambda r: (r['gap'], r['key']))}
reg.check_ids()
write_csv(f'{OUT}/sources_ca_indigenous.csv', SOURCE_COLS, list(reg.rows.values()), key=lambda r: r['source_id'])
write_json(f'{OUT}/summary_ca_indigenous.json', {'rows': counts, 'bands': len(ents), 'isc_reserve_links': len(rel), 'isc_reserves': len(share),
  'shared_reserves': sum(1 for v in share.values() if len(v) > 1), 'reserve_of_links': len(eu),
  'parents': dict(sorted(collections.Counter(e['parent_id'] for e in ents).items())),
  'gaps': dict(sorted(collections.Counter(g['gap'] for g in gaps).items())), 'retrieved_at': RET})
print(counts)
