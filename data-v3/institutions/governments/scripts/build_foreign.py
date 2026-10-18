"""Foreign national governments, foreign dependencies and first-level subdivisions (data-v3/institutions/governments/foreign/).

Sources (all cached in cache/, see sources.csv):
  iso_codes   Debian iso-codes v4.20.1 (LGPL-2.1), data/iso_3166-1.json and iso_3166-2.json: codes, English names, subdivision
              types; a subdivision is first-level when iso-codes gives it no `parent`
  un_members  un.org Member States page (193 members, date of admission); un_observers: un.org Non-member States page
              (Holy See, State of Palestine)
  wikidata    QID by exact code: P297 (ISO 3166-1 alpha-2) and P300 (ISO 3166-2), item not dissolved (no P576), exactly one
              item per code and one code per item; P463 = Q1065 (UN membership, no end date) as a second check of the UN list;
              P17 (country) of a dependency -> its sovereign; P41 flag, P158 seal, else P94 coat of arms (stored as the seal),
              P36 capital, P1313 office held by head of government
IDs: nation:<iso2>, territory:<iso2> (foreign dependency, parent = sovereign nation), province:ca-<code> / territory:ca-<code>
for Canada, subdivision:<iso 3166-2 lowercased> for every other country (proposal, see SCHEMA.md). The United States and
its states/DC/territories already exist in the domestic files (nation:us, state:SS, territory:SS); they are listed in
iso_domestic_crosswalk.csv instead of being duplicated here.
"""
import collections, html, json, os, re
from common import CACHE, ROOT, fetch, manifest, norm, write_csv
from wikidata import claims, commons_meta, qv, sparql
from build_images import spdx, rank, text

ISO_TAG = 'v4.20.1'
ISO = 'https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/{}/data/{}.json'
UN_MEMBERS = 'https://www.un.org/en/about-us/member-states'
UN_OBSERVERS = 'https://www.un.org/en/about-us/non-member-states'
SGC = 'https://www.statcan.gc.ca/eng/statistical-programs/document/sgc-cgt-2021-structure-eng.csv'
# reviewed: ISO 3166-2 lists Taiwan as a province of China (CN-TW); the ISO 3166-1 entry TW is built as nation:tw, so the
# CN-TW row is not built a second time (crosswalk relation duplicate_of_iso_3166_1)
ISO2_DUPLICATES = {'CN-TW': 'TW'}
OBSERVERS = {'VA': 'Holy See', 'PS': 'State of Palestine'}   # the two non-member observer States on UN_OBSERVERS
# un.org names that are not an iso-codes name/official_name/common_name; each mapping must also be confirmed by Wikidata
# P463 = Q1065 on the P297 item (checked below), so a name alone never decides
UN_NAME_CODES = {'Bahamas (The)': 'BS', "China (the People's Republic of)": 'CN', 'Democratic Republic of the Congo': 'CD',
                 'Gambia (Republic of The)': 'GM', 'Naoero': 'NR', 'Netherlands (Kingdom of the)': 'NL', 'Republic of Korea': 'KR'}
DOMESTIC = {'US': 'nation:us', 'AS': 'territory:60', 'GU': 'territory:66', 'MP': 'territory:69', 'PR': 'territory:72',
            'VI': 'territory:78'}
# the U.S. Minor Outlying Islands have no domestic row; keyed like the other U.S. territories (FIPS 74), parent nation:us
US_FIPS_TERRITORY = {'UM': 'territory:74'}
# realm items that are the UN member but carry no P297 (that sits on the constituent country's item): reviewed mapping
REALMS = {'Q756617': 'DK', 'Q29999': 'NL', 'Q889033': 'NZ'}   # Kingdom of Denmark, Kingdom of the Netherlands, Realm of New Zealand
# reviewed: Wikidata gives the Isle of Man itself as its P17; it is a Crown Dependency like Jersey and Guernsey (whose P17 is
# the United Kingdom), see https://www.gov.uk/government/publications/crown-dependencies-jersey-guernsey-and-isle-of-man
SOVEREIGN_REVIEWED = {'IM': ('GB', 'Crown Dependency (UK government, Crown dependencies page)')}
NO_GOVERNMENT = {'AQ': 'Antarctica: no government (Antarctic Treaty area)',
                 'BV': 'Bouvet Island: uninhabited Norwegian dependency without its own government',
                 'HM': 'Heard Island and McDonald Islands: uninhabited Australian external territory without its own government'}
FOREIGN_COLUMNS = ['entity_id', 'name', 'official_name', 'type', 'subtype', 'gov_status', 'parent_id', 'iso_alpha2', 'iso_alpha3',
                   'iso_numeric', 'iso_3166_2', 'un_status', 'un_admission_date', 'wikidata_qid', 'capital_qid', 'capital',
                   'head_of_government_office_qid', 'head_of_government_office', 'external_ids', 'alias', 'is_active', 'note', 'flags',
                   'source', 'source_url', 'retrieved_at', 'license']
XW_COLUMNS = ['iso_code', 'iso_name', 'entity_id', 'relation', 'source', 'source_url']
LIC_ISO = 'LGPL-2.1-or-later (Debian iso-codes)'


def sources():
    for f in ('iso_3166-1', 'iso_3166-2'):
        fetch('iso_' + f[4:], url=ISO.format(ISO_TAG, f), fname=f + '.json')
    fetch('un_members', url=UN_MEMBERS, fname='un_member_states.html')
    fetch('un_observers', url=UN_OBSERVERS, fname='un_non_member_states.html')
    fetch('statcan_sgc', url=SGC, fname='sgc-cgt-2021-structure-eng.csv')


def sgc_codes():
    """province/territory name -> SGC 2021 two-digit code (Statistics Canada, level 2 of the classification structure)"""
    import csv
    with open(os.path.join(CACHE, 'sgc-cgt-2021-structure-eng.csv'), encoding='cp1252') as f:
        return {r['Class title']: r['Code'] for r in csv.DictReader(f) if r['Level'] == '2'}


def un_members():
    t = open(os.path.join(CACHE, 'un_member_states.html'), encoding='utf-8').read()
    out = []
    for p in re.split(r'<h2(?: class="mb-0")?>', t)[1:]:
        name = html.unescape(re.sub(r'<[^>]+>', '', p.split('</h2>')[0])).strip()
        d = re.search(r'Date of Admission:\s*(\d\d)-(\d\d)-(\d{4})', p)
        if d:
            out.append((name, '{}-{}-{}'.format(d.group(3), d.group(2), d.group(1))))
    return out


def code_qids(prop):
    """code -> set of live items carrying it (best rank), and item -> set of codes"""
    by_code, by_item = collections.defaultdict(set), collections.defaultdict(set)
    for b in sparql('wdf_' + prop.lower(), 'SELECT ?i ?c WHERE { ?i wdt:%s ?c . FILTER NOT EXISTS { ?i wdt:P576 [] } }' % prop):
        by_code[qv(b, 'c').upper()].add(qv(b, 'i'))
        by_item[qv(b, 'i')].add(qv(b, 'c').upper())
    return by_code, by_item


def labelled(key, qids, prop):
    """QID -> [(value QID, English label)] for an item-valued property, batched"""
    out = collections.defaultdict(list)
    qids = sorted(set(qids), key=lambda q: int(q[1:]))
    for k in range(0, len(qids), 300):
        q = ('SELECT ?i ?v ?l WHERE { VALUES ?i { %s } ?i wdt:%s ?v . OPTIONAL { ?v rdfs:label ?l . FILTER(LANG(?l) = "en") } }'
             % (' '.join('wd:' + c for c in qids[k:k + 300]), prop))
        for b in sparql(key, q, True):
            v = (qv(b, 'v'), b.get('l', {}).get('value', ''))
            if v not in out[qv(b, 'i')]:
                out[qv(b, 'i')].append(v)
    return out


def build(reg):
    sources()
    iso1 = json.load(open(os.path.join(CACHE, 'iso_3166-1.json'), encoding='utf-8'))['3166-1']
    iso2 = json.load(open(os.path.join(CACHE, 'iso_3166-2.json'), encoding='utf-8'))['3166-2']
    man = manifest()
    ra_iso = man['iso_3166-1']['retrieved_at']
    iso_url1, iso_url2 = ISO.format(ISO_TAG, 'iso_3166-1'), ISO.format(ISO_TAG, 'iso_3166-2')
    stats = collections.Counter()
    gaps = []
    # ---- QIDs by exact code
    c1, i1 = code_qids('P297')
    c2, i2 = code_qids('P300')

    def one(by_code, by_item, code):
        qs = by_code.get(code, set())
        if len(qs) == 1 and len(by_item[next(iter(qs))]) == 1:
            return next(iter(qs)), ''
        return '', 'no_item' if not qs else 'multiple_items' if len(qs) > 1 else 'item_has_several_codes'
    # ---- UN membership: un.org list, matched to ISO by name; listed exceptions only with Wikidata P463 confirmation
    wd_un = {qv(b, 'i') for b in sparql('wdf_un', 'SELECT ?i WHERE { ?i p:P463 ?s . ?s ps:P463 wd:Q1065 . '
                                                 'FILTER NOT EXISTS { ?s pq:P582 [] } FILTER NOT EXISTS { ?i wdt:P576 [] } }')}
    idx = collections.defaultdict(set)
    for x in iso1:
        for k in ('name', 'official_name', 'common_name'):
            if x.get(k):
                idx[norm(x[k])].add(x['alpha_2'])
    un = {}
    for name, date in un_members():
        cs = idx.get(norm(name), set())
        if len(cs) == 1:
            un[next(iter(cs))] = (name, date, 'name')
        elif name in UN_NAME_CODES:
            c = UN_NAME_CODES[name]
            assert c1.get(c) and c1[c] & wd_un, 'UN name {} -> {} not confirmed by Wikidata P463'.format(name, c)
            un[c] = (name, date, 'listed_name_confirmed_by_wikidata_p463')
        else:
            raise SystemExit('un.org member name not resolved to an ISO code: ' + name)
    assert len(un) == 193, len(un)
    stats['un_members'] = len(un)
    stats['un_members_also_wikidata_p463'] = sum(1 for c in un if c1.get(c, set()) & wd_un)
    # ---- dependencies: sovereign from P17 of the P297 item
    p17 = labelled('wdf_p17', [q for qs in c1.values() for q in qs], 'P17')
    p131 = labelled('wdf_p131', [q for qs in c1.values() for q in qs], 'P131')
    p361 = labelled('wdf_p361', [q for qs in c1.values() for q in qs], 'P361')
    iso2_type = {s['code']: s['type'] for s in iso2 if not s.get('parent')}
    nations, deps, subs, xw = [], [], [], []
    ent_of_code = {}
    for x in sorted(iso1, key=lambda x: x['alpha_2']):
        c = x['alpha_2']
        q, why = one(c1, i1, c)
        how_q = 'qid_by_p297'
        if not q and why == 'multiple_items' and c in un and len(c1[c] & wd_un) == 1:
            # several live items carry the code (e.g. CY); the one with UN membership (P463 Q1065) is the state
            q, how_q = next(iter(c1[c] & wd_un)), 'qid_by_p297_and_p463'
        base = {k: '' for k in FOREIGN_COLUMNS}
        base.update(name=x['name'], official_name=x.get('official_name', ''), iso_alpha2=c, iso_alpha3=x['alpha_3'],
                    iso_numeric=x['numeric'], wikidata_qid=q, is_active='Y', alias=x.get('common_name', ''),
                    source='iso_codes' + (';wikidata_foreign' if q else ''), source_url=iso_url1, retrieved_at=ra_iso,
                    license=LIC_ISO, flags=how_q if q else 'no_qid:' + why)
        if c in DOMESTIC:
            xw.append({'iso_code': c, 'iso_name': x['name'], 'entity_id': DOMESTIC[c], 'relation': 'domestic_row',
                       'source': 'iso_codes', 'source_url': iso_url1})
            ent_of_code[c] = DOMESTIC[c]
            stats['domestic_cross_reference'] += 1
            continue
        if c in NO_GOVERNMENT:
            gaps.append({'entity_id': '', 'image_kind': '', 'wikidata_qid': q, 'reason': 'iso {} not built: {}'.format(c, NO_GOVERNMENT[c])})
            stats['iso_not_built_no_government'] += 1
            continue
        if c in un or c in OBSERVERS:
            eid = reg.get(['iso3166-1:' + c], 'nation:' + c.lower(), ra_iso[:10])
            st = 'member' if c in un else 'observer'
            base.update(entity_id=eid, type='sovereign', subtype='state', gov_status='independent', parent_id='',
                        un_status=st, un_admission_date=un[c][1] if c in un else '')
            base['source'] += ';un_members' if c in un else ';un_observers'
            base['source_url'] += ' ; ' + (UN_MEMBERS if c in un else UN_OBSERVERS)
            if c in un and un[c][0] != x['name']:
                base['note'] = 'UN name: ' + un[c][0]
            nations.append(base)
            ent_of_code[c] = eid
            continue
        sov = [v for v, _ in p17.get(q, []) if v != q]
        sov_codes = sorted({cc for v in sov for cc in i1.get(v, set())} |
                           {REALMS[v] for pr in (p17, p131, p361) for v, _ in pr.get(q, []) if v in REALMS})
        how = 'sovereign from Wikidata P17/P131/P361 of {}'.format(q)
        if c in US_FIPS_TERRITORY:
            sov_codes = ['US']
        if c in SOVEREIGN_REVIEWED:
            sov_codes, how = [SOVEREIGN_REVIEWED[c][0]], 'sovereign reviewed: ' + SOVEREIGN_REVIEWED[c][1]
        if len(sov_codes) == 1 and (sov_codes[0] in un or sov_codes[0] == 'US'):
            eid = US_FIPS_TERRITORY.get(c) or reg.get(['iso3166-1:' + c], 'territory:' + c.lower(), ra_iso[:10])
            if c in US_FIPS_TERRITORY:
                reg.get(['iso3166-1:' + c], eid, ra_iso[:10])
            kind = next((iso2_type[k] for k in iso2_type if k.endswith('-' + c) and k.split('-')[0] == sov_codes[0]), '')
            base.update(entity_id=eid, type='foreign', subtype=kind.lower() or 'dependency', gov_status='dependent',
                        parent_id='nation:' + sov_codes[0].lower(), un_status='none')
            base['source'] += ';wikidata_foreign'
            base['note'] = how + ('; subtype = ISO 3166-2 type of {}-{}'.format(sov_codes[0], c) if kind else '') if c not in US_FIPS_TERRITORY else \
                'U.S. Minor Outlying Islands: keyed by FIPS 74 like the other U.S. territories'
            deps.append(base)
            ent_of_code[c] = eid
        else:
            # not a UN member or observer and no single sovereign (e.g. Taiwan, Western Sahara): a nation-level row, flagged
            eid = reg.get(['iso3166-1:' + c], 'nation:' + c.lower(), ra_iso[:10])
            base.update(entity_id=eid, type='sovereign', subtype='non_un_state', gov_status='disputed_or_unrecognized',
                        parent_id='', un_status='none',
                        note='not a UN member or observer; Wikidata P17 gives {} (no single UN-member sovereign)'.format(
                            ','.join(sov_codes) or 'no other country'))
            base['flags'] += ';review_status'
            nations.append(base)
            ent_of_code[c] = eid
            stats['non_un_nation_rows'] += 1
    # ---- first-level subdivisions
    sgc = sgc_codes()
    from common import state_table
    us_fips = {u: fp for fp, (u, _, _) in state_table().items()}   # USPS -> state FIPS (DC: the CoG municipality cog:124214)
    qid_of_entity = {r['wikidata_qid']: r['entity_id'] for r in nations + deps if r['wikidata_qid']}
    for s in sorted(iso2, key=lambda s: s['code']):
        if s.get('parent'):
            stats['iso2_not_first_level'] += 1
            continue
        cc, sub = s['code'].split('-', 1)
        if s['code'] in ISO2_DUPLICATES:
            xw.append({'iso_code': s['code'], 'iso_name': s['name'], 'entity_id': ent_of_code[ISO2_DUPLICATES[s['code']]],
                       'relation': 'duplicate_of_iso_3166_1', 'source': 'iso_codes', 'source_url': iso_url2})
            stats['iso2_duplicate_of_iso1_reviewed'] += 1
            continue
        if cc == 'US':
            ss = us_fips.get(sub, '')
            eid = ('state:' + ss if ss and int(ss) <= 56 and ss != '11' else 'cog:124214' if ss == '11'
                   else DOMESTIC.get(sub) or US_FIPS_TERRITORY.get(sub, ''))
            xw.append({'iso_code': s['code'], 'iso_name': s['name'], 'entity_id': eid, 'relation': 'domestic_row',
                       'source': 'iso_codes', 'source_url': iso_url2})
            stats['us_subdivision_cross_reference'] += 1
            continue
        parent = ent_of_code.get(cc)
        if not parent or cc in NO_GOVERNMENT:
            stats['iso2_parent_not_built'] += 1
            continue
        q, why = one(c2, i2, s['code'])
        if q and q in qid_of_entity:
            # the same place as an ISO 3166-1 entry (e.g. an overseas department that also has its own alpha-2 code)
            xw.append({'iso_code': s['code'], 'iso_name': s['name'], 'entity_id': qid_of_entity[q], 'relation': 'same_wikidata_item',
                       'source': 'iso_codes;wikidata_foreign', 'source_url': iso_url2})
            stats['iso2_same_item_as_iso1'] += 1
            continue
        typ = s['type'].lower()
        if cc == 'CA':
            pre = 'territory' if typ == 'territory' else 'province'
            eid = reg.get(['iso3166-2:' + s['code']], '{}:ca-{}'.format(pre, sub.lower()), ra_iso[:10])
        else:
            eid = reg.get(['iso3166-2:' + s['code']], 'subdivision:' + s['code'].lower(), ra_iso[:10])
        r = {k: '' for k in FOREIGN_COLUMNS}
        r.update(entity_id=eid, name=s['name'], type='foreign', subtype=typ, gov_status='subnational', parent_id=parent,
                 iso_alpha2=cc, iso_3166_2=s['code'], wikidata_qid=q, is_active='Y',
                 source='iso_codes' + (';wikidata_foreign' if q else ''), source_url=iso_url2, retrieved_at=ra_iso,
                 license=LIC_ISO, flags='qid_by_p300' if q else 'no_qid:' + why)
        if cc == 'CA':
            code = sgc.get(s['name'])
            assert code, 'no SGC 2021 code for ' + s['name']
            r['external_ids'] = 'statcan_sgc:' + code
            r['source'] += ';statcan_sgc'
            r['source_url'] += ' ; ' + SGC
        subs.append(r)
    # ---- Wikidata facts and images
    rows = nations + deps + subs
    qids = [r['wikidata_qid'] for r in rows if r['wikidata_qid']]
    cap = labelled('wdf_p36', qids, 'P36')
    hog = labelled('wdf_p1313', qids, 'P1313')
    ra_wd = max((v['retrieved_at'] for k, v in manifest().items() if k.startswith('wdf_')), default='')
    for r in rows:
        q = r['wikidata_qid']
        if not q:
            continue
        r['capital_qid'] = ';'.join(v for v, _ in cap.get(q, []))
        r['capital'] = ';'.join(l for _, l in cap.get(q, []))
        r['head_of_government_office_qid'] = ';'.join(v for v, _ in hog.get(q, []))
        r['head_of_government_office'] = ';'.join(l for _, l in hog.get(q, []))
        r['retrieved_at'] = max(r['retrieved_at'], ra_wd)
    for r in rows:
        lic = [LIC_ISO] + (['CC0 1.0 (Wikidata)'] if 'wikidata_foreign' in r['source'] else []) + \
              (['facts only (UN website)'] if ';un_' in r['source'] else []) + \
              (['Statistics Canada Open Licence'] if 'statcan_sgc' in r['source'] else [])
        r['license'] = '; '.join(lic)
    cl = claims('wdf_img', qids, ['P41'])
    cl2 = claims('wdf_img2', qids, ['P158', 'P94'])
    files = [f for q in qids for f in cl.get(q, {}).get('P41', [])] + \
            [f for q in qids for p in ('P158', 'P94') for f in cl2.get(q, {}).get(p, [])]
    cm = commons_meta(files)
    ra_c = max((v['retrieved_at'] for k, v in manifest().items() if k.startswith('commons_')), default='')
    images = []
    for r in rows:
        q, eid = r['wikidata_qid'], r['entity_id']
        for ik, props in (('flag', [('P41', cl)]), ('seal', [('P158', cl2), ('P94', cl2)])):
            if not q:
                gaps.append({'entity_id': eid, 'image_kind': ik, 'wikidata_qid': '', 'reason': 'no_qid: ' + r['flags'].split(':', 1)[-1]})
                continue
            done = False
            for prop, src in props:
                cands = []
                for f in src.get(q, {}).get(prop, []):
                    m = cm.get(f)
                    if not m or m['missing']:
                        continue
                    em = m['em']
                    lic = spdx(em.get('LicenseShortName', {}).get('value', ''), em.get('LicenseUrl', {}).get('value', ''))
                    att = text(em.get('Artist', {}).get('value', '')) or text(em.get('Credit', {}).get('value', ''))
                    cands.append((rank(lic), f, m['url'], lic, att))
                if cands:
                    _, f, url, lic, att = sorted(cands)[0]
                    images.append({'entity_id': eid, 'image_kind': ik, 'commons_file': f, 'commons_url': url, 'license': lic,
                                   'attribution': att[:300], 'wikidata_qid': q, 'retrieved_at': ra_c,
                                   'usage_basis': 'coat of arms (P94) used as the seal' if prop == 'P94' else '', 'source_url': ''})
                    stats['{}|{}|{}'.format(ik, r['type'] if r['type'] == 'sovereign' else r['subtype'] if r in deps else 'subdivision', prop)] += 1
                    done = True
                    break
            if not done:
                gaps.append({'entity_id': eid, 'image_kind': ik, 'wikidata_qid': q,
                             'reason': 'no_P41_on_wikidata' if ik == 'flag' else 'no_P158_or_P94_on_wikidata'})
    stats['nations'] = len(nations)
    stats['dependencies'] = len(deps)
    stats['subdivisions'] = len(subs)
    stats['qid_nations_deps'] = sum(1 for r in nations + deps if r['wikidata_qid'])
    stats['qid_subdivisions'] = sum(1 for r in subs if r['wikidata_qid'])
    out_dir = os.path.join(ROOT, 'foreign')
    os.makedirs(out_dir, exist_ok=True)
    write_csv(os.path.join(out_dir, 'nations.csv'), nations, FOREIGN_COLUMNS)
    write_csv(os.path.join(out_dir, 'dependencies.csv'), deps, FOREIGN_COLUMNS)
    write_csv(os.path.join(out_dir, 'subdivisions.csv'), subs, FOREIGN_COLUMNS)
    write_csv(os.path.join(out_dir, 'iso_domestic_crosswalk.csv'), sorted(xw, key=lambda x: x['iso_code']), XW_COLUMNS)
    return rows, images, gaps, stats
