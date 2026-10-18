"""Shared helpers for the governments dataset (data-v3/institutions/governments).

Every source file is downloaded once into ../cache/ (gitignored). cache/manifest.json records
for each file its URL, the time we retrieved it and the server's Last-Modified date, so a re-run
with a warm cache reproduces byte-identical CSVs. Run fetch_sources.py --refresh to re-download.
"""
import csv, datetime, email.utils, json, os, re, unicodedata, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # data-v3/institutions/governments
CACHE = os.path.join(ROOT, 'cache')
MANIFEST = os.path.join(CACHE, 'manifest.json')

GAZ = 'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_{}_national.zip'
SOURCES = {
    'cog2022': ('https://www2.census.gov/programs-surveys/gus/datasets/2022/govt_units_2022.ZIP', 'govt_units_2022.zip'),
    'states': ('https://www2.census.gov/geo/docs/reference/codes2020/national_state2020.txt', 'national_state2020.txt'),
    'fr_agencies': ('https://www.federalregister.gov/api/v1/agencies', 'fr_agencies.json'),
    'bia_search': ('https://www.federalregister.gov/api/v1/documents.json?conditions[term]=%22Indian+Entities+Recognized+by+and+Eligible%22'
                   '&conditions[agencies][]=indian-affairs-bureau&conditions[type][]=NOTICE&order=newest&per_page=20'
                   '&fields[]=title&fields[]=document_number&fields[]=publication_date&fields[]=citation&fields[]=full_text_xml_url&fields[]=html_url',
                   'bia_search.json'),
}
SOURCES['tiger_aiannh'] = ('https://www2.census.gov/geo/tiger/TIGER2024/AIANNH/tl_2024_us_aiannh.zip', 'tl_2024_us_aiannh.zip')
for g in ('counties', 'cousubs', 'place', 'unsd', 'elsd', 'scsd', 'aiannh'):
    SOURCES['gaz_' + g] = (GAZ.format(g), '2024_Gaz_{}_national.zip'.format(g))
# earlier vintages, used only for units that are not in TIGER 2024 (renamed, dissolved, new)
for y in ('2022', '2020'):
    for g in ('cousubs', 'place'):
        SOURCES['gaz{}_{}'.format(y, g)] = (GAZ.replace('2024', y).format(g), '{}_Gaz_{}_national.zip'.format(y, g))
# TIGER 2024 consolidated cities (only these states have one)
CONCITY_STATES = ('09', '13', '18', '20', '21', '30', '47')
for ss in CONCITY_STATES:
    SOURCES['concity_' + ss] = ('https://www2.census.gov/geo/tiger/TIGER2024/CONCITY/tl_2024_{}_concity.zip'.format(ss),
                                'tl_2024_{}_concity.zip'.format(ss))
# Annual Survey of School System Finances (F-33) unit files: PID6 (= CoG CENSUS_ID_PID6) + NCESID (= NCES LEAID)
F33 = 'https://www2.census.gov/programs-surveys/school-finances/tables/{0}/secondary-education-finance/elsec{1}.txt'
F33_YEARS = ('2024', '2023', '2022')            # newest first; a unit takes the newest file that lists it
for y in F33_YEARS:
    SOURCES['f33_' + y] = (F33.format(y, y[2:]), 'elsec{}.txt'.format(y[2:]))

PUBLIC_DOMAIN = 'public domain (U.S. Government work, 17 U.S.C. 105)'
COLUMNS = ['entity_id', 'name', 'type', 'subtype', 'gov_status', 'parent_id', 'state_fips', 'state',
           'county_geoid', 'geoid', 'geoid_layer', 'geoid_vintage', 'geoid_match', 'cog_id', 'cog_gidid',
           'fips_place', 'alias', 'gnis_id', 'ocd_id', 'wikidata_qid', 'is_active', 'note',
           'source', 'source_url', 'source_date', 'retrieved_at', 'license',
           'nces_leaid', 'tiger_status']     # appended Oct 18, 2026 (columns are only ever appended)
XWALK_COLUMNS = ['entity_id', 'unit_layer', 'geoid', 'vintage', 'relation', 'match', 'source', 'source_date']  # source = short code, see README


def manifest():
    if os.path.exists(MANIFEST):
        return json.load(open(MANIFEST))
    return {}


def fetch(key, refresh=False, url=None, fname=None):
    """Download SOURCES[key] (or an explicit url/fname) into the cache unless already present."""
    os.makedirs(CACHE, exist_ok=True)
    m = manifest()
    if url is None:
        url, fname = SOURCES[key]
    path = os.path.join(CACHE, fname)
    if os.path.exists(path) and key in m and not refresh:
        return path
    req = urllib.request.Request(url.replace('[', '%5B').replace(']', '%5D'),
                                 headers={'User-Agent': 'us-districts-governments-dataset/1.0'})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read()
        lm = r.headers.get('Last-Modified')
    with open(path, 'wb') as f:
        f.write(data)
    last_mod = email.utils.parsedate_to_datetime(lm).date().isoformat() if lm else ''
    m[key] = {'url': url, 'file': fname, 'bytes': len(data), 'last_modified': last_mod,
              'retrieved_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
    json.dump(m, open(MANIFEST, 'w'), indent=1, sort_keys=True)
    if fname.lower().endswith('.zip'):
        with zipfile.ZipFile(path) as z:
            z.extractall(CACHE)
    return path


def meta(key):
    return manifest()[key]


def read_gaz(name, year='2024'):
    """Gazetteer national file -> list of dicts (tab separated, trailing spaces stripped)."""
    path = os.path.join(CACHE, '{}_Gaz_{}_national.txt'.format(year, name))
    with open(path, encoding='utf-8', errors='replace') as f:
        rows = list(csv.reader(f, delimiter='\t'))
    hdr = [h.strip() for h in rows[0]]
    return [dict(zip(hdr, [c.strip() for c in r])) for r in rows[1:] if r]


def norm(s):
    """Uppercase ASCII, punctuation -> space, collapsed whitespace. Used only for exact matching."""
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode()
    s = s.upper().replace('&', ' AND ').replace("'", '')
    s = re.sub(r'[^A-Z0-9]+', ' ', s)
    return ' '.join(s.split())


def write_csv(path, rows, columns):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator='\n', extrasaction='raise')
        w.writeheader()
        for r in rows:
            w.writerow({c: ('' if r.get(c) is None else r.get(c)) for c in columns})
    return len(rows)


def state_table():
    """STATEFP -> (USPS, name) from the Census 2020 state code file."""
    out = {}
    with open(os.path.join(CACHE, 'national_state2020.txt'), encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='|'):
            out[r['STATEFP']] = (r['STATE'], r['STATE_NAME'], r['STATENS'])
    return out


def read_dbf(path):
    """Minimal dBase III reader (stdlib only) for TIGER .dbf attribute tables."""
    import struct
    with open(path, 'rb') as f:
        n, hlen, rlen = struct.unpack('<xxxxIHH', f.read(12))
        f.seek(32)
        fields = []
        while True:
            d = f.read(32)
            if d[0] == 0x0D:
                break
            fields.append((d[:11].split(b'\0')[0].decode(), d[16]))
        f.seek(hlen)
        out = []
        for _ in range(n):
            rec = f.read(rlen)
            if rec[:1] == b'*':
                continue
            pos, row = 1, {}
            for name, ln in fields:
                row[name] = rec[pos:pos + ln].decode('utf-8', 'replace').strip()
                pos += ln
            out.append(row)
    return out
