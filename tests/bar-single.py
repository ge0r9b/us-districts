# usage: python3 tests/bar-single.py URL tag -- single-year bar chart is ONE block: [thumbnail on the icon axis] + [bar with its value inside], no text labels/names/table, Other as a gray row, bubbles for names/exact values; # and % modes, phone + desktop
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
        r=await pg.evaluate("""()=>{const x=document.querySelector('#cands .dmx'); if(!x) return {none:true}; const rows=[...x.querySelectorAll('.dmr')]; const rail=document.querySelector('.rail').getBoundingClientRect().left; const im=x.querySelector('img').getBoundingClientRect();
          return {rows:rows.length,txt:x.innerText.replace(/\\s+/g,' ').trim(),ic:Math.round(im.left+im.width/2),maxR:Math.round(Math.max(...[...x.querySelectorAll('.dmb')].map(e=>e.getBoundingClientRect().right))),rail:Math.round(rail),others:[...document.querySelectorAll('#cands > *')].filter(e=>e!==x&&getComputedStyle(e).display!=='none').length,table:!!(document.querySelector('.cleg')&&document.querySelector('.cleg').offsetParent),bub:x.querySelectorAll('[data-party]').length}}""")
        ok=(not r.get('none')) and r['rows']==3 and abs(r['ic']-27)<=2 and r['maxR']<=r['rail'] and r['others']==0 and not r['table'] and not re.search(r'[A-Za-z]{4,}',r['txt'].replace('M','').replace('K','')) and (('%' in r['txt']) if mode=='pct' else not '%' in r['txt'])
        fails+=0 if ok else 1; print(t,mode,'OK' if ok else 'FAIL',json.dumps(r)[:360],flush=True); await pg.screenshot(path=f"/workspace/shots/bs-{tag}-{t}-{mode}.png")
      await pg.evaluate("()=>document.querySelector('#cands .dmx .dmb').dispatchEvent(new MouseEvent('click',{bubbles:true}))"); await pg.wait_for_timeout(300)
      bt=await pg.evaluate("()=>{const e=document.getElementById('partyBub');return e&&e.textContent}"); ok=bool(bt) and re.search(r'\d',bt) is not None; fails+=0 if ok else 1; print(t,'bar bubble','OK' if ok else 'FAIL',bt)
      await pg.close()
    await b.close()
  print('FAILS',fails); sys.exit(1 if fails else 0)
asyncio.run(main())
