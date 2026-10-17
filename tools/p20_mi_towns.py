import json,sys,shapefile,re
from shapely.geometry import shape
fn=sys.argv[1]; d=json.load(open(fn)); T={};TL=[]
for sr in shapefile.Reader('/workspace/db/src/cousub_26/tl_2020_26_cousub').iterShapeRecords():
  a=sr.record.as_dict(); nm=a['NAMELSAD'].upper().replace('CHARTER TOWNSHIP','TOWNSHIP'); T[(a['COUNTYFP'],a['COUSUBFP'])]=nm; TL.append((nm,shape(sr.shape.__geo_interface__)))
for f in d['features']:
  n=f['properties']['name']; m=re.match(r'^(\d+)\s*\(WP-(\d{3})-(\d{5})-(\d+)\)',n)
  if m: f['properties']['name']=f"{T[(m.group(2),m.group(3))]} {int(m.group(1))}"
  else:
    g=shape(f['geometry']).buffer(0); b=max(TL,key=lambda t:t[1].intersection(g).area if t[1].intersects(g.envelope) else 0)
    f['properties']['name']=f"{b[0]} {int(re.match(r'\d+',n).group(0))}"
json.dump(d,open(fn,'w')); print(sorted(f['properties']['name'] for f in d['features']))
