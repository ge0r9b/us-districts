# Oct 26 ~7 AM (1622): probe whether the page stays responsive when the time slider is opened / a range is set in a county towns list (All States > TX > Harris)
import asyncio,sys,json,time
from playwright.async_api import async_playwright
from common import *
exec(open('h0800-chip.py').read().split('async def main')[0].split('from gaps import typegq')[1])
async def ev(pg,js,t=8):
  t0=time.time()
  try: r=await asyncio.wait_for(pg.evaluate(js),t); return [round(time.time()-t0,2),r]
  except Exception as e: return [round(time.time()-t0,2),'ERR '+str(e)[:100]]
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; ab,cty=sys.argv[3].split(':')
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng); pre=f"../shots/b1622d26h07-{eng[:2]}-{W}x{H}-hang-{cty}"
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
    for lvl in [ab,cty]:
      xy=await pg.evaluate(NMXY,lvl); await pg.wait_for_timeout(300); xy=await pg.evaluate(NMXY,lvl); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(5000)
    print('crumbs',await ev(pg,"()=>document.getElementById('crumbs').innerText"),flush=True)
    print('barTime hidden',await ev(pg,"()=>document.getElementById('barTime').hidden"),flush=True)
    print('bTime rect',await ev(pg,"()=>{const r=document.getElementById('bTime').getBoundingClientRect();return [r.left,r.top,r.width]}"),flush=True)
    xy=(await ev(pg,"()=>{const r=document.getElementById('bTime').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"))[1]
    t0=time.time(); await asyncio.wait_for(pg.touchscreen.tap(*xy),15); print('tap bTime',round(time.time()-t0,2),flush=True)
    await pg.wait_for_timeout(1500); print('after bTime',await ev(pg,"()=>[document.getElementById('barTime').hidden,window.__ysl.get()]"),flush=True)
    await safeshot(pg,pre+'-slider.png')
    for js in ["()=>{window.__ySet16(1);return 1}","()=>window.__ysl.get()","()=>{window.__ySelectAll();return 1}","()=>window.__ysl.get()","()=>{window.__ySet16(2);return 1}","()=>window.__ysl.get()"]:
      print(js,await ev(pg,js,15),flush=True); await pg.wait_for_timeout(2500)
    await safeshot(pg,pre+'-range.png')
    print('err',log['pageerr'],[x for x in log['console'] if x.startswith('error')][:5])
    await b.close()
asyncio.run(main())
