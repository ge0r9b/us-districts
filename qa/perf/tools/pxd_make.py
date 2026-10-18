# emulate the build step for one state: load A2, drill into PA, run pxd_dump.js, write raw/pxd-Pennsylvania.js
import asyncio,time,os
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__))
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); c=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); pg=await c.new_page()
    await pg.goto("http://127.0.0.1:8857/A2/v2/?v=%d"%time.time(),wait_until="networkidle"); await pg.wait_for_timeout(2500)
    await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
    await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(3000)
    await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()==='PA'}).click()")
    for _ in range(100):
      if await pg.evaluate("()=>!!PREC['Pennsylvania']&&(GEOM.ushouse||[]).some(d=>d[0]==='Pennsylvania')"): break
      await pg.wait_for_timeout(200)
    await pg.wait_for_timeout(1500)
    s=await pg.evaluate(open(D+'/pxd_dump.js').read()); open(D+'/../raw/pxd-Pennsylvania.js','w').write(s); print(len(s))
    await b.close()
asyncio.run(main())
