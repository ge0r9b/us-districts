"""Seating Charts bodies -> institution entities (body_entity.csv), courts minted from bodies.csv.

Input: the Seating Charts bot's committed files at a pinned commit (repo ge0r9b/us-districts, branch data/seating):
data-v3/seating/bodies.csv (key, st, kind L/C/M, office, name, unit_type, geoid, entity), build_meta.json (excluded /
dropped courts), city_bodies.csv (read-only cross-check of geoid/entity for the city bodies). Read with `git show`.
The join is on bodies.csv `key` only (integer `b` ids shift between builds and are never stored).

Rules (Full Stack, Oct 18):
  L  US us_senate -> us-senate; US us_house -> us-house; <st> state_senate|state_legislature (sldu) -> chamber:<st>-upper
     (type upper_chamber, unicameral for NE); <st> state_house (sldl) -> chamber:<st>-lower. Names never compared. role chamber.
  C  each court body is minted as entity court:<st>-<slug> (kind court), slug from `office` (COURT_SLUG), name = bodies.csv
     name verbatim; parent state:<fips>. role court. Courts in build_meta excluded_courts / dropped_courts are not minted.
  M  city_council -> role council (role board when the key ends in -board-of-supervisors), mayor -> role mayor.
     The file's `entity` is a claim, accepted only when verified here: it exists, its state is `st`, and the body's place
     `geoid` is a place GEOID of that entity in entity_geoid_xwalk (or of its parent_id, for DC's council under state:11);
     city_bodies.csv must list the geoid. Consolidated governments: when the verified entity is the area_only city side
     of a consolidated_with pair, the body goes to the pair's county entity, which holds the government (CoG id,
     gov_status government) -> match consolidated_government, reported in `judged`. Council and mayor share one entity.
body_key is unique (primary key of body_entity.csv); an entity may carry several bodies with different roles.
"""
import csv, hashlib, io, json, subprocess

SEAT_DIR = 'data-v3/seating'
GAPCOLS = ['body_key', 'st', 'kind', 'office', 'name', 'reason', 'source_id']
LINKCOLS = ['body_key', 'entity_id', 'role', 'st', 'kind', 'office', 'match', 'source_record_id', 'source_id']
COURT_SLUG = {'state_supreme_court': ('supreme', 'supreme_court'),
              'state_court_criminal_appeals': ('criminal-appeals', 'court_of_criminal_appeals')}
ROLE_M = {'city_council': 'council', 'mayor': 'mayor'}
BOARD_SUFFIX = '-board-of-supervisors'

def load(repo, ref):
    def show(p):
        return subprocess.run(['git', '-C', repo, 'show', f'{ref}:{SEAT_DIR}/{p}'], capture_output=True, check=True).stdout
    commit = subprocess.run(['git', '-C', repo, 'rev-parse', ref + '^{commit}'], capture_output=True, text=True, check=True).stdout.strip()
    out = {'commit': commit, 'files': {}}
    for f in ('bodies.csv', 'build_meta.json', 'city_bodies.csv'):
        raw = show(f); out['files'][f] = {'path': f'{SEAT_DIR}/{f}', 'sha256': hashlib.sha256(raw).hexdigest(), 'raw': raw}
    out['bodies'] = list(csv.DictReader(io.StringIO(out['files']['bodies.csv']['raw'].decode('utf-8'))))
    out['city'] = list(csv.DictReader(io.StringIO(out['files']['city_bodies.csv']['raw'].decode('utf-8'))))
    out['meta'] = json.loads(out['files']['build_meta.json']['raw'])
    keys = [b['key'] for b in out['bodies']]
    assert len(keys) == len(set(keys)), 'bodies.csv key not unique'
    return out

def courts(bodies):
    """(entity_id, type, st, name, key) for every court body with a known office; others are left to match() as gaps."""
    out = []
    for b in bodies:
        if b['kind'] == 'C' and b['office'] in COURT_SLUG:
            slug, typ = COURT_SLUG[b['office']]
            out.append((f"court:{b['st'].lower()}-{slug}", typ, b['st'].upper(), b['name'], b['key']))
    ids = [c[0] for c in out]; assert len(ids) == len(set(ids)), 'court id collision'
    return out

def not_in_seating(meta):
    """court codes the Seating Charts build excluded or dropped (build_meta.json): (code, list name)."""
    return [(c, k) for k in ('excluded_courts', 'dropped_courts') for c in sorted(meta.get(k, []))]

def slot(b):
    st, off = b['st'].upper(), b['office']
    if st == 'US' and off == 'us_senate': return 'us-senate', {'upper_chamber'}
    if st == 'US' and off == 'us_house': return 'us-house', {'lower_chamber'}
    if off in ('state_senate', 'state_legislature') and b['unit_type'] in ('sldu', ''): return f'chamber:{st.lower()}-upper', {'upper_chamber', 'unicameral'}
    if off == 'state_house' and b['unit_type'] in ('sldl', ''): return f'chamber:{st.lower()}-lower', {'lower_chamber'}
    return None, None

def match(S, ents, abbr_of_fips, xw_places, relations):
    """xw_places: entity_id -> set of place GEOIDs in entity_geoid_xwalk; relations: entity_relations rows."""
    links, gaps, judged = [], [], []
    city = {}
    for c in S['city']: city.setdefault(c['geoid'], set()).add(c['entity'])
    cons = {}
    for r in relations:
        if r['relation'] == 'consolidated_with': cons[r['related_entity_id']] = r['entity_id']; cons[r['entity_id']] = r['related_entity_id']
    court_ids = {c[4]: c[0] for c in courts(S['bodies'])}
    def gap(b, reason): gaps.append({'body_key': b['key'], 'st': b['st'], 'kind': b['kind'], 'office': b['office'], 'name': b['name'], 'reason': reason})
    def st_of(e): return 'US' if e['level'] == 'federal' else abbr_of_fips.get(e['state_fips'], '').upper()
    for b in S['bodies']:
        k = b['kind']
        if k == 'L':
            eid, types = slot(b)
            if eid is None: gap(b, f"no_structural_slot:office_{b['office']}"); continue
            e = ents.get(eid)
            if e is None: gap(b, f'no_entity:{eid}_not_in_registry'); continue
            assert st_of(e) == b['st'].upper() and e['type'] in types, ('structural check failed', b['key'], eid)
            exp = {'us-senate': 'us-senate', 'us-house': 'us-house'}.get(eid) or f"us-{b['st'].lower()}-{'senate' if eid.endswith('-upper') else 'house'}"
            if b['key'] != exp: judged.append(f"{b['key']} -> {eid}: key is not the {exp} pattern; matched on st={b['st']} + office={b['office']} (entity type {e['type']})")
            links.append((b, eid, 'chamber', 'structural'))
        elif k == 'C':
            eid = court_ids.get(b['key'])
            if eid is None or eid not in ents: gap(b, f"no_entity:court_office_{b['office']}_has_no_slug"); continue
            links.append((b, eid, 'court', 'minted_from_body'))
        elif k == 'M':
            role = ROLE_M.get(b['office'])
            if role is None: gap(b, f"no_role_for_office_{b['office']}"); continue
            if role == 'council' and b['key'].endswith(BOARD_SUFFIX): role = 'board'
            eid, g = b.get('entity', ''), b.get('geoid', '')
            e = ents.get(eid)
            if not eid or not g: gap(b, 'entity_or_geoid_empty_in_bodies_csv'); continue
            if e is None: gap(b, f'entity_not_in_registry:{eid}'); continue
            if st_of(e) != b['st'].upper(): gap(b, f'entity_state_mismatch:{eid}_is_{st_of(e)}_body_st_{b["st"]}'); continue
            via = eid if g in xw_places.get(eid, ()) else (e['parent_id'] if g in xw_places.get(e['parent_id'], ()) else '')
            if not via: gap(b, f'entity_geoid_mismatch:place_{g}_not_in_xwalk_of_{eid}_or_its_parent'); continue
            if e['kind'] not in ('municipality', 'state', 'dc_council'): gap(b, f"entity_kind_mismatch:{eid}_is_{e['kind']}"); continue
            if g not in city: gap(b, f'city_bodies_crosscheck_failed:geoid_{g}_not_listed'); continue
            m = 'file_entity_verified' if via == eid else f'file_entity_verified_via_parent:{via}'
            if e['kind'] == 'municipality' and e['gov_status'] == 'area_only' and eid in cons and ents.get(cons[eid], {}).get('gov_status') == 'government':
                judged.append(f"{b['key']}: file entity {eid} is the area_only balance place of a consolidated_with pair; mapped to {cons[eid]} (holds the consolidated government: CoG id, gov_status government)")
                eid, m = cons[eid], 'consolidated_government'
            if role == 'board': judged.append(f"{b['key']} -> {eid}: role board (key ends in {BOARD_SUFFIX}; office {b['office']})")
            links.append((b, eid, role, m))
        else:
            gap(b, f'unknown_body_kind_{k}')
    rows = [{'body_key': b['key'], 'entity_id': eid, 'role': role, 'st': b['st'], 'kind': b['kind'], 'office': b['office'], 'match': m,
             'source_record_id': b['key'], '_m': b['kind'] == 'M'} for b, eid, role, m in links]
    keys = [r['body_key'] for r in rows]; assert len(keys) == len(set(keys)), 'body_key not unique'
    by = {}
    for r in rows: by.setdefault(f"{r['kind']}|{r['role']}", 0); by[f"{r['kind']}|{r['role']}"] += 1
    kinds = sorted({b['kind'] for b in S['bodies']})
    stats = {'bodies': len(S['bodies']),
             'by_body_kind': {k: {'mapped': sum(1 for r in rows if r['kind'] == k), 'unmapped': sum(1 for g in gaps if g['kind'] == k)} for k in kinds},
             'mapped_by_kind_role': dict(sorted(by.items())), 'gaps_by_reason': {}, 'judged': judged,
             'entities_with_bodies': len({r['entity_id'] for r in rows})}
    for g in gaps:
        rk = g['reason'].split(':')[0]; stats['gaps_by_reason'][rk] = stats['gaps_by_reason'].get(rk, 0) + 1
    return sorted(rows, key=lambda r: r['body_key']), sorted(gaps, key=lambda g: g['body_key']), stats
