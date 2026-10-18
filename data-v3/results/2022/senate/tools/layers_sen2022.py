#!/usr/bin/env python3
"""Area-weight the Senate polygons (build_sen2022.py pickles) into v2's current district shapes.
usage: layers_sen2022.py <repo> <work_dir>   -> <work_dir>/layers_<race>.json  {layer: {"State|Name": [d,r,t] or [d,r,t,1]}}
A polygon's share = its overlap with the district / min(its overlap with all districts of the layer, its area); shares under 3% / over 97% count as 0 / 1 (simplification slivers).
≈ (4th element 1) when more than 2% of the district total comes from polygons split by the district line, or from votes
allocated to polygons without a matched precinct. Gray (left out) when the polygons cover < 50% of the district's area."""
import sys, os, json, pickle, glob, collections
from multiprocessing import Pool
import numpy as np, shapely
from shapely import wkb
sys.path.insert(0, os.path.dirname(__file__)); from races22 import *
from shapely.geometry import Polygon, MultiPolygon
repo, wd = sys.argv[1:3]
LAYERS = {'ushouse':'v2/data/uscd.js','senate':'v2/data/ussldu.js','statehouse':'v2/data/ussldl.js','schools':'v2/data/ussch.js'}
def dec(f,sc=1000):
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
def rows_of(path):
    t=open(path).read(); i=t.index('[['); return json.JSONDecoder().raw_decode(t,i)[0]
DROWS = {lay: rows_of(f'{repo}/{p}') for lay, p in LAYERS.items()}
def job(args):
    pk, = args
    ab, race = os.path.basename(pk)[:-4].split('_'); st = NAME[ab]
    rows = [x for x in pickle.load(open(pk,'rb')) if x[5] is not None]
    g = np.array([shapely.make_valid(wkb.loads(x[5])) for x in rows]); v = np.array([[x[2],x[3],x[4]] for x in rows], float)
    al = np.array([x[6] for x in rows], float); area = shapely.area(g); tree = shapely.STRtree(g)
    res = collections.defaultdict(dict); gray = collections.defaultdict(list)
    for lay, drows in DROWS.items():
        pend = []; tot_ov = np.zeros(len(g))
        for row in drows:
            if row[0] != st: continue
            nm = row[1]; D = geom(row[2])
            if D is None: gray[lay].append((nm,'no shape')); continue
            idx = tree.query(D, predicate='intersects')
            if len(idx) == 0: gray[lay].append((nm,'no overlap')); continue
            try: inter = shapely.area(shapely.intersection(g[idx], D))
            except Exception:
                Dv = D.buffer(0); inter = []
                for q in g[idx]:
                    try: inter.append(shapely.area(shapely.intersection(q, Dv)))
                    except Exception:
                        try: inter.append(shapely.area(shapely.intersection(q.buffer(0), Dv)))
                        except Exception: inter.append(0.0)
                inter = np.array(inter)
            inter = np.asarray(inter, float); np.add.at(tot_ov, idx, inter); pend.append((nm, idx, inter, D.area))
        # 2022 change vs 2024: a polygon's share in a district = its overlap with that district / its overlap with all districts of
        # the layer, capped at its own area (school layers overlap: elementary + secondary), so polygon parts outside every simplified district shape (coast, water, AK) are not lost
        for nm, idx, inter, darea in pend:
            fr = np.clip(inter/np.maximum(np.minimum(tot_ov[idx], area[idx]), 1e-15),0,1); cover = inter.sum()/max(darea,1e-15)
            fr = np.where(fr < 0.03, 0.0, np.where(fr > 0.97, 1.0, fr))   # simplification slivers (~40 m) are not splits
            if cover < 0.5: gray[lay].append((nm, f'cover {cover:.0%}')); continue
            vals = (v[idx]*fr[:,None]).sum(0)
            split = (fr>0)&(fr<1); sv = (v[idx][split,2]*fr[split]).sum(); av = (al[idx]*fr).sum()
            # d, r and all-others are area-weighted and rounded separately; t = their sum, so all-others is never negative
            vo = (np.maximum(v[idx,2]-v[idx,0]-v[idx,1], 0)*fr).sum()
            tr = [int(round(vals[0])), int(round(vals[1]))]; tr.append(tr[0] + tr[1] + int(round(vo)))
            if tr[2] <= 0: gray[lay].append((nm,'no votes')); continue
            if sv > 0.02*vals[2] or av > 0.02*vals[2]: tr.append(1)
            res[lay][f'{st}|{nm}'] = tr
    return race, dict(res), dict(gray), st
if __name__ == '__main__':
    pks = sorted(glob.glob(f'{wd}/*_regular.pkl') + glob.glob(f'{wd}/*_special.pkl') + glob.glob(f'{wd}/*_runoff.pkl'))
    out = collections.defaultdict(lambda: collections.defaultdict(dict)); gr = collections.defaultdict(lambda: collections.defaultdict(dict))
    with Pool(int(os.environ.get('NP','6'))) as p:
        for race, res, gray, st in p.imap_unordered(job, [(x,) for x in pks]):
            for lay in LAYERS:
                out[race][lay].update(res.get(lay, {})); gr[race][lay][st] = gray.get(lay, [])
            print('done', st, race, {l: len(res.get(l,{})) for l in LAYERS}, flush=True)
    for race in out: json.dump({'values': out[race], 'gray': gr[race]}, open(f'{wd}/layers_{race}.json','w'))
