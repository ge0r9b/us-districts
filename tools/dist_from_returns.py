#!/usr/bin/env python3
"""State legislative district totals for 2024 from official precinct returns that name each precinct's districts.
Source: MIT Election Data + Science Lab 2024 precinct returns (github.com/MEDSL/2024-elections-official,
individual_states/<st>24.csv, CC0), compiled from each state's official precinct results (source per state in the
MEDSL README). Method:
 - reporting unit = (county, precinct); presidential votes summed over vote modes (TOTAL rows when present);
   total = all named candidates (write-in, over/under votes, blanks excluded). Harris and Trump per county must equal
   the official county totals in data/election2024.js within 0.1 % (counties that do not are unusable);
 - a unit's House (Senate) district = the district of the State House (State Senate) race on its ballot. A unit
   with two or more districts (split precinct) is apportioned by the votes cast in each district's race in that unit,
   keeping the unit's party split (same rule as the Maine town split) -> the district is an estimate ('e24'),
   written only when apportioned votes are <= 30 % of the district's votes (the earlier split-share rule);
 - a unit with no Senate race in 2024 takes the Senate district that holds >= 98 % of its House district (app
   boundaries); otherwise it is unmapped;
 - a district is computed only if every county it touches (>= 0.5 % of its area) is usable and no unmapped unit
   could belong to it (a unit with a known House district but no Senate race can only belong to the Senate districts
   overlapping that House district; a unit with no district at all blocks every district in its county). Unmapped
   votes up to 0.05 % of the county (district) total do not block; they are left out and reported. Exact districts (no apportioned votes) replace the old value; estimated ones only replace a gray or
   estimated ('e24'/'est') value. 2020 flags are kept (e20/est).
usage: dist_from_returns.py <repo> <State> <st24.csv> [--layers ussldl,ussldu] [--dry] [--gray-only]"""
import sys,json,csv,collections,re
from shapely.geometry import Polygon,MultiPolygon
from shapely.strtree import STRtree
repo,ST,csvf=sys.argv[1],sys.argv[2],sys.argv[3]; dry='--dry' in sys.argv; gray_only='--gray-only' in sys.argv
LAY=sys.argv[sys.argv.index('--layers')+1].split(',') if '--layers' in sys.argv else ['ussldl','ussldu']
E=json.loads(re.search(r'=(\{.*\})',open(f"{repo}/data/election2024.js").read(),re.S).group(1))
def cn(s): return re.sub(r'[^A-Z]','',s.upper().replace('SAINT','ST').replace(' COUNTY','').replace(' PARISH',''))
CN={}
for k in E:
  if k.startswith(ST+'|'):
    c=k.split('|')[1]; CN[cn(c)]=c
    if c.endswith(' city'): CN[cn(c[:-5])+'CITY']=c
 # election authorities that report apart from their county (Kansas City Board of Election Commissioners = the
# Kansas City part of Jackson County, MO)
ALIAS={('Missouri','KANSASCITY'):'Jackson County'}
def county(x):
  n=cn(x['county_name'])
  if (ST,n) in ALIAS: return ALIAS[(ST,n)]
  return CN.get(n) or CN.get(n+'CITY') or CN.get(n.replace('CITY',''))
SKIP=('WRITE','OVER','UNDER','BLANK','SPOILED','TOTAL VOTES','REGISTERED','BALLOTS CAST')
rows=list(csv.DictReader(open(csvf)))
hasT=any(x['mode']=='TOTAL' for x in rows)
U=collections.defaultdict(lambda:[0,0,0]); UC={}; LEG={'ussldl':collections.defaultdict(collections.Counter),'ussldu':collections.defaultdict(collections.Counter)}
nocty=set()
for x in rows:
  if hasT and x['mode']!='TOTAL': continue
  c=county(x)
  if not c: nocty.add(x['county_name']); continue
  k=(c,x['precinct']); v=int(float(x['votes'] or 0))
  if x['office']=='US PRESIDENT':
    UC[k]=c
    if x['writein']=='TRUE' or any(s in x['candidate'].upper() for s in SKIP): continue
    a=U[k]; a[2]+=v
    if x['party_simplified']=='DEMOCRAT': a[0]+=v
    elif x['party_simplified']=='REPUBLICAN': a[1]+=v
  elif x['office'] in ('STATE HOUSE','STATE SENATE') and not any(s in x['candidate'].upper() for s in SKIP[1:]):
    d=re.sub(r'^0+','',x['district'].strip()) or '0'
    LEG['ussldl' if x['office']=='STATE HOUSE' else 'ussldu'][k][d]+=v
if nocty: print('county names not matched:',nocty)
cs=collections.defaultdict(lambda:[0,0,0])
for k,a in U.items():
  for i in range(3): cs[k[0]][i]+=a[i]
USABLE=set()
for c,a in cs.items():
  o=E[ST+'|'+c]
  if abs(a[0]-o[0])<=max(2,0.001*o[0]) and abs(a[1]-o[1])<=max(2,0.001*o[1]): USABLE.add(c)
  else: print('county not equal to official (D,R):',c,a[:2],o[:2])
print(f'{ST}: {len(cs)} counties in the returns, {len(USABLE)} equal to official (Harris, Trump); total = named candidates; official totals {sum(E[ST+"|"+c][2] for c in cs)} returns {sum(a[2] for a in cs.values())}')
def ldw(p):
  s=open(p).read(); i=s.index('[',s.index('(')); j=s.rindex(']')+1; return s,i,j,json.loads(s[i:j])
def mp(enc,S=1000):
  ps=[]
  for rg in enc:
    rings=[]
    for f in rg:
      o=[];x=y=0
      for k in range(0,len(f)-1,2): x+=f[k]; y+=f[k+1]; o.append((x/S,y/S))
      if len(o)>=3: rings.append(o)
    if rings:
      try: ps.append(Polygon(rings[0],rings[1:]))
      except Exception: pass
  if not ps: return None
  g=MultiPolygon(ps); return g if g.is_valid else g.buffer(0)
L={f:ldw(f'{repo}/v2/data/{f}.js') for f in ('ussldl','ussldu')}
def key(r): return re.sub(r'^0+','',r[1]) or '0'
G={f:{key(r):mp(r[2]) for r in L[f][3] if r[0]==ST} for f in L}
# counties (app county layer) for the touch test
cs_=open(f'{repo}/v2/data/uscounties.js').read(); CT=json.loads(cs_[cs_.index('[',cs_.index('(')):cs_.rindex(']')+1])
CG={}
for r in CT:
  if r[0]==ST: CG[r[1]]=mp(r[2])
# House -> Senate nesting, for units without a Senate race
NEST={}
for h,g in G['ussldl'].items():
  if g is None: continue
  best=max(((s,g.intersection(q).area/g.area) for s,q in G['ussldu'].items() if q is not None and g.intersects(q)),key=lambda x:x[1],default=(None,0))
  if best[1]>=0.98: NEST[h]=best[0]
print('House districts nested >= 98 % in one Senate district:',len(NEST),'of',len(G['ussldl']))
TOL=0.0005  # unmapped votes up to 0.05 % of a county (or district) total are left out rather than blocking it
rep={}
for f in LAY:
  acc=collections.defaultdict(lambda:[0.0,0.0,0.0]); app=collections.Counter(); unm=collections.Counter(); blk=collections.Counter(); how=collections.Counter()
  for k,a in U.items():
    ds=LEG[f].get(k)
    if not ds and f=='ussldu':
      h=LEG['ussldl'].get(k)
      if h and all(x in NEST for x in h):
        ds=collections.Counter()
        for x,w in h.items(): ds[NEST[x]]+=w
        how['senate via House nesting']+=1
    if a[2]<=0: continue
    if not ds or sum(ds.values())<=0:
      how['unmapped']+=1; h=LEG['ussldl'].get(k) if f=='ussldu' else None
      if h and all(x in G['ussldl'] and G['ussldl'][x] is not None for x in h):
        # the unit can only be in a Senate district that overlaps its House district(s)
        for x in h:
          for sd,q in G['ussldu'].items():
            if q is not None and G['ussldl'][x].intersects(q) and G['ussldl'][x].intersection(q).area/G['ussldl'][x].area>=0.001: blk[sd]+=a[2]
      else: unm[k[0]]+=a[2]
      continue
    tot=sum(ds.values())
    if len(ds)==1: how['one district']+=1
    else: how['split, apportioned']+=1
    for d,w in ds.items():
      sh=w/tot
      for i in range(3): acc[d][i]+=a[i]*sh
      if len(ds)>1: app[d]+=a[2]*sh
  s,i,j,data=L[f]; ch=[]; skipped=[]
  for r in data:
    if r[0]!=ST: continue
    d=key(r); g=G[f].get(d)
    if g is None or d not in acc: skipped.append((r[1],'no returns')); continue
    touch=[c for c,q in CG.items() if q is not None and g.intersects(q) and g.intersection(q).area/g.area>=0.005]
    badc=[c for c in touch if c not in USABLE or unm[c]>TOL*cs[c][2]]
    if badc: skipped.append((r[1],'county unusable/unmapped: '+','.join(badc))); continue
    if blk[d]>TOL*acc[d][2]: skipped.append((r[1],f'{round(blk[d])} votes in units whose Senate district is unknown may belong to it')); continue
    a=acc[d]; v=[round(a[0]),round(a[1]),round(a[2])]; est=app[d]>0
    old=r[3] if len(r)>3 else None; fl=r[5] if len(r)>5 else None; e20=fl in ('e20','est')
    if est and app[d]>0.30*a[2]: skipped.append((r[1],f'split precincts hold {app[d]/a[2]:.0%} of its votes (> 30 %)')); continue
    if old and (gray_only or (est and fl not in ('e24','est'))): continue
    while len(r)<5: r.append(None)
    nf=('est' if e20 else 'e24') if est else ('e20' if e20 else None)
    ch.append((r[1],old,fl,v,nf,round(app[d]/max(1,a[2])*100,1))); r[3]=v
    if nf: r[5:]=[nf]
    else: del r[5:]
  rep[f]=ch
  print(f,dict(how),'unmapped votes by county',dict(unm) or 0)
  print(f,'written',len(ch),'previously gray',[c[0] for c in ch if not c[1]],'estimated (split precincts)',sum(1 for c in ch if c[4] in('e24','est')),'skipped',skipped[:12],len(skipped))
  dif=sorted(((c[0],round(abs(c[3][1]/c[3][2]-c[1][1]/c[1][2])*100,2),round((c[3][2]/c[1][2]-1)*100,1),c[2]) for c in ch if c[1]),key=lambda x:-x[1])
  print(' largest R-share change vs old (pts, total %, old flag):',dif[:6])
  if not dry: open(f'{repo}/v2/data/{f}.js','w').write(s[:i]+json.dumps(data,separators=(',',':'))+s[j:])
json.dump(rep,open(f'/workspace/db/dist_from_returns_{ST.replace(" ","_")}{"_dry" if dry else ""}.json','w'))
