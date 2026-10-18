"""Explicit image overrides for entity_images.csv (Full Stack, Oct 18). Builder-only; never written to data-v3/institutions/.

An override swaps one feed image file for another Commons file of the same subject. It is applied only when
  * the feed row (entity_id, role) still carries `old_file`, and
  * the new file's cached Commons answers (tools/inst_commons.py v3/v4 cache) show a machine-readable free licence
    template (+ 'License template tag'), no deletion / no-machine-readable category, a LicenseShortName and an Artist.
It DROPS ITSELF (logged, nothing changed) once the feed already points at `new_file` for that entity and role, and is
logged as not_applicable when the feed row carries some third file. Every outcome goes to entities_summary.json
`image_overrides`; an applied override writes `note` on the row.

NO_REPLACEMENT lists rows that were searched for a replacement and have none; the reason is appended to the row's gap.
"""
import re
OVERRIDES = [
    {'entity_id': 'province:ca-qc', 'role': 'seal', 'old_file': 'Coat of arms of Quebec (without crown).svg', 'new_file': 'Coat of arms of Quebec.svg',
     'why': 'old file: no machine-readable licence, open deletion request May 2026; new file: the file the old one says it was extracted from ({{Extracted from}})'},
]
NO_REPLACEMENT = {
    ('subdivision:jp-34', 'flag'): 'no replacement on Commons: search intitle:flag intitle:Hiroshima (50 hits, all municipal flags) and Category:Prefectural flag of Hiroshima '
                                    'prefecture (3 files: this one and two flag-map stub images, Hiroshima-geo-stub.png/.svg) have no other prefectural flag file; kept private',
}
LIC_T = re.compile(r'Template:(PD-|Cc-|CC-|Cc0|Cc-zero|GFDL|FAL)')

def check(page, text):
    """page: a cached Commons query page (templates, categories, imageinfo). Returns (ok, fields or reason)."""
    if not page: return False, 'new file not in the Commons cache'
    tpl = [x['title'] for x in page.get('templates', [])]
    lic = [x for x in tpl if LIC_T.match(x)]
    bad = [c['title'] for c in page.get('categories', []) if 'machine-readable' in c['title'] or 'eletion' in c['title']]
    ii = (page.get('imageinfo') or [{}])[0]; em = ii.get('extmetadata') or {}
    if isinstance(em, list): em = {}
    g = lambda k: text((em.get(k) or {}).get('value', ''))
    if not lic or 'Template:License template tag' not in tpl: return False, 'no machine-readable licence template'
    if bad: return False, 'category ' + ', '.join(bad)
    if not g('LicenseShortName') or not g('Artist'): return False, 'no LicenseShortName or Artist'
    return True, {'descriptionurl': ii['descriptionurl'], 'License': g('License'), 'LicenseUrl': g('LicenseUrl'), 'Artist': g('Artist'), 'template': lic[0][len('Template:'):]}

def apply(imgs, pages, text, spdx):
    """imgs: image rows (mutable). pages: {'File:<name>': cached page}. Returns the log list."""
    log = []
    for o in OVERRIDES:
        rows = [i for i in imgs if i['entity_id'] == o['entity_id'] and i['role'] == o['role']]
        k = f"{o['entity_id']}|{o['role']}"
        if any(i['file'] == o['new_file'] for i in rows):
            log.append({'override': k, 'outcome': 'dropped', 'detail': f"feed already points at {o['new_file']}; override no longer needed"}); continue
        hit = [i for i in rows if i['file'] == o['old_file']]
        if not hit:
            log.append({'override': k, 'outcome': 'not_applicable', 'detail': 'feed row carries ' + (';'.join(i['file'] for i in rows) or 'no row')}); continue
        ok, f = check(pages.get('File:' + o['new_file']), text)
        if not ok:
            log.append({'override': k, 'outcome': 'not_applied', 'detail': f}); continue
        for i in hit:
            i.update(file=o['new_file'], commons_url=f['descriptionurl'], source_url=f['descriptionurl'], license=spdx(f['License']), attribution=f['Artist'],
                     attribution_source='commons_artist', licence_url=f['LicenseUrl'],
                     note=f"override (tools/inst_image_overrides.py): replaces {o['old_file']} with {o['new_file']} ({{{{{f['template']}}}}}); {o['why']}"); i['_cm'] = True
        log.append({'override': k, 'outcome': 'applied', 'detail': f"{o['old_file']} -> {o['new_file']}"})
    return log
