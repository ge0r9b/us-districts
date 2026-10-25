# Oct 25 10AM: full row-name order in % vs # mode (state counties list + county places list)
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
NMS="()=>[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).map(r=>{const n=r.querySelector('.nmx');return (n?n.textContent:r.innerText.split('\\n')[0]).trim()})"
NM="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim()===t);if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    await typegq(pg,sys.argv[3]); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
    await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
    async def cap(k):
      o={}
      for m in ['pct','num','pct']:
        await pg.evaluate(f"()=>window.__setNum('{m}')"); await pg.wait_for_timeout(2000); o.setdefault(m,[]).append(await pg.evaluate(NMS))
      out[k]={'pct1':o['pct'][0],'num':o['num'][0],'pct2':o['pct'][1],'same_pn':o['pct'][0]==o['num'][0],'same_pp':o['pct'][0]==o['pct'][1],
        'diff':[(i,a,b) for i,(a,b) in enumerate(zip(o['pct'][0],o['num'][0])) if a!=b][:10]}
      print(k,out[k]['same_pn'],out[k]['same_pp'],len(o['pct'][0]),out[k]['diff'],flush=True)
    await cap('state')
    await pg.evaluate(NM,sys.argv[4]); await pg.wait_for_timeout(400); await pg.touchscreen.tap(*(await pg.evaluate(NM,sys.argv[4]))); await pg.wait_for_timeout(5000)
    await cap('county'); await safeshot(pg,f"shotsh1000/b1618h10-{eng[:2]}-{W}x{H}-order-{sys.argv[4]}.png")
    json.dump(out,open(f"b1618h1000-order-{eng}-{W}x{H}-{sys.argv[4]}.json",'w'),indent=1); await b.close()
asyncio.run(main())
