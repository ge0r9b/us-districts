# pass 23: tap-to-next-paint of slider year taps on PA district-type maps (repeat 3x each direction)
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for typ in sys.argv[4].split(','):
      c,pg,log=await ctx(b,W,H,W<600,eng)
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await typegq(pg,'Pennsylvania'); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
      if typ!='map':
        await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(900)
        l=await tap_latency(pg,*(await center(pg,f'.lbtn[data-k={typ}]'))); await pg.wait_for_timeout(5000)
        if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(800)
      else: l=None
      if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(1000)
      R=out[typ]={'layer':l,'y':[]}
      for rep in range(3):
        for i,yr in [(0,'16'),(2,'24'),(1,'20'),(2,'24')]:
          xy=await pg.evaluate("i=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();const N=w.querySelectorAll('.tk').length;return [r.left+52+i/(N-1)*(r.width-104),r.top+r.height/2]}",i)
          v=await tap_latency(pg,*xy); R['y'].append((yr,v)); await pg.wait_for_timeout(4000)
      R['mode']=await pg.evaluate("()=>window.__ymode()"); R['err']=log['pageerr'][:3]+[x for x in log['console'] if x.startswith('error')][:3]
      if typ=='statehouse': await safeshot(pg,f'../shots/b1611p32-{eng[:2]}-{W}x{H}-ylat-PA-{typ}.png')
      print(eng,W,H,typ,json.dumps(R),flush=True); await c.close()
    await b.close()
  json.dump(out,open(f'b1611p32-ylat-{eng}-{W}x{H}.json','w'),indent=1)
asyncio.run(main())
