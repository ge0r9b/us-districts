import asyncio,json
from playwright.async_api import async_playwright
from common import *
ROWS="()=>{const s=document.getElementById('sheet')||document.body;const L=[...s.querySelectorAll('li')].filter(e=>e.offsetParent&&e.innerText.trim());return L.slice(0,8).map(e=>e.innerText.replace(/\\n/g,' ').slice(0,40))}"
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); c,pg,log=await ctx(b,1024,768,False,'webkit'); await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    o={'build':await pg.evaluate("()=>window.BUILD")}
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
    await pg.touchscreen.tap(*(await center(pg,'#barGeo .fsq input'))); await pg.keyboard.type('America',delay=30); await pg.wait_for_timeout(1500)
    o['America']=await pg.evaluate(ROWS); await safeshot(pg,'../shots/b1601p26-we-1024x768-inst-America.png'); print(json.dumps(o))
asyncio.run(main())
