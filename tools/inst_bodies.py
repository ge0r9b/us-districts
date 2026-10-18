"""body_key: link institution entities to the Seating Charts bot's bodies.csv (key column), by structure only.

bodies.csv (Seating Charts bot, /workspace/seating/v3data/bodies.csv; not committed by this lane) columns used:
key, st, kind (L legislature, C court), office, name, unit_type. A body matches an entity only when st + office name
one structural slot that exists in the registry:
  US us_senate          -> entity us-senate (chamber, federal, upper_chamber)
  US us_house           -> entity us-house  (chamber, federal, lower_chamber)
  XX state_senate/sldu  -> chamber:<xx>-upper (type upper_chamber, or unicameral for NE)
  XX state_house/sldl   -> chamber:<xx>-lower (type lower_chamber)
  DC council            -> chamber:dc-council (kind dc_council), if bodies.csv has such a row
Names are never compared (Assembly / House of Delegates / General Assembly all are office state_house). The key is
checked against the expected pattern us-<xx>-senate / us-<xx>-house; a mismatch is still matched when st + office
are unambiguous and is reported in `judged`. Courts (kind C) have no entity kind yet -> gap, no entity minted.
"""
import csv, hashlib

GAPCOLS = ['body_key', 'st', 'kind', 'office', 'name', 'reason', 'source_id']

def load(path):
    raw = open(path, 'rb').read()
    rows = list(csv.DictReader(raw.decode('utf-8').splitlines()))
    keys = [r['key'] for r in rows]
    assert len(keys) == len(set(keys)), 'bodies.csv key not unique'
    return rows, hashlib.sha256(raw).hexdigest()

def slot(b):
    """(expected entity_id, accepted entity types, expected key) for a body, or None when no entity kind exists."""
    st, off = b['st'].upper(), b['office']
    if st == 'US' and off == 'us_senate': return 'us-senate', {'upper_chamber'}, 'us-senate'
    if st == 'US' and off == 'us_house': return 'us-house', {'lower_chamber'}, 'us-house'
    if b['kind'] == 'L' and off == 'state_senate' and b['unit_type'] in ('sldu', ''):
        return f'chamber:{st.lower()}-upper', {'upper_chamber', 'unicameral'}, f'us-{st.lower()}-senate'
    if b['kind'] == 'L' and off == 'state_house' and b['unit_type'] in ('sldl', ''):
        return f'chamber:{st.lower()}-lower', {'lower_chamber'}, f'us-{st.lower()}-house'
    if st == 'DC' and 'council' in off: return 'chamber:dc-council', {'council'}, None
    return None

def match(bodies, ents, abbr_of_fips):
    """ents: entity_id -> row. Returns (body_key by entity_id, gap rows, judged notes, stats)."""
    out, gaps, judged = {}, [], []
    st = {'L': [0, 0], 'C': [0, 0]}
    for b in bodies:
        st.setdefault(b['kind'], [0, 0])
        s = slot(b)
        if s is None:
            reason = ('no_entity:court_kind_not_approved (kind C, office %s; no court entities minted, see ENTITIES_SCHEMA.md court proposal)' % b['office']
                      if b['kind'] == 'C' else 'no_entity:no_structural_slot_for_office_%s' % b['office'])
            gaps.append({'body_key': b['key'], 'st': b['st'], 'kind': b['kind'], 'office': b['office'], 'name': b['name'], 'reason': reason})
            st[b['kind']][1] += 1; continue
        eid, types, expkey = s
        e = ents.get(eid)
        if e is None:
            gaps.append({'body_key': b['key'], 'st': b['st'], 'kind': b['kind'], 'office': b['office'], 'name': b['name'],
                         'reason': f'no_entity:{eid}_not_in_registry (not minted here)'})
            st[b['kind']][1] += 1; continue
        ok_st = (b['st'].upper() == 'US' and e['level'] == 'federal') or abbr_of_fips.get(e['state_fips'], '').upper() == b['st'].upper()
        assert ok_st and e['type'] in types, ('structural check failed', b['key'], eid, e['state_fips'], e['type'])
        assert eid not in out, ('two bodies for one entity', eid, out.get(eid), b['key'])
        out[eid] = b['key']; st[b['kind']][0] += 1
        if expkey and b['key'] != expkey:
            judged.append(f"{b['key']} -> {eid}: key is not the {expkey} pattern; matched on st={b['st']} + office={b['office']} (entity type {e['type']}, {e['name']})")
    vals = list(out.values()); assert len(vals) == len(set(vals)), 'body_key not unique'
    stats = {'bodies': len(bodies), 'by_body_kind': {k: {'mapped': v[0], 'unmapped': v[1]} for k, v in sorted(st.items())},
             'entities_with_body_key': len(out), 'judged': judged}
    return out, gaps, judged, stats
