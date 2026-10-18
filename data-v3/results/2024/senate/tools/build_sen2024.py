#!/usr/bin/env python3
"""2024 US Senate: MEDSL 2024 precinct returns -> v2 2024 precinct polygons -> county/precinct values + per-state pickles for layers.
usage: build_sen2024.py <repo> <medsl_dir> <work_dir> <ST>...
Per state and race:
 - MEDSL rows: per (office, county_fips, jurisdiction, precinct) use only mode=TOTAL rows when any exist, else sum all modes ('*' = 0).
 - candidate -> d/r/o via races.py; non-votes (under/over/blank/void/totals/'none of these') excluded.
 - match MEDSL precincts to v2 precincts2024 rows (same polygons the president layer uses) by the 2024 president result:
   1) county + exact (Harris, Trump) pair, unique on both sides; 2) county + normalized name; 3) state-wide unique (Harris, Trump) pair.
 - matched polygon -> exact MEDSL Senate values. Unmatched MEDSL votes of a county are allocated to the county's unmatched
   polygons (or all its polygons if none) in proportion to their president d / r / t; these polygons carry an 'alloc' amount.
"""
import sys, os, csv, re, json, pickle, collections
sys.path.insert(0, os.path.dirname(__file__)); from races import *
import shapely
from shapely.geometry import Polygon, MultiPolygon
repo, md, wd = sys.argv[1:4]; STS = sys.argv[4:]
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
for r in csv.DictReader(open(f'{repo}/data-v3/geo/counties.csv')): CTY[r['geoid']] = (r['state'], r['v2_name'])
def norm(s): return re.sub(r'[^A-Z0-9]', '', str(s).upper().replace('PRECINCT','').replace('PCT',''))
os.makedirs(wd, exist_ok=True)
for ab in STS:
    stn = NAME[ab]; races = [k[1] for k in RACES if k[0]==ab]
    groups = collections.defaultdict(list)
    for r in csv.DictReader(open(f'{md}/{ab.lower()}24/{ab.lower()}24.csv', encoding='utf-8', errors='replace')):
        o = r['office']
        if o == 'US PRESIDENT': race = 'pres'
        elif o.startswith('US SENATE') and r['district'] in ('STATEWIDE', ''): race = 'special' if r['special'] == 'TRUE' else 'regular'
        else: continue
        pr = r['precinct']
        if ab == 'CA': pr = re.sub(r'(?<=\d)(AA|A|B|C)$', '', pr)   # CA SWDB: 202A = absentee part of 202 etc. (MEDSL README)
        key = (r['county_fips'], r['jurisdiction_name'], pr)
        groups[(race,)+key].append((r['mode'], r['candidate'], r['party_simplified'], num(r['votes'])))
    P = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))   # race -> pkey -> cand -> votes
    for (race, *key), rows in groups.items():
        use = [x for x in rows if x[0] == 'TOTAL'] or rows
        for _, c, p, v in use:
            if not is_nonvote(c): P[race][tuple(key)][(c, p)] += v
    def tri(race, cnt):
        a = {'d':0,'r':0,'o':0}
        for (c, p), v in cnt.items():
            if race == 'pres': u = c.upper(); k = 'd' if 'HARRIS' in u else 'r' if 'TRUMP' in u else 'o'   # by name: fusion lines (NY WFP/CON) count
            else: k = slot(ab, race, c)
            a[k] += v
        return [a['d'], a['r'], a['d']+a['r']+a['o']]
    t = open(f'{repo}/v2/data/precincts2024/{stn.replace(" ","_")}.js').read(); i = t.index('[[')
    V = json.JSONDecoder().raw_decode(t, i)[0]
    rep = {'state': ab, 'v2_rows': len(V)}
    keys = sorted(set(k for race in races for k in P[race]) | set(P['pres']))
    pres = {k: tri('pres', P['pres'].get(k, {})) for k in keys}
    def cname(k): return CTY.get(k[0], (None, None))[1]
    # matching
    match = {}; vt = {}
    byc = collections.defaultdict(lambda: collections.defaultdict(list)); byn = collections.defaultdict(lambda: collections.defaultdict(list)); bys = collections.defaultdict(list)
    for j, row in enumerate(V):
        byc[row[0]][(row[2], row[3])].append(j); byn[row[0]][norm(row[1])].append(j); bys[(row[2], row[3])].append(j)
    mk = collections.defaultdict(lambda: collections.defaultdict(list)); mn = collections.defaultdict(lambda: collections.defaultdict(list)); ms = collections.defaultdict(list)
    for k in keys:
        p = pres[k]
        if p[0]+p[1] > 0: mk[cname(k)][(p[0], p[1])].append(k); ms[(p[0], p[1])].append(k)
        mn[cname(k)][norm(k[2])].append(k)
    byt = collections.defaultdict(list)
    for j, row in enumerate(V): byt[norm(re.sub(r'^\d+-', '', str(row[1])))].append(j)
    used = set()
    for c in mk:
        for pr, ks in mk[c].items():
            js = byc.get(c, {}).get(pr, [])
            if len(ks) == 1 and len(js) == 1: match[ks[0]] = js[0]; used.add(js[0])
    for c in mn:
        for nm, ks in mn[c].items():
            ks = [k for k in ks if k not in match]; js = [j for j in byn.get(c, {}).get(nm, []) if j not in used]
            if len(ks) == 1 and len(js) == 1: match[ks[0]] = js[0]; used.add(js[0])
    for pr, ks in ms.items():
        ks = [k for k in ks if k not in match]; js = [j for j in bys.get(pr, []) if j not in used]
        if len(ks) == 1 and len(js) == 1: match[ks[0]] = js[0]; used.add(js[0])
    # 4) unmatched MEDSL precincts summed by (county, jurisdiction) = town/ward-level v2 polygons (RI, NJ, CT, MA, VT, ...)
    grp = collections.defaultdict(list)
    for k in keys:
        if k not in match: grp[(cname(k), k[1])].append(k)
    gk = collections.defaultdict(list)
    for (c, jur), ks in grp.items():
        sp = [sum(pres[k][0] for k in ks), sum(pres[k][1] for k in ks)]
        js = [j for j in byc.get(c, {}).get(tuple(sp), []) if j not in used]
        if len(js) != 1: js = [j for j in byn.get(c, {}).get(norm(jur), []) if j not in used]
        if len(js) != 1 and c is None: js = [j for j in bys.get(tuple(sp), []) if j not in used]   # county code not in v2 (CT)
        if len(js) != 1 and c is None: js = [j for j in byt.get(norm(jur), []) if j not in used]
        if len(js) == 1: gk[js[0]].append(ks)
    for j, kss in gk.items():
        if len(kss) == 1:
            for k in kss[0]: match[k] = j
            used.add(j)
    G = [None]*len(V)
    for race in races:
        S = {k: tri(race, P[race].get(k, {})) for k in keys if k in P[race]}
        vals = [[0.0,0.0,0.0] for _ in V]; alloc = [0.0]*len(V); exact = [False]*len(V)
        cty_tot = collections.defaultdict(lambda: [0,0,0]); resid = collections.defaultdict(lambda: [0,0,0]); unk = [0,0,0]
        for k, s in S.items():
            if k in match:
                j = match[k]; c = V[j][0]
                for q in range(3): vals[j][q] += s[q]
                exact[j] = True
            else:
                c = cname(k)
                if c is None or c not in byc: unk = [unk[q]+s[q] for q in range(3)]; continue
                for q in range(3): resid[c][q] += s[q]
            for q in range(3): cty_tot[c][q] += s[q]
        if sum(unk):   # MEDSL county code not in v2 (e.g. CT old counties): spread over the state's unmatched polygons by president votes
            tot = [0,0,0]
            for j in range(len(V)):
                if j not in used: tot = [tot[q]+V[j][2+q] for q in range(3)]
            per = collections.defaultdict(lambda: [0.0,0.0,0.0])
            for j in range(len(V)):
                if j not in used:
                    for q in range(3): per[V[j][0]][q] += unk[q]*V[j][2+q]/max(tot[q],1)
            for c, a in per.items():
                for q in range(3): resid[c][q] += a[q]; cty_tot[c][q] += a[q]
        for c, rs in resid.items():
            if sum(rs) == 0: continue
            js = [j for j in range(len(V)) if V[j][0] == c and j not in used] or [j for j in range(len(V)) if V[j][0] == c]
            tot = [sum(V[j][2+q] for j in js) for q in range(3)]
            for j in js:
                for q in range(3):
                    a = rs[q]*V[j][2+q]/tot[q] if tot[q] else rs[q]/len(js)
                    vals[j][q] += a
                alloc[j] += rs[2]*V[j][4]/tot[2] if tot[2] else rs[2]/len(js)
        for j in range(len(V)):
            if G[j] is None:
                g = geom(V[j][5]); G[j] = g.wkb if g is not None else None
        out = [(V[j][0], V[j][1], vals[j][0], vals[j][1], vals[j][2], G[j], alloc[j], exact[j]) for j in range(len(V))]
        pickle.dump(out, open(f'{wd}/{ab}_{race}.pkl', 'wb'))
        st_tot = [sum(s[q] for s in S.values()) for q in range(3)]
        m_tot = sum(s[2] for k, s in S.items() if k in match)
        rep[race] = {'medsl_state': st_tot, 'matched_share': round(m_tot/max(st_tot[2],1), 4), 'medsl_precincts': len(S),
                     'matched_precincts': sum(1 for k in S if k in match), 'unknown_county_votes': unk[2],
                     'counties': {c: [int(round(x)) for x in a] for c, a in cty_tot.items()},
                     'precincts': {},
                     'unmatched_by_county': {}}
        pj = collections.defaultdict(lambda: [0,0,0])
        for k, s in S.items():
            if k in match:
                for q in range(3): pj[match[k]][q] += s[q]
        rep[race]['precincts'] = {f'{V[j][0]}|{V[j][1]}|{j}': a for j, a in pj.items()}
        rep[race]['matched_polys'] = len(pj)
        um = collections.defaultdict(lambda: [0,0])
        for k, s in S.items():
            if k not in match: c = V[match[k]][0] if k in match else (cname(k) or f'fips {k[0]}'); um[c][0] += 1; um[c][1] += s[2]
        rep[race]['unmatched_by_county'] = dict(um)
        print(ab, race, 'medsl', st_tot, 'matched precincts', rep[race]['matched_precincts'], '/', len(S), 'vote share', rep[race]['matched_share'], 'v2 polys', len(V), flush=True)
    json.dump(rep, open(f'{wd}/{ab}.json', 'w'))
