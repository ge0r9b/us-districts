# pass 36: QA-007 (All States row) and QA-102 ("Texas counties", Harris > Houston city) tap-to-paint, 3 reps each, Chromium 390 touch
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={'allstates':[],'txcounties':[],'harris':[],'houston':[]}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for rep in range(3):
      c,pg,log=await ctx(b,W,H,W<600,eng)
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(5000); out['build']=await pg.evaluate("window.BUILD")
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
      out['allstates'].append(await tap_latency(pg,*(await center(pg,'li.la-row')))); await pg.wait_for_timeout(4000)
      await typegq(pg,'Texas'); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      if (await pg.evaluate("()=>document.body.classList.contains('listmode')")): await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(3000)
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
      out['txcounties'].append(await tap_latency(pg,*(await center(pg,'li.la-row')))); await pg.wait_for_timeout(5000)
      xy=await pg.evaluate(NMXY,'Harris'); await pg.wait_for_timeout(400); xy=await pg.evaluate(NMXY,'Harris')
      if xy: out['harris'].append(await tap_latency(pg,*xy)); await pg.wait_for_timeout(5000)
      xy=await pg.evaluate(NMXY,'Houston'); await pg.wait_for_timeout(400); xy=await pg.evaluate(NMXY,'Houston')
      if xy: out['houston'].append(await tap_latency(pg,*xy)); await pg.wait_for_timeout(5000)
      if rep==0: await safeshot(pg,f'shotsh0600/b1618h6-{eng[:2]}-{W}x{H}-lat-houston.png')
      out.setdefault('err',[]).extend(log['pageerr']); print(rep,out,flush=True); await c.close()
    await b.close()
  json.dump(out,open(f'b1618h0600-lat-{eng}-{W}x{H}.json','w'),indent=1)
asyncio.run(main())
