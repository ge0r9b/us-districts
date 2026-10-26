# Oct 26 ~10 AM (1623) copy of d26h09-pa16.py
# Oct 26 ~9 AM (1622) copy of d26h07-pa16.py
# Oct 26 ~6 AM (1622) copy of h0400-pa16.py
# pass 21: PA '16 bar and pie by touch (time row opened first), '16 > '24 > '16
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
G="()=>{const v=e=>{if(!e)return null;const r=e.getBoundingClientRect();return r.width>0&&r.height>0?[Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)]:null};return {b:window.BUILD,y:window.__ymode&&window.__ymode(),mode:window.chartMode,bars:[...document.querySelectorAll('#cands .sebr')].map(b=>[b.dataset.k,v(b.querySelector('.sebt i')),b.innerText.replace(/\\n/g,' ')]),pie:v(document.querySelector('#cands .cpie1 svg')),pietxt:(document.querySelector('#cands .cpie1')||{}).textContent,lbl:[...document.querySelectorAll('#cands .cand')].filter(e=>e.offsetParent).map(e=>(e.getAttribute('aria-label')||'')+' '+((e.querySelector('.cpt')||{}).textContent||''))}}"
async def main():
  eng=sys.argv[1]; out=[]
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); W,H=int(sys.argv[2]),int(sys.argv[3]); c,pg,log=await ctx(b,W,H,W<600,eng)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(5000)
    await typegq(pg,'Pennsylvania'); await pg.wait_for_timeout(600); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
    async def tick(i):
      if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(1000)
      xy=await pg.evaluate("i=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();const N=w.querySelectorAll('.tk').length;return [r.left+52+i/(N-1)*(r.width-104),r.top+r.height/2]}",i)
      await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
    await tick(0)
    for ch in ['bar','pie']:
      await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain'))); await pg.wait_for_timeout(900)
      xy=await center(pg,f'#chartBox .copts button[data-ch={ch}]')
      if xy: await pg.touchscreen.tap(*xy)
      else: await pg.touchscreen.tap(*(await center(pg,'#chartBox .cmain')))
      await pg.wait_for_timeout(2500)
      for i,yl in [(0,'16a'),(2,'24'),(0,'16b')]:
        if yl!='16a': await tick(i)
        g=await pg.evaluate(G); out.append((ch,yl,g)); print(eng,ch,yl,json.dumps(g)[:600],flush=True)
        await safeshot(pg,f'shotsb1623/d26h10-{eng[:2]}-{W}x{H}-PA-{ch}-{yl}.png')
    print('err',log['pageerr'][:3],[x for x in log['console'] if x.startswith('error')][:3]); await b.close()
  json.dump(out,open(f'b1623d26h10-pa16-{eng}-{W}x{H}.json','w'),indent=1)
asyncio.run(main())
