#!/usr/bin/env python3
"""Build offline 2016 presidential precinct files from VEST 2016 (Harvard Dataverse doi:10.7910/DVN/NH5S2I, CC BY 4.0).
Same row format as data/precincts2020/<State>.js: [county, precinct, dem, rep, total_all_candidates, polygons].
Based on tools/build_vest2020.py, with these changes for completeness: every county is kept (no county QC drop), and a precinct
whose representative point falls outside every county polygon goes to the nearest county in the same state.
Rows are exact VEST precinct results (no area weighting), so none of them is an estimate (no ≈).
usage: build_vest2016.py <vest16_dir> <repo>/v2/data/uscounties.js <out_dir> [st ...]"""
import sys,os,glob,json,zipfile,shapefile,io,re,pickle
from shapely.ops import unary_union
from pyproj import CRS,Transformer
from shapely.ops import transform
import warnings; warnings.filterwarnings('ignore')
from shapely.geometry import shape
from shapely.strtree import STRtree
vd,cshp,od=sys.argv[1:4]; REPO=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(cshp)))); only=set(sys.argv[4:])
FIPS={'01':'Alabama','02':'Alaska','04':'Arizona','05':'Arkansas','06':'California','08':'Colorado','09':'Connecticut','10':'Delaware','11':'District of Columbia','12':'Florida','13':'Georgia','15':'Hawaii','16':'Idaho','17':'Illinois','18':'Indiana','19':'Iowa','20':'Kansas','21':'Kentucky','22':'Louisiana','23':'Maine','24':'Maryland','25':'Massachusetts','26':'Michigan','27':'Minnesota','28':'Mississippi','29':'Missouri','30':'Montana','31':'Nebraska','32':'Nevada','33':'New Hampshire','34':'New Jersey','35':'New Mexico','36':'New York','37':'North Carolina','38':'North Dakota','39':'Ohio','40':'Oklahoma','41':'Oregon','42':'Pennsylvania','44':'Rhode Island','45':'South Carolina','46':'South Dakota','47':'Tennessee','48':'Texas','49':'Utah','50':'Vermont','51':'Virginia','53':'Washington','54':'West Virginia','55':'Wisconsin','56':'Wyoming'}
AB={'al':'Alabama','ak':'Alaska','az':'Arizona','ar':'Arkansas','ca':'California','co':'Colorado','ct':'Connecticut','de':'Delaware','dc':'District of Columbia','fl':'Florida','ga':'Georgia','hi':'Hawaii','id':'Idaho','il':'Illinois','in':'Indiana','ia':'Iowa','ks':'Kansas','ky':'Kentucky','la':'Louisiana','me':'Maine','md':'Maryland','ma':'Massachusetts','mi':'Michigan','mn':'Minnesota','ms':'Mississippi','mo':'Missouri','mt':'Montana','ne':'Nebraska','nv':'Nevada','nh':'New Hampshire','nj':'New Jersey','nm':'New Mexico','ny':'New York','nc':'North Carolina','nd':'North Dakota','oh':'Ohio','ok':'Oklahoma','or':'Oregon','pa':'Pennsylvania','ri':'Rhode Island','sc':'South Carolina','sd':'South Dakota','tn':'Tennessee','tx':'Texas','ut':'Utah','vt':'Vermont','va':'Virginia','wa':'Washington','wv':'West Virginia','wi':'Wisconsin','wy':'Wyoming'}
# County polygons = v2's own geography (v2/data/uscounties.js, x/1000 delta-encoded), so every 2016 key exists in v2.
from shapely.geometry import Polygon,MultiPolygon
def dec(f,sc):
  o=[];x=y=0
  for i in range(0,len(f),2): x+=f[i];y+=f[i+1];o.append((x/sc,y/sc))
  return o
t=open(cshp).read(); CROWS=json.loads(t[t.index('['):t.rindex(']')+1]); CG={}
for stn,nm,encp in CROWS:
  ps=[]
  for rs in encp:
    rings=[dec(f,1000) for f in rs if len(f)>=6]
    if rings: ps.append(Polygon(rings[0],rings[1:]).buffer(0))
  if ps: CG.setdefault(stn,[]).append((MultiPolygon([q for g in ps for q in (g.geoms if hasattr(g,'geoms') else [g]) if not q.is_empty]),nm))
NAMEF=['PRECINCTNA','PRECINCT_N','PREC_NAME','PCT_NAME','PRECNAME','NAME','PRECINCT','NAME10','VTDNAME','PCTNAME','WP_NAME','MUNINAME','LABEL','ENR_DESC','SRPREC','PRECINCTID','PREC_ID','VTDST10','VTDST','VTD','GEOID10']
S=10000
def enc(ring):
  out=[];px=py=0
  for x,y in ring:
    X=round(x*S);Y=round(y*S); out+=[X-px,Y-py]; px,py=X,Y
  return out
CREDIT="Voting and Election Science Team (VEST), 2016 General Election precinct boundaries and results, Harvard Dataverse doi:10.7910/DVN/NH5S2I, CC BY 4.0. County = v2 county (v2/data/uscounties.js) containing the precinct's representative point (nearest county if none). Shapes simplified to ~40 m. Total = all presidential candidates in the VEST file. Exact precinct results, no area weighting."
os.makedirs(od,exist_ok=True); report={}
for z in sorted(glob.glob(vd+'/*.zip')):
  ab=os.path.basename(z)[:2]; st=AB.get(ab)
  if not st or (only and ab not in only): continue
  xd=f'{vd}/x_{ab}'
  if not os.path.isdir(xd): zipfile.ZipFile(z).extractall(xd)
  shps=[s for s in glob.glob(f'{xd}/**/*.shp',recursive=True)]
  if not shps: print(st,'no shapefile'); continue
  shp=max(shps,key=os.path.getsize)
  r=shapefile.Reader(shp,encoding='latin-1'); fn=[f[0] for f in r.fields][1:]
  pre=[f for f in fn if f.upper().startswith('G16PRE')]
  dem=[f for f in pre if f.upper().startswith('G16PRED')]; rep=[f for f in pre if f.upper().startswith('G16PRER')]
  nf=next((f for f in NAMEF if f in fn),None) or next((f for f in fn if 'NAME' in f.upper() or 'PREC' in f.upper()),None)
  prjf=shp[:-4]+'.prj'; prj=open(prjf).read() if os.path.exists(prjf) else ''
  tf=Transformer.from_crs(CRS.from_wkt(prj),4326,always_xy=True).transform if prj and CRS.from_wkt(prj).is_projected else None
  cg=CG.get(st); tree=STRtree([g for g,_ in cg]) if cg else None
  rows=[];cnt={};near=0;zero=0
  for sr in r.shapeRecords():
    rec=sr.record.as_dict()
    try: g=shape(sr.shape.__geo_interface__)
    except Exception: continue
    if g.is_empty: continue
    if tf: g=transform(tf,g)
    if not g.is_valid: g=g.buffer(0)
    d=sum(int(rec.get(f) or 0) for f in dem); rp=sum(int(rec.get(f) or 0) for f in rep); tot=sum(int(rec.get(f) or 0) for f in pre)
    if tot<=0: zero+=1; continue
    if cg:
      p=g.representative_point(); idx=[i for i in tree.query(p) if cg[i][0].contains(p)]
      if not idx: idx=[min(range(len(cg)),key=lambda i:cg[i][0].distance(p))]; near+=1
      cn=cg[idx[0]][1]
    else: cn=st  # DC: v2 key 'District of Columbia|District of Columbia'
    P=g
    nm=str(rec.get(nf) or '').strip() if nf else ''
    if not nm: nm=str(len(rows))
    town=None
    if ab=='nj': town=str(rec.get('MUNINAME') or '').strip()
    elif ab in ('ct','ri'): town=re.sub(r'[\s\-]*[0-9][0-9A-Za-z\-]*$','',nm).strip()
    rows.append([cn,nm,d,rp,tot,P,town])
    c=cnt.setdefault(cn,[0,0,0]); c[0]+=d; c[1]+=rp; c[2]+=tot
  # NJ, CT, RI: v2's 2020 files are town-level and small; dissolve 2016 precincts to towns (exact sums, no weighting) to stay within size
  if ab in ('nj','ct','ri'):
    grp={}
    for x in rows:
      k=(x[0],x[6] or x[1]); grp.setdefault(k,[]).append(x)
    rows=[[k[0],k[1],sum(x[2] for x in v),sum(x[3] for x in v),sum(x[4] for x in v),unary_union([x[5] for x in v]).buffer(0),None] for k,v in grp.items()]
  os.makedirs(f'{vd}/geom',exist_ok=True)
  pickle.dump([(x[0],x[1],x[2],x[3],x[4],x[5].wkb) for x in rows],open(f'{vd}/geom/{ab}.pkl','wb'))
  rows=[x[:6] for x in rows]
  seen={}
  for x in rows: seen[(x[0],x[1])]=seen.get((x[0],x[1]),0)+1
  k2={}
  for x in rows:
    if seen[(x[0],x[1])]>1: k2[(x[0],x[1])]=k2.get((x[0],x[1]),0)+1; x[1]=f'{x[1]} ({k2[(x[0],x[1])]})'
  out=f'{od}/{st.replace(" ","_")}.js'
  # size cap = smallest existing v2 equivalent (2020 / 2024 precinct file of the same state)
  caps=[os.path.getsize(f) for f in (f'{REPO}/data/precincts2020/{st.replace(" ","_")}.js',f'{REPO}/data/precincts2024/{st.replace(" ","_")}.js',f'{REPO}/v2/data/precincts2020-DC.js' if st=='District of Columbia' else '') if f and os.path.exists(f) and os.path.getsize(f)>1000]
  cap=min(caps) if caps else None; geoms=[x[5] for x in rows]
  for tol in (0.0004,0.0006,0.0008,0.0012,0.0016,0.0024,0.0032,0.0048):
    for x,g in zip(rows,geoms):
      gs=g.simplify(tol,preserve_topology=True)
      if gs.is_empty: gs=g
      polys=[gs] if gs.geom_type=='Polygon' else [q for q in getattr(gs,'geoms',[]) if q.geom_type=='Polygon']
      x[5]=[[enc(list(q.exterior.coords))]+[enc(list(i.coords)) for i in q.interiors if i.length>5*tol] for q in polys if q.area>0] or [[enc(list(g.envelope.exterior.coords))]]
    body='__prec('+json.dumps(st)+','+json.dumps(rows,separators=(',',':'))+','+json.dumps(CREDIT)+');'
    if cap is None or len(body.encode())<=cap: break
  open(out,'w').write(body)
  sd=sum(v[0] for v in cnt.values()); sr_=sum(v[1] for v in cnt.values()); stt=sum(v[2] for v in cnt.values())
  report[st]={'file':os.path.basename(out),'bytes':os.path.getsize(out),'precincts':len(rows),'counties':len(cnt),'dem':sd,'rep':sr_,'total':stt,'nearest_county':near,'cap_bytes':cap,'tol':tol,'zero_vote_skipped':zero,'dem_fields':dem,'rep_fields':rep,'name_field':nf,'county':cnt,'vest_zip':os.path.basename(z)}
  print(f"{st}: tol {tol} cap {cap} {len(rows)} precincts, {len(cnt)} counties, D {sd} R {sr_} T {stt}, nearest {near}, zero {zero}, fields D{dem} R{rep} name {nf}, {os.path.getsize(out)/1e6:.1f} MB",flush=True)
  os.makedirs(f'{od}/../report',exist_ok=True); json.dump(report[st],open(f'{od}/../report/{ab}.json','w'),indent=0)
