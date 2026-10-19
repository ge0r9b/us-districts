# pass 23: (a) what the list shows during the first-visit drill gap; (b) QA-076 bubble re-check
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
BUB="()=>{const e=document.getElementById('iconBub');const i=document.querySelector('#cands .cand img');const v=e=>{const r=e.getBoundingClientRect();return [Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]};return e?{t:e.textContent,b:v(e),img:v(i),vis:getComputedStyle(e).opacity}:null}"
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4500)
    # (b) bubble: chart bar on US, tap Trump photo
    await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
    await pg.touchscreen.tap(*((await center(pg,'#chartBox .copts button[data-ch=bar]')) or (await center(pg,'#chartBox .cmain')))); await pg.wait_for_timeout(2500); out['mode']=await pg.evaluate('()=>window.chartMode')
    xy=await center(pg,'#cands .cand img'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(500)
    out['bubble']=await pg.evaluate(BUB); await safeshot(pg,f'../shots/b1597p25-{eng[:2]}-{W}-bubble.png'); print(eng,W,'bubble',out['bubble'],flush=True)
    await pg.wait_for_timeout(3000)
    await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(800); await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(2000)
    # (a) first-visit drill gap
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
    for st in ['MA','OH']:
      xy=await pg.evaluate("t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim()===t);if(!e)return null;e.scrollIntoView({block:'nearest'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",st)
      await pg.wait_for_timeout(400); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(90)
      g=await pg.evaluate("()=>({rows:[...document.querySelectorAll('#listView .lvrow')].filter(e=>e.offsetParent).length,txt:document.getElementById('listView').innerText.slice(0,120),crumbs:document.getElementById('crumbs').innerText,thumbs:[...document.querySelectorAll('#laCands img')].filter(i=>i.offsetParent).length})")
      out['gap_'+st]=g; print(eng,W,'gap',st,g,flush=True); await safeshot(pg,f'../shots/b1597p25-{eng[:2]}-{W}-drillgap-{st}.png')
      await pg.wait_for_timeout(3000); await pg.touchscreen.tap(*(await center(pg,'#bBack'))); await pg.wait_for_timeout(3000)
    out['err']=log['pageerr'][:3]+[x for x in log['console'] if x.startswith('error')][:3]; print('err',out['err'])
    await c.close(); await b.close()
  json.dump(out,open(f'b1597p25-misc-{eng}-{W}x{H}.json','w'),indent=1)
asyncio.run(main())
