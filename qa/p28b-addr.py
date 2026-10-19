# pass 27: White House address from the map, the All States list and the PA > Philadelphia townships list (follow-up on the flow's addr-result shot)
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
NMXY="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
ST="""()=>({crumbs:(document.getElementById('crumbs')||{}).innerText,gq:document.getElementById('gq').value,ph:document.getElementById('gq').placeholder,
 thumbs:[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' '+e.innerText.replace(/\\n/g,' ')).slice(0,4),
 rows:[...document.querySelectorAll('#listView .lvrow')].filter(r=>r.offsetParent).slice(0,4).map(r=>r.innerText.replace(/\\n/g,' | ')),
 snap:window.__stateSnapshot?JSON.stringify(window.__stateSnapshot()).slice(0,260):null,
 pop:[...document.querySelectorAll('.leaflet-popup-content')].map(e=>e.innerText.slice(0,120))})"""
ADDR="1600 Pennsylvania Ave NW, Washington, DC 20500"
async def main():
  eng=sys.argv[1]; W,H=390,844; R={'eng':eng}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for sc in ['map','allstates','phila']:
      c,pg,log=await ctx(b,W,H,True,eng)
      try:
        await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); R['build']=await pg.evaluate("window.BUILD")
        if sc!='map':
          await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
          await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
        if sc=='phila':
          await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'PA'))); await pg.wait_for_timeout(3500)
          await pg.touchscreen.tap(*(await pg.evaluate(NMXY,'Philadelphia'))); await pg.wait_for_timeout(3500)
        before=await pg.evaluate(ST)
        await pg.touchscreen.tap(*(await center(pg,"#gq"))); await pg.wait_for_timeout(600); await pg.evaluate("()=>document.getElementById('gq').focus()"); await pg.wait_for_timeout(300)
        await pg.keyboard.type(ADDR,delay=20); await pg.wait_for_timeout(2500)
        await pg.keyboard.press("Enter"); await pg.wait_for_timeout(7000)
        after=await pg.evaluate(ST); await pg.screenshot(path=f"../shots/b{R['build'][-4:]}p28-{eng[:2]}-390-addr-{sc}.png")
        R[sc]={'before':before,'after':after,'err':log['pageerr']+[x for x in log['console'] if x.startswith('error')]}
        print(sc,json.dumps(R[sc]),flush=True)
      except Exception as e: R[sc]={'EXC':str(e)[:300]}; print('EXC',sc,e,flush=True)
      await c.close()
    await b.close()
  json.dump(R,open(f"b{R.get('build','0000')[-4:]}p28-addr-{eng}-390.json",'w'),indent=1)
asyncio.run(main())
