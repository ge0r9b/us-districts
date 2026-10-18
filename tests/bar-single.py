# usage: python3 tests/bar-single.py URL tag -- SUPERSEDED in build 1557 (a single entity shows no bar chart): now checks that the single entity (US) offers no bar and shows no bar block. Old spec: single-year bar chart is ONE block: [thumbnail on the icon axis] + [bar with its value inside], no text labels/names/table, Other as a gray row, bubbles for names/exact values; # and % modes, phone + desktop
import asyncio,sys,json,re
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
async def main():
  global fails
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((1280,800,'dk'),(430,800,'ph')):
      pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(700)
      await pg.evaluate("()=>{const x=[...document.querySelectorAll('button')].find(b=>b.dataset.ch==='bar'); x&&x.click();}"); await pg.wait_for_timeout(2000)
      for mode in ('pct','num'):
        await pg.evaluate("m=>window.__setNum(m)",mode); await pg.wait_for_timeout(1500)
        r=await pg.evaluate("()=>({mode:window.chartMode, dmx:!!document.querySelector('#cands .dmx .dmr'), la:window.__laInfo().on})")
        ok=r['mode']!='bar' and not r['dmx'] and not r['la']; fails+=0 if ok else 1; print(t,mode,'OK' if ok else 'FAIL','single entity: no bar chart',json.dumps(r),flush=True)
      await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
