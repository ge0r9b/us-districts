"""Shared source registry for data-v3/inst (same file on data/inst-officeholders and data/inst-entities).

data-v3/inst/sources.csv: source_id, source, source_url, license, retrieved_at, commit, sha256
source_id = '<slug>-<h8>', h8 = first 8 hex of sha256(source_url + '|' + commit). Deterministic, never sequential:
the same URL(s) + commit always give the same id, on any machine, in any build order. The slug is a readable prefix
derived from the source (publisher / dataset), not from row order.
"""
import csv, hashlib, os, re
COLS = ['source_id', 'source', 'source_url', 'license', 'retrieved_at', 'commit', 'sha256']

def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:40]

def make_id(slug, url, commit=''):
    h = hashlib.sha256(('%s|%s' % (url.strip(), (commit or '').strip())).encode('utf-8')).hexdigest()[:8]
    return '%s-%s' % (slugify(slug), h)

# Canonical slugs for sources both branches cite, so the same source gets the same id everywhere.
CANON = [
    (r'gus/datasets/2022/govt_units_2022', 'census-cog2022'),
    (r'gazetteer/(\d{4})_Gazetteer/\d{4}_Gaz_(\w+?)_national', lambda m: 'census-gaz%s-%s' % (m.group(1), m.group(2))),
    (r'tiger/TIGER(\d{4})/COUSUB/ ; .*TIGER\d{4}/PLACE/', lambda m: 'census-tiger%s-cousub-place' % m.group(1)),
    (r'tiger/TIGER(\d{4})/(\w+)/?$', lambda m: 'census-tiger%s-%s' % (m.group(1), m.group(2).lower())),
    (r'census\.gov/library/reference/code-lists/ansi', 'census-ansi-codes'),
    (r'archives\.gov/founding-docs/constitution', 'us-constitution'),
    (r'code\.dccouncil\.gov', 'dc-code-home-rule'),
    (r'github\.com/openstates/people', 'openstates-people'),
    (r'github\.com/unitedstates/congress-legislators', 'congress-legislators'),
    (r'clerk\.house\.gov/xml/lists/MemberData', 'house-clerk-memberdata'),
    (r'query\.wikidata\.org/sparql', 'wikidata-sparql'),
    (r'github\.com/ge0r9b/us-districts/(?:blob|tree)/[0-9a-f]+/(\S+)', lambda m: 'repo-' + m.group(1).rsplit('/', 1)[-1].split('.')[0]),
]
def slug_for(url):
    for pat, s in CANON:
        m = re.search(pat, url)
        if m: return s(m) if callable(s) else s
    return None

class Registry:
    def __init__(self):
        self.rows = {}
    def add(self, slug, source, url, license='', retrieved_at='', commit='', sha256=''):
        slug = slug_for(url) or slug
        assert slug, ('no slug for', url)
        sid = make_id(slug, url, commit)
        new = {'source_id': sid, 'source': source, 'source_url': url, 'license': license, 'retrieved_at': retrieved_at,
               'commit': commit or '', 'sha256': sha256 or ''}
        old = self.rows.get(sid)
        if old:
            for k in ('source_url', 'commit'):
                assert old[k] == new[k], ('source_id collision', sid, old, new)
            for k in ('source', 'license', 'retrieved_at', 'sha256'):   # fill blanks; two different non-empty values = error
                if old[k] and new[k]: assert old[k] == new[k], ('source_id conflict', sid, k, old[k], new[k])
                elif new[k]: old[k] = new[k]
        else:
            self.rows[sid] = new
        return sid
    def load(self, path_or_text, text=False):
        rows = csv.DictReader(path_or_text.splitlines() if text else open(path_or_text, encoding='utf-8'))
        for r in rows:
            self.rows.setdefault(r['source_id'], {c: r.get(c, '') for c in COLS})
    def check_ids(self):
        """stability test part 1: every id re-derives from its own url + commit."""
        bad = [sid for sid, r in self.rows.items() if make_id(sid.rsplit('-', 1)[0], r['source_url'], r['commit']) != sid
               or (slug_for(r['source_url']) and slugify(slug_for(r['source_url'])) != sid.rsplit('-', 1)[0])]
        assert not bad, ('unstable source ids', bad[:5])
        return len(self.rows)
    def write(self, path, keep_existing=True):
        if keep_existing and os.path.exists(path):
            self.load(path)
        with open(path, 'w', encoding='utf-8', newline='') as fh:
            w = csv.DictWriter(fh, COLS, lineterminator='\n'); w.writeheader()
            for sid in sorted(self.rows): w.writerow(self.rows[sid])
