import asyncio,json,sys
from playwright.async_api import async_playwright
from common import *
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,390,844,True,'chromium')
    await pg.goto(URL,wait_until="load"); await pg.wait_for_function("()=>window.__ymode&&window.__ysl",timeout=60000); await pg.wait_for_timeout(5000)
    o={}
    o['build']=await pg.evaluate("window.BUILD")
    o['globals']=await pg.evaluate("()=>Object.keys(window).filter(k=>k.startsWith('__')).join(' ')")
    o['lyr']=await pg.evaluate("()=>[...document.querySelectorAll('#lyrRow button')].map(b=>b.dataset.k+':'+b.innerText.trim())")
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1500)
    o['geo']=await pg.evaluate("()=>[...document.querySelectorAll('li')].filter(e=>e.offsetParent).slice(0,30).map(e=>e.className+'|'+e.innerText.replace(/\\n/g,' ').slice(0,50))")
    await safeshot(pg,'shots36/b1615p36-ch-390-probe-geo.png')
    o['buttons']=await pg.evaluate("()=>[...document.querySelectorAll('button')].filter(e=>e.offsetParent).map(e=>(e.id||e.className)+':'+(e.getAttribute('aria-label')||e.innerText.trim()).slice(0,30))")
    o['sortsrc']=await pg.evaluate("()=>{const s=document.getElementById('laSort');return s?s.outerHTML.slice(0,300):null}")
    o['chart']=await pg.evaluate("()=>[...document.querySelectorAll('#chartBox .copts button')].map(b=>b.dataset.ch)")
    json.dump(o,open('b1615p36-probe.json','w'),indent=1); print(json.dumps(o,indent=1))
    await b.close()
asyncio.run(main())
