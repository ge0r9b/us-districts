# Oct 25 (1621): user's iPhone report - '#' over Gulf, precinct heat at US zoom; WebKit, persistent profile, touch
import asyncio,sys,json,shutil
from playwright.async_api import async_playwright
from common import *
from gaps import typegq
S="""()=>{const b=document.getElementById('bNum');const r=b?b.getBoundingClientRect():null;const bb=document.getElementById('barBottom');const q=bb?bb.getBoundingClientRect():null;
 let ll=null;try{if(r&&r.width)ll=map.containerPointToLatLng([r.left+r.width/2,r.top+r.height/2]);}catch(e){}
 return {build:window.BUILD,heat:typeof heatLevel!=='undefined'?heatLevel:'?',z:map.getZoom(),c:map.getCenter(),st:(typeof state!=='undefined'&&state.value)||'',co:(typeof county!=='undefined'&&county.value)||'',crumbs:(document.getElementById('crumbs')||{}).innerText,list:document.body.classList.contains('listmode'),
  lt:(window.__stateSnapshot?__stateSnapshot().lt:'?'),bNum:r&&[Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)],bNumLL:ll&&[+ll.lat.toFixed(2),+ll.lng.toFixed(2)],bNumPos:b?getComputedStyle(b).position:null,bNumParent:b&&b.parentElement?b.parentElement.id||b.parentElement.className:null,barBottom:q&&[Math.round(q.left),Math.round(q.top),Math.round(q.width),Math.round(q.height)],vv:[innerWidth,innerHeight,visualViewport&&Math.round(visualViewport.height)],
  precPaths:document.querySelectorAll('.leaflet-overlay-pane path').length}}"""
async def main():
  W,H=[int(x) for x in sys.argv[1].split('x')]; out=[]; prof='/tmp/b1621h19-prof-%d'%W; shutil.rmtree(prof,ignore_errors=True)
  tag='shotsb1621/b1621h19-iph-we-%dx%d'%(W,H)
  async with async_playwright() as p:
    async def launch():
      c=await p.webkit.launch_persistent_context(prof,viewport={'width':W,'height':H},device_scale_factor=2,has_touch=True,user_agent=UA)
      pg=c.pages[0] if c.pages else await c.new_page(); errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)[:150])); return c,pg,errs
    async def rec(pg,name,errs):
      await pg.wait_for_timeout(3500)
      try: s=await pg.evaluate(S)
      except Exception as e: s={'err':str(e)[:150]}
      s['name']=name; s['pageerr']=list(errs); out.append(s); print(json.dumps(s),flush=True); await safeshot(pg,f'{tag}-{name}.png')
    async def enter(pg,q):
      await typegq(pg,q); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(5000)
    async def us(pg): await enter(pg,'United States')
    c,pg,errs=await launch(); await pg.goto(URL+'?cb=iph',wait_until='networkidle',timeout=120000); await rec(pg,'00-fresh',errs)
    # path A: drill into a precinct then back to US
    await enter(pg,'Pittsburgh'); await pg.touchscreen.tap(W//2,H//2-60); await pg.wait_for_timeout(3000); await rec(pg,'A1-drilled',errs)
    await us(pg); await rec(pg,'A2-backUS',errs)
    await pg.reload(wait_until='networkidle'); await rec(pg,'A3-reload',errs)
    await c.close(); c,pg,errs=await launch(); await pg.goto(URL,wait_until='networkidle',timeout=120000); await rec(pg,'A4-relaunch',errs)
    # path B: address/ZIP search, back to US, relaunch
    await enter(pg,'15213'); await rec(pg,'B1-zip',errs); await us(pg); await rec(pg,'B2-backUS',errs)
    await c.close(); c,pg,errs=await launch(); await pg.goto(URL,wait_until='networkidle',timeout=120000); await rec(pg,'B3-relaunch',errs)
    # path C: district type set then cleared
    for k in range(2):
      await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(800)
      xy=await center(pg,'#lyrRow .lbtn[data-k=ushouse]')
      if xy: await pg.touchscreen.tap(*xy); await pg.wait_for_timeout(2500)
      await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(1500); await rec(pg,'C%d-type%s'%(k+1,'on' if k==0 else 'off'),errs)
    await pg.reload(wait_until='networkidle'); await rec(pg,'C3-reload',errs)
    # path D: list view round trip, then rotate/resize
    await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(2500); await pg.touchscreen.tap(*(await center(pg,'#bGlobe'))); await pg.wait_for_timeout(2500); await rec(pg,'D1-listRoundtrip',errs)
    await pg.set_viewport_size({'width':H,'height':W}); await rec(pg,'D2-landscape',errs)
    await pg.set_viewport_size({'width':W,'height':H}); await rec(pg,'D3-portrait',errs)
    await pg.set_viewport_size({'width':W,'height':H-300}); await rec(pg,'D4-kbdshrink',errs)
    await pg.set_viewport_size({'width':W,'height':H}); await rec(pg,'D5-restored',errs)
    await c.close(); c,pg,errs=await launch(); await pg.goto(URL,wait_until='networkidle',timeout=120000); await rec(pg,'D6-relaunch',errs)
    await c.close()
  json.dump(out,open('b1621h19-iph-%dx%d.json'%(W,H),'w'),indent=1)
asyncio.run(main())
