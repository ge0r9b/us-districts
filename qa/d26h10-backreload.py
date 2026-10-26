# Oct 26 ~10 AM (1623) copy of d26h09-backreload.py
# Oct 26 ~9 AM (1622): is the list Back button there after a reload of a restored list (state counties, county towns)?
import asyncio,sys,json
from playwright.async_api import async_playwright
from common import *
NMX="t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}"
BK="()=>{const e=document.getElementById('bBack');if(!e)return 'none';const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height),cs.display,cs.visibility,e.hidden,(document.getElementById('crumbs')||{}).innerText]}"
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; st=sys.argv[3]; cty=sys.argv[4]; out={}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng); pre=f"shotsb1623/d26h10-{eng[:2]}-{W}x{H}-bk"
    await pg.goto(URL,wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(4500); out['build']=await pg.evaluate("window.BUILD")
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4500)
    for i,t in enumerate([st,cty]):
      xy=await pg.evaluate(NMX,t); await pg.wait_for_timeout(400); xy=await pg.evaluate(NMX,t); await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(6000)
      await pg.evaluate("()=>document.getElementById('listView').scrollTop=0"); await pg.wait_for_timeout(400)
      L=out[t]={'before':await pg.evaluate(BK)}; await safeshot(pg,f'{pre}-{i}-{t}-before.png')
      await pg.evaluate("()=>window.__stateSaveNow&&window.__stateSaveNow()"); await pg.wait_for_timeout(1200)
      await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(9000)
      L['after']=await pg.evaluate(BK); L['snap']=await pg.evaluate("()=>JSON.stringify(window.__stateSnapshot())"); await safeshot(pg,f'{pre}-{i}-{t}-after-reload.png')
      print(t,json.dumps(L),flush=True)
    out['err']=log['pageerr']+[x for x in log['console'] if x.startswith('error')][:6]; print('err',out['err'])
    json.dump(out,open(f'b1623d26h10-backreload-{eng}-{W}x{H}.json','w'),indent=1); await b.close()
asyncio.run(main())
