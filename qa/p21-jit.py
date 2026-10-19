# pass 21: sort chip + list rows bounce 6 px after the list stops at some scroll positions
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
SAMP="(ms)=>new Promise(res=>{const o=[];const t0=performance.now();const f=()=>{const t=performance.now()-t0;const c=document.getElementById('laSort').getBoundingClientRect();const r=[...document.querySelectorAll('#listView .lvrow')].find(e=>e.offsetParent).getBoundingClientRect();const lv=document.getElementById('listView');const v=[Math.round(c.top*10)/10,Math.round(r.top*10)/10,lv.scrollTop];if(!o.length||o[o.length-1][1]!=v[0]||o[o.length-1][2]!=v[1])o.push([Math.round(t),...v]);if(t<ms)requestAnimationFrame(f);else res(o)};requestAnimationFrame(f)})"
async def main():
  eng=sys.argv[1]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for W,H in ([(390,844),(1024,768),(320,568)] if len(sys.argv)<3 else [(int(sys.argv[2]),int(sys.argv[3]))]):
      c,pg,log=await ctx(b,W,H,W<600,eng)
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
      R=out[f'{W}x{H}']={}
      # 1) programmatic stops
      for st in [10,40,97]:
        await pg.evaluate(f"()=>{{document.getElementById('listView').scrollTop={st}}}"); fr=await pg.evaluate(SAMP,int(__import__("os").environ.get("MS","3000")))
        R[f'set{st}']=fr; print(eng,W,'scrollTop',st,len(fr),'changes',fr[:6],flush=True)
      await pg.evaluate("()=>{document.getElementById('listView').scrollTop=0}"); await pg.wait_for_timeout(1500)
      # 2) user-like: touch drag (chromium: CDP touch events) / wheel
      for dy in [40,60]:
        if eng=='chromium':
          cdp=await c.new_cdp_session(pg); x=W/2; y0=H*0.6
          await cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y0}]})
          for i in range(1,11): await cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y0-dy*i/10}]}); await pg.wait_for_timeout(16)
          await pg.wait_for_timeout(200); await cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        else:
          await pg.mouse.move(W/2,H*0.6); await pg.mouse.wheel(0,dy)
        await pg.wait_for_timeout(700); fr=await pg.evaluate(SAMP,int(__import__("os").environ.get("MS","3000"))); R[f'drag{dy}']=fr; print(eng,W,'drag',dy,len(fr),fr[:6],flush=True)
      await safeshot(pg,f'../shots/b1593p21-{eng[:2]}-{W}-jitter.png')
      R['build']=await pg.evaluate('window.BUILD'); await c.close()
    await b.close()
  json.dump(out,open(f'b1593p21-jit-{eng}.json','w'),indent=1)
asyncio.run(main())
