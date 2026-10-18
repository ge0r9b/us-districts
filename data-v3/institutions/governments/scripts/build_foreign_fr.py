"""French government units at every level (foreign/fr/), keyed by INSEE COG codes and SIREN.

Sources (Licence Ouverte / Open Licence 2.0):
  * INSEE Code officiel geographique au 1er janvier 2026 (CSV): regions, departements, collectivites territoriales ayant
    les competences departementales (CTCD), collectivites d'outre-mer (COM), communes, communes deleguees / associees,
    arrondissements municipaux, communes of the COM, and the 2026 movement file (dated creations).
  * INSEE Base des EPCI a fiscalite propre et des EPT au 1er janvier 2026 (SIREN, nature, commune composition).
  * IGN ADMIN EXPRESS COG CARTO (latest edition = COG 2026, checked on names), WFS attribute tables only: SIREN of
    communes, regions and CTCD.
  * IGN ADMIN EXPRESS COG 2026 (full precision, the edition Geo uses per FOREIGN_VINTAGES.md), WFS attribute tables:
    codes present in the region, departement, epci and commune layers (boundary_xwalk.csv).
The State = nation:fr. Existing rows reused, never re-minted: metropolitan regions subdivision:fr-xxx (through the Wikidata
item that carries both the INSEE region code P2585 and the ISO code P300), Corse subdivision:fr-20r, the overseas
territory: rows (single collectivities of Martinique, Guyane, Mayotte; the departements of Guadeloupe and La Reunion;
the COM). New IDs: fr-cog:<level>:<code> (reg, dep, ctcd, com, comd, coma, arm) and fr-siren:<SIREN> (EPCI, EPT).
"""
import collections, csv, os, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CACHE, ROOT, Registry, fetch, manifest, norm, write_csv
from wikidata import sparql, qv
from foreign_local import (FOREIGN, LOCAL_COLUMNS, CODE_XW_COLUMNS, BOUNDARY_COLUMNS, check, existing_foreign, read_xlsx,
                           wfs, write_split)

OUT = os.path.join(FOREIGN, 'fr')
COG_URL = 'https://www.insee.fr/fr/statistiques/fichier/8740222/cog_ensemble_2026_csv.zip'
COG_PAGE = 'https://www.insee.fr/fr/information/8740222'
EPCI_URL = 'https://www.insee.fr/fr/statistiques/fichier/2510634/epci_au_01-01-2026.zip'
EPT_URL = 'https://www.insee.fr/fr/statistiques/fichier/2510634/ept_au_01-01-2026.zip'
EPCI_PAGE = 'https://www.insee.fr/fr/information/2510634'
# DGCL (BANATIC) table de passage code INSEE des communes / SIREN (data.gouv.fr, 2025-03-12): primary source of commune SIREN.
# IGN ADMIN EXPRESS code_siren is only a fallback: it repeats a SIREN on two communes in 3 cases (46002/55102/97502 carry
# the SIREN of 31006/55039/97416), so it is used only where DGCL has no row and the SIREN is unique.
DGCL_SIREN_URL = ('https://static.data.gouv.fr/resources/base-nationale-sur-les-intercommunalites/20250312-083024/'
                  'correspondance-code-commune-siren.csv')
DGCL_PAGE = 'https://www.data.gouv.fr/datasets/base-nationale-sur-les-intercommunalites'
IGN = 'https://data.geopf.fr/wfs/ows'
IGN_LAYER = 'ADMINEXPRESS-COG-CARTO.LATEST:{}'
# Geo's exact boundary edition (data/geo data-v3/geo/FOREIGN_VINTAGES.md): ADMIN EXPRESS COG 4.0 full precision,
# edition 2026-01-01; codes are checked against the same product's WFS layers. layer -> key property
GEO_IGN_LAYER = 'ADMINEXPRESS-COG.2026:{}'
GEO_LAYERS = {'region': 'code_insee', 'departement': 'code_insee', 'epci': 'code_siren', 'commune': 'code_insee'}
GEO_VINTAGE = 'COG 2026'
LO = 'Licence Ouverte / Open Licence 2.0 (Etalab)'
VINTAGE = '2026-01-01'
HISTORY_FROM = '2015-01-01'   # terminated commune codes whose COG DATE_FIN is on or after this date
# reviewed: COG overseas collectivity code -> existing territory row (names checked in build except the two noted)
COMER = {'975': 'territory:pm', '977': 'territory:bl', '978': 'territory:mf', '984': 'territory:tf', '986': 'territory:wf',
         '987': 'territory:pf', '988': 'territory:nc', '989': 'subdivision:fr-cp'}
COMER_NAME_REVIEWED = {'984', '989'}   # ISO 'Terres australes françaises' / 'Clipperton' vs COG long forms
# CTCD whose government is an existing row (single collectivities; ISO FR-971/974 departemental collectivities)
CTCD_EXISTING = {'20R': 'subdivision:fr-20r', '972R': 'territory:mq', '973R': 'territory:gf', '976R': 'territory:yt',
                 '971D': 'territory:gp', '974D': 'territory:re'}
PARIS = '75056'
LYON_SIREN = '200046977'
MGP_SIREN = '200054781'
NATURE = {'METRO': 'metropole', 'ME': 'metropole', 'CU': 'communaute_urbaine', 'CA': 'communaute_d_agglomeration', 'CC': 'communaute_de_communes',
          'METLYON': 'metropole_de_lyon'}
CTCD_SPECIAL = {'69M': 'metropole_de_lyon', '6AE': 'collectivite_europeenne_d_alsace', '75C': 'ville_de_paris'}


def cog():
    p = fetch('insee_cog2026', url=COG_URL, fname='insee_cog_ensemble_2026_csv.zip')
    out = {}
    with zipfile.ZipFile(p) as z:
        for n in z.namelist():
            if n.endswith('_2026.csv') or n == 'v_commune_depuis_1943.csv':
                out[n[2:-9] if n.endswith('_2026.csv') else n[2:-4]] = list(csv.DictReader(z.read(n).decode('utf-8-sig').splitlines()))
    return out


def dgcl_siren():
    p = fetch('dgcl_siren', url=DGCL_SIREN_URL, fname='dgcl_correspondance-code-commune-siren.csv')
    raw = open(p, 'rb').read()
    try:
        txt = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        txt = raw.decode('cp1252')
    rows = list(csv.DictReader(txt.splitlines(), delimiter=';'))
    out = {r['Code INSEE de la commune'].strip(): r['Siren'].strip() for r in rows}
    assert len(out) == len(rows) > 30000, len(rows)
    return out


def insee_xlsx(key, url, fname):
    p = fetch(key, url=url, fname=fname)
    with zipfile.ZipFile(p) as z:
        x = [n for n in z.namelist() if n.lower().endswith('.xlsx')][0]
        z.extract(x, CACHE)
    sheets = read_xlsx(os.path.join(CACHE, x))
    out = {}
    for name, rows in sheets.items():
        hi = next((i for i, r in enumerate(rows) if len(r) > 1 and r[1] in ('LIBEPCI', 'LIBEPT', 'LIBGEO')), None)
        if hi is not None:
            out[name] = [dict(zip(rows[hi], r)) for r in rows[hi + 1:] if r and r[0]]
    return out


def wd_maps():
    out = {}
    for prop, key in (('P374', 'wd_fr_p374'), ('P1616', 'wd_fr_p1616'), ('P2585', 'wd_fr_p2585')):
        q = 'SELECT ?i ?v ?iso WHERE { ?i wdt:%s ?v . OPTIONAL { ?i wdt:P300 ?iso } }' % prop
        by_code, by_item, iso = collections.defaultdict(set), collections.defaultdict(set), collections.defaultdict(set)
        for b in sparql(key, q):
            by_code[b['v']['value']].add(qv(b, 'i'))
            by_item[qv(b, 'i')].add(b['v']['value'])
            if 'iso' in b:
                iso[qv(b, 'i')].add(b['iso']['value'])
        for c, qs in by_code.items():
            if len(qs) == 1 and len(by_item[next(iter(qs))]) == 1:
                i = next(iter(qs))
                out[(prop, c)] = (i, next(iter(iso[i])) if len(iso[i]) == 1 else '')
    return out


def build(reg):
    os.makedirs(OUT, exist_ok=True)
    C = cog()
    E = insee_xlsx('insee_epci2026', EPCI_URL, 'insee_epci_au_01-01-2026.zip')
    T = insee_xlsx('insee_ept2026', EPT_URL, 'insee_ept_au_01-01-2026.zip')
    ign = {}
    for lay, props in (('region', ['code_insee', 'nom_officiel', 'code_siren']), ('departement', ['code_insee', 'nom_officiel']),
                       ('collectivite_territoriale', ['code_insee', 'nom_officiel', 'code_siren']),
                       ('epci', ['code_siren', 'nom_officiel']), ('commune', ['code_insee', 'nom_officiel', 'code_siren']),
                       ('commune_associee_ou_deleguee', ['code_insee', 'nom_officiel', 'nature']),
                       ('arrondissement_municipal', ['code_insee', 'nom_officiel'])):
        ign[lay] = wfs('ign_adminexpress_' + lay, IGN, IGN_LAYER.format(lay), props)
    geo = {lay: {r[k] for r in wfs('ign_aecog2026_' + lay, IGN, GEO_IGN_LAYER.format(lay), [k])} for lay, k in GEO_LAYERS.items()}
    dg = dgcl_siren()
    wd = wd_maps()
    man = manifest()
    ra_c, ra_e = man['insee_cog2026']['retrieved_at'], max(man['insee_epci2026']['retrieved_at'], man['insee_ept2026']['retrieved_at'])
    ra_i = max(v['retrieved_at'] for k, v in man.items() if k.startswith('ign_adminexpress_'))
    ra_dg = man['dgcl_siren']['retrieved_at']
    ra_w = max(v['retrieved_at'] for k, v in man.items() if k.startswith('wd_fr_'))
    known = existing_foreign()
    iso2 = {x['code']: x for x in __import__('json').load(open(os.path.join(CACHE, 'iso_3166-2.json'), encoding='utf-8'))['3166-2']}
    stats, gaps, xw = collections.Counter(), [], []
    siren_ign = {lay: {r['code_insee']: r.get('code_siren') or '' for r in ign[lay]} for lay in ('region', 'collectivite_territoriale', 'commune')}
    # commune SIREN: DGCL table by INSEE code; IGN only where DGCL has none and the IGN SIREN is on exactly one commune
    ign_n = collections.Counter(v for v in siren_ign['commune'].values() if v)
    com_siren, com_siren_src = {}, {}
    for c in sorted(r['COM'] for r in C['commune'] if r['TYPECOM'] == 'COM'):
        i, d = siren_ign['commune'].get(c, ''), dg.get(c, '')
        if d:
            com_siren[c], com_siren_src[c] = d, 'dgcl_siren'
            if i and i != d:
                gaps.append({'code': c, 'issue': 'IGN ADMIN EXPRESS code_siren {} differs from DGCL {}; DGCL used'.format(i, d)})
                stats['commune_siren_ign_differs_dgcl'] += 1
        elif i and ign_n[i] == 1 and i not in set(dg.values()):
            com_siren[c], com_siren_src[c] = i, 'ign_adminexpress'
        elif i:
            gaps.append({'code': c, 'issue': 'IGN ADMIN EXPRESS code_siren {} is not unique and DGCL has no row; left empty'.format(i)})
            stats['commune_siren_dropped_not_unique'] += 1
    assert not [v for v, n in collections.Counter(com_siren.values()).items() if n > 1], 'commune SIREN not unique'
    # edition check: IGN 'latest' names equal COG 2026 names
    com_cog = {r['COM']: r for r in C['commune'] if r['TYPECOM'] == 'COM'}
    same = sum(1 for r in ign['commune'] if r['code_insee'] in com_cog and r['nom_officiel'] == com_cog[r['code_insee']]['LIBELLE'])
    stats['ign_commune_names_equal_cog2026'] = same
    assert same > 0.99 * len(com_cog), same
    # dated creations from the 2026 movement file: creation (20), re-establishment (21), commune nouvelle (32)
    created = {}
    for m in C['mvt_commune']:
        if m['MOD'] in ('20', '21', '32') and m['TYPECOM_AP'] == 'COM':
            created[m['COM_AP']] = max(created.get(m['COM_AP'], ''), m['DATE_EFF'])

    def row(eid, name, sub, gs, parent, scheme, code, alt='', alt_name='', member='', iso='', q='', src='insee_cog2026',
            vf='', note='', flags=(), url=COG_PAGE):
        srcs = src + (';wikidata_foreign' if q else '')
        ra = max(ra_c if 'cog' in src else '', ra_e if 'epci' in src or 'ept' in src else '', ra_i if 'ign' in src else '',
                 ra_w if q else '', ra_dg if 'dgcl' in src else '')
        return dict(entity_id=eid, name=name, name_local='', name_en='', alt_name=alt_name if alt_name != name else '',
                    type='foreign', subtype=sub, gov_status=gs, parent_id=parent, member_of=member, country='FR',
                    code_scheme=scheme, code=code, alt_code=alt, iso_3166_2=iso, wikidata_qid=q, code_valid_from='',
                    code_valid_to='', valid_from=vf, valid_to='', is_active='Y', note=note, flags=';'.join(flags),
                    source=srcs, source_url=url, source_date=VINTAGE, retrieved_at=ra,
                    license=LO + (' ; IGN ADMIN EXPRESS: ' + LO if 'ign' in src else ''))
    rows = []
    # ---- regions
    reg_ent = {}
    ctcd = {r['CTCD']: r for r in C['ctcd']}
    single = {r['REG']: c for c, r in ctcd.items() if c.endswith('R')}     # region-level single collectivities
    for r in C['region']:
        code = r['REG']
        q, iso = wd.get(('P2585', code), ('', ''))
        q_shared = q and q in {k['wikidata_qid'] for k in known.values()}
        if code in single:
            reg_ent[code] = CTCD_EXISTING[single[code]]
            xw.append(dict(entity_id=reg_ent[code], code_scheme='insee_reg', code=code, relation='same_government',
                           note='region and departement are one collectivity ({})'.format(ctcd[single[code]]['LIBELLE']),
                           source='insee_cog2026', source_url=COG_PAGE))
            continue
        e = 'subdivision:' + iso.lower() if iso and 'subdivision:' + iso.lower() in known else ''
        if e:
            reg_ent[code] = e
            xw.append(dict(entity_id=e, code_scheme='insee_reg', code=code, relation='same_government',
                           note='Wikidata {} has P2585 {} and P300 {}'.format(q, code, iso), source='insee_cog2026;wikidata_foreign',
                           source_url='https://www.wikidata.org/wiki/' + q))
            continue
        eid = reg.get(['fr-cog:reg:' + code], 'fr-cog:reg:' + code, ra_c[:10])
        reg_ent[code] = eid
        rows.append(row(eid, r['LIBELLE'], 'region', 'self_governing', 'nation:fr', 'insee_reg', code,
                        alt=siren_ign['region'].get(code, ''), q='' if q_shared else q, src='insee_cog2026;ign_adminexpress',
                        flags=('qid_is_shared_area_item:' + q,) if q_shared else (),
                        note='région (conseil régional); the département of the same name is {}'.format(
                            CTCD_EXISTING.get(next((c for c, x in ctcd.items() if x['REG'] == code), ''), ''))))
    for r in C['region']:
        xw.append(dict(entity_id=reg_ent[r['REG']], code_scheme='siren', code=siren_ign['region'].get(r['REG'], ''),
                       relation='same_government', note='region SIREN (IGN ADMIN EXPRESS)', source='ign_adminexpress',
                       source_url=IGN)) if reg_ent[r['REG']] in known and siren_ign['region'].get(r['REG']) else None
    # ---- departement-level collectivities (CTCD)
    ct_ent = {}
    for c, r in sorted(ctcd.items()):
        siren = siren_ign['collectivite_territoriale'].get(c, '')
        if c in CTCD_EXISTING:
            ct_ent[c] = CTCD_EXISTING[c]
            xw.append(dict(entity_id=ct_ent[c], code_scheme='insee_ctcd', code=c, relation='same_government', note=r['LIBELLE'],
                           source='insee_cog2026', source_url=COG_PAGE))
            if siren:
                xw.append(dict(entity_id=ct_ent[c], code_scheme='siren', code=siren, relation='same_government', note=r['LIBELLE'],
                               source='ign_adminexpress', source_url=IGN))
            continue
        if c == '75C':
            continue                               # Ville de Paris = commune 75056 (row below)
        dep = c[:-1] if c.endswith('D') else ''
        iso = 'FR-' + (dep or c) if 'FR-' + (dep or c) in iso2 else ''
        if dep:
            eid = reg.get(['fr-cog:dep:' + dep], 'fr-cog:dep:' + dep, ra_c[:10])
            depname = next(d['LIBELLE'] for d in C['departement'] if d['DEP'] == dep)
            rows.append(row(eid, r['LIBELLE'], 'conseil_departemental', 'self_governing', reg_ent[r['REG']], 'insee_ctcd', c,
                            alt=siren, alt_name=depname, iso=iso, src='insee_cog2026;ign_adminexpress',
                            note='departement {} ({})'.format(dep, depname)))
        else:
            eid = reg.get(['fr-cog:ctcd:' + c], 'fr-cog:ctcd:' + c, ra_c[:10])
            rows.append(row(eid, r['LIBELLE'], CTCD_SPECIAL[c], 'self_governing', reg_ent[r['REG']], 'insee_ctcd', c,
                            alt=siren or (LYON_SIREN if c == '69M' else ''), iso=iso, src='insee_cog2026;ign_adminexpress',
                            note='collectivité à statut particulier'))
        ct_ent[c] = eid
    # departements -> the collectivity that governs them (from the communes' CTCD)
    dep_ct = collections.defaultdict(set)
    for r in C['commune']:
        if r['TYPECOM'] == 'COM':
            dep_ct[r['DEP']].add(r['CTCD'])
    paris_eid = reg.get(['fr-cog:com:' + PARIS], 'fr-cog:com:' + PARIS, ra_c[:10])
    ct_ent['75C'] = paris_eid
    for d in C['departement']:
        cs = sorted(dep_ct[d['DEP']])
        for c in cs:
            own = c == d['DEP'] + 'D' or (c in CTCD_EXISTING and c.startswith(d['DEP'])) and len(cs) == 1
            rel = 'same_government' if own else 'governs_part' if len(cs) > 1 else 'governs_departement'
            xw.append(dict(entity_id=ct_ent[c], code_scheme='insee_dep', code=d['DEP'], relation=rel,
                           note='département {}: {}'.format(d['LIBELLE'], ctcd[c]['LIBELLE']), source='insee_cog2026', source_url=COG_PAGE))
            if 'FR-' + d['DEP'] in iso2 and rel == 'governs_departement':   # e.g. FR-2A/2B (Corse), FR-67/68 (Alsace)
                xw.append(dict(entity_id=ct_ent[c], code_scheme='iso_3166_2', code='FR-' + d['DEP'], relation=rel,
                               note='ISO 3166-2 code of département {}, governed by {}'.format(d['LIBELLE'], ctcd[c]['LIBELLE']),
                               source='iso_codes;insee_cog2026', source_url=''))
    for c in ('69M', '6AE', '75C'):
        if 'FR-' + c in iso2:
            xw.append(dict(entity_id=ct_ent[c], code_scheme='iso_3166_2', code='FR-' + c, relation='same_government',
                           note=ctcd[c]['LIBELLE'], source='iso_codes', source_url=''))
    # ---- overseas collectivities (COM): existing territory rows
    for r in C['comer']:
        e = COMER.get(r['COMER'])
        if not e:
            gaps.append({'code': r['COMER'], 'issue': 'COG collectivity {} has no own government row (not built)'.format(r['LIBELLE'])})
            continue
        if r['COMER'] not in COMER_NAME_REVIEWED:
            isoc = known[e]['iso_alpha2'] or known[e]['iso_3166_2'][-2:]
            assert norm(iso2['FR-' + isoc]['name']) == norm(r['LIBELLE']), (e, r['LIBELLE'])
        xw.append(dict(entity_id=e, code_scheme='insee_comer', code=r['COMER'], relation='same_government', note=r['LIBELLE'],
                       source='insee_cog2026', source_url=COG_PAGE))
    # ---- EPCI a fiscalite propre and EPT
    epci = {r['EPCI']: r for r in E['EPCI']}
    comp = {r['CODGEO']: r['EPCI'] for r in E['Composition_communale']}
    ept = {r['EPT']: r for r in T['EPT'] if r['EPT'] != 'ZZZZZZZZZ'}
    comp_t = {r['CODGEO']: r['EPT'] for r in T['Composition_communale'] if r['EPT'] != 'ZZZZZZZZZ'}
    com_reg = {r['COM']: r['REG'] for r in C['commune'] if r['TYPECOM'] == 'COM'}
    ep_ent = {LYON_SIREN: ct_ent['69M']}
    ep_regs = collections.defaultdict(set)
    for c, s in comp.items():
        ep_regs[s].add(com_reg.get(c))
    for s, r in sorted(epci.items()):
        if s == LYON_SIREN or s == 'ZZZZZZZZZ':
            continue
        regs = ep_regs[s]
        parent = reg_ent[next(iter(regs))] if len(regs) == 1 and None not in regs else 'nation:fr'
        q = wd.get(('P1616', s), ('', ''))[0]
        eid = reg.get(['fr-siren:' + s], 'fr-siren:' + s, ra_e[:10])
        ep_ent[s] = eid
        rows.append(row(eid, r['LIBEPCI'], NATURE[r['NATURE_EPCI']], 'intercommunal', parent, 'siren', s, q=q,
                        src='insee_epci2026', url=EPCI_PAGE, note='EPCI à fiscalité propre ({} communes)'.format(r['NB_COM']),
                        flags=() if len(regs) == 1 else ('epci_spans_regions',)))
    for s, r in sorted(ept.items()):
        q = wd.get(('P1616', s), ('', ''))[0]
        eid = reg.get(['fr-siren:' + s], 'fr-siren:' + s, ra_e[:10])
        ep_ent[s] = eid
        rows.append(row(eid, r['LIBEPT'], 'etablissement_public_territorial', 'intercommunal', 'fr-siren:' + MGP_SIREN, 'siren', s,
                        q=q, src='insee_ept2026', url=EPCI_PAGE, note='EPT of the Métropole du Grand Paris (no own tax base)'))
    xw.append(dict(entity_id=ct_ent['69M'], code_scheme='siren', code=LYON_SIREN, relation='same_government',
                   note='Métropole de Lyon in the INSEE EPCI file', source='insee_epci2026', source_url=EPCI_PAGE))
    # ---- communes, Ville de Paris, children (deleguees, associees, arrondissements municipaux)
    for c, r in sorted(com_cog.items()):
        q = wd.get(('P374', c), ('', ''))[0]
        s = comp.get(c, '')
        member = ';'.join(x for x in (ep_ent.get(s, ''), ep_ent.get(comp_t.get(c, ''), '')) if x)
        if s and s != 'ZZZZZZZZZ' and s not in ep_ent:
            gaps.append({'code': c, 'issue': 'EPCI {} not in EPCI list'.format(s)})
        if not s:
            gaps.append({'code': c, 'issue': 'commune not in the INSEE EPCI composition'})
        flags = ['no_epci'] if s == 'ZZZZZZZZZ' else []
        if c == PARIS:
            rows.append(row(paris_eid, r['LIBELLE'], 'ville_de_paris', 'self_governing', reg_ent[r['REG']], 'insee_com', c,
                            alt=com_siren.get(c, ''), member=member, iso='FR-75C', q=q,
                            src='insee_cog2026;insee_epci2026;' + com_siren_src.get(c, 'ign_adminexpress'),
                            note='Ville de Paris: commune with departemental powers (CTCD 75C)'))
            continue
        eid = reg.get(['fr-cog:com:' + c], 'fr-cog:com:' + c, ra_c[:10])
        if c not in siren_ign['commune']:
            flags.append('not_in_ign_adminexpress')
        rows.append(row(eid, r['LIBELLE'], 'commune', 'self_governing', ct_ent[r['CTCD']], 'insee_com', c,
                        alt=com_siren.get(c, ''), member=member, q=q, vf=created.get(c, ''),
                        src='insee_cog2026;insee_epci2026;' + com_siren_src.get(c, 'ign_adminexpress'), flags=flags))
    kids = {'COMD': ('comd', 'commune_deleguee', 'delegated'), 'COMA': ('coma', 'commune_associee', 'delegated'),
            'ARM': ('arm', 'arrondissement_municipal', 'sub_municipal')}
    for r in C['commune']:
        if r['TYPECOM'] in kids:
            lv, sub, gs = kids[r['TYPECOM']]
            eid = reg.get(['fr-cog:{}:{}'.format(lv, r['COM'])], 'fr-cog:{}:{}'.format(lv, r['COM']), ra_c[:10])
            rows.append(row(eid, r['LIBELLE'], sub, gs, 'fr-cog:com:' + r['COMPARENT'], 'insee_' + lv, r['COM'],
                            note='child of commune {}'.format(r['COMPARENT'])))
    for r in C['commune_comer']:
        if r['NATURE_ZONAGE'] != 'COM':
            continue
        q = wd.get(('P374', r['COM_COMER']), ('', ''))[0]
        eid = reg.get(['fr-cog:com:' + r['COM_COMER']], 'fr-cog:com:' + r['COM_COMER'], ra_c[:10])
        terr = COMER[r['COMER']]
        note = 'commune of {}'.format(r['LIBELLE_COMER'])
        if q and q == known[terr]['wikidata_qid']:
            # single-commune collectivity (Saint-Barthelemy, Saint-Martin): the Wikidata item is the collectivity's own,
            # already on the territory row; the commune row keeps no QID and is crosswalked as the same government
            q, note = '', 'commune of {}; same government as {} (single-commune collectivity)'.format(r['LIBELLE_COMER'], terr)
            xw.append(dict(entity_id=terr, code_scheme='insee_com', code=r['COM_COMER'], relation='same_government',
                           note='{} = {} (single-commune collectivity; commune row {})'.format(r['LIBELLE_COMER'], r['LIBELLE'], eid),
                           source='insee_cog2026', source_url=COG_PAGE))
            stats['comer_commune_same_government'] += 1
        rows.append(row(eid, r['LIBELLE'], 'commune', 'self_governing', terr, 'insee_com', r['COM_COMER'], q=q, note=note))
    stats['comer_zones_not_communes'] = sum(1 for r in C['commune_comer'] if r['NATURE_ZONAGE'] != 'COM')
    for r in rows:
        stats[r['subtype']] += 1
        stats['with_qid'] += bool(r['wikidata_qid'])
        stats['with_valid_from'] += bool(r['valid_from'])
    # ---- history: commune codes terminated since HISTORY_FROM (COG 'communes depuis 1943' DATE_FIN), linked through the
    # COG 2026 movement file (the commune(s) a code became on that date); code_valid_to = day before DATE_FIN
    import datetime
    by_code = {r['code']: r for r in rows if r['code_scheme'] == 'insee_com'}
    last = {}
    for h in C['commune_depuis_1943']:
        if h['TYPECOM'] == 'COM' and (h['COM'] not in last or h['DATE_DEBUT'] > last[h['COM']]['DATE_DEBUT']):
            last[h['COM']] = h
    term = {c: h for c, h in last.items() if c not in by_code and h['DATE_FIN'] and h['DATE_FIN'] >= HISTORY_FROM}
    succ, pred = collections.defaultdict(set), collections.defaultdict(set)
    mods = collections.defaultdict(set)
    for m in C['mvt_commune']:
        c = m['COM_AV']
        if m['TYPECOM_AV'] == 'COM' and c in term and m['DATE_EFF'] == term[c]['DATE_FIN']:
            mods[c].add(m['MOD'])
            if m['TYPECOM_AP'] == 'COM' and m['COM_AP'] != c:
                succ[c].add(m['COM_AP'])
    known_codes = set(by_code) | set(term)
    for c in list(succ):
        bad = succ[c] - known_codes
        for x in sorted(bad):
            gaps.append({'code': c, 'issue': 'successor {} of terminated commune is neither current nor terminated since {}'.format(x, HISTORY_FROM)})
        succ[c] -= bad
        for x in succ[c]:
            pred[x].add(c)
    cid = lambda cs: ';'.join('fr-cog:com:' + x for x in sorted(cs))
    for c, r in by_code.items():
        if pred[c]:
            r['predecessor_id'] = cid(pred[c])
            stats['commune_with_predecessor'] += 1
    comd_codes = {r['code'] for r in rows if r['code_scheme'] in ('insee_comd', 'insee_coma')}
    for c, h in sorted(term.items()):
        end = (datetime.date.fromisoformat(h['DATE_FIN']) - datetime.timedelta(days=1)).isoformat()
        ss = sorted(succ[c])
        parents = {by_code[x]['parent_id'] for x in ss if x in by_code}
        dep = c[:3] if c.startswith('97') else c[:2]
        cts = dep_ct.get(dep, set())
        parent = next(iter(parents)) if len(parents) == 1 else (ct_ent[next(iter(cts))] if len(cts) == 1 else '')
        note = 'commune code ended {} (COG mouvement {})'.format(h['DATE_FIN'], ','.join(sorted(mods[c])) or 'none listed')
        if c in comd_codes:
            note += '; the code continues as a commune déléguée/associée (fr-cog:{}:{})'.format(
                next(r['code_scheme'][6:] for r in rows if r['code'] == c and r['code_scheme'] in ('insee_comd', 'insee_coma')), c)
        eid = reg.get(['fr-cog:com:' + c], 'fr-cog:com:' + c, ra_c[:10])
        r = row(eid, h['LIBELLE'], 'commune', 'self_governing', parent, 'insee_com', c, note=note,
                flags=['code_terminated'] + ([] if ss else ['no_successor_in_cog']))
        r.update(is_active='N', code_valid_from=h['DATE_DEBUT'] if h['DATE_DEBUT'] > '1943-01-01' else '', code_valid_to=end,
                 successor_id=cid(ss), predecessor_id=cid(pred[c]))
        rows.append(r)
        stats['terminated_commune'] += 1
        stats['terminated_commune_with_successor'] += bool(ss)
    check(rows, known)
    # ---- boundary crosswalk: Geo's layers (IGN ADMIN EXPRESS COG 2026), codes present in each layer
    pairs = collections.defaultdict(list)
    for code, e in reg_ent.items():
        pairs['region'].append((e, code, 'same_code'))
    for d in C['departement']:
        cs = dep_ct[d['DEP']]
        c = next(iter(cs))
        if len(cs) == 1 and sum(1 for x in dep_ct.values() if c in x) == 1:
            pairs['departement'].append((ct_ent[c], d['DEP'], 'same_area'))
    for r in rows:
        if r['code_scheme'] == 'siren':
            pairs['epci'].append((r['entity_id'], r['code'], 'same_code'))
        elif r['code_scheme'] == 'insee_com' and (r['parent_id'] in COMER.values() or r['is_active'] != 'Y'):
            continue
        elif r['code_scheme'] == 'insee_com':
            pairs['commune'].append((r['entity_id'], r['code'], 'same_code'))
    pairs['epci'].append((ct_ent['69M'], LYON_SIREN, 'same_code'))
    bx = []
    for lay, ps in sorted(pairs.items()):
        for e, c, rel in ps:
            if c in geo[lay]:
                bx.append(dict(entity_id=e, boundary_dataset='IGN ADMIN-EXPRESS-COG ' + lay, boundary_code=c, vintage=GEO_VINTAGE,
                               relation=rel, source_url=IGN + '?SERVICE=WFS&REQUEST=GetCapabilities'))
                stats['boundary|' + lay] += 1
            else:
                stats['boundary_missing|' + lay] += 1
                gaps.append({'code': c, 'issue': 'not in IGN ADMIN-EXPRESS-COG {} ({})'.format(lay, e)})
    xw = [x for x in xw if x]
    xw.sort(key=lambda x: (x['entity_id'], x['code_scheme'], x['code']))
    # split for the 10 MB limit: upper levels in one file, communes (+ their children) by région
    region_of = {'fr-cog:com:' + c: r['REG'] for c, r in com_cog.items()}
    region_of[paris_eid] = '11'

    def part(r):
        if r['is_active'] == 'N':
            return 'communes_terminated'
        if r['code_scheme'] == 'insee_com':
            return 'communes_' + region_of.get(r['entity_id'], 'om')
        if r['code_scheme'] in ('insee_comd', 'insee_coma', 'insee_arm'):
            return 'communes_' + region_of[r['parent_id']]
        return 'upper'
    files = write_split(os.path.join(OUT, 'units'), rows, LOCAL_COLUMNS, part)
    write_csv(os.path.join(OUT, 'code_xwalk.csv'), xw, CODE_XW_COLUMNS)
    write_csv(os.path.join(OUT, 'boundary_xwalk.csv'), bx, BOUNDARY_COLUMNS)
    write_csv(os.path.join(OUT, 'gaps.csv'), sorted(gaps, key=lambda g: (g['issue'], g['code'])), ['code', 'issue'])
    stats['units'] = len(rows)
    stats['gaps'] = len(gaps)
    return rows, dict(sorted(stats.items())), [os.path.relpath(f, ROOT) for f in files]


if __name__ == '__main__':
    import json
    reg = Registry()
    rows, stats, files = build(reg)
    print(json.dumps(stats, indent=1), files)
    if '--save' in sys.argv:
        reg.save()
