# Oct 26 ~10 AM (1623): QA-138 follow-up: county town list, FIRST 2016 load via a range ('16-'24 = __ySet16(2)), then '16-'20, '20-'24, '16 single, '24, each with max main-thread gap and rows; chart button menu items listed.
import asyncio,sys,json,time
from playwright.async_api import async_playwright
from common import *
exec(open('h0800-chip.py').read().split('async def main')[0].split('from gaps import typegq')[1])
ROWS="()=>[...document.querySelectorAll('#listView .lvrow')].filter(e=>e.offsetParent).slice(0,4).map(e=>e.innerText.replace(/\\n/g,' ').slice(0,60))"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; path=sys.argv[3].split(':'); out={'steps':[]}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng); pre=f"shotsb1623/d26h10-{eng[:2]}-{W}x{H}-q138b-{'-'.join(path)}"
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
    for lvl in path:
      xy=await pg.evaluate(NMXY,lvl); await pg.wait_for_timeout(300); xy=await pg.evaluate(NMXY,lvl); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
    out['p16_before']=await pg.evaluate("()=>!!window.PREC16")
    for nm,js in [('r16-24','window.__ySet16(2)'),('r16-20','window.__ySet16(1)'),('r20-24','window.__ySelectAll()'),('y16','window.__ySetYr(0)'),('y24','window.__ySetYr(2)')]:
      await pg.evaluate("()=>{clearInterval(window.__hbI);window.__mg=0;let l=performance.now();window.__hbI=setInterval(()=>{const n=performance.now();window.__mg=Math.max(window.__mg,n-l);l=n},50)}")
      t0=time.time()
      try: await asyncio.wait_for(pg.evaluate(f"()=>{{{js};return 1}}"),60)
      except Exception as e: out['steps'].append([nm,'TIMEOUT']); continue
      t1=round(time.time()-t0,2); await pg.wait_for_timeout(2500)
      r=await asyncio.wait_for(pg.evaluate(ROWS),60); mg=await pg.evaluate("()=>Math.round(window.__mg)")
      th=await pg.evaluate("()=>[...document.querySelectorAll('#laCands .lact,.cand')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' '))")
      out['steps'].append([nm,t1,mg,th,r]); print(nm,t1,mg,th,r,flush=True); await safeshot(pg,f'{pre}-{nm}.png')
    out['err']=[log['pageerr'],[x for x in log['console'] if x.startswith('error')][:5]]; print(out['err'])
    json.dump(out,open(f"b1623d26h10-q138b-{eng}-{W}x{H}-{'-'.join(path)}.json",'w'),indent=1); await b.close()
asyncio.run(main())
