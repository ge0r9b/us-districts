"""Shared helpers for the Canada part of data-v3/inst (data-v3/inst/ca/). Deterministic output only."""
import csv, hashlib, io, json, os, re, sys, zipfile, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inst_sources import Registry, make_id  # same <slug>-<sha8(url|commit)> scheme as data-v3/inst/sources.csv

RAW = '/workspace/w/inst-raw/ca'
OGL_CA = 'Open Government Licence - Canada (https://open.canada.ca/en/open-government-licence-canada)'
# Statistics Canada SGC province/territory code -> ISO 3166-2 code, entity id (agreed with Full Stack, SCHEMA 3c1e42d)
SGC = {'10': 'NL', '11': 'PE', '12': 'NS', '13': 'NB', '24': 'QC', '35': 'ON', '46': 'MB', '47': 'SK', '48': 'AB', '59': 'BC',
       '60': 'YT', '61': 'NT', '62': 'NU'}
ISO2SGC = {v: k for k, v in SGC.items()}
PROV_NAME = {'NL': 'Newfoundland and Labrador', 'PE': 'Prince Edward Island', 'NS': 'Nova Scotia', 'NB': 'New Brunswick',
             'QC': 'Quebec', 'ON': 'Ontario', 'MB': 'Manitoba', 'SK': 'Saskatchewan', 'AB': 'Alberta', 'BC': 'British Columbia',
             'YT': 'Yukon', 'NT': 'Northwest Territories', 'NU': 'Nunavut'}
CA_TERR = {'NT', 'NU', 'YT'}
def prov_entity(iso): return ('territory:ca-%s' if iso in CA_TERR else 'province:ca-%s') % iso.lower()

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''): h.update(b)
    return h.hexdigest()

def dbf_rows(zpath, member_glob):
    """Read the attribute table (DBF) of a shapefile inside a zip; geometry is never read."""
    import shapefile, fnmatch
    z = zipfile.ZipFile(zpath)
    names = [n for n in z.namelist() if fnmatch.fnmatch(n.lower(), member_glob.lower())]
    assert len(names) == 1, (zpath, member_glob, names)
    r = shapefile.Reader(dbf=io.BytesIO(z.read(names[0])), encoding='utf-8', encodingErrors='strict')
    f = [x[0] for x in r.fields[1:]]
    return [dict(zip(f, rec)) for rec in r.records()], names[0]

def norm_name(s):
    s = unicodedata.normalize('NFKC', s or '').replace('\u2014', '-').replace('\u2013', '-').replace('--', '-')
    s = re.sub(r'\s*-\s*', '-', s)
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9-]+', ' ', s.lower()).strip()

def write_csv(path, cols, rows, key=None):
    rows = sorted(rows, key=key) if key else rows
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, cols, lineterminator='\n', extrasaction='raise'); w.writeheader()
        for r in rows: w.writerow({c: ('' if r.get(c) is None else r.get(c)) for c in cols})
    return len(rows)

def write_json(path, obj):
    with open(path, 'w', encoding='utf-8') as fh: json.dump(obj, fh, indent=1, sort_keys=True, ensure_ascii=False); fh.write('\n')

ENTITY_COLS = ['entity_id', 'kind', 'state_fips', 'state', 'name', 'alias', 'label', 'gov_status', 'parent_id', 'valid_from',
               'valid_to', 'predecessor_id', 'successor_id', 'v2_layer', 'v2_row', 'v2_key', 'source_id', 'feed', 'level', 'type',
               'cog_pid6', 'flags',
               # Canada additions (proposed, CANADA_SCHEMA_PROPOSALS.md)
               'country', 'province', 'name_fr', 'external_id']
UNIT_COLS = ['boundary_set', 'unit_type', 'unit_key', 'name', 'name_fr', 'alias', 'country', 'province', 'parent_boundary_set',
             'parent_unit_key', 'entity_id', 'attrs', 'source_id', 'source_record_id', 'geometry_ref', 'flags']
GAP_COLS = ['level', 'gap', 'key', 'detail', 'source_id']
SOURCE_COLS = ['source_id', 'source', 'source_url', 'license', 'retrieved_at', 'commit', 'sha256']
