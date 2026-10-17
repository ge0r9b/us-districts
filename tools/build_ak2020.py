#!/usr/bin/env python3
"""Alaska 2020: precinct file, borough/census-area totals and 2024-boundary House/Senate district totals.
Source: VEST 2020 Alaska precinct boundaries and results (Harvard Dataverse doi:10.7910/DVN/K7760H, CC BY 4.0).
VEST took the official Division of Elections precinct returns and distributed the absentee, early and question
ballots (reported by House district only) to the precincts of each district by candidate; statewide totals equal the
official result (Biden 153,778, Trump 189,951). Precinct figures are therefore estimates.
Boroughs and 2024 House districts: each precinct's votes are split by the share of its land area in each unit (shares normalised to 1, so every vote is counted once)
(Alaska Albers, EPSG:3338). Senate = sum of its two House districts. All flagged as estimates.
usage: build_ak2020.py <vest_dir> <repo_dir>"""
import sys,json,collections,shapefile
from shapely.geometry import shape,Polygon,MultiPolygon
from shapely.ops import transform
from shapely.strtree import STRtree
from pyproj import Transformer
vd,repo=sys.argv[1],sys.argv[2]
tf=Transformer.from_crs(4326,3338,always_xy=True).transform
F=['G20PRERTRU','G20PREDBID','G20PRELJOR','G20PREGVEN','G20PRECBLA','G20PREADEL','G20PREIPIE']
cr=shapefile.Reader(vd+'/cty/cb_2020_us_county_500k'); B=[];BN=[]
for sr in cr.shapeRecords():
  rec=sr.record.as_dict()
  if rec['STATEFP']!='02': continue
  g=shape(sr.shape.__geo_interface__); B.append(g); BN.append(rec['NAMELSAD'])
BP=[transform(tf,g).buffer(0) for g in B]; bt=STRtree(B)
s=open(repo+'/v2/data/ussldl.js').read(); i0=s.index('[',s.index('(')); j0=s.rindex(']')+1; SL=json.loads(s[i0:j0])
def dec(enc):
  ps=[]
  for rs in enc:
    rings=[]
    for f in rs:
      o=[];x=y=0
      for k in range(0,len(f),2): x+=f[k]; y+=f[k+1]; o.append((x/1000,y/1000))
      rings.append(o)
    try: ps.append(Polygon(rings[0],rings[1:]))
    except Exception: pass
  return MultiPolygon(ps).buffer(0)
HD=[(str(int(r[1])),dec(r[2])) for r in SL if r[0]=='Alaska']; HP=[transform(tf,g).buffer(0) for _,g in HD]; ht=STRtree([g for _,g in HD])
S=10000
def enc(ring):
  out=[];px=py=0
  for x,y in ring:
    X=round(x*S);Y=round(y*S); out+=[X-px,Y-py]; px,py=X,Y
  return out
R=shapefile.Reader(vd+'/x_ak/ak_2020'); rows=[]; boro=collections.defaultdict(lambda:[0.0,0.0,0.0]); hd=collections.defaultdict(lambda:[0.0,0.0,0.0])
for sr in R.shapeRecords():
  rec=sr.record.as_dict(); g=shape(sr.shape.__geo_interface__).buffer(0)
  if g.is_empty: continue
  d=rec['G20PREDBID']; rp=rec['G20PRERTRU']; t=sum(rec[f] or 0 for f in F)
  p=g.representative_point(); idx=[i for i in bt.query(p) if B[i].contains(p)]
  cn=BN[idx[0]] if idx else BN[min(range(len(B)),key=lambda i:B[i].distance(p))]
  gp=transform(tf,g); A=gp.area or 1
  # shares of the precinct's land area (cartographic shapes exclude water) in each unit, normalised to sum to 1
  for idx,PP,NN,acc in ((bt.query(g),BP,BN,boro),(ht.query(g),HP,[h[0] for h in HD],hd)):
    ov=[(NN[i],gp.intersection(PP[i]).area) for i in idx]; ov=[(n,a) for n,a in ov if a>0]; sa=sum(a for _,a in ov)
    if not sa: ov=[(NN[min(range(len(PP)),key=lambda i:PP[i].distance(gp))],1.0)]; sa=1.0
    for n,a in ov: f=a/sa; x=acc[n]; x[0]+=d*f; x[1]+=rp*f; x[2]+=t*f
  gs=g.simplify(0.0004,preserve_topology=True)
  polys=[gs] if gs.geom_type=='Polygon' else [q for q in gs.geoms if q.geom_type=='Polygon']
  P=[[enc(list(q.exterior.coords))]+[enc(list(i.coords)) for i in q.interiors if i.length>0.002] for q in polys if q.area>0]
  if P and t>0: rows.append([cn,rec['NAME'],d,rp,t,P])
credit="Voting and Election Science Team (VEST), 2020 General Election precinct boundaries and results for Alaska (official Division of Elections returns; absentee, early and question ballots reported by House district were distributed to that district's precincts by VEST), Harvard Dataverse doi:10.7910/DVN/K7760H, CC BY 4.0. Precinct figures are estimates; county = borough/census area containing the precinct."
open(repo+'/data/precincts2020/Alaska.js','w').write('__prec("Alaska",'+json.dumps(rows,separators=(',',':'))+','+json.dumps(credit)+');')
rnd=lambda v:[round(x) for x in v]
p=repo+'/v2/data/ak.js'; t=open(p).read(); pre,body=t.split('=',1); AK=json.loads(body.strip().rstrip(';'))
AK['boro2020']={k:rnd(v) for k,v in sorted(boro.items())}
AK['hd2020']={k:rnd(hd[k]) for k in sorted(hd,key=int)}
AK['boroNote2020']="2020 borough/census-area and House-district figures: VEST 2020 precinct results (official returns, district-level absentee/early/question ballots distributed by VEST), split by the share of each precinct's area in the unit. Estimates."
AK['src']=AK['src']+"; 2020 precincts, boroughs and 2024-boundary districts: VEST 2020 (CC BY 4.0)"
open(p,'w').write(pre+'='+json.dumps(AK,separators=(',',':'))+';')
# keep the district file in step with what the app shows (2020 = area-weighted, estimate)
for r in SL:
  if r[0]!='Alaska': continue
  v=hd.get(str(int(r[1])))
  if v: r[4]=rnd(v); r[5:]=['e20']
open(repo+'/v2/data/ussldl.js','w').write(s[:i0]+json.dumps(SL,separators=(',',':'))+s[j0:])
s=open(repo+'/v2/data/ussldu.js').read(); i0=s.index('[',s.index('(')); j0=s.rindex(']')+1; SU=json.loads(s[i0:j0])
for r in SU:
  if r[0]!='Alaska': continue
  k=ord(r[1].lstrip('0')[0])-65; a,b=AK['hd2020'].get(str(2*k+1)),AK['hd2020'].get(str(2*k+2))
  if a and b: r[4]=[a[0]+b[0],a[1]+b[1],a[2]+b[2]]; r[5:]=['e20']
open(repo+'/v2/data/ussldu.js','w').write(s[:i0]+json.dumps(SU,separators=(',',':'))+s[j0:])
tot=[sum(r[i] for r in rows) for i in (2,3,4)]
print(len(rows),'precincts',tot,'boro sum',rnd([sum(v[i] for v in boro.values()) for i in range(3)]),'hd sum',rnd([sum(v[i] for v in hd.values()) for i in range(3)]),len(boro),len(hd))
