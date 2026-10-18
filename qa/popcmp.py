import asyncio,json
from playwright.async_api import async_playwright
from common import *
from gaps import fresh,typegq
CS=[('Maricopa County, AZ','Arizona','Maricopa County','AZ'),('Harris County, TX','Texas','Harris County','TX'),('Hennepin County, MN','Minnesota','Hennepin County','MN'),('Fulton County, GA','Georgia','Fulton County','GA')]
async def main():
  out={}
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for q,st,co,ab in CS:
      c,pg,log=await fresh(b); await pg.evaluate("()=>{window.__setNum('num')}"); await pg.wait_for_timeout(800)
      await typegq(pg,q); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(6000)
      # tap the county centroid
      xy=await pg.evaluate("n=>{const c=map.getCenter();const p=map.latLngToContainerPoint(c);return [p.x,p.y]}",co)
      await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(1500)
      pop=await pg.evaluate("()=>[...document.querySelectorAll('.leaflet-popup-content')].map(e=>e.innerText.replace(/\\n/g,' | '))")
      data=await pg.evaluate("k=>ELECTION2024[k]",st+'|'+co)
      # list: state counties list, # mode
      await pg.screenshot(path=f"../shots/b1569-ch-390-pop-{ab}-map.png")
      await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(3000)
      lst=await pg.evaluate("()=>document.getElementById('listView').innerText.replace(/\\n/g,' | ').slice(0,300)")
      await pg.screenshot(path=f"../shots/b1569-ch-390-pop-{ab}.png")
      cands=await pg.evaluate("()=>[...document.querySelectorAll('.cand')].map(b=>b.getAttribute('aria-label')+' '+b.innerText.trim())")
      out[q]={'popup':pop,'list':lst,'data':data,'thumbs':cands,'ph':await pg.evaluate("()=>document.getElementById('gq').placeholder")}
      await c.close()
    await b.close()
  for k,v in out.items(): print(k,json.dumps(v)[:600])
asyncio.run(main())
