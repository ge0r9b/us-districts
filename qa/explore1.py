import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    ids=await pg.evaluate("()=>[...document.querySelectorAll('button,[id]')].filter(e=>e.offsetParent||e.tagName=='BUTTON').map(e=>e.tagName+'#'+e.id+'.'+(e.className||'').toString().slice(0,30)+' ['+(e.getAttribute('aria-label')||'')+'] '+(e.textContent||'').trim().slice(0,20)).slice(0,120)")
    print('\n'.join(ids))
    print([k for k in await pg.evaluate("()=>Object.keys(window).filter(k=>k.startsWith('__')||/^[A-Z0-9_]+$/.test(k))")])
    x,y=await center(pg,'#bGeo'); print('lat bGeo',await tap_latency(pg,x,y)); await pg.wait_for_timeout(1500)
    await pg.screenshot(path="../shots/chromium-iphone390-geo-open.png")
    print(await pg.evaluate("()=>[...document.querySelectorAll('li')].filter(e=>e.offsetParent).map(e=>e.className+': '+e.textContent.trim().slice(0,50)).slice(0,30)"))
    await c.close(); await b.close()
asyncio.run(main())
