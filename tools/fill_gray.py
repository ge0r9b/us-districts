#!/usr/bin/env python3
"""Fill districts that have no value for a year ("gray") by area-weighting that year's precinct results, scaled per
county and party to the official county totals (data/election<year>.js). Rows filled are flagged as estimates
('e20' = 2020 estimated, 'e24' = 2024 estimated, 'est' = both). Rules (same family as the earlier fill passes):
 - every precinct p gives district D the share area(p & D)/area(p) of its votes;
 - a county's precincts are usable only if their Biden/Harris+Trump sum is 50-110 % of the official county total;
   their votes are then scaled per party (dem, rep, other) to the official county total;
 - Alaska is skipped: its House/Senate come from build_ak2020.py, and its school districts are small towns inside
   huge rural precincts, where area-weighting gives misleading counts (tested and rejected at build 1533);
 - D is filled only if usable precincts cover >= 90 % of D's area and unusable/missing counties touch < 2 % of it.
Also validates the estimator on districts that already have exact values (flag None) and prints the errors.
--redo ST:County A,County B also re-estimates districts of ST that already have a value when the named counties'
precincts were replaced (their old values came from the old precinct file): a district is redone when those counties'
precincts cover >= 1 % of it; it keeps its old value if the estimate fails the rules above. --redo-exact-min F: an unflagged (exact) district is
redone only when the replaced counties cover >= F of it (default 0.01; its old sum came from the incomplete file).
usage: fill_gray.py <repo> <year> [--validate N] [--dry] [--redo ST:County,County [--redo-exact-min F]] [--only uscd,ussldu,ussldl,ussch]"""
import sys,os,json,re,random,collections,statistics
from shapely.geometry import Polygon,MultiPolygon
from shapely.strtree import STRtree
repo,year=sys.argv[1],sys.argv[2]; dry='--dry' in sys.argv
NV=int(sys.argv[sys.argv.index('--validate')+1]) if '--validate' in sys.argv else 0
YI=3 if year=='2024' else 4
REDO=None
if '--redo' in sys.argv:
  a=sys.argv[sys.argv.index('--redo')+1]; REDO=(a.split(':')[0],set(a.split(':')[1].split(',')))
ONLY=set(sys.argv[sys.argv.index('--only')+1].split(',')) if '--only' in sys.argv else None
REDO_EXACT=float(sys.argv[sys.argv.index('--redo-exact-min')+1]) if '--redo-exact-min' in sys.argv else 0.01
def redo_hit(st,D,exact=False):
  if not REDO or st!=REDO[0]: return False
  T,G,V,sc,TB,BAD=prec(st); a=0.0
  for i in T.query(D):
    if V[i][0] in REDO[1]:
      try: a+=G[i].intersection(D).area
      except Exception: pass
  return a/D.area>=(REDO_EXACT if exact else 0.01)
E=json.loads(re.search(r'=(\{.*\})',open(f"{repo}/data/election{year}.js").read(),re.S).group(1))
def ldw(p):
  s=open(p).read(); i=s.index('[',s.index('(')); j=s.rindex(']')+1; return s,i,j,json.loads(s[i:j])
def mp(enc,S):
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
  g=MultiPolygon(ps)
  return g if g.is_valid else g.buffer(0)
PC={}
def prec(st):
  if st in PC: return PC[st]
  fn=f"{repo}/data/precincts{year}/{st.replace(' ','_')}.js"
  if not os.path.exists(fn): PC[st]=None; return None
  t=open(fn).read(); rows=json.loads('['+t[t.index(',')+1:t.rindex(');')]+']')[0]
  cs=collections.defaultdict(lambda:[0,0,0])
  for r in rows: c=cs[r[0]]; c[0]+=r[2]; c[1]+=r[3]; c[2]+=r[4]
  sc={}
  if st=='Alaska':  # no official borough totals; AK precinct files already sum to the official statewide result (district-level ballots allocated)
    sc={c:(1.0,1.0,1.0) for c in cs}
  for c,(d,rp,t_) in (cs.items() if st!='Alaska' else []):
    o=E.get(st+'|'+c)
    if not o or d+rp<=0: continue
    q=(d+rp)/max(1,o[0]+o[1])
    if 0.5<=q<=1.1: sc[c]=(o[0]/max(1,d), o[1]/max(1,rp), max(0,o[2]-o[0]-o[1])/max(1,t_-d-rp) if t_-d-rp>0 else 0.0)
  G=[];V=[];BAD=[]
  for r in rows:
    g=mp(r[5],10000)
    if g is None or g.is_empty or g.area<=0: continue
    if r[0] in sc: G.append(g); V.append((r[0],r[2],r[3],r[4],g.area))
    else: BAD.append(g)
  PC[st]=(STRtree(G) if G else None,G,V,sc,STRtree(BAD) if BAD else None,BAD)
  return PC[st]
def estimate(st,D):
  P=prec(st)
  if not P or P[0] is None: return None,'no precinct file'
  T,G,V,sc,TB,BAD=P; acc=[0.0,0.0,0.0]; cov=0.0; A=D.area
  for i in T.query(D):
    try: a=G[i].intersection(D).area
    except Exception: continue
    if a<=0: continue
    cov+=a; c,d,rp,t_,pa=V[i]; f=a/pa; s=sc[c]
    acc[0]+=d*f*s[0]; acc[1]+=rp*f*s[1]; acc[2]+=(d*s[0]+rp*s[1]+(t_-d-rp)*s[2])*f
  bad=0.0
  if TB is not None:
    for i in TB.query(D):
      try: bad+=BAD[i].intersection(D).area
      except Exception: pass
  if bad/A>=0.02: return None,f'failing county precincts cover {bad/A:.0%}'
  if cov/A<0.9: return None,f'usable precinct cover {cov/A:.0%}'
  if acc[2]<1: return None,'no votes'
  return [round(acc[0]),round(acc[1]),round(acc[2])],None
FL={'uscd':'uscd','ussldu':'ussldu','ussldl':'ussldl','ussch':'ussch'}
report={}
for f in FL:
  if ONLY and f not in ONLY: continue
  p=f"{repo}/v2/data/{f}.js"; s,i,j,d=ldw(p); filled=[];left=[]
  for r in d:
    if r[0]=='District of Columbia' or r[0]=='Alaska': continue
    D=None
    if len(r)>YI and r[YI]:
      if not (REDO and r[0]==REDO[0]): continue
      D=mp(r[2],1000)
      if D is None or D.is_empty or not redo_hit(r[0],D,exact=not (len(r)>5 and r[5] in ('e24','est','e20'))): continue
    D=D or mp(r[2],1000)
    if D is None or D.is_empty: left.append((r[0],r[1],'no shape')); continue
    v,why=estimate(r[0],D)
    if v is None: left.append((r[0],r[1],why)); continue
    while len(r)<5: r.append(None)
    r[YI]=v; fl=r[5] if len(r)>5 else None
    nf={'2024':{None:'e24','cty':'e24','e20':'est','e24':'e24','est':'est'},'2020':{None:'e20','cty':'e20','e24':'est','e20':'e20','est':'est'}}[year].get(fl,'est')
    r[5:]=[nf]; filled.append((r[0],r[1],v))
  # validation on exact districts
  val=[]
  if NV:
    ex=[r for r in d if r[0] not in ('Alaska','District of Columbia') and len(r)>YI and r[YI] and (len(r)<6 or r[5] in (None,)) and r[YI][2]>0]
    random.seed(7); 
    for r in random.sample(ex,min(NV,len(ex))):
      D=mp(r[2],1000)
      if D is None: continue
      v,_=estimate(r[0],D)
      if v and v[2]>0: val.append((abs(v[1]/v[2]-r[YI][1]/r[YI][2])*100, abs(v[2]-r[YI][2])/r[YI][2]*100))
  vs=None
  if val:
    a=sorted(x for x,_ in val); b=sorted(y for _,y in val)
    vs={'n':len(val),'median_rshare_err_pts':round(statistics.median(a),2),'p90_rshare_err_pts':round(a[int(.9*len(a))-1],2),'median_total_err_pct':round(statistics.median(b),2),'over3pts':sum(1 for x in a if x>3)}
  report[f]={'filled':filled,'left':left,'validation':vs}
  print(f,year,'filled',len(filled),'left',len(left),'validation',vs,flush=True)
  if not dry and filled: open(p,'w').write(s[:i]+json.dumps(d,separators=(',',':'))+s[j:])
json.dump(report,open(f'/workspace/db/fill_gray_{year}{"_dry" if dry else ""}.json','w'),indent=0)
