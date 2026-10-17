# Rebuild failing 2024 counties from MEDSL official returns + the 2020 (VEST) boundaries of the same precincts, via fix_county2024.py.
# usage: county2024_from2020.py <State> <st abbr> "A County,B County" --credit TEXT [--write] [fix_county2024 options]; env REN (JSON rename map 'COUNTY|unit'), RXSUB ('regex|||repl' on unit names), SKIPGJ=1 (use a prepared geojson). Check afterwards with check_vs2020.py.
# driver: rebuild failing 2024 counties from MEDSL returns + 2020 precinct shapes of the same precincts (dry unless --write)
import sys,csv,collections,subprocess,json,os
st=sys.argv[1]; ab=sys.argv[2]; cs=sys.argv[3]; extra=sys.argv[4:]
src=f'/workspace/db/medsl24/{ab}24.csv'; out=f'/workspace/db/medsl24/{ab}24_t.csv'
if not os.path.exists(src):
  subprocess.run(f'cd /workspace/db/medsl24 && curl -sSfLO https://raw.githubusercontent.com/MEDSL/2024-elections-official/main/individual_states/{ab}24.zip && unzip -oq {ab}24.zip',shell=True)
R=csv.DictReader(open(src)); fn=R.fieldnames; rows=[r for r in R if r['office']=='US PRESIDENT']
modes=collections.defaultdict(set)
for r in rows: modes[(r['county_name'],r['precinct'])].add(r['mode'])
anyT=any('TOTAL' in m for m in modes.values())
w=csv.DictWriter(open(out,'w'),fieldnames=fn); w.writeheader()
REN=json.loads(os.environ.get('REN','{}'))
for r in rows:
  cu=r['candidate'].upper()
  if 'HARRIS' in cu: r['party_simplified']='DEMOCRAT'
  elif 'TRUMP' in cu: r['party_simplified']='REPUBLICAN'
  r['precinct']=REN.get(r['county_name']+'|'+r['precinct'],r['precinct'])
  if os.environ.get('RXSUB'):
    import re; pa,rp=os.environ['RXSUB'].split('|||'); r['precinct']=re.sub(pa,rp,r['precinct'])
  m=modes[(r['county_name'],r['precinct'])]
  if anyT and 'TOTAL' not in m: r['mode']='TOTAL'
  if anyT and 'TOTAL' in m and r['mode']!='TOTAL': continue
  w.writerow(r)
if not os.environ.get('SKIPGJ'): subprocess.run(['python3','/workspace/w/us-districts-app/tools/p20_geojson.py',st,cs],check=True)
cmd=['python3','tools/fix_county2024.py','.',st,out,f"/workspace/db/src/p20/{st.replace(' ','_')}_2020.geojson",'--cf','county','--nf','name','--counties',cs,
 '--pool',r'ABSENTEE|PROVISIONAL|PROVSIONAL|EARLY|MAIL|ONE STOP|CURBSIDE|UOCAVA|OVERSEAS|FEDERAL|COUNTYWIDE|COUNTY WIDE',
 '--fuzzy','0.3','--eliminate']+extra
if '--write' not in extra: cmd.append('--dry')
else: cmd.remove('--write')
p=subprocess.run(cmd,cwd='/workspace/w/us-districts-app',capture_output=True,text=True); print(p.stdout[-6000:],p.stderr[-2000:])
