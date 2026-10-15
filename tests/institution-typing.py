# usage: python3 tests/institution-typing.py http://localhost:8765/v2/  (checks typing + Enter + field layout, desktop and phone)
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
CASES=[('united states','United States','us'),('united','United','x'),('us','United States','us'),('usa','United States','us'),('canada','Canada','ca'),('pa','Pennsylvania','PA'),('pennsylvania','Pennsylvania','PA'),('colombia','Colombia','co')]
async def main():
  global fails
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H in((1280,800),(430,900)):
      for q,exp,res in CASES:
        pg=await b.new_page(viewport={"width":W,"height":H}); er=[]; pg.on("pageerror",lambda e:er.append(str(e)))
        await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2200)
        await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1300)
        await pg.evaluate("()=>document.querySelector('#crumbs .crumb.glob').click()"); await pg.wait_for_timeout(2200)
        inp=pg.locator('#barGeo .fsq input').first
        await inp.click(); await inp.type(q,delay=40); await pg.wait_for_timeout(800)
        r=await pg.evaluate("()=>{const rows=window.__orgSearchRows(); const i=document.querySelector('#barGeo .fsq input'); const rec=document.querySelector('#barGeo .fsq .fsqrec'); const ir=i.getBoundingClientRect(); const cs=getComputedStyle(i); const rr=rec&&rec.getBoundingClientRect(); return {rows:rows.slice(0,4), n:rows.length, padL:parseFloat(cs.paddingLeft), textX:Math.round(ir.left+parseFloat(cs.paddingLeft)), rec:rec&&rec.innerHTML.length>0, recX:rr&&rec.innerHTML.length?Math.round(rr.left+rr.width/2):null}}")
        okRows=bool(r['rows']) and r['rows'][0].lower().startswith(exp.lower())
        if q in('united',): okRows=bool(r['rows'])
        okLay=r['textX']==52 and (r['rec'] if q not in('united',) else True) and (r['recX'] in(27,None) if q=='united' else r['recX']==27)
        await pg.screenshot(path=f"/workspace/shots/typing-{tag}-{W}-{q.replace(' ','_')}.png")
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(2500)
        a=await pg.evaluate("()=>[window.__W&&window.__W(), state.value, document.body.classList.contains('foldfs')]")
        okEnter= True if q=='united' else (a[0]=='ca' if res=='ca' else (a[1]=='Pennsylvania' if res=='PA' else (a[0]==res or (res=='us' and not a[0] and not a[1]) if res!='x' else True)))
        ok=okRows and okLay and okEnter; fails+=0 if ok else 1
        print(W,q,'OK' if ok else 'FAIL',json.dumps(r),a,'rows',okRows,'layout',okLay,'enter',okEnter,er[:1]); await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
