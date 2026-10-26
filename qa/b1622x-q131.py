# Oct 25 (1622): QA-131 verify - city/ZIP then United States; persistent profile, touch
import asyncio,sys,json,shutil
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
S="""()=>{const th=[...document.querySelectorAll('.cand,#laCands .lact')].filter(e=>e.offsetParent).map(e=>e.innerText.replace(/\\n/g,' ')).slice(0,3);
return {build:window.BUILD,heat:typeof heatLevel!=='undefined'?heatLevel:'?',z:+map.getZoom().toFixed(2),c:map.getCenter(),title:(document.getElementById('vtitle')||{}).innerText,crumbs:(document.getElementById('crumbs')||{}).innerText,gq:document.getElementById('gq').value,th,popups:document.querySelectorAll('.leaflet-popup').length,paths:document.querySelectorAll('.leaflet-overlay-pane path').length}}"""
async def main():
  eng=sys.argv[1]; W,H=[int(x) for x in sys.argv[2].split('x')]; out=[]; prof='/tmp/b1622x-prof-%s-%d'%(eng,W); shutil.rmtree(prof,ignore_errors=True)
  tag='shotsb1622/b1622x-q131-%s-%dx%d'%(eng[:2],W,H)
  async with async_playwright() as p:
    c=await getattr(p,eng).launch_persistent_context(prof,viewport={'width':W,'height':H},device_scale_factor=2,has_touch=True,user_agent=UA)
    pg=c.pages[0] if c.pages else await c.new_page(); errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)[:150]))
    async def rec(name):
      await pg.wait_for_timeout(3000); s=await pg.evaluate(S); s['name']=name; s['err']=list(errs); out.append(s); print(json.dumps(s),flush=True); await safeshot(pg,f'{tag}-{name}.png')
    async def enter(q): await typegq(pg,q); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
    await pg.goto(URL+'?cb=1622',wait_until='networkidle',timeout=120000); await rec('00-fresh')
    for q in ['Pittsburgh','15213','Boston','Columbus']:
      await enter(q); await rec(q+'-1'); await enter('United States'); await rec(q+'-2US')
      if q in('Pittsburgh','15213'): await pg.reload(wait_until='networkidle'); await rec(q+'-3reload')
    for k in range(2):
      await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(800)
      xy=await center(pg,'#lyrRow .lbtn[data-k=ushouse]')
      if xy: await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(2500)
      await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(1200)
    await rec('atl-1typeoff'); await pg.reload(wait_until='networkidle'); await rec('atl-2reload')
    await c.close()
  json.dump(out,open('b1622x-q131-%s-%dx%d.json'%(eng,W,H),'w'),indent=1)
asyncio.run(main())
