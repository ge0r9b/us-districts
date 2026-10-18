# pass 14: DC > district type (schools/ushouse/senate) > list
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq,ST
CANDS="()=>[...document.querySelectorAll('.cand')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' '))"
ROWS="()=>[...document.querySelectorAll('#listView .lvrow.la')].slice(0,3).map(r=>r.innerText.replace(/\\n/g,' | '))"
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for k in ['schools','ushouse']:
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await typegq(pg,'District of Columbia'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      R=out[k]={'start':await pg.evaluate(ST),'cands0':await pg.evaluate(CANDS)}
      await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(1200)
      xy=await center(pg,f'#lyrRow .lbtn[data-k={k}]'); R['btn']=bool(xy)
      if xy:
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(4000); R['map']=await pg.evaluate(ST); R['cands_map']=await pg.evaluate(CANDS)
        await safeshot(pg,f"../shots/b1582p14-{eng[:2]}-{W}-DC-{k}-map.png")
        await pg.touchscreen.tap(10,H//2); await pg.wait_for_timeout(800)
        await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(6000)
        R['list']=await pg.evaluate(ST); R['rows']=await pg.evaluate(ROWS); R['n']=await pg.evaluate("()=>document.querySelectorAll('#listView .lvrow.la').length"); R['cands_list']=await pg.evaluate(CANDS)
        await safeshot(pg,f"../shots/b1582p14-{eng[:2]}-{W}-DC-{k}-list.png")
      R['build']=await pg.evaluate('window.BUILD'); R['err']=log['pageerr'][:3]
      print(k,json.dumps(R)[:900],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f'b1583p14-dcschools-{eng}-{W}.json','w'),indent=1)
asyncio.run(main())
