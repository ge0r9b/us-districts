# usage: python3 tests/menu-header.py URL tag -- institution menu open (also after list-all, with a district type): header rows stay at the approved fixed positions, nothing floats above the sheet (cands, sort arrows, bubbles), no scroll offset; desktop sizes incl. short heights + phone
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
async def main():
  global fails
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H in((1024,575),(1280,520),(1920,1010),(430,800)):
      pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.click("#bGeo"); await pg.wait_for_timeout(1000); await pg.click("li.la-row"); await pg.wait_for_timeout(3000)
      await pg.click("#bGeo"); await pg.wait_for_timeout(1500)
      S="()=>({sy:scrollY+document.documentElement.scrollTop+document.body.scrollTop,bs:Math.round(document.getElementById('barSearch').getBoundingClientRect().top),bg:Math.round(document.getElementById('barGeo').getBoundingClientRect().top),sort:getComputedStyle(document.getElementById('laSort')).display,cands:getComputedStyle(document.getElementById('cands')).display,sheet:Math.round(document.getElementById('sheet').getBoundingClientRect().top)})"
      r=await pg.evaluate(S); ok=r['sy']==0 and r['bs']==8 and r['bg']==64 and r['sort']=='none' and r['cands']=='none' and r['sheet']>=110
      fails+=0 if ok else 1; print(W,H,'list-all menu','OK' if ok else 'FAIL',json.dumps(r),flush=True)
      await pg.evaluate("()=>{const r=[...document.querySelectorAll('#sheet li')].find(x=>/School districts/.test(x.textContent)&&x.offsetParent); r&&r.click();}"); await pg.wait_for_timeout(3000)
      await pg.click("#bGeo"); await pg.wait_for_timeout(1500); r=await pg.evaluate(S)
      ok=r['sy']==0 and r['bs']==8 and r['bg']==64 and r['sort']=='none' and r['cands']=='none' and r['sheet']>=110
      fails+=0 if ok else 1; print(W,H,'schools menu','OK' if ok else 'FAIL',json.dumps(r),flush=True)
      await pg.screenshot(path=f"/workspace/shots/mh-{tag}-{W}x{H}.png"); await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
