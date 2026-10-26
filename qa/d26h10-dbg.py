import asyncio
from playwright.async_api import async_playwright
from common import *
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True)
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    print(await pg.evaluate("()=>window.BUILD"))
    print(await center(pg,'#bGeo'))
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
    print(await pg.evaluate("()=>[...document.querySelectorAll('li.la-row')].map(e=>e.innerText.slice(0,40))"))
    await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
    print(await pg.evaluate("()=>[document.getElementById('crumbs').innerText,[...document.querySelectorAll('#listView .lvrow .nmx')].slice(0,8).map(e=>[e.textContent,!!e.offsetParent])]"))
    await pg.screenshot(path='shotsb1623/d26h10-dbg.png')
    await b.close()
asyncio.run(main())
