#!/usr/bin/env python3
"""Idaho 2024: Owyhee and Idaho counties from the official Idaho Secretary of State precinct file
(archive.sos.idaho.gov/elections/data/results/2024/raw_races_general.xlsx, public record).
The app's 2024 file had 1 of 12 Owyhee precincts and 23 of 27 Idaho County precincts.
Shapes: the 2020 precinct shapes of the same names in data/precincts2020/Idaho.js (VEST 2020, CC BY 4.0), reused
verbatim (identical encoding, so 2020 and 2024 pair as the same precinct). The county-wide absentee precinct is
allocated to the precincts in proportion to each candidate group's (Harris, Trump, other) election-day votes, so
the county totals equal the official totals; precinct figures are therefore estimates.
usage: fix_id2024.py <xlsx> <repo>"""
import sys,json,re,collections,openpyxl
xl,repo=sys.argv[1],sys.argv[2]
def norm(s): s=re.sub(r'^\d+-','',str(s)).upper().strip(); return s.replace(' II',' 2').replace(' I',' 1').replace('SLATE CREEK 1','SLATE CREEK 1')
OFF=collections.defaultdict(lambda:[0,0,0])
ws=openpyxl.load_workbook(xl,read_only=True)['raw_races']
for c,p,rt,race,party,cand,v in ws.iter_rows(min_row=2,values_only=True):
  if race!='United States President' or c not in ('Owyhee County','Idaho County'): continue
  a=OFF[(c,str(p))]; v=int(v or 0); a[2]+=v
  if 'Harris' in cand: a[0]+=v
  elif 'Trump' in cand: a[1]+=v
t=open(repo+'/data/precincts2020/Idaho.js').read(); P20=json.loads('['+t[t.index(',')+1:t.rindex(');')]+']')[0]
SH={(r[0],norm(r[1])):r[5] for r in P20 if r[0] in ('Owyhee County','Idaho County')}
NM={(r[0],norm(r[1])):r[1] for r in P20 if r[0] in ('Owyhee County','Idaho County')}  # 2020 name kept so the same-name-and-shape rule pairs the years
p24=repo+'/data/precincts2024/Idaho.js'; t=open(p24).read(); A=json.loads('['+t[t.index(',')+1:t.rindex(');')]+']'); rows,credit=A[0],A[1]
new=[]
for cty in ('Owyhee County','Idaho County'):
  ed={k[1]:v for k,v in OFF.items() if k[0]==cty and 'ABSENTEE' not in k[1].upper()}
  ab=next(v for k,v in OFF.items() if k[0]==cty and 'ABSENTEE' in k[1].upper())
  sd=sum(v[0] for v in ed.values()); sr=sum(v[1] for v in ed.values()); so=sum(v[2]-v[0]-v[1] for v in ed.values())
  miss=[p for p in ed if (cty,norm(p)) not in SH]
  if miss: sys.exit(f'{cty}: no 2020 shape for {miss}')
  for p,(d,r,tt) in sorted(ed.items()):
    o=tt-d-r; D=d+ab[0]*d/max(1,sd); R=r+ab[1]*r/max(1,sr); O=o+(ab[2]-ab[0]-ab[1])*o/max(1,so) if so else o
    new.append([cty,NM[(cty,norm(p))],round(D),round(R),round(D)+round(R)+round(O),SH[(cty,norm(p))]])
  print(cty,len(ed),'precincts; official',[sum(v[i] for k,v in OFF.items() if k[0]==cty) for i in range(3)],'rows',[sum(x[i] for x in new if x[0]==cty) for i in (2,3,4)])
rows=[r for r in rows if r[0] not in ('Owyhee County','Idaho County')]+new
note=" Owyhee and Idaho counties (build 1534): official Idaho Secretary of State 2024 precinct results (raw_races_general.xlsx, public record), county absentee ballots allocated to precincts in proportion to election-day votes (estimates); shapes = 2020 VEST precinct shapes of the same names (CC BY 4.0)."
credit=(credit if isinstance(credit,str) else json.dumps(credit)); credit=credit.split(' Owyhee and Idaho counties (build')[0]+note
open(p24,'w').write('__prec("Idaho",'+json.dumps(rows,separators=(',',':'))+','+json.dumps(credit)+');')
