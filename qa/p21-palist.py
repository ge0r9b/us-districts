import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
async def run(b,eng,variant,old):
  c,pg,log=await ctx(b,390,844,True,eng)
  if old:
    html=open(old).read()
    await pg.route("**/us-districts/v2/", lambda r: r.fulfill(status=200,content_type="text/html",body=html))
  await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4500)
  if variant=='enter': await typegq(pg,'Pennsylvania'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
  elif variant=='mapTap':
    xy=await pg.evaluate("()=>{const q=window.__map.latLngToContainerPoint([40.9,-77.6]);const r=window.__map.getContainer().getBoundingClientRect();return [q.x+r.left,q.y+r.top]}")
    await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
  elif variant=='enterWait': await typegq(pg,'Pennsylvania'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(12000)
  crumbs=await pg.evaluate("()=>(document.getElementById('crumbs')||{}).innerText")
  xy=await center(pg,'#bGlobe'); l=await tap_latency(pg,*xy); await pg.wait_for_timeout(9000)
  r=await pg.evaluate("()=>[document.body.className.slice(0,120),document.querySelectorAll('#listView .lvrow').length,JSON.stringify(window.__laInfo()).slice(0,120),window.BUILD]")
  await pg.screenshot(path=f'../shots/b1592p21-{eng[:2]}-390-palist-{variant}-{"old" if old else "live"}.png')
  print(eng,variant,old,crumbs,l,r,log['pageerr'][:2],flush=True); await c.close()
async def main():
  async with async_playwright() as p:
    for eng in (sys.argv[1:] or ['chromium','webkit']):
      b=await getattr(p,eng).launch()
      for v in ['enter','mapTap','enterWait']: await run(b,eng,v,None)
      if False:
        await run(b,eng,'enter','/tmp/v1587/v2/index.html'); await run(b,eng,'mapTap','/tmp/v1587/v2/index.html'); await run(b,eng,'enter','/tmp/v1588/v2/index.html')
      await b.close()
asyncio.run(main())
