#!/usr/bin/env python3
"""Connecticut 2020 at town level, in the app's planning-region geography.
Source: VEST 2020 CT precinct results (Harvard Dataverse doi:10.7910/DVN/K7760H, CC BY 4.0; VEST took the official
CT Secretary of the State town/precinct returns). Precincts (NAME20 'Town 004-00') are summed per town.
Each town row reuses the 2024 town polygon of data/precincts2024/Connecticut.js verbatim (town boundaries did not
change), so the app's same-name-and-shape rule pairs 2020 and 2024 for every town. Towns missing from the 2024 file
(Cheshire, Naugatuck) get the dissolved VEST shape. Also writes the 9 planning-region totals into data/election2020.js.
usage: build_ct2020.py <vest_dir> <repo_dir>"""
import sys,json,re,collections,shapefile
from shapely.geometry import shape
from shapely.ops import unary_union
vd,repo=sys.argv[1],sys.argv[2]
s=open(repo+'/data/precincts2024/Connecticut.js').read(); a=json.loads('['+s[s.index(',')+1:s.rindex(');')]+']'); r24=a[0]
code2reg={}; town={}
for r in r24:
  c,t=r[1].split('-',1); code2reg[c]=r[0]; town[t]=(r[0],r[1],r[5])
EXTRA={'Cheshire':'170','Naugatuck':'140'}  # Census 2022 planning-region county codes (09170 South Central, 09140 Naugatuck Valley)
F=['G20PREDBID','G20PRERTRU','G20PRELJOR','G20PREGHAW','G20PREOWRI']
R=shapefile.Reader(vd+'/x_ct/ct_2020'); T=collections.defaultdict(lambda:[0,0,0]); G=collections.defaultdict(list)
for sr in R.shapeRecords():
  rec=sr.record.as_dict(); nm=re.sub(r'\s+\d{3}-\d{2}$','',rec['NAME20']).strip(); t=T[nm]
  t[0]+=rec['G20PREDBID']; t[1]+=rec['G20PRERTRU']; t[2]+=sum(rec[f] for f in F)
  if nm in EXTRA: G[nm].append(shape(sr.shape.__geo_interface__))
S=10000
def enc(ring):
  out=[];px=py=0
  for x,y in ring:
    X=round(x*S);Y=round(y*S); out+=[X-px,Y-py]; px,py=X,Y
  return out
rows=[]
for nm,(d,rp,tt) in sorted(T.items()):
  if nm in town: reg,label,P=town[nm]
  else:
    reg=code2reg[EXTRA[nm]]; label=EXTRA[nm]+'-'+nm; g=unary_union(G[nm]).simplify(0.0004,preserve_topology=True)
    polys=[g] if g.geom_type=='Polygon' else list(g.geoms); P=[[enc(list(q.exterior.coords))] for q in polys if q.area>0]
  rows.append([reg,label,d,rp,tt,P])
credit="Voting and Election Science Team (VEST), 2020 General Election precinct results for Connecticut (official CT Secretary of the State returns), Harvard Dataverse doi:10.7910/DVN/K7760H, CC BY 4.0; summed by town and placed in the 2024 town shapes (town boundaries unchanged)."
open(repo+'/data/precincts2020/Connecticut.js','w').write('__prec("Connecticut",'+json.dumps(rows,separators=(',',':'))+','+json.dumps(credit)+');')
reg=collections.defaultdict(lambda:[0,0,0])
for r in rows:
  g=reg[r[0]]; g[0]+=r[2]; g[1]+=r[3]; g[2]+=r[4]
p=repo+'/data/election2020.js'; t=open(p).read(); pre,body=t.split('=',1); E=json.loads(body.strip().rstrip(';'))
for k,v in reg.items(): E['Connecticut|'+k]=v
open(p,'w').write(pre+'='+json.dumps(E,separators=(',',':'))+';')
print(len(rows),'towns',dict(reg),'state',[sum(v[i] for v in reg.values()) for i in range(3)])
