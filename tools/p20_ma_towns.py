# rename 2020 precinct features "<TOWN>_ward<W>_precinct<P>" (MEDSL MA style) using Census cousub spatial join; name '1' or 'W-P'
import json,sys,shapefile,re
from shapely.geometry import shape
fn=sys.argv[1]; sf=sys.argv[2]
d=json.load(open(fn)); T=[]
for sr in shapefile.Reader(sf).iterShapeRecords():
  a=sr.record.as_dict(); T.append((re.sub(r' TOWN$','',a['NAME'].upper()),shape(sr.shape.__geo_interface__)))
for f in d['features']:
  g=shape(f['geometry']).buffer(0); c=g.representative_point()
  best=max(T,key=lambda t:t[1].intersection(g).area if t[1].bounds[0]<=g.bounds[2] and t[1].bounds[2]>=g.bounds[0] and t[1].bounds[1]<=g.bounds[3] and t[1].bounds[3]>=g.bounds[1] else 0)
  n=f['properties']['name']; m=re.match(r'^(\d+)-(\d+)$',n)
  w,p=(m.group(1),m.group(2)) if m else ('0',n)
  f['properties']['name']=f"{best[0]}_ward{int(w)}_precinct{int(p) if p.isdigit() else p}"
json.dump(d,open(fn,'w'))
