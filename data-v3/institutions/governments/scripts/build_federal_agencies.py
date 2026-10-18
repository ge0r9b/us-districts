"""Federal Register agencies API -> federal_agencies.csv (entity_id fr:<id>, parent_id fr:<parent_id>).

The API lists every agency that has ever published in the Federal Register, including abolished ones
(e.g. ACTION); the API has no active/inactive flag, so is_active is left blank.
"""
import json, os
from common import CACHE, COLUMNS, PUBLIC_DOMAIN, meta

def build():
    m = meta('fr_agencies')
    data = json.load(open(os.path.join(CACHE, 'fr_agencies.json')))
    ids = {a['id'] for a in data}
    rows = []
    for a in sorted(data, key=lambda a: a['id']):
        p = a.get('parent_id')
        rows.append({'entity_id': 'fr:{}'.format(a['id']), 'name': ' '.join((a['name'] or '').split()),
                     'type': 'federal_agency', 'subtype': 'sub_agency' if p else 'agency', 'gov_status': '',
                     'parent_id': 'fr:{}'.format(p) if p else '',
                     'alias': ';'.join(x for x in [a.get('short_name') or '', a.get('slug') or ''] if x),
                     'note': '' if (not p or p in ids) else 'parent id {} not in API list'.format(p),
                     'source': 'Federal Register API v1, agencies endpoint ({})'.format(a.get('url') or ''),
                     'source_url': m['url'], 'source_date': m['retrieved_at'][:10], 'retrieved_at': m['retrieved_at'],
                     'license': PUBLIC_DOMAIN})
    return rows
