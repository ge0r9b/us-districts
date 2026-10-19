# pass 35: Brooklyn addresses (map path) and Dauphin County / Harrisburg precinct names
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
TH="()=>[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' / '+e.innerText.replace(/\\n/g,' ')).slice(0,2)"
CR="()=>(document.getElementById('crumbs')||{}).innerText"
ROWS="()=>[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).map(r=>r.innerText.replace(/\\n/g,' | '))"
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
async def main():
  out={}
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for a in ['350 Jay St, Brooklyn, NY 11201','95 Prospect Park West, Brooklyn, NY 11215','1000 Richmond Terrace, Staten Island, NY 10301','100 State St, Erie, PA 16507']:
      c,pg,log=await ctx(b,390,844,True,'chromium')
      await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await pg.touchscreen.tap(*(await center(pg,'#gq'))); await pg.wait_for_timeout(500); await pg.evaluate("()=>document.getElementById('gq').focus()")
      await pg.keyboard.type(a,delay=15); await pg.wait_for_timeout(2500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(7000)
      out[a]=[await pg.evaluate(CR),await pg.evaluate(TH),await pg.evaluate("()=>[...document.querySelectorAll('.leaflet-popup-content')].map(e=>e.innerText.replace(/\\n/g,' | '))")]
      print(a,out[a],flush=True); await c.close()
    c,pg,log=await ctx(b,390,844,True,'chromium')
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    await typegq(pg,'Pennsylvania'); await pg.wait_for_timeout(500); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
    xy=await pg.evaluate(NMXY,'Dauphin'); await pg.wait_for_timeout(300); xy=await pg.evaluate(NMXY,'Dauphin'); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
    out['dauphin']=[await pg.evaluate(CR),(await pg.evaluate(ROWS))[:8]]
    xy=await pg.evaluate(NMXY,'Harrisburg'); await pg.wait_for_timeout(300); xy=await pg.evaluate(NMXY,'Harrisburg')
    if xy: await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000); out['hbg']=[await pg.evaluate(CR),(await pg.evaluate(ROWS))[:10]]; await safeshot(pg,'shots35/b1614p35-ch-390x844-harrisburg-precincts.png')
    print(json.dumps({k:out[k] for k in ('dauphin','hbg') if k in out}),flush=True)
    out['err']=log['pageerr']; await b.close()
  json.dump(out,open('b1614p35-probe-chromium-390x844.json','w'),indent=1)
asyncio.run(main())
