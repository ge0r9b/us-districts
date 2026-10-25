# Oct 25 6PM (1621): QA-129 follow-up: list body after geo entry with vs without a district type
import asyncio,sys,json,os
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
exec(open('p38-fresh.py').read().split('\nasync def main')[0].split('from gaps import typegq',1)[1])
LV="()=>{const v=document.getElementById('listView');return {n:[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).length,txt:v?v.innerText.slice(0,160):null,vis:v?!!v.offsetParent:null,first:[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).slice(0,3).map(r=>r.innerText.replace(/\\n/g,' | '))}}"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for q in sys.argv[3].split('|'):
     for typ in [1,0]:
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(2500)
      if typ:
        await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(800)
        await pg.touchscreen.tap(*(await center(pg,'#lyrRow .lbtn[data-k=ushouse]'))); await pg.wait_for_timeout(2500)
        await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(1500)
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1300)
      inp=await pg.evaluate(INP); await pg.touchscreen.tap(inp[0][2],inp[0][3]); await pg.wait_for_timeout(500)
      await pg.keyboard.type(q,delay=30); await pg.wait_for_timeout(1500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      if not await pg.evaluate("()=>document.getElementById('sheet').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bGeo')))
      await pg.wait_for_timeout(4000); a=await pg.evaluate(LV); await pg.wait_for_timeout(8000); bb=await pg.evaluate(LV)
      k=f"{q}|type={typ}"; out[k]={'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH),'at4s':a,'at12s':bb,'err':log['pageerr']+[x for x in log['console'] if x.startswith('error')][:4]}
      await safeshot(pg,f"shotsb1621/b1621h18-{eng[:2]}-{W}x{H}-q129-{q.replace(' ','')}-type{typ}.png")
      print(json.dumps({k:out[k]}),flush=True); await c.close()
    json.dump(out,open(f"b1621h1800-q129-{eng}-{W}x{H}.json",'w'),indent=1); await b.close()
asyncio.run(main())
