#!/usr/bin/env python3
"""2016 values for v2's layers, from the VEST 2016 precinct geometries written by build_vest2016.py (/workspace/vest16/geom/<st>.pkl).
Triples [d,r,t] = [Clinton, Trump, all presidential candidates].
- states: FEC Federal Elections 2016, Table 2 (exact).
- counties: sum of the precincts assigned to each v2 county (exact precinct sums; county = representative point).
- ushouse / senate / statehouse / schools: precinct votes area-weighted into v2's current district shapes (uscd.js, ussldu.js, ussldl.js, ussch.js).
  A 4th element 1 (= est, shown with ≈) is added when more than 2% of a district's total comes from precincts split by the district line.
  A district is left out (gray, no data) when 2016 precincts cover less than 50% of its area.
usage: build_layers2016.py <repo> <geom_dir> <fec2016.xlsx> <out_dir>"""
import sys,os,json,pickle,glob,collections
import numpy as np, shapely, openpyxl
from shapely import wkb
from shapely.geometry import Polygon,MultiPolygon
repo,gd,fecx,od=sys.argv[1:5]
AB={'al':'Alabama','ak':'Alaska','az':'Arizona','ar':'Arkansas','ca':'California','co':'Colorado','ct':'Connecticut','de':'Delaware','dc':'District of Columbia','fl':'Florida','ga':'Georgia','hi':'Hawaii','id':'Idaho','il':'Illinois','in':'Indiana','ia':'Iowa','ks':'Kansas','ky':'Kentucky','la':'Louisiana','me':'Maine','md':'Maryland','ma':'Massachusetts','mi':'Michigan','mn':'Minnesota','ms':'Mississippi','mo':'Missouri','mt':'Montana','ne':'Nebraska','nv':'Nevada','nh':'New Hampshire','nj':'New Jersey','nm':'New Mexico','ny':'New York','nc':'North Carolina','nd':'North Dakota','oh':'Ohio','ok':'Oklahoma','or':'Oregon','pa':'Pennsylvania','ri':'Rhode Island','sc':'South Carolina','sd':'South Dakota','tn':'Tennessee','tx':'Texas','ut':'Utah','vt':'Vermont','va':'Virginia','wa':'Washington','wv':'West Virginia','wi':'Wisconsin','wy':'Wyoming'}
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
      stack=[g]
      while stack:
        q=stack.pop()
        if hasattr(q,'geoms'): stack+=list(q.geoms)
        elif q.geom_type=='Polygon': ps.append(q)
  ps=[p for p in ps if not p.is_empty and p.geom_type=='Polygon']
  if not ps: return None
  mp=MultiPolygon(ps)
  return mp if mp.is_valid else shapely.union_all(ps)
def rows_of(path):
  t=open(path).read(); i=t.index('[['); return json.JSONDecoder().raw_decode(t,i)[0]
LAYERS={'ushouse':'v2/data/uscd.js','senate':'v2/data/ussldu.js','statehouse':'v2/data/ussldl.js','schools':'v2/data/ussch.js'}
P={}
for f in glob.glob(gd+'/*.pkl'):
  ab=os.path.basename(f)[:2]; P[AB[ab]]=pickle.load(open(f,'rb'))
out={}; rep={}
# states (FEC)
ws=openpyxl.load_workbook(fecx,read_only=True)['Table 2. Electoral &  Pop Vote']
AB2={k.upper():v for k,v in AB.items()}
out['states']={}
for r in ws.iter_rows(values_only=True):
  k=str(r[0]).rstrip('*') if r[0] else None
  if k in AB2: out['states'][AB2[k]]=[r[4],r[3],r[6]]
# counties (exact precinct sums)
cty=collections.defaultdict(lambda:[0,0,0])
for st,rows in P.items():
  for cn,nm,d,rp,t,_ in rows:
    a=cty[st+'|'+cn]; a[0]+=d;a[1]+=rp;a[2]+=t
out['counties']=dict(cty)
# districts
PG={st:(np.array([shapely.make_valid(wkb.loads(x[5])) for x in rows]),np.array([[x[2],x[3],x[4]] for x in rows],dtype=float)) for st,rows in P.items()}
for st,(g,_) in PG.items():
  shapely.prepare(g)
TREE={st:shapely.STRtree(g) for st,(g,_) in PG.items()}
AREA={st:shapely.area(g) for st,(g,_) in PG.items()}
ONLY=os.environ.get('LAYERS','').split(',') if os.environ.get('LAYERS') else list(LAYERS)
os.makedirs(od+'/cache',exist_ok=True)
for lay,path in LAYERS.items():
  if lay not in ONLY:
    if os.path.exists(f'{od}/cache/{lay}.json'): out[lay],rep[lay]=json.load(open(f'{od}/cache/{lay}.json'))
    continue
  rows=rows_of(f'{repo}/{path}'); res={}; miss=[]; est=0
  for row in rows:
    st,nm=row[0],row[1]
    if st not in PG: miss.append((st,nm,'no 2016 precincts for state')); continue
    D=geom(row[2])
    if D is None: miss.append((st,nm,'no district shape')); continue
    idx=TREE[st].query(D,predicate='intersects')
    if len(idx)==0: miss.append((st,nm,'no precinct overlap')); continue
    g,v=PG[st]
    try: inter=shapely.area(shapely.intersection(g[idx],D))
    except Exception:
      Dv=D.buffer(0); inter=[]
      for q in g[idx]:
        try: inter.append(shapely.area(shapely.intersection(q,Dv)))
        except Exception:
          try: inter.append(shapely.area(shapely.intersection(q.buffer(0),Dv)))
          except Exception: inter.append(0.0)
      inter=np.array(inter)
    fr=np.clip(inter/np.maximum(AREA[st][idx],1e-15),0,1)
    cover=inter.sum()/max(D.area,1e-15)
    if cover<0.5: miss.append((st,nm,f'precinct cover {cover:.0%}')); continue
    vals=(v[idx]*fr[:,None]).sum(0)
    split=(fr>0.01)&(fr<0.99); sv=(v[idx][split,2]*fr[split]).sum()
    tr=[int(round(x)) for x in vals]
    if tr[2]<=0: miss.append((st,nm,'no votes')); continue
    if sv>0.02*vals[2]: tr.append(1); est+=1
    res[st+'|'+nm]=tr
  out[lay]=res; rep[lay]={'districts':len(rows),'filled':len(res),'est':est,'gray':len(miss),'gray_items':miss}
  json.dump([res,rep[lay]],open(f'{od}/cache/{lay}.json','w'))
  print(lay,len(rows),'filled',len(res),'est',est,'gray',len(miss),flush=True)
os.makedirs(od,exist_ok=True)
J=lambda o: json.dumps(o,separators=(',',':'))
if all(k in out for k in LAYERS): open(f'{od}/election2016.js','w').write('window.ELECTION2016='+J(out['counties'])+';')
if all(k in out for k in LAYERS): open(f'{od}/ds2016.js','w').write('window.__ds2016&&window.__ds2016('+J({k:out[k] for k in ('states','ushouse','senate','statehouse','schools')})+');')
if all(k in out for k in LAYERS): json.dump(rep,open(f'{od}/../layers_report.json','w'),indent=0)
