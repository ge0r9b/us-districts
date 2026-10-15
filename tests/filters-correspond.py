# usage: python3 tests/filters-correspond.py http://localhost:8765/v2/
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
async def main():
  global fails
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H in((1280,800),(430,900)):
      pg=await b.new_page(viewport={"width":W,"height":H}); er=[]; pg.on("pageerror",lambda e:er.append(str(e)))
      await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
      async def geo(q):
        await pg.evaluate("()=>{window.__worldExit&&window.__worldExit()}")
        await pg.locator('#gq').click(); await pg.wait_for_timeout(600); await pg.locator('#gq').fill(''); await pg.locator('#gq').type(q,delay=40); await pg.wait_for_timeout(1200)
        return await pg.evaluate("()=>[...document.querySelectorAll('#geofs li')].slice(0,5).map(l=>(l.querySelector('.nm')||l).textContent.trim())")
      for q,exp in [('canada','Canada'),('PA','Pennsylvania'),('uk','United Kingdom'),('alberta','Alberta, Canada')]:
        r=await geo(q); ok=bool(r) and exp.lower() in r[0].lower() or any(exp.lower()==x.lower() for x in r[:3]); fails+=0 if ok else 1; print(W,'geo',q,'OK' if ok else 'FAIL',r)
        await pg.evaluate("()=>window.__geoClose&&window.__geoClose()"); await pg.wait_for_timeout(300)
      # geo: Enter on a province selects it and zooms
      await pg.evaluate("()=>{window.__worldExit&&window.__worldExit()}"); await pg.locator('#gq').click(); await pg.wait_for_timeout(600); await pg.locator('#gq').type('alberta, canada',delay=30); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(3500)
      r=await pg.evaluate("()=>[window.__W&&window.__W(), document.body.className.includes('worldmode'), Math.round(map.getZoom())]") if False else await pg.evaluate("()=>[window.__W&&window.__W(), document.body.classList.contains('worldmode')]")
      ok=r[0]=='ca'; fails+=0 if ok else 1; print(W,'geo enter alberta ->',r,'OK' if ok else 'FAIL'); await pg.screenshot(path=f"/workspace/shots/corr-alberta-{W}.png")
      # institution aliases
      await pg.evaluate("()=>{window.__worldExit&&window.__worldExit(); state.value=''; state.onchange&&state.onchange();}"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>{ if(!document.body.classList.contains('foldfs')) document.getElementById('bGeo').click(); }"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.querySelector('#crumbs .crumb.glob').click()"); await pg.wait_for_timeout(2500)
      inp=pg.locator('#barGeo .fsq input').first
      for q,exp in [('PA','Pennsylvania'),('uk','United Kingdom'),('usa','United States'),('alberta','Alberta')]:
        await inp.fill(''); await pg.wait_for_timeout(300); await inp.type(q,delay=40); await pg.wait_for_timeout(900)
        r=await pg.evaluate("()=>window.__orgSearchRows()"); ok=bool(r) and r[0].startswith(exp); fails+=0 if ok else 1; print(W,'inst',q,'OK' if ok else 'FAIL',r[:3])
      await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
