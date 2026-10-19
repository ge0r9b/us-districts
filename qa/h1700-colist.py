# hourly ~5PM: county via bottom field > globe (list) rows, and sort flip in the county drill list (Ohio > Franklin, Nevada > Clark)
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
ROWS="()=>[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).map(r=>r.innerText.replace(/\\n/g,' | ')).slice(0,5)"
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
ST="()=>({crumbs:document.getElementById('crumbs').innerText,list:document.body.classList.contains('listmode'),n:document.querySelectorAll('#listView .lvrow.la').length,sort:(document.getElementById('laSort')||{}).innerText,lv:window.__laInfo().on?window.__laInfo().lv:'-'})"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for st,co in [('Ohio','Franklin'),('Nevada','Clark')]:
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
      R=out[st]={}
      await typegq(pg,f'{co} County, {"OH" if st=="Ohio" else "NV"}'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(5000)
      R['gq_globe']={'st':await pg.evaluate(ST),'rows':await pg.evaluate(ROWS)}; await safeshot(pg,f"shotsh1700/b1618h7-{eng[:2]}-{W}x{H}-colist-{co}-gqglobe.png")
      await c.close(); c,pg,log2=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await typegq(pg,st); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
      xy=await pg.evaluate(NMXY,co); await pg.wait_for_timeout(400); await pg.touchscreen.tap(*(await pg.evaluate(NMXY,co))); await pg.wait_for_timeout(5000)
      R['drill']={'st':await pg.evaluate(ST),'rows':await pg.evaluate(ROWS)}
      if await center(pg,'#laSort'):
        R['lat_flip']=await tap_latency(pg,*(await center(pg,'#laSort'))); await pg.wait_for_timeout(2000); R['flip']={'st':await pg.evaluate(ST),'rows':await pg.evaluate(ROWS)}
        await safeshot(pg,f"shotsh1700/b1618h7-{eng[:2]}-{W}x{H}-colist-{co}-flip.png")
        await pg.touchscreen.tap(*(await center(pg,'#laSort'))); await pg.wait_for_timeout(2000); R['back']={'st':await pg.evaluate(ST),'rows':await pg.evaluate(ROWS)}
      R['err']=log['pageerr']+log2['pageerr']+[x for x in log['console']+log2['console'] if x.startswith('error')][:4]
      print(st,json.dumps(R),flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1618h1700-colist-{eng}-{W}x{H}.json",'w'),indent=1)
asyncio.run(main())
