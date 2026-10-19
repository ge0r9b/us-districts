import csv,re,json,subprocess,sys
REPO='/workspace/w/lanes/election-data'
def n(x): return int(x.replace(',','')) if x.strip() else 0
SRC={2016:'https://results.elections.ny.gov/contest/1650 (NYSBOE doc 116 "2016 General Election Results" p.2-3 for Trump REP+CON; NYSBOE contest 1650 county CSV for Clinton lines and Total-Blank-Void)',
     2020:'https://results.elections.ny.gov/contest/308 (NYSBOE contest 308 county CSV https://ny.elstats2.civera.com/eng/contests/download/308/show_granularity_dt_id:3/.csv; doc 128)',
     2024:'https://results.elections.ny.gov/contest/5591 (NYSBOE contest 5591 county CSV https://ny.elstats2.civera.com/eng/contests/download/5591/show_granularity_dt_id:3/.csv; doc 476)'}
def contest(id):
    r=list(csv.reader(open(f'raw/nysboe_contest_{id}_county.csv',encoding='utf-8',errors='replace')))
    h=r[0]; out={}
    for row in r[1:]:
        if not row or row[0] in ('Totals',''): continue
        rec=dict(zip(h,row)); c=row[0]
        D=sum(n(v) for k,v in rec.items() if k.startswith(('Hillary Clinton','Joseph R. Biden','Kamala D. Harris')))
        R=sum(n(v) for k,v in rec.items() if k.startswith(('Donald J. Trump',)))
        T=n(rec['Total Votes'])-n(rec['Blank'])-n(rec['Void'])
        cand=sum(n(v) for k,v in rec.items() if k not in ('County','Blank','Void','Total Votes'))
        out[c]=[D,R,T,cand]
    return out
def name(c):
    c={'St. Lawrence':'St. Lawrence'}.get(c,c)
    return c if c.endswith('County') else c+' County'
res={}
for y,id in ((2016,1650),(2020,308),(2024,5591)):
    o=contest(id); res[y]={}
    for c,(D,R,T,cand) in o.items():
        if y!=2016: assert cand==T,(y,c,cand,T)
        res[y][name(c)]=[D,R,T]
# 2016 Trump from PDF doc116 page 2-3 (cols: Clinton DEM, Trump REP, Trump CON, Stein GRE, Clinton WOR, Johnson IND, Clinton WEP, Johnson LBT)
txt=subprocess.run(['pdftotext','-layout','-f','2','-l','3','raw/nysboe_doc116.pdf','-'],capture_output=True,text=True).stdout
pdf={}
for l in txt.split('\n'):
    m=re.match(r'^\s*([A-Z][A-Za-z. ]+?)\s{2,}((?:[0-9,]+\s+){7}[0-9,]+)',l)
    if m and not m.group(1).startswith(('Total','Statewide','RECAP')):
        v=[n(x) for x in m.group(2).split()]; pdf[name(m.group(1))]=v
assert len(pdf)==62,len(pdf)
for c,v in pdf.items():
    D=v[0]+v[4]+v[6]; R=v[1]+v[2]
    assert D==res[2016][c][0],(c,D,res[2016][c])
    # csv 2016 lacks Trump columns: its non-Trump candidate sum + Trump must equal Total-Blank-Void
    res[2016][c][1]=R
c16=contest(1650)
for c,(D,R0,T,cand) in c16.items():
    assert cand+pdf[name(c)][1]+pdf[name(c)][2]==T,(c,)
for y in res:
    with open(f'ny_counties_{y}.csv','w',newline='') as f:
        w=csv.writer(f); w.writerow(['county','d','r','total','source_url'])
        for c in sorted(res[y]): w.writerow([c,*res[y][c],SRC[y]])
    print(y,len(res[y]),*[sum(v[i] for v in res[y].values()) for i in range(3)])
json.dump(res,open('ny_official.json','w'))
