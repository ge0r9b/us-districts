# pass 13: WebKit back chevron at the precinct level: touch tap vs element.click()
import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
LV="()=>window.__laInfo&&window.__laInfo().lv"
ROW="()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent)[0];if(!r)return null;const q=r.getBoundingClientRect();return [q.left+60,q.top+q.height/2]}"
async def main():
  W,H=int(sys.argv[1]),int(sys.argv[2]); out={}
  async with async_playwright() as p:
    b=await p.webkit.launch()
    c,pg,log=await ctx(b,W,H,W<600,'webkit')
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    out['build']=await pg.evaluate('window.BUILD')
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
    await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
    xy=await pg.evaluate("()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()==='PA'});if(!r)return null;r.scrollIntoView({block:'center'});const q=r.getBoundingClientRect();return [q.left+60,q.top+q.height/2]}")
    await pg.wait_for_timeout(600); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
    for i in range(2): await pg.touchscreen.tap(*(await pg.evaluate(ROW))); await pg.wait_for_timeout(6000)
    out['start']=await pg.evaluate(LV)
    bb=await pg.evaluate("()=>{const e=document.getElementById('bBack');if(!e)return null;const r=e.getBoundingClientRect();const x=r.left+r.width/2,y=r.top+r.height/2;const t=document.elementFromPoint(x,y);return {r:[r.left,r.top,r.width,r.height],top:t?(t.id||t.className||t.nodeName).toString().slice(0,40):null,pe:getComputedStyle(e).pointerEvents}}")
    out['bBack']=bb
    await pg.evaluate("()=>{window.__ev=[];['touchstart','touchend','pointerdown','pointerup','click'].forEach(t=>document.addEventListener(t,e=>window.__ev.push(t+':'+((e.target.id||e.target.className||e.target.nodeName)+'').slice(0,20)),true))}")
    await pg.touchscreen.tap(*(await center(pg,'#bBack'))); await pg.wait_for_timeout(3000)
    out['after_touch']=await pg.evaluate(LV); out['events']=await pg.evaluate("window.__ev")
    await safeshot(pg,f"../shots/b1579p13-we-{W}-back-after-touch.png")
    await pg.evaluate("()=>document.getElementById('bBack').click()"); await pg.wait_for_timeout(3000)
    out['after_click']=await pg.evaluate(LV)
    await pg.locator('#bBack').tap(); await pg.wait_for_timeout(3000)
    out['after_locator_tap']=await pg.evaluate(LV)
    out['err']=log['pageerr'][:3]
    print(json.dumps(out),flush=True); json.dump(out,open(f'b1579p13-wkback-{W}.json','w'),indent=1)
asyncio.run(main())
