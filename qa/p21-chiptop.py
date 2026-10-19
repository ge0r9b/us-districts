import asyncio,sys
sys.path.insert(0,'/workspace/w/lanes/qa/qa')
from playwright.async_api import async_playwright
from common import *
async def main():
  eng=sys.argv[1]
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,390,844,True,eng)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
    print(await pg.evaluate("()=>{const s=document.getElementById('laSort');const cs=getComputedStyle(s);return [s.style.cssText.slice(0,200),cs.transition.slice(0,100)]}"))
    o=[]
    for st in [15,20,22,25,28,30,35,0]:
      await pg.evaluate(f"()=>{{document.getElementById('listView').scrollTop={st}}}"); await pg.wait_for_timeout(900)
      o.append((st,await pg.evaluate("()=>[Math.round(document.getElementById('laSort').getBoundingClientRect().top),document.getElementById('laSort').style.cssText.slice(0,120)]")))
    for x in o: print(eng,x)
    await b.close()
asyncio.run(main())
