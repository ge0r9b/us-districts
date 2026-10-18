import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    print(await pg.evaluate("()=>({body:document.body.className,crumbs:document.getElementById('crumbs').innerText,la:window.__laInfo()})"))
    await pg.screenshot(path='../shots/b1574-probe-load.png')
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    print(await pg.evaluate("()=>[...document.querySelectorAll('li.la-row, li')].filter(l=>l.offsetParent).slice(0,12).map(l=>l.className+': '+l.innerText.slice(0,40))"))
    await pg.screenshot(path='../shots/b1574-probe-geo.png')
    await c.close(); await b.close()
asyncio.run(main())
