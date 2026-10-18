#!/usr/bin/env python3
"""World institutions for data-v3/inst/entities.csv: national governments (nation:<iso2>), foreign dependencies
(territory:<iso2>), Canadian provinces (province:ca-<code>) and territories (territory:ca-<code>).

The LIST of which institutions exist comes from v2's Natural Earth layers on origin/main (v2/data/countries.js,
v2/data/canada.js; Geo bot's files, read only). No geometry is copied: the institution is a separate entity from the
area (user rule), and non-US places carry no xwalk unit and no boundary_set (SCHEMA 62cb622).
Status (sovereign / UN member / dependency + sovereign) and QIDs come only from Wikidata (SPARQL, CC0).

  inst_world.py fetch <repo> <rawdir>     # writes the .rq queries + .json answers + SHA256SUMS + retrieved_at.txt
  (import) build(repo, rawdir) -> dict    # used by tools/inst_entities.py --world-raw <rawdir>; offline, deterministic
"""
import csv, hashlib, io, json, os, re, subprocess, sys, collections as C

NE_REF = 'origin/main'
COUNTRIES = 'v2/data/countries.js'; CANADA = 'v2/data/canada.js'
UA = 'us-districts-inst/1.0 (https://github.com/ge0r9b/us-districts)'
EP = 'https://query.wikidata.org/sparql'
W = 'http://www.wikidata.org/entity/'
# Canada: ISO 3166-2 code -> kind. Id pattern kept in ONE place (Full Stack confirmed territory:ca-<code>, province:ca-<code>).
CA_TERRITORIES = {'NT', 'NU', 'YT'}
def ca_id(code): return ('territory:ca-%s' if code in CA_TERRITORIES else 'province:ca-%s') % code.lower()
def ca_kind(code): return 'territory' if code in CA_TERRITORIES else 'province'
# US: ISO alpha-2 codes that are US territories stay territory:<FIPS> under nation:us (never nations, never territory:<iso2>)
US_ISO_TERRITORIES = {'pr': '72', 'gu': '66', 'vi': '78', 'as': '60', 'mp': '69'}
SOV, UN = 'Q3624078', 'Q1065'

def git(repo, *a): return subprocess.run(['git', '-C', repo] + list(a), capture_output=True, check=True).stdout
def jsarr(text):
    i = text.index('=', text.index('window.')); return json.loads(text[i + 1:].strip().rstrip(';'))
def ne_inputs(repo):
    out = {}
    for p in (COUNTRIES, CANADA):
        b = git(repo, 'show', f'{NE_REF}:{p}')
        out[p] = {'rows': jsarr(b.decode('utf-8')), 'sha256': hashlib.sha256(b).hexdigest(),
                  'commit': git(repo, 'log', '-1', '--format=%H', NE_REF, '--', p).decode().strip()}
    return out

CUR = lambda r: f'?{r} wikibase:rank ?{r}k . FILTER(?{r}k != wikibase:DeprecatedRank) FILTER NOT EXISTS {{ ?{r} pq:P582 [] }}'
HEAD = ('# us-districts data-v3/inst world institutions (tools/inst_world.py, CC0 data from Wikidata).\n'
        '# "Current" statement = rank not deprecated and no end time (P582).\n')
def q_items(codes, cacodes):
    return HEAD + '''# (A) items holding a current ISO 3166-1 alpha-2 (P297; v2/data/countries.js) or ISO 3166-2 (P300; v2/data/canada.js) code
SELECT ?code ?prop ?item ?itemLabel WHERE {
  { VALUES ?code { %s } ?item p:P297 ?c . ?c ps:P297 ?code . %s BIND("P297" AS ?prop) }
  UNION
  { VALUES ?code { %s } ?item p:P300 ?c . ?c ps:P300 ?code . %s BIND("P300" AS ?prop) }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
ORDER BY ?prop ?code ?item
''' % (' '.join('"%s"' % c for c in codes), CUR('c'), ' '.join('"CA-%s"' % c for c in cacodes), CUR('c'))
def q_claims(items):
    br = [('P31', 'wd:' + SOV), ('P463', 'wd:' + UN), ('P17', None), ('P361', None), ('P300', None), ('P36', None), ('P297', None)]
    def one(p, fixed):
        if fixed: return '{ ?item p:%s ?s . ?s ps:%s %s . %s BIND(%s AS ?value) BIND("%s" AS ?p) }' % (p, p, fixed, CUR('s'), fixed, p)
        return '{ ?item p:%s ?s . ?s ps:%s ?value . %s BIND("%s" AS ?p) }' % (p, p, CUR('s'), p)
    return HEAD + '''# (B/C) current status claims of the listed items: P31 = Q3624078 (sovereign state), P463 = Q1065 (member of the
# United Nations), P17 (country), P361 (part of), P300 (ISO 3166-2), P36 (capital), P297 (ISO 3166-1 alpha-2)
SELECT ?item ?p ?value WHERE {
  VALUES ?item { %s }
  %s
}
ORDER BY ?item ?p ?value
''' % (' '.join('wd:' + q for q in items), '\n  UNION '.join(one(p, f) for p, f in br))
def q_un():
    return HEAD + '''# (C) all current UN member states (P463 = Q1065) with current ISO 3166-1 alpha-2, for the coverage comparison
SELECT ?item ?itemLabel ?iso2 WHERE {
  ?item p:P463 ?s . ?s ps:P463 wd:%s . %s
  OPTIONAL { ?item p:P297 ?t . ?t ps:P297 ?iso2 . %s }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
ORDER BY ?item ?iso2
''' % (UN, CUR('s'), CUR('t'))

def val(b, k): return b.get(k, {}).get('value', '').replace(W, '')
def load(rawdir, name): return [{k: val(b, k) for k in b} for b in json.load(open(os.path.join(rawdir, name + '.json')))['results']['bindings']]

def fetch(repo, rawdir):
    import urllib.request, urllib.parse, time
    os.makedirs(rawdir, exist_ok=True)
    ne = ne_inputs(repo)
    codes = sorted({r[0].upper() for r in ne[COUNTRIES]['rows']}); cac = sorted(r[1] for r in ne[CANADA]['rows'])
    def run(name, q):
        open(os.path.join(rawdir, name + '.rq'), 'w').write(q)
        req = urllib.request.Request(EP + '?' + urllib.parse.urlencode({'query': q}), headers={'Accept': 'application/sparql-results+json', 'User-Agent': UA})
        body = urllib.request.urlopen(req, timeout=120).read(); json.loads(body)
        open(os.path.join(rawdir, name + '.json'), 'wb').write(body); time.sleep(1)
    run('world_a_items', q_items(codes, cac))
    items = sorted({r['item'] for r in load(rawdir, 'world_a_items')}, key=lambda q: int(q[1:]))
    run('world_b_claims', q_claims(items))
    # second hop: the countries / part-of targets (their own P297, P31 sovereign, P463 UN, P36 capital)
    b = load(rawdir, 'world_b_claims')
    hop = sorted({r['value'] for r in b if r['p'] in ('P17', 'P361') and r['value'].startswith('Q')} - set(items), key=lambda q: int(q[1:]))
    run('world_c_targets', q_claims(hop))
    run('world_d_un_members', q_un())
    open(os.path.join(rawdir, 'retrieved_at.txt'), 'w').write(__import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ') + '\n')
    with open(os.path.join(rawdir, 'SHA256SUMS'), 'w') as fh:
        for f in sorted(os.listdir(rawdir)):
            if f.endswith(('.rq', '.json')): fh.write('%s  %s\n' % (hashlib.sha256(open(os.path.join(rawdir, f), 'rb').read()).hexdigest(), f))

def build(repo, rawdir):
    """-> {'rows': [entity dicts], 'gaps': [...], 'skipped': [...], 'compare': {...}, 'files': {...}, 'ne': ne, 'qid_us': ...}"""
    ne = ne_inputs(repo)
    A = load(rawdir, 'world_a_items'); B = load(rawdir, 'world_b_claims') + load(rawdir, 'world_c_targets'); UNM = load(rawdir, 'world_d_un_members')
    label = {r['item']: r['itemLabel'] for r in A}
    cl = C.defaultdict(lambda: C.defaultdict(set))
    for r in B: cl[r['item']][r['p']].add(r['value'])
    sov = lambda q: SOV in cl[q]['P31']; un = lambda q: UN in cl[q]['P463']
    by_code = C.defaultdict(list)
    for r in A: by_code[r['code']].append(r['item'])
    rows, gaps, skipped = [], [], []
    def gap(g, key, detail): gaps.append({'gap': g, 'key': key, 'detail': detail})
    # 1. resolve one item per ISO alpha-2 code
    chosen = {}
    for iso, name, *_ in ne[COUNTRIES]['rows']:
        c = iso.upper(); items = sorted(set(by_code.get(c, [])), key=lambda q: int(q[1:]))
        if len(items) > 1:
            s_ = [q for q in items if sov(q)]
            if len(s_) == 1:
                gap('wikidata_p297_several_items', f'nation:{iso}', f'P297 {c} on {";".join(items)}; kept {s_[0]} (the only current sovereign state, P31 Q3624078)')
                items = s_
        chosen[iso] = items
    # sovereign item -> nation iso2 (a sovereign holding a P297 code of the list)
    sov_to_iso = {}
    for iso, items in chosen.items():
        if len(items) == 1 and sov(items[0]): sov_to_iso[items[0]] = iso
    # Wikidata puts some ISO codes on the metropolitan part, not on the sovereign realm (DK: Q35 Denmark vs Q756617 Kingdom of
    # Denmark). Rule: a non-sovereign P297 item whose current P17 is ONE sovereign state without a P297 code, and which has the same
    # current capital (P36) as that sovereign, is the sovereign's home part -> nation:<iso2> = that sovereign state.
    home = {}
    for iso, items in chosen.items():
        if len(items) != 1 or sov(items[0]): continue
        q = items[0]; ss = [s for s in cl[q]['P17'] if s != q and sov(s) and not cl[s]['P297']]
        if len(ss) == 1 and cl[q]['P36'] and cl[q]['P36'] & cl[ss[0]]['P36']:
            home[iso] = ss[0]; sov_to_iso[ss[0]] = iso
    def sovereign_of(q):
        cands = sorted({s for s in cl[q]['P17'] if s != q and sov(s)}); via = 'P17'
        if not cands: cands = sorted({s for s in cl[q]['P361'] if s != q and sov(s)}); via = 'P361'
        if not cands:   # ISO 3166-2 code of the dependency in its sovereign's ISO 3166-2 list (e.g. NL-AW)
            pre = sorted({c.split('-')[0] for c in cl[q]['P300'] if '-' in c})
            cands = sorted({q2 for c in pre for q2 in by_code.get(c, []) if sov(q2)} | {home_q for c in pre for i_, home_q in home.items() if i_.upper() == c}); via = 'P300'
        return cands, via
    us_qid = ''
    for iso, name, *_ in ne[COUNTRIES]['rows']:
        items = chosen[iso]; key = f'nation:{iso}'
        if iso == 'us':
            if len(items) == 1: us_qid = items[0]
            continue
        if iso in US_ISO_TERRITORIES:
            skipped.append({'iso2': iso, 'name': name, 'reason': f'US territory: stays territory:{US_ISO_TERRITORIES[iso]} under nation:us'}); continue
        r = {'iso2': iso, 'ne_name': name, 'flags': [], 'wikidata': '', 'wd_label': '', 'parent_id': ''}
        if not items:
            r.update(entity_id=key, kind='nation'); r['flags'].append('wikidata_qid_missing:no_current_p297_item')
            r['flags'].append('status_unknown:no_wikidata_item'); gap('wikidata_qid_missing', key, f'{name}: no Wikidata item with current P297 {iso.upper()}'); rows.append(r); continue
        if len(items) > 1:
            r.update(entity_id=key, kind='nation'); r['flags'].append('status_unknown:several_p297_items')
            gap('wikidata_status_ambiguous', key, f'{name}: P297 {iso.upper()} on {";".join(items)}, none or several sovereign; QID left empty'); rows.append(r); continue
        q = items[0]; r['wd_label'] = label.get(q, '')
        if sov(q) or iso in home:
            sq = home.get(iso, q)
            r.update(entity_id=key, kind='nation', wikidata=sq)
            if iso in home:
                r['flags'].append(f'wikidata_p297_item_is_home_part:{q}(sovereign_{sq}_via_P17+same_P36)')
                gap('wikidata_qid_via_home_part_rule', key, f'{name}: P297 {iso.upper()} is on {q} ({label.get(q, "")}, not a sovereign state); its P17 {sq} is the sovereign state (same capital P36); QID set to {sq}')
            if not un(sq):
                r['flags'].append('not_un_member(wikidata_P463)')
                gap('nation_not_un_member', key, f'{name} ({sq}): current sovereign state (P31 Q3624078) but no current P463 Q1065 (UN member); kept kind nation, no parent')
        else:
            cands, via = sovereign_of(q)
            mapped = sorted({sov_to_iso[s] for s in cands if s in sov_to_iso})
            r.update(wikidata=q)
            r['flags'].append('not_sovereign_state(wikidata_P31)'); 
            if not un(q): r['flags'].append('not_un_member(wikidata_P463)')
            if len(mapped) == 1 and mapped[0] != 'us':
                r.update(entity_id=f'territory:{iso}', kind='territory', parent_id=f'nation:{mapped[0]}')
                r['flags'].append(f'sovereign_via_wikidata_{via}:{";".join(cands)}'.replace(';', ','))
                if len(cands) > 1: gap('territory_sovereign_several_candidates', f'territory:{iso}', f'{name} ({q}): {via} -> {";".join(cands)}; mapped to nation:{mapped[0]} (only one of them is a nation in the list)')
            elif len(mapped) == 1 and mapped[0] == 'us':
                skipped.append({'iso2': iso, 'name': name, 'reason': 'Wikidata sovereign is the United States: US territories stay territory:<FIPS>'}); continue
            else:
                r.update(entity_id=f'territory:{iso}', kind='territory', parent_id='')
                r['flags'].append('sovereign_unknown')
                gap('territory_sovereign_unknown', f'territory:{iso}', f'{name} ({q}): not a current sovereign state; Wikidata P17/P361/P300 give {"no sovereign" if not cands else "; ".join(cands) + " (not a nation in the list)"}; parent left empty')
        rows.append(r)
    # Canada
    ca_q = chosen.get('ca', [''])
    for nm, code, *_ in ne[CANADA]['rows']:
        items = sorted(set(by_code.get('CA-' + code, [])), key=lambda q: int(q[1:]))
        eid = ca_id(code)
        r = {'iso2': 'ca', 'ne_name': nm, 'code': code, 'flags': [], 'entity_id': eid, 'kind': ca_kind(code), 'parent_id': 'nation:ca',
             'wikidata': '', 'wd_label': ''}
        if len(items) == 1:
            q = items[0]; r['wikidata'] = q; r['wd_label'] = label.get(q, '')
            if ca_q and ca_q[0] and ca_q[0] not in cl[q]['P17']:
                r['flags'].append('wikidata_P17_is_not_canada'); gap('wikidata_status_ambiguous', eid, f'{nm} ({q}): current P17 {";".join(sorted(cl[q]["P17"]))} does not include Canada {ca_q[0]}')
        else:
            r['flags'].append('wikidata_qid_missing' if not items else 'wikidata_status_ambiguous:several_p300_items')
            gap('wikidata_qid_missing' if not items else 'wikidata_status_ambiguous', eid, f'{nm}: P300 CA-{code} on {";".join(items) or "no item"}')
        rows.append(r)
    # UN-193 comparison (Wikidata current P463 Q1065), against the Natural Earth list
    un_iso = C.defaultdict(set); un_lab = {}
    for u in UNM:
        un_lab[u['item']] = u['itemLabel']
        if u.get('iso2'): un_iso[u['item']].add(u['iso2'].lower())
    ne_iso = {r[0] for r in ne[COUNTRIES]['rows']}
    nation_q = {r['wikidata'] for r in rows if r['kind'] == 'nation'} | ({us_qid} if us_qid else set())
    missing = sorted((un_lab[q], q, ';'.join(sorted(un_iso[q]))) for q in un_lab if not (un_iso[q] & ne_iso) and q not in nation_q)
    ne_not_un = sorted((r['iso2'], r['ne_name'], r['kind']) for r in rows if r['kind'] != 'province' and r['iso2'] != 'ca' or (r.get('code') is None and r['iso2'] == 'ca'))
    ne_not_un = [x for x in ne_not_un if not any(rr['entity_id'] in ('nation:' + x[0], 'territory:' + x[0]) and rr['wikidata'] and un(rr['wikidata']) for rr in rows)]
    compare = {'un_members_wikidata': len(un_lab), 'un_members_not_in_natural_earth_list': [f'{a} ({b}, iso2 {c or "none"})' for a, b, c in missing],
               'natural_earth_rows_not_un_members': [f'{a} {b} -> {c}' for a, b, c in ne_not_un]}
    files = {}
    for f in sorted(os.listdir(rawdir)):
        if f.endswith(('.rq', '.json')): files[f] = hashlib.sha256(open(os.path.join(rawdir, f), 'rb').read()).hexdigest()
    retrieved = open(os.path.join(rawdir, 'retrieved_at.txt')).read().strip()
    return {'rows': rows, 'gaps': gaps, 'skipped': skipped, 'compare': compare, 'files': files, 'retrieved_at': retrieved, 'ne': ne, 'qid_us': us_qid}

if __name__ == '__main__':
    if sys.argv[1] == 'fetch': fetch(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'show':
        d = build(sys.argv[2], sys.argv[3]); d.pop('ne')
        print(json.dumps(d, indent=1, ensure_ascii=False))
