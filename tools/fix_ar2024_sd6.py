#!/usr/bin/env python3
"""Arkansas State Senate district 6, 2024 (gray after build 1534).
Sources: MEDSL 2024 official precinct returns (github.com/MEDSL/2024-elections-official, ar24.csv, CC0; compiled from
the Arkansas Secretary of State results), and the official Arkansas precinct and Senate boundaries (Arkansas GIS Office,
gis.arkansas.gov/arcgis/rest/services/FEATURESERVICES/Boundaries/FeatureServer, layer 11 ELECTION_PRECINCTS and layer 34
SENATE_DISTRICTS; public government data). SD 6 lies in Garland and Saline counties.
Why the generic tool could not do it: the SD 6 race was uncontested (one candidate, heavy undervote), and units with no
Senate race on the ballot could not be placed without shapes. Method here:
 - a returns unit (county, precinct; Garland names like "014 16" carry a ballot-style suffix, the first 3 digits are the
   precinct) is matched to the precinct shape of the same number; its share of SD 6 = area(precinct n SD 6)/area(precinct);
 - share >= 0.98 and an SD 6 race on its ballot -> counted whole (exact); share < 0.01 and no SD 6 race -> outside;
 - anything in between is a split precinct: apportioned by its SD 6 race votes relative to the SD 6 undervote rate of the
   county's whole precincts (votes_SD6 / (president_total * rate)), capped at 1, keeping the unit's party split. The
   district is then an estimate ('e24'); the apportioned votes must stay <= 30 % of the district (repo rule).
 - every unit with an SD 6 race must be matched to a shape that overlaps SD 6, and every shape overlapping SD 6 must be
   matched to a returns unit; the county Harris/Trump sums must equal the official county totals; else abort.
usage: fix_ar2024_sd6.py <repo> <ar24.csv> <precincts.geojson> <senate.geojson> [--dry]"""
import sys,csv,json,re,collections
from shapely.geometry import shape
repo,csvf,pf,sf=sys.argv[1:5]; dry='--dry' in sys.argv
E=json.loads(re.search(r'=(\{.*\})',open(f"{repo}/data/election2024.js").read(),re.S).group(1))
CTY={'GARLAND':'Garland County','SALINE':'Saline County'}
SKIP=('WRITE','OVER','UNDER','BLANK')
U=collections.defaultdict(lambda:[0,0,0]); SD=collections.Counter(); CS=collections.defaultdict(lambda:[0,0,0])
for x in csv.DictReader(open(csvf)):
  if x['county_name'] not in CTY: continue
  k=(x['county_name'],x['precinct']); v=int(float(x['votes'] or 0))
  if x['office']=='US PRESIDENT':
    if x['writein']=='TRUE' or any(s in x['candidate'].upper() for s in SKIP): continue
    a=U[k]; c=CS[x['county_name']]; a[2]+=v; c[2]+=v
    if x['party_simplified']=='DEMOCRAT': a[0]+=v; c[0]+=v
    elif x['party_simplified']=='REPUBLICAN': a[1]+=v; c[1]+=v
  elif x['office']=='STATE SENATE' and x['district'].lstrip('0')=='6' and not any(s in x['candidate'].upper() for s in SKIP): SD[k]+=v
for c,a in CS.items():
  o=E['Arkansas|'+CTY[c]]
  print(c,'returns',a,'official',o[:3])
  if abs(a[0]-o[0])>max(2,0.001*o[0]) or abs(a[1]-o[1])>max(2,0.001*o[1]): sys.exit('county not equal to official')
s6=[shape(f['geometry']).buffer(0) for f in json.load(open(sf))['features'] if int(f['properties']['ndistrict'])==6][0]
SH={}
for f in json.load(open(pf))['features']:
  p=f['properties']; c=(p['county_name'] or '').upper()
  if c not in CTY: continue
  g=shape(f['geometry']).buffer(0); n=int(re.match(r'\d+',p['precinct']).group())
  SH[(c,n)]=g.intersection(s6).area/g.area if g.intersects(s6) else 0.0
def pn(c,x): return int(float(x)) if c=='SALINE' else int(x.split()[0])
share={}; acc=[0.0,0.0,0.0]; app=0.0; cls=collections.Counter(); rows=[]
for k,a in U.items():
  c=k[0]; n=pn(c,k[1]); s=SH.get((c,n))
  if s is None: sys.exit(f'no shape for {k}')
  share[k]=s
whole={c:[sum(SD[k] for k in U if k[0]==c and share[k]>=0.98 and SD[k]),sum(U[k][2] for k in U if k[0]==c and share[k]>=0.98 and SD[k])] for c in CTY}
rate={c:w[0]/w[1] for c,w in whole.items() if w[1]}
print('SD 6 race votes / president total in whole precincts:',{c:round(r,3) for c,r in rate.items()})
for k,a in U.items():
  s=share[k]; v=SD[k]
  if s>=0.98 and v: w=1.0; cls['whole']+=1
  elif s<0.01 and not v: cls['outside']+=1; continue
  elif s<0.01 and v: sys.exit(f'{k} has SD 6 votes but its shape is outside SD 6')
  elif s>=0.98 and not v: sys.exit(f'{k} is inside SD 6 but has no SD 6 race')
  else:
    w=min(1.0,v/(a[2]*rate[k[0]])); cls['split']+=1; app+=a[2]*w
  for i in range(3): acc[i]+=a[i]*w
  rows.append((k,a,v,round(s,3),round(w,3)))
used={(k[0],pn(k[0],k[1])) for k in U}
miss=[k for k,s in SH.items() if s>=0.01 and k not in used]
if miss: sys.exit(f'shapes in SD 6 with no returns: {miss}')
for r in sorted(rows,key=lambda r:r[4]):
  if r[4]<1: print(' split',r)
v=[round(x) for x in acc]; pct=app/acc[2]
print(dict(cls),'SD 6 2024 (Harris, Trump, total):',v,f'apportioned {app:.0f} votes = {pct:.1%}')
if pct>0.30: sys.exit('apportioned share over 30 %')
fn=f'{repo}/v2/data/ussldu.js'; s=open(fn).read(); i=s.index('[',s.index('(')); j=s.rindex(']')+1; data=json.loads(s[i:j])
for r in data:
  if r[0]=='Arkansas' and r[1]=='006':
    old=r[5] if len(r)>5 else None
    while len(r)<5: r.append(None)
    r[3]=v; nf=('est' if old in ('e20','est') else 'e24') if app>0 else old
    if nf: r[5:]=[nf]
    print('row',r[0],r[1],r[3:])
if not dry: open(fn,'w').write(s[:i]+json.dumps(data,separators=(',',':'))+s[j:])
