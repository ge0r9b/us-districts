# usage: python3 tests/two-point-cols.py URL -- in the two-point view the 2020 column sits under the 2020 label (left icon axis) and the 2024 column is right-aligned under the 2024 label, phone + desktop
import asyncio,sys
from playwright.async_api import async_playwright
fails=0
async def main():
  global fails
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H in((430,800),(1280,800)):
      pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(sys.argv[1],wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.click("#bTime"); await pg.wait_for_timeout(500); await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(2500)
      r=await pg.evaluate("""()=>{const tr=e=>{const r=document.createRange();r.selectNodeContents(e);return r.getBoundingClientRect()};const sp=[...document.querySelectorAll('#ysl .tk span')];const cols=[...document.querySelectorAll('#cands > .ccol')].map(c=>c.getBoundingClientRect());const dots=[...document.querySelectorAll('#ysl .tk i')].map(d=>{const b=d.getBoundingClientRect();return b.left+b.width/2});const imgs=[...document.querySelectorAll('#cands > .ccol')].map(c=>{const b=c.querySelector('img').getBoundingClientRect();return b.left+b.width/2});const cyr=[...document.querySelectorAll('#cands .cyr')].filter(e=>getComputedStyle(e).display!=='none').length;const cpt=document.querySelectorAll('#cands > .ccol')[1].querySelector('.cpt').getBoundingClientRect(), im=document.querySelectorAll('#cands > .ccol')[1].querySelector('img').getBoundingClientRect();return {d0:dots[0],d1:dots[dots.length-1],i0:imgs[0],i1:imgs[1],cyr:cyr,inward:cpt.right<=im.left+im.width/2+1}}""")
      ok=abs(r['i1']-r['d1'])<=1.5 and abs(r['i0']-r['d0'])<=2 and r['cyr']==0 and r['inward']; fails+=0 if ok else 1; print(W,'OK' if ok else 'FAIL',r)
      await pg.close()
    await b.close()
  sys.exit(1 if fails else 0)
asyncio.run(main())
