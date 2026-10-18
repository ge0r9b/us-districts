#!/usr/bin/env python3
"""2022 US Senate on v2's 2024 precinct polygons (v2 has no 2022 precinct polygons).
usage: build_sen2022.py <repo> <medsl22_dir> <medsl24_dir> <work_dir> <ST>...
 1. MEDSL 2024 precinct returns are matched to the v2 2024 polygons by the 2024 president result, exactly as in
    2024/senate/tools/build_sen2024.py (county + Harris/Trump pair; county + name; statewide pair; town groups).
 2. Each MEDSL 2022 precinct is bridged to a polygon: (a) identical MEDSL key (county FIPS, jurisdiction, precinct) in 2024;
    (b) same county + normalized precinct name as a matched 2024 MEDSL precinct; (c) same county + normalized v2 polygon name;
    (d) MEDSL 2022 precincts summed by (county, jurisdiction) -> a town-level v2 polygon with that name.
 3. Same MEDSL mode rule, candidate slots (races22.py) and allocation of unbridged votes as 2024 (weights = each polygon's
    2024 president d / r / total)."""
import sys, os, csv, re, json, pickle, glob, collections
sys.path.insert(0, os.path.dirname(__file__)); from races22 import *
import shapely
from shapely.geometry import Polygon, MultiPolygon
repo, m22, m24, wd = sys.argv[1:5]; STS = sys.argv[5:]
def num(x):
    try: return int(float(x))
    except: return 0
def dec(f, sc=10000):
    o=[];x=y=0
    for i in range(0,len(f),2): x+=f[i];y+=f[i+1];o.append((x/sc,y/sc))
    return o
def geom(encp):
    ps=[]
    for rs in encp:
        rings=[dec(f) for f in rs if len(f)>=6]
        if rings:
            g=Polygon(rings[0],rings[1:])
            if not g.is_valid: g=shapely.make_valid(g)
            st=[g]
            while st:
                q=st.pop()
                if hasattr(q,'geoms'): st+=list(q.geoms)
                elif q.geom_type=='Polygon' and not q.is_empty: ps.append(q)
    if not ps: return None
    mp=MultiPolygon(ps); return mp if mp.is_valid else shapely.union_all(ps)
CTY = {}
for r in csv.DictReader(open(f'{repo}/data-v3/geo/counties.csv')): CTY[r['geoid']] = r['v2_name']
def norm(s): return re.sub(r'[^A-Z0-9]', '', str(s).upper().replace('PRECINCT','').replace('PCT',''))
def fips(x): return x.zfill(5) if x and x.isdigit() else x
def variants(name):
    n = str(name); out = [norm(n)]
    a = re.sub(r'^\d{2}-\d{3}\s+', '', n)            # AK '01-600 Ketchikan No. 1'
    if a != n: out.append(norm(a))
    b = re.sub(r'^\d+[A-Z]?\s+(?=[A-Za-z])', '', n)    # AZ '01 BE BENSON'
    if b != n: out.append(norm(b))
    head = n.split('_')[0]
    for x in (n, head):
        if re.fullmatch(r'[\d\s\-./]+', x.strip() or 'x'): out.append('N:' + '.'.join(str(int(d)) for d in re.findall(r'\d+', x)))
    return [v for i, v in enumerate(out) if v and v not in out[:i]]
def collapse(groups):
    P = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for (race, *key), rows in groups.items():
        use = [x for x in rows if x[0] == 'TOTAL'] or rows
        for _, c, p, v in use:
            if not is_nonvote(c): P[race][tuple(key)][(c, p)] += v
    return P
os.makedirs(wd, exist_ok=True)
for ab in STS:
    stn = NAME[ab]; races = sorted({k[1] for k in RACES if k[0] == ab})
    # ---- 2024 MEDSL president -> v2 polygons
    g24 = collections.defaultdict(list)
    for r in csv.DictReader(open(f'{m24}/{ab.lower()}24/{ab.lower()}24.csv', encoding='utf-8', errors='replace')):
        if r['office'] != 'US PRESIDENT': continue
        pr = r['precinct']
        if ab == 'CA': pr = re.sub(r'(?<=\d)(AA|A|B|C)$', '', pr)
        g24[('pres', fips(r['county_fips']), r['jurisdiction_name'], pr)].append((r['mode'], r['candidate'], r['party_simplified'], num(r['votes'])))
    P24 = collapse(g24)['pres']
    def ptri(cnt):
        a = [0, 0, 0]
        for (c, p), v in cnt.items():
            u = c.upper(); a[0 if 'HARRIS' in u else 1 if 'TRUMP' in u else 2] += v
        return [a[0], a[1], sum(a)]
    pres = {k: ptri(c) for k, c in P24.items()}
    t = open(f'{repo}/v2/data/precincts2024/{stn.replace(" ","_")}.js').read(); V = json.JSONDecoder().raw_decode(t, t.index('[['))[0]
    cname = lambda k: CTY.get(k[0])
    byc = collections.defaultdict(lambda: collections.defaultdict(list)); byn = collections.defaultdict(lambda: collections.defaultdict(list)); bys = collections.defaultdict(list); byt = collections.defaultdict(list)
    for j, row in enumerate(V):
        byc[row[0]][(row[2], row[3])].append(j); byn[row[0]][norm(row[1])].append(j); bys[(row[2], row[3])].append(j)
        byt[norm(re.sub(r'^\d+-', '', str(row[1])))].append(j)
    m24k = {}; used = set()
    mk = collections.defaultdict(lambda: collections.defaultdict(list)); mn = collections.defaultdict(lambda: collections.defaultdict(list)); ms = collections.defaultdict(list)
    for k, p in pres.items():
        if p[0]+p[1] > 0: mk[cname(k)][(p[0], p[1])].append(k); ms[(p[0], p[1])].append(k)
        mn[cname(k)][norm(k[2])].append(k)
    for c in mk:
        for pr, ks in mk[c].items():
            js = byc.get(c, {}).get(pr, [])
            if len(ks) == 1 and len(js) == 1: m24k[ks[0]] = js[0]; used.add(js[0])
    for c in mn:
        for nm, ks in mn[c].items():
            ks = [k for k in ks if k not in m24k]; js = [j for j in byn.get(c, {}).get(nm, []) if j not in used]
            if len(ks) == 1 and len(js) == 1: m24k[ks[0]] = js[0]; used.add(js[0])
    for pr, ks in ms.items():
        ks = [k for k in ks if k not in m24k]; js = [j for j in bys.get(pr, []) if j not in used]
        if len(ks) == 1 and len(js) == 1: m24k[ks[0]] = js[0]; used.add(js[0])
    grp = collections.defaultdict(list)
    for k in pres:
        if k not in m24k: grp[(cname(k), k[1])].append(k)
    for (c, jur), ks in grp.items():
        sp = (sum(pres[k][0] for k in ks), sum(pres[k][1] for k in ks))
        js = [j for j in byc.get(c, {}).get(sp, []) if j not in used]
        if len(js) != 1: js = [j for j in byn.get(c, {}).get(norm(jur), []) if j not in used]
        if len(js) != 1 and c is None: js = [j for j in bys.get(sp, []) if j not in used]
        if len(js) != 1 and c is None: js = [j for j in byt.get(norm(jur), []) if j not in used]
        if len(js) == 1:
            for k in ks: m24k[k] = js[0]
            used.add(js[0])
    n24 = collections.defaultdict(set)
    for k, j in m24k.items():
        for v in variants(k[2]): n24[(k[0], v)].add(j)
    bv = collections.defaultdict(lambda: collections.defaultdict(set)); bvs = collections.defaultdict(set)
    for j, row in enumerate(V):
        for v in variants(row[1]): bv[row[0]][v].add(j); bvs[v].add(j)
    # ---- 2022 Senate rows
    f22 = (glob.glob(f'{m22}/2022-{ab.lower()}/*_official.csv') or glob.glob(f'{m22}/2022-{ab.lower()}/*_swdb.csv') or glob.glob(f'{m22}/2022-{ab.lower()}/*.csv'))[0]   # official replacements first (ID SOS, IN IED), then CA SWDB, then MEDSL
    g22 = collections.defaultdict(list)
    for r in csv.DictReader(open(f22, encoding='utf-8', errors='replace')):
        o = r['office']
        if not o.startswith('US SENATE') or r['district'] not in ('STATEWIDE', '', '000'): continue
        stage = r.get('stage', 'GEN')
        race = 'runoff' if 'RUNOFF' in stage.upper() else 'special' if r['special'].upper() == 'TRUE' else 'regular'
        if (ab, race) not in RACES: continue
        pr = r['precinct']
        if ab == 'CA': pr = re.sub(r'(?<=\d)(AA|A|B|C)$', '', pr)
        g22[(race, fips(r['county_fips']), r['jurisdiction_name'], pr)].append((r['mode'], r['candidate'], r.get('party_simplified', ''), num(r['votes'])))
    P = collapse(g22)
    rep = {'state': ab, 'v2_rows': len(V), 'medsl24_matched_polys': len(used), 'source_file': os.path.basename(f22)}
    G = [None]*len(V)
    for race in races:
        S = {}
        for k, cnt in P[race].items():
            a = {'d':0,'r':0,'o':0}
            for (c, p), v in cnt.items(): a[slot(ab, race, c)] += v
            S[k] = [a['d'], a['r'], a['d']+a['r']+a['o']]
        bridge = {}; how = collections.Counter()
        for k in S:
            if k in m24k: bridge[k] = m24k[k]; how['a'] += 1; continue
            done = False
            for v in variants(k[2]):
                js = n24.get((k[0], v), set())
                if len(js) == 1: bridge[k] = next(iter(js)); how['b'] += 1; done = True; break
            if done: continue
            for v in variants(k[2]):
                js = bv[cname(k)].get(v, set()) if cname(k) else bvs.get(v, set())
                if len(js) == 1: bridge[k] = next(iter(js)); how['c'] += 1; break
        tg = collections.defaultdict(list)
        for k in S:
            if k not in bridge: tg[(cname(k), k[1])].append(k)
        for (c, jur), ks in tg.items():
            js = byn.get(c, {}).get(norm(jur), []) if c else byt.get(norm(jur), [])
            if len(js) == 1:
                for k in ks: bridge[k] = js[0]
                how['d'] += len(ks)
        vals = [[0.0,0.0,0.0] for _ in V]; alloc = [0.0]*len(V)
        cty_tot = collections.defaultdict(lambda: [0,0,0]); resid = collections.defaultdict(lambda: [0,0,0]); unk = [0,0,0]
        for k, s in S.items():
            if k in bridge:
                j = bridge[k]; c = V[j][0]
                for q in range(3): vals[j][q] += s[q]
            else:
                c = cname(k)
                if c is None or c not in byc: unk = [unk[q]+s[q] for q in range(3)]; continue
                for q in range(3): resid[c][q] += s[q]
            for q in range(3): cty_tot[c][q] += s[q]
        bj = set(bridge.values())
        if sum(unk):
            # votes with no usable county (AK: House-district absentee/early/question rows) are spread over every polygon by 2024 president votes
            tot = [sum(V[j][2+q] for j in range(len(V))) for q in range(3)]
            per = collections.defaultdict(lambda: [0.0,0.0,0.0])
            for j in range(len(V)):
                if True:
                    for q in range(3): per[V[j][0]][q] += unk[q]*V[j][2+q]/max(tot[q],1)
            for c, a in per.items():
                for q in range(3): resid[c][q] += a[q]; cty_tot[c][q] += a[q]
        for c, rs in resid.items():
            if sum(rs) == 0: continue
            js = [j for j in range(len(V)) if V[j][0] == c and j not in bj]
            # unbridged polygons only when they are big enough to hold the residual (2024 president total >= residual total); else the whole county
            if sum(V[j][4] for j in js) < rs[2]: js = [j for j in range(len(V)) if V[j][0] == c]
            tot = [sum(V[j][2+q] for j in js) for q in range(3)]
            for j in js:
                for q in range(3): vals[j][q] += rs[q]*V[j][2+q]/tot[q] if tot[q] else rs[q]/len(js)
                alloc[j] += rs[2]*V[j][4]/tot[2] if tot[2] else rs[2]/len(js)
        for j in range(len(V)):
            if G[j] is None:
                g = geom(V[j][5]); G[j] = g.wkb if g is not None else None
        # polygons in counties with no 2022 Senate rows at all (e.g. IN: MEDSL has 39 of 92 counties) carry no shape, so districts there go gray instead of looking like 0 votes
        has = {c for c, a in cty_tot.items() if a[2] > 0}
        pickle.dump([(V[j][0], V[j][1], vals[j][0], vals[j][1], vals[j][2], G[j] if V[j][0] in has else None, alloc[j], j in bj) for j in range(len(V))], open(f'{wd}/{ab}_{race}.pkl', 'wb'))
        st_tot = [sum(s[q] for s in S.values()) for q in range(3)]; m_tot = sum(s[2] for k, s in S.items() if k in bridge)
        pj = collections.defaultdict(lambda: [0,0,0])
        for k, s in S.items():
            if k in bridge:
                for q in range(3): pj[bridge[k]][q] += s[q]
        um = collections.defaultdict(lambda: [0,0])
        for k, s in S.items():
            if k not in bridge: c = cname(k) or (f'fips {k[0]}' if k[0] else f'(no county) {k[1]}'); um[c][0] += 1; um[c][1] += s[2]
        rep[race] = {'medsl_state': st_tot, 'matched_share': round(m_tot/max(st_tot[2],1), 4), 'medsl_precincts': len(S),
                     'matched_precincts': len(bridge), 'matched_polys': len(pj), 'bridge': dict(how), 'unknown_county_votes': unk[2],
                     'counties': {c: [int(round(x)) for x in a] for c, a in cty_tot.items()},
                     'precincts': {f'{V[j][0]}|{V[j][1]}|{j}': a for j, a in pj.items()}, 'unmatched_by_county': dict(um)}
        print(ab, race, 'medsl', st_tot, 'bridged', len(bridge), '/', len(S), dict(how), 'share', rep[race]['matched_share'], 'polys', len(pj), '/', len(V), flush=True)
    json.dump(rep, open(f'{wd}/{ab}.json', 'w'))
