# QA-114: sweep nationwide district lists for 'no data' rows across years/ranges (DOM textContent)
import asyncio,sys,json
from playwright.async_api import async_playwright
URL="https://ge0r9b.github.io/us-districts/v2/"; ENG=sys.argv[1] if len(sys.argv)>1 else "chromium"
TYPES=(sys.argv[2] if len(sys.argv)>2 else "ushouse,senate,statehouse,schools").split(",")
MODES=[("16","__ySetYr(0)"),("20","__ySetYr(1)"),("24","__ySetYr(2)"),("16-24","__ySet16(2)"),("20-24","__ySelectAll()")]
ROWS="()=>{const R=[...document.querySelectorAll('#listView .lvrow.la')];return {n:R.length,crumb:(document.getElementById('crumbs')||{}).innerText,nd:R.filter(r=>/no data/.test(r.textContent)).map(r=>(r.querySelector('.nmx')||r).textContent.trim().slice(0,50)),ym:window.__ymode&&window.__ymode()}}"
async def main():
  out={}
  async with async_playwright() as p:
    b=await getattr(p,ENG).launch()
    for k in TYPES:
      c=await b.new_context(viewport={"width":390,"height":844},has_touch=True,is_mobile=(ENG=="chromium")); pg=await c.new_page()
      await pg.goto(URL,wait_until="load"); await pg.wait_for_timeout(6000)
      await pg.evaluate(f"()=>document.querySelector('#lyrRow .lbtn[data-k={k}]').click()"); await pg.wait_for_timeout(4000)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(4000)
      await pg.evaluate("()=>{const r=document.querySelector('li.la-row');(r.querySelector('.nmx')||r).click()}"); await pg.wait_for_timeout(10000)
      for nm,js in MODES:
        await pg.evaluate(f"()=>{{window.{js};return 0}}"); prev=None
        for i in range(12):
          await pg.wait_for_timeout(3000); r=await pg.evaluate(ROWS)
          if prev and r['n']==prev['n'] and r['nd']==prev['nd'] and i>=2: break
          prev=r
        out[f"{k}|{nm}"]=r; print(k,nm,"rows",r['n'],"ym",r['ym'],"crumb",r['crumb'][:40].replace('\n',' '),"nodata",len(r['nd']),r['nd'][:40],flush=True)
      await c.close()
    await b.close()
  json.dump(out,open(f"qa/p40-nodata-{ENG}-{'_'.join(TYPES)}.json","w"),indent=1)
asyncio.run(main())
