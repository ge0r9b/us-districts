# Oct 26 ~10 AM (1623): QA-138 retest (copy of d26h07-hang2.py). All States > state > county towns list (or its map), then mode: tick16 = real tap on the slider's '16 tick; r1620 = __ySet16(1) ('16-'20 range); r2024 = __ySelectAll(); poll page responsiveness every 5 s up to 150 s
import asyncio,sys,json,time
from playwright.async_api import async_playwright
from common import *
exec(open('h0800-chip.py').read().split('async def main')[0].split('from gaps import typegq')[1])
async def ev(pg,js,t=5):
  t0=time.time()
  try: r=await asyncio.wait_for(pg.evaluate(js),t); return [round(time.time()-t0,2),r]
  except Exception as e: return [round(time.time()-t0,2),'TIMEOUT']
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; path=sys.argv[3].split(':'); mode=sys.argv[4]; view=sys.argv[5] if len(sys.argv)>5 else 'list'
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng); pre=f"shotsb1623/d26h10-{eng[:2]}-{W}x{H}-hang-{'-'.join(path)}-{mode}-{view}"
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
    for lvl in path:
      xy=await pg.evaluate(NMXY,lvl); await pg.wait_for_timeout(300); xy=await pg.evaluate(NMXY,lvl); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
    if view=='map': await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(4000)
    print('at',await ev(pg,"()=>[document.getElementById('crumbs').innerText,document.body.classList.contains('listmode'),window.__ysl.get(),[...document.querySelectorAll('#laCands .lact,.cand')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' '))]"),flush=True)
    if mode!='y16c': await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(1500)
    await safeshot(pg,pre+'-0-slider.png')
    t0=time.time()
    if mode=='tick16':
      xy=await pg.evaluate("()=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();return [r.left+52,r.top+r.height/2]}")
      await pg.touchscreen.tap(*xy)
    elif mode=='r1620': await ev(pg,"()=>{window.__ySet16(1);return 1}")
    elif mode=='r2024': await ev(pg,"()=>{window.__ySelectAll();return 1}")
    elif mode in('y16','y16c'): await ev(pg,"()=>{window.__ySetYr(0);return 1}")
    for i in range(int(sys.argv[6]) if len(sys.argv)>6 else 30):
      await asyncio.sleep(2); r=await ev(pg,"()=>[window.__ysl.get(),document.getElementById('crumbs').innerText,[...document.querySelectorAll('#laCands .lact,.cand')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' '))]",4)
      print(round(time.time()-t0,1),r,flush=True)
      if r[1]!='TIMEOUT':
        await safeshot(pg,pre+'-1-after.png'); break
    print('err',log['pageerr'],[x for x in log['console'] if x.startswith('error')][:5],flush=True)
    await b.close()
asyncio.run(main())
