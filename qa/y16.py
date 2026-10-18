import asyncio,json
from playwright.async_api import async_playwright
from common import *
from gaps import fresh
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c,pg,log=await fresh(b)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(5000)
    xy=await center(pg,'#bTime'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(1200)
    t=await pg.evaluate("()=>{const e=document.querySelector('.ylb.l')||document.getElementById('yslider');const r=e.getBoundingClientRect();const tr=document.querySelector('.trk').getBoundingClientRect();return {lab:e.textContent,trk:[tr.left,tr.top+tr.height/2,tr.width]}}")
    x,y,w=t['trk']; lat=await tap_latency(pg,x+2,y); await pg.wait_for_timeout(2500)
    o={'lab':t['lab'],'lat':lat,'ym':await pg.evaluate("()=>window.__ymode()"),'yv':await pg.evaluate("()=>document.getElementById('yslider').value"),
       'rows':await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].filter(r=>r.offsetParent).slice(0,4).map(r=>r.innerText.replace(/\\n/g,' | '))"),
       'cands':await pg.evaluate("()=>[...document.querySelectorAll('.cand')].map(b=>b.getAttribute('aria-label')+' '+b.innerText.trim())"),'text':await pg.evaluate("()=>document.getElementById('listView').innerText.slice(0,200)")}
    await pg.screenshot(path="../shots/b1569-ch-390-2016-tap.png")
    await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(2000); await pg.touchscreen.tap(200,500); await pg.wait_for_timeout(1200)
    o['pop']=await pg.evaluate("()=>[...document.querySelectorAll('.leaflet-popup-content')].map(e=>e.innerText.replace(/\\n/g,' | ').slice(0,150))")
    await pg.screenshot(path="../shots/b1569-ch-390-2016-map.png"); o['err']=log['pageerr']+log['console']
    print(json.dumps(o,indent=0)); await c.close(); await b.close()
asyncio.run(main())
