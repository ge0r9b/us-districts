import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq,ST
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for stn in ['Georgia','Texas','Washington','New Mexico']:
      c,pg,log=await ctx(b,390,844,True,'chromium'); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await typegq(pg,stn); await pg.wait_for_timeout(800)
      sug=await pg.evaluate("()=>[...document.querySelectorAll('#gsug *,.sug,[role=option]')].map(e=>e.innerText.trim()).filter(Boolean).slice(0,8)")
      await pg.keyboard.press("Enter"); await pg.wait_for_timeout(4500)
      st=await pg.evaluate(ST)
      xy=await center(pg,'#bLyr'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(1200)
      keys=await pg.evaluate("()=>[...document.querySelectorAll('#lyrRow .lbtn')].map(b=>[b.dataset.k,b.offsetWidth>0])")
      await safeshot(pg,f"../shots/b1585p18-ch-390-{stn}-layers.png")
      print(stn,'sug',sug,'crumb',st.get('crumb'),'keys',keys,log['pageerr'][:2],flush=True); await c.close()
asyncio.run(main())
