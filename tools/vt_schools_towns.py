#!/usr/bin/env python3
"""Vermont 2024 school districts as exact sums of official town returns.
Returns: MEDSL 2024-elections-official vt24.csv (CC0; Vermont SOS town results; towns reported per legislative district
part are summed per town). Towns: Census 2020 county subdivisions (public domain). A school district is written only if it is
made of whole towns: every town overlapping it is >= 90 % inside it or <= 5 % (sliver, ignored), and the whole towns cover
>= 97 % of its area. Essex Junction (city since 2022) is counted with Essex town; a district containing only part of the
2020 Essex town is skipped. Gores/unorganized towns with no reporting unit contribute nothing; a district made only of them stays gray.
Result is exact (2024 flag removed: 'e24'->None, 'est'->'e20').
usage: vt_schools_towns.py <repo> <vt24.csv> <cousub shp (no ext)> [--dry]"""
import sys,json,csv,collections,re,shapefile
from shapely.geometry import shape,Polygon,MultiPolygon
repo,csvf,shp=sys.argv[1:4]; dry='--dry' in sys.argv
AB={'E.':'EAST','W.':'WEST','S.':'SOUTH','N.':'NORTH'}
V=collections.defaultdict(lambda:[0,0,0]); SKIP=('WRITE','OVER','UNDER','BLANK','SPOILED','TOTAL VOTES')
for r in csv.DictReader(open(csvf)):
  if r['office']!='US PRESIDENT' or r['writein']=='TRUE' or any(s in r['candidate'].upper() for s in SKIP): continue
  j=r['jurisdiction_name'].upper(); p=j.split(' ',1)
  if p[0] in AB: j=AB[p[0]]+' '+p[1]
  if j=='ESSEX JUNCTION': j='ESSEX'
  v=int(r['votes'] or 0); a=V[j]; a[2]+=v
  if 'HARRIS' in r['candidate'].upper(): a[0]+=v
  elif 'TRUMP' in r['candidate'].upper(): a[1]+=v
T=[]
for sr in shapefile.Reader(shp).iterShapeRecords():
  a=sr.record.as_dict(); n=a['NAMELSAD'].upper(); g=shape(sr.shape.__geo_interface__).buffer(0)
  key=next((k for k in (n, re.sub(r' (TOWN|CITY|GORE|GRANT|TOWNSHIP)$','',n)) if k in V),None)
  T.append((n,key,g))
def mp(enc,S):
  ps=[]
  for rg in enc:
    rr=[]
    for f in rg:
      o=[];x=y=0
      for k in range(0,len(f)-1,2): x+=f[k]; y+=f[k+1]; o.append((x/S,y/S))
      if len(o)>=3: rr.append(o)
    if rr:
      try: ps.append(Polygon(rr[0],rr[1:]).buffer(0))
      except Exception: pass
  from shapely.ops import unary_union
  return unary_union(ps) if ps else None
p=f"{repo}/v2/data/ussch.js"; s=open(p).read(); i=s.index('[',s.index('(')); j=s.rindex(']')+1; d=json.loads(s[i:j])
used=set(); out=[]; skipped=[]
for r in d:
  if r[0]!='Vermont': continue
  D=mp(r[2],1000)
  if D is None or D.is_empty: skipped.append((r[1],'no shape')); continue
  A=D.area; whole=[]; part=[]; cov=0
  for n,key,g in T:
    if not g.intersects(D): continue
    ia=g.intersection(D).area; f=ia/g.area
    if f>=0.9: whole.append((n,key)); cov+=ia
    elif f>0.05: part.append((n,round(f,2)))
  if part: skipped.append((r[1],'partial towns '+str(part))); continue
  if cov/A<0.97: skipped.append((r[1],f'whole-town cover {cov/A:.0%}')); continue
  vs=[V[k] for n,k in whole if k]
  if not vs or sum(v[2] for v in vs)==0: skipped.append((r[1],'no reporting town (gores only)')); continue
  val=[sum(v[q] for v in vs) for q in range(3)]
  old=r[3] if len(r)>3 else None
  while len(r)<6: r.append(None)
  fl=r[5]; r[3]=val; r[5]={'e24':None,'est':'e20'}.get(fl,fl)
  out.append((r[1],old,val,[n for n,k in whole]))
if not dry:
  while d and False: pass
  open(p,'w').write(s[:i]+json.dumps(d,separators=(',',':'))+s[j:])
for o in out: print('W',o[0],o[1],'->',o[2],len(o[3]),'towns')
for k in skipped: print('S',k)
print('written',len(out),'skipped',len(skipped))
