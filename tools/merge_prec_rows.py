# merge rows of a 2024 precinct file into one (union of shapes, summed votes): merge_rows.py State County "name1,name2" "New name"
import json,sys
from shapely.ops import unary_union
sys.argv+=[]
A='/workspace/w/us-districts-app/'
st,c,ns,new=sys.argv[1:5]; ns=ns.split(',')
fn=f"{A}data/precincts2024/{st.replace(' ','_')}.js"; t=open(fn).read(); data,credit=json.loads('['+t[t.index(',')+1:t.rindex(');')]+']')
from shapely.geometry import Polygon,MultiPolygon
def mp(enc,S=10000):
  ps=[]
  for rg in enc:
    rr=[]
    for f in rg:
      o=[];x=y=0
      for k in range(0,len(f)-1,2): x+=f[k]; y+=f[k+1]; o.append((x/S,y/S))
      if len(o)>=3: rr.append(o)
    if rr: ps.append(Polygon(rr[0],rr[1:]).buffer(0))
  return unary_union(ps)
S=10000
def enc(ring):
  out=[];px=py=0
  for x,y in ring:
    X=round(x*S);Y=round(y*S); out+=[X-px,Y-py]; px,py=X,Y
  return out
def encg(g):
  polys=[g] if g.geom_type=='Polygon' else [q for q in g.geoms if q.geom_type=='Polygon']
  return [[enc(list(q.exterior.coords))]+[enc(list(i.coords)) for i in q.interiors if i.length>0.001] for q in polys if q.area>0]
sel=[r for r in data if r[0]==c and r[1] in ns]; assert len(sel)==len(ns),sel
g=unary_union([mp(r[5]) for r in sel]).buffer(0)
row=[c,new,sum(r[2] for r in sel),sum(r[3] for r in sel),sum(r[4] for r in sel),encg(g)]
data=[r for r in data if not(r[0]==c and r[1] in ns)]+[row]
open(fn,'w').write('__prec('+json.dumps(st)+','+json.dumps(data,separators=(',',':'))+','+json.dumps(credit,separators=(',',':'))+');'); print(row[:5])
