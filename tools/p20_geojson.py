# export 2020 precinct rows (repo data/precincts2020/<St>.js) of the given counties as GeoJSON (props county,name,d,r,t)
import json,sys
A='/workspace/w/us-districts-app/'
st=sys.argv[1]; cs=set(sys.argv[2].split(',')); yr=sys.argv[3] if len(sys.argv)>3 else '2020'
s=open(f"{A}data/precincts{yr}/{st.replace(' ','_')}.js").read(); R=json.loads('['+s[s.index(',')+1:s.rindex(');')]+']')[0]
def rings(enc,S=10000):
  out=[]
  for rg in enc:
    poly=[]
    for f in rg:
      o=[];x=y=0
      for k in range(0,len(f)-1,2): x+=f[k]; y+=f[k+1]; o.append([x/S,y/S])
      if len(o)>=3: o.append(o[0]); poly.append(o)
    if poly: out.append(poly)
  return out
F=[]
for r in R:
  if r[0] in cs: F.append({'type':'Feature','properties':{'county':r[0],'name':r[1],'d':r[2],'r':r[3],'t':r[4]},'geometry':{'type':'MultiPolygon','coordinates':rings(r[5])}})
fn=f"/workspace/db/src/p20/{st.replace(' ','_')}_{yr}.geojson"
json.dump({'type':'FeatureCollection','features':F},open(fn,'w')); print(fn,len(F))
