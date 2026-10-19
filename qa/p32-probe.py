import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True,'chromium')
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    await pg.evaluate("n=>{const s=document.getElementById('state');s.value=n;s.dispatchEvent(new Event('change',{bubbles:true}))}",'Texas'); await pg.wait_for_timeout(5000)
    print('TX thumbs',await pg.evaluate("()=>[...document.querySelectorAll('.cand')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' '))"))
    print('title',await pg.evaluate("()=>[document.getElementById('vtitle').innerText,document.getElementById('crumbs').innerText]"))
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
    print('geo menu',await pg.evaluate("()=>[...document.querySelectorAll('li')].filter(e=>e.offsetParent).map(e=>e.className+' :: '+e.innerText.replace(/\\n/g,' ').slice(0,60))"))
    await pg.screenshot(path='../shots/b1609p32-ch-390-probe-geo-TX.png')
    await pg.keyboard.press('Escape'); await pg.wait_for_timeout(600)
    await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(1200)
    print('lyr',await pg.evaluate("()=>[...document.querySelectorAll('#lyrRow .lbtn')].map(e=>e.dataset.k+' '+e.innerText.replace(/\\n/g,' ')+' vis'+(e.offsetParent?1:0))"))
    print('globals',await pg.evaluate("()=>Object.keys(window).filter(k=>k.startsWith('__'))"))
    print('snap',await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"))
    print(log)
    await b.close()
asyncio.run(main())
