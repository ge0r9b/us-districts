"""UK local and devolved government units (foreign/gb/): every council level with its GSS code.

Sources (all ONS, Open Government Licence v3.0):
  * Register of Geographic Codes (RGC) June 2026: live GSS codes, English and Welsh names, operative/termination dates and
    parent codes for E04 civil parishes, W04 communities, E06/E07/E08/E09/W06 local authorities, E10 counties,
    E47 combined authorities, E61 Greater London Authority, N09 NI local government districts.
  * WD26_LAD26_CTYUA26_RGN26_CTRY26_UK_LU (ward-to-LAD lookup, May 2026): S12 Scottish council areas (the RGC
    workbook carries no Scottish entity sheets) and a cross-check of the live LAD set.
  * LAD25_CAUTH25_EN_LU (May 2025): which combined authority area each local authority district lies in.
  * Attribute tables (no geometry) of the BFC boundary services Geo builds from (FOREIGN_VINTAGES.md), for boundary_xwalk.csv.
Units: one row per council area; the existing nation:gb and subdivision:gb-eng/sct/wls/nir rows are reused (crosswalk),
never re-minted. New IDs: gss:<GSS code> (frozen in id_registry/gb.csv).
"""
import collections, os, sys
import openpyxl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CACHE, ROOT, Registry, fetch, manifest, write_csv
from wikidata import sparql, qv
from foreign_local import (FOREIGN, LOCAL_COLUMNS, CODE_XW_COLUMNS, BOUNDARY_COLUMNS, arcgis, check, existing_foreign,
                           write_split)

OUT = os.path.join(FOREIGN, 'gb')
OGL = 'Open Government Licence v3.0 (ONS; contains public sector information licensed under the OGL)'
ARC = 'https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services'
RGC_ITEM = 'ef9bb98c8c62471684aaf42b8898f220'
RGC_URL = 'https://www.arcgis.com/sharing/rest/content/items/{}/data'.format(RGC_ITEM)
RGC_PAGE = 'https://geoportal.statistics.gov.uk/datasets/{}'.format(RGC_ITEM)
RGC_FILE = 'Register_of_Geographic_Codes_(June_2026)_UK.xlsx'
RGC_DATE = '2026-06-24'          # date of the workbook inside the zip
# ONS Code History Database (June 2026): Changes.csv = each code with the code(s) it replaced (GEOGCD_P), with the order
CHD_ITEM = 'e0bc41722b1a4b76a6ecfff14f91cbb4'
CHD_URL = 'https://www.arcgis.com/sharing/rest/content/items/{}/data'.format(CHD_ITEM)
CHD_PAGE = 'https://geoportal.statistics.gov.uk/datasets/{}'.format(CHD_ITEM)
LU_WD26 = 'WD26_LAD26_CTYUA26_RGN26_CTRY26_UK_LU'
LU_CAUTH = 'LAD25_CAUTH25_EN_LU'
# entity -> (subtype, gov_status, note)
ENTITIES = {
    'E61': ('strategic_authority', 'self_governing', 'Greater London Authority (Mayor of London and London Assembly)'),
    'E47': ('combined_authority', 'self_governing', 'combined authority or combined county authority (RGC E47 CAUTH)'),
    'E10': ('county_council', 'self_governing', 'two-tier county (RGC E10 CTY)'),
    'E06': ('unitary_authority', 'self_governing', ''),
    'E07': ('non_metropolitan_district', 'self_governing', ''),
    'E08': ('metropolitan_borough', 'self_governing', ''),
    'E09': ('london_borough', 'self_governing', ''),
    'W06': ('principal_council', 'self_governing', 'Welsh unitary authority (principal council)'),
    'S12': ('council_area', 'self_governing', 'Scottish council area'),
    'N09': ('district_council', 'self_governing', 'Northern Ireland local government district'),
    'E04': ('civil_parish', 'parish', 'civil parish; may have a parish/town council or only a parish meeting (RGC does not say which)'),
    'W04': ('community', 'parish', 'community; may or may not have a community/town council (RGC does not say which)'),
}
LAD = ('E06', 'E07', 'E08', 'E09', 'W06', 'S12', 'N09')
COUNTRY = {'E92000001': 'subdivision:gb-eng', 'S92000003': 'subdivision:gb-sct', 'W92000004': 'subdivision:gb-wls',
           'N92000002': 'subdivision:gb-nir', 'K02000001': 'nation:gb'}
DEVOLVED = {'E': 'nation:gb', 'S': 'subdivision:gb-sct', 'W': 'subdivision:gb-wls', 'N': 'subdivision:gb-nir'}
# Geo's exact editions (data/geo data-v3/geo/FOREIGN_VINTAGES.md): (boundary_dataset, ONS service, layer id, code field,
# vintage, entity prefixes). Presence of every code is checked against the service's attribute table.
GEO_VINTAGES = 'data/geo:data-v3/geo/FOREIGN_VINTAGES.md'
BOUNDARIES = [
    ('ONS LAD_MAY_2026_UK_BFC', 'Local_Authority_Districts_May_2026_Boundaries_UK_BFC', 0, 'LAD26CD', '2026-05', LAD),
    ('ONS CTYUA_DEC_2025_UK_BFC', 'Counties_and_Unitary_Authorities_December_2025_Boundaries_UK_BFC', 0, 'CTYUA25CD', '2025-12', ('E10',)),
    ('ONS CAUTH_DEC_2025_EN_BFC', 'Combined_Authorities_December_2025_Boundaries_EN_BFC', 1, 'CAUTH25CD', '2025-12', ('E47',)),
    ('ONS PARNCP_MAY_2026_EW_BFC', 'PARNCP_MAY_2026_EW_BFC', 0, 'PARNCP26CD', '2026-05', ('E04', 'W04')),
]
LONDON_RGN = 'E12000007'


def d(v):
    return v.date().isoformat() if hasattr(v, 'date') else (v or '')


def rgc():
    fetch('ons_rgc', url=RGC_URL, fname='ons_rgc_jun2026.zip')
    wb = openpyxl.load_workbook(os.path.join(CACHE, RGC_FILE), read_only=True)
    out = {}
    for ws in wb.worksheets:
        if ws.title[:3] in ENTITIES:
            it = ws.iter_rows(values_only=True)
            h = next(it)
            out[ws.title[:3]] = [dict(zip(h, r)) for r in it if r and r[0]]
    return out


def chd_changes():
    """(code, predecessor code, SI title, operative date) rows of the CHD Changes table (zip kept unextracted)."""
    import csv, io, zipfile
    p = fetch('ons_chd', url=CHD_URL, fname='ons_chd_jun2026.zipdata')
    with zipfile.ZipFile(p) as z:
        raw = z.read('Changes.csv')
    txt = raw.decode('utf-8-sig', errors='replace')   # mixed encodings in a few names; only codes and dates are used
    return [(r['GEOGCD'], r['GEOGCD_P'], r['SI_TITLE'] or '', r['OPER_DATE'][:10]) for r in csv.DictReader(io.StringIO(txt))]


def gss_qids():
    """Wikidata items by exact GSS code (P836) and their ISO 3166-2 code (P300); only 1:1 links are used."""
    bs = sparql('wd_gss', 'SELECT ?i ?g ?iso WHERE { ?i wdt:P836 ?g . '
                'FILTER(REGEX(?g, "^(E0[46789]|E10|E47|E61|W0[46]|S12|N09)[0-9]{6}$")) OPTIONAL { ?i wdt:P300 ?iso } }')
    by_code, by_item, iso = collections.defaultdict(set), collections.defaultdict(set), collections.defaultdict(set)
    for b in bs:
        by_code[b['g']['value']].add(qv(b, 'i'))
        by_item[qv(b, 'i')].add(b['g']['value'])
        if 'iso' in b:
            iso[qv(b, 'i')].add(b['iso']['value'])
    out = {}
    for c, qs in by_code.items():
        if len(qs) == 1:
            q = next(iter(qs))
            if len(by_item[q]) == 1:
                isos = {x for x in iso[q] if x.startswith('GB-')}
                out[c] = (q, next(iter(isos)) if len(isos) == 1 else '')
    return out


def build(reg):
    os.makedirs(OUT, exist_ok=True)
    R = rgc()
    wd26 = arcgis('ons_lu_wd26', ARC, LU_WD26, fields='LAD26CD,LAD26NM,LAD26NMW,CTYUA26CD', page=1000)
    cauth = arcgis('ons_lu_cauth25', ARC, LU_CAUTH, page=1000)
    man = manifest()
    ra_rgc = man['ons_rgc']['retrieved_at']
    ra_lu = max(v['retrieved_at'] for k, v in man.items() if k.startswith('ons_lu_'))
    qids = gss_qids()
    ra_wd = manifest()['wd_gss']['retrieved_at']
    known = existing_foreign()
    for e in COUNTRY.values():
        assert e in known, e
    stats, gaps = collections.Counter(), []
    lad26 = {r['LAD26CD']: r for r in wd26}
    lad_cauth = {r['LAD25CD']: r['CAUTH25CD'] for r in cauth}

    # ---- unit table from the RGC (live rows) + Scottish council areas from the 2026 lookup
    units = {}
    for ent, rs in R.items():
        for r in rs:
            if r['STATUS'] != 'live':
                continue
            si = r['SI_TITLE'] if r['SI_TITLE'] and r['SI_TITLE'] != 'GSS re-coding strategy' else ''
            if r['GEOGCD'] in units:   # the same live code listed twice (one row per statutory instrument)
                prev = units[r['GEOGCD']]
                assert (prev['name'], prev['parent']) == (r['GEOGNM'], r['PARENTCD'] or ''), r['GEOGCD']
                prev['si'] = '; '.join(sorted({x for x in (prev['si'], si) if x}))
                continue
            units[r['GEOGCD']] = dict(si=si, code=r['GEOGCD'], ent=ent, name=r['GEOGNM'], nmw=r['GEOGNMW'] or '', oper=d(r['OPER_DATE']),
                                      term=d(r['TERM_DATE']), parent=r['PARENTCD'] or '', src='ons_rgc', url=RGC_PAGE,
                                      sdate=RGC_DATE, ra=ra_rgc)
    for c, r in lad26.items():
        if c.startswith('S12'):
            units[c] = dict(si='', code=c, ent='S12', name=r['LAD26NM'], nmw='', oper='', term='', parent='', src='ons_lookup',
                            url='{}/{}/FeatureServer'.format(ARC, LU_WD26), sdate='2026-05', ra=ra_lu)
    rgc_lad = {c for c, u in units.items() if u['ent'] in LAD}
    for c in sorted(rgc_lad ^ set(lad26)):
        gaps.append({'code': c, 'issue': 'LAD in {} but not in {}'.format(*(('RGC', LU_WD26) if c in rgc_lad else (LU_WD26, 'RGC')))})

    # county of each two-tier district (RGC parent) and combined authority containing each area (ONS lookup)
    county_cauth = collections.defaultdict(set)
    for c, u in units.items():
        if u['ent'] == 'E07':
            county_cauth[u['parent']].add(lad_cauth.get(c, ''))
    rows = []
    for c, u in sorted(units.items()):
        sub, gs, note = ENTITIES[u['ent']]
        flags, member = [], ''
        if u['ent'] in LAD:
            member = lad_cauth.get(c, '')
            if u['ent'] == 'E07':
                parent = u['parent']
            elif u['ent'] == 'E09':
                parent = 'E61000001'
            elif member:
                parent = member
            else:
                parent = DEVOLVED[c[0]]
        elif u['ent'] == 'E10':
            cs = county_cauth.get(c, {''})
            member = next(iter(cs)) if len(cs) == 1 else ''
            if len(cs) > 1:
                flags.append('districts_in_several_cauth')
            elif member:
                flags.append('cauth_from_district_lookup')
            parent = member or 'nation:gb'
        elif u['ent'] in ('E47', 'E61'):
            parent = 'nation:gb'
        else:   # parish / community -> its local authority
            parent = u['parent']
        if u['ent'] in ('E04', 'W04'):
            flags.append('council_status_unknown')
        if member and member not in units:
            gaps.append({'code': c, 'issue': 'combined authority {} (2025 lookup) not live in RGC June 2026'.format(member)})
            member = ''
        pid = parent if parent.startswith(('nation:', 'subdivision:')) else 'gss:' + parent if parent else ''
        if pid.startswith('gss:') and parent not in units:
            gaps.append({'code': c, 'issue': 'parent {} not a live unit'.format(parent)})
        if c == 'E09000001':
            note = 'City of London Corporation (sui generis)'
        if c == 'E06000053':
            note = 'Council of the Isles of Scilly (sui generis)'
        if u['si']:
            note = '; '.join(x for x in (note, 'code introduced by ' + u['si']) if x)
        q, iso = qids.get(c, ('', ''))
        eid = reg.get(['gss:' + c], 'gss:' + c, u['ra'][:10])
        src = u['src'] + (';ons_lookup' if member and u['src'] == 'ons_rgc' else '') + (';wikidata_foreign' if q else '')
        rows.append(dict(entity_id=eid, name=u['name'], name_local=u['nmw'], name_en='', type='foreign', subtype=sub,
                         gov_status=gs, parent_id=pid, member_of='gss:' + member if member else '', country='GB',
                         code_scheme='gss', code=c, alt_code='', iso_3166_2=iso, wikidata_qid=q,
                         code_valid_from=u['oper'], code_valid_to=u['term'], valid_from='', valid_to='', is_active='Y',
                         note=note, flags=';'.join(flags), source=src, source_url=u['url'], source_date=u['sdate'],
                         retrieved_at=max(u['ra'], ra_lu if member or u['src'] == 'ons_lookup' else '', ra_wd if q else ''), license=OGL))
        stats[sub] += 1
        if q:
            stats['with_qid'] += 1
        if iso:
            stats['with_iso_3166_2'] += 1
    # ---- history: terminated RGC codes (is_active=N, code_valid_to = RGC TERM_DATE) and CHD predecessor links
    term = {}
    for ent, rs in R.items():
        for r in rs:
            c = r['GEOGCD']
            if r['STATUS'] != 'terminated' or c in units:
                continue
            if c not in term or d(r['TERM_DATE']) > term[c]['term']:
                term[c] = dict(code=c, ent=ent, name=r['GEOGNM'], nmw=r['GEOGNMW'] or '', oper=d(r['OPER_DATE']),
                               term=d(r['TERM_DATE']), parent=r['PARENTCD'] or '',
                               si=r['SI_TITLE'] if r['SI_TITLE'] and r['SI_TITLE'] != 'GSS re-coding strategy' else '')
    scope = set(units) | set(term)
    pred, succ = collections.defaultdict(set), collections.defaultdict(set)
    for c, cp, si, od in chd_changes():
        if c in scope and cp in scope and c != cp:
            pred[c].add(cp)
            succ[cp].add(c)
    ra_chd = manifest()['ons_chd']['retrieved_at']
    ids = lambda cs: ';'.join('gss:' + x for x in sorted(cs))
    for r in rows:
        c = r['code']
        if pred[c] or succ[c]:
            r['predecessor_id'], r['successor_id'] = ids(pred[c]), ids(succ[c])
            r['source'] = r['source'].replace('ons_rgc', 'ons_rgc;ons_chd', 1) if 'ons_rgc' in r['source'] else r['source'] + ';ons_chd'
            r['retrieved_at'] = max(r['retrieved_at'], ra_chd)
            stats['with_chd_link'] += 1
    for c, u in sorted(term.items()):
        sub, gs, note = ENTITIES[u['ent']]
        pid = 'gss:' + u['parent'] if u['parent'] in scope else ''
        if u['parent'] and not pid:
            note = '; '.join(x for x in (note, 'RGC parent {} (outside this table)'.format(u['parent'])) if x)
        if u['si']:
            note = '; '.join(x for x in (note, 'code introduced by ' + u['si']) if x)
        q, iso = qids.get(c, ('', ''))
        eid = reg.get(['gss:' + c], 'gss:' + c, ra_rgc[:10])
        link = bool(pred[c] or succ[c])
        rows.append(dict(entity_id=eid, name=u['name'], name_local=u['nmw'], name_en='', type='foreign', subtype=sub,
                         gov_status=gs, parent_id=pid, member_of='', country='GB', code_scheme='gss', code=c, alt_code='',
                         iso_3166_2=iso, wikidata_qid=q, code_valid_from=u['oper'], code_valid_to=u['term'], valid_from='',
                         valid_to='', is_active='N', predecessor_id=ids(pred[c]), successor_id=ids(succ[c]), note=note,
                         flags=';'.join(['code_terminated'] + (['council_status_unknown'] if u['ent'] in ('E04', 'W04') else [])),
                         source='ons_rgc' + (';ons_chd' if link else '') + (';wikidata_foreign' if q else ''),
                         source_url=RGC_PAGE, source_date=RGC_DATE,
                         retrieved_at=max(ra_rgc, ra_chd if link else '', ra_wd if q else ''), license=OGL))
        stats['terminated|' + sub] += 1
        stats['terminated_with_successor'] += bool(succ[c])
    check(rows, known)

    # ---- code crosswalk: GSS country codes and ISO 3166-2 to existing rows; every new row's GSS and ISO code
    xw = []
    for c, e in sorted(COUNTRY.items()):
        rel = 'same_government' if e != 'subdivision:gb-eng' else 'area_only'
        nt = {'subdivision:gb-eng': 'England has no devolved government; English councils sit under nation:gb',
              'subdivision:gb-sct': 'Scottish Government', 'subdivision:gb-wls': 'Welsh Government',
              'subdivision:gb-nir': 'Northern Ireland Executive', 'nation:gb': 'UK Government'}[e]
        xw.append(dict(entity_id=e, code_scheme='gss', code=c, relation=rel, note=nt, source='ons_rgc', source_url=RGC_PAGE))
        if known[e]['iso_3166_2']:
            xw.append(dict(entity_id=e, code_scheme='iso_3166_2', code=known[e]['iso_3166_2'], relation=rel,
                           note=nt, source='iso_codes', source_url=''))
    for r in rows:
        if r['iso_3166_2'] and r['is_active'] == 'Y':      # terminated codes keep their ISO code on the row only
            xw.append(dict(entity_id=r['entity_id'], code_scheme='iso_3166_2', code=r['iso_3166_2'], relation='same_area',
                           note='via Wikidata item with this GSS code (P836) and ISO 3166-2 code (P300)',
                           source='wikidata_foreign', source_url='https://www.wikidata.org/wiki/' + r['wikidata_qid']))

    # ---- boundary crosswalk: only codes actually present in the boundary attribute table
    bx = []
    by_code = {r['code']: r for r in rows}
    for ds, svc, lid, fld, vint, ents in BOUNDARIES:
        have = {a[fld] for a in arcgis('ons_bfc_' + svc.lower(), ARC, svc, fields=fld, layer=lid)}
        url = '{}/{}/FeatureServer/{}'.format(ARC, svc, lid)
        for r in rows:
            e, c = r['entity_id'], r['code']
            if c[:3] not in ents or r['is_active'] != 'Y':   # terminated codes are not in the current boundaries
                continue
            if c in have:
                bx.append(dict(entity_id=e, boundary_dataset=ds, boundary_code=c, vintage=vint, relation='same_code', source_url=url))
                stats['boundary|' + ds] += 1
            else:
                gaps.append({'code': c, 'issue': 'not in boundary dataset {}'.format(ds)})
                stats['boundary_missing|' + ds] += 1
    files = write_split(os.path.join(OUT, 'units'), rows, LOCAL_COLUMNS, lambda r: r['code'][0].lower())
    write_csv(os.path.join(OUT, 'code_xwalk.csv'), xw, CODE_XW_COLUMNS)
    write_csv(os.path.join(OUT, 'boundary_xwalk.csv'), bx, BOUNDARY_COLUMNS)
    write_csv(os.path.join(OUT, 'gaps.csv'), sorted(gaps, key=lambda g: (g['issue'], g['code'])), ['code', 'issue'])
    stats['units'] = len(rows)
    stats['gaps'] = len(gaps)
    return rows, dict(sorted(stats.items())), [os.path.relpath(f, ROOT) for f in files]


if __name__ == '__main__':
    reg = Registry()
    rows, stats, files = build(reg)
    reg.save()
    import json
    print(json.dumps(stats, indent=1), files)
