# pass 23: QA-082/QA-083-style jitter check for one viewport (WebKit 320 carry-over): rest positions, wheel drags, smooth scrolls, chip top scan
import asyncio,sys,json,os
from playwright.async_api import async_playwright
from common import *
src=open('p23-jit.py').read(); SAMP=src.split('SAMP="',1)[1].split('"\nasync def',1)[0]
MS=3000
async def main():
  eng=sys.argv[1]; W,H=int(sys.argv[2]),int(sys.argv[3]); R={'size':f'{W}x{H}','eng':eng}
  async with async_playwright() as p:
    b=await getattr(p,eng).launch(); c,pg,log=await ctx(b,W,H,W<600,eng)
    await pg.goto(URL,wait_until="networkidle"); await pg.wait_for_timeout(4000)
    await pg.touchscreen.tap(*(await center(pg,'#bGeo'))); await pg.wait_for_timeout(1200); await pg.touchscreen.tap(*(await center(pg,'li.la-row'))); await pg.wait_for_timeout(5000)
    R['build']=await pg.evaluate('window.BUILD')
    def summ(fr):
      chips=sorted(set(f[1] for f in fr)); rows=sorted(set(f[2] for f in fr)); sts=sorted(set(f[3] for f in fr))
      return {'n':len(fr),'chip':chips,'row':rows,'st':sts}
    for st in [10,22,25,40,97]:
      await pg.evaluate(f"()=>{{document.getElementById('listView').scrollTop={st}}}"); await pg.wait_for_timeout(300); fr=await pg.evaluate(SAMP,MS)
      R[f'set{st}']=fr; print(eng,W,'set',st,summ(fr),fr[:5],flush=True)
    await pg.evaluate("()=>{document.getElementById('listView').scrollTop=0}"); await pg.wait_for_timeout(1200)
    for dy in [40,60,-100,25]:
      await pg.mouse.move(W/2,H*0.6); await pg.mouse.wheel(0,dy); await pg.wait_for_timeout(600); fr=await pg.evaluate(SAMP,MS)
      R[f'wheel{dy}']=fr; print(eng,W,'wheel',dy,summ(fr),fr[:5],flush=True)
    for tgt in [25,60,0]:
      # sample from the start of a smooth scroll (deceleration then stop)
      samp=asyncio.ensure_future(pg.evaluate(SAMP,MS+1000)); await pg.wait_for_timeout(30)
      await pg.evaluate(f"()=>document.getElementById('listView').scrollTo({{top:{tgt},behavior:'smooth'}})"); fr=await samp
      tail=[f for f in fr if f[0]>1000]; R[f'smooth{tgt}']=fr; print(eng,W,'smooth',tgt,'all',summ(fr),'after1s',summ(tail),flush=True)
    ct=[]
    for st in [15,20,22,25,28,30,35,0]:
      await pg.evaluate(f"()=>{{document.getElementById('listView').scrollTop={st}}}"); await pg.wait_for_timeout(900)
      ct.append((st,await pg.evaluate("()=>[Math.round(document.getElementById('laSort').getBoundingClientRect().top*10)/10,document.getElementById('laSort').style.cssText.slice(0,80)]")))
    R['chiptop']=ct; print(eng,W,'chiptop',ct,flush=True)
    await pg.evaluate("()=>{document.getElementById('listView').scrollTop=60}"); await pg.wait_for_timeout(800)
    await pg.screenshot(path=f'../shots/b1595p23-{eng[:2]}-{W}-jitter.png')
    R['err']=log['pageerr'][:3]+[x for x in log['console'] if x.startswith('error')][:3]; print('err',R['err'],flush=True)
    await c.close(); await b.close()
  json.dump(R,open(f'b1595p23-jit-{eng}-{W}x{H}.json','w'),indent=1)
asyncio.run(main())
