import asyncio,json
from playwright.async_api import async_playwright
from common import *
VISTXT="(t)=>{const e=[...document.querySelectorAll('li,.lvrow,button,a')].filter(e=>e.offsetParent&&e.innerText&&e.innerText.trim().split('\\n')[0].trim()===t);if(!e.length)return null;const r=e[e.length-1];r.scrollIntoView({block:'center'});const b=r.getBoundingClientRect();return [b.left+Math.min(40,b.width/2),b.top+b.height/2]}"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await pg.goto(URL,wait_until="load"); await pg.wait_for_timeout(6000)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
    xy=await pg.evaluate(VISTXT,'Massachusetts'); print('MA',xy); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
    print(await pg.evaluate("()=>({crumbs:document.getElementById('crumbs').innerText,list:document.body.classList.contains('listmode'),items:[...document.querySelectorAll('li,.lvrow')].filter(e=>e.offsetParent).slice(0,12).map(e=>e.className+': '+e.innerText.replace(/\\n/g,' ').slice(0,40))})"))
    await pg.screenshot(path='../shots/b1574-probe2-ma.png')
    xy=await pg.evaluate(VISTXT,'Worcester County') or await pg.evaluate(VISTXT,'Worcester'); print('Worc',xy)
    if not xy:
      await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
      print(await pg.evaluate("()=>[...document.querySelectorAll('li,.lvrow')].filter(e=>e.offsetParent).slice(0,20).map(e=>e.className+': '+e.innerText.replace(/\\n/g,' ').slice(0,40))"))
      xy=await pg.evaluate(VISTXT,'Worcester County') or await pg.evaluate(VISTXT,'Worcester'); print('Worc2',xy)
    await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
    print(await pg.evaluate("()=>({crumbs:document.getElementById('crumbs').innerText,list:document.body.classList.contains('listmode'),la:window.__laInfo()})"))
    await pg.screenshot(path='../shots/b1574-probe2-worc.png')
    await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(1200)
    print(await pg.evaluate("()=>[...document.querySelectorAll('#lyrRow button')].map(b=>b.dataset.k+':'+(b.getAttribute('aria-label')||b.innerText))"))
    await pg.screenshot(path='../shots/b1574-probe2-lyr.png')
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
    print(await pg.evaluate("()=>[...document.querySelectorAll('li,.lvrow')].filter(e=>e.offsetParent).slice(0,12).map(e=>e.className+': '+e.innerText.replace(/\\n/g,' ').slice(0,40))"))
    print(await pg.evaluate("()=>[...document.querySelectorAll('[aria-label]')].filter(e=>e.offsetParent&&/back/i.test(e.getAttribute('aria-label'))).map(e=>e.tagName+'.'+e.className+' '+e.getAttribute('aria-label'))"))
    await pg.screenshot(path='../shots/b1574-probe2-geo.png')
    await c.close(); await b.close()
asyncio.run(main())
