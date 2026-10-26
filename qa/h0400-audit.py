# Oct 26 ~4 AM (1622): town audit for the drilled counties (QA-134/135 family check): unassigned precincts, town totals vs county
import asyncio,json
from playwright.async_api import async_playwright
from common import *
JS="""async ([st,cn])=>{ const a=await window.__townAudit(st,cn); let x={}; try{ const rows=(PREC[st]||[]).filter(r=>r[0]===cn); const T=window.__townsIn(st,cn); const used=new Map(); const per=[]; for(const d of T){const g=window.__pri(d,PREC[st],cn); g.forEach(r=>used.set(r,(used.get(r)||0)+1)); per.push([d.n||d.name||String(d).slice(0,40),g.length,g.reduce((x,r)=>x+(+r[2]||0),0),g.reduce((x,r)=>x+(+r[3]||0),0)]);} const un=rows.filter(r=>!used.has(r)); const dup=[...used.values()].filter(v=>v>1).length; const s=(a,i)=>a.reduce((x,r)=>x+(+r[i]||0),0); x={un:[un.length,s(un,2),s(un,3),s(un,4)], cty:[rows.length,s(rows,2),s(rows,3),s(rows,4)], dup, per:per.sort((a,b)=>b[1]-a[1]).slice(0,12), unNames:un.map(r=>r[1]).slice(0,30)} }catch(e){x={e:String(e)}} return {audit:a.map(t=>({n:t.n,np24:t.np24,tot24:t.v24&&t.v24.tot,est:t.v24&&t.v24.est})).slice(0,30),x}; }"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
    out={}
    for st,cn in [('Indiana','Marion County'),('Michigan','Wayne County'),('Wisconsin','Milwaukee County'),('Arizona','Maricopa County'),('Ohio','Franklin County'),('Delaware','New Castle County'),('New Hampshire','Hillsborough County')]:
      try: r=await pg.evaluate(JS,[st,cn])
      except Exception as e: r={'EXC':str(e)[:300]}
      out[cn]=r; print(st,cn,json.dumps(r)[:2500],flush=True)
    json.dump(out,open('b1622h0400-audit.json','w'),indent=1)
asyncio.run(main())
