#!/usr/bin/env python3
"""Replace the 2024 precinct rows of whole counties with official precinct returns joined to official precinct shapes.
Used for counties whose old (mostly NYT-merged) rows sum outside 90-110 % of the official county total.
Returns: MIT Election Data + Science Lab 2024 official precinct returns (github.com/MEDSL/2024-elections-official,
individual_states/<st>24.csv, CC0), presidential votes summed over vote modes (TOTAL rows when present); total = all
named candidates (write-ins, over/under votes excluded), as in dist_from_returns.py.
Shapes: a GeoJSON of official precinct boundaries (source named with --credit), county field --cf, name field --nf.
Join (per county, in this order): the leading precinct code ("1-A", "JP01", "07"), the full name, the parts of a
"A/B" name (shapes unioned), the precinct number; with --fuzzy S, remaining units are paired with remaining shapes by name-token overlap
(best unique pairs first, score >= S; every pair is printed for review); --eliminate pairs the last unit with the last shape when exactly one of each is
left (the partition is the same, only the polling-place name changed). Duplicate shapes (same name, same area) are merged. Row name = the shape's name when one shape matches (--name shape, default),
else the returns unit's name. Abbreviations MTN/OZ/WD and spacing are normalised.
QC, per county, else the county is left unchanged: every returns unit with votes is matched; Harris and Trump sum to the
official county total in data/election2024.js within 0.1 %; a shape matched by no unit is kept as a 0-vote row only
with --keep-empty. Countywide pseudo-units (absentee/early/provisional with no shape, named with --pool REGEX) are
allocated to the county's precincts in proportion to their votes (≈ precinct figures, exact county total).
usage: fix_county2024.py <repo> <State> <st24.csv> <shapes.geojson> --cf F --nf F --counties "A County,B County"
       --credit TEXT [--name shape|returns] [--pool REGEX] [--fuzzy MINSCORE [--eliminate]] [--keep-empty] [--dry]"""
import sys,json,csv,re,collections,os
from shapely.geometry import shape
from shapely.ops import unary_union
a=sys.argv; repo,ST,csvf,gjf=a[1:5]; dry='--dry' in a; keep_empty='--keep-empty' in a
opt=lambda k,d=None: a[a.index(k)+1] if k in a else d
CF,NF=opt('--cf'),opt('--nf'); COUNTIES=opt('--counties').split(','); CREDIT=opt('--credit'); POOL=opt('--pool'); NAME=opt('--name','shape'); FUZZY=float(opt('--fuzzy','0')); ELIM='--eliminate' in a
E=json.loads(re.search(r'=(\{.*\})',open(f"{repo}/data/election2024.js").read(),re.S).group(1))
def cn(s): return re.sub(r'[^A-Z]','',s.upper().replace('SAINT','ST').replace(' COUNTY','').replace(' PARISH',''))
AB={'MTN':'MOUNTAIN','OZ':'OZARK','WD':'WARD','DE QUEEN':'DEQUEEN','MT':'MOUNT','PCT':'PRECINCT'}
def norm(s):
  s=re.sub(r'^\d+_','',str(s)); s=re.sub(r'[()\[\],.#]',' ',s.upper()); s=re.sub(r'\s+',' ',s).strip()
  for k,v in AB.items(): s=re.sub(r'\b'+k+r'\b',v,s)
  return s.replace(' - ',' ').strip()
FZ={'ES':'ELEMENTARY SCHOOL','ELEM':'ELEMENTARY','STA':'STATION','DP':'DEPT','DEPARTMENT':'DEPT','CNTR':'CENTER','COMM':'COMMUNITY',
    'CCHS':'CAMPBELL COUNTY HIGH SCHOOL','HS':'HIGH SCHOOL','REC':'RECREATION','SCH':'SCHOOL','N':'NORTH','S':'SOUTH','E':'EAST','W':'WEST',
    'NE':'NORTH EAST','SE':'SOUTH EAST','SW':'SOUTH WEST','NW':'NORTH WEST','JEFF':'JEFFERSON','CO':'COUNTY'}
STOPW={'OF','THE','AND','SCHOOL','ELEMENTARY','CENTER','COMMUNITY','HALL','DEPT','FIRE','CITY','OLD','PRECINCT'}
def toks(s):
  s=re.sub(r'^\s*[0-9]+(-[0-9A-Z]+)?\s+','',norm(s)); t=[]
  for w in re.split(r'[\s/-]+',s.replace('.',' ')):
    if w: t+=FZ.get(w,w).split()
  return t
def fsc(a,b):
  ta,tb=set(toks(a)),set(toks(b)); ka,kb=ta-STOPW,tb-STOPW
  if not ka or not kb: return 0.0
  j=len(ka&kb)/len(ka|kb); return j+0.25*(len(ta&tb)/max(1,len(ta|tb)))
def code(s):
  if re.match(r'^\d+_',str(s)): return None  # Missouri 'NN_NAME': NN is a reporting-order number, not the precinct code
  m=re.match(r'^\s*([0-9]+-[A-Z0-9]+|[A-Z]{1,3}\s?-?\s?[0-9]+|[0-9]+)\b',str(s).upper())
  return re.sub(r'\s','',m.group(1)) if m else None
def num(s):
  if re.match(r'^\d+_',str(s)): return None
  ns=re.findall(r'\d+(?:\.\d+)?',str(s)); return int(float(ns[0])) if len(ns)==1 or (ns and re.fullmatch(r'\d+\.\d+',str(s).strip())) else None
SKIP=('WRITE','OVER','UNDER','BLANK','SPOILED','TOTAL VOTES','REGISTERED','BALLOTS CAST')
rows=list(csv.DictReader(open(csvf))); hasT=any(x['mode']=='TOTAL' for x in rows)
CNM={cn(c):c for c in COUNTIES}
U=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0]))
for x in rows:
  if x['office']!='US PRESIDENT' or (hasT and x['mode']!='TOTAL'): continue
  c=CNM.get(cn(x['county_name']))
  if not c or x['writein']=='TRUE' or any(s in x['candidate'].upper() for s in SKIP): continue
  v=int(float(x['votes'] or 0)); u=U[c][x['precinct']]; u[2]+=v
  if x['party_simplified']=='DEMOCRAT': u[0]+=v
  elif x['party_simplified']=='REPUBLICAN': u[1]+=v
SH=collections.defaultdict(list)
for f in json.load(open(gjf))['features']:
  p=f['properties']; c=CNM.get(cn(p[CF] or ''))
  if c and f['geometry']:
    g=shape(f['geometry']); g=g if g.is_valid else g.buffer(0); n=str(p[NF]).strip()
    if any(n2==n and abs(g2.area-g.area)<=1e-6*max(g.area,1e-12)+1e-12 and g2.symmetric_difference(g).area<=0.001*g.area for n2,g2 in SH[c]): continue
    SH[c].append((n,g))
S=10000
def enc(ring):
  out=[];px=py=0
  for x,y in ring:
    X=round(x*S);Y=round(y*S); out+=[X-px,Y-py]; px,py=X,Y
  return out
def encg(g):
  gs=g.simplify(0.0002,preserve_topology=True)
  if gs.is_empty: gs=g
  polys=[gs] if gs.geom_type=='Polygon' else [q for q in getattr(gs,'geoms',[]) if q.geom_type=='Polygon']
  return [[enc(list(q.exterior.coords))]+[enc(list(i.coords)) for i in q.interiors if i.length>0.001] for q in polys if q.area>0]
fn=f"{repo}/data/precincts2024/{ST.replace(' ','_')}.js"; t=open(fn).read()
data,credit=json.loads('['+t[t.index(',')+1:t.rindex(');')]+']')
if isinstance(credit,str): credit={r[0]:credit for r in data}
report={}; done=[]
for c in COUNTIES:
  sh=SH.get(c,[]); units=U.get(c,{})
  idx={'code':collections.defaultdict(list),'full':collections.defaultdict(list),'num':collections.defaultdict(list)}
  for i,(n,g) in enumerate(sh):
    if code(n): idx['code'][code(n)].append(i)
    idx['full'][norm(n)].append(i)
    if num(n) is not None: idx['num'][num(n)].append(i)
  M={}; pool=[]; miss=[]; fz=[]; fuzzy_pairs=[]
  for un,v in units.items():
    if POOL and re.search(POOL,un,re.I): pool.append(un); continue
    m=None
    if code(un) and idx['code'].get(code(un)): m=idx['code'][code(un)]
    elif idx['full'].get(norm(un)): m=idx['full'][norm(un)]
    elif '/' in un and all(idx['full'].get(norm(p)) for p in un.split('/')): m=sum((idx['full'][norm(p)] for p in un.split('/')),[])
    elif num(un) is not None and idx['num'].get(num(un)): m=idx['num'][num(un)]
    if m: M[un]=m
    elif FUZZY: fz.append(un)
    elif v[2]>0: miss.append((un,v[2]))
  if FUZZY and fz:
    # token-overlap matching for the remaining units against the remaining shapes, best unique pairs first
    taken={i for m in M.values() for i in m}; free=[i for i in range(len(sh)) if i not in taken]
    cand=sorted(((fsc(un,sh[i][0]),un,i) for un in fz for i in free),reverse=True); du=set(); di=set()
    for sc_,un,i in cand:
      if un in du or i in di or sc_<FUZZY: continue
      M[un]=[i]; du.add(un); di.add(i); fuzzy_pairs.append((un,sh[i][0],round(sc_,2)))
    left=[un for un in fz if un not in du and units[un][2]>0]; freeleft=[i for i in free if i not in di]
    if ELIM and len(left)==1 and len(freeleft)==1:
      # every other unit and shape is paired, so the last unit is the last shape (same partition, renamed polling place)
      M[left[0]]=[freeleft[0]]; fuzzy_pairs.append((left[0],sh[freeleft[0]][0],'by elimination')); left=[]
    for un in left: miss.append((un,units[un][2]))
  used=collections.Counter(i for m in M.values() for i in m)
  dup=[sh[i][0] for i,k in used.items() if k>1]; empty=[sh[i][0] for i in range(len(sh)) if i not in used]
  tot=[sum(v[i] for v in units.values()) for i in range(3)]; o=E[f'{ST}|{c}']
  ok=not miss and not dup and (keep_empty or not empty) and units and abs(tot[0]-o[0])<=max(2,0.001*o[0]) and abs(tot[1]-o[1])<=max(2,0.001*o[1])
  old=[r for r in data if r[0]==c]; oldsum=sum(r[2]+r[3] for r in old)
  report[c]={'units':len(units),'shapes':len(sh),'matched':len(M),'pool':pool,'missing':miss,'shared shapes':dup,'empty shapes':empty,'fuzzy pairs':fuzzy_pairs,
             'returns D,R,T':tot,'official':o[:3],'old ratio':round(oldsum/max(1,o[0]+o[1]),3),'ok':bool(ok)}
  print(c,json.dumps({k:(v[:8] if isinstance(v,list) else v) for k,v in report[c].items() if k!='fuzzy pairs'}))
  if fuzzy_pairs: print('   pairs:',fuzzy_pairs)
  if not ok: continue
  pv=[sum(units[p][i] for p in pool) for i in range(3)]; base=[sum(units[u][i] for u in M) for i in range(3)]
  new=[]
  for un,m in M.items():
    v=units[un]; vv=[v[i]+(pv[i]*v[i]/base[i] if base[i] else 0) for i in range(3)]
    g=unary_union([sh[i][1] for i in m]); P=encg(g)
    if not P: continue
    nm=sh[m[0]][0] if len(m)==1 and NAME=='shape' else (re.sub(r'\.0$','',un) if re.fullmatch(r'\d+\.0',un) else un)
    new.append([c,nm,round(vv[0]),round(vv[1]),max(round(vv[2]),round(vv[0])+round(vv[1])),P])
  if keep_empty:
    for i in range(len(sh)):
      if i not in used:
        P=encg(sh[i][1])
        if P: new.append([c,sh[i][0],0,0,0,P])
  # rounding of allocated pools: fix D/R so the county sums stay exact
  for k in (2,3):
    d=o[k-2]-sum(r[k] for r in new)
    if d and new and pool: mx=max(new,key=lambda r:r[k]); mx[k]+=d; mx[4]=max(mx[4],mx[2]+mx[3])
  data=[r for r in data if r[0]!=c]+new
  credit[c]=CREDIT+(' Countywide units '+', '.join(pool)+' allocated to precincts in proportion to their votes (precinct figures ≈, county total exact).' if pool else '')
  done.append(c)
print('replaced',len(done),done)
if done and not dry:
  open(fn,'w').write('__prec('+json.dumps(ST)+','+json.dumps(data,separators=(',',':'))+','+json.dumps(credit,separators=(',',':'))+');')
json.dump(report,open(f'/workspace/db/fix_county2024_{ST.replace(" ","_")}{"_dry" if dry else ""}.json','w'),indent=1)
