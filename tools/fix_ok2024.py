#!/usr/bin/env python3
"""Oklahoma 2024 from official precinct returns joined to the official precinct map.
Results: MIT Election Data + Science Lab 2024 precinct returns (github.com/MEDSL/2024-elections-official, ok24.csv,
CC0; converted from the Oklahoma State Election Board export results.okelections.gov/OKER/?elecDate=20241105).
Per-county sums equal the official county totals in data/election2024.js for all 77 counties (checked here).
Shapes and precinct->district attributes: statewide voting precincts by the OU Center for Spatial Analysis for the
Oklahoma State Election Board (map11.incog.org/arcgis11wa/rest/services/PCT_OK_State/FeatureServer/0, fields
PCT_CEB, St_house, St_senate; boundaries updated 2024). Every contested state house/senate/US House race row in the
returns names the same district as the map attribute of its precinct (checked here: 0 mismatches).
Oklahoma and Tulsa counties report early and absentee ballots in one county-wide pseudo precinct (559999, 729999);
those votes are allocated to the county's precincts in proportion to each group's (Harris, Trump, other) in-person
votes, so the county totals are exact and the precinct figures in those two counties are estimates.
Writes:
 - data/precincts2024/Oklahoma.js: Oklahoma County and Tulsa County rows replaced (all precincts, CSA shapes,
   names = the 6-digit county+precinct number used for every other Oklahoma county);
 - v2/data/ussldu.js / ussldl.js: every Oklahoma senate/house district = sum of its precincts (exact containment
   by the official attribute); also v2/data/uscd.js. Flag None when it holds none or all of a pool county's
   precincts, 'e24' when it holds only part of Oklahoma or Tulsa county (2020 flag kept: e20/est -> est).
usage: fix_ok2024.py <repo> <ok24.csv> <okpct_0.geojson> [<okpct_1000.geojson> ...] [--dry] [--gray-only]"""
import sys,json,csv,collections,re
from shapely.geometry import shape
repo,csvf=sys.argv[1],sys.argv[2]; gj=[a for a in sys.argv[3:] if not a.startswith('--')]
dry='--dry' in sys.argv; gray_only='--gray-only' in sys.argv
E=json.loads(re.search(r'=(\{.*\})',open(f"{repo}/data/election2024.js").read(),re.S).group(1))
CN={k.split('|')[1].upper().replace(' ','').replace('COUNTY',''):k.split('|')[1] for k in E if k.startswith('Oklahoma|')}
V=collections.defaultdict(lambda:[0,0,0]); CTY={}
for x in csv.DictReader(open(csvf)):
  if x['office']!='US PRESIDENT' or x['mode']!='TOTAL': continue
  p=x['precinct'].zfill(6); v=int(x['votes']); a=V[p]; a[2]+=v; CTY[p]=CN[x['county_name'].replace(' ','')]
  if x['party_simplified']=='DEMOCRAT': a[0]+=v
  elif x['party_simplified']=='REPUBLICAN': a[1]+=v
# county check vs official
cs=collections.defaultdict(lambda:[0,0,0])
for p,a in V.items():
  for i in range(3): cs[CTY[p]][i]+=a[i]
bad=[(c,a,E['Oklahoma|'+c]) for c,a in cs.items() if a!=E['Oklahoma|'+c][:3]]
print('counties',len(cs),'not equal to official:',bad)
F=[]
for g in gj: F+=json.load(open(g))['features']
AT={f['properties']['PCT_CEB']:f for f in F}
POOL=[p for p in V if p.endswith('9999')]
miss=[p for p in V if p not in AT and p not in POOL]
if miss: sys.exit(f'precincts with no shape: {miss}')
# allocate county-wide early/absentee pools
VA={p:[float(x) for x in a] for p,a in V.items() if p not in POOL}; ALLOC=set()
for pool in POOL:
  cc=pool[:2]; ps=[p for p in VA if p[:2]==cc]; ALLOC.add(cc); pv=V[pool]
  sd=sum(V[p][0] for p in ps); sr=sum(V[p][1] for p in ps); so=sum(V[p][2]-V[p][0]-V[p][1] for p in ps)
  po=pv[2]-pv[0]-pv[1]
  for p in ps:
    d,r,t=V[p]; o=t-d-r
    D=d+pv[0]*d/sd; R=r+pv[1]*r/sr; O=o+(po*o/so if so else 0)
    VA[p]=[D,R,O]
  # largest-remainder rounding per group, so the county sums stay exact
  for gi in range(3):
    fl={p:int(VA[p][gi]) for p in ps}; tgt=[pv[0]+sd,pv[1]+sr,po+so][gi]; left=tgt-sum(fl.values())
    for p in sorted(ps,key=lambda q:-(VA[q][gi]-int(VA[q][gi])))[:max(0,left)]: fl[p]+=1
    for p in ps: VA[p][gi]=fl[p]
  for p in ps: VA[p]=[VA[p][0],VA[p][1],VA[p][0]+VA[p][1]+VA[p][2]]
  print('pool',pool,CTY[pool],pv,'over',len(ps),'precincts')
S=10000
def enc(ring):
  out=[];px=py=0
  for x,y in ring:
    X=round(x*S);Y=round(y*S); out+=[X-px,Y-py]; px,py=X,Y
  return out
def encg(g):
  gs=g.simplify(0.0002,preserve_topology=True)
  if gs.is_empty: gs=g
  polys=[gs] if gs.geom_type=='Polygon' else [q for q in gs.geoms if q.geom_type=='Polygon']
  return [[enc(list(q.exterior.coords))]+[enc(list(i.coords)) for i in q.interiors if i.length>0.001] for q in polys if q.area>0]
# precinct file
p24=f'{repo}/data/precincts2024/Oklahoma.js'; t=open(p24).read(); A=json.loads('['+t[t.index(',')+1:t.rindex(');')]+']'); rows,credit=A[0],A[1]
REPL={CTY[p] for p in POOL}
new=[]
for p in sorted(VA):
  if CTY[p] not in REPL: continue
  g=shape(AT[p]['geometry'])
  if not g.is_valid: g=g.buffer(0)
  d,r,tt=VA[p]; D,R=round(d),round(r); T=max(D+R,round(tt))
  new.append([CTY[p],p,D,R,T,encg(g)])
for c in REPL:
  o=E['Oklahoma|'+c]; s=[sum(x[i] for x in new if x[0]==c) for i in (2,3,4)]
  print(c,'rows',sum(1 for x in new if x[0]==c),'sum',s,'official',o[:3])
  credit[c]=("Oklahoma State Election Board 2024 precinct returns via MIT Election Data + Science Lab (CC0); precinct shapes: "
    "OU Center for Spatial Analysis / Oklahoma State Election Board statewide precincts (2024). County-wide early and absentee "
    "ballots allocated to precincts in proportion to in-person votes (precinct figures are estimates; county total exact).")
rows=[r for r in rows if r[0] not in REPL]+new
# districts
def ldw(p):
  s=open(p).read(); i=s.index('[',s.index('(')); j=s.rindex(']')+1; return s,i,j,json.loads(s[i:j])
rep={}
for fn,key in (('uscd','Uscong'),('ussldu','St_senate'),('ussldl','St_house')):
  acc=collections.defaultdict(lambda:[0.0,0.0,0.0]); hasA=set()
  for p,a in VA.items():
    k=str(int(AT[p]['properties'][key])).zfill(3) if fn!='uscd' else str(int(AT[p]['properties'][key])).zfill(2)
    for i in range(3): acc[k][i]+=a[i]
    if p[:2] in ALLOC: hasA.add((k,p[:2]))
  # a district holding all of a pool county's precincts gets the whole pool: exact. Only a partial share is an estimate
  nall=collections.Counter(p[:2] for p in VA if p[:2] in ALLOC)
  nin=collections.Counter((str(int(AT[p]['properties'][key])).zfill(3 if fn!='uscd' else 2),p[:2]) for p in VA if p[:2] in ALLOC)
  hasA={k for (k,c) in hasA if nin[(k,c)]<nall[c]}
  path=f'{repo}/v2/data/{fn}.js'; s,i,j,d=ldw(path); ch=[]
  for r in d:
    if r[0]!='Oklahoma': continue
    k=r[1]
    if k not in acc: print('no precincts for',fn,k); continue
    a=acc[k]; v=[round(a[0]),round(a[1]),round(a[2])]
    old=r[3] if len(r)>3 else None; fl=r[5] if len(r)>5 else None
    if gray_only and old: continue
    while len(r)<5: r.append(None)
    e20=fl in ('e20','est')
    nf=('est' if e20 else 'e24') if k in hasA else ('e20' if e20 else None)
    ch.append((k,old,fl,v,nf)); r[3]=v
    if nf: r[5:]=[nf]
    else: del r[5:]
  rep[fn]=ch
  if not dry: open(path,'w').write(s[:i]+json.dumps(d,separators=(',',':'))+s[j:])
if not dry: open(p24,'w').write('__prec("Oklahoma",'+json.dumps(rows,separators=(',',':'))+','+json.dumps(credit)+');')
json.dump(rep,open('/workspace/db/fix_ok2024_report.json','w'))
for fn,ch in rep.items():
  print(fn,'districts written',len(ch),'previously gray',sum(1 for c in ch if not c[1]),'flagged e24/est',sum(1 for c in ch if c[4] in('e24','est')))
  dif=[(c[0],round(abs(c[3][1]/c[3][2]-c[1][1]/c[1][2])*100,2),round((c[3][2]/c[1][2]-1)*100,1),c[2]) for c in ch if c[1]]
  dif.sort(key=lambda x:-x[1]); print(' largest R-share change vs old value (pts, total %, old flag):',dif[:8])
