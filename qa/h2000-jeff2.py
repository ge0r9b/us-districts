import asyncio,json
from playwright.async_api import async_playwright
from common import *
JS="""async ([st,cn])=>{ await window.__townAudit(st,cn); const rows=(PREC[st]||[]).filter(r=>r[0]===cn); const T=window.__townsIn(st,cn); const used=new Map(); const per=[]; for(const d of T){const g=window.__pri(d,PREC[st],cn); per.push([d[2],g.length,g.reduce((s,r)=>s+(+r[4]||0),0)]); g.forEach(r=>used.set(r,(used.get(r)||0)+1));} const un=rows.filter(r=>!used.has(r)); const dbl=rows.filter(r=>(used.get(r)||0)>1); const sum=a=>a.reduce((s,r)=>s+(+r[4]||0),0); return {sample:rows[0], nrows:rows.length, tot:sum(rows), nun:un.length, unv:sum(un), unSample:un.slice(0,12).map(r=>r.slice(0,7)), ndbl:dbl.length, dblv:sum(dbl), per:per.sort((a,b)=>b[2]-a[2]).slice(0,4)}; }"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
    out={}
    for st,cn in [('Kentucky','Jefferson County'),('Kentucky','Fayette County'),('Tennessee','Davidson County'),('Indiana','Marion County'),('Georgia','Clarke County'),('Kansas','Wyandotte County')]:
      try: r=await pg.evaluate(JS,[st,cn])
      except Exception as e: r=str(e)[:200]
      out[st+'|'+cn]=r; print(cn,json.dumps(r)[:1500],flush=True)
    json.dump(out,open('b1621h2000-jeff2.json','w'),indent=1)
asyncio.run(main())
