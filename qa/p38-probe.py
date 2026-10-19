import asyncio,json
from playwright.async_api import async_playwright
from common import *
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4000)
    print(await pg.evaluate("window.BUILD"))
    await pg.touchscreen.tap(*await center(pg,'#bGeo')); await pg.wait_for_timeout(1500)
    print(await pg.evaluate("()=>document.getElementById('sheet').outerHTML.slice(0,3000)"))
    print(await pg.evaluate("()=>[...document.querySelectorAll('button')].filter(b=>b.offsetParent).map(b=>(b.id||b.className)+':'+(b.getAttribute('aria-label')||b.innerText).slice(0,30))"))
    await pg.screenshot(path='shots38/b1616p38-ch-390x844-probe-geo.png'); await b.close()
asyncio.run(main())
