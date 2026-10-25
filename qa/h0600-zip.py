# hourly ~3PM (build 1618): QA-107 retest: ZIP searches + address->ZIP fallbacks, map and list paths, popup at centre, reload
import asyncio,sys,json,os
from playwright.async_api import async_playwright
from common import *
exec(open('p33-states.py').read().split('NMXY=')[0].split('from gaps import typegq')[1].replace("exec(open('p33-flow.py')","exec(open('p33-flow.py')"))
POP="()=>[...document.querySelectorAll('.leaflet-popup-content')].map(e=>e.innerText.replace(/\\n/g,' | ').slice(0,200))"
MP="()=>{const m=window.__map;return m?[m.getZoom(),+m.getCenter().lat.toFixed(4),+m.getCenter().lng.toFixed(4)]:null}"
GQ="()=>document.getElementById('gq').value"
SN="()=>JSON.stringify(window.__stateSnapshot())"
Q0=[('z19103','19103'),('z90210','90210'),('z43215','43215'),('z60601','60601'),('z30303','30303'),('stpaul','75 Rev Dr Martin Luther King Jr Blvd, St Paul, MN 55155'),('cbus','1 Capitol Square, Columbus, OH 43215')]
Q=[a for a in Q0 if not os.environ.get('ONLYQ') or a[0] in os.environ['ONLYQ'].split(',')]
async def st(pg): return {'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH),'gq':await pg.evaluate(GQ),'mp':await pg.evaluate(MP),'snap':await pg.evaluate(SN),'pop':await pg.evaluate(POP)}
async def popc(pg):
  # tap map centre to open the popup for the point (the searched point is centred)
  m=await pg.evaluate("()=>{const r=document.getElementById('map').getBoundingClientRect();const p=window.__map.latLngToContainerPoint(window.__map.getCenter());return [r.left+p.x,r.top+p.y]}")
  await pg.touchscreen.tap(*m); await pg.wait_for_timeout(1500); return await pg.evaluate(POP)
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; paths=sys.argv[3].split(','); out={}
  pre=f"shotsh0600/b1618h6-{eng[:2]}-{W}x{H}"
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for k0,a in Q:
      for path in paths:
        c,pg,log=await ctx(b,W,H,W<600,eng); k=f'{k0}-{path}'; R=out[k]={'q':a}
        await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
        if path=='list':
          await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
          await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
        await pg.touchscreen.tap(*(await center(pg,'#gq'))); await pg.wait_for_timeout(600); await pg.evaluate("()=>document.getElementById('gq').focus()")
        await pg.keyboard.type(a,delay=15); await pg.wait_for_timeout(4000)
        R['sugg']=await pg.evaluate("()=>[...document.querySelectorAll('li')].filter(e=>e.offsetParent).map(e=>e.textContent.trim().slice(0,60)).slice(0,4)")
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(9000)
        R['res']=await st(pg)
        if path=='list': R['rows']=(await pg.evaluate(ROWS))[:3]
        await safeshot(pg,f"{pre}-zip-{k}.png")
        if path=='list':
          await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(4000)
          R['tomap']=await st(pg); await safeshot(pg,f"{pre}-zip-{k}-tomap.png")
        await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()"); R['snap_before_reload']=await pg.evaluate(SN); await pg.wait_for_timeout(1200)
        await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(7500)
        R['reload']=await st(pg); await safeshot(pg,f"{pre}-zip-{k}-reload.png")
        try: R['popc']=await popc(pg)
        except Exception as e: R['popc']='err '+str(e)[:80]
        R['after_pop']={'hdr':await pg.evaluate(HDR),'th':await pg.evaluate(TH),'gq':await pg.evaluate(GQ)}
        await safeshot(pg,f"{pre}-zip-{k}-pop.png")
        R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:5]
        print(k,json.dumps(R)[:2600],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1618h0600-zip-{eng}-{W}x{H}-{'_'.join(paths)}.json",'w'),indent=1)
asyncio.run(main())
