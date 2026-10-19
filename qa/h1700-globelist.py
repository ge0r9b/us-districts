# hourly ~5PM: map > globe > list rows at US, state and county level (fresh, no district type)
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
ROWS="()=>[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).map(r=>r.innerText.replace(/\\n/g,' | ')).slice(0,3)"
ST="()=>({crumbs:document.getElementById('crumbs').innerText,list:document.body.classList.contains('listmode'),n:document.querySelectorAll('#listView .lvrow.la').length,lv:window.__laInfo().on?window.__laInfo().lv:'-',la:window.__stateSnapshot().la})"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for q in ['','Ohio','Franklin County, OH','Georgia','Fulton County, GA','Philadelphia County, PA']:
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
      if q: await typegq(pg,q); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(6000)
      a=await pg.evaluate(ST); await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(5000)
      out[q or 'US']={'map':a,'list':await pg.evaluate(ST),'rows':await pg.evaluate(ROWS),'err':log['pageerr']}
      await safeshot(pg,f"shotsh1700/b1618h7-{eng[:2]}-{W}x{H}-globelist-{(q or 'US').split(',')[0].replace(' ','')}.png")
      print(q or 'US',json.dumps(out[q or 'US']),flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1618h1700-globelist-{eng}-{W}x{H}.json",'w'),indent=1)
asyncio.run(main())
