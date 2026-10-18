"""Governments bot feed (data-v3/institutions/governments at a pinned commit; read only) -> data-v3/inst.

Maps EVERY Governments id to its registry entity (entity_feed_map.csv), never renaming either side:
  1. state:<FIPS> / territory:<FIPS> -> the same registry id; the bot's older state:60/66/69/72/78 keys -> territory:<FIPS> (logged)
  2. school_district rows: nces_leaid -> school:<leaid>
  3. GEOID (geoid_layer + geoid, TIGER 2024) -> the registry entity holding that GEOID (entity_geoid_xwalk)
  4. CoG 2022 id (cog_id) -> the registry entity carrying that cog_pid6
  (3 and 4 must agree when both exist; a disagreement is a conflict row, nothing is changed)
Unmapped ids (special districts, federal agencies, tribes, units with no GEOID/CoG link) stay feed-only; v3's loader turns
them into government_other (DATA_LOADING §15.1). Carried onto mapped entities: wikidata_qid (only when every bot row of the
entity agrees), ceased units (valid_to + flag is_active_false), new units (valid_from + flag not_in_cog2022). Seals/flags ->
entity_images.csv (institution-only attributes; license, usage_basis and source_url kept so fair-use rows can be filtered).
"""
import csv, io, subprocess, collections as C
P = 'data-v3/institutions/governments/'
LAYER = {'place': 'place', 'cousub': 'cousub', 'counties': 'county', 'unsd': 'unsd', 'elsd': 'elsd', 'scsd': 'scsd', 'states': 'state'}
US_TERR = {'60', '66', '69', '72', '78'}

def _show(R, sha, f):
    return subprocess.run(['git', '-C', R, 'show', f'{sha}:{P}{f}'], capture_output=True, check=True).stdout.decode('utf-8')
def _csv(R, sha, f): return list(csv.DictReader(io.StringIO(_show(R, sha, f))))

def load(R, sha):
    files = subprocess.run(['git', '-C', R, 'ls-tree', '--name-only', sha, P + 'local/'], capture_output=True, text=True, check=True).stdout.split()
    rows = []
    for f in ['states.csv'] + [x[len(P):] for x in sorted(files)] + ['federal_agencies.csv', 'tribes.csv']:
        for r in _csv(R, sha, f): r['_file'] = f; rows.append(r)
    # the foreign layer (foreign/*.csv and the images of foreign ids, territory:74 included) is read by tools/inst_foreign.py
    import inst_foreign
    dom = lambda i: not (inst_foreign.is_foreign_id(i) or i == 'territory:74')
    return {'rows': rows, 'registry': [x for x in _csv(R, sha, 'id_registry.csv') if dom(x['entity_id'])], 'changes': _csv(R, sha, 'changes_since_cog2022.csv'),
            'images': [x for x in _csv(R, sha, 'images.csv') if dom(x['entity_id'])], 'images_gaps': _csv(R, sha, 'images_gaps.csv'), 'sources': _csv(R, sha, 'sources.csv')}

def integrate(G, ents, gidx, consolidated=None):
    consolidated = consolidated or {}   # cog_pid6 -> county entity kept separate from its consolidated city (CoG code not a TIGER place)
    rels = []
    """ents: {entity_id: row dict (mutable)}; gidx: {(layer, geoid, '2024'): entity_id}. Returns (feed_map, images, gaps, stats)."""
    by_pid = C.defaultdict(set)
    for eid, e in ents.items():
        for p in (e.get('cog_pid6') or '').split(';'):
            if p: by_pid[p].add(eid)
    fmap, gaps, st = [], [], C.Counter()
    seen = set()
    for r in G['rows']:
        fid = r['entity_id']; assert fid not in seen, fid; seen.add(fid)
        tgt, how, note = '', '', ''
        pre, _, code = fid.partition(':')
        if pre in ('state', 'territory') and code.isdigit():
            if code in US_TERR:
                tgt = f'territory:{code}'; how = 'territory_fips'
                if pre == 'state': note = 'territory_rekey'; gaps.append({'gap': 'govbot_territory_key_differs', 'key': fid, 'detail': 'bot key state:%s -> registry territory:%s (agreed SCHEMA id)' % (code, code)})
            elif f'state:{code}' in ents: tgt = f'state:{code}'; how = 'state_fips'
        else:
            g_t = ''
            if r['type'] == 'school_district' and r.get('nces_leaid') and f"school:{r['nces_leaid']}" in ents: g_t = f"school:{r['nces_leaid']}"; how_g = 'nces_leaid'
            elif r.get('geoid') and LAYER.get(r.get('geoid_layer')):
                g_t = gidx.get((LAYER[r['geoid_layer']], r['geoid'], '2024'), ''); how_g = 'geoid'
            c_t = sorted(by_pid.get(r.get('cog_id') or '', ()))
            if g_t and c_t and g_t not in c_t and consolidated.get(r.get('cog_id')) == c_t[0] and len(c_t) == 1:
                # consolidated city-county kept as two entities: CoG id -> the county entity; the place GEOID stays on the city
                tgt, how, note = c_t[0], 'cog_pid6', 'consolidated'
                rels.append({'entity_id': c_t[0], 'relation': 'consolidated_with', 'related_entity_id': g_t, 'feed_id': fid})
            elif g_t and c_t and g_t not in c_t:
                gaps.append({'gap': 'govbot_mapping_conflict', 'key': fid, 'detail': f"{how_g} -> {g_t}; cog_id {r['cog_id']} -> {';'.join(c_t)}; left unmapped"}); note = 'conflict(see entity_gaps)'
            elif g_t: tgt, how = g_t, how_g + ('+cog_pid6' if c_t else '')
            elif len(c_t) == 1: tgt, how = c_t[0], 'cog_pid6'
            elif len(c_t) > 1: gaps.append({'gap': 'govbot_mapping_ambiguous', 'key': fid, 'detail': 'cog_id %s on %s' % (r['cog_id'], ';'.join(c_t))}); note = 'ambiguous(see entity_gaps)'
        if fid in ents and tgt != fid:   # the bot uses one of OUR ids for something else: report, rename nothing
            gaps.append({'gap': 'govbot_frozen_id_conflict', 'key': fid, 'detail': f'registry has {fid}; bot row maps to {tgt or "nothing"}'}); st['frozen_id_conflicts'] += 1
        if not tgt and not note:
            note = {'special_district': 'feed_only:special_district', 'federal_agency': 'feed_only:federal_agency',
                    'tribe': 'feed_only:tribe'}.get(r['type'], 'no_geoid_or_cog_link')
        st[('mapped' if tgt else 'unmapped') + '|' + r['type']] += 1
        status = 'mapped' if tgt else ('feed_only' if note.startswith('feed_only') else 'unmapped')
        fmap.append({'feed': 'governments-bot', 'feed_id': fid, 'feed_entity_id': fid, 'feed_type': r['type'], 'entity_id': tgt, 'status': status,
                     'note': ';'.join(x for x in [note, f'match={how}' if how else '', f"type={r['type']}"] if x), '_r': r})
    # registry ids that the feed files don't carry
    reg_ids = {x['entity_id'] for x in G['registry']}
    for x in sorted(reg_ids - seen): gaps.append({'gap': 'govbot_registry_id_not_in_files', 'key': x, 'detail': 'id_registry.csv only'})
    st['feed_ids'] = len(fmap); st['registry_ids'] = len(reg_ids)
    # per registry entity: carried attributes
    per = C.defaultdict(list)
    for m in fmap:
        if m['entity_id']: per[m['entity_id']].append(m['_r'])
    for eid, rs in per.items():
        e = ents[eid]
        q = sorted({x['wikidata_qid'] for x in rs if x.get('wikidata_qid')})
        if len(q) == 1:
            if e.get('wikidata') and e['wikidata'] != q[0]:
                gaps.append({'gap': 'wikidata_qid_conflict', 'key': eid, 'detail': f"registry {e['wikidata']} vs governments-bot {q[0]}; kept registry value"}); st['qid_conflict'] += 1
            elif not e.get('wikidata'): e['wikidata'] = q[0]; st['qid_carried'] += 1; e['_gov'] = True
        elif len(q) > 1:
            gaps.append({'gap': 'wikidata_qid_conflict', 'key': eid, 'detail': 'governments-bot rows disagree: ' + ';'.join(f"{x['entity_id']}={x['wikidata_qid']}" for x in rs if x.get('wikidata_qid'))}); st['qid_conflict'] += 1
        ceased = [x for x in rs if x.get('is_active') == 'false' or 'ceased' in x.get('flags', '').split(';')]
        if ceased:
            if len(ceased) == len(rs):
                vt = sorted({x['valid_to'] for x in ceased if x.get('valid_to')})
                if len(vt) == 1: e['valid_to'] = vt[0]
                elif len(vt) > 1: gaps.append({'gap': 'govbot_ceased_dates_disagree', 'key': eid, 'detail': ';'.join(vt)})
                e['_flags'].append('is_active_false:governments_bot_' + ','.join(x['entity_id'] for x in ceased)); st['ceased_applied'] += 1; e['_gov'] = True
            else:
                gaps.append({'gap': 'govbot_ceased_partial', 'key': eid, 'detail': 'ceased ' + ','.join(x['entity_id'] for x in ceased) + ' of ' + ','.join(x['entity_id'] for x in rs) + '; entity kept active'}); st['ceased_partial'] += 1
        new = [x for x in rs if 'not_in_cog2022' in x.get('flags', '').split(';')]
        if new:
            vf = sorted({x['valid_from'] for x in new if x.get('valid_from')})
            if len(vf) == 1 and not e.get('valid_from'): e['valid_from'] = vf[0]
            if 'not_in_cog2022' not in e['_flags']: e['_flags'].append('not_in_cog2022')
            st['new_units_applied'] += 1; e['_gov'] = True
    for m in fmap:   # bot rows flagged ceased / new that found no registry entity
        r = m['_r']; fl = r.get('flags', '').split(';')
        if not m['entity_id'] and ('ceased' in fl or r.get('is_active') == 'false'): st['ceased_unmapped'] += 1
        if not m['entity_id'] and 'not_in_cog2022' in fl:
            st['new_units_unmapped'] += 1; gaps.append({'gap': 'govbot_new_unit_not_in_registry', 'key': m['feed_entity_id'], 'detail': f"{r['name']} ({r['state']}); valid_from {r.get('valid_from', '')}; geoid {r.get('geoid', '') or 'none'}"})
    # images
    f2e = {m['feed_entity_id']: m['entity_id'] for m in fmap}
    imgs = []
    for x in G['images']:
        fid = x['entity_id']; tgt = f2e.get(fid, '')
        if not tgt and fid in ents: tgt = fid   # nation:us and other ids the registry shares verbatim
        if not tgt:
            gaps.append({'gap': 'image_entity_unmapped', 'key': fid, 'detail': x['image_kind'] + ' ' + x['commons_file']}); st['images_unmapped'] += 1
        su = x.get('source_url') or ''
        sid = ['fr_agencies'] if 'federalregister.gov' in su else ['wikidata_images', 'enwiki_api' if 'wikipedia.org' in su else 'commons_api']
        assert x['image_kind'] in ('seal', 'flag', 'logo'), x['image_kind']
        fu = x['license'] == 'fair-use'
        if fu != bool(x['usage_basis']): gaps.append({'gap': 'image_fair_use_inconsistent', 'key': fid, 'detail': f"license {x['license']}; usage_basis {'set' if x['usage_basis'] else 'empty'}"})
        imgs.append({'entity_id': tgt, 'feed_id': fid, 'feed_entity_id': fid, 'role': x['image_kind'], 'file': x['commons_file'], 'image_kind': x['image_kind'], 'commons_file': x['commons_file'], 'commons_url': x['commons_url'],
                     'license': x['license'], 'usage_basis': x['usage_basis'], 'attribution': x['attribution'], 'source_url': x['source_url'],
                     'wikidata_qid': x['wikidata_qid'], 'retrieved_at': x['retrieved_at'], 'fair_use': 'yes' if x['license'] == 'fair-use' else 'no', '_sid': sid})
    st['images'] = len(imgs); st['images_fair_use'] = sum(1 for i in imgs if i['fair_use'] == 'yes')
    st['consolidated_relations'] = len(rels)
    return fmap, imgs, gaps, st, rels
