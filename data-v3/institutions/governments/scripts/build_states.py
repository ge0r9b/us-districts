"""50 state governments -> states.csv (entity_id state:SS, geoid = 2-digit state FIPS).

CoG 2022 counts 50 state governments but its unit file lists only local governments, so the rows come from the
Census state code file (FIPS + GNIS/ANSI code). DC (no state government; CoG counts it as a municipal government,
see local/DC.csv) and the territories are not included.
"""
from common import COLUMNS, PUBLIC_DOMAIN, meta, state_table

def build():
    m = meta('states')
    rows = []
    for ss, (usps, name, ns) in sorted(state_table().items()):
        if int(ss) > 56 or ss == '11':
            continue
        rows.append({'entity_id': 'state:' + ss, 'name': name, 'type': 'state', 'gov_status': 'independent',
                     'parent_id': '', 'state_fips': ss, 'state': usps, 'geoid': ss, 'geoid_layer': 'states',
                     'geoid_vintage': '2024', 'geoid_match': 'fips', 'gnis_id': ns, 'alias': usps,
                     'source': 'U.S. Census Bureau, 2020 FIPS state codes (national_state2020.txt); 50 state governments per 2022 Census of Governments',
                     'source_url': m['url'], 'source_date': m['last_modified'], 'retrieved_at': m['retrieved_at'],
                     'license': PUBLIC_DOMAIN})
    xw = [{'entity_id': r['entity_id'], 'unit_layer': 'states', 'geoid': r['geoid'], 'vintage': '2024',
           'relation': 'primary', 'match': 'fips', 'source': 'census_state_codes',
           'source_date': r['source_date']} for r in rows]
    return rows, xw
