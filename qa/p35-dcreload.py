# pass 32 (build 1611): DC picked (map address / All States row tap / All States address) > globe to map > reload: what comes back (title, thumbs, saved state, outline)
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
src=open('p32-orch-list-dc-globe.py').read(); exec(src[src.index('NMXY='):src.index('ADDR=')])
ADDR="1600 Pennsylvania Ave NW, Washington, DC 20500"
SNAP="()=>{for(const k of Object.keys(localStorage)){const v=localStorage.getItem(k);if(v&&v.startsWith('{\"v\":1'))return v}return null}"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for sc in ['mapaddr','dcrow','listaddr']:
      c,pg,log=await ctx(b,W,H,True,eng); R=out[sc]={}
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
      tap=lambda s: pg.evaluate(CEN,s)
      if sc!='mapaddr':
        await pg.touchscreen.tap(*(await tap('#bGeo'))); await pg.wait_for_timeout(1200)
        await pg.touchscreen.tap(*(await tap('li.la-row'))); await pg.wait_for_timeout(4000)
      if sc=='dcrow':
        await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'DC'))); await pg.wait_for_timeout(3500)
      else:
        await pg.touchscreen.tap(*(await tap('#gq'))); await pg.wait_for_timeout(600); await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(300)
        await pg.keyboard.type(ADDR,delay=20); await pg.wait_for_timeout(2500); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(6000)
      if sc!='mapaddr':
        await pg.touchscreen.tap(*(await tap('#bGlobe'))); await pg.wait_for_timeout(3000)
      R['before']=await pg.evaluate(ST); R['snap_before']=await pg.evaluate(SNAP)
      await pg.screenshot(path=f"shots35/b1614p35-{eng[:2]}-{W}x{H}-dcreload-{sc}-before.png")
      await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(5000)
      R['after']=await pg.evaluate(ST); R['snap_after']=await pg.evaluate(SNAP)
      await pg.screenshot(path=f"shots35/b1614p35-{eng[:2]}-{W}x{H}-dcreload-{sc}-after.png")
      R['err']=log['pageerr'][:3]
      print(sc,json.dumps(R)[:1500],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1614p35-dcreload-{eng}-{W}x{H}.json",'w'),indent=1)
asyncio.run(main())
