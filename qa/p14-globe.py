# pass 14: does a touch tap on the globe button switch to the list after a district-type pick?
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    await typegq(pg,'Hawaii'); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4500)
    await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(1200)
    await pg.touchscreen.tap(*(await center(pg,'#lyrRow .lbtn[data-k=schools]'))); await pg.wait_for_timeout(4000)
    INFO="()=>{const e=document.getElementById('bGlobe');const r=e.getBoundingClientRect();const t=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return {r:[r.left,r.top,r.width,r.height],top:t?(t.id||String(t.className)||t.nodeName).slice(0,50):null,lyrOpen:!document.getElementById('lyrRow')||getComputedStyle(document.getElementById('lyrRow')).display,active:(document.activeElement||{}).id,list:document.body.classList.contains('listmode')}}"
    out['before']=await pg.evaluate(INFO)
    await pg.evaluate("()=>{window.__ev=[];['touchstart','touchend','pointerdown','pointerup','click'].forEach(t=>document.addEventListener(t,e=>window.__ev.push(t+':'+((e.target.id||e.target.className||e.target.nodeName)+'').slice(0,20)),true))}")
    await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(3000)
    out['after_tap']=await pg.evaluate(INFO); out['ev']=await pg.evaluate("window.__ev")
    await safeshot(pg,f"../shots/b1582p14-{eng[:2]}-{W}-globe-after-schools-tap.png")
    await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(3000)
    out['after_tap2']=await pg.evaluate(INFO); out['ev2']=await pg.evaluate("window.__ev")
    print(json.dumps(out),flush=True); json.dump(out,open(f'b1582p14-globe-{eng}-{W}.json','w'),indent=1)
    await c.close(); await b.close()
asyncio.run(main())
