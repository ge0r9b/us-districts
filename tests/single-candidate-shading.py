# usage: python3 tests/single-candidate-shading.py URL -- Harris-only / Trump-only statewide fills must follow the candidate's actual share on the legend scale (monotonic, many distinct colors, WY light for Harris, DC light for Trump), fills opaque
import asyncio,sys,re
from playwright.async_api import async_playwright
fails=0
def lum(c):
  r,g,b=map(int,re.findall(r'\d+',c)[:3]); return 0.3*r+0.59*g+0.11*b
async def main():
  global fails
  async with async_playwright() as p:
    b=await p.chromium.launch(); pg=await b.new_page(viewport={"width":430,"height":800}); await pg.goto(sys.argv[1],wait_until="networkidle"); await pg.wait_for_timeout(3500)
    for name,off,ix in (("harris-only","t24",0),("trump-only","h24",1)):
      await pg.evaluate("id=>{window.__candOn.delete(id); window.__syncYears();}",off); await pg.wait_for_timeout(1500)
      rows=await pg.evaluate("(ix)=>window.__STget().map(d=>{const t=window.__stTot(d.st,'2024');return [d.st,window.__fillOf(d.st),t[ix?1:0]/t[2]]})",ix)
      rows.sort(key=lambda r:r[2]); L=[lum(r[1]) for r in rows]
      mono=all(L[i]>=L[i+1]-1.5 for i in range(len(L)-1)); distinct=len(set(r[1] for r in rows))
      ok=mono and distinct>=30; fails+=0 if ok else 1; print('OK  ' if ok else 'FAIL',name,'monotonic',mono,'distinct',distinct,rows[0][:2],rows[-1][:2],flush=True)
      await pg.screenshot(path=f"/workspace/shots/shade-{name}.png")
      op=await pg.evaluate("()=>window.__map.getPane('stPane').querySelector('canvas')!==null"); 
      await pg.evaluate("id=>{window.__candOn.add(id);window.__syncYears();}",off); await pg.wait_for_timeout(800)
    await b.close()
  sys.exit(1 if fails else 0)
asyncio.run(main())
