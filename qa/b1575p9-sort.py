# pass 9: repeat sort-chip taps in WebKit/Chromium at a size, measure tap-to-next-paint
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
async def main():
  eng,W,H=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]); out=[]
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for run in range(2):
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      xy=await center(pg,'#bGeo'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(1500)
      xy=await center(pg,'li.la-row'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
      L=[]
      for i in range(6):
        xy=await center(pg,'#laSort'); L.append(await tap_latency(pg,*xy)); await pg.wait_for_timeout(2200)
      out.append(L); await c.close()
    await b.close()
  print(eng,W,H,json.dumps(out))
asyncio.run(main())
