import asyncio,sys,json,time,statistics as st
from playwright.async_api import async_playwright
M="async js=>{const t0=performance.now();(0,eval)(js);await new Promise(r=>requestAnimationFrame(()=>setTimeout(r,0)));return performance.now()-t0}"
PA="[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()==='PA'}).click()"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for rep in range(int(sys.argv[2]) if len(sys.argv)>2 else 1):
     for v in sys.argv[1].split(','):
      c=await b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,is_mobile=True,has_touch=True); pg=await c.new_page()
      await pg.goto(f"http://127.0.0.1:8857/{v}/v2/?v=%d"%(time.time()*1000),wait_until="networkidle"); await pg.wait_for_timeout(2500)
      await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1200)
      await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(3000)
      bk=[];dr=[]
      for i in range(6):
        dr.append(round(await pg.evaluate(M,PA),1)); await pg.wait_for_timeout(3500)
        bk.append(round(await pg.evaluate(M,"document.getElementById('bBack').click()"),1)); await pg.wait_for_timeout(3000)
      print(v,'back',bk,'med',st.median(bk[1:]),'drill med',st.median(dr[1:]),flush=True); await c.close()
    await b.close()
asyncio.run(main())
