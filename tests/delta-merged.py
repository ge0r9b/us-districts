# usage: python3 tests/delta-merged.py URL tag -- two-point bar view: one merged block [2020 thumb]--change bar--[2024 thumb], change values only (no totals / no party text labels), nothing under the floating buttons; # and % modes, phone + desktop
import asyncio,sys,json,re
from playwright.async_api import async_playwright
base=sys.argv[1]; tag=sys.argv[2] if len(sys.argv)>2 else 'x'; fails=0
async def main():
  global fails
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for W,H,t in((430,800,'ph'),(1280,800,'dk')):
      pg=await b.new_page(viewport={"width":W,"height":H}); await pg.goto(base,wait_until="networkidle"); await pg.wait_for_timeout(3000)
      await pg.click("#bTime"); await pg.wait_for_timeout(500); await pg.evaluate("()=>window.__ySelectAll()"); await pg.wait_for_timeout(1500)
      await pg.evaluate("()=>document.querySelector('[aria-label=Chart]').click()"); await pg.wait_for_timeout(600)
      await pg.evaluate("()=>{const x=[...document.querySelectorAll('button')].find(b=>b.dataset.ch==='bar'); x&&x.click();}"); await pg.wait_for_timeout(2500)
      for mode in ('num','pct'):
        await pg.evaluate("m=>window.__setNum(m==='num'?'num':'pct')",mode); await pg.wait_for_timeout(1200)
        r=await pg.evaluate("""()=>{const x=document.querySelector('#cands .dmx'); if(!x) return {none:true}; const rail=document.querySelector('.rail').getBoundingClientRect().left; const rows=[...x.querySelectorAll('.dmr')]; const imgs=[...x.querySelectorAll('img.dmt')].map(i=>i.getBoundingClientRect());
          const dd=[...document.querySelectorAll('#ysl .ylb')]; const db=dd[dd.length-1].getBoundingClientRect(); const lb={right:db.left+db.width/2};
          const vis=[...document.querySelectorAll('#cands > *')].filter(e=>e!==x&&getComputedStyle(e).display!=='none').length;
          return {rows:rows.length,txt:x.innerText.replace(/\\s+/g,' '),maxR:Math.max(...imgs.map(i=>i.right)),minL:Math.min(...imgs.map(i=>i.left)),rail,lblR:lb.right,dotC:lb.right,others:vis,bubbles:x.querySelectorAll('[data-party]').length}}""")
        ok=(not r.get('none')) and r['rows']==3 and r['others']==0 and r['maxR']<=r['rail']-2 and abs(r['maxR']-19-r['dotC'])<=2 and not re.search(r'Republican|Democratic|Other|\\d{2},\\d{3}',r['txt']) and (('%' not in r['txt']) )
        if mode=='num': ok=ok and bool(re.search(r'[MK]',r['txt']))
        fails+=0 if ok else 1; print(t,mode,'OK' if ok else 'FAIL',json.dumps(r)[:330],flush=True)
        await pg.screenshot(path=f"/workspace/shots/dm-{tag}-{t}-{mode}.png")
        if mode=='pct':
          await pg.evaluate("()=>document.querySelector('#cands .dmb').click()"); await pg.wait_for_timeout(300)
          bt=await pg.evaluate("()=>{const e=document.getElementById('partyBub');return e&&e.textContent}"); ok=bool(bt) and 'pts' in bt and len(bt)<=32; fails+=0 if ok else 1; print(t,'bubble','OK' if ok else 'FAIL',bt)
      await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
