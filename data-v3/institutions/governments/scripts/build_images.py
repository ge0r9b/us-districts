"""images.csv (seal / flag image records, long format) and images_gaps.csv. See wikidata.py for the rules.

One row per (entity, image_kind): when Wikidata lists several files, the most open license wins
(public domain / CC0, then CC BY, then CC BY-SA, then others), ties by file name. School districts are skipped.
No image binaries are stored; commons_url is the file description page.
"""
import collections, html, re
from wikidata import claims, commons_meta, enwiki_seals
from common import manifest

IMAGE_COLUMNS = ['entity_id', 'image_kind', 'commons_file', 'commons_url', 'license', 'attribution', 'wikidata_qid',
                 'retrieved_at', 'usage_basis', 'source_url']
GAP_COLUMNS = ['entity_id', 'image_kind', 'wikidata_qid', 'reason']
FLAG_TYPES = {'nation', 'state', 'dc', 'territory'}
FALLBACK_TYPES = {'nation', 'state', 'dc', 'territory', 'county', 'tribe', 'municipality', 'township', 'federal_agency'}   # enwiki seal fallback attempted for these
FAIR_USE = 'identification icon, small size'


def spdx(short, url):
    s = (short or '').strip()
    low = s.lower()
    if not s:
        return ''
    if low.startswith('public domain') or low in ('pd', 'pd-us', 'no restrictions') or low.startswith('pd-'):
        return 'LicenseRef-PublicDomain'
    if low.startswith('cc0'):
        return 'CC0-1.0'
    m = re.match(r'cc[ -]by(-sa)?[ -](\d\.\d)', low)
    if m:
        return 'CC-BY{}-{}'.format('-SA' if m.group(1) else '', m.group(2))
    if low.startswith('gfdl'):
        return 'GFDL-1.2-or-later' if '1.2' in low else 'LicenseRef-GFDL'
    return 'LicenseRef-' + re.sub(r'[^A-Za-z0-9.]+', '-', s).strip('-')


def rank(lic):
    return (0 if lic in ('LicenseRef-PublicDomain', 'CC0-1.0') else 1 if lic.startswith('CC-BY-') and '-SA' not in lic
            else 2 if lic.startswith('CC-BY-SA') else 3)


def text(v):
    v = html.unescape(re.sub(r'<[^>]+>', ' ', v or ''))
    return ' '.join(v.split())


def fr_logos(fr_json):
    """entity_id -> Federal Register agency logo URL (medium size), the last-resort icon for federal agencies"""
    out = {}
    for a in fr_json:
        lg = a.get('logo') or {}
        u = lg.get('medium_url') or lg.get('small_url') or lg.get('thumb_url')
        if u:
            out['fr:{}'.format(a['id'])] = u
    return out


def fr_logo_row(eid, url, name, ra):
    """Federal Register agency logo: no Commons file and no stated license, so it is used under the fair-use basis
    (identification icon); source_url is the image on agency-logos.federalregister.gov."""
    return {'entity_id': eid, 'image_kind': 'logo', 'commons_file': '', 'commons_url': '', 'license': 'fair-use',
            'attribution': name + ' (agency logo as shown by the Federal Register)', 'wikidata_qid': '', 'retrieved_at': ra,
            'usage_basis': FAIR_USE, 'source_url': url}


def build(states, local, tribes, fed, terr_qids, fr_json=()):
    ents = [('nation:us', 'Q30', 'nation')]
    ents += [(r['entity_id'], r['wikidata_qid'], 'state') for r in states]
    for ss, qs in sorted(terr_qids.items()):
        if len(qs) == 1:
            ents.append(('territory:' + ss, next(iter(qs)), 'territory'))
    for r in local:
        if r['type'] in ('county', 'municipality', 'township'):
            ents.append((r['entity_id'], r.get('wikidata_qid', ''), 'dc' if r['state_fips'] == '11' and r['type'] == 'municipality' else r['type']))
    ents += [(r['entity_id'], r.get('wikidata_qid', ''), 'tribe') for r in tribes if r.get('subtype') != 'cross_reference']
    ents += [(r['entity_id'], r.get('wikidata_qid', ''), 'federal_agency') for r in fed]
    qid_gap = {r['entity_id']: r.get('_qid_gap', '') for r in fed}
    logos = fr_logos(fr_json)
    ra_fr = manifest().get('fr_agencies', {}).get('retrieved_at', '')
    name_of = {r['entity_id']: r['name'] for r in fed}
    gaps = []
    qids = [q for _, q, _ in ents if q]
    cl = claims('wd_img', qids, ['P158', 'P41'])
    files = [f for q in qids for p in ('P158', 'P41') for f in cl.get(q, {}).get(p, [])]
    cm = commons_meta(files)
    ra = max((v['retrieved_at'] for k, v in manifest().items() if k.startswith('commons_')), default='')
    have = {q for q in qids if cl.get(q, {}).get('P158')}
    p158_files = {f for q in qids for f in cl.get(q, {}).get('P158', [])}
    fb = enwiki_seals([q for e, q, k in ents if q and k in FALLBACK_TYPES and q not in have], p158_files)
    ra_en = max((v['retrieved_at'] for k, v in manifest().items() if k.startswith('enwp_')), default='')
    rows, stats = [], collections.Counter()
    for eid, q, kind in ents:
        for prop, ik in (('P158', 'seal'), ('P41', 'flag')):
            if ik == 'flag' and kind not in FLAG_TYPES:
                continue
            if not q and kind == 'federal_agency' and eid in logos:
                rows.append(fr_logo_row(eid, logos[eid], name_of[eid], ra_fr))
                stats['logo|federal_agency|fr_logo'] += 1
                continue
            if not q:
                why = 'no_qid' + (': ' + qid_gap[eid] if qid_gap.get(eid) else '')
                if kind == 'federal_agency':
                    why += '; no Federal Register logo'
                gaps.append({'entity_id': eid, 'image_kind': ik, 'wikidata_qid': '', 'reason': why})
                continue
            cands = []
            for f in cl.get(q, {}).get(prop, []):
                m = cm.get(f)
                if not m or m['missing']:
                    continue
                em = m['em']
                lic = spdx(em.get('LicenseShortName', {}).get('value', ''), em.get('LicenseUrl', {}).get('value', ''))
                att = text(em.get('Artist', {}).get('value', '')) or text(em.get('Credit', {}).get('value', ''))
                cands.append((rank(lic), f, m['url'], lic, att))
            if not cands and ik == 'seal' and q in fb:
                b = fb[q]
                em = b['em']
                att = text(em.get('Artist', {}).get('value', '')) or text(em.get('Credit', {}).get('value', ''))
                nonfree = b['local'] or em.get('NonFree', {}).get('value', '').lower() == 'true'
                lic = 'fair-use' if nonfree else spdx(em.get('LicenseShortName', {}).get('value', ''), '')
                rows.append({'entity_id': eid, 'image_kind': ik, 'commons_file': '' if b['local'] else b['file'],
                             'commons_url': '' if b['local'] else b['url'], 'license': lic, 'attribution': att[:300],
                             'wikidata_qid': q, 'retrieved_at': ra_en, 'usage_basis': FAIR_USE if nonfree else '',
                             'source_url': (b['url'] if b['local'] else b['page'])})
                stats['{}|{}|enwiki_{}'.format(ik, kind, 'fair_use' if nonfree else 'free')] += 1
                continue
            if not cands and kind == 'federal_agency' and eid in logos:
                rows.append(dict(fr_logo_row(eid, logos[eid], name_of[eid], ra_fr), wikidata_qid=q))
                stats['logo|federal_agency|fr_logo'] += 1
                continue
            if not cands:
                why = 'no_{}_on_wikidata'.format(prop) if not cl.get(q, {}).get(prop) else 'commons_file_missing'
                if ik == 'seal':
                    why += '; enwiki article fallback: ' + ('no single seal file' if kind in FALLBACK_TYPES else 'not attempted for this type')
                gaps.append({'entity_id': eid, 'image_kind': ik, 'wikidata_qid': q, 'reason': why})
                continue
            _, f, url, lic, att = sorted(cands)[0]
            rows.append({'entity_id': eid, 'image_kind': ik, 'commons_file': f, 'commons_url': url, 'license': lic,
                         'attribution': att[:300], 'wikidata_qid': q, 'retrieved_at': ra, 'usage_basis': '', 'source_url': ''})
            stats['{}|{}'.format(ik, kind)] += 1
    rows.sort(key=lambda r: (r['entity_id'], r['image_kind']))
    gaps.sort(key=lambda r: (r['entity_id'], r['image_kind']))
    return rows, gaps, stats
