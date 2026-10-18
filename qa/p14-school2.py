# pass 14: Georgia school-district layer button; same-name school district rows (values)
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
ROWS="()=>{const a=window.__laInfo&&window.__laInfo();return a&&a.order?a.order.map(x=>[x[0],x[1]]):[]}"
async def main():
  out={}
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for stn in ['Georgia','California','Ohio']:
      c,pg,log=await ctx(b,390,844,True,'chromium'); await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
      await pg.evaluate("n=>{const s=document.getElementById('state');s.value=n;s.dispatchEvent(new Event('change',{bubbles:true}))}",stn); await pg.wait_for_timeout(4500)
      await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(1200)
      R=out[stn]={'keys':await pg.evaluate("()=>[...document.querySelectorAll('#lyrRow .lbtn')].filter(b=>b.offsetParent).map(b=>b.dataset.k)"),'crumb':await pg.evaluate("()=>document.getElementById('crumbs').innerText")}
      xy=await center(pg,'#lyrRow .lbtn[data-k=schools]')
      if xy:
        await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
        await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(7000)
        rows=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].map(r=>((r.querySelector('.nmx')||r).getAttribute('title')||'')+' || '+(r.querySelector('.nmx')||r).textContent.trim()+' || '+r.innerText.replace(/\\n/g,' | '))")
        R['n']=len(rows); names=[r.split(' || ')[1] for r in rows]
        R['dups']=[r for r in rows if names.count(r.split(' || ')[1])>1][:12]
        R['order_dups']=[]; od=await pg.evaluate(ROWS); nm=[x[0] for x in od]; R['order_dups']=[x for x in od if nm.count(x[0])>1][:12]
        await safeshot(pg,f"../shots/b1582p14-ch-390-schools-{stn}.png")
      print(stn,json.dumps(R)[:1500],flush=True); await c.close()
    await b.close()
  json.dump(out,open('b1582p14-school2-chromium-390.json','w'),indent=1)
asyncio.run(main())
