import asyncio,json
from playwright.async_api import async_playwright
from common import *
Q=[('Pennsylvania','Allegheny County','Pittsburgh city'),('Pennsylvania','Allegheny County','Baldwin township'),('Wisconsin','Kenosha County','Kenosha city'),('Wisconsin','Kenosha County','Pleasant Prairie village'),('North Carolina','Alamance County','Burlington city'),('North Carolina','Alamance County','Graham city'),('Georgia','Clayton County','Forest Park city'),('Georgia','Clayton County','Morrow city'),('Vermont','Chittenden County','Burlington city'),('Rhode Island','Kent County','Warwick city'),('Pennsylvania','Montgomery County','Pottstown borough'),('Pennsylvania','Montgomery County','West Pottsgrove township'),('Massachusetts','Hampden County','Chicopee city'),('Michigan','Washtenaw County','Ann Arbor city'),('Ohio','Cuyahoga County','Cleveland city'),('Ohio','Cuyahoga County','Brook Park city'),('Iowa','Linn County','Hiawatha city'),('Connecticut','New Haven County','Milford city (balance)'),('Connecticut','New Haven County','Milford town')]
JS="""async ([st,cn,tn])=>{ await window.__townAudit(st); const rows=(PREC[st]||[]).filter(r=>r[0]===cn); const T=window.__townsIn(st,cn).filter(d=>d[2]===tn); return T.map(d=>{const g=window.__pri(d,PREC[st],cn); return {n:g.length,v:g.reduce((s,r)=>s+(+r[4]||0),0),p:g.map(r=>String(r[1])).filter(x=>!x.toLowerCase().includes(tn.split(' ')[0].toLowerCase())).slice(0,8)};}); }"""
async def main():
  out={}
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await pg.goto(URL+'?cb=1621p',wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4000)
    for q in Q:
      try: r=await pg.evaluate(JS,list(q))
      except Exception as e: r=str(e)[:150]
      out['|'.join(q)]=r; print(q[2],r,flush=True)
    json.dump(out,open('b1621x-pri.json','w'),indent=1); await b.close()
asyncio.run(main())
