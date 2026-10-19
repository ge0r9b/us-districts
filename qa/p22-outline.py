import asyncio,sys,json
sys.path.insert(0,'/workspace/w/lanes/qa/qa')
from playwright.async_api import async_playwright
from common import *
async def main():
  eng=sys.argv[1]
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for tag,W,H,mob in [VPS[0],VPS[4]]:
      c,pg,log=await ctx(b,W,H,mob,eng)
      await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
      s=tag.replace('iphone','').replace('ipad','')
      await pg.fill('#gq','Pennsylvania'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      await pg.screenshot(path=f'../shots/b1595p22-{eng[:2]}-{s}-PA-map.png')
      try:
        await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(1000)
        btn=pg.locator('button:has-text("US House")').first
        bb=await btn.bounding_box(); await pg.touchscreen.tap(bb['x']+bb['width']/2,bb['y']+bb['height']/2); await pg.wait_for_timeout(5000)
        await pg.screenshot(path=f'../shots/b1595p22-{eng[:2]}-{s}-PA-ushouse.png')
      except Exception as e: print('lyr',e)
      st=await pg.evaluate("()=>[...document.querySelectorAll('.leaflet-overlay-pane path, .leaflet-overlay-pane canvas')].slice(0,400).reduce((m,e)=>{const w=e.getAttribute&&e.getAttribute('stroke-width');m[w]=(m[w]||0)+1;return m},{})")
      print(tag,json.dumps({'strokes':st,'err':log['pageerr'][:3],'cons':[x for x in log.get('console',[])][:3],'build':await pg.evaluate('window.BUILD')}),flush=True)
      await c.close()
    await b.close()
asyncio.run(main())
