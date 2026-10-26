# Oct 26 ~10 AM (1623) copy of h0000-denver.py
# Oct 26 ~12 AM (1622): Denver County town rows vs county (city row 271K vs county 279K in h2300 sortchart)
import asyncio,json
from playwright.async_api import async_playwright
from common import *
JS="""async ([st,cn])=>{ const a=await window.__townAudit(st,cn); let x={}; try{ const rows=(PREC[st]||[]).filter(r=>r[0]===cn); const T=window.__townsIn(st,cn); const used=new Set(); for(const d of T){const g=window.__pri(d,PREC[st],cn); g.forEach(r=>used.add(r));} const un=rows.filter(r=>!used.has(r)); const s=(a,i)=>a.reduce((x,r)=>x+(+r[i]||0),0); x={un:[un.length,s(un,2),s(un,3),s(un,4)], cty:[rows.length,s(rows,2),s(rows,3),s(rows,4)], unNames:un.map(r=>r[1]).slice(0,40), sample:rows.slice(0,2)} }catch(e){x={e:String(e)}} return {audit:a,x}; }"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
    out={}
    for st,cn in [('Colorado','Denver County')]:
      r=await pg.evaluate(JS,[st,cn]); out[cn]=r; print(cn,json.dumps(r)[:3000])
    json.dump(out,open('b1623d26h10-denver.json','w'),indent=1)
asyncio.run(main())
