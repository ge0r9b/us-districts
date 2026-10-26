# Oct 26 ~10 AM (1623): QA-138 fine timing. Same path as d26h10-hang3 (All States > state > county towns list), then real tap on '16 tick (tick16) or the '16-'20 range (r1620).
# Measures: main-thread longest gap (50 ms heartbeat), time until first row values change, row count, errors.
import asyncio,sys,json,time
from playwright.async_api import async_playwright
from common import *
exec(open('h0800-chip.py').read().split('async def main')[0].split('from gaps import typegq')[1])
ROWS="()=>[...document.querySelectorAll('#listView .lvrow')].filter(e=>e.offsetParent).slice(0,6).map(e=>e.innerText.replace(/\\n/g,' ').slice(0,60))"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; path=sys.argv[3].split(':'); mode=sys.argv[4]
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng); pre=f"shotsb1623/d26h10-{eng[:2]}-{W}x{H}-q138-{'-'.join(path)}-{mode}"
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
    for lvl in path:
      xy=await pg.evaluate(NMXY,lvl); await pg.wait_for_timeout(300); xy=await pg.evaluate(NMXY,lvl); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
    await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(1500)
    r0=await pg.evaluate(ROWS); n0=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow')].filter(e=>e.offsetParent).length")
    print('before',window:=await pg.evaluate("()=>[document.getElementById('crumbs').innerText,window.BUILD,window.__ysl.get(),!!(window.PREC16)]"),n0,r0,flush=True)
    await pg.evaluate("()=>{window.__mg=0;let l=performance.now();window.__hbI=setInterval(()=>{const n=performance.now();window.__mg=Math.max(window.__mg,n-l);l=n},50)}")
    t0=time.time()
    if mode=='tick16':
      xy=await pg.evaluate("()=>{const w=document.querySelector('.kn.a').parentElement;const r=w.getBoundingClientRect();return [r.left+52,r.top+r.height/2]}")
      await pg.touchscreen.tap(*xy)
    elif mode=='r1620': await pg.evaluate("()=>{window.__ySet16(1);return 1}")
    first=None; chg=None
    while time.time()-t0<120:
      try: r=await asyncio.wait_for(pg.evaluate(ROWS),4)
      except Exception: print(round(time.time()-t0,1),'TIMEOUT',flush=True); continue
      if first is None: first=round(time.time()-t0,2)
      if r!=r0 and chg is None: chg=round(time.time()-t0,2)
      if chg is not None and time.time()-t0>chg+3: break
      await asyncio.sleep(0.1)
    mg=await pg.evaluate("()=>window.__mg")
    st=await pg.evaluate("()=>[document.getElementById('crumbs').innerText,window.__ysl.get(),[...document.querySelectorAll('#laCands .lact,.cand')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' '))]")
    n1=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lvrow')].filter(e=>e.offsetParent).length")
    # tap latency after load: tap '24 tick back and forth
    await safeshot(pg,pre+'.png')
    print(json.dumps({'eng':eng,'vp':f'{W}x{H}','path':path,'mode':mode,'first_response_s':first,'rows_changed_s':chg,'max_main_gap_ms':round(mg),'rows_before':n0,'rows_after':n1,'state':st,'rows':await pg.evaluate(ROWS),'pageerr':log['pageerr'],'conerr':[x for x in log['console'] if x.startswith('error')][:5]}),flush=True)
    await b.close()
asyncio.run(main())
