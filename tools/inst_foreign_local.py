"""Governments bot country layers (foreign/gb, foreign/de, foreign/fr at a pinned commit; read only) -> data-v3/inst.

Full Stack ruling (Oct 18):
  * entity ids `<kind>:<cc>-<code at minting>` (lowercase, frozen); the bot's gss: / de-ars: / fr-cog:<level>: / fr-siren:
    ids are feed ids in entity_feed_map only. The current code goes in code_scheme / code (UK gss, DE ars, FR insee_*/siren).
      GB  <kind>:gb-<gss>                      DE  <kind>:de-<12-digit ARS>
      FR  municipality:fr-<insee com>          county:fr-<département code | ctcd code (69m, 6ae)>
          submunicipal:fr-<comd|coma|arm>-<code> (the level is needed: 584 communes déléguées share their commune's code)
          intermunicipal:fr-<siren>            regional_authority:fr-<insee région code>
  * kinds: KIND below; Regierungsbezirke and erfüllende Gemeinde rows are feed_only (Kreise -> their Land; Gemeinden under an
    erfüllende Gemeinde -> its parent Kreis).
  * gov_status from the feed's own fields only: self_governing -> government; FR intercommunal (EPCI à fiscalité propre / EPT,
    councils by the ruling) -> government; delegated / sub_municipal -> dependent; parish -> empty + flag
    council_status_unknown; DE association: the feed does not say whether the body has a council -> empty + flag
    gov_status_unknown:council_not_in_feed + gap intermunicipal_council_unknown (never guessed).
  * FR région councils are regional_authority rows; the région areas stay subdivision:<iso> / territory:<iso2>; relation `area`
    council -> area. Guadeloupe / Réunion: territory:gp / territory:re stay the area; the département council
    (county:fr-971 / -974) and the région council (regional_authority:fr-01 / -04) are their children; the 56 communes sit
    under the département council (builder override of the bot's mapping, logged as govbot_mapping_overridden).
  * valid_from = FR establishment dates (INSEE mouvements) + valid_from_source + flag predecessor_pending (relation type
    `predecessor` exists, no rows yet). UK RGC operative dates / DE VG250 WSK are code dates -> code_valid_from.
  * feed-defect workarounds, each self-checking and logged in entities_summary.json country_layers.workarounds (applied /
    noop): fr-cog:com:97701 / 97801 = territory:bl / territory:mf (since e0ee04c the bot crosswalks them same_government with
    no QID -> noop; any unit whose INSEE commune code the bot crosswalks same_government to a registry row is mapped there);
    SIRENs 215500398 / 213100068 on two communes (DGCL SIRENs since e0ee04c -> noop); subdivision:gb-eng area_only (noop
    since e0ee04c).
  * history (e0ee04c): terminated codes (is_active N). Code change of the same government (UK: official successor with the
    same name and subtype, followed through terminated successors; FR: COG mouvement 41 / 50) -> feed-map row to the current
    entity (code history), not minted. Distinct government that ended (UK: other successor(s), or no link and no current
    namesake under the same parent; FR: mouvement 32 / commune merged) -> minted with valid_to = the code's end date and flag
    is_active_false:code_terminated. No link but a current namesake under the same parent -> feed_only + gap
    code_terminated_unresolved. `predecessor` relations only point at an ENDED entity (a link between two current
    governments is a boundary transfer); predecessor_pending is cleared on rows that got one.
  * lean rows: no parent relation rows (parent_id carries it), no source_record_id (the feed id is in entity_feed_map), no
    outside_v2_scope flag (no foreign local unit ever has a unit), empty optional fields stay empty.
"""
import csv, hashlib, io, re, subprocess, collections as C
P = 'data-v3/institutions/governments/foreign/'
CCS = ['gb', 'de', 'fr']
FEED_PREFIX = ('gss:', 'de-ars:', 'fr-cog:', 'fr-siren:')
KIND = {
    'gb': {'county_council': 'county', 'unitary_authority': 'local_authority', 'non_metropolitan_district': 'local_authority',
           'metropolitan_borough': 'local_authority', 'london_borough': 'local_authority', 'principal_council': 'local_authority',
           'council_area': 'local_authority', 'district_council': 'local_authority', 'combined_authority': 'regional_authority',
           'strategic_authority': 'regional_authority', 'civil_parish': 'parish', 'community': 'parish'},
    'de': {'landkreis': 'county', 'kreis': 'county', 'gemeinde': 'municipality', 'stadt': 'municipality', 'kreisfreie_stadt': 'municipality',
           'stadtkreis': 'municipality', 'amt': 'intermunicipal', 'verbandsgemeinde': 'intermunicipal', 'samtgemeinde': 'intermunicipal',
           'verwaltungsgemeinschaft': 'intermunicipal', 'verwaltungsverband': 'intermunicipal', 'regierungsbezirk': None, 'erfuellende_gemeinde': None},
    'fr': {'commune': 'municipality', 'ville_de_paris': 'municipality', 'conseil_departemental': 'county', 'metropole_de_lyon': 'county',
           'collectivite_europeenne_d_alsace': 'county', 'region': 'regional_authority', 'communaute_de_communes': 'intermunicipal',
           'communaute_d_agglomeration': 'intermunicipal', 'communaute_urbaine': 'intermunicipal', 'metropole': 'intermunicipal',
           'etablissement_public_territorial': 'intermunicipal', 'commune_deleguee': 'submunicipal', 'commune_associee': 'submunicipal',
           'arrondissement_municipal': 'submunicipal'}}
LEVEL = {'regional_authority': 'subnational', 'county': 'county'}   # everything else: local
COUNTY_POWERS = {'kreisfreie_stadt', 'stadtkreis', 'ville_de_paris'}
DUP_REGISTRY = {'fr-cog:com:97701': 'territory:bl', 'fr-cog:com:97801': 'territory:mf'}
BAD_SIREN = {'215500398': ('fr-cog:com:55039', 'fr-cog:com:55102'), '213100068': ('fr-cog:com:31006', 'fr-cog:com:46002')}
CORSE_AREA = 'subdivision:fr-20r'
GPRE = {'territory:gp': ('971', '01'), 'territory:re': ('974', '04')}   # area -> (département code, région code)
PENDING = ('territory:gf', 'territory:mq', 'territory:yt')   # single collectivities (CTU): not ruled; bot mapping kept, parked
XW_PREFIX = {'insee_com': 'insee_com', 'gss': 'gss', 'ars': 'de-ars', 'iso_3166_2': 'iso3166', 'insee_dep': 'insee_dep', 'insee_reg': 'insee_reg', 'insee_ctcd': 'insee_ctcd',
             'insee_comer': 'insee_comer', 'siren': 'fr-siren'}   # département / région / CTCD codes are not the bot's unit ids (fr-cog:dep:69 is the Rhône council; insee_dep:69 is the area)

def _raw(R, sha, path): return subprocess.run(['git', '-C', R, 'show', f'{sha}:{path}'], capture_output=True, check=True).stdout

def is_feed_id(i): return i.startswith(FEED_PREFIX)

def load(R, sha):
    commit = subprocess.run(['git', '-C', R, 'rev-parse', sha + '^{commit}'], capture_output=True, text=True, check=True).stdout.strip()
    L = {'commit': commit, 'files': {}, 'units': {}, 'xwalk': {}}
    for cc in CCS:
        names = subprocess.run(['git', '-C', R, 'ls-tree', '--name-only', commit, P + cc + '/'], capture_output=True, text=True, check=True).stdout.split()
        L['units'][cc] = []
        for path in sorted(names):
            f = path[len(P):]
            if not (f.split('/')[1].startswith('units') or f.endswith('/code_xwalk.csv')): continue
            raw = _raw(R, commit, path)
            rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
            L['files'][f] = {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'rows': len(rows)}
            for r in rows: r['_file'] = f
            if f.endswith('/code_xwalk.csv'): L['xwalk'][cc] = rows
            else: L['units'][cc] += rows
    # the bot's frozen-id registry for the country (id_registry/<cc>.csv since b198633): ids no longer in the unit files
    # (or marked pruned) are pruned history -> never minted by us
    rp = P.replace('foreign/', '') + f'id_registry/'
    try:   # the bot's HISTORY_CUTOFF (scripts/common.py, since bd0ce1a): rows ended before it and their links are not written
        m = re.search(r"^HISTORY_CUTOFF = '(\d{4}-\d\d-\d\d)'", _raw(R, commit, P.replace('foreign/', '') + 'scripts/common.py').decode(), re.M)
        L['history_cutoff'] = m.group(1) if m else ''
    except subprocess.CalledProcessError: L['history_cutoff'] = ''
    L['registry'] = {}
    for cc in CCS:
        try: raw = _raw(R, commit, rp + cc + '.csv')
        except subprocess.CalledProcessError: L['registry'][cc] = []; continue
        L['registry'][cc] = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
    return L

def eid_of(cc, r, kind):
    fid, code = r['entity_id'], r['code']
    if cc in ('gb', 'de'): return f'{kind}:{cc}-{code.lower()}'
    lvl = fid.split(':')[1] if fid.startswith('fr-cog:') else 'siren'
    if lvl == 'com': return f'municipality:fr-{code.lower()}'
    if lvl == 'dep': return f'county:fr-{fid.split(":")[2].lower()}'
    if lvl == 'ctcd': return f'county:fr-{code.lower()}'
    if lvl == 'reg': return f'regional_authority:fr-{code}'
    if lvl in ('comd', 'coma', 'arm'): return f'submunicipal:fr-{lvl}-{code.lower()}'
    if lvl == 'siren': return f'intermunicipal:fr-{code}'
    raise ValueError(fid)

def esc(x): return x.replace(';', '\\;')

def integrate(L, ents, new_row):
    """ents: entity_id -> row (mutable; minted rows added). Returns dict(rows, fmap, rels, gaps, stats)."""
    qid_owner = {e['wikidata'].replace('wikidata:', ''): eid for eid, e in ents.items() if e.get('wikidata')}
    rows, fmap, rels, gaps, st = [], [], [], [], C.Counter()
    units = {r['entity_id']: (cc, r) for cc in CCS for r in L['units'][cc]}
    # pruned upstream (HISTORY_CUTOFF): in the bot's registry, not in the unit files, or marked pruned. Never minted here;
    # an id we would derive from a pruned feed id must not already be one of our entities (frozen; reported if so)
    pruned = {x['entity_id'] for cc in CCS for x in L.get('registry', {}).get(cc, [])
              if x['entity_id'] not in units or x.get('pruned') or 'prun' in (x.get('status', '') + x.get('note', '') + x.get('flags', '')).lower()}
    def would_be(f_):
        pre, _, rest = f_.partition(':')
        if pre == 'gss': return {f'{k}:gb-{rest.lower()}' for k in ('county', 'local_authority', 'parish', 'regional_authority')}
        if pre == 'de-ars': return {f'{k}:de-{rest}' for k in ('county', 'municipality', 'intermunicipal')}
        if f_.startswith('fr-cog:com:'): return {f'municipality:fr-{rest.split(":")[1].lower()}'}
        return set()
    pruned_in_ents = sorted({i for f_ in pruned for i in would_be(f_) if i in ents})
    st['pruned_registry_ids'] = len(pruned); st['history_cutoff'] = L.get('history_cutoff', ''); st['pruned_already_minted_by_us'] = len(pruned_in_ents)
    assert not (pruned & {f_ for f_, (c_, r_) in units.items() if 'prun' in (r_.get('flags') or '')}), 'pruned row in unit files'
    # a unit whose own code the bot crosswalks as same_government to an existing registry row is that row (not minted):
    # since e0ee04c this covers fr-cog:com:97701 / 97801 -> territory:bl / territory:mf, so the DUP_REGISTRY workaround is a no-op
    xsame = {}
    for x in L['xwalk']['fr']:
        f_ = f"fr-cog:com:{x['code']}"
        if x['code_scheme'] == 'insee_com' and x['relation'] == 'same_government' and x['entity_id'] in ents and f_ in units: xsame[f_] = x['entity_id']
    WORKAROUND = []
    for fid, t in DUP_REGISTRY.items():
        if xsame.get(fid) == t and not units[fid][1]['wikidata_qid']: WORKAROUND.append({'workaround': f'{fid}->{t}', 'outcome': 'noop', 'detail': 'bot code_xwalk maps it same_government and the row has no QID'})
        else: xsame[fid] = t; WORKAROUND.append({'workaround': f'{fid}->{t}', 'outcome': 'applied', 'detail': 'bot still emits the commune as a separate row'})
    for s_, pair in BAD_SIREN.items():
        hit = [p_ for p_ in pair if units[p_][1]['alt_code'] == s_]
        WORKAROUND.append({'workaround': f'siren {s_}', 'outcome': 'applied' if len(hit) > 1 else 'noop', 'detail': f'on {len(hit)} of ' + '/'.join(pair)})
    eng = [x['relation'] for x in L['xwalk']['gb'] if x['entity_id'] == 'subdivision:gb-eng']
    WORKAROUND.append({'workaround': 'subdivision:gb-eng area_only', 'outcome': 'noop' if set(eng) == {'area_only'} else 'applied', 'detail': 'bot crosswalk relations: ' + ';'.join(eng)})
    # GP/RE (ruling Oct 18): the bot emits the départements' councils as units (fr-cog:dep:971/974, parent the territory)
    # and the territories area_only since 310086f -> the builder override drops itself; it stays for a feed without them
    GPRE_ACT = {a: v for a, v in GPRE.items() if f'fr-cog:dep:{v[0]}' not in units}
    for a, (d, g) in GPRE.items():
        WORKAROUND.append({'workaround': f'{a} council split', 'outcome': 'applied' if a in GPRE_ACT else 'dropped', 'detail': f'bot units fr-cog:dep:{d} / fr-cog:reg:{g} ' + ('absent' if a in GPRE_ACT else 'present, parent ' + units.get(f'fr-cog:reg:{g}', ('', {'parent_id': '?'}))[1]['parent_id'])})
    bad_siren = {s_ for s_, pair in BAD_SIREN.items() if sum(units[p_][1]['alt_code'] == s_ for p_ in pair) > 1}
    # history (e0ee04c): is_active N rows. A terminated code whose official successor chain (UK ONS CHD Changes; FR COG
    # mouvement) reaches a current code of the same government is a CODE CHANGE: it maps to that entity (code history in the
    # feed map), nothing minted. The same government = UK: a successor with the same name and subtype (followed through
    # terminated successors); FR: COG mouvement 41 (code change on a département change) / 50 (code change on a chef-lieu
    # transfer). Every other terminated row with a link (UK: successor of another name / split; FR mouvement 32: merged into
    # a commune nouvelle) or with no link and no current namesake under the same parent is a distinct government that ENDED:
    # minted with valid_to = the code's end date (RGC TERM_DATE / COG end date) and flag is_active_false:code_terminated.
    # No link but a current namesake under the same parent: undecidable from the data -> feed_only + gap code_terminated_unresolved.
    nm = lambda x: re.sub(r'[^a-z]', '', x.lower())
    term = {f: u for f, u in units.items() if u[1]['is_active'] == 'N'}
    live_by_parent_name = C.defaultdict(set)
    for f, (cc, r) in units.items():
        if r['is_active'] != 'N': live_by_parent_name[(r['parent_id'], nm(r['name']))].add(f)
    code_change, ended, unresolved = {}, set(), set()
    def same_gov(fid, seen=()):
        cc, r = units[fid]
        if cc == 'fr':
            m = re.search(r'COG mouvement (\d+)', r['note']); mv = m.group(1) if m else ''
            succ = [x for x in r['successor_id'].split(';') if x]
            if mv in ('41', '50') and len(succ) == 1 and succ[0] in units:
                return succ[0] if units[succ[0]][1]['is_active'] != 'N' else (same_gov(succ[0], seen + (fid,)) if succ[0] not in seen else None)
            return None
        if cc == 'de':   # BKG VG250 editions: one successor carrying the same name (name or alt_name) = same government recoded
            succ = [x for x in r['successor_id'].split(';') if x]
            nms = lambda u: {nm(u['name']), nm(u.get('alt_name') or u['name'])}
            if len(succ) == 1 and succ[0] in units and nms(units[succ[0]][1]) & nms(r):
                return succ[0] if units[succ[0]][1]['is_active'] != 'N' else None
            return None
        for sx in sorted(x for x in r['successor_id'].split(';') if x):
            if sx in units and sx not in seen and nm(units[sx][1]['name']) == nm(r['name']) and units[sx][1]['subtype'] == r['subtype']:
                return sx if units[sx][1]['is_active'] != 'N' else same_gov(sx, seen + (fid,))
        return None
    for fid, (cc, r) in sorted(term.items()):
        if KIND[cc][r['subtype']] is None: st[f'history|{cc}|feed_only_kind'] += 1; continue   # e.g. an ended erfüllende Gemeinde: stays feed_only
        t = same_gov(fid)
        if t: code_change[fid] = t; st[f'history|{cc}|code_change'] += 1
        elif r['successor_id'] or cc == 'fr' or not (live_by_parent_name[(r['parent_id'], nm(r['name']))]): ended.add(fid); st[f'history|{cc}|ended_minted'] += 1
        else: unresolved.add(fid); st[f'history|{cc}|unresolved_feed_only'] += 1
    f2e, feed_only = {}, {}
    for fid, (cc, r) in units.items():
        k = KIND[cc][r['subtype']]
        if fid in xsame: f2e[fid] = xsame[fid]
        elif k is None or fid in unresolved: feed_only[fid] = r
        elif fid not in code_change: f2e[fid] = eid_of(cc, r, k)
    minted_ids = [v for f, v in f2e.items() if f not in xsame]
    assert len(set(minted_ids)) == len(minted_ids), 'minted id collision'
    assert not set(minted_ids) & set(ents), 'minted id already in registry'
    clash = set(minted_ids) & {i for f_ in pruned for i in would_be(f_)}
    assert not clash, ('minted id equals a pruned id', sorted(clash)[:5])   # never re-mint a pruned id
    for fid, t in code_change.items(): f2e[fid] = f2e[t]
    gpre_county = {a: f'county:fr-{d}' for a, (d, _) in GPRE_ACT.items()}
    gpre_reg = {f'fr-cog:reg:{g}': a for a, (_, g) in GPRE_ACT.items()}
    # Corse (ruling on 04227d3): the communes' parent is the Collectivité de Corse council (minted from the bot's
    # code_xwalk insee_ctcd row of subdivision:fr-20r, as regional_authority:fr-<insee_reg>), which has an `area` relation to
    # subdivision:fr-20r (the GP/RE pattern)
    cx = {x['code_scheme']: x for x in L['xwalk']['fr'] if x['entity_id'] == CORSE_AREA}
    corse_council = f"regional_authority:fr-{cx['insee_reg']['code']}" if 'insee_reg' in cx and 'insee_ctcd' in cx else ''
    def parent_of(cc, r):
        p_ = parent_of_(cc, r)
        if corse_council and p_ == CORSE_AREA:
            if r['entity_id'].startswith('fr-cog:com:'): st['corse_commune_parent_to_council'] += 1; return corse_council
            st[f'corse_area_parent_kept|{r["subtype"]}'] += 1
        return p_
    def parent_of_(cc, r):
        p, hops = r['parent_id'], []
        while p in feed_only: hops.append(feed_only[p]['subtype']); p = feed_only[p]['parent_id']
        if hops: st['reparented_past_feed_only|' + hops[0]] += 1
        if r['entity_id'] in gpre_reg:
            gaps.append({'gap': 'govbot_mapping_overridden', 'key': r['entity_id'], 'detail': f"région council: bot parent {p} -> {gpre_reg[r['entity_id']]} (the area; ruling Oct 18)"}); return gpre_reg[r['entity_id']]
        if p in gpre_county:
            gaps.append({'gap': 'govbot_mapping_overridden', 'key': r['entity_id'], 'detail': f'commune: bot parent {p} -> {gpre_county[p]} (département council; {p} stays the area)'}); return gpre_county[p]
        if (is_feed_id(p) and p not in f2e) or not p:   # terminated row whose parent is outside the table or has no entity
            if cc == 'gb':   # the bot's own rule for councils with no council parent: devolved government row, else nation:gb (GSS country letter)
                st['parent_from_gss_country_letter'] += 1
                return {'E': 'nation:gb', 'W': 'subdivision:gb-wls', 'S': 'subdivision:gb-sct', 'N': 'subdivision:gb-nir'}[r['code'][0]]
            st['parent_not_resolvable_empty'] += 1; return ''
        return f2e.get(p, p)
    def carry_qid(e, q, fid):
        if not q: return
        own = qid_owner.get(q)
        if own and own != e['entity_id']:
            gaps.append({'gap': 'wikidata_qid_conflict', 'key': e['entity_id'], 'detail': f'governments-bot {fid} {q} is already on {own}; not carried'}); st['qid_conflict'] += 1
        else: e['wikidata'] = q; qid_owner[q] = e['entity_id']; st['qid_carried'] += 1
    for cc in CCS:
        for r in sorted(L['units'][cc], key=lambda r: r['is_active'] == 'N'):   # current rows first (they keep a shared QID)
            fid = r['entity_id']; base = {'feed': 'governments-bot', 'feed_id': fid, '_file': r['_file']}
            if fid in unresolved:
                fmap.append(dict(base, entity_id='', status='feed_only', note=f"code_terminated:{r['code_valid_to']};unresolved"))
                gaps.append({'gap': 'code_terminated_unresolved', 'key': fid, 'detail': f"{r['name']}: code terminated {r['code_valid_to']} with no official successor link, and a current unit of the same name exists under the same parent ({';'.join(sorted(live_by_parent_name[(r['parent_id'], nm(r['name']))]))}); code change or ended government is not decidable from the data"}); continue
            if fid in feed_only:
                fmap.append(dict(base, entity_id='', status='feed_only', note=f"{r['subtype']}:{r['gov_status']};not_minted")); st['feed_only|' + r['subtype']] += 1; continue
            if fid in code_change:
                fmap.append(dict(base, entity_id=f2e[fid], status='mapped', note=f"code_history:terminated_{r['code_valid_to']};current={code_change[fid]}")); continue
            if fid in xsame:
                fmap.append(dict(base, entity_id=f2e[fid], status='mapped', note='same_government_as_registry_row;not_minted'))
                if fid in DUP_REGISTRY and not any(w['outcome'] == 'noop' for w in WORKAROUND if w['workaround'].startswith(fid)):
                    gaps.append({'gap': 'govbot_unit_duplicates_registry', 'key': fid, 'detail': f"commune {r['name']} is the collectivity {f2e[fid]}; mapped, not minted"})
                st['mapped_existing'] += 1; continue
            k = KIND[cc][r['subtype']]; eid = f2e[fid]
            al = r.get('name_local') or (r.get('alt_name') or '')
            gs, fl = '', [x for x in r['flags'].split(';') if x and x != 'code_terminated']
            if r['gov_status'] in ('self_governing', 'intercommunal'): gs = 'government'
            elif r['gov_status'] in ('delegated', 'sub_municipal'): gs = 'dependent'
            elif r['gov_status'] == 'association':
                gs = 'unknown'; fl.append('gov_status_unknown:council_not_in_feed')
                gaps.append({'gap': 'intermunicipal_council_unknown', 'key': eid, 'detail': f"{r['subtype']}: the feed (VG250 BEZ / Destatis) gives the designation only, not whether the body has a council; gov_status left empty"})
            elif r['gov_status'] == 'parish':   # ruling on 04227d3: literal 'unknown'; the bot flag only restated it -> dropped
                assert 'council_status_unknown' in fl; gs = 'unknown'; fl.remove('council_status_unknown')
            else: raise ValueError(r['gov_status'])
            if r['subtype'] in COUNTY_POWERS: fl.append('county_powers')
            e = new_row(entity_id=eid, kind=k, name=r['name'], alias=al if al and al != r['name'] else '', gov_status=gs,
                        parent_id=parent_of(cc, r), level=LEVEL.get(k, 'local'), type=r['subtype'], feed='governments-bot',
                        code_scheme=r['code_scheme'], code=r['code'], code_valid_from=r.get('code_valid_from', ''), iso_3166_2=r['iso_3166_2'])
            if r['valid_from']:
                e['valid_from'] = r['valid_from']; e['valid_from_source'] = 'INSEE COG 2026 mouvements (DATE_EFF of a creation / re-establishment / commune nouvelle)'
                st['valid_from'] += 1
            if fid in ended:
                assert r['code_valid_to'], fid
                e['valid_to'] = r['code_valid_to']; fl.append('is_active_false:code_terminated')
            e['_flags'] = fl; e['wikidata'] = ''
            e['_src'] = [f'GOVLOCAL:{r["_file"]}'] + [f'GOVSRC:{s}' for s in r['source'].split(';') if s]
            carry_qid(e, r['wikidata_qid'], fid)
            ents[eid] = e; rows.append(e); st[f'minted|{cc}|{k}'] += 1
            fmap.append(dict(base, entity_id=eid, status='mapped', note='ended' if fid in ended else ''))   # boilerplate 'minted' dropped (ruling on 04227d3)
            if cc == 'fr' and r['alt_code']:
                if r['alt_code'] in bad_siren:
                    fmap[-1]['note'] = f"minted;siren_dropped:{r['alt_code']}(bad_join)"; st['siren_dropped'] += 1
                else: fmap.append(dict(base, feed_id=f"fr-siren:{r['alt_code']}", entity_id=eid, status='mapped', note=''))   # boilerplate 'alt_code' dropped
    for s, pair in BAD_SIREN.items():
        if s not in bad_siren: continue
        who = ' and '.join(p + ' ' + units[p][1]['name'] for p in pair)
        gaps.append({'gap': 'siren_bad_join', 'key': f'fr-siren:{s}', 'detail': f'bot alt_code SIREN {s} on two different communes ({who}); dropped from both, recorded in their feed-map notes'})
    # code_xwalk: FR région councils (mint), GP/RE département councils (mint), England, every code -> feed map
    xw = {cc: L['xwalk'][cc] for cc in CCS}
    fr_x = C.defaultdict(dict)
    for x in xw['fr']: fr_x[x['entity_id']].setdefault(x['code_scheme'], x)
    def mint_council(eid, kind, name, parent, scheme, code, area, srcfile, srcs, flags=()):
        e = new_row(entity_id=eid, kind=kind, name=name, gov_status='government', parent_id=parent, level=LEVEL.get(kind, 'local'),
                    type={'county': 'conseil_departemental', 'regional_authority': 'region'}[kind], feed='governments-bot', code_scheme=scheme, code=code)
        e['_flags'] = list(flags); e['wikidata'] = ''; e['_src'] = [f'GOVLOCAL:{srcfile}'] + [f'GOVSRC:{s}' for s in srcs]
        assert eid not in ents; ents[eid] = e; rows.append(e); st[f'minted|fr|{kind}'] += 1
        rels.append({'entity_id': eid, 'relation': 'area', 'related_entity_id': area, '_file': srcfile})
        return eid
    council = {}   # (existing entity, scheme) -> new council id for same_government codes
    for a, xs in sorted(fr_x.items()):
        if a.startswith('subdivision:fr-') and 'insee_reg' in xs:
            reg = xs['insee_reg']['code']; corse = 'insee_ctcd' in xs
            nm = xs['insee_ctcd']['note'] if corse else ents[a]['name']
            c_ = mint_council(f'regional_authority:fr-{reg}', 'regional_authority', nm, 'nation:fr', 'insee_reg', reg, a, xs['insee_reg']['_file'],
                              ['insee_cog2026'] + (['ign_adminexpress'] if 'siren' in xs else []), ['county_powers'] if corse else [])
            if not corse: ents[c_]['_src'].append('GF:foreign/subdivisions.csv')   # name = the région's name as in our subdivision row
            council[a] = c_
        if a in GPRE and a not in GPRE_ACT:   # councils are bot units now: link them to the area, mark the area
            d, g = GPRE[a]
            for u_ in (f'fr-cog:dep:{d}', f'fr-cog:reg:{g}'):
                assert units[u_][1]['parent_id'] == a, u_
                rels.append({'entity_id': f2e[u_], 'relation': 'area', 'related_entity_id': a, '_file': units[u_][1]['_file']})
            council[a] = None
        if a in GPRE_ACT:
            d, g = GPRE[a]; x = xs['insee_ctcd']
            c_ = mint_council(f'county:fr-{d}', 'county', x['note'], a, 'insee_ctcd', x['code'], a, x['_file'], ['insee_cog2026'])
            council[a] = c_
            rels.append({'entity_id': f'regional_authority:fr-{g}', 'relation': 'area', 'related_entity_id': a, '_file': x['_file']})
    for cc in CCS:
        for x in xw[cc]:
            fid = f"{XW_PREFIX[x['code_scheme']]}:{x['code']}"; t = f2e.get(x['entity_id'], x['entity_id']); rel = x['relation']; note = rel
            if x['code_scheme'] != 'iso_3166_2' and council.get(t) and rel == 'same_government':
                if t in GPRE_ACT: gaps.append({'gap': 'govbot_mapping_overridden', 'key': fid, 'detail': f"code_xwalk {x['code_scheme']} {x['code']}: bot {t} (same_government) -> {council[t]}; {t} stays the area"})
                t = council[t]; note = rel + ';council_split_from_area'
            if x['entity_id'] == 'subdivision:gb-eng' and rel != 'area_only':
                gaps.append({'gap': 'govbot_xwalk_relation_overridden', 'key': fid, 'detail': f'bot code_xwalk says {rel}; England has no devolved government (bot note), so area_only like its GSS row E92000001'}); note = 'area_only;bot_said_' + rel
            if t in PENDING: note += ';ctu_pending_ruling'
            assert t in ents, (fid, t)
            fmap.append({'feed': 'governments-bot', 'feed_id': fid, 'entity_id': t, 'status': 'mapped', 'note': 'code_xwalk:' + note, '_file': x['_file']})
    # predecessor relations (method sourced): from every row's predecessor_id (row -> each predecessor) and successor_id
    # (each successor -> row), resolved through f2e (a code change resolves to its current entity; self links dropped)
    # only an ENDED (minted, is_active N) entity can be a predecessor: a link between two current governments in the
    # official tables is a boundary transfer (e.g. Gateshead -> Northumberland 2013), not a succession -> not a relation
    ended_e = {f2e[f] for f in ended}
    pred, live_link = {}, C.defaultdict(set)
    for fid, (cc, r) in units.items():
        a = f2e.get(fid)
        for p_ in [x for x in r['predecessor_id'].split(';') if x]:
            b_ = f2e.get(p_)
            if a and b_ and a != b_ and b_ in ended_e: pred.setdefault((a, b_), (r['_file'], ''))
            elif a and b_ and a != b_ and cc == 'fr' and r['valid_from'] and r['is_active'] != 'N':   # FR creation / re-establishment
                pred.setdefault((a, b_), (r['_file'], ';split_from_current')); st['predecessor_split_from_current'] += 1   # split off a commune that still exists
            elif not (a and b_): st['predecessor_link_unresolved'] += 1
            elif a != b_: st['predecessor_link_not_ended_skipped'] += 1; live_link[a].add(b_)
        for s_ in [x for x in r['successor_id'].split(';') if x]:
            b_ = f2e.get(s_)
            if a and b_ and a != b_ and a in ended_e: pred.setdefault((b_, a), (r['_file'], ''))
            elif not (a and b_): st['successor_link_unresolved'] += 1
            elif a != b_: st['successor_link_not_ended_skipped'] += 1; live_link[b_].add(a)
    SRCN = {'gb': 'ons_chd', 'fr': 'insee_cog_mouvements', 'de': 'bkg_vg250_editions'}
    for (a, b_), (f_, t_) in sorted(pred.items()):
        rels.append({'entity_id': a, 'relation': 'predecessor', 'related_entity_id': b_, 'note': SRCN[f_[:2]] + t_, '_file': f_})
    # a sourced valid_from with no predecessor relation: the feed carries the whole official history for its window
    # (FR COG mouvements), so -> predecessor_none_in_source. Nothing is left predecessor_pending; DE rows carry no
    # valid_from (the feed has no DE history before 2026), so no DE row is flagged. (predecessor_is_current is a guard:
    # a live->live link on a row that got no relation; none expected.)
    has_pred = {a for a, _ in pred}
    for e in rows:
        if not e.get('valid_from') or e['entity_id'] in has_pred:
            if e.get('valid_from'): st['valid_from_with_predecessor'] += 1
            continue
        if L.get('history_cutoff') and e['valid_from'] <= L['history_cutoff']:   # its predecessors ended before the cutoff: pruned upstream, links cleared -> no flag
            st['valid_from_at_cutoff_links_pruned'] += 1; continue
        cur = sorted(live_link.get(e['entity_id'], ()))
        if cur: e['_flags'].append('predecessor_is_current:' + '|'.join(cur)); st['predecessor_is_current'] += 1
        else: e['_flags'].append('predecessor_none_in_source'); st['predecessor_none_in_source'] += 1
    st['relations_predecessor'] = len(pred)
    # member_of (ruling on 04227d3): the bot's member_of column (UK combined authority, FR EPCI / EPT, DE Amt /
    # Verbandsgemeinde ...) -> relation member_of, method sourced; minted rows only, resolved through f2e
    mem = {}
    for fid, (cc, r) in units.items():
        a = f2e.get(fid)
        if not a or fid in code_change or fid in xsame: continue
        for m_ in [x for x in (r.get('member_of') or '').split(';') if x]:
            b_ = f2e.get(m_)
            if b_ and b_ != a: mem.setdefault((a, b_), r['_file'])
            else: st[f'member_of_unresolved|{cc}'] += 1
    for (a, b_), f_ in sorted(mem.items()):
        rels.append({'entity_id': a, 'relation': 'member_of', 'related_entity_id': b_, 'note': '', '_file': f_}); st[f'relations_member_of|{f_[:2]}'] += 1
    # dedupe feed ids (a code can be both a unit's alt_code and a crosswalk row): same target required, first kept
    # a code the bot crosswalks both same_government (to the council) and area_only (to the area it governs; GP/RE since
    # 310086f): the council row is kept, the area_only row dropped (the council->area link is the `area` relation)
    gov_ids = {m['feed_id'] for m in fmap if 'area_only' not in m['note']}
    seen, seen_note, out = {}, {}, []
    for m in fmap:
        if m['note'].startswith('code_xwalk:area_only') and m['feed_id'] in gov_ids: st['feed_id_area_only_shadowed'] += 1; continue
        k = m['feed_id']
        if k in seen and seen[k] == m['entity_id']: st['feed_rows_deduped'] += 1; continue
        if k in seen:   # one area code governed in parts by two bodies (insee_dep:69: Métropole de Lyon + Rhône council): both kept
            assert 'governs_part' in m['note'] + seen_note[k], (k, seen[k], m['entity_id']); st['feed_id_two_targets'] += 1
        seen.setdefault(k, m['entity_id']); seen_note.setdefault(k, m['note']); out.append(m)
    # feed-map key (feed, feed_id, role) + is_primary (ruling on 04227d3): a feed id with one target has role '' and is
    # primary; with several targets each gets the role of its target body, and the primary is the one the bot crosswalks
    # same_government (the others govern part of it: governs_part)
    ROLE = {'metropole_de_lyon': 'territorial_collectivity', 'conseil_departemental': 'departmental_council'}
    grp = C.defaultdict(list)
    for m in out: grp[m['feed_id']].append(m)
    for k, ms in grp.items():
        if len(ms) == 1: ms[0]['role'], ms[0]['is_primary'] = '', '1'; continue
        for m in ms:
            m['role'] = ROLE[ents[m['entity_id']]['type']]; m['is_primary'] = '1' if m['note'].endswith(':same_government') else '0'
        assert sum(m['is_primary'] == '1' for m in ms) == 1 and len({m['role'] for m in ms}) == len(ms), k
        st['feed_id_roles_assigned'] += len(ms)
    # area rows: subdivision:gb-eng, the FR région subdivisions and territory:gp / territory:re are areas only now
    areas = ['subdivision:gb-eng'] + sorted(a for a in council)
    for a in areas:
        e = ents[a]; e['gov_status'] = 'area_only'; e['_flags'] = [f for f in e['_flags'] if not f.startswith('gov_status_unknown:')]; st['set_area_only'] += 1
    for e in rows: assert e['parent_id'] in ents or (not e['parent_id'] and e.get('valid_to')), (e['entity_id'], e['parent_id'])
    st['feed_rows'] = len(out); st['relations_area'] = sum(1 for x in rels if x['relation'] == 'area')
    return {'rows': rows, 'fmap': out, 'rels': rels, 'gaps': gaps, 'stats': dict(sorted(st.items())), 'areas': areas, 'workarounds': WORKAROUND, 'pruned_already_minted': pruned_in_ents}
