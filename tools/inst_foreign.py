"""Governments bot foreign layer -> data-v3/inst (read only; data-v3/institutions/governments/foreign/ + images.csv at a pinned commit).

nations.csv / dependencies.csv / subdivisions.csv (ids nation:<iso2>, territory:<iso2>, territory:74, province:ca-xx /
territory:ca-xx, subdivision:<iso 3166-2 lowercased>) and iso_domestic_crosswalk.csv (ISO code -> existing domestic row).
Rules (user / Full Stack, Oct 18):
  * a feed id that is already a registry id is mapped (never renamed); parent and QID disagreements are logged, ours kept;
  * rows flagged review_status (Taiwan, Western Sahara) are feed_only: not minted, not mapped, their gaps stay open; their
    subdivisions are feed_only too (parent pending the user);
  * every other row is minted with its feed id (frozen): kind nation / territory / subdivision, parent from the row,
    a `parent` relation for each minted territory and subdivision; no units, no xwalk, no boundary_set;
  * crosswalk codes are feed-map rows (feed_id iso3166:<code>) pointing at the existing entity; nothing is minted for them;
  * wikidata: carried only when no other registry entity holds the QID (else wikidata_qid_conflict, registry kept);
  * constituent_qid (nations: the constituent country item under the sovereign-state item, e.g. nation:dk Q35), valid_from
    / valid_to / valid_from_source (valid_from = earliest sourced inception, Wikidata P571 with a P248/P854 reference; NOT
    the date the current government began, e.g. Barbados 1623 is a settlement date) are carried as given; on an existing
    row a non-empty registry value that differs is kept and logged (govbot_foreign_attr_differs); a constituent_qid
    that is some entity's wikidata is logged (wikidata_qid_conflict) and not carried;
  * images: only rows of foreign ids (+ territory:74); domestic images stay on the domestic feed ref.
"""
import csv, hashlib, io, subprocess, collections as C
P = 'data-v3/institutions/governments/'
FILES = ['foreign/nations.csv', 'foreign/dependencies.csv', 'foreign/subdivisions.csv', 'foreign/iso_domestic_crosswalk.csv', 'images.csv']
US_FIPS_TERR = {'territory:60', 'territory:66', 'territory:69', 'territory:72', 'territory:78'}

def _raw(R, sha, f): return subprocess.run(['git', '-C', R, 'show', f'{sha}:{P}{f}'], capture_output=True, check=True).stdout

def load(R, sha):
    commit = subprocess.run(['git', '-C', R, 'rev-parse', sha + '^{commit}'], capture_output=True, text=True, check=True).stdout.strip()
    F = {'commit': commit, 'files': {}}
    for f in FILES:
        raw = _raw(R, commit, f)
        F['files'][f] = {'path': P + f, 'sha256': hashlib.sha256(raw).hexdigest(), 'rows': list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))}
    return F

def is_foreign_id(i):
    p = i.split(':')[0]
    return (p in ('nation', 'province', 'subdivision') and i != 'nation:us') or (p == 'territory' and i not in US_FIPS_TERR)

def integrate(F, ents, new_row, domestic_f2e):
    """ents: entity_id -> row (mutable; minted rows are added). new_row(**kw) -> fresh row dict.
    Returns dict(rows=minted, fmap, imgs, gaps, rels, stats, closed=set of (gap, key))."""
    rows_by_file = {f: F['files'][f]['rows'] for f in FILES}
    qid_owner = {e['wikidata'].replace('wikidata:', ''): eid for eid, e in ents.items() if e.get('wikidata')}
    fmap, gaps, rels, minted, st = [], [], [], [], C.Counter()
    review = set()
    for f in FILES[:3]:
        for r in rows_by_file[f]:
            if 'review_status' in r['flags'].split(';'): review.add(r['entity_id'])
    def carry_attrs(e, eid, r):
        for c in ('constituent_qid', 'valid_from', 'valid_to', 'valid_from_source'):
            v = r.get(c, '')
            if not v: continue
            if c == 'constituent_qid' and qid_owner.get(v) not in (None,):
                gaps.append({'gap': 'wikidata_qid_conflict', 'key': eid, 'detail': f'governments-bot constituent_qid {v} is the wikidata of {qid_owner[v]}; not carried'}); st['qid_conflict'] += 1; continue
            cur = e.get(c, '')
            if cur and cur != v:
                gaps.append({'gap': 'govbot_foreign_attr_differs', 'key': eid, 'detail': f'{c}: registry {cur} vs governments-bot {v}; kept registry'}); continue
            if not cur: e[c] = v; st['carried_' + c] += 1; e['_gf'] = e.get('_gf') or 'x'
    def carry_qid(e, eid, q, what):
        if not q: return
        own = qid_owner.get(q)
        cur = e.get('wikidata', '').replace('wikidata:', '')
        if cur and cur != q:
            gaps.append({'gap': 'wikidata_qid_conflict', 'key': eid, 'detail': f'registry {cur} vs governments-bot foreign {q}; kept registry value'}); st['qid_conflict'] += 1
        elif not cur:
            if own and own != eid:
                gaps.append({'gap': 'wikidata_qid_conflict', 'key': eid, 'detail': f'governments-bot foreign {q} is already on {own}; not carried'}); st['qid_conflict'] += 1
            else:
                e['wikidata'] = q; qid_owner[q] = eid; st['qid_carried_' + what] += 1; return True
    for f, kind in (('foreign/nations.csv', 'nation'), ('foreign/dependencies.csv', 'territory'), ('foreign/subdivisions.csv', None)):
        for r in rows_by_file[f]:
            fid = r['entity_id']; par = r['parent_id']; k = kind or fid.split(':')[0]
            base = {'feed': 'governments-bot', 'feed_id': fid, '_file': f}
            if fid in review:
                fmap.append(dict(base, entity_id='', status='feed_only', note=f'review_status;pending_user;registry_{"has_" + fid if fid in ents else "lacks_it"}'))
                st['feed_only_review_status'] += 1; continue
            if par in review:
                fmap.append(dict(base, entity_id='', status='feed_only', note=f'parent_{par}_review_status;pending_user;not_minted'))
                st['feed_only_parent_review'] += 1; continue
            if fid in ents:
                e = ents[fid]; notes = ['existing']
                if (e.get('parent_id') or '') != par:
                    gaps.append({'gap': 'govbot_foreign_parent_differs', 'key': fid, 'detail': f"registry parent {e.get('parent_id') or 'none'} vs governments-bot {par or 'none'}; kept registry"}); notes.append('parent_differs')
                if carry_qid(e, fid, r['wikidata_qid'], 'existing'): e['_gf'] = f; notes.append('qid_carried')
                if r['iso_3166_2'] and not e.get('iso_3166_2'): e['iso_3166_2'] = r['iso_3166_2']; e['_gf'] = f
                carry_attrs(e, fid, r)
                if e.get('_gf') == 'x': e['_gf'] = f
                fmap.append(dict(base, entity_id=fid, status='mapped', note=';'.join(notes + [f'type={r["type"]}'])))
                st['mapped_existing|' + k] += 1; continue
            if par and par not in ents:
                gaps.append({'gap': 'govbot_foreign_parent_missing', 'key': fid, 'detail': f'parent {par} not in registry; not minted'})
                fmap.append(dict(base, entity_id='', status='unmapped', note=f'parent_missing:{par}')); continue
            us = fid == 'territory:74'
            e = new_row(entity_id=fid, kind=k, name=r['name'], parent_id=par,
                        alias=r['official_name'] if r['official_name'] and r['official_name'] != r['name'] else '',
                        label='sovereign' if k == 'nation' else '', gov_status='government' if k == 'nation' else '',
                        level='national' if k == 'nation' else ('federal' if us else 'subnational'),
                        type='sovereign_state' if k == 'nation' else ('territory' if us else ('dependency' if k == 'territory' else r['subtype'])),
                        state_fips='74' if us else '', state=r['name'] if us else '',
                        feed='governments-bot', source_record_id=fid, iso_3166_2=r['iso_3166_2'])
            fl = []
            if k != 'nation': fl.append('gov_status_unknown:' + ('not_in_cog2022_scope' if us else 'outside_cog2022_scope'))
            if r['un_status'] == 'observer': fl.append('un_observer(governments_bot)')
            fl.append('outside_v2_scope:no_unit_no_boundary_set')
            e['_flags'] = fl; e['_gf'] = f; e['wikidata'] = ''
            carry_qid(e, fid, r['wikidata_qid'], 'minted')
            carry_attrs(e, fid, r); e['_gf'] = f
            ents[fid] = e; minted.append(e)
            if par: rels.append({'entity_id': fid, 'relation': 'parent', 'related_entity_id': par, '_file': f})
            fmap.append(dict(base, entity_id=fid, status='mapped', note=f'minted;type={r["type"]}'))
            st['minted|' + k] += 1
    for r in rows_by_file['foreign/iso_domestic_crosswalk.csv']:
        t = r['entity_id']; t2 = domestic_f2e.get(t, '') if t not in ents else t
        base = {'feed': 'governments-bot', 'feed_id': 'iso3166:' + r['iso_code'], '_file': 'foreign/iso_domestic_crosswalk.csv'}
        if t in review: fmap.append(dict(base, entity_id='', status='feed_only', note=f'{r["relation"]};target {t} review_status;pending_user'))
        elif t2: fmap.append(dict(base, entity_id=t2, status='mapped', note=r['relation'] + ('' if t2 == t else f';via_feed_id={t}')))
        else: fmap.append(dict(base, entity_id='', status='unmapped', note=f'{r["relation"]};target {t} not in registry'))
    imgs = []
    f2e = {m['feed_id']: m['entity_id'] for m in fmap}
    note_of = {m['feed_id']: m['note'] for m in fmap}
    for x in rows_by_file['images.csv']:
        fid = x['entity_id']
        if not is_foreign_id(fid) and fid != 'territory:74': continue
        tgt = f2e.get(fid, '')
        assert x['image_kind'] in ('seal', 'flag', 'logo'), x['image_kind']
        if not tgt:
            gaps.append({'gap': 'image_entity_unmapped', 'key': fid, 'detail': x['image_kind'] + ' ' + x['commons_file'] + ('; review_status, pending user' if 'review_status' in note_of.get(fid, '') else '')})
            st['images_unmapped'] += 1
        fu = x['license'] == 'fair-use'
        if fu and not x['usage_basis']: gaps.append({'gap': 'image_fair_use_inconsistent', 'key': fid, 'detail': 'fair-use without usage_basis'})
        imgs.append({'entity_id': tgt, 'feed_id': fid, 'role': x['image_kind'], 'file': x['commons_file'], 'commons_url': x['commons_url'],
                     'license': x['license'], 'usage_basis': x['usage_basis'], 'attribution': x['attribution'], 'source_url': x['source_url'],
                     'wikidata_qid': x['wikidata_qid'], 'retrieved_at': x['retrieved_at'], 'fair_use': 'yes' if fu else 'no', '_foreign': True})
    st['images'] = len(imgs); st['images_fair_use'] = sum(1 for i in imgs if i['fair_use'] == 'yes')
    st['feed_rows'] = len(fmap); st['relations_parent'] = len(rels)
    return {'rows': minted, 'fmap': fmap, 'imgs': imgs, 'gaps': gaps, 'rels': rels, 'stats': dict(sorted(st.items())), 'review': sorted(review)}
