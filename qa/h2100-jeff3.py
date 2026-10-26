import asyncio,json
from playwright.async_api import async_playwright
from common import *
JS="""async ([st,cn])=>{ await window.__townAudit(st,cn); const rows=(PREC[st]||[]).filter(r=>r[0]===cn); const T=window.__townsIn(st,cn); const used=new Set(); let bal=null; for(const d of T){const g=window.__pri(d,PREC[st],cn); g.forEach(r=>used.add(r)); if(/balance/.test(d[2])) bal=g;} const un=rows.filter(r=>!used.has(r)); const s=(a,i)=>a.reduce((x,r)=>x+(+r[i]||0),0); return {un:[un.length,s(un,2),s(un,3),s(un,4)], bal:[bal.length,s(bal,2),s(bal,3),s(bal,4)], cty:[rows.length,s(rows,2),s(rows,3),s(rows,4)], unNames:un.map(r=>r[1]).slice(0,40)}; }"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
    r=await pg.evaluate(JS,['Kentucky','Jefferson County']); print(json.dumps(r)); json.dump(r,open('b1622h2100-jeff3.json','w'),indent=1)
asyncio.run(main())
