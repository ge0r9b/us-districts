# QA-085: year taps on Pennsylvania's district-type maps paint in under 100 ms (tap -> rAF -> task), WebKit touch 390/375/320, Chromium 1024x576 and 390 (QA-085 reopened for Chromium).
# State house, state senate, US House and the county map; '16/'24/'20/'24 x3. Pass: median < 100 and at most 1 of 12 taps over 100 (first data load).
# DPR 2 and Chromium is_mobile at every size, same as Bug Tester's qa/common.py ctx().
import asyncio,sys,json
from playwright.async_api import async_playwright
URL=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8843/v2/'; import os; TY=['statehouse','senate','ushouse','map']; PROF=bool(os.environ.get('PROF')); ONLY=os.environ.get('ONLY','');
CFG=[('webkit',390,844),('webkit',375,667),('webkit',320,568),('chromium',1024,576),('chromium',390,844)]
if ONLY: CFG=[x for x in CFG if x[0]==ONLY]
if os.environ.get('TY'): TY=os.environ['TY'].split(',')
F=[]
def ck(c,m,x=None): print(('ok   ' if c else 'FAIL ')+m+('' if c else ' '+json.dumps(x)[:300]),flush=True); (None if c else F.append(m))
LAT="""()=>{window.__lat=null;let done=false;const g=e=>{if(done)return;done=true;const t0=e.timeStamp;requestAnimationFrame(()=>setTimeout(()=>{window.__lat=performance.now()-t0},0));};['pointerup','touchend','click'].forEach(t=>document.addEventListener(t,g,{capture:true,once:true}))}"""
async def center(pg,sel):
  return await pg.evaluate("s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(!r.width)return null;return [r.left+r.width/2,r.top+r.height/2]}",sel)
async def lat(pg,x,y):
  await pg.evaluate(LAT); await pg.touchscreen.tap(x,y)
  for _ in range(60):
    v=await pg.evaluate("()=>window.__lat")
    if v is not None: return round(v)
    await pg.wait_for_timeout(50)
async def main():
  async with async_playwright() as p:
    for ENG,W,H in CFG:
     b=await getattr(p,ENG).launch()
     for ty in TY:
       c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=2,has_touch=True,is_mobile=(ENG=='chromium' or W<600)); pg=await c.new_page(); er=[]; pg.on('pageerror',lambda e:er.append(str(e)[:150]))
       await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(3500)
       await pg.evaluate("()=>{const s=document.getElementById('state');s.value='Pennsylvania';s.onchange&&s.onchange()}"); await pg.wait_for_timeout(4000)
       if ty!='map':
         await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(900)
         await pg.touchscreen.tap(*(await center(pg,f'.lbtn[data-k={ty}]'))); await pg.wait_for_timeout(5000)
         if await pg.evaluate("()=>!document.getElementById('lyrRow').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bLyr'))); await pg.wait_for_timeout(800)
       if await pg.evaluate("()=>document.getElementById('barTime').hidden"): await pg.touchscreen.tap(*(await center(pg,'#bTime'))); await pg.wait_for_timeout(1000)
       out=[]
       for rep in range(3):
         for i,yr in [(0,'16'),(2,'24'),(1,'20'),(2,'24')]:
           xy=await pg.evaluate("i=>{const t=document.querySelector('#ysl .tk[data-i=\"'+i+'\"]');const r=t.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}",i)
           if PROF and rep==1 and yr=='20':
             cdp=await c.new_cdp_session(pg); await cdp.send('Profiler.enable'); await cdp.send('Profiler.setSamplingInterval',{'interval':200}); await cdp.send('Profiler.start')
           v=await lat(pg,*xy); out.append((yr,v))
           if PROF and rep==1 and yr=='20':
             await pg.wait_for_timeout(600); pr=(await cdp.send('Profiler.stop'))['profile']; json.dump(pr,open(f'/tmp/prof-{W}-{ty}.json','w'))
           await pg.wait_for_timeout(2500)
       v=[x[1] or 999 for x in out]; med=sorted(v)[len(v)//2]; ck(med<100 and sum(1 for x in v if x>100)<=1,f'{ENG} {W}x{H} {ty}: year taps median {med} ms, {sum(1 for x in v if x>100)} of {len(v)} over 100 ms',out); ck(not er,f'{ENG} {W} {ty}: no page errors',er); await c.close()
     await b.close()
asyncio.run(main()); print('FAILS',len(F)); sys.exit(1 if F else 0)
