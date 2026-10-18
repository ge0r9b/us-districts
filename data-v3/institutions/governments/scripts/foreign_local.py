"""Shared pieces for the country-level foreign government builds (foreign/<gb|de|fr>/)."""
import collections, csv, json, os, urllib.parse
from common import CACHE, ROOT, fetch, manifest, write_csv

FOREIGN = os.path.join(ROOT, 'foreign')
# one column set for all three countries; country-specific codes go in code / alt_code / member_of
LOCAL_COLUMNS = ['entity_id', 'name', 'name_local', 'name_en', 'type', 'subtype', 'gov_status', 'parent_id', 'member_of',
                 'country', 'code_scheme', 'code', 'alt_code', 'iso_3166_2', 'wikidata_qid', 'code_valid_from', 'code_valid_to',
                 'valid_from', 'valid_to', 'is_active', 'note', 'flags', 'source', 'source_url', 'source_date', 'retrieved_at',
                 'license']
CODE_XW_COLUMNS = ['entity_id', 'code_scheme', 'code', 'relation', 'note', 'source', 'source_url']
BOUNDARY_COLUMNS = ['entity_id', 'boundary_dataset', 'boundary_code', 'vintage', 'relation', 'source_url']
MAX_BYTES = 10 * 1000 * 1000


def existing_foreign():
    """entity_id -> row of the ISO-based foreign layer (nations, dependencies, subdivisions)."""
    out = {}
    for f in ('nations.csv', 'dependencies.csv', 'subdivisions.csv'):
        with open(os.path.join(FOREIGN, f), encoding='utf-8') as fh:
            for r in csv.DictReader(fh):
                out[r['entity_id']] = r
    return out


def arcgis(key, base, service, where='1=1', fields='*', page=2000):
    """All attribute rows of an ArcGIS FeatureServer layer (no geometry), cached page by page."""
    rows, off = [], 0
    while True:
        q = urllib.parse.urlencode({'where': where, 'outFields': fields, 'returnGeometry': 'false', 'f': 'json',
                                    'resultOffset': off, 'resultRecordCount': page})
        k = '{}_{}'.format(key, off)
        p = fetch(k, url='{}/{}/FeatureServer/0/query?{}'.format(base, service, q), fname=k + '.json')
        d = json.load(open(p, encoding='utf-8'))
        if 'error' in d:
            raise RuntimeError('{}: {}'.format(service, d['error']))
        feats = [f['attributes'] for f in d.get('features', [])]
        rows += feats
        if not d.get('exceededTransferLimit') and len(feats) < page:
            return rows
        off += len(feats)


def write_split(path_base, rows, columns, region_key):
    """Write rows to <base>.csv, or split by region_key into <base>_<region>.csv if over 10 MB."""
    path = path_base + '.csv'
    write_csv(path, rows, columns)
    if os.path.getsize(path) < MAX_BYTES:
        return [path]
    os.remove(path)
    by = collections.defaultdict(list)
    for r in rows:
        by[region_key(r)].append(r)
    out = []
    for k, rs in sorted(by.items()):
        p = '{}_{}.csv'.format(path_base, k)
        write_csv(p, rs, columns)
        out.append(p)
    return out


def check(rows, known_parents):
    ids = [r['entity_id'] for r in rows]
    dup = [e for e, n in collections.Counter(ids).items() if n > 1]
    assert not dup, ('duplicate entity_id', dup[:5])
    known = set(ids) | set(known_parents)
    dangling = sorted({r['parent_id'] for r in rows if r['parent_id'] and r['parent_id'] not in known})
    assert not dangling, ('dangling parent_id', dangling[:5])
