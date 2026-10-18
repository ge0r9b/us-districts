"""50 state governments -> states.csv (entity_id state:SS, geoid = 2-digit state FIPS).

CoG 2022 counts 50 state governments but its unit file lists only local governments, so the rows come from the
Census state code file (FIPS + GNIS/ANSI code). DC (no state government; CoG counts it as a municipal government,
see local/DC.csv) and the territories are not included.
"""
from common import COLUMNS, PUBLIC_DOMAIN, meta, state_table

def build(reg):
    m = meta('states')
    rows = []
    for ss, (usps, name, ns) in sorted(state_table().items()):
        if int(ss) > 56 or ss == '11':
            continue
        eid = reg.get(['fips_state:' + ss], 'state:' + ss, m['retrieved_at'][:10])
        rows.append({'entity_id': eid, 'name': name, 'type': 'state', 'gov_status': 'independent',
                     'parent_id': 'nation:us', 'state_fips': ss, 'state': usps, 'geoid': ss, 'geoid_layer': 'states',
                     'geoid_vintage': '2024', 'geoid_match': 'fips', 'tiger_status': 'current_2024', 'gnis_id': ns, 'alias': usps,
                     'source': 'census_state_codes', 'source_url': '', 'source_date': m['last_modified'], 'retrieved_at': m['retrieved_at'],
                     'license': PUBLIC_DOMAIN})
    xw = [{'entity_id': r['entity_id'], 'unit_layer': 'states', 'geoid': r['geoid'], 'vintage': '2024',
           'relation': 'primary', 'match': 'fips', 'source': 'census_state_codes',
           'source_date': r['source_date']} for r in rows]
    return rows, xw
