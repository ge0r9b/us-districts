# usage: python3 tests/legend-size.py URL tag -- bottom-left legend (labels 4px, bar 37x3) and credit (6px, NYT kept) are ~35% smaller than before, same bottom-left anchor; phone + desktop
import asyncio,sys
from playwright.async_api import async_playwright
base=sys.argv[1]; fails=0
async def main():
  global fails
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((1280,800,'dk'),(430,800,'ph')):
      pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3500)
      r=await pg.evaluate("()=>{const g=s=>document.querySelector(s); const bar=g('.heatlegend .heatbar').getBoundingClientRect(), l=getComputedStyle(g('.heatlegend .heatlbl span')).fontSize, e=g('.esria'), er=e.getBoundingClientRect(); return {barW:Math.round(bar.width),barH:Math.round(bar.height),lbl:l,es:getComputedStyle(e).fontSize,txt:e.textContent,bottom:Math.round(innerHeight-er.bottom),left:Math.round(er.left)}}")
      ok=r['barW']<=40 and r['lbl']=='4px' and r['es']=='6px' and 'NYT' in r['txt'] and r['left']<=8 and r['bottom']<=60
      fails+=0 if ok else 1; print(t,'OK' if ok else 'FAIL',r,flush=True); await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
