# QA-114 spot check: FL-20 row in the nationwide US House list, '16
import asyncio,sys
from playwright.async_api import async_playwright
ENG=sys.argv[1]
async def main():
  async with async_playwright() as p:
    b=await getattr(p,ENG).launch(); c=await b.new_context(viewport={"width":390,"height":844},has_touch=True,is_mobile=(ENG=="chromium")); pg=await c.new_page()
    await pg.goto("https://ge0r9b.github.io/us-districts/v2/",wait_until="load"); await pg.wait_for_timeout(6000)
    await pg.evaluate("()=>document.querySelector('#lyrRow .lbtn[data-k=ushouse]').click()"); await pg.wait_for_timeout(3000)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(3000)
    await pg.evaluate("()=>{const r=document.querySelector('li.la-row');(r.querySelector('.nmx')||r).click()}"); await pg.wait_for_timeout(9000)
    await pg.evaluate("()=>{window.__ySetYr(0);return 0}"); await pg.wait_for_timeout(9000)
    r=await pg.evaluate("()=>{const R=[...document.querySelectorAll('#listView .lvrow.la')];const f=R.find(r=>/^FL-20/.test((r.querySelector('.nmx')||r).textContent.trim()));if(f)f.scrollIntoView({block:'center'});return {build:window.BUILD,n:R.length,fl20:f&&f.textContent,nd:R.filter(r=>/no data/.test(r.textContent)).map(r=>(r.querySelector('.nmx')||r).textContent.trim())}}")
    await pg.wait_for_timeout(2500); fn=f"qa/shots40/fl20-{ENG}-390-16.png"; await pg.screenshot(path=fn); print(r,fn); await b.close()
asyncio.run(main())
