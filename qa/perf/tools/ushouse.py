# first/median US House pick + Back in the PA counties list, per variant; usage: ushouse.py <variants> <vps> <sessions> <wait_ms> <out.json>
import asyncio,json,sys,time,statistics as st
from playwright.async_api import async_playwright
V=sys.argv[1].split(','); VPS=sys.argv[2].split(','); N=int(sys.argv[3]); WAIT=int(sys.argv[4]); OUT=sys.argv[5]
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
ARM="""()=>{window.__lat=null;let done=false;const g=e=>{if(done)return;done=true;const t0=e.timeStamp;requestAnimationFrame(()=>setTimeout(()=>{window.__lat=performance.now()-t0},0))};['pointerup','touchend','click'].forEach(t=>document.addEventListener(t,g,{capture:true,once:true}))}"""
PA="()=>{const r=[...document.querySelectorAll('#listView .lvrow.la')].find(r=>{const n=r.querySelector('.nmx');return n&&n.textContent.trim()==='PA'});if(!r)return null;r.scrollIntoView({block:'center'});const q=r.getBoundingClientRect();return [q.left+60,q.top+q.height/2]}"
AGGJ="()=>{const m=window.__aggDbg().AGG['Pennsylvania|ushouse|2024'];if(!m)return null;return [...m].map(([d,a])=>[d[1],a.dem,a.rep,a.tot,a.n,+(a.cov||0).toFixed(4)]).sort((x,y)=>x[0]<y[0]?-1:1)}"
async def main():
  out={}
  async with async_playwright() as p:
    b=await p.chromium.launch()
    for s in range(N):
      for vp in VPS:
        W,H=map(int,vp.split('x'))
        for v in V:
          c=await b.new_context(viewport={'width':W,'height':H},device_scale_factor=2,is_mobile=True,has_touch=True,user_agent=UA); pg=await c.new_page()
          errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)[:150]))
          async def center(sel): return await pg.evaluate("s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(!r.width)return null;return [r.left+r.width/2,r.top+r.height/2]}",sel)
          async def tapxy(x,y):
            await pg.evaluate(ARM); await pg.touchscreen.tap(x,y)
            for _ in range(80):
              q=await pg.evaluate("()=>window.__lat")
              if q is not None: return round(q,1)
              await pg.wait_for_timeout(50)
          async def tap(sel,w):
            xy=await center(sel)
            if not xy: return None
            r=await tapxy(*xy); await pg.wait_for_timeout(w); return r
          R={'pick':[],'back':[],'errors':errs}
          await pg.goto(f"http://127.0.0.1:8857/{v}/v2/?v=%d"%(time.time()*1000),wait_until="networkidle",timeout=120000); await pg.wait_for_timeout(2500)
          await tap('#bGeo',1200); await tap('li.la-row',3000)
          xy=await pg.evaluate(PA); await pg.wait_for_timeout(300); xy=await pg.evaluate(PA)
          await tapxy(*xy)
          # wait until PA precincts are in, then the idle budget a user gives before tapping
          for _ in range(100):
            if await pg.evaluate("()=>!!(window.PREC||PREC)['Pennsylvania']"): break
            await pg.wait_for_timeout(100)
          await pg.wait_for_timeout(WAIT)
          R['warm_before_tap']=await pg.evaluate("()=>!!window.__aggDbg().AGG['Pennsylvania|ushouse|2024']")
          await tap('#bLyr',800)
          for i in range(5):
            if not await center('#lyrRow .lbtn[data-k=ushouse]'): await tap('#bLyr',800)
            R['pick'].append(await tap('#lyrRow .lbtn[data-k=ushouse]',2500))
            if i==0: R['agg']=await pg.evaluate(AGGJ); R['rows']=await pg.evaluate("()=>document.querySelectorAll('#listView .lvrow.la').length")
            if i<4:
              if not await center('#lyrRow .lbtn[data-k=ushouse]'): await tap('#bLyr',800)
              await tap('#lyrRow .lbtn[data-k=ushouse]',2000)
          for i in range(3):
            R['back'].append(await tap('#bBack',3000))
            xy=await pg.evaluate(PA)
            if xy: await pg.wait_for_timeout(300); xy=await pg.evaluate(PA); await tapxy(*xy); await pg.wait_for_timeout(3500)
          out.setdefault(v,{}).setdefault(vp,[]).append(R); json.dump(out,open(OUT,'w'),indent=1)  # incremental: survive a crash
          print(v,vp,s,'warm',R['warm_before_tap'],'pick',R['pick'],'back',R['back'],'rows',R.get('rows'),errs[:2],flush=True)
          await c.close()
    await b.close()
  json.dump(out,open(OUT,'w'),indent=1)
asyncio.run(main())
