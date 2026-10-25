import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
JS=open('b1620-gate.py').read().split('JS="""')[1].split('"""')[0]
JS=JS.replace("return out; }","""out.empty=[]; out.townTot={}; for(const cn of cs){ let T=[]; try{T=window.__townsIn(st,cn);}catch(e){continue;} for(const d of T){ const g=window.__pri(d,rows,cn); const gv=g.reduce((s,r)=>s+(+r[4]||0),0); let geoN=0,geoV=0; for(const r of rows){ if(r[0]!==cn) continue; const [x,y]=cen(r); if(inPolys(d[3],x,y)){geoN++;geoV+=(+r[4]||0);} } if(cn==='Franklin County'||/Gloucester|Alpena|Royal Oak|Bristol|Skokie|Baldwin/.test(d[2])) out.townTot[cn+'|'+d[2]]={gN:g.length,gV:gv,geoN,geoV}; if(g.length===0&&geoN>0) out.empty.push({c:cn,t:d[2],geoN,geoV}); } } return out; }""")
async def main():
  sts=sys.argv[1].split(','); res=[]
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await pg.goto(URL+'?cb=1621',wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(3000)
    print('BUILD',await pg.evaluate("window.BUILD"))
    for st in sts:
      try: r=await pg.evaluate(JS,st)
      except Exception as e: r={'st':st,'err':str(e)[:200]}
      print(st,r.get('nprec'),r.get('ntowns'),'moved',len(r.get('moved',[])),'dups',len(r.get('dups',[])),'empty',len(r.get('empty',[])),r.get('err',''),flush=True); res.append(r)
    json.dump(res,open('b1621x-empty-%s.json'%sys.argv[2],'w'),indent=0)
    await b.close()
asyncio.run(main())
