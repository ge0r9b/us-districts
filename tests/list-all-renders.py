# usage: python3 tests/list-all-renders.py URL tag -- 'List all states' must render >=50 visible rows in map/list/chart(bar,line,pie) modes on desktop+phone; fails when no rows render
import asyncio,sys,json
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
VIS="""()=>{const lv=document.getElementById('listView'); const rows=[...lv.querySelectorAll('.lvrow.la')]; const vis=rows.filter(r=>{const b=r.getBoundingClientRect(); return b.height>0&&r.offsetParent!==null}); const o=vis[0]&&vis[0].getBoundingClientRect(); return {on:window.__LA&&window.__LA.on,n:rows.length,vis:vis.length,body:document.body.className,lvDisp:getComputedStyle(lv).display,lvH:Math.round(lv.getBoundingClientRect().height),first:vis[0]&&vis[0].innerText.slice(0,40).replace(/\\n/g,' | '),sort:!!document.getElementById('laSort')&&getComputedStyle(document.getElementById('laSort')).display}}"""
async def main():
  global fails
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((1280,800,'dk'),(430,900,'ph')):
      for mode in ['map','list','bar','line','pie']:
        pg=await b.new_page(viewport={"width":W,"height":H}); er=[]; pg.on("pageerror",lambda e:er.append(str(e)))
        await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(2500)
        if mode=='list': await pg.evaluate("()=>document.getElementById('bGlobe').click()"); await pg.wait_for_timeout(1200)
        if mode in('bar','line','pie'):
          await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(700)
          await pg.evaluate("(m)=>{const x=[...document.querySelectorAll('button')].find(b=>b.dataset.ch===m); x&&x.click();}",mode); await pg.wait_for_timeout(900)
        pre=await pg.evaluate("()=>document.body.className")
        await pg.evaluate("()=>document.getElementById('bGeo').click()"); await pg.wait_for_timeout(1500)
        await pg.evaluate("()=>document.querySelector('li.la-row').click()"); await pg.wait_for_timeout(4500)
        await pg.evaluate("()=>{ window.__v2&&window.__v2.renderList&&window.__v2.renderList(); }"); await pg.wait_for_timeout(900)
        r=await pg.evaluate(VIS); ok=r['vis']>=51 and not er; fails+=0 if ok else 1
        print(W,mode,'OK' if ok else 'FAIL',json.dumps(r)[:330],'pre=',pre[:40],er[:1])
        await pg.screenshot(path=f"/workspace/shots/lar-{tag}-{t}-{mode}.png"); await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
