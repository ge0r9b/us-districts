"""Wikidata QIDs from exact identifier links, and seal/flag image records from Wikidata + Wikimedia Commons.

QIDs (never from names):
  state         P5087 FIPS 5-2 numeric code      = state FIPS
  county        P882  FIPS 6-4                   = county GEOID (SSCCC)
  municipality  P774  FIPS 55-3 (digits only)    = place GEOID (SSPPPPP), and/or P590 GNIS ID = TIGER ANSI code
  township      P590  GNIS ID                    = TIGER ANSI code (P774 is not used: MCD and place codes collide)
  tribe         kept from tribes.csv (exact BIA-name = label/P1448 rule of part A)
  nation        Q30 for nation:us (fixed)
A QID is set only when exactly one item links to the entity and that item links to no other entity; if P774 and P590
disagree nothing is set. Federal agencies: Wikidata has no Federal Register agency-ID property, so none get a QID.

Images: P158 (seal image) for every entity with a QID except school districts; P41 (flag image) for the nation,
states, DC and territories whose P5087 code is in Wikidata. License/author from Commons imageinfo extmetadata.
Only URLs and metadata are written; no image files.
"""
import collections, json, os, time, urllib.parse
from common import CACHE, fetch, meta

UA_NOTE = 'batched SPARQL (VALUES <= 400) and Commons API (50 titles/request), one request per second'
SPARQL = 'https://query.wikidata.org/sparql?format=json&query='
COMMONS = 'https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url|extmetadata&titles='
TERRITORIES = {'60': 'AS', '66': 'GU', '69': 'MP', '72': 'PR', '78': 'VI'}


def sparql(key, q):
    path = os.path.join(CACHE, key + '.json')
    if not os.path.exists(path):
        time.sleep(1)
    fetch(key, url=SPARQL + urllib.parse.quote(q), fname=key + '.json')
    return json.load(open(path))['results']['bindings']


def qv(b, k):
    v = b.get(k, {}).get('value', '')
    return v.rsplit('/', 1)[-1] if v.startswith('http://www.wikidata.org/entity/') else v


def id_maps(gnis_ids):
    """identifier value -> set of QIDs, per property."""
    out = collections.defaultdict(lambda: collections.defaultdict(set))
    for prop in ('P5087', 'P882', 'P774'):
        for b in sparql('wd_ids_' + prop.lower(), 'SELECT ?i ?v WHERE { ?i wdt:%s ?v }' % prop):
            v = qv(b, 'v')
            if prop == 'P774':
                v = ''.join(c for c in v if c.isdigit())
            out[prop][v].add(qv(b, 'i'))
    ids = sorted({str(int(g)) for g in gnis_ids if g and g.isdigit()}, key=int)
    for k in range(0, len(ids), 400):
        chunk = ids[k:k + 400]
        q = 'SELECT ?i ?v WHERE { VALUES ?v { %s } ?i wdt:P590 ?v }' % ' '.join('"{}"'.format(c) for c in chunk)
        for b in sparql('wd_p590_{:05d}'.format(k // 400), q):
            out['P590'][qv(b, 'v')].add(qv(b, 'i'))
    return out


def assign_qids(states, local):
    gn = [r['gnis_id'] for r in local if r['type'] in ('county', 'municipality', 'township')]
    m = id_maps(gn)
    cand = {}
    for r in states:
        cand[r['entity_id']] = (m['P5087'].get(r['state_fips'], set()), 'qid_by_p5087')
    for r in local:
        t = r['type']
        if t == 'county' and r.get('geoid_layer') == 'counties':
            cand[r['entity_id']] = (m['P882'].get(r['geoid'], set()), 'qid_by_p882')
        elif t in ('municipality', 'township'):
            g = str(int(r['gnis_id'])) if r.get('gnis_id', '').isdigit() else ''
            a = m['P590'].get(g, set()) if g else set()
            if t == 'municipality' and r.get('geoid_layer') == 'place':
                b = m['P774'].get(r['geoid'], set())
                if a and b and a != b:
                    cand[r['entity_id']] = (set(), 'p774_p590_disagree')
                    continue
                cand[r['entity_id']] = ((b or a), 'qid_by_p774' if b else 'qid_by_p590')
            else:
                cand[r['entity_id']] = (a, 'qid_by_p590')
    use = collections.Counter(q for qs, _ in cand.values() if len(qs) == 1 for q in qs)
    stats = collections.Counter()
    rows = {r['entity_id']: r for r in states + local}
    for eid, (qs, how) in cand.items():
        r = rows[eid]
        if len(qs) == 1 and use[next(iter(qs))] == 1:
            r['wikidata_qid'] = next(iter(qs))
            r['flags'] = ';'.join(sorted(set(f for f in r.get('flags', '').split(';') if f) | {how}))
            r['source'] = ';'.join(dict.fromkeys(r['source'].split(';') + ['wikidata_ids']))
            stats[how] += 1
        else:
            why = how if how == 'p774_p590_disagree' else 'no_item' if not qs else 'multiple_items' if len(qs) > 1 else 'item_shared'
            r['_qid_gap'] = why
            stats['none:' + why] += 1
    terr = {ss: m['P5087'].get(ss, set()) for ss in TERRITORIES}
    return stats, terr


def commons_meta(files):
    out = {}
    files = sorted(set(files))
    for k in range(0, len(files), 50):
        chunk = files[k:k + 50]
        key = 'commons_{:05d}'.format(k // 50)
        path = os.path.join(CACHE, key + '.json')
        if not os.path.exists(path):
            time.sleep(1)
        fetch(key, url=COMMONS + urllib.parse.quote('|'.join('File:' + f for f in chunk)), fname=key + '.json')
        d = json.load(open(path))
        norm_map = {n['to']: n['from'] for n in d.get('query', {}).get('normalized', [])}
        for p in d.get('query', {}).get('pages', {}).values():
            title = norm_map.get(p.get('title'), p.get('title'))
            ii = (p.get('imageinfo') or [{}])[0]
            out[title[5:]] = {'url': ii.get('descriptionurl', ''), 'em': ii.get('extmetadata', {}), 'missing': 'missing' in p}
    return out


def claims(key, qids, props):
    """QID -> {prop: [Commons file names]} for the given properties, batched."""
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    qids = sorted(set(qids), key=lambda q: int(q[1:]))
    for k in range(0, len(qids), 400):
        chunk = qids[k:k + 400]
        opt = ' '.join('OPTIONAL {{ ?i wdt:{0} ?{0} }}'.format(p) for p in props)
        q = 'SELECT ?i %s WHERE { VALUES ?i { %s } %s }' % (' '.join('?' + p for p in props), ' '.join('wd:' + c for c in chunk), opt)
        for b in sparql('{}_{:05d}'.format(key, k // 400), q):
            for p in props:
                v = b.get(p, {}).get('value', '')
                if v:
                    f = urllib.parse.unquote(v.rsplit('/Special:FilePath/', 1)[-1])
                    if f not in out[qv(b, 'i')][p]:
                        out[qv(b, 'i')][p].append(f)
    return out


WD_API = 'https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=sitelinks&sitefilter=enwiki&ids='
EN_API = 'https://en.wikipedia.org/w/api.php?format=json&action=query'


def _get(key, url):
    path = os.path.join(CACHE, key + '.json')
    if not os.path.exists(path):
        time.sleep(1)
    fetch(key, url=url, fname=key + '.json')
    return json.load(open(path))


def enwiki_seals(qids, exclude=frozenset()):
    """Fallback for items without P158: the seal file shown in the item's own English Wikipedia article (the article
    is the item's enwiki sitelink, so the entity link is exact). Exactly one file whose name contains 'seal' must be on
    the page, appear on no other fetched article, and not be another item's P158 seal; otherwise nothing. Returns QID -> {file, page, source_url, em, local} (local = hosted on enwiki,
    i.e. a non-free / fair-use upload)."""
    qids = sorted(set(qids), key=lambda q: int(q[1:]))
    title_of = {}
    for k in range(0, len(qids), 50):
        d = _get('enwd_sl_{:05d}'.format(k // 50), WD_API + '|'.join(qids[k:k + 50]))
        for q, e in d.get('entities', {}).items():
            t = e.get('sitelinks', {}).get('enwiki', {}).get('title')
            if t:
                title_of[q] = t
    titles = sorted(set(title_of.values()))
    files_of = collections.defaultdict(set)
    for k in range(0, len(titles), 50):
        chunk = titles[k:k + 50]
        cont, n = '', 0
        while True:
            url = EN_API + '&prop=images&imlimit=max&redirects=1&titles=' + urllib.parse.quote('|'.join(chunk)) + cont
            d = _get('enwp_img_{:05d}_{}'.format(k // 50, n), url)
            red = {r['from']: r['to'] for r in d.get('query', {}).get('redirects', [])}
            nor = {r['from']: r['to'] for r in d.get('query', {}).get('normalized', [])}
            back = {}
            for t in chunk:
                back[red.get(nor.get(t, t), nor.get(t, t))] = t
            for p in d.get('query', {}).get('pages', {}).values():
                for im in p.get('images', []):
                    files_of[back.get(p['title'], p['title'])].add(im['title'])
            if 'continue' not in d:
                break
            cont = ''.join('&{}={}'.format(a, urllib.parse.quote(str(b))) for a, b in d['continue'].items())
            n += 1
    # a file shown on more than one of these articles is a navbox / shared image (e.g. a state seal), never the entity's
    on_pages = collections.Counter(f for fs in files_of.values() for f in fs)
    pick = {}
    for q, t in title_of.items():
        seals = sorted(f for f in files_of.get(t, ()) if 'seal' in f.lower() and on_pages[f] == 1 and f[5:] not in exclude)
        if len(seals) == 1:
            pick[q] = (t, seals[0])
    fl = sorted({f for _, f in pick.values()})
    info = {}
    for k in range(0, len(fl), 50):
        url = EN_API + '&prop=imageinfo&iiprop=url|extmetadata&titles=' + urllib.parse.quote('|'.join(fl[k:k + 50]))
        d = _get('enwp_ii_{:05d}'.format(k // 50), url)
        nor = {r['to']: r['from'] for r in d.get('query', {}).get('normalized', [])}
        for p in d.get('query', {}).get('pages', {}).values():
            ii = (p.get('imageinfo') or [{}])[0]
            info[nor.get(p['title'], p['title'])] = {'url': ii.get('descriptionurl', ''), 'em': ii.get('extmetadata', {}),
                                                     'local': p.get('imagerepository') == 'local'}
    out = {}
    for q, (t, f) in pick.items():
        i = info.get(f)
        if i and i['url']:
            out[q] = dict(i, file=f[5:], page='https://en.wikipedia.org/wiki/' + urllib.parse.quote(t.replace(' ', '_')))
    return out
