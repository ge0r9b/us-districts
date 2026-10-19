# QA-110: type 'Georgia' in the geo field (no Enter): field icon vs first row icon
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
exec(open('p38-fresh.py').read().split('\nasync def main')[0].split('from gaps import typegq',1)[1])
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for q in ['Georgia','ohio','georgia']:
      c,pg,log=await ctx(b,W,H,W<600,eng); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1300)
      inp=await pg.evaluate(INP); await pg.touchscreen.tap(inp[0][2],inp[0][3]); await pg.wait_for_timeout(500)
      await pg.keyboard.type(q,delay=30); await pg.wait_for_timeout(1800)
      imgs=await pg.evaluate("()=>[...document.querySelectorAll('img')].filter(e=>e.offsetParent).map(e=>{const r=e.getBoundingClientRect();return [e.getAttribute('src').split('?')[0],Math.round(r.left),Math.round(r.top)]}).filter(x=>x[2]<140)")
      await safeshot(pg,f"shotsh1700/b1618h7-{eng[:2]}-{W}x{H}-110-{q}.png")
      print(eng,W,q,imgs,(await pg.evaluate(SHEET))[:2],await pg.evaluate("window.BUILD"),flush=True); await c.close()
    await b.close()
asyncio.run(main())
