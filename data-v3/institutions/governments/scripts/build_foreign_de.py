"""German government units at every level (foreign/de/), keyed by the Amtlicher Regionalschluessel (ARS).

Sources:
  * Destatis, Regionalschluessel code list (all Gemeinden by ARS, as in the Gemeindeverzeichnis GV-ISys), version
    2026-09-30, published by Destatis on XRepository (www.destatis.de itself refuses connections from this build host).
  * BKG Verwaltungsgebiete 1:250 000 (VG250), Stand 01.01.2026, attribute tables (Excel download; no geometry): Laender,
    Regierungsbezirke, Kreise (with their designation BEZ), Gemeindeverbaende (VWG layer: Amt, Verbandsgemeinde,
    Samtgemeinde, Verwaltungsgemeinschaft, Verwaltungsverband, erfuellende Gemeinde), Gemeinden; WSK = date of legal effect.
  * Boundary crosswalk keyed to Geo's editions (data/geo data-v3/geo/FOREIGN_VINTAGES.md): VG250 Stand 01.01.2026,
    layers LAN/KRS/VWG/GEM.
  * History: codes in VG250 01.01.2025 / 31.12.2025 but not 01.01.2026 (derived from the BKG editions; Destatis
    Gebietsaenderungen is on www.destatis.de, unreachable from this host).
Bund = existing nation:de; Laender = existing subdivision:de-xx (ARS Land code -> ISO 3166-2, names checked); Berlin and
Hamburg are Land and Gemeinde at once (mapped, not re-minted). New IDs: de-ars:<12-digit ARS> (shorter keys zero-padded).
"""
import collections, os, re, sys, urllib.parse
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CACHE, ROOT, Registry, fetch, manifest, norm, write_csv
from wikidata import sparql, qv
from foreign_local import (FOREIGN, LOCAL_COLUMNS, CODE_XW_COLUMNS, BOUNDARY_COLUMNS, check, existing_foreign, read_xlsx, wfs,
                           write_split)

OUT = os.path.join(FOREIGN, 'de')
RS_VERSION = '2026-09-30'
RS_URN = 'urn:de:bund:destatis:bevoelkerungsstatistik:schluessel:rs'
RS_URL = 'https://www.xrepository.de/api/version_codeliste/{}_{}/genericode'.format(RS_URN, RS_VERSION)
RS_PAGE = 'https://www.xrepository.de/details/{}'.format(RS_URN)
VG250 = 'https://sgx.geodatenzentrum.de/wfs_vg250'
VG250_VINTAGE = '2026-01-01'
# BKG VG250 attribute tables (Excel, table VGTB_ATT_VG), the same editions Geo builds from. The VG250 WFS
# (sgx.geodatenzentrum.de/wfs_vg250) used before served the 31.12.2025 state (no Hanau 06415) and shifted WSK one day
# (2009-01-01 -> 2008-12-31Z), so the downloads replace it.
VG_DL = 'https://daten.gdz.bkg.bund.de/produkte/vg/'
VG_EDITIONS = {'20260101': VG_DL + 'vg250_ebenen_0101/2026/vg250_01-01.ee.excel.ebenen.zip',
               '20251231': VG_DL + 'vg250_ebenen_1231/2025/vg250_12-31.ee.excel.ebenen.zip',
               '20250101': VG_DL + 'vg250_ebenen_0101/2025/vg250_01-01.ee.excel.ebenen.zip'}
VG_ADE = {'sta': '1', 'lan': '2', 'rbz': '3', 'krs': '4', 'vwg': '5', 'gem': '6'}
# Successors of codes that ended on 2025-12-31, as listed in data/geo README.md @ a92f2b0 (VG250 31.12.2025 vs
# 01.01.2026) and in the request of 2026-10-18; BKG itself states no successor. Codes not listed get none.
STATED_SUCCESSOR = {'064350014014': '064150000000',      # Hanau kreisfrei (Kreis 06415)
                    '010570008008': '010575785008',      # Bönebüttel joins an Amt
                    '160775052043': '160770043043',      # Schmölln, new code after Dobitschen merged in
                    '160775052003': '160770043043'}      # Dobitschen merged into Schmölln
GEO_NOTE = 'data/geo README.md @ a92f2b0'
# Geo's exact boundary editions (FOREIGN_VINTAGES.md): layer key -> boundary_dataset
GEO_LAYERS = {'lan': 'BKG VG250 VG250_LAN', 'krs': 'BKG VG250 VG250_KRS', 'vwg': 'BKG VG250 VG250_VWG',
              'gem': 'BKG VG250 VG250_GEM'}
GF4 = {}                                   # WFS cache key -> ARS that have a GF=4 feature
PROPS = ['ars', 'ade', 'gf', 'ags', 'gen', 'bez', 'nbd', 'wsk']
LIC_D = 'dl-de/by-2-0 (Statistisches Bundesamt (Destatis), 2026)'
LIC_B = 'dl-de/by-2-0 (BKG 2026, Datenquellen: https://sg.geodatenzentrum.de/web_public/gdz/datenquellen/datenquellen_vg_nuts.pdf)'
# Destatis Land code (first 2 ARS digits) -> ISO 3166-2:DE (checked against the Land names below)
LAND_ISO = {'01': 'SH', '02': 'HH', '03': 'NI', '04': 'HB', '05': 'NW', '06': 'HE', '07': 'RP', '08': 'BW', '09': 'BY',
            '10': 'SL', '11': 'BE', '12': 'BB', '13': 'MV', '14': 'SN', '15': 'ST', '16': 'TH'}
CITY_STATES = {'110000000000': 'subdivision:de-be', '020000000000': 'subdivision:de-hh'}   # Land = Gemeinde
# VG250 VWG designations that are associations of municipalities (others are single municipalities, not a level)
ASSOC = {'Amt': 'amt', 'Verbandsgemeinde': 'verbandsgemeinde', 'Samtgemeinde': 'samtgemeinde',
         'Verwaltungsgemeinschaft': 'verwaltungsgemeinschaft', 'Verwaltungsverband': 'verwaltungsverband',
         'Erfüllende Gemeinde': 'erfuellende_gemeinde'}
KREIS = {'Landkreis': 'landkreis', 'Kreis': 'kreis', 'Kreisfreie Stadt': 'kreisfreie_stadt', 'Stadtkreis': 'stadtkreis'}
GEMFREI = re.compile(r'gemfr\.|gemeindefrei', re.I)


def ars12(a):
    return a + '0' * (12 - len(a))


def vg_edition(ed):
    """(ADE, ARS) -> unit of the VG250 edition ed (attribute table VGTB_ATT_VG), with WSK as an ISO date."""
    import datetime, zipfile
    key = 'bkg_vg250_xlsx_' + ed
    p = fetch(key, url=VG_EDITIONS[ed], fname=key + '.zipdata')
    x = os.path.join(CACHE, key + '.xlsx')
    if not os.path.exists(x) or os.path.getmtime(x) < os.path.getmtime(p):
        with zipfile.ZipFile(p) as z:
            n = next(n for n in z.namelist() if n.endswith('verwaltungsgebiete.xlsx'))
            open(x, 'wb').write(z.read(n))
    t = read_xlsx(x)['VGTB_ATT_VG']
    out = {}
    for v in t[1:]:
        r = dict(zip(t[0], v))
        w = r.get('WSK') or ''
        wsk = (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(w)))).isoformat() if w else ''
        k = (r['ADE'], r['ARS'])
        assert k not in out, k
        out[k] = dict(ars=r['ARS'], ade=int(r['ADE']), gf=4, ags=r['AGS'], gen=r['GEN'], bez=r['BEZ'], nbd=r['NBD'], wsk=wsk)
    return out


def layer(svc, name, key):
    lk = key.rsplit('_', 1)[-1]
    ed = vg_edition('20260101')
    out = {a: r for (ade, a), r in ed.items() if ade == VG_ADE[lk]}
    GF4[key] = set(out)
    return out


def destatis_rs():
    p = fetch('destatis_rs', url=RS_URL, fname='destatis_rs_{}.xml'.format(RS_VERSION))
    rows = [{v.get('ColumnRef'): v.findtext('SimpleValue') for v in r.findall('Value')} for r in ET.parse(p).getroot().iter('Row')]
    return {r['SCHLUESSEL']: r['Bezeichnung'] for r in rows if not r.get('Hinweis')}   # Hinweis rows: city-state districts


def wd_codes():
    """Wikidata items by exact ARS (P1388) and Kreisschluessel (P440); 1:1 links only."""
    out = {}
    for prop, key in (('P1388', 'wd_de_p1388'), ('P440', 'wd_de_p440')):
        by_code, by_item = collections.defaultdict(set), collections.defaultdict(set)
        for b in sparql(key, 'SELECT ?i ?v WHERE { ?i wdt:%s ?v . }' % prop):
            by_code[b['v']['value']].add(qv(b, 'i'))
            by_item[qv(b, 'i')].add(b['v']['value'])
        for c, qs in by_code.items():
            if len(qs) == 1 and len(by_item[next(iter(qs))]) == 1:
                out[(prop, c)] = next(iter(qs))
    return out


def build(reg):
    os.makedirs(OUT, exist_ok=True)
    rs = destatis_rs()
    L = {k: layer(VG250, 'vg250:vg250_' + k, 'bkg_vg250_' + k) for k in ('sta', 'lan', 'rbz', 'krs', 'vwg', 'gem')}
    wd = wd_codes()
    man = manifest()
    ra_d = man['destatis_rs']['retrieved_at']
    ra_b = man['bkg_vg250_xlsx_20260101']['retrieved_at']
    ra_w = max(man['wd_de_p1388']['retrieved_at'], man['wd_de_p440']['retrieved_at'])
    known = existing_foreign()
    stats, gaps = collections.Counter(), []
    land = {}
    for a, r in L['lan'].items():
        e = 'subdivision:de-' + LAND_ISO[a[:2]].lower()
        assert norm(known[e]['name']) == norm(r['gen']), (e, r['gen'])
        land[a[:2]] = e
    assert len(land) == 16
    url_b, url_d = VG_EDITIONS['20260101'], RS_PAGE

    def row(eid, name, alt, sub, gs, parent, code, ags, q, wsk, src, note='', flags=()):
        srcs = src + (';wikidata_foreign' if q else '')
        ra = max(ra_d if 'destatis' in src else '', ra_b if 'bkg' in src else '', ra_w if q else '')
        return dict(entity_id=eid, name=name, name_local='', name_en='', alt_name=alt if alt != name else '', type='foreign',
                    subtype=sub, gov_status=gs, parent_id=parent, member_of='', country='DE', code_scheme='ars', code=code,
                    alt_code=ags, iso_3166_2='', wikidata_qid=q, code_valid_from=(wsk or '').rstrip('Z'), code_valid_to='',
                    valid_from='', valid_to='', is_active='Y', note=note, flags=';'.join(flags), source=srcs,
                    source_url=' ; '.join(u for u, s in ((url_d, 'destatis'), (url_b, 'bkg')) if s in src),
                    source_date=';'.join(d for d, s in ((RS_VERSION, 'destatis'), (VG250_VINTAGE, 'bkg')) if s in src),
                    retrieved_at=ra, license=' ; '.join(l for l, s in ((LIC_D, 'destatis'), (LIC_B, 'bkg')) if s in src))
    rows, ids = [], {}
    # Regierungsbezirke (administrative, no elected body)
    for a, r in sorted(L['rbz'].items()):
        eid = reg.get(['de-ars:' + ars12(a)], 'de-ars:' + ars12(a), ra_b[:10])
        ids[a] = eid
        rows.append(row(eid, r['gen'], '', 'regierungsbezirk', 'administrative', land[a[:2]], ars12(a), '', '', r['wsk'],
                        'bkg_vg250', 'Regierungsbezirk: state administrative region, not self-governing'))

    def up(a5):
        return ids.get(a5[:3]) or land[a5[:2]]
    # Kreise: Landkreise / Kreise from VG250; kreisfreie Staedte are Gemeinden whose ARS ends in 0000000 (Destatis key)
    # areas without a municipal government: gemeindefreie Gebiete (named so, VG250 BEZ, or Destatis Verband key 9999:
    # coastal waters, the German-Luxembourg condominium)
    gem_names = {a: n for a, n in rs.items() if not GEMFREI.search(n) and a[5:9] != '9999'
                 and L['gem'].get(a, {}).get('bez') != 'Gemeindefreies Gebiet'}
    stats['gemeindefrei_excluded'] = len(rs) - len(gem_names)
    for a, r in sorted(L['krs'].items()):
        if r['bez'] in ('Kreisfreie Stadt', 'Stadtkreis'):
            continue
        q = wd.get(('P440', a), '')
        eid = reg.get(['de-ars:' + ars12(a)], 'de-ars:' + ars12(a), ra_b[:10])
        ids[a] = eid
        rows.append(row(eid, r['gen'], '', KREIS[r['bez']], 'self_governing', up(a), ars12(a), a, q, r['wsk'], 'bkg_vg250'))
    xw = []
    for a, n in sorted(gem_names.items()):
        if not a.endswith('0000000'):
            continue
        if a in CITY_STATES:
            xw.append(dict(entity_id=CITY_STATES[a], code_scheme='ars', code=a, relation='same_government',
                           note='city-state: Land, Kreis and Gemeinde are one government', source='destatis_rs', source_url=url_d))
            ids[a[:5]] = ids[a] = CITY_STATES[a]
            continue
        k, g = L['krs'].get(a[:5]), L['gem'].get(a)
        flags = [] if k else ['kreisfrei_from_ars_structure']
        if not k:
            gaps.append({'code': a, 'issue': 'kreisfreie Stadt in Destatis {} but not in VG250 {} (new since)'.format(RS_VERSION, VG250_VINTAGE)})
        q = wd.get(('P1388', a), '')
        eid = reg.get(['de-ars:' + a], 'de-ars:' + a, ra_d[:10])
        ids[a[:5]] = ids[a] = eid
        rows.append(row(eid, n, g['gen'] if g else '', KREIS[k['bez']] if k else 'kreisfreie_stadt', 'self_governing', up(a), a,
                        a[:5] + a[9:], q, (g or {}).get('wsk', ''), 'destatis_rs;bkg_vg250' if k else 'destatis_rs',
                        'kreisfreie Stadt: Kreis and Gemeinde in one government', flags))
    # Gemeindeverbaende (VG250 VWG layer, associations only)
    used_v = {a[:9] for a in gem_names}
    for a, r in sorted(L['vwg'].items()):
        if r['bez'] not in ASSOC:
            continue
        if a[:5] not in ids:
            gaps.append({'code': a, 'issue': 'Gemeindeverband whose Kreis is not in the unit list'})
            continue
        flags = [] if a in used_v else ['no_member_in_destatis_' + RS_VERSION]
        if a not in used_v:
            gaps.append({'code': a, 'issue': 'Gemeindeverband in VG250 {} with no member Gemeinde in Destatis {}'.format(VG250_VINTAGE, RS_VERSION)})
        sub = ASSOC[r['bez']]
        q = wd.get(('P1388', a), '') or wd.get(('P1388', ars12(a)), '')
        eid = reg.get(['de-ars:' + ars12(a)], 'de-ars:' + ars12(a), ra_b[:10])
        ids[a] = eid
        rows.append(row(eid, r['gen'], '', sub, 'association' if sub != 'erfuellende_gemeinde' else 'administrative_arrangement',
                        ids[a[:5]], ars12(a), '', q, r['wsk'], 'bkg_vg250',
                        'Gemeindeverband ({})'.format(r['bez']) if sub != 'erfuellende_gemeinde' else
                        'erfüllende Gemeinde: one member municipality carries out the administration for the others', flags))
    # Gemeinden (Destatis), parent = Gemeindeverband if any, else Kreis / kreisfreie Stadt
    for a, n in sorted(gem_names.items()):
        if a.endswith('0000000'):
            continue
        g = L['gem'].get(a)
        flags = []
        if a[:5] not in ids:
            gaps.append({'code': a, 'issue': 'Gemeinde whose Kreis {} is not in the unit list'.format(a[:5])})
            continue
        parent = ids.get(a[:9]) or ids[a[:5]]
        if a[:9] not in L['vwg']:
            gaps.append({'code': a, 'issue': 'Gemeindeverband key {} not in VG250 {} (changed since)'.format(a[:9], VG250_VINTAGE)})
            flags.append('verband_not_in_vg250')
        if not g:
            flags.append('not_in_vg250')
        q = wd.get(('P1388', a), '')
        eid = reg.get(['de-ars:' + a], 'de-ars:' + a, ra_d[:10])
        ids[a] = eid
        sub = 'stadt' if (g and g['bez'] == 'Stadt') or re.search(r', (\w+-)?(Stadt|St)\b', n) else 'gemeinde'
        rows.append(row(eid, n, g['gen'] if g else '', sub, 'self_governing', parent, a, a[:5] + a[9:], q,
                        (g or {}).get('wsk', ''), 'destatis_rs;bkg_vg250' if g else 'destatis_rs', '', flags))
    for r in rows:
        stats[r['subtype']] += 1
        stats['with_qid'] += bool(r['wikidata_qid'])
    # ---- history: codes in VG250 31.12.2025 (or 01.01.2025) that VG250 01.01.2026 no longer has, levels with
    # government rows (Kreis, Gemeindeverband association, Gemeinde; gemeindefreie Gebiete have no government)
    eds = {ed: vg_edition(ed) for ed in ('20250101', '20251231')}
    now = vg_edition('20260101')
    cur_ids = {r['entity_id'] for r in rows}
    ended = {}
    for ed in ('20250101', '20251231'):                      # later edition wins
        for k, r in eds[ed].items():
            if k not in now and k[0] in ('4', '5', '6'):
                ended[k] = dict(r, last=ed)
    ended_ids = set()
    ra_h = max(manifest()[k]['retrieved_at'] for k in ('bkg_vg250_xlsx_20250101', 'bkg_vg250_xlsx_20251231'))
    for (ade, a), r in sorted(ended.items()):
        if ade == '6' and GEMFREI.search(r['gen'] + ' ' + r['bez']):
            stats['ended_gemeindefrei_not_a_government'] += 1
            continue
        if ade == '5' and r['bez'] not in ASSOC:
            continue                                         # Einheitsgemeinde-type VWG units are not associations
        if ade == '4':
            sub, gs = KREIS[r['bez']], 'self_governing'
        elif ade == '5':
            sub = ASSOC[r['bez']]
            gs = 'association' if sub != 'erfuellende_gemeinde' else 'administrative_arrangement'
        else:
            sub, gs = ('stadt' if r['bez'] == 'Stadt' else 'gemeinde'), 'self_governing'
        eid_key = 'de-ars:' + ars12(a)
        assert eid_key not in cur_ids, eid_key
        succ = STATED_SUCCESSOR.get(a, '')
        sid = 'de-ars:' + ars12(succ) if succ else ''
        if sid and sid not in cur_ids:
            gaps.append({'code': a, 'issue': 'stated successor {} has no current row'.format(succ)})
            sid = ''
        par = [p for p in ('de-ars:' + ars12(a[:9]), 'de-ars:' + ars12(a[:5])) if p in cur_ids | ended_ids or p == eid_key]
        parent = next((p for p in par if p != eid_key), land[a[:2]])
        end = '2025-12-31' if r['last'] == '20251231' else ''
        note = 'code in BKG VG250 {} but not 01.01.2026 (derived from the BKG editions; ended {})'.format(
            '31.12.2025' if r['last'] == '20251231' else '01.01.2025', end or 'during 2025')
        if sid:
            note += '; successor as listed in ' + GEO_NOTE
        eid = reg.get([eid_key], eid_key, ra_h[:10])
        rows.append(dict(entity_id=eid, name=r['gen'], name_local='', name_en='', alt_name='', type='foreign', subtype=sub,
                         gov_status=gs, parent_id=parent, member_of='', country='DE', code_scheme='ars', code=ars12(a),
                         alt_code=r['ags'] if ade == '6' else '', iso_3166_2='', wikidata_qid='', code_valid_from=r['wsk'],
                         code_valid_to=end, valid_from='', valid_to='', is_active='N', predecessor_id='', successor_id=sid,
                         note=note, flags=';'.join(['code_terminated', 'derived_from_vg250_editions'] +
                                                   (['successor_stated_by_geo'] if sid else [])),
                         source='bkg_vg250_history', source_url=VG_DL, source_date=end or '2025-12-31', retrieved_at=ra_h,
                         license='dl-de/by-2-0 (BKG 2026)'))
        ended_ids.add(eid)
        stats['ended|' + sub] += 1
        stats['ended_with_successor'] += bool(sid)
    pred = collections.defaultdict(set)
    for r in rows:
        if r.get('successor_id'):
            pred[r['successor_id']].add(r['entity_id'])
    for r in rows:
        if pred.get(r['entity_id']):
            r['predecessor_id'] = ';'.join(sorted(pred[r['entity_id']]))
    check(rows, known)
    for a2, e in sorted(land.items()):
        xw.append(dict(entity_id=e, code_scheme='ars', code=a2, relation='same_government', note='Land',
                       source='bkg_vg250', source_url=url_b))
        xw.append(dict(entity_id=e, code_scheme='iso_3166_2', code='DE-' + LAND_ISO[a2], relation='same_government',
                       note='Land', source='iso_codes', source_url=''))
    xw.sort(key=lambda x: (x['entity_id'], x['code_scheme'], x['code']))
    # boundary crosswalk: Geo's VG250 layers (LAN, KRS, VWG, GEM), codes present as GF=4 features
    bx = []
    by_ars = collections.defaultdict(list)       # layer key -> (entity, code)
    for a, r in L['sta'].items():
        by_ars['sta'].append(('nation:de', a))
    for a2, e in land.items():
        by_ars['lan'].append((e, next(x for x in L['lan'] if x[:2] == a2)))
    for r in rows:
        c = r['code']
        if r['is_active'] != 'Y':
            continue                                          # ended codes are not in the 2026 boundaries
        if r['subtype'] == 'regierungsbezirk':
            by_ars['rbz'].append((r['entity_id'], c[:3]))
        elif r['subtype'] in KREIS.values():
            by_ars['krs'].append((r['entity_id'], c[:5]))
            if r['subtype'] in ('kreisfreie_stadt', 'stadtkreis'):
                by_ars['vwg'].append((r['entity_id'], c[:9]))
                by_ars['gem'].append((r['entity_id'], c))
        elif r['subtype'] in ASSOC.values():
            by_ars['vwg'].append((r['entity_id'], c[:9]))
        else:
            by_ars['gem'].append((r['entity_id'], c))
    for a in CITY_STATES:
        by_ars['krs'].append((CITY_STATES[a], a[:5]))
        by_ars['gem'].append((CITY_STATES[a], a))
    for lk, ds in GEO_LAYERS.items():
        have = GF4['bkg_vg250_' + lk]
        for e, c in by_ars[lk]:
            if c in have:
                bx.append(dict(entity_id=e, boundary_dataset=ds, boundary_code=c, vintage=VG250_VINTAGE,
                               relation='same_code', boundary_type='', source_url=VG_EDITIONS['20260101']))
                stats['boundary|' + ds] += 1
            else:
                stats['boundary_missing|' + ds] += 1
                gaps.append({'code': c, 'issue': 'not in {} as GF=4 ({})'.format(ds, e)})
    bx.sort(key=lambda x: (x['boundary_dataset'], x['boundary_code'], x['entity_id']))
    files = write_split(os.path.join(OUT, 'units'), rows, LOCAL_COLUMNS, lambda r: r['code'][:2])
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
    reg.save()
    print(json.dumps(stats, indent=1), files)
