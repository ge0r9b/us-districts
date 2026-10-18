"""Wikimedia Commons imageinfo/extmetadata cache for entity_images.csv backfill (Full Stack, Oct 18).

fetch:  python3 tools/inst_commons.py fetch --images data-v3/inst/entity_images.csv --out DIR
        Picks the Commons files of free (public) image rows missing source_url, attribution or license, plus every free row
        whose licence is LicenseRef-Copyrighted-free-use / LicenseRef-Attribution; queries the public Commons API
        (action=query, prop=imageinfo, iiprop=url|extmetadata, 50 titles per request, maxlag=5, 2 s between requests,
        identifying User-Agent; backs off on 429 / maxlag; stops on 403 and writes nothing for the rest). Writes
        titles.txt, batch_NNNN.json (raw API answers), retrieved_at.txt and SHA256SUMS. Builds read only the cache.
fetch-v2 (Full Stack, Oct 18, second ruling): python3 tools/inst_commons.py fetch-v2 --images ... --out DIR
        Re-queries, with the extra fields License / UsageTerms / Copyrighted, the free rows still missing attribution or
        licence and the free rows whose attribution is only "Unknown" (UNKNOWN_RE); and for the files in PAGES reads the
        file page itself (prop=revisions wikitext + categories + templates). Files: v2_titles.txt, v2_batch_NNNN.json,
        v2_page_NNNN.json; SHA256SUMS is rewritten over every cache file. v2 answers override v1 for the same title.
load:   info(DIR) -> {file name (spaces, no 'File:'): {'descriptionurl', 'Artist', 'Credit', 'LicenseShortName'}} (plain text:
        HTML tags removed, entities unescaped, whitespace collapsed), plus the sha256 of SHA256SUMS.
"""
import csv, hashlib, html, json, os, re, sys, time, urllib.parse, urllib.request
API = 'https://commons.wikimedia.org/w/api.php'
UA = 'us-districts-inst-lane/1.0 (https://github.com/ge0r9b/us-districts; institution registry image metadata backfill)'
KEEP_ATTR_LIC = ('LicenseRef-Copyrighted-free-use', 'LicenseRef-Attribution')
UNKNOWN_RE = re.compile(r'(?i)^[\s.,;:()]*((unknown|author|artist)[\s.,;:()]*)+$')   # 'Unknown', 'Unknown author Unknown author', 'Author unknown'
def is_unknown(a): return bool(a) and bool(UNKNOWN_RE.match(a))
PAGES = ['Coat of arms of Quebec (without crown).svg', 'Flag of Hiroshima Prefecture.svg']   # province:ca-qc arms, subdivision:jp-34 flag

def norm(f): return f.replace('_', ' ').strip()

def wanted(images_csv):
    out = set()
    for x in csv.DictReader(open(images_csv, encoding='utf-8')):
        if x['public'] != 'yes' or not x['file']: continue
        if not (x['source_url'] and x['attribution'] and x['license']) or x['license'] in KEEP_ATTR_LIC: out.add(norm(x['file']))
    return sorted(out)

def wanted_v2(images_csv):
    out = set()
    for x in csv.DictReader(open(images_csv, encoding='utf-8')):
        if x['fair_use'] != 'no' or not x['file']: continue
        if not x['attribution'] or not x['license'] or is_unknown(x['attribution']) or x['public'] == 'no': out.add(norm(x['file']))
    return sorted(out | set(PAGES))

def _get(params):
    q = urllib.parse.urlencode(dict(params, format='json', formatversion='2', maxlag='5'))
    for attempt in range(6):
        req = urllib.request.Request(API + '?' + q, headers={'User-Agent': UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r: body = r.read()
        except urllib.error.HTTPError as e:
            if e.code == 403: sys.exit('BLOCKED: HTTP 403; stopped, not retried')
            if e.code in (429, 503): time.sleep(int(e.headers.get('Retry-After') or 30)); continue
            raise
        if json.loads(body).get('error', {}).get('code') == 'maxlag': time.sleep(10); continue
        time.sleep(2); return body
    sys.exit('gave up')

def sums(out):
    names = sorted(f for f in os.listdir(out) if f != 'SHA256SUMS')
    open(os.path.join(out, 'SHA256SUMS'), 'w').write(''.join(f'{hashlib.sha256(open(os.path.join(out, f), "rb").read()).hexdigest()}  {f}\n' for f in names))

def fetch_v2(images_csv, out):
    titles = wanted_v2(images_csv)
    open(os.path.join(out, 'v2_titles.txt'), 'w', encoding='utf-8').write('\n'.join(titles) + '\n')
    for b in range(0, len(titles), 50):
        body = _get({'action': 'query', 'prop': 'imageinfo', 'iiprop': 'url|extmetadata', 'iiextmetadatafilter': 'Artist|Credit|LicenseShortName|License|UsageTerms|Copyrighted',
                     'titles': '|'.join('File:' + t for t in titles[b:b + 50])})
        open(os.path.join(out, f'v2_batch_{b // 50:04d}.json'), 'wb').write(body)
    for n, t in enumerate(PAGES):
        body = _get({'action': 'query', 'prop': 'revisions|categories|templates', 'rvprop': 'content|ids', 'rvslots': 'main', 'cllimit': 'max', 'tllimit': 'max', 'titles': 'File:' + t})
        open(os.path.join(out, f'v2_page_{n:04d}.json'), 'wb').write(body)
    open(os.path.join(out, 'v2_retrieved_at.txt'), 'w').write(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) + '\n')
    sums(out); print(len(titles), 'titles')

def pages(d):
    res = {}
    for f in sorted(x for x in os.listdir(d) if x.startswith('v2_page_')):
        for p in json.load(open(os.path.join(d, f), encoding='utf-8'))['query']['pages']:
            rv = (p.get('revisions') or [{}])[0]
            res[p['title'][len('File:'):]] = {'revid': rv.get('revid'), 'wikitext': rv.get('slots', {}).get('main', {}).get('content', ''),
                                              'categories': [c['title'] for c in p.get('categories', [])], 'templates': [t['title'] for t in p.get('templates', [])]}
    return res

def text(v):
    v = re.sub(r'<[^>]+>', ' ', v or ''); v = html.unescape(v)
    return re.sub(r'\s+', ' ', v).strip()

def fetch(images_csv, out):
    titles = wanted(images_csv); os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'titles.txt'), 'w', encoding='utf-8').write('\n'.join(titles) + '\n')
    n = 0
    for b in range(0, len(titles), 50):
        chunk = titles[b:b + 50]
        q = urllib.parse.urlencode({'action': 'query', 'format': 'json', 'formatversion': '2', 'prop': 'imageinfo', 'iiprop': 'url|extmetadata',
                                    'iiextmetadatafilter': 'Artist|Credit|LicenseShortName', 'maxlag': '5', 'titles': '|'.join('File:' + t for t in chunk)})
        for attempt in range(6):
            req = urllib.request.Request(API + '?' + q, headers={'User-Agent': UA})
            try:
                with urllib.request.urlopen(req, timeout=60) as r: body = r.read()
            except urllib.error.HTTPError as e:
                if e.code == 403: sys.exit(f'BLOCKED: HTTP 403 at batch {b // 50}; stopped, not retried')
                if e.code in (429, 503): time.sleep(int(e.headers.get('Retry-After') or 30)); continue
                raise
            j = json.loads(body)
            if j.get('error', {}).get('code') == 'maxlag': time.sleep(10); continue
            break
        else: sys.exit(f'gave up at batch {b // 50}')
        open(os.path.join(out, f'batch_{b // 50:04d}.json'), 'wb').write(body); n += 1
        time.sleep(2)
    open(os.path.join(out, 'retrieved_at.txt'), 'w').write(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) + '\n')
    names = sorted(f for f in os.listdir(out) if f != 'SHA256SUMS')
    open(os.path.join(out, 'SHA256SUMS'), 'w').write(''.join(f'{hashlib.sha256(open(os.path.join(out, f), "rb").read()).hexdigest()}  {f}\n' for f in names))
    print(len(titles), 'titles', n, 'batches')

def info(d):
    sums = open(os.path.join(d, 'SHA256SUMS'), 'rb').read()
    for line in sums.decode().splitlines():
        h, f = line.split('  ', 1); assert hashlib.sha256(open(os.path.join(d, f), 'rb').read()).hexdigest() == h, f
    res = {}
    for f in sorted(x for x in os.listdir(d) if x.startswith('batch_')) + sorted(x for x in os.listdir(d) if x.startswith('v2_batch_')):
        j = json.load(open(os.path.join(d, f), encoding='utf-8'))
        nm = {x['to']: x['from'] for x in j.get('query', {}).get('normalized', [])}
        for p in j.get('query', {}).get('pages', []):
            t = p['title'][len('File:'):]
            ii = (p.get('imageinfo') or [{}])[0]; em = ii.get('extmetadata', {})
            rec = {'descriptionurl': ii.get('descriptionurl', ''), 'missing': bool(p.get('missing')),
                   **{k: text(em.get(k, {}).get('value', '')) for k in ('Artist', 'Credit', 'LicenseShortName', 'License', 'UsageTerms', 'Copyrighted')}}
            for k in {t, norm(nm.get(p['title'], p['title'])[len('File:'):])}: res[k] = rec
    return res, hashlib.sha256(sums).hexdigest(), open(os.path.join(d, 'retrieved_at.txt')).read().strip()

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('--images'); ap.add_argument('--out')
    a = ap.parse_args(); assert a.cmd in ('fetch', 'fetch-v2')
    (fetch if a.cmd == 'fetch' else fetch_v2)(a.images, a.out)
