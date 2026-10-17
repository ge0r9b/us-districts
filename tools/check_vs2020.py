# after a county rebuild: pair each 2024 row with the 2020 row of max overlap; print turnout ratios and R-share shifts
import json,sys,subprocess
sys.path.insert(0,'/workspace/w/us-districts-app/tools')
from shapely.geometry import Polygon,MultiPolygon
A='/workspace/w/us-districts-app/'
def ld(y,st):
  s=open(f"{A}data/precincts{y}/{st.replace(' ','_')}.js").read(); return json.loads('['+s[s.index(',')+1:s.rindex(');')]+']')[0]
def mp(enc,S=10000):
  ps=[]
  for rg in enc:
    rr=[]
    for f in rg:
      o=[];x=y=0
      for k in range(0,len(f)-1,2): x+=f[k]; y+=f[k+1]; o.append((x/S,y/S))
      if len(o)>=3: rr.append(o)
    if rr: ps.append(Polygon(rr[0],rr[1:]))
  g=MultiPolygon(ps); return g if g.is_valid else g.buffer(0)
st=sys.argv[1]; cs=sys.argv[2].split(',')
N=ld('2024',st); O=ld('2020',st)
for c in cs:
  n=[(r,mp(r[5])) for r in N if r[0]==c]; o=[(r,mp(r[5])) for r in O if r[0]==c]
  bad=0
  for r,g in n:
    best=max(o,key=lambda q:q[1].intersection(g).area) if o else None
    if not best: continue
    q=best[0]; ov=best[1].intersection(g).area/max(g.area,1e-12)
    rt=r[4]/max(1,q[4]); sh=r[3]/max(1,r[4])-q[3]/max(1,q[4])
    flag= (not 0.7<=rt<=1.4 and r[4]>100) or abs(sh)>0.12 or ov<0.8
    bad+=flag
    if flag or '-v' in sys.argv: print(f"  {'!!' if flag else '  '} {c} | {r[1]} <- {q[1]}  t {r[4]}/{q[4]}={rt:.2f}  Rshift {sh:+.3f} ov {ov:.2f}")
  print(c,'rows',len(n),'flagged',bad)
