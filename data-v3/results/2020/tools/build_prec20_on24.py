#!/usr/bin/env python3
"""2020 presidential (adapted from data-v3/results/2016/tools/build_prec16_on24.py; input = the former v2/data/precincts2020 polygon files, copied to /workspace/prec20_orig). Original 2016 doc follows:
2016 presidential precinct votes placed onto v2's CURRENT (2024) precinct polygons. No historic geometry is stored.
Input : VEST 2016 precincts, full resolution (/workspace/vest16/geom/<ab>.pkl written by build_vest2016.py:
        (v2 county, precinct name, d, r, t, wkb); NJ/CT/RI dissolved to towns), and v2/data/precincts2024/<State>.js.
Method (same idea as data-v3/results/2022/senate: match first, area-weight otherwise):
  1. name match: a VEST precinct whose normalized name equals a 2024 polygon's name in the same county, and which has at
     least half of its area in that polygon, goes wholly to it;
  2. otherwise its votes are split over the 2024 polygons it overlaps, by overlap area / min(its overlap with all 2024
     polygons, its own area) (so parts in water or outside the 2024 file are not lost; if less than half of the precinct
     is covered, the denominator is its own area and the rest is reported as unplaced);
     shares under 3% count as 0 and over 97% as 1 (simplification slivers), the rest is renormalized.
  ≈ (6th element 1): the 2024 polygon got votes from a precinct that was split (share < 1) or from more than one precinct
  (merged). Exact: exactly one VEST precinct, wholly inside, and nothing else.
Output: v2/data/precincts2020/<State>.js and v2/data/precincts2020-DC.js, one row per row of the matching
precincts2024 file, in the same order and with the same [county, precinct] key:
  window.__prec20&&window.__prec20("<State>",[[county,precinct,d,r,t] | [county,precinct,d,r,t,1] | [county,precinct]],{"credit":...});
  [county,precinct] alone = no 2016 votes placed there (gray).
usage: build_prec20_on24.py <repo> <prec20_orig_dir> <report_json> [ab ...]"""
import sys, os, json, re, pickle, collections
from multiprocessing import Pool
import numpy as np, shapely
from shapely import wkb
from shapely.geometry import Polygon, MultiPolygon
repo, gd, rep_out = sys.argv[1:4]; only = set(sys.argv[4:])
AB = {'al':'Alabama','ak':'Alaska','az':'Arizona','ar':'Arkansas','ca':'California','co':'Colorado','ct':'Connecticut','de':'Delaware','dc':'District of Columbia','fl':'Florida','ga':'Georgia','hi':'Hawaii','id':'Idaho','il':'Illinois','in':'Indiana','ia':'Iowa','ks':'Kansas','ky':'Kentucky','la':'Louisiana','me':'Maine','md':'Maryland','ma':'Massachusetts','mi':'Michigan','mn':'Minnesota','ms':'Mississippi','mo':'Missouri','mt':'Montana','ne':'Nebraska','nv':'Nevada','nh':'New Hampshire','nj':'New Jersey','nm':'New Mexico','ny':'New York','nc':'North Carolina','nd':'North Dakota','oh':'Ohio','ok':'Oklahoma','or':'Oregon','pa':'Pennsylvania','ri':'Rhode Island','sc':'South Carolina','sd':'South Dakota','tn':'Tennessee','tx':'Texas','ut':'Utah','vt':'Vermont','va':'Virginia','wa':'Washington','wv':'West Virginia','wi':'Wisconsin','wy':'Wyoming'}
CREDIT = ("2020 president [Biden, Trump, all candidates] from v2's former 2020 precinct file (VEST 2020 / sources as credited there), "
          "placed onto v2's 2024 precinct polygons (same rows/keys as precincts2024): name match where possible, otherwise area-weighted; "
          "a 6th element 1 = ≈ (votes from a split or merged 2020 precinct). No 2020 geometry is stored.")
def dec(f, sc=10000):
    o = []; x = y = 0
    for i in range(0, len(f), 2): x += f[i]; y += f[i+1]; o.append((x/sc, y/sc))
    return o
def geom(encp):
    ps = []
    for rs in encp:
        rings = [dec(f) for f in rs if len(f) >= 6]
        if rings:
            g = Polygon(rings[0], rings[1:])
            if not g.is_valid: g = shapely.make_valid(g)
            st = [g]
            while st:
                q = st.pop()
                if hasattr(q, 'geoms'): st += list(q.geoms)
                elif q.geom_type == 'Polygon' and not q.is_empty: ps.append(q)
    if not ps: return None
    mp = MultiPolygon(ps); return mp if mp.is_valid else shapely.union_all(ps)
def norm(s):
    s = re.sub(r'\s*\(\d+\)$', '', str(s)).upper()
    s = re.sub(r'\b(PRECINCT|PRECINCTS|PCT|PREC|VOTING DISTRICT|DISTRICT|WARD|TOWNSHIP|TWP|CITY|TOWN|BOROUGH|VILLAGE|OF)\b', ' ', s)
    s = re.sub(r'[^A-Z0-9]', '', s); s = re.sub(r'^0+(?=\d)', '', s)
    return s
def job(ab):
    st = AB[ab]; fn = 'precincts2024-DC.js' if ab == 'dc' else f'precincts2024/{st.replace(" ", "_")}.js'
    t = open(f'{repo}/v2/data/{fn}').read(); i = t.index('[['); V, end = json.JSONDecoder().raw_decode(t, i)
    G = [geom(r[5]) for r in V]; okj = [j for j, g in enumerate(G) if g is not None]
    Ga = np.array([G[j] for j in okj]); tree = shapely.STRtree(Ga)
    f20 = f'{gd}/precincts2020-DC.js' if ab == 'dc' else f'{gd}/{st.replace(" ", "_")}.js'
    t2 = open(f20).read(); P0, e2 = json.JSONDecoder().raw_decode(t2, t2.index('[['))
    try: oc = json.JSONDecoder().raw_decode(t2, t2.index(',', e2) + 1)[0]
    except Exception: oc = ''
    oc = oc.get('credit', '') if isinstance(oc, dict) else str(oc); del t2
    P = []; Pgl = []
    for x in P0:
        g = geom(x[5])
        if g is None: continue
        P.append(x[:5]); Pgl.append(g)
    nogeom = [sum(x[2+q] for x in P0 if geom(x[5]) is None) for q in range(3)] if len(P) < len(P0) else [0, 0, 0]
    allv = np.array([[x[2], x[3], x[4]] for x in P0], float); del P0
    Pg = np.array(Pgl); Pv = np.array([[x[2], x[3], x[4]] for x in P], float); Pa = shapely.area(Pg)
    pi, gj = tree.query(Pg, predicate='intersects')
    try: inter = shapely.area(shapely.intersection(Pg[pi], Ga[gj]))
    except Exception:
        inter = np.zeros(len(pi))
        for k in range(len(pi)):
            try: inter[k] = shapely.area(shapely.intersection(Pg[pi[k]], Ga[gj[k]]))
            except Exception:
                try: inter[k] = shapely.area(shapely.intersection(Pg[pi[k]].buffer(0), Ga[gj[k]].buffer(0)))
                except Exception: inter[k] = 0
    by = collections.defaultdict(list)
    for k in range(len(pi)):
        if inter[k] > 0: by[pi[k]].append((okj[gj[k]], inter[k]))
    vals = np.zeros((len(V), 3)); ncon = np.zeros(len(V), int); split = np.zeros(len(V), bool)
    nm24 = collections.defaultdict(list)
    for j, r in enumerate(V): nm24[(r[0], norm(r[1]))].append(j)
    how = collections.Counter(); unplaced = np.zeros(3)
    for p in range(len(P)):
        ov = by.get(p, [])
        if not ov: unplaced += Pv[p]; how['no_overlap'] += 1; continue
        tot = sum(a for _, a in ov)
        cand = [j for j in nm24.get((P[p][0], norm(P[p][1])), []) if any(jj == j and a >= 0.5 * Pa[p] for jj, a in ov)]
        if len(cand) == 1:
            sh = {cand[0]: 1.0}; how['name'] += 1
        else:
            den = min(tot, Pa[p]) if tot >= 0.5 * Pa[p] else Pa[p]
            raw = {j: a / den for j, a in ov}; s0 = min(1.0, sum(raw.values()))
            sn = {j: (0.0 if s < 0.03 else 1.0 if s > 0.97 else s) for j, s in raw.items()}
            sn = {j: s for j, s in sn.items() if s > 0}
            if any(s == 1.0 for s in sn.values()): sn = {next(j for j, s in sn.items() if s == 1.0): 1.0}
            elif sn:
                k_ = s0 / sum(sn.values()); sn = {j: s * k_ for j, s in sn.items()}
            if not sn: unplaced += Pv[p]; how['sliver_only'] += 1; continue
            sh = sn; how['whole' if len(sh) == 1 and list(sh.values())[0] == 1.0 else 'split'] += 1
            if s0 < 1 and len(sh) > 1 or (len(sh) == 1 and list(sh.values())[0] < 1): unplaced += Pv[p] * (1 - sum(sh.values()))
        for j, s in sh.items():
            vals[j] += Pv[p] * s; ncon[j] += 1
            if s < 1: split[j] = True
    rows = []; ex = apx = gray = 0; exv = 0.0
    for j, r in enumerate(V):
        if ncon[j] == 0: rows.append([r[0], r[1]]); gray += 1; continue
        v = [int(round(x)) for x in vals[j]]
        if ncon[j] == 1 and not split[j]: rows.append([r[0], r[1]] + v); ex += 1; exv += vals[j][2]
        else: rows.append([r[0], r[1]] + v + [1]); apx += 1
    out = f'{repo}/v2/data/precincts2020-DC.js' if ab == 'dc' else f'{repo}/v2/data/precincts2020/{st.replace(" ", "_")}.js'
    body = 'window.__prec20&&window.__prec20(' + json.dumps(st) + ',' + json.dumps(rows, separators=(',', ':'), ensure_ascii=False) + ',' + json.dumps({'credit': CREDIT + ' Original 2020 source credit: ' + oc}, ensure_ascii=False) + ');'
    open(out, 'w').write(body)
    vt = allv.sum(0); placed = [sum(x[2+q] for x in rows if len(x) > 2) for q in range(3)]
    return st, {'file': os.path.relpath(out, repo), 'bytes': os.path.getsize(out), 'precincts_2020': len(P), 'polygons_2024': len(V),
                'exact': ex, 'approx': apx, 'gray': gray, 'how': dict(how), 'drt_2020': [int(x) for x in vt], 'placed': placed,
                'exact_vote_share': round(exv / max(vt[2], 1), 4), 'unplaced': [int(round(x)) for x in unplaced], 'no_geom_2020': nogeom}
if __name__ == '__main__':
    abs_ = sorted(a for a in AB if (not only or a in only) and os.path.exists((f'{gd}/precincts2020-DC.js' if a == 'dc' else f'{gd}/{AB[a].replace(" ", "_")}.js')))
    rep = json.load(open(rep_out)) if os.path.exists(rep_out) else {}
    with Pool(int(os.environ.get('NP', '2')), maxtasksperchild=1) as pool:
        for st, r in pool.imap_unordered(job, abs_):
            rep[st] = r; print(st, r['bytes'], r['exact'], r['approx'], r['gray'], r['exact_vote_share'], r['how'], 'D/R/T', r['drt_2020'], r['placed'], flush=True)
    json.dump(rep, open(rep_out, 'w'), indent=1, sort_keys=True)
