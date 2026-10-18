import asyncio,json
from playwright.async_api import async_playwright
from common import *
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await ctx(b,1024,768,False)
    await pg.goto(URL,wait_until="load"); await pg.wait_for_timeout(6000)
    await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(1000)
    print(json.dumps(await pg.evaluate("""()=>[...document.querySelectorAll('body *')].filter(e=>e.id&&e.offsetParent!==null&&e.getBoundingClientRect().width>0).map(e=>{const r=e.getBoundingClientRect();return e.tagName+'#'+e.id+' '+(e.className&&e.className.baseVal===undefined?e.className:'')+' ['+[r.left,r.top,r.width,r.height].map(Math.round)+'] '+(e.innerText||'').slice(0,20).replace(/\\n/g,' ')}).filter(s=>!/leaflet|path/.test(s)).slice(0,80)""")),)
    print(await pg.evaluate("()=>{const c=document.querySelector('.cand');return c?c.parentElement.id+' '+c.parentElement.className+' '+c.outerHTML.slice(0,200):null}"))
    await c.close(); await b.close()
asyncio.run(main())
