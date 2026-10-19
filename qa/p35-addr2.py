# pass 31 (build 1610): non-DC address searches from the map and from the All States list (then globe), + reload
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
exec(open('p33-states.py').read().split('NMXY=')[0].split('from gaps import typegq')[1].replace("exec(open('p33-flow.py')","exec(open('p33-flow.py')"))
POP="()=>[...document.querySelectorAll('.leaflet-popup-content')].map(e=>e.innerText.replace(/\\n/g,' | ').slice(0,200))"
MP="()=>{const m=window.__map;return m?[m.getZoom(),+m.getCenter().lat.toFixed(4),+m.getCenter().lng.toFixed(4)]:null}"
ADDR0=[('TX','1100 Congress Ave, Austin, TX 78701'),('FL','400 S Monroe St, Tallahassee, FL 32399'),('AZ','1700 W Washington St, Phoenix, AZ 85007'),('MI','2 Woodward Ave, Detroit, MI 48226'),('PA','1400 John F Kennedy Blvd, Philadelphia, PA 19107'),('PAh','501 N 3rd St, Harrisburg, PA 17120'),('NY','350 5th Ave, New York, NY 10118'),('NYb','209 Joralemon St, Brooklyn, NY 11201')]
import os
ADDR=[a for a in ADDR0 if not os.environ.get('ONLYA') or a[0] in os.environ['ONLYA'].split(',')]
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; paths=sys.argv[3].split(','); out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch()
    for ab,a in ADDR:
      for path in paths:
        c,pg,log=await ctx(b,W,H,W<600,eng); k=f'{ab}-{path}'; R=out[k]={'addr':a}
        await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
        if path.startswith('list'):
          await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200)
          await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
        await pg.touchscreen.tap(*(await center(pg,'#gq'))); await pg.wait_for_timeout(600); await pg.evaluate("()=>document.getElementById('gq').focus()")
        await pg.keyboard.type(a,delay=15); await pg.wait_for_timeout(2500)
        R['sugg']=await pg.evaluate("()=>[...document.querySelectorAll('li')].filter(e=>e.offsetParent).map(e=>e.textContent.trim().slice(0,60)).slice(0,4)")
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(7000)
        R['res']=[await pg.evaluate(HDR),await pg.evaluate(TH),await pg.evaluate(POP),await pg.evaluate(MP),await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())")]
        if path.startswith('list'): R['rows']=(await pg.evaluate(ROWS))[:3]; R['sel']=await pg.evaluate("()=>[...document.querySelectorAll('#listView .lasel')].map(e=>e.innerText.replace(/\\n/g,' | '))")
        await safeshot(pg,f"shots35/b1614p35-{eng[:2]}-{W}x{H}-addr2-{k}.png")
        if path=='list':
          await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(3500)
          R['tomap']=[await pg.evaluate(HDR),await pg.evaluate(TH),await pg.evaluate(POP),await pg.evaluate(MP)]
          await safeshot(pg,f"shots35/b1614p35-{eng[:2]}-{W}x{H}-addr2-{k}-tomap.png")
        await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()"); R['snap_before_reload']=await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"); await pg.wait_for_timeout(1200); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(7000)
        R['reload']=[await pg.evaluate(HDR),await pg.evaluate(TH),await pg.evaluate(POP),await pg.evaluate(MP),await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())")]
        R['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:5]
        await safeshot(pg,f"shots35/b1614p35-{eng[:2]}-{W}x{H}-addr2-{k}-reload.png"); print(k,json.dumps(R)[:2500],flush=True); await c.close()
    await b.close()
  json.dump(out,open(f"b1614p35-addr2-{eng}-{W}x{H}.json",'w'),indent=1)
asyncio.run(main())
