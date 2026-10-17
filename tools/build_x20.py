#!/usr/bin/env python3
"""2020 estimates for 2024 precincts that have no same-name-and-shape 2020 precinct (the "'20 n/a" rows).
Areal interpolation: each 2020 precinct p (data/precincts2020/<State>.js) gives a 2024 precinct q the share
area(p & q) / area(p) of its Biden, Trump and total votes. Only written when 2020 precincts cover at least half of
q's area (same 50 % rule as the town area-weighting). Output v2/data/x20/<State>.js:
window.__x20("State",{"<county>|<precinct name>":[biden,trump,total],...}). Rows are shown with the ≈ mark.
usage: build_x20.py <repo_dir> [State ...]"""
import sys,os,json,glob
from shapely.geometry import Polygon,MultiPolygon
from shapely.strtree import STRtree
from multiprocessing import Pool
repo=sys.argv[1]
def ld(p):
  t=open(p).read(); a=json.loads('['+t[t.index(',')+1:t.rindex(');')]+']'); return a[0]
def ghash(e):
  h=0
  for rg in e:
    for r in rg:
      for v in r: h=(h*31+v)&0xffffffff
  return h-(1<<32) if h>=1<<31 else h
def geom(e):
  ps=[]
  for rg in e:
    rings=[]
    for f in rg:
      o=[];x=y=0
      for k in range(0,len(f)-1,2): x+=f[k]; y+=f[k+1]; o.append((x/10000,y/10000))
      if len(o)>=3: rings.append(o)
    if rings:
      try: ps.append(Polygon(rings[0],rings[1:]))
      except Exception: pass
  g=MultiPolygon(ps) if ps else None
  if g is not None and not g.is_valid: g=g.buffer(0)
  return g
def run(st):
  f20=f'{repo}/data/precincts2020/{st.replace(" ","_")}.js'; f24=f'{repo}/data/precincts2024/{st.replace(" ","_")}.js'
  if not (os.path.exists(f20) and os.path.exists(f24)): return st,0,0,0
  P20=ld(f20); P24=ld(f24)
  keys={(r[0],r[1],ghash(r[5])) for r in P20 if r[4]}
  G=[];V=[]
  for r in P20:
    if not r[4]: continue
    g=geom(r[5])
    if g is None or g.is_empty or g.area<=0: continue
    G.append(g); V.append((r[2],r[3],r[4],g.area))
  T=STRtree(G); out={}; n=0; low=0
  for r in P24:
    if not r[4] or (r[0],r[1],ghash(r[5])) in keys: continue
    n+=1; q=geom(r[5])
    if q is None or q.is_empty or q.area<=0: low+=1; continue
    acc=[0.0,0.0,0.0]; cov=0.0
    for i in T.query(q):
      try: a=G[i].intersection(q).area
      except Exception: continue
      if a<=0: continue
      cov+=a; f=a/V[i][3]
      for j in range(3): acc[j]+=V[i][j]*f
    if cov/q.area<0.5 or acc[2]<0.5: low+=1; continue
    out[r[0]+'|'+r[1]]=[round(acc[0]),round(acc[1]),max(1,round(acc[2]))]
  os.makedirs(f'{repo}/v2/data/x20',exist_ok=True)
  open(f'{repo}/v2/data/x20/{st.replace(" ","_")}.js','w').write('window.__x20&&window.__x20('+json.dumps(st)+','+json.dumps(out,separators=(',',':'),ensure_ascii=False)+');')
  return st,n,len(out),low
if __name__=='__main__':
  sts=sys.argv[2:] or sorted(os.path.basename(p)[:-3].replace('_',' ') for p in glob.glob(f'{repo}/data/precincts2024/*.js'))
  with Pool(6) as pool:
    for st,n,k,low in pool.imap_unordered(run,sts): print(f'{st}: unmatched 2024 precincts {n}, estimated {k}, left n/a (2020 cover <50%) {low}',flush=True)
