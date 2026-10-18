"""Wikidata QIDs from exact identifier links, and seal/flag image records from Wikidata + Wikimedia Commons.

QIDs (never from names):
  state         P5087 FIPS 5-2 numeric code      = state FIPS
  county        P882  FIPS 6-4                   = county GEOID (SSCCC)
  municipality  P774  FIPS 55-3 (digits only)    = place GEOID (SSPPPPP), and/or P590 GNIS ID = TIGER ANSI code
  township      P590  GNIS ID                    = TIGER ANSI code (P774 is not used: MCD and place codes collide)
  tribe         kept from tribes.csv (exact BIA-name = label/P1448 rule of part A)
  nation        Q30 for nation:us (fixed)
A QID is set only when exactly one item links to the entity and that item links to no other entity; if P774 and P590
disagree nothing is set. Federal agencies: Wikidata has no Federal Register agency-ID property, so the link is the
agency's official website: the Federal Register API `agency_url` must equal an item's P856 (official website) exactly
after normalisation (scheme, leading www., trailing slash, query and fragment dropped; host + path compared). Same
uniqueness rule. P1813 (short name) is a name, so it is never used.

Images: P158 (seal image) for every entity with a QID except school districts; P41 (flag image) for the nation,
states, DC and territories whose P5087 code is in Wikidata. License/author from Commons imageinfo extmetadata.
Only URLs and metadata are written; no image files.
"""
import collections, hashlib, json, os, re, time, urllib.parse
from common import CACHE, fetch, meta

UA_NOTE = 'batched SPARQL (VALUES <= 400) and Commons API (50 titles/request), one request per second'
SPARQL = 'https://query.wikidata.org/sparql?format=json&query='
COMMONS = 'https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url|extmetadata&titles='
TERRITORIES = {'60': 'AS', '66': 'GU', '69': 'MP', '72': 'PR', '78': 'VI'}


def hkey(prefix, url):
    """cache key = prefix + hash of the request, so a changed batch never reuses another batch's cached answer"""
    return '{}_{}'.format(prefix, hashlib.sha1(url.encode()).hexdigest()[:16])


def sparql(key, q, batched=False):
    if batched:
        key = hkey(key, q)
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
        for b in sparql('wd_p590', q, True):
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


def norm_url(u):
    """host + path, lowercased host, no scheme / leading www. / trailing slash / query / fragment"""
    p = urllib.parse.urlsplit(u.strip())
    host = p.netloc.lower().split('@')[-1].split(':')[0]
    host = host[4:] if host.startswith('www.') else host
    path = urllib.parse.unquote(p.path).rstrip('/')
    return host + path if host else ''


# reviewed: the Federal Register agency_url points at a different agency, so the exact link is wrong at the source
AGENCY_URL_REJECTS = {'fr:334': 'FR agency_url nctc.gov is the National Counterterrorism Center, not the National Counterintelligence Center'}


def agency_qids(fed, fr_agencies):
    """QIDs for federal agencies whose FR agency_url equals one Wikidata item's P856 (normalised host + path)."""
    url_of = {'fr:{}'.format(a['id']): a.get('agency_url') or '' for a in fr_agencies}
    want = {}
    for r in fed:
        n = norm_url(url_of.get(r['entity_id'], ''))
        if n:
            want[r['entity_id']] = n
    variants = sorted({'{}://{}{}{}'.format(s, w, n, sl) for n in set(want.values()) for s in ('http', 'https')
                       for w in ('', 'www.') for sl in ('', '/')})
    items = collections.defaultdict(set)
    for k in range(0, len(variants), 100):
        q = 'SELECT ?i ?w WHERE { VALUES ?w { %s } ?i wdt:P856 ?w }' % ' '.join('<{}>'.format(v) for v in variants[k:k + 100])
        for b in sparql('wd_p856', q, True):
            items[norm_url(qv(b, 'w'))].add(qv(b, 'i'))
    # the item must be an organisation (P31/P279* Q43229): P856 also sits on offices, positions and CFR titles
    cands = sorted({q for qs in items.values() for q in qs}, key=lambda q: int(q[1:]))
    org = set()
    for k in range(0, len(cands), 100):
        q = 'SELECT DISTINCT ?i WHERE { VALUES ?i { %s } ?i wdt:P31/wdt:P279* wd:Q43229 }' % ' '.join('wd:' + c for c in cands[k:k + 100])
        org |= {qv(b, 'i') for b in sparql('wd_p856org', q, True)}
    items = {n: {q for q in qs if q in org} for n, qs in items.items()}
    use = collections.Counter(q for n in set(want.values()) if len(items.get(n, ())) == 1 for q in items[n])
    by_url = collections.Counter(want.values())
    stats = collections.Counter()
    for r in fed:
        n = want.get(r['entity_id'])
        if r['entity_id'] in AGENCY_URL_REJECTS:
            r['_qid_gap'] = 'agency_url_rejected: ' + AGENCY_URL_REJECTS[r['entity_id']]
            stats['none:agency_url_rejected'] += 1
            continue
        if not n:
            r['_qid_gap'] = 'no_agency_url'
            stats['none:no_agency_url'] += 1
            continue
        qs = items.get(n, set())
        if len(qs) == 1 and use[next(iter(qs))] == 1 and by_url[n] == 1:
            r['wikidata_qid'] = next(iter(qs))
            r['flags'] = ';'.join(sorted(set(f for f in r.get('flags', '').split(';') if f) | {'qid_by_p856'}))
            r['source'] = ';'.join(dict.fromkeys(r['source'].split(';') + ['wikidata_ids']))
            stats['qid_by_p856'] += 1
        else:
            why = 'no_item' if not qs else 'multiple_items' if len(qs) > 1 else 'url_shared'
            r['_qid_gap'] = why
            stats['none:' + why] += 1
    return stats


def commons_meta(files, prefix='commons'):
    out = {}
    files = sorted(set(files))
    for k in range(0, len(files), 50):
        chunk = files[k:k + 50]
        d = _get(prefix, COMMONS + urllib.parse.quote('|'.join('File:' + f for f in chunk)))
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
        for b in sparql(key, q, True):
            for p in props:
                v = b.get(p, {}).get('value', '')
                if v:
                    f = urllib.parse.unquote(v.rsplit('/Special:FilePath/', 1)[-1])
                    if f not in out[qv(b, 'i')][p]:
                        out[qv(b, 'i')][p].append(f)
    return out


WD_API = 'https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=sitelinks&sitefilter=enwiki&ids='
EN_API = 'https://en.wikipedia.org/w/api.php?format=json&action=query'


def _get(prefix, url):
    key = hkey(prefix, url)
    path = os.path.join(CACHE, key + '.json')
    if not os.path.exists(path):
        time.sleep(1)
    fetch(key, url=url, fname=key + '.json')
    return json.load(open(path))


_STATE_WORDS = None


def _state_seal_name(f):
    """True for a file named only for a state (e.g. 'File:Seal utah.png', 'File:Seal of the State of Ohio.svg'): a
    state seal shown on a single city article is still the state's, not the city's."""
    global _STATE_WORDS
    if _STATE_WORDS is None:
        from common import state_table
        _STATE_WORDS = {re.sub('[^a-z]', '', n.lower()) for _, n, _ in state_table().values()} | \
                       {u.lower() for u, _, _ in state_table().values()}
    stem = re.sub(r'\.[a-z0-9]+$', '', f[5:].lower())
    words = [w for w in re.split(r'[^a-z]+', stem) if w and w not in ('seal', 'of', 'the', 'state', 'great', 'official', 'commonwealth', 'svg', 'png')]
    return bool(words) and ''.join(words) in _STATE_WORDS


def enwiki_seals(qids, exclude=frozenset()):
    """Fallback for items without P158: the seal file shown in the item's own English Wikipedia article (the article
    is the item's enwiki sitelink, so the entity link is exact). Exactly one file whose name contains 'seal' must be on
    the page, appear on no other fetched article, and not be another item's P158 seal; otherwise nothing. Returns QID -> {file, page, source_url, em, local} (local = hosted on enwiki,
    i.e. a non-free / fair-use upload)."""
    qids = sorted(set(qids), key=lambda q: int(q[1:]))
    title_of = {}
    for k in range(0, len(qids), 50):
        d = _get('enwd_sl', WD_API + '|'.join(qids[k:k + 50]))
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
            d = _get('enwp_img', url)
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
        seals = sorted(f for f in files_of.get(t, ()) if 'seal' in f.lower() and on_pages[f] == 1 and f[5:] not in exclude
                       and not _state_seal_name(f))
        if len(seals) == 1:
            pick[q] = (t, seals[0])
    fl = sorted({f for _, f in pick.values()})
    info = {}
    for k in range(0, len(fl), 50):
        url = EN_API + '&prop=imageinfo&iiprop=url|extmetadata&titles=' + urllib.parse.quote('|'.join(fl[k:k + 50]))
        d = _get('enwp_ii', url)
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

