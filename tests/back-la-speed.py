# QA-020: WebKit Back from the Los Angeles County cities list to the California counties paints in under 100 ms (was ~400-450),
# and the map's heat layer is rebuilt right after (not lost). WebKit touch 390/375/320, 2 reps each.
# Pass 27: the CA county ROWS must be on screen under 100 ms too (the map layer waits), WebKit 390/375/320 + Chromium 390 and 1024x768, DPR 2.
import asyncio,sys,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8843/v2/'; F=[]
ROWS="""()=>{window.__rows=null;let t0=null;const ok=()=>[...document.querySelectorAll('#listView .lvrow .nmx')].some(e=>e.offsetParent&&/^Alameda/.test(e.textContent.trim()));const g=e=>{if(t0!==null)return;t0=e.timeStamp;const f=()=>{if(ok()){setTimeout(()=>{window.__rows=performance.now()-t0},0);return;}if(performance.now()-t0<4000)requestAnimationFrame(f);};requestAnimationFrame(f);};['pointerup','click'].forEach(t=>document.addEventListener(t,g,{capture:true,once:true}))}"""
def ck(c,m,x=None): print(('ok   ' if c else 'FAIL ')+m+('' if c else ' '+json.dumps(x)[:300]),flush=True); (None if c else F.append(m))
LAT="""()=>{window.__lat=null;let done=false;const g=e=>{if(done)return;done=true;const t0=e.timeStamp;requestAnimationFrame(()=>setTimeout(()=>{window.__lat=performance.now()-t0},0));};['pointerup','touchend','click'].forEach(t=>document.addEventListener(t,g,{capture:true,once:true}))}"""
WRAP="""()=>{ window.__T={}; const names=['drawTowns','drawCtx','updShift','drawCtyFill','drawPrecInDist','refreshLayers','fixLegend','drawCounties','drawStateFill','heatSel','precSrc','redraw','render','renderCands','renderList','drawNat','drawHeat','drawCD','drawDist','crumbs','syncPlot','updateLegend','refreshBubble','layoutSide','setView','drawStates','restyleType'];
 names.forEach(n=>{ const f=window[n]; if(typeof f!=='function'||f.__w) return; const g=function(){ const t=performance.now(); try{ return f.apply(this,arguments); } finally { const d=performance.now()-t; const o=window.__T[n]||(window.__T[n]=[0,0]); o[0]+=d; o[1]++; } }; g.__w=1; try{ window[n]=g; }catch(e){} }); }"""
async def center(pg,sel):
  return await pg.evaluate("s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(!r.width)return null;return [r.left+r.width/2,r.top+r.height/2]}",sel)
async def lat(pg,x,y):
  await pg.evaluate(LAT); await pg.touchscreen.tap(x,y)
  for _ in range(80):
    v=await pg.evaluate("()=>window.__lat")
    if v is not None: return round(v)
    await pg.wait_for_timeout(50)
async def nmxy(pg,t):
  return await pg.evaluate("t=>{const e=[...document.querySelectorAll('#listView .lvrow .nmx')].find(e=>e.offsetParent&&e.textContent.trim().startsWith(t));if(!e)return null;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",t)
async def main():
  async with async_playwright() as p:
    for ENG,W,H in [('webkit',390,844),('webkit',375,667),('webkit',320,568),('chromium',390,844),('chromium',1024,768)]:
     b=await getattr(p,ENG).launch()
     c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=2,has_touch=True,is_mobile=True); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
     await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3500)
     await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(4000)
     for rep in range(2):
       xy=await nmxy(pg,'CA'); await pg.wait_for_timeout(300); l1=await lat(pg,*xy); await pg.wait_for_timeout(3500)
       xy=await nmxy(pg,'Los Angeles'); await pg.wait_for_timeout(300); l2=await lat(pg,*xy); await pg.wait_for_timeout(5000)
       n=await pg.evaluate("()=>document.querySelectorAll('#listView .lvrow').length")
       await pg.evaluate(WRAP); await pg.evaluate("()=>{window.__T={}}")
       await pg.evaluate(ROWS); l3=await lat(pg,*(await center(pg,'#bBack'))); T=await pg.evaluate("()=>window.__T"); await pg.wait_for_timeout(3500); rw=await pg.evaluate("()=>window.__rows"); rw=None if rw is None else round(rw)
       ck(rw is not None and rw<100,f'{ENG} {W} rep {rep}: the CA county rows are on screen {rw} ms after Back',rw)
       n2=await pg.evaluate("()=>document.querySelectorAll('#listView .lvrow').length")
       hl=await pg.evaluate("()=>heatLayer?heatLayer.getLayers().length:-1"); ck(hl>=58,f'{ENG} {W} rep {rep}: the map heat layer is rebuilt after Back ({hl} shapes)',hl)
       l4=await lat(pg,*(await center(pg,'#bBack'))); await pg.wait_for_timeout(3500)
       ck(n>=50 and n2>=50 and l3 is not None and l3<100,f'{ENG} {W} rep {rep}: Back LA cities ({n}) -> CA counties ({n2}) paints in {l3} ms',[l3,T])
     ck(not er,f'{ENG} {W}: no page errors',er); await c.close()
     await b.close()
asyncio.run(main()); print('FAILS',len(F)); sys.exit(1 if F else 0)
