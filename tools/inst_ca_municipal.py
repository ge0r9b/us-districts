"""Canada, census divisions and census subdivisions (StatCan SGC 2021) as UNITS -> data-v3/inst/ca/ (institutions lane).

No municipal / county ENTITIES are minted yet: entity ids are frozen at first sight, and which CSDs / CDs are governments
depends on the CSD / CD type (city, town, RM, Indian reserve, unorganized ...). The 2021 type table is on www12.statcan.gc.ca
(boundary files, GeoSuite: behind a "Security Check" bot challenge) and www150.statcan.gc.ca (table 98-10-0002: TLS refused
from this box). Both are logged as blocked; nothing was bypassed. The SGC 2021 structure file (codes + names, no types) is used.
"""
import collections, csv, re, sys
from inst_ca_common import *
OUT = sys.argv[1] if len(sys.argv) > 1 else 'data-v3/inst/ca'
RET = '2026-10-18'
reg = Registry()
LIC = 'Statistics Canada Open Licence (https://www.statcan.gc.ca/en/terms-conditions/open-licence)'
F = f'{RAW}/statcan/sgc-cgt-2021-structure-eng.csv'
S = reg.add('statcan-sgc2021-structure', 'Statistics Canada, Standard Geographical Classification (SGC) 2021, structure file (sgc-cgt-2021-structure-eng.csv)',
            'https://www.statcan.gc.ca/en/statistical-programs/document/sgc-cgt-2021-structure-eng.csv', LIC, RET, '', sha256(F))
B1 = reg.add('statcan-boundary-2021', 'Statistics Canada, 2021 Census boundary files (lcsd000b21a_e / lcd_000b21a_e: CSDTYPE, CDTYPE)',
             'https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/index2021-eng.cfm?year=21', LIC, RET)
B2 = reg.add('statcan-tbl-98100002', 'Statistics Canada, Table 98-10-0002 Population and dwelling counts: census subdivisions (CSD names with type)',
             'https://www150.statcan.gc.ca/n1/tbl/csv/98100002-eng.zip', LIC, RET)
rows = list(csv.DictReader(open(F, encoding='cp1252')))
units, gaps = [], []
cds = {r['Code']: r['Class title'] for r in rows if r['Hierarchical structure'] == 'Census division'}
csds = [(r['Code'], r['Class title']) for r in rows if r['Hierarchical structure'] == 'Census subdivision']
for c, n in sorted(cds.items()):
    units.append({'boundary_set': 'statcan-2021-cd', 'unit_type': 'cd', 'unit_key': c, 'name': n, 'country': 'ca', 'province': SGC[c[:2]],
                  'attrs': 'cd_type=unknown', 'source_id': S, 'source_record_id': 'CDUID=' + c, 'geometry_ref': 'StatCan lcd_000a21a_e (CDUID=%s), not downloaded' % c,
                  'flags': 'gov_status_unknown:cd_type_not_retrieved'})
for c, n in sorted(csds):
    assert c[:4] in cds
    units.append({'boundary_set': 'statcan-2021-csd', 'unit_type': 'csd', 'unit_key': c, 'name': n, 'country': 'ca', 'province': SGC[c[:2]],
                  'parent_boundary_set': 'statcan-2021-cd', 'parent_unit_key': c[:4], 'attrs': 'csd_type=unknown', 'source_id': S,
                  'source_record_id': 'CSDUID=' + c, 'geometry_ref': 'StatCan lcsd000a21a_e (CSDUID=%s), not downloaded' % c,
                  'flags': 'incorporated_unknown:csd_type_not_retrieved'})
gaps.append({'level': 'municipality', 'gap': 'blocked_source', 'key': 'www12.statcan.gc.ca',
             'detail': 'boundary-file download answers HTTP 403 "Security Check" (bot challenge); not bypassed. Needed for CSDTYPE / CDTYPE (incorporated flag, which CSDs/CDs are governments)', 'source_id': B1})
gaps.append({'level': 'municipality', 'gap': 'blocked_source', 'key': 'www150.statcan.gc.ca',
             'detail': 'TLS connection refused from this box (unexpected EOF, 3 tries); table 98-10-0002 gives every CSD name with its type; not bypassed', 'source_id': B2})
gaps.append({'level': 'municipality', 'gap': 'entities_not_minted', 'key': 'csd+cd',
             'detail': '%d CSDs and %d CDs loaded as units only; municipal / county / regional government entities wait for the 2021 type table (entity ids are frozen at first sight, so they are not minted on a guess)' % (len(csds), len(cds)), 'source_id': S})
gaps.append({'level': 'school_board', 'gap': 'not_built', 'key': 'all',
             'detail': 'no national list; provincial lists exist (e.g. Ontario school board list, BC school districts, Alberta school authorities) - see CANADA_PLAN.md', 'source_id': ''})
nat = lambda r: (r['unit_type'], r['unit_key'])
counts = {'units_ca_cd.csv': write_csv(f'{OUT}/units_ca_cd.csv', UNIT_COLS, [u for u in units if u['unit_type'] == 'cd'], key=nat),
          'units_ca_csd.csv': write_csv(f'{OUT}/units_ca_csd.csv', UNIT_COLS, [u for u in units if u['unit_type'] == 'csd'], key=nat),
          'gaps_ca_municipal.csv': write_csv(f'{OUT}/gaps_ca_municipal.csv', GAP_COLS, gaps, key=lambda r: (r['level'], r['gap'], r['key']))}
reg.check_ids()
write_csv(f'{OUT}/sources_ca_municipal.csv', SOURCE_COLS, list(reg.rows.values()), key=lambda r: r['source_id'])
write_json(f'{OUT}/summary_ca_municipal.json', {'rows': counts, 'cd': len(cds), 'csd': len(csds), 'retrieved_at': RET,
  'csd_by_province': dict(sorted(collections.Counter(SGC[c[:2]] for c, _ in csds).items()))})
print(counts)
