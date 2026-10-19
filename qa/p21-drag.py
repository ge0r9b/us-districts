import asyncio,sys
sys.path.insert(0,'/workspace/w/lanes/qa/qa')
from playwright.async_api import async_playwright
from common import *
Q="()=>{const g=e=>{const q=document.getElementById(e).getBoundingClientRect();return [Math.round(q.top),Math.round(q.bottom)]};const vv=window.visualViewport;return {b:window.BUILD,st:document.getElementById('listView').scrollTop,chip:g('laSort'),geo:g('barGeo'),time:g('bTime'),vv:[vv.offsetTop,vv.pageTop,vv.scale,scrollY],row:Math.round([...document.querySelectorAll('#listView .lvrow')].find(e=>e.offsetParent).getBoundingClientRect().top)}}"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
    print('start',await pg.evaluate(Q))
    cdp=await c.new_cdp_session(pg)
    for dy in [40,40,-80,20]:
      x=195; y0=500
      await cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y0}]})
      for i in range(1,11): await cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y0-dy*i/10}]}); await pg.wait_for_timeout(16)
      await pg.wait_for_timeout(200); await cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
      await pg.wait_for_timeout(1500); print('drag',dy,await pg.evaluate(Q))
    await pg.screenshot(path='/workspace/w/lanes/qa/shots/b1594p21-ch-390-drag-chip.png')
    await b.close()
asyncio.run(main())
