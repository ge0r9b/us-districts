#!/usr/bin/env python3
"""Add VEST 2020 precinct results (Harvard Dataverse doi:10.7910/DVN/K7760H, CC BY 4.0) to data/precincts2020/<State>.js
for the counties that the existing 2020 file does not cover. Existing rows are kept (they match the 2024 shapes by hash).
County = Census 2020 cartographic county containing the precinct's representative point (names = Census NAMELSAD, same as the app).
QC: per-county Biden+Trump vs ELECTION2020 official county totals; counties outside 0.9-1.1 are dropped (not used) and reported.
usage: build_vest2020.py <vest_dir> <repo_dir> <st> [<st>...]"""
import sys,os,glob,json,re,shapefile
from pyproj import CRS,Transformer
from shapely.ops import transform
from shapely.geometry import shape
from shapely.strtree import STRtree
vd,repo=sys.argv[1],sys.argv[2]; sts=sys.argv[3:]
NAMES={'al':'Alabama','ak':'Alaska','az':'Arizona','ar':'Arkansas','ca':'California','co':'Colorado','ct':'Connecticut','de':'Delaware','fl':'Florida','ga':'Georgia','hi':'Hawaii','id':'Idaho','il':'Illinois','in':'Indiana','ia':'Iowa','ks':'Kansas','ky':'Kentucky','la':'Louisiana','me':'Maine','md':'Maryland','ma':'Massachusetts','mi':'Michigan','mn':'Minnesota','ms':'Mississippi','mo':'Missouri','mt':'Montana','ne':'Nebraska','nv':'Nevada','nh':'New Hampshire','nj':'New Jersey','nm':'New Mexico','ny':'New York','nc':'North Carolina','nd':'North Dakota','oh':'Ohio','ok':'Oklahoma','or':'Oregon','pa':'Pennsylvania','ri':'Rhode Island','sc':'South Carolina','sd':'South Dakota','tn':'Tennessee','tx':'Texas','ut':'Utah','vt':'Vermont','va':'Virginia','wa':'Washington','wv':'West Virginia','wi':'Wisconsin','wy':'Wyoming'}
FIPS={'01':'Alabama','02':'Alaska','04':'Arizona','05':'Arkansas','06':'California','08':'Colorado','09':'Connecticut','10':'Delaware','12':'Florida','13':'Georgia','15':'Hawaii','16':'Idaho','17':'Illinois','18':'Indiana','19':'Iowa','20':'Kansas','21':'Kentucky','22':'Louisiana','23':'Maine','24':'Maryland','25':'Massachusetts','26':'Michigan','27':'Minnesota','28':'Mississippi','29':'Missouri','30':'Montana','31':'Nebraska','32':'Nevada','33':'New Hampshire','34':'New Jersey','35':'New Mexico','36':'New York','37':'North Carolina','38':'North Dakota','39':'Ohio','40':'Oklahoma','41':'Oregon','42':'Pennsylvania','44':'Rhode Island','45':'South Carolina','46':'South Dakota','47':'Tennessee','48':'Texas','49':'Utah','50':'Vermont','51':'Virginia','53':'Washington','54':'West Virginia','55':'Wisconsin','56':'Wyoming'}
E20=json.loads(open(repo+'/data/election2020.js').read().split('=',1)[1].strip().rstrip(';'))
cr=shapefile.Reader(vd+'/cty/cb_2020_us_county_500k'); CG=[];CN=[]
for sr in cr.shapeRecords():
  rec=sr.record.as_dict(); 
  CG.append(shape(sr.shape.__geo_interface__)); CN.append((FIPS.get(rec['STATEFP']),rec['NAMELSAD']))
tree=STRtree(CG)
NAMEF=['PRECINCT','PRECINCTNA','PRECINCT_N','NAME20','NAME','PCTNAME','WP_NAME','MUNINAME','LABEL','ENR_DESC','SRPREC','PRECINCTID','PREC_ID','VTDST20','VTDST','VTD']
S=10000
def enc(ring):
  out=[];px=py=0
  for x,y in ring:
    X=round(x*S);Y=round(y*S); out+=[X-px,Y-py]; px,py=X,Y
  return out
CREDIT=" Added for counties missing above: Voting and Election Science Team (VEST), 2020 General Election precinct boundaries and results, Harvard Dataverse doi:10.7910/DVN/K7760H, CC BY 4.0 (county = Census 2020 county containing the precinct; shapes simplified to ~40 m; total = all presidential candidates in the file)."
for s in sts:
  st=NAMES[s]; shp=glob.glob(f'{vd}/x_{s}/**/*.shp',recursive=True)[0]; r=shapefile.Reader(shp); fn=[f[0] for f in r.fields][1:]
  pre=[f for f in fn if f.startswith('G20PRE')]; nf=next((f for f in NAMEF if f in fn),None)
  out=f'{repo}/data/precincts2020/{st.replace(" ","_")}.js'
  old_rows=[];old_credit=''
  if os.path.exists(out):
    t=open(out).read(); a=json.loads('['+t[t.index(',')+1:t.rindex(');')]+']'); old_rows,old_credit=a[0],a[1]
  have={x[0] for x in old_rows}; new=[]; cnt={}
  prj=open(shp[:-4]+'.prj').read() if os.path.exists(shp[:-4]+'.prj') else ''
  tf=Transformer.from_crs(CRS.from_wkt(prj),4326,always_xy=True).transform if 'PROJCS' in prj else None
  for sr in r.shapeRecords():
    rec=sr.record.as_dict(); g=shape(sr.shape.__geo_interface__)
    if g.is_empty: continue
    if tf: g=transform(tf,g)
    dem=int(rec.get('G20PREDBID') or 0); rep=int(rec.get('G20PRERTRU') or 0); tot=sum(int(rec.get(f) or 0) for f in pre)
    if tot<=0: continue
    p=g.representative_point(); idx=[i for i in tree.query(p) if CG[i].contains(p)]
    if not idx: continue
    stn,cn=CN[idx[0]]
    if stn!=st or cn in have: continue
    gs=g.simplify(0.0004,preserve_topology=True)
    if gs.is_empty: gs=g
    polys=[gs] if gs.geom_type=='Polygon' else [q for q in gs.geoms if q.geom_type=='Polygon']
    P=[[enc(list(q.exterior.coords))]+[enc(list(i.coords)) for i in q.interiors if i.length>0.002] for q in polys if q.area>0]
    if not P: continue
    nm=str(rec.get(nf) or '').strip() if nf else ''
    if not nm: nm=str(rec.get('VTDST20') or rec.get('VTDST') or len(new))
    new.append([cn,nm,dem,rep,tot,P,rec.get('VTDST20') or rec.get('VTDST') or rec.get('PRECINCTID') or ''])
    c=cnt.setdefault(cn,[0,0,0]); c[0]+=dem; c[1]+=rep; c[2]+=tot
  # QC against official county results
  good=set();bad=[];allc=set()
  for cn,(d,rp,t) in cnt.items():
    e=E20.get(st+'|'+cn); allc.add(cn)
    if not e: bad.append((cn,'no official row')); continue
    ratio=(d+rp)/max(1,e[0]+e[1])
    (good.add(cn) if 0.9<=ratio<=1.1 else bad.append((cn,round(ratio,3))))
  keep=[x for x in new if x[0] in good]
  # make duplicate names unique inside a county
  seen={}
  for x in keep:
    k=(x[0],x[1]); seen[k]=seen.get(k,0)+1
  dup={k for k,v in seen.items() if v>1}
  rows=[]
  for x in keep:
    nm=x[1]+(' ('+str(x[6])+')' if (x[0],x[1]) in dup and x[6] else '')
    rows.append([x[0],nm,x[2],x[3],x[4],x[5]])
  total_rows=old_rows+rows
  if not rows: print(st,'nothing added',bad[:5]); continue
  credit=(old_credit+CREDIT) if old_credit else CREDIT.strip()
  open(out,'w').write('__prec('+json.dumps(st)+','+json.dumps(total_rows,separators=(',',':'))+','+json.dumps(credit)+');')
  print(f"{st}: +{len(rows)} precincts in {len(good)} counties (kept existing {len(old_rows)}); dropped counties {len(bad)}: {bad[:6]}; file {os.path.getsize(out)/1e6:.1f} MB",flush=True)
