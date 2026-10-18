"""Shared helpers for the governments dataset (data-v3/institutions/governments).

Every source file is downloaded once into ../cache/ (gitignored). cache/manifest.json records
for each file its URL, the time we retrieved it and the server's Last-Modified date, so a re-run
with a warm cache reproduces byte-identical CSVs. Run fetch_sources.py --refresh to re-download.
"""
import collections, csv, datetime, email.utils, json, os, re, time, unicodedata, urllib.error, urllib.request, zipfile

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

SOURCES['wikidata_tribes'] = ('https://query.wikidata.org/sparql?format=json&query=' + __import__('urllib.parse').parse.quote(
    'SELECT ?i ?label ?off WHERE { ?i wdt:P31 wd:Q7840353 . OPTIONAL { ?i rdfs:label ?label FILTER(LANG(?label)="en") } '
    'OPTIONAL { ?i wdt:P1448 ?off } }'), 'wd_tribes.json')

# Census Bureau Geographic Change Notes (BAS): official record of incorporations, disincorporations, mergers and
# renames reported by state/local governments, by effective year. Used for changes after the CoG 2022 snapshot.
GCN_YEARS = ('2021', '2022', '2023', '2024', '2025')
GCN = 'https://www2.census.gov/geo/docs/reference/bndrychange/national_gcn_{}.txt'
for y in GCN_YEARS:
    SOURCES['gcn_' + y] = (GCN.format(y), 'national_gcn_{}.txt'.format(y))

PUBLIC_DOMAIN = 'public domain (U.S. Government work, 17 U.S.C. 105)'
COLUMNS = ['entity_id', 'name', 'type', 'subtype', 'gov_status', 'parent_id', 'state_fips', 'state',
           'county_geoid', 'geoid', 'geoid_layer', 'geoid_vintage', 'geoid_match', 'cog_id', 'cog_gidid',
           'fips_place', 'alias', 'gnis_id', 'ocd_id', 'wikidata_qid', 'is_active', 'note',
           'source', 'source_url', 'source_date', 'retrieved_at', 'license',
           'nces_leaid', 'tiger_status',     # appended Oct 18, 2026 (columns are only ever appended)
           'flags', 'valid_from', 'valid_to']
XWALK_COLUMNS = ['entity_id', 'unit_layer', 'geoid', 'vintage', 'relation', 'match', 'source', 'source_date']  # source = short code, see README


EXTERNAL_IDS = {'nation:us', 'territory:60', 'territory:66', 'territory:69', 'territory:72', 'territory:78'}   # defined on data/inst-entities (territories: kind territory, parent nation:us), not here

# stable source codes -> (description, landing/file URL, license, manifest keys whose retrieval time applies)
SOURCE_TABLE = {
    'cog2022': ('U.S. Census Bureau, 2022 Census of Governments: Organization, Government Units Listing (Govt_Units_2022_Final.xlsx)',
                'https://www2.census.gov/programs-surveys/gus/datasets/2022/govt_units_2022.ZIP', ['cog2022']),
    'gaz2024': ('U.S. Census Bureau, TIGER 2024 Gazetteer national files (counties, cousubs, place, unsd, elsd, scsd)',
                'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/', ['gaz_counties', 'gaz_cousubs', 'gaz_place', 'gaz_unsd', 'gaz_elsd', 'gaz_scsd']),
    'gaz2022': ('U.S. Census Bureau, 2022 Gazetteer national files (cousubs, place)',
                'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2022_Gazetteer/', ['gaz2022_cousubs', 'gaz2022_place']),
    'gaz2020': ('U.S. Census Bureau, 2020 Gazetteer national files (cousubs, place)',
                'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/', ['gaz2020_cousubs', 'gaz2020_place']),
    'concity2024': ('U.S. Census Bureau, TIGER/Line 2024 consolidated cities (attribute tables)',
                    'https://www2.census.gov/geo/tiger/TIGER2024/CONCITY/', ['concity_' + s for s in CONCITY_STATES]),
    'tiger2024_aiannh': ('U.S. Census Bureau, TIGER/Line 2024 American Indian/Alaska Native/Native Hawaiian Areas (attribute table)',
                         'https://www2.census.gov/geo/tiger/TIGER2024/AIANNH/tl_2024_us_aiannh.zip', ['tiger_aiannh']),
    'census_state_codes': ('U.S. Census Bureau, 2020 FIPS state codes (national_state2020.txt)',
                           'https://www2.census.gov/geo/docs/reference/codes2020/national_state2020.txt', ['states']),
    'fr_agencies': ('Federal Register API v1, agencies endpoint', 'https://www.federalregister.gov/api/v1/agencies', ['fr_agencies']),
    'f33_2024': ('U.S. Census Bureau, Annual Survey of School System Finances FY2024 (elsec24.txt)', F33.format('2024', '24'), ['f33_2024']),
    'f33_2023': ('U.S. Census Bureau, Annual Survey of School System Finances FY2023 (elsec23.txt)', F33.format('2023', '23'), ['f33_2023']),
    'f33_2022': ('U.S. Census Bureau, Annual Survey of School System Finances FY2022 (elsec22.txt)', F33.format('2022', '22'), ['f33_2022']),
    'wikidata_tribes': ('Wikidata SPARQL: items with P31 = Q7840353 (federally recognized Native American tribe), English label and P1448 official name',
                        'https://query.wikidata.org/', ['wikidata_tribes']),
    'census_gcn': ('U.S. Census Bureau, Geographic Change Notes (Boundary and Annexation Survey), national files by effective year '
                   + '-'.join((GCN_YEARS[0], GCN_YEARS[-1])), 'https://www2.census.gov/geo/docs/reference/bndrychange/',
                   ['gcn_' + y for y in GCN_YEARS]),
    'wikidata_ids': ('Wikidata SPARQL: items by exact identifier (P5087 FIPS 5-2 numeric, P882 FIPS 6-4, P774 FIPS 55-3, P590 GNIS ID; '
                     'federal agencies: P856 official website = Federal Register agency_url, item an organisation)',
                     'https://query.wikidata.org/', ['wd_ids_*', 'wd_p590_*', 'wd_p856_*', 'wd_p856org_*']),
    'wikidata_images': ('Wikidata SPARQL: P158 seal image and P41 flag image of the matched items', 'https://query.wikidata.org/', ['wd_img_*']),
    'iso_codes': ('Debian iso-codes v4.20.1: ISO 3166-1 and ISO 3166-2 codes, English names and subdivision types (iso_3166-1.json, iso_3166-2.json)',
                  'https://salsa.debian.org/iso-codes-team/iso-codes/-/tree/v4.20.1/data', ['iso_3166-1', 'iso_3166-2']),
    'un_members': ('United Nations, Member States (names and dates of admission)', 'https://www.un.org/en/about-us/member-states', ['un_members']),
    'un_observers': ('United Nations, Non-member States (permanent observers: Holy See, State of Palestine)',
                     'https://www.un.org/en/about-us/non-member-states', ['un_observers']),
    'statcan_sgc': ('Statistics Canada, Standard Geographical Classification (SGC) 2021, classification structure CSV (province and territory codes)',
                    'https://www.statcan.gc.ca/eng/statistical-programs/document/sgc-cgt-2021-structure-eng.csv', ['statcan_sgc']),
    'wikidata_foreign': ('Wikidata SPARQL: items by exact ISO code (P297 alpha-2, P300 ISO 3166-2), UN membership (P463 Q1065), sovereign (P17/P131/P361), '
                         'capital (P36), office of head of government (P1313), flag (P41), seal (P158), coat of arms (P94); '
                         'UK council areas by exact GSS code (P836) with their ISO 3166-2 code (P300); German units by exact ARS (P1388) and Kreisschlüssel (P440); French units by exact INSEE commune code (P374), SIREN (P1616), INSEE region code (P2585, with P300)',
                         'https://query.wikidata.org/', ['wdf_*', 'wd_gss', 'wd_de_*', 'wd_fr_*']),
    'commons_api': ('Wikimedia Commons API imageinfo/extmetadata (license, author, attribution of each file)',
                    'https://commons.wikimedia.org/w/api.php', ['commons_*', 'sealovr_*']),
    'enwiki_api': ('English Wikipedia API: the matched Wikidata item\'s enwiki article (sitelink), its seal file and the file metadata '
                   '(fair-use fallback for seals)', 'https://en.wikipedia.org/w/api.php', ['enwd_sl_*', 'enwp_*']),
    'ons_rgc': ('Office for National Statistics, Register of Geographic Codes (June 2026) for the UK (live GSS codes, names, Welsh names, '
                'operative/termination dates, statutory instrument, parent code)',
                'https://geoportal.statistics.gov.uk/datasets/ef9bb98c8c62471684aaf42b8898f220', ['ons_rgc']),
    'ons_lookup': ('Office for National Statistics, Open Geography Portal lookups: WD26_LAD26_CTYUA26_RGN26_CTRY26_UK_LU (May 2026; '
                   'Scottish council areas, LAD cross-check) and LAD25_CAUTH25_EN_LU (May 2025; local authority -> combined authority)',
                   'https://geoportal.statistics.gov.uk/', ['ons_lu_*']),
    'ons_boundaries': ('Office for National Statistics, Open Geography Portal BFC boundary services (the editions Geo builds from: '
                       'LAD May 2026, CTYUA Dec 2025, CAUTH Dec 2025, PARNCP May 2026), attribute tables only (codes present; '
                       'foreign/gb/boundary_xwalk.csv)', 'https://geoportal.statistics.gov.uk/',
                       ['ons_bfc_*']),
    'destatis_rs': ('Statistisches Bundesamt (Destatis), Regionalschlüssel code list (all Gemeinden by ARS as in the Gemeindeverzeichnis '
                    'GV-ISys), version 2026-09-30, published on XRepository (urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:rs)',
                    'https://www.xrepository.de/details/urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:rs', ['destatis_rs']),
    'bkg_vg250': ('BKG, Verwaltungsgebiete 1:250 000 (VG250), Stand 01.01.2026, WFS attribute tables (no geometry): Staat, Länder, '
                  'Regierungsbezirke, Kreise, Gemeindeverbände, Gemeinden (ARS, AGS, name, designation BEZ, WSK)',
                  'https://sgx.geodatenzentrum.de/wfs_vg250', ['bkg_vg250_*']),
    'insee_cog2026': ('INSEE, Code officiel géographique au 1er janvier 2026 (CSV: régions, départements, CTCD, collectivités '
                      "d'outre-mer, communes, communes déléguées/associées, arrondissements municipaux, communes des COM, mouvements)",
                      'https://www.insee.fr/fr/information/8740222', ['insee_cog2026']),
    'insee_epci2026': ('INSEE, Base des EPCI à fiscalité propre au 1er janvier 2026 (SIREN, nature, composition communale)',
                       'https://www.insee.fr/fr/information/2510634', ['insee_epci2026']),
    'insee_ept2026': ('INSEE, Base des établissements publics territoriaux (EPT) au 1er janvier 2026',
                      'https://www.insee.fr/fr/information/2510634', ['insee_ept2026']),
    'ign_adminexpress': ('IGN, ADMIN EXPRESS COG CARTO (latest edition, names equal to COG 2026), Géoplateforme WFS attribute tables '
                         '(no geometry): SIREN of régions, CTCD and communes',
                         'https://data.geopf.fr/wfs/ows?SERVICE=WFS&REQUEST=GetCapabilities', ['ign_adminexpress_*']),
    'ign_aecog2026': ('IGN, ADMIN EXPRESS COG 4.0 édition 2026-01-01 (COG 2026, full precision; the edition Geo builds from), '
                      'Géoplateforme WFS attribute tables (no geometry): codes present in the region, departement, epci and '
                      'commune layers (foreign/fr/boundary_xwalk.csv)',
                      'https://data.geopf.fr/wfs/ows?SERVICE=WFS&REQUEST=GetCapabilities', ['ign_aecog2026_*']),
}
LICENSES = {'insee_cog2026': 'Licence Ouverte / Open Licence 2.0', 'insee_epci2026': 'Licence Ouverte / Open Licence 2.0',
            'insee_ept2026': 'Licence Ouverte / Open Licence 2.0', 'ign_adminexpress': 'Licence Ouverte / Open Licence 2.0 (IGN)',
            'ign_aecog2026': 'Licence Ouverte / Open Licence 2.0 (IGN)',
            'destatis_rs': 'dl-de/by-2-0 (Statistisches Bundesamt (Destatis), 2026)',
            'bkg_vg250': 'dl-de/by-2-0 (BKG 2026; Datenquellen https://sg.geodatenzentrum.de/web_public/gdz/datenquellen/datenquellen_vg_nuts.pdf)',
            'ons_rgc': 'Open Government Licence v3.0', 'ons_lookup': 'Open Government Licence v3.0',
            'ons_boundaries': 'Open Government Licence v3.0 (contains OS data (c) Crown copyright and database right)','wikidata_tribes': 'CC0 1.0 (Wikidata)', 'wikidata_ids': 'CC0 1.0 (Wikidata)', 'wikidata_images': 'CC0 1.0 (Wikidata)',
            'iso_codes': 'LGPL-2.1-or-later (Debian iso-codes); the codes themselves are ISO 3166 facts',
            'un_members': 'facts only (United Nations website, terms of use https://www.un.org/en/about-us/terms-of-use)',
            'un_observers': 'facts only (United Nations website, terms of use https://www.un.org/en/about-us/terms-of-use)',
            'statcan_sgc': 'Statistics Canada Open Licence (https://www.statcan.gc.ca/en/terms-conditions/open-licence)',
            'wikidata_foreign': 'CC0 1.0 (Wikidata)',
            'enwiki_api': 'metadata: CC BY-SA 4.0 (Wikipedia); each image under its own license or fair use (images.csv)', 'commons_api': 'metadata: CC BY-SA 4.0 / CC0 (Wikimedia); each image under its own license (images.csv)'}


class Registry:
    """id_registry/<scope>.csv: frozen entity IDs. One row per (entity_id, source_key); an entity may have several keys
    (e.g. a tribe's former and current listed names). Registered IDs are always reused; new IDs are only minted
    for keys never seen before. Rows are never deleted. Split by scope (us, foreign, gb, de, fr) to keep every file
    under 10 MB; all scopes are loaded together, so reuse and uniqueness work across them. The scope comes from the
    source_key scheme (see SCOPES). A legacy single id_registry.csv is read once and migrated."""
    COLS = ['entity_id', 'source_key', 'first_seen']
    SCOPES = (('iso3166-', 'foreign'), ('gss:', 'gb'), ('de-ars:', 'de'), ('fr-cog:', 'fr'), ('fr-siren:', 'fr'))

    def __init__(self):
        self.dir = os.path.join(ROOT, 'id_registry')
        self.legacy = os.path.join(ROOT, 'id_registry.csv')
        paths = sorted(os.path.join(self.dir, f) for f in os.listdir(self.dir) if f.endswith('.csv')) \
            if os.path.isdir(self.dir) else []
        if not paths and os.path.exists(self.legacy):
            paths = [self.legacy]
        self.rows = []
        for p in paths:
            with open(p, encoding='utf-8') as f:
                self.rows += list(csv.DictReader(f))
        self.by_key = {r['source_key']: r['entity_id'] for r in self.rows}
        assert len(self.by_key) == len(self.rows), 'source_key listed twice in id_registry'
        self.ids = {r['entity_id'] for r in self.rows}
        self.used = set()

    @classmethod
    def scope(cls, source_key):
        return next((sc for pre, sc in cls.SCOPES if source_key.startswith(pre)), 'us')

    def get(self, keys, proposed, first_seen):
        eid = next((self.by_key[k] for k in keys if k in self.by_key), None)
        if eid is None:
            eid, n = proposed, 1
            while eid in self.ids or eid in self.used:
                n += 1
                eid = '{}-{}'.format(proposed, n)
            self.ids.add(eid)
        if eid in self.used:
            raise ValueError('entity_id {} claimed twice in one build (keys {})'.format(eid, keys))
        self.used.add(eid)
        for k in keys:
            if k not in self.by_key:
                self.by_key[k] = eid
                self.rows.append({'entity_id': eid, 'source_key': k, 'first_seen': first_seen})
        return eid

    def save(self):
        self.rows.sort(key=lambda r: (r['entity_id'], r['source_key']))
        by = collections.defaultdict(list)
        for r in self.rows:
            by[self.scope(r['source_key'])].append(r)
        os.makedirs(self.dir, exist_ok=True)
        for f in os.listdir(self.dir):
            if f.endswith('.csv') and f[:-4] not in by:
                os.remove(os.path.join(self.dir, f))
        for sc, rs in by.items():
            write_csv(os.path.join(self.dir, sc + '.csv'), rs, self.COLS)
        if os.path.exists(self.legacy):
            os.remove(self.legacy)
        return len(self.rows)


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
                                 headers={'User-Agent': 'us-districts-governments-dataset/1.0 (https://github.com/ge0r9b/us-districts; ge0r9b@users.noreply.github.com)'})
    for attempt in range(4):   # transient network errors: retry with back-off, then give up
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
                lm = r.headers.get('Last-Modified')
            break
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 3:
                raise
            time.sleep(15 * (attempt + 1))
    with open(path, 'wb') as f:
        f.write(data)
    last_mod = email.utils.parsedate_to_datetime(lm).date().isoformat() if lm else ''
    m[key] = {'url': url, 'file': fname, 'bytes': len(data), 'last_modified': last_mod,
              'retrieved_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
    with open(MANIFEST + '.tmp', 'w') as f:      # atomic replace: a reader never sees a half-written manifest
        json.dump(m, f, indent=1, sort_keys=True)
    os.replace(MANIFEST + '.tmp', MANIFEST)
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
