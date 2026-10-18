# usage: python3 tests/bar-single.py URL tag -- build 1563: a single entity (US) offers bar again: ONE bar per answer in the chart panel (.sebar), sorted high -> low (% / #), labeled with its total; no merged .dmx block for one year, no list. (Build 1557-1562: no bar for a single entity.)
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
        r=await pg.evaluate("()=>({mode:window.chartMode, dmx:!!document.querySelector('#cands .dmx .dmr'), la:window.__laInfo().on, v:[...document.querySelectorAll('.cpanel .sebar .sebr')].map(e=>+e.dataset.v), lab:[...document.querySelectorAll('.cpanel .sebar .sebt b')].map(b=>b.textContent)})")
        ok=r['mode']=='bar' and not r['dmx'] and not r['la'] and len(r['v'])==3 and r['v']==sorted(r['v'],reverse=True) and all(r['lab']); fails+=0 if ok else 1; print(t,mode,'OK' if ok else 'FAIL','single entity: one bar per answer, sorted high -> low, each labeled',json.dumps(r),flush=True)
      await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
