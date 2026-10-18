"""Shared pieces for the country-level foreign government builds (foreign/<gb|de|fr>/)."""
import collections, csv, json, os, urllib.parse
from common import CACHE, ROOT, fetch, manifest, write_csv

FOREIGN = os.path.join(ROOT, 'foreign')
# one column set for all three countries; country-specific codes go in code / alt_code / member_of
LOCAL_COLUMNS = ['entity_id', 'name', 'name_local', 'name_en', 'alt_name', 'type', 'subtype', 'gov_status', 'parent_id', 'member_of',
                 'country', 'code_scheme', 'code', 'alt_code', 'iso_3166_2', 'wikidata_qid', 'code_valid_from', 'code_valid_to',
                 'valid_from', 'valid_to', 'is_active', 'predecessor_id', 'successor_id', 'note', 'flags', 'source', 'source_url', 'source_date', 'retrieved_at',
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


def arcgis(key, base, service, where='1=1', fields='*', page=2000, layer=0):
    """All attribute rows of an ArcGIS FeatureServer layer (no geometry), cached page by page."""
    rows, off = [], 0
    while True:
        q = urllib.parse.urlencode({'where': where, 'outFields': fields, 'returnGeometry': 'false', 'f': 'json',
                                    'resultOffset': off, 'resultRecordCount': page})
        k = '{}_{}'.format(key, off)
        p = fetch(k, url='{}/{}/FeatureServer/{}/query?{}'.format(base, service, layer, q), fname=k + '.json')
        d = json.load(open(p, encoding='utf-8'))
        if 'error' in d:
            raise RuntimeError('{}: {}'.format(service, d['error']))
        feats = [f['attributes'] for f in d.get('features', [])]
        rows += feats
        if not d.get('exceededTransferLimit') and len(feats) < page:
            return rows
        off += len(feats)


def wfs(key, base, typename, props, page=5000):
    """All features of a WFS 2.0 layer, selected properties only (no geometry), GeoJSON, cached page by page."""
    rows, start = [], 0
    while True:
        q = urllib.parse.urlencode({'service': 'WFS', 'version': '2.0.0', 'request': 'GetFeature', 'typeNames': typename,
                                    'propertyName': ','.join(props), 'outputFormat': 'application/json', 'count': page,
                                    'startIndex': start, 'sortBy': props[0]})
        k = '{}_{}'.format(key, start)
        p = fetch(k, url='{}?{}'.format(base, q), fname=k + '.json')
        feats = [f['properties'] for f in json.load(open(p, encoding='utf-8'))['features']]
        rows += feats
        if len(feats) < page:
            return rows
        start += page


def write_split(path_base, rows, columns, region_key):
    """Write rows to <base>.csv, or split by region_key into <base>_<region>.csv if over 10 MB."""
    import glob
    for old in glob.glob(path_base + '.csv') + glob.glob(path_base + '_*.csv'):   # stale parts of an earlier split
        os.remove(old)
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
    links = sorted({x for r in rows for k in ('predecessor_id', 'successor_id') for x in (r.get(k) or '').split(';')
                    if x and x not in known})
    assert not links, ('dangling predecessor/successor', links[:5])


def read_xlsx(path):
    """Minimal stdlib .xlsx reader (values only) for workbooks openpyxl cannot open: {sheet name: [row tuples]}."""
    import re as _re, zipfile
    import xml.etree.ElementTree as ET
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
          'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
    z = zipfile.ZipFile(path)
    ss = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', ns):
            ss.append(''.join(t.text or '' for t in si.iter('{%s}t' % ns['m'])))
    rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    out = {}
    for sh in ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets', ns):
        target = rels[sh.get('{%s}id' % ns['r'])].lstrip('/')
        target = target if target.startswith('xl/') else 'xl/' + target
        rows = []
        for row in ET.fromstring(z.read(target)).iter('{%s}row' % ns['m']):
            vals = {}
            for c in row.findall('m:c', ns):
                col = 0
                for ch in _re.match(r'[A-Z]+', c.get('r')).group():
                    col = col * 26 + ord(ch) - 64
                t, v = c.get('t'), c.find('m:v', ns)
                if t == 's':
                    val = ss[int(v.text)]
                elif t == 'inlineStr':
                    val = ''.join(x.text or '' for x in c.iter('{%s}t' % ns['m']))
                else:
                    val = v.text if v is not None else None
                vals[col - 1] = val
            rows.append(tuple(vals.get(i) for i in range(max(vals) + 1)) if vals else ())
        out[sh.get('name')] = rows
    return out
