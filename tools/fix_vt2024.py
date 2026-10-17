#!/usr/bin/env python3
"""Vermont 2024 state house, state senate and town school districts from the official town returns.
Source: Vermont Secretary of State election archive (electionarchive.vermont.gov/elections/search/date:2024-11-05),
as compiled by the MIT Election Data + Science Lab (github.com/MEDSL/2024-elections-official, vt24.csv, CC0).
Vermont reports the presidential vote by town, and for towns split between House districts by each district part
(e.g. Essex: 'Chittenden 23' and 'Chittenden 24'; Rutland City: 'Rutland 4' to 'Rutland 7'). Each reporting unit
lies in exactly one House district and one Senate district (taken from the State House / State Senate rows of the
same unit), so district totals are exact sums (flag None for 2024). Harris and Trump per county equal the official
county totals in data/election2024.js (checked here). Total = all named candidates (write-ins, blanks and spoiled
ballots excluded, as in the official county table).
School districts: a gray school district named '<Town> School District' gets that town's exact total when the town
is one reporting unit or the sum of its district parts. Unorganized gores/grants with no reporting unit stay gray.
usage: fix_vt2024.py <repo> <vt24.csv> [--dry]"""
import sys,json,csv,collections,re
repo,csvf=sys.argv[1],sys.argv[2]; dry='--dry' in sys.argv
E=json.loads(re.search(r'=(\{.*\})',open(f"{repo}/data/election2024.js").read(),re.S).group(1))
R=list(csv.DictReader(open(csvf)))
def nd(s): return re.sub(r'[\s\-]+',' ',s.upper()).strip()
U=collections.defaultdict(lambda:[0,0,0]); UC={}; HD=collections.defaultdict(set); SD=collections.defaultdict(set)
for x in R:
  k=(x['jurisdiction_name'],x['precinct'])
  if x['office']=='US PRESIDENT':
    if x['candidate'] in ('TOTAL VOTES CAST','BLANKS','SPOILED','WRITE-IN') or x['writein']=='TRUE': continue
    v=int(x['votes']); a=U[k]; a[2]+=v; UC[k]=x['county_name'].title()+' County'
    if x['party_simplified']=='DEMOCRAT': a[0]+=v
    elif x['party_simplified']=='REPUBLICAN': a[1]+=v
  elif x['office']=='STATE HOUSE': HD[k].add(nd(x['district']))
  elif x['office']=='STATE SENATE': SD[k].add(nd(x['district']))
cs=collections.defaultdict(lambda:[0,0,0])
for k,a in U.items():
  for i in range(3): cs[UC[k]][i]+=a[i]
print('county check (D,R,total) vs official:',[(c,a,E['Vermont|'+c]) for c,a in cs.items() if a!=E['Vermont|'+c][:3]] or 'all equal')
def ldw(p):
  s=open(p).read(); i=s.index('[',s.index('(')); j=s.rindex(']')+1; return s,i,j,json.loads(s[i:j])
NAME={}  # Census SLDL code -> district name (Census TIGER 2024 tl_2024_50_sldl NAMELSAD; SLDU codes are county abbreviations)
SLDL={'A':'ADDISON','B':'BENNINGTON','C':'CHITTENDEN','CA':'CALEDONIA','E':'ESSEX','F':'FRANKLIN','L':'LAMOILLE','O':'ORLEANS','OR':'ORANGE','R':'RUTLAND','W':'WINDHAM','WA':'WASHINGTON','Y':'WINDSOR'}
SPECIAL={'A-R':'ADDISON RUTLAND','B-R':'BENNINGTON RUTLAND','C-F':'CHITTENDEN FRANKLIN','CAE':'CALEDONIA ESSEX','CAW':'CALEDONIA WASHINGTON','E-C':'ESSEX CALEDONIA','E-O':'ESSEX ORLEANS','GIC':'GRAND ISLE CHITTENDEN','L-W':'LAMOILLE WASHINGTON','O-L':'ORLEANS LAMOILLE','ORC':'ORANGE CALEDONIA','OWA':'ORANGE WASHINGTON ADDISON','R-B':'RUTLAND BENNINGTON','R-W':'RUTLAND WINDSOR','WAC':'WASHINGTON CHITTENDEN','WAO':'WASHINGTON ORANGE','WWB':'WINDHAM WINDSOR BENNINGTON','Y-A':'WINDSOR ADDISON','Y-W':'WINDSOR WINDHAM','YO1':'WINDSOR ORANGE 1','YO2':'WINDSOR ORANGE 2'}
def hname(c):
  if c in SPECIAL: return SPECIAL[c]
  m=re.match(r'^([A-Z]+)-?(\d+)$',c); return SLDL[m.group(1)]+' '+str(int(m.group(2)))
SEN={'ADD':'ADDISON','BEN':'BENNINGTON','CAL':'CALEDONIA','CHC':'CHITTENDEN CENTRAL','CHN':'CHITTENDEN NORTH','CHS':'CHITTENDEN SOUTHEAST','ESX':'ESSEX','FRA':'FRANKLIN','GRI':'GRAND ISLE','LAM':'LAMOILLE','ORA':'ORANGE','ORL':'ORLEANS','RUT':'RUTLAND','WAS':'WASHINGTON','WDH':'WINDHAM','WSR':'WINDSOR'}
# district of each reporting unit
from shapely.geometry import Polygon,MultiPolygon
def mp(enc,S=1000):
  ps=[]
  for rg in enc:
    rings=[]
    for f in rg:
      o=[];x=y=0
      for k in range(0,len(f)-1,2): x+=f[k]; y+=f[k+1]; o.append((x/S,y/S))
      if len(o)>=3: rings.append(o)
    if rings: ps.append(Polygon(rings[0],rings[1:]))
  g=MultiPolygon(ps); return g if g.is_valid else g.buffer(0)
HN={d for v in HD.values() for d in v}; L={}
for fn in ('ussldl','ussldu'): L[fn]=ldw(f'{repo}/v2/data/{fn}.js')
HG={hname(r[1]):mp(r[2]) for r in L['ussldl'][3] if r[0]=='Vermont'}; SG={SEN[r[1]]:mp(r[2]) for r in L['ussldu'][3] if r[0]=='Vermont'}
HINT={'GI':'GRAND ISLE','CHI CT':'CHITTENDEN CENTRAL'}
UH={};US={};bad=[];how=collections.Counter()
for k in U:
  m=re.match(r'^([A-Za-z .\-]+?)[ -](\d+)(?:\s+(.*?))?(?:\s+\d+)?$',k[1]); h=None
  if m and nd(m.group(1))+' '+m.group(2) in HN: h=nd(m.group(1))+' '+m.group(2); how['house: unit named after its district']+=1
  elif nd(k[1]) in HN and k[0]!=nd(k[1]): h=nd(k[1]); how['house: unit named after its district']+=1
  elif len(HD.get(k,()))==1: h=next(iter(HD[k])); how['house: own State House row']+=1
  if not h: bad.append(('house',k,HD.get(k))); continue
  UH[k]=h; sd=None
  if len(SD.get(k,()))==1: sd=next(iter(SD[k])); how['senate: own State Senate row']+=1
  elif m and m.group(3) and nd(m.group(3)) in HINT: sd=HINT[nd(m.group(3))]; how['senate: unit name (Gi / Chi Ct)']+=1
  else:
    ov={n:HG[h].intersection(g).area/HG[h].area for n,g in SG.items()}; n,a=max(ov.items(),key=lambda x:x[1])
    if a>=0.95: sd=n; how[f'senate: House district part lies >=95 % in one Senate district']+=1; print('  senate by geometry:',k,h,'->',n,round(a,3))
  if not sd: bad.append(('senate',k,SD.get(k))); continue
  US[k]=sd
print('unit assignment:',dict(how),'unresolved:',bad)
if bad: sys.exit('unresolved reporting units')
rep={}
for fn,M,nm in (('ussldl',UH,hname),('ussldu',US,lambda c:SEN[c])):
  acc=collections.defaultdict(lambda:[0,0,0])
  for k,a in U.items():
    for i in range(3): acc[M[k]][i]+=a[i]
  s,i,j,data=L[fn]; path=f'{repo}/v2/data/{fn}.js'; ch=[]; names=set(acc)
  for r in data:
    if r[0]!='Vermont': continue
    n=nm(r[1])
    if n not in acc: print('no returns for',fn,r[1],n); continue
    v=acc[n]; names.discard(n); old=r[3] if len(r)>3 else None; fl=r[5] if len(r)>5 else None
    while len(r)<5: r.append(None)
    nf='e20' if fl in ('e20','est') else None
    ch.append((r[1],old,fl,v,nf)); r[3]=v
    if nf: r[5:]=[nf]
    else: del r[5:]
  if names: sys.exit(f'{fn}: districts in the returns not in the app: {names}')
  rep[fn]=ch
  if not dry: open(path,'w').write(s[:i]+json.dumps(data,separators=(',',':'))+s[j:])
# town school districts (gray only)
TOWN=collections.defaultdict(lambda:[0,0,0])
for k,a in U.items():
  for i in range(3): TOWN[k[0]][i]+=a[i]
path=f'{repo}/v2/data/ussch.js'; s,i,j,data=ldw(path); ch=[]; left=[]
for r in data:
  if r[0]!='Vermont' or (len(r)>3 and r[3]): continue
  m=re.match(r'^(.*) School District$',r[1]); t=m.group(1).upper().replace('SAINT ','ST. ') if m else None
  if t and t in TOWN:
    fl=r[5] if len(r)>5 else None
    while len(r)<5: r.append(None)
    r[3]=TOWN[t]; nf='e20' if fl in ('e20','est') else None
    if nf: r[5:]=[nf]
    else: del r[5:]
    ch.append((r[1],None,fl,TOWN[t],nf))
  else: left.append(r[1])
rep['ussch']=ch; print('ussch filled',[c[0] for c in ch],'left (no reporting unit):',left)
if not dry: open(path,'w').write(s[:i]+json.dumps(data,separators=(',',':'))+s[j:])
json.dump(rep,open('/workspace/db/fix_vt2024_report.json','w'))
for fn,ch in rep.items():
  dif=[(c[0],round(abs(c[3][1]/c[3][2]-c[1][1]/c[1][2])*100,2),round((c[3][2]/c[1][2]-1)*100,1),c[2]) for c in ch if c[1]]
  dif.sort(key=lambda x:-x[1])
  print(fn,'written',len(ch),'previously gray',sum(1 for c in ch if not c[1]),'largest R-share change (pts, total %, old flag):',dif[:6])
