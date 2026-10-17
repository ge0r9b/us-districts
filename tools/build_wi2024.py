#!/usr/bin/env python3
"""Wisconsin 2024 precincts from the Wisconsin Legislative Technology Services Bureau (LTSB) "2024 Election Data with
2025 Wards" (gis-ltsb.hub.arcgis.com/datasets/LTSB::2024-election-data-with-2025-wards; FeatureServer
services1.arcgis.com/FDsAtKBk8Hy4cAH0/arcgis/rest/services/2024_Election_Data_with_2025_Wards/FeatureServer/0;
terms: "open and publicly available data", source LTSB, Wisconsin County Clerks and Land Information Offices).
LTSB takes the official Wisconsin Elections Commission reporting-unit results and disaggregates them to wards by
Census 2020 population, so ward figures are estimates while every county total is exact (checked here against
data/election2024.js: Harris and Trump equal in all 72 counties). Total = PRETOT24 - PRESCT24 (scattering write-ins
excluded, as in the official county table). Wards with no votes (no population) are left out.
Names: "<City|Village|Town> of <municipality> Ward <n>" (the voter-facing ward name). Replaces the whole file
(the NYT-merged file had 20 counties outside 90-110 % of the official total).
usage: build_wi2024.py <repo> <w_0.geojson> [...] --sct <sct.json> [--dry]"""
import sys,json,re,collections
from shapely.geometry import shape
repo=sys.argv[1]; gj=[a for a in sys.argv[2:] if a.endswith('.geojson')]; dry='--dry' in sys.argv
SCT=json.load(open(sys.argv[sys.argv.index('--sct')+1]))
E=json.loads(re.search(r'=(\{.*\})',open(f"{repo}/data/election2024.js").read(),re.S).group(1))
CN={k.split('|')[1].upper().replace(' COUNTY',''):k.split('|')[1] for k in E if k.startswith('Wisconsin|')}
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
TY={'C':'City','V':'Village','T':'Town'}
rows=[]; cs=collections.defaultdict(lambda:[0,0,0]); seen=collections.Counter()
for fn in gj:
  for f in json.load(open(fn))['features']:
    p=f['properties']
    if p['PRETOT24'] is None or not f['geometry']: continue
    c=CN[p['CNTY_NAME'].upper()]; d,r=p['PREDEM24'],p['PREREP24']; t=p['PRETOT24']-(SCT.get(p['GEOID'],{}).get('PRESCT24') or 0)
    if t<=0: continue
    w=re.sub(r'^0+','',str(p['WARDID'])) or '0'
    nm=f"{TY.get(p['CTV'],'')} of {p['MCD_NAME']} Ward {w}".strip()
    seen[(c,nm)]+=1
    if seen[(c,nm)]>1: nm+=f" ({seen[(c,nm)]})"
    g=shape(f['geometry'])
    if not g.is_valid: g=g.buffer(0)
    P=encg(g)
    if not P: continue
    rows.append([c,nm,d,r,max(t,d+r),P]); a=cs[c]; a[0]+=d; a[1]+=r; a[2]+=max(t,d+r)
bad=[(c,a,E['Wisconsin|'+c][:3]) for c,a in cs.items() if a[0]!=E['Wisconsin|'+c][0] or a[1]!=E['Wisconsin|'+c][1]]
print('wards',len(rows),'counties',len(cs),'not equal to official (Harris, Trump):',bad)
print('total',sum(a[2] for a in cs.values()),'official',sum(v[2] for k,v in E.items() if k.startswith('Wisconsin|')))
if bad: sys.exit('QC failed')
credit=("Wisconsin Legislative Technology Services Bureau, 2024 Election Data with 2025 Wards (open public data; official "
 "Wisconsin Elections Commission reporting-unit results disaggregated to wards by Census 2020 population, so ward figures are "
 "estimates; county totals exact).")
out=f'{repo}/data/precincts2024/Wisconsin.js'
if not dry: open(out,'w').write('__prec("Wisconsin",'+json.dumps(rows,separators=(',',':'))+','+json.dumps(credit)+');')
import os; print('file', round(os.path.getsize(out)/1e6,1),'MB')
