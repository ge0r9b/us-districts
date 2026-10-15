# usage: python3 tests/default-solid.py URL tag -- the default (initial) view and a slightly zoomed-in view show SOLID statewide fills (natPane hidden, state fill present), phone + desktop; US House keeps district detail
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
def chk(n,ok,info=''):
  global fails
  fails+=0 if ok else 1; print('OK  ' if ok else 'FAIL',n,info,flush=True)
S="()=>({solid:window.__stSolid(),span:Math.round(window.__vspan()*10)/10,z:window.__map.getZoom(),nat:getComputedStyle(window.__map.getPane('natPane')).visibility,type:getComputedStyle(window.__map.getPane('typePane')).visibility})"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((430,800,'ph'),(1280,800,'dk')):
      pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="commit")
      early=[]
      for i in range(10):
        await pg.wait_for_timeout(600)
        try: early.append(await pg.evaluate("()=>window.__map?[window.__stSolid(),getComputedStyle(window.__map.getPane('natPane')).visibility]:null"))
        except Exception: early.append('x')
      await pg.wait_for_timeout(3500); r=await pg.evaluate(S)
      chk(f'{t} default view solid statewide',r['solid'] and r['nat']=='hidden',json.dumps(r)+' early='+json.dumps(early)); await pg.screenshot(path=f"/workspace/shots/ds-{tag}-{t}-default.png")
      await pg.evaluate("()=>{ const c=window.__map.getCenter(); window.__map.setZoom(window.__map.getZoom()+1,{animate:false}); }"); await pg.wait_for_timeout(2500); r=await pg.evaluate(S)
      if t=='dk': chk(f'{t} slightly zoomed-in view (still most of the US) solid',r['solid'] and r['nat']=='hidden',json.dumps(r))
      else: chk(f'{t} one zoom step in = Texas-sized view (zoom steps are whole levels on the phone)',(not r['solid']) and r['span']<=15.5,json.dumps(r))
      await pg.screenshot(path=f"/workspace/shots/ds-{tag}-{t}-zoom1.png")
      await pg.evaluate("()=>{ window.__map.setView([31,-99.3],innerWidth<700?5:6,{animate:false}); }"); await pg.wait_for_timeout(2500); r=await pg.evaluate(S)
      chk(f'{t} Texas-sized view shows counties',(not r['solid']) and r['nat']!='hidden',json.dumps(r)); await pg.screenshot(path=f"/workspace/shots/ds-{tag}-{t}-texas.png")
      await pg.close()
      pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
      await pg.evaluate("()=>{const b=document.querySelector('#lyrRow .lbtn[data-k=ushouse]'); b&&b.click();}"); await pg.wait_for_timeout(3500); r=await pg.evaluate(S)
      chk(f'{t} US House keeps district detail at the zoomed-out default',(not r['solid']) and r['type']!='hidden',json.dumps(r)); await pg.screenshot(path=f"/workspace/shots/ds-{tag}-{t}-ushouse.png"); await pg.close()
      for k in ('senate','statehouse','schools'):
        pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
        await pg.evaluate("k=>{const b=document.querySelector('#lyrRow .lbtn[data-k='+k+']'); b&&b.click();}",k); await pg.wait_for_timeout(4000); r=await pg.evaluate(S)
        chk(f'{t} {k} keeps district detail at the zoomed-out default',(not r['solid']) and r['type']!='hidden',json.dumps(r)); await pg.screenshot(path=f"/workspace/shots/ds-{tag}-{t}-{k}.png"); await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
