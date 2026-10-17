#!/usr/bin/env python3
"""California 2024 precincts from the Statewide Database (SWDB, UC Berkeley Law; California's redistricting database):
G24 Statement of Vote by SR precinct (statewidedatabase.org/pub/data/G24/state/state_g24_sov_data_by_g24_srprec.zip,
columns PRSDEM01 Harris, PRSREP01 Trump, PRS* all presidential candidates) joined to the SR precinct shapes
(statewidedatabase.org/pub/data/G24/c<fips>/srprec_<fips>_g24_v01_shp.zip). The SOV is the Secretary of State's
official Statement of Vote at precinct level; SWDB suppresses ("***") a few tiny precincts for voter privacy, so county
sums are 99.4-100 % of the official total (QC here: D and R within 1.2 % of data/election2024.js in every county).
Zero-vote SR precincts are kept with 0 votes (the official count); only the unassigned shape with no SOV row is left out.
Names are the county's SR precinct code (as on SWDB / county precinct lists). Replaces the named counties (or all with
--all) in data/precincts2024/California.js and sets their per-county credit; other counties are kept as they are.
usage: build_ca2024.py <repo> <sov.csv> <shpdir> (--all | --counties "El Dorado County,Imperial County") [--dry]"""
import sys,os,json,re,csv,collections,glob
import shapefile
from shapely.geometry import Polygon
from shapely.ops import unary_union
def shp_geom(sh):
  # shapefile rings: clockwise = outer, counter-clockwise = hole (degenerate slivers are dropped by buffer(0))
  pts=sh.points; parts=list(sh.parts)+[len(pts)]; ext=[];hol=[]
  for a,b in zip(parts[:-1],parts[1:]):
    r=pts[a:b]
    if len(r)<4: continue
    ar=sum(r[i][0]*r[i+1][1]-r[i+1][0]*r[i][1] for i in range(len(r)-1))
    q=Polygon(r).buffer(0)
    if q.is_empty: continue
    (ext if ar<0 else hol).append(q)
  g=unary_union(ext) if ext else None
  if g is not None and hol: g=g.difference(unary_union(hol))
  return g
repo,sovf,shpd=sys.argv[1:4]; dry='--dry' in sys.argv
E=json.loads(re.search(r'=(\{.*\})',open(f"{repo}/data/election2024.js").read(),re.S).group(1))
NAMES=sorted(k.split('|')[1] for k in E if k.startswith('California|'))
FIPS={'%03d'%(2*i+1):c for i,c in enumerate(NAMES)}
if '--all' in sys.argv: WANT=set(NAMES)
else: WANT=set(sys.argv[sys.argv.index('--counties')+1].split(','))
assert WANT<=set(NAMES),WANT-set(NAMES)
PRS=('PRSAIP01','PRSDEM01','PRSGRN01','PRSLIB01','PRSPAF01','PRSREP01')
def iv(v):
  try: return int(v)
  except ValueError: return 0   # '***' = suppressed for privacy
V={}
for x in csv.DictReader(open(sovf)):
  V[(x['FIPS'][2:],x['SRPREC'])]=(iv(x['PRSDEM01']),iv(x['PRSREP01']),sum(iv(x[k]) for k in PRS))
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
new=collections.defaultdict(list); cs=collections.defaultdict(lambda:[0,0,0]); noshape=collections.defaultdict(int)
for f,c in FIPS.items():
  if c not in WANT: continue
  r=shapefile.Reader(glob.glob(f"{shpd}/srprec_{f}_g24_v01.shp")[0]); have=set()
  for sr in r.iterShapeRecords():
    k=(f,str(sr.record[0])); v=V.get(k)
    if not v: continue   # zero-vote SR precincts are kept (official 0; mountains, parks, bases) so the area counts as covered
    g=shp_geom(sr.shape)
    if g is None or g.is_empty: continue
    P=encg(g)
    if not P: continue
    have.add(k[1]); new[c].append([c,k[1],v[0],v[1],v[2],P]); a=cs[c]
    for i in range(3): a[i]+=v[i]
  for (ff,p),v in V.items():
    if ff==f and p not in have: noshape[c]+=v[2]
bad=[]
for c in WANT:
  o=E['California|'+c]; a=cs[c]
  if abs(a[0]-o[0])>0.012*o[0] or abs(a[1]-o[1])>0.012*o[1]: bad.append((c,a,o))
print('counties',len(new),'precincts',sum(len(v) for v in new.values()),'QC fail',bad)
print('votes in SOV units without a shape (left out):',{c:v for c,v in noshape.items() if v})
if bad: sys.exit('QC failed')
p=f"{repo}/data/precincts2024/California.js"; t=open(p).read(); a=json.loads('['+t[t.index(',')+1:t.rindex(');')]+']')
rows=[r for r in a[0] if r[0] not in WANT]; cr=a[1] if isinstance(a[1],dict) else {}
for c in sorted(WANT): rows+=new[c]; cr[c]=("Statewide Database (UC Berkeley Law), 2024 general election Statement of Vote by SR precinct "
  "and SR precinct boundaries (statewidedatabase.org); official CA SOS precinct results, tiny precincts suppressed for privacy")
if not dry:
  open(p,'w').write('__prec("California",'+json.dumps(rows,separators=(',',':'))+','+json.dumps(cr,separators=(',',':'))+');')
  print('file',round(os.path.getsize(p)/1e6,1),'MB','rows',len(rows))
