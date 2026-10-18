import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
async def main():
  async with async_playwright() as p:
    for eng in ('chromium','webkit'):
      b=await getattr(p,eng).launch()
      for tag,W,H,mob in (VPS[0],VPS[4]):
        for mode in ('bar','line'):
          for where in ('name','graphic'):
            c,pg,log=await ctx(b,W,H,mob,eng)
            await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
            await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
            await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4500)
            if mode=='line':
              await pg.evaluate("()=>{ if(document.getElementById('barTime').hidden) document.getElementById('bTime').click() }"); await pg.wait_for_timeout(800)
              await pg.evaluate("()=>window.__ySelectAll&&window.__ySelectAll()"); await pg.wait_for_timeout(2000)
              await pg.evaluate("()=>{document.querySelector('#chartBox .cmain').click()}"); await pg.wait_for_timeout(700)
              await pg.evaluate("()=>{const b=document.querySelector('#chartBox .copts button[data-ch=line]'); b&&b.click()}"); await pg.wait_for_timeout(2500)
            xy=await pg.evaluate("w=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const x=r.querySelector('.nmx');return x&&x.textContent.trim()==='OH'});r.scrollIntoView({block:'center'});const n=r.querySelector('.nmx').getBoundingClientRect(),q=r.getBoundingClientRect();return w=='name'?[n.left+n.width/2,q.top+q.height/2]:[q.left+q.width*0.55,q.top+q.height/2]}",where)
            await pg.wait_for_timeout(500); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(3500)
            i=await pg.evaluate("()=>window.__laInfo().lv+' '+state.value")
            print(eng,tag,mode,where,[round(v) for v in xy],'->',i,flush=True)
            if where=='graphic': await pg.screenshot(path=f"../shots/b1567-{eng[:2]}-{W}-{mode}-rowtap.png")
            await c.close()
      await b.close()
asyncio.run(main())
