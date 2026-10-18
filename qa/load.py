import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
async def main():
  eng=sys.argv[1]
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    out={}
    for tag,W,H,mob in VPS:
      c,pg,log=await ctx(b,W,H,mob,eng); t=time.time()
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000)
      info=await pg.evaluate("()=>({build:window.BUILD,cls:window.__cls,shifts:window.__shifts.slice(0,8),ow:document.documentElement.scrollWidth,iw:innerWidth})")
      info['load_s']=round(time.time()-t,1); info.update(log); out[tag]=info
      await pg.screenshot(path=f"../shots/{eng}-{tag}-initial.png"); await c.close()
    await b.close(); print(json.dumps(out,indent=1))
asyncio.run(main())
